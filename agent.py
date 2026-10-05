import os, sys, json, subprocess, getpass
from pathlib import Path
import requests
from dotenv import load_dotenv
from rich.console import Console
from langchain_core.tools import tool
from langchain_core.messages import (
    SystemMessage, HumanMessage, ToolMessage,
    messages_to_dict, messages_from_dict,
)
from langchain_anthropic import ChatAnthropic

ROOT = Path.home() / "agi"
WORKSPACE = ROOT / "workspace"
MEMORY_FILE = ROOT / "memory.json"
ENV_FILE = ROOT / ".env"
WORKSPACE.mkdir(parents=True, exist_ok=True)
load_dotenv(ENV_FILE)

MODEL = os.getenv("AGENT_MODEL", "claude-sonnet-5-5")
MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "15"))
ALLOW_SHELL = os.getenv("AGENT_ALLOW_SHELL", "1") == "1"
console = Console()

SYSTEM = (
    "You are Nova, an autonomous agent running inside Termux on an Android phone. "
    f"Your workspace directory is {WORKSPACE}. Use tools to act: think, call a tool, "
    "read the result, repeat until the task is done, then give a short final answer. "
    "Prefer small, verifiable steps. Never delete anything outside the workspace."
)

def _safe(path: str) -> Path:
    p = (WORKSPACE / path).resolve()
    if WORKSPACE.resolve() not in p.parents and p != WORKSPACE.resolve():
        raise ValueError("Path escapes workspace")
    return p

@tool
def run_shell(command: str) -> str:
    """Run a shell command in the workspace (60s timeout). Returns stdout+stderr."""
    if not ALLOW_SHELL:
        return "Shell tool disabled (AGENT_ALLOW_SHELL=0)."
    if os.getenv("AGENT_CONFIRM_SHELL", "1") == "1":
        import re
        safe = {"ls", "cat", "pwd", "echo", "date", "whoami", "head", "tail",
                "wc", "df", "uname", "uptime"}
        parts = command.strip().split()
        is_safe = bool(parts) and parts[0] in safe and not re.search(r'[;&|<>`$()\n]', command)
        if not is_safe:
            console.print(f"[yellow]Nova wants to run:[/yellow] {command}")
            try:
                ok = input("Allow? [y/N] ").strip().lower() == "y"
            except EOFError:
                ok = False
            if not ok:
                return "DENIED by user. Do not retry this command; ask the user what to do instead."
    try:
        r = subprocess.run(command, shell=True, cwd=WORKSPACE, capture_output=True,
                           text=True, timeout=60)
        return (r.stdout + r.stderr).strip() or f"(exit code {r.returncode}, no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 60s"

@tool
def read_file(path: str) -> str:
    """Read a text file from the workspace (relative path)."""
    return _safe(path).read_text(errors="replace")[:8000]

@tool
def write_file(path: str, content: str) -> str:
    """Write (overwrite) a text file in the workspace (relative path)."""
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Wrote {len(content)} chars to {path}"

@tool
def list_files(path: str = ".") -> str:
    """List files and folders in a workspace directory."""
    items = sorted(x.name + ("/" if x.is_dir() else "") for x in _safe(path).iterdir())
    return "\n".join(items) or "(empty)"

@tool
def fetch_url(url: str) -> str:
    """Fetch a web page or API URL and return the first 6000 characters of text."""
    r = requests.get(url, timeout=20, headers={"User-Agent": "termux-agent"})
    return r.text[:6000]

