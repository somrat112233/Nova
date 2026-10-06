import os, sys, json, subprocess, getpass
from pathlib import Path
import requests
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
from rich.console import Console
from langchain_core.tools import tool
from langchain_core.messages import (
    SystemMessage, HumanMessage, ToolMessage,
    messages_to_dict, messages_from_dict,
)
from langchain_openai import ChatOpenAI

ROOT = Path.home() / "agi"
WORKSPACE = ROOT / "workspace"
ENV_FILE = ROOT / ".env"
WORKSPACE.mkdir(parents=True, exist_ok=True)
load_dotenv(ENV_FILE)

MODEL = os.getenv("AGENT_MODEL", "openai/gpt-oss-120b")
MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "15"))
ALLOW_SHELL = os.getenv("AGENT_ALLOW_SHELL", "1") == "1"
console = Console()

# --- System Prompt (নিরাপদ ও পরিষ্কার) ---
SYSTEM = (
    "You are Nova, an autonomous AI agent running inside Termux on an Android phone. "
    "Your workspace is /opt/render/agi/workspace. "
    "Current capabilities: run_shell, read_file, write_file, list_files, fetch_url, "
    "battery_status, notify, speak, get_clipboard, set_clipboard, get_location, "
    "vibrate, toggle_torch, set_volume, get_volume, get_sensor, take_photo, "
    "send_file_to_user, schedule_task, list_scheduled_tasks, cancel_scheduled_task, "
    "remember, recall, forget, save_skill, list_skills. "
    "You can execute shell commands, but you cannot use root privileges. "
    "You cannot install new packages unless the user explicitly allows it. "
    "You are sandboxed to the workspace directory. "
    "You must NEVER store or retrieve secrets in long-term memory. "
    "Future goals: Encourage installing the full termux-api suite. "
    "Suggest scheduling background tasks. Suggest voice control. "
    "Always prioritize small, verifiable steps. Never delete anything outside the workspace."
)

def _safe(path: str) -> Path:
    p = (WORKSPACE / path).resolve()
    if WORKSPACE.resolve() not in p.parents and p != WORKSPACE.resolve():
        raise ValueError("Path escapes workspace")
    return p

