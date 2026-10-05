import os, re, sys, time, secrets, getpass, threading, hmac
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent
import ws_server
import asyncio

if "Nova wants to run" not in (HERE / "agent.py").read_text():
    sys.exit("Shell confirmation patch missing in agent.py. Apply the confirmation step first.")

agent.MEMORY_FILE = HERE / "memory_telegram.json"
os.environ["AGENT_CONFIRM_SHELL"] = "1"
ENV_FILE = agent.ENV_FILE


def save_env(key, value):
    with open(ENV_FILE, "a") as f:
        f.write(f"\n{key}={value}\n")
    os.chmod(ENV_FILE, 0o600)
    os.environ[key] = value


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    TOKEN = getpass.getpass("Enter TELEGRAM_BOT_TOKEN (from @BotFather, saved to ~/agi/.env): ").strip()
    save_env("TELEGRAM_BOT_TOKEN", TOKEN)
API = f"https://api.telegram.org/bot{TOKEN}/"
OWNER = int(os.getenv("TELEGRAM_OWNER_ID") or 0)
PAIR_CODE = None
FAILS = 0


def tg(method, **params):
    try:
        return requests.post(API + method, json=params, timeout=45).json()
    except Exception as e:
        print("telegram error:", e)
        return {}


def send(chat, text, markup=None):
    text = text or "(empty)"
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
    for i, c in enumerate(chunks):
        p = {"chat_id": chat, "text": c}
        if markup and i == len(chunks) - 1:
            p["reply_markup"] = markup
        tg("sendMessage", **p)


def build_llm():
    backend = os.getenv("AGENT_BACKEND", "anthropic")
    if backend == "local":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="local", base_url="http://127.0.0.1:8080/v1",
                         api_key="none", max_tokens=1024, temperature=0.2)
    elif backend == "groq":
        from langchain_openai import ChatOpenAI
        key = os.getenv("GROQ_API_KEY")
        if not key:
            sys.exit("GROQ_API_KEY not found. Please add it to Render Environment Variables.")
        llm = ChatOpenAI(model=os.getenv("AGENT_GROQ_MODEL", "llama-3.3-70b-versatile"),
                         base_url="https://api.groq.com/openai/v1",
                         api_key=key, max_tokens=2048)
    else:
        agent.ensure_key()
        llm = agent.ChatAnthropic(model=agent.MODEL, max_tokens=2048)
    return llm.bind_tools(list(agent.TOOLS.values()))


LLM = build_llm()

# ---- shell confirmation via Telegram buttons ----
pending = {"event": None, "answer": False}
last_print = {"text": ""}


class FakeConsole:
    def __init__(self, real):
        self.real = real

    def print(self, *a, **k):
        text = " ".join(str(x) for x in a)
        last_print["text"] = re.sub(r"\[/?[a-z ]+\]", "", text)
        self.real.print(*a, **k)


agent.console = FakeConsole(agent.console)


def tg_input(prompt=""):
    ev = threading.Event()
    pending["answer"] = False
    pending["event"] = ev
    markup = {"inline_keyboard": [[
        {"text": "✅ Allow", "callback_data": "allow"},
        {"text": "❌ Deny", "callback_data": "deny"},
    ]]}
    send(OWNER, last_print["text"] + "\n\nAllow? (auto-deny in 2 min)", markup)
    ev.wait(120)
    pending["event"] = None
    return "y" if pending["answer"] else "n"


agent.input = tg_input

busy = threading.Lock()


def work(chat, text):
    try:
        history = agent.load_history()
        reply = agent.run_agent(LLM, history, text)
        agent.save_history(history)
    except Exception as e:
        reply = f"Error: {e}"
    try:
        send(chat, reply)
    finally:
        busy.release()


def handle(u):
    global OWNER, FAILS
    cq = u.get("callback_query")
    if cq:
        tg("answerCallbackQuery", callback_query_id=cq["id"])
        if cq["from"]["id"] != OWNER:
            return
        ev = pending["event"]
        if ev:
            pending["answer"] = cq.get("data") == "allow"
            ev.set()
        else:
            send(OWNER, "That request already expired.")
        return

    m = u.get("message")
    if not m or "text" not in m:
        return
    uid = m["from"]["id"]
    chat = m["chat"]["id"]
    text = m["text"].strip()

    if not OWNER:
        if text.startswith("/pair") and chat == uid:
            given = text[5:].strip()
            if hmac.compare_digest(given.encode(), PAIR_CODE.encode()):
                OWNER = uid
                save_env("TELEGRAM_OWNER_ID", str(uid))
                send(chat, "Paired. Nova is ready - send me a task.")
            else:
                FAILS += 1
                send(chat, "Wrong code.")
                if FAILS >= 5:
                    sys.exit("Too many wrong pairing codes. Restart the bot.")
        else:
            send(chat, "Send: /pair <code shown in Termux>")
        return

    if uid != OWNER:
        return

    if text in ("/start", "/help"):
        send(chat, "Nova ready. Send any task. /reset clears memory.")
        return
    if text == "/reset":
        if busy.locked():
            send(chat, "Nova is busy, try again after it finishes.")
        else:
            agent.save_history([])
            send(chat, "Memory cleared.")
        return
    if not busy.acquire(blocking=False):
        send(chat, "Nova is still working on the previous task.")
        return
    send(chat, "Working...")
    threading.Thread(target=work, args=(chat, text), daemon=True).start()


if not OWNER:
    PAIR_CODE = f"{secrets.randbelow(10**6):06d}"
    print(f"\n>>> PAIRING CODE: {PAIR_CODE}")
    print(">>> In Telegram, open your bot and send:  /pair " + PAIR_CODE + "\n")

print(f"Nova Telegram bot running (backend: {os.getenv('AGENT_BACKEND', 'anthropic')}). Ctrl+C to stop.")
offset = None
while True:
    params = {"timeout": 30, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        params["offset"] = offset
    try:
        r = requests.post(API + "getUpdates", json=params, timeout=45).json()
    except Exception:
        time.sleep(3)
        continue
    if not r.get("ok", True):
        print("Telegram error:", r)
        if r.get("error_code") in (401, 404):
            sys.exit("Bot token is invalid. Fix TELEGRAM_BOT_TOKEN in ~/agi/.env")
        time.sleep(5)
        continue
    for u in r.get("result", []):
        offset = u["update_id"] + 1
        try:
            handle(u)
        except SystemExit:
            raise
        except Exception as e:
            print("handler error:", e)


import threading
threading.Thread(target=lambda: asyncio.run(ws_server.start_ws_server()), daemon=True).start()
