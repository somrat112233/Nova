import os, re, sys, time, secrets, getpass, threading, hmac
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent
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
    from langchain_openai import ChatOpenAI
    key = os.getenv("GROQ_API_KEY")
    if not key:
        sys.exit("GROQ_API_KEY not found. Please add it to Render Environment Variables.")
    llm = ChatOpenAI(model=os.getenv("AGENT_GROQ_MODEL", "llama-3.3-70b-versatile"),
                     base_url="https://api.groq.com/openai/v1",
                     api_key=key, max_tokens=2048)
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



# হেলথ চেক সার্ভারটি একটি আলাদা থ্রেডে চালু করা

# ---- Render Combined HTTP + WebSocket Server ----
from flask import Flask, request
from flask_sock import Sock
import threading
import json
import hmac
import hashlib

app = Flask(__name__)
sock = Sock(app)
SHARED_SECRET = os.getenv("AGENT_SHARED_SECRET", "your-secret-here")
ws_clients = set()

@app.route("/")
def health_check():
    return "Nova is running!", 200

@sock.route('/ws')
def ws_handler(ws):
    token = request.headers.get('X-Auth-Token')
    if token != SHARED_SECRET:
        print("❌ Unauthorized connection attempt.")
        ws.close()
        return
    ws_clients.add(ws)
    print("✅ Phone client connected.")
    try:
        while True:
            message = ws.receive()
            if message is None: break
            data = json.loads(message)
            if data.get("type") == "tool_result":
                print(f"[Phone Result] {data.get('tool')}: {data.get('result')}")
    except Exception as e:
        print(f"WS Error: {e}")
    finally:
        ws_clients.discard(ws)
        print("❌ Phone client disconnected.")

def run_flask_server():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# সার্ভার চালু করা (ব্যাকগ্রাউন্ডে)
threading.Thread(target=run_flask_server, daemon=True).start()
# ------------------------------------------------