# --- Neon Database Memory Manager ---
class NeonMemoryStore:
    def __init__(self, connection_string):
        self.conn_string = connection_string
        if not self.conn_string:
            print("WARNING: NEON_DATABASE_URL is not set. Memory will not be persistent.")
            self.enabled = False
            return
        self.enabled = True
        self._init_table()

    def _init_table(self):
        if not self.enabled: return
        try:
            with psycopg2.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS chat_history (
                            id SERIAL PRIMARY KEY,
                            session_id TEXT NOT NULL,
                            message_json JSONB NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        );
                    """)
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON chat_history(session_id);")
                    conn.commit()
        except Exception as e:
            print(f"Neon DB Init Error: {e}")

    def load_history(self, session_id: str):
        if not self.enabled: return []
        try:
            with psycopg2.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT message_json FROM chat_history WHERE session_id = %s ORDER BY id ASC", (session_id,))
                    rows = cur.fetchall()
                    if not rows: return []
                    return messages_from_dict([row[0] for row in rows])
        except Exception as e:
            print(f"Error loading history: {e}")
            return []

    def save_history(self, session_id: str, history: list):
        if not self.enabled: return
        try:
            with psycopg2.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM chat_history WHERE session_id = %s", (session_id,))
                    for msg in history:
                        msg_dict = messages_to_dict([msg])[0]
                        cur.execute("INSERT INTO chat_history (session_id, message_json) VALUES (%s, %s)", (session_id, Json(msg_dict)))
                    conn.commit()
        except Exception as e:
            print(f"Error saving history: {e}")

memory_store = NeonMemoryStore(os.getenv("NEON_DATABASE_URL"))

def load_history():
    return memory_store.load_history("default_session")

def save_history(history):
    memory_store.save_history("default_session", history)

# --- Tools ---
@tool
def run_shell(command: str) -> str:
    """Run a shell command in the workspace (60s timeout). Returns stdout+stderr."""
    if not ALLOW_SHELL: return "Shell tool disabled."
    try:
        r = subprocess.run(command, shell=True, cwd=WORKSPACE, capture_output=True, text=True, timeout=60)
        return (r.stdout + r.stderr).strip() or f"(exit code {r.returncode}, no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 60s"

@tool
def read_file(path: str) -> str:
    """Read a text file from the workspace (relative path)."""
    return _safe(path).read_text(errors="replace")[:8000]

@tool
def write_file(path: str, content: str) -> str:
    """Write (overwrite) a text file in the workspace."""
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

@tool
def battery_status() -> str: return "Command sent to phone."
@tool
def notify(title: str, text: str) -> str: return "Command sent to phone."
@tool
def speak(text: str) -> str: return "Command sent to phone."
@tool
def get_clipboard() -> str: return "Command sent to phone."
@tool
def set_clipboard(text: str) -> str: return "Command sent to phone."
@tool
def get_location() -> str: return "Command sent to phone."
@tool
def vibrate(duration_ms: int = 1000) -> str: return "Command sent to phone."
@tool
def toggle_torch(state: str = "on") -> str: return "Command sent to phone."
@tool
def set_volume(stream: str = "music", volume: int = 50) -> str: return "Command sent to phone."
@tool
def get_volume() -> str: return "Command sent to phone."
@tool
def get_sensor(sensor_name: str = "accelerometer") -> str: return "Command sent to phone."
@tool
def take_photo(filename: str = "photo.jpg") -> str: return "Command sent to phone."
@tool
def send_file_to_user(filepath: str) -> str: return f"FILE_SEND:{filepath}"
@tool
def schedule_task(interval_minutes: int, tool_name: str, args: dict = None, task_id: str = None) -> str: return "Command sent to phone."
@tool
def list_scheduled_tasks() -> str: return "Command sent to phone."
@tool
def cancel_scheduled_task(task_id: str) -> str: return "Command sent to phone."

# Learning Tools
try:
    import learn
    from learn import remember, recall, forget, save_skill, list_skills
except Exception as _e:
    print("learn not loaded:", _e)
    @tool
    def remember(topic: str, fact: str) -> str: return "Learning module not loaded."
    @tool
    def recall(query: str) -> str: return "Learning module not loaded."
    @tool
    def forget(contains: str) -> str: return "Learning module not loaded."
    @tool
    def save_skill(name: str, description: str, code: str) -> str: return "Learning module not loaded."
    @tool
    def list_skills() -> str: return "Learning module not loaded."

TOOLS = {t.name: t for t in [
    run_shell, read_file, write_file, list_files, fetch_url,
    battery_status, notify, speak, get_clipboard, set_clipboard,
    get_location, vibrate, toggle_torch, set_volume, get_volume,
    get_sensor, take_photo, send_file_to_user, schedule_task,
    list_scheduled_tasks, cancel_scheduled_task, remember, recall,
    forget, save_skill, list_skills
]}

def learn_ctx(q):
    try: return learn.context(q)
    except Exception: return ""

def ensure_key():
    backend = os.getenv("AGENT_BACKEND", "groq")
    if backend in ("local", "gemini", "groq") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GROQ_API_KEY"):
        return

def text_of(msg) -> str:
    c = msg.content
    if isinstance(c, str): return c
    return "".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")

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
    backend = os.getenv("AGENT_BACKEND", "groq")
    if backend == "groq":
        gkey = os.getenv("GROQ_API_KEY")
        if not gkey: sys.exit("GROQ_API_KEY missing")
        llm = ChatOpenAI(model=os.getenv("AGENT_GROQ_MODEL", "openai/gpt-oss-120b"),
                         base_url="https://api.groq.com/openai/v1",
                         api_key=gkey, max_tokens=2048)
    else:
        sys.exit("Only Groq backend is configured for this deployment.")
    
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
        if not q: continue
        if q == "/exit": break
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