def _termux(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip() or "(done)"
    except FileNotFoundError:
        return "ERROR: termux-api package missing. Run: pkg install termux-api"
    except subprocess.TimeoutExpired:
        return "ERROR: timed out (is the Termux:API app installed and opened once?)"

@tool
def battery_status() -> str:
    """Get phone battery percentage, charging state and temperature."""
    return _termux(["termux-battery-status"])

@tool
def notify(title: str, text: str) -> str:
    """Show an Android notification on the phone."""
    return _termux(["termux-notification", "--title", title, "--content", text])

@tool
def speak(text: str) -> str:
    """Speak text aloud using the phone text-to-speech."""
    return _termux(["termux-tts-speak", text], timeout=60)

@tool
def get_clipboard() -> str:
    """Read the phone clipboard text."""
    return _termux(["termux-clipboard-get"])

@tool
def set_clipboard(text: str) -> str:
    """Put text on the phone clipboard."""
    return _termux(["termux-clipboard-set", text])

@tool
def get_location() -> str:
    """Get the phone's current GPS/network location as JSON."""
    return _termux(["termux-location", "-p", "network"], timeout=40)

TOOLS = {t.name: t for t in [run_shell, read_file, write_file, list_files, fetch_url,
                             battery_status, notify, speak, get_clipboard,
                             set_clipboard, get_location]}

def learn_ctx(q):
    try:
        import learn
        return learn.context(q)
    except Exception:
        return ""


try:
    import learn
    TOOLS.update(learn.TOOLS)
except Exception as _e:
    print("learn not loaded:", _e)


def ensure_key():
    if os.getenv("AGENT_BACKEND") in ("local", "gemini") or os.getenv("ANTHROPIC_API_KEY"):
        return
    key = getpass.getpass("Enter your ANTHROPIC_API_KEY (saved to ~/agi/.env): ").strip()
    with open(ENV_FILE, "a") as _f:
        _f.write(f"\nANTHROPIC_API_KEY={key}\n")
    os.chmod(ENV_FILE, 0o600)
    os.environ["ANTHROPIC_API_KEY"] = key

def text_of(msg) -> str:
    c = msg.content
    if isinstance(c, str):
        return c
    return "".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")

def load_history():
    if MEMORY_FILE.exists():
        try:
            return messages_from_dict(json.loads(MEMORY_FILE.read_text()))
        except Exception:
            pass
    return []

def save_history(history):
    # keep last ~40 messages, starting on a human turn so tool pairs stay intact
    if len(history) > 40:
        history[:] = history[-40:]
        while history and not isinstance(history[0], HumanMessage):
            history.pop(0)
    MEMORY_FILE.write_text(json.dumps(messages_to_dict(history)))

def run_agent(llm, history, user_input):
    history.append(HumanMessage(content=user_input))
    for step in range(MAX_STEPS):
        ai = llm.invoke([SystemMessage(content=SYSTEM + learn_ctx(user_input))] + history)
        history.append(ai)
        if not ai.tool_calls:
            return text_of(ai)
        for call in ai.tool_calls:
            console.print(f"[cyan]> {call['name']}[/cyan] {str(call['args'])[:150]}")
            try:
                out = TOOLS[call["name"]].invoke(call["args"])
            except Exception as e:
                out = f"ERROR: {e}"
            history.append(ToolMessage(content=str(out)[:8000], tool_call_id=call["id"]))
    return "Stopped: reached max steps."

def main():
    ensure_key()
    if os.getenv("AGENT_BACKEND") == "groq":
        from langchain_openai import ChatOpenAI
        gkey = os.getenv("GROQ_API_KEY")
        if not gkey:
            gkey = getpass.getpass("Enter your GROQ_API_KEY (saved to ~/agi/.env): ").strip()
            with open(ENV_FILE, "a") as f:
                f.write(f"
GROQ_API_KEY={gkey}
")
            os.chmod(ENV_FILE, 0o600)
        llm = ChatOpenAI(model=os.getenv("AGENT_GROQ_MODEL", "llama-3.3-70b-versatile"),
                         base_url="https://api.groq.com/openai/v1",
                         api_key=gkey, max_tokens=2048)
    else:
        llm = ChatAnthropic(model=MODEL, max_tokens=2048)
    llm = llm.bind_tools(list(TOOLS.values()))
    history = load_history()
    if len(sys.argv) > 1:
        console.print(run_agent(llm, history, " ".join(sys.argv[1:])))
        save_history(history)
        return
    console.print("[bold green]Nova ready.[/bold green] /reset clears memory, /exit quits.")
    while True:
        try:
            q = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q == "/exit":
            break
        if q == "/reset":
            history.clear()
            save_history(history)
            console.print("Memory cleared.")
            continue
        try:
            console.print(f"\n[bold magenta]nova>[/bold magenta] {run_agent(llm, history, q)}")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
        save_history(history)

if __name__ == "__main__":
    main()
