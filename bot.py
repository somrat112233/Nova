import os, sys, json, time, secrets, getpass, threading, hmac, requests
from pathlib import Path
from flask import Flask, request
from flask_sock import Sock

# Agent পাথ সেটআপ
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent

# Telegram কনফিগারেশন
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "dummy_token")
API = f"https://api.telegram.org/bot{TOKEN}/"
OWNER = int(os.getenv("TELEGRAM_OWNER_ID") or 0)
PAIR_CODE = None
FAILS = 0

# WebSocket কনফিগারেশন
SHARED_SECRET = os.getenv("AGENT_SHARED_SECRET", "your-secret-here")
ws_clients = set()

# LLM সেটআপ (Groq)
def build_llm():
    from langchain_openai import ChatOpenAI
    key = os.getenv("GROQ_API_KEY")
    if not key:
        print("GROQ_API_KEY not found. LLM will be unavailable.")
        return None
    llm = ChatOpenAI(model=os.getenv("AGENT_GROQ_MODEL", "llama-3.3-70b-versatile"),
                     base_url="https://api.groq.com/openai/v1",
                     api_key=key, max_tokens=2048)
    return llm.bind_tools(list(agent.TOOLS.values()))

LLM = build_llm()

# টেলিগ্রাম হেল্পার ফাংশন
def tg(method, **params):
    try:
        return requests.post(API + method, json=params, timeout=45).json()
    except Exception as e:
        print("telegram error:", e)
        return {}

def send(chat, text, markup=None):
    text = text or "(empty)"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for i, c in enumerate(chunks):
        p = {"chat_id": chat, "text": c}
        if markup and i == len(chunks) - 1:
            p["reply_markup"] = markup
        tg("sendMessage", **p)

def work(chat, text):
    try:
        history = agent.memory_store.load_history("telegram_session")
        reply = agent.run_agent(LLM, history, text)
        agent.memory_store.save_history("telegram_session", history)
    except Exception as e:
        reply = f"Error: {e}"
    try:
        send(chat, reply)
    finally:
        pass # busy.release() না থাকলে এখানে কিছু করার নেই

def handle(u):
    global OWNER, FAILS, PAIR_CODE
    cq = u.get("callback_query")
    if cq:
        tg("answerCallbackQuery", callback_query_id=cq["id"])
        return

    m = u.get("message")
    if not m:
        return
        
    uid = m["from"]["id"]
    chat = m["chat"]["id"]
    
    text = ""
    if "text" in m:
        text = m["text"].strip()
    elif "voice" in m:
        send(chat, "🎤 Transcribing voice note...")
        try:
            file_id = m["voice"]["file_id"]
            file_info = tg("getFile", file_id=file_id)
            if not file_info.get("ok"):
                send(chat, "❌ Failed to get voice file from Telegram.")
                return
            file_path = file_info["result"]["file_path"]
            url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            
            audio_data = requests.get(url).content
            
            headers = {"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"}
            files = {"file": ("voice.ogg", audio_data)}
            data = {"model": "whisper-large-v3"}
            
            res = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data)
            res_json = res.json()
            
            if "text" not in res_json:
                send(chat, f"❌ Transcription failed: {res_json}")
                return
                
            text = res_json["text"].strip()
            send(chat, f"📝 You said: {text}")
        except Exception as e:
            send(chat, f"Error transcribing: {e}")
            return
    else:
        return

    if not OWNER:
        if text.startswith("/pair"):
            given = text[5:].strip()
            if hmac.compare_digest(given.encode(), (PAIR_CODE or "").encode()):
                OWNER = uid
                agent.save_env("TELEGRAM_OWNER_ID", str(uid))
                send(chat, "Paired. Nova is ready - send me a task.")
            else:
                FAILS += 1
                send(chat, "Wrong code.")
                if FAILS >= 5:
                    sys.exit("Too many wrong pairing codes.")
        else:
            send(chat, "Send: /pair <code shown in Termux>")
        return

    if uid != OWNER:
        return

    if text in ("/start", "/help"):
        send(chat, "Nova ready. Send any task. /reset clears memory.")
        return
    if text == "/reset":
        agent.memory_store.save_history("telegram_session", [])
        send(chat, "Memory cleared.")
        return

    send(chat, "Working...")
    threading.Thread(target=work, args=(chat, text), daemon=True).start()

def run_telegram_bot():
    global PAIR_CODE
    if not OWNER:
        PAIR_CODE = f"{secrets.randbelow(10**6):06d}"
        print(f"\n>>> PAIRING CODE: {PAIR_CODE}")
        print(">>> In Telegram, send:  /pair " + PAIR_CODE + "\n")
    print("🚀 Telegram bot is running...")
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
            time.sleep(5)
            continue
        for u in r.get("result", []):
            offset = u["update_id"] + 1
            try:
                handle(u)
            except Exception as e:
                print("handler error:", e)

# ---- Render Combined HTTP + WebSocket Server ----
app = Flask(__name__)
sock = Sock(app)

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

if __name__ == "__main__":
    # ১. টেলিগ্রাম বট চালু করা (ব্যাকগ্রাউন্ড থ্রেডে)
    threading.Thread(target=run_telegram_bot, daemon=True).start()
    
    # ২. Flask সার্ভার চালু করা (মূল থ্রেডে, যাতে Render পোর্ট ডিটেক্ট করতে পারে)
    port = int(os.getenv("PORT", 10000))
    print(f"🌐 Starting Flask server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
