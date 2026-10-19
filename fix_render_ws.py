from pathlib import Path

bot_path = Path("bot.py")
content = bot_path.read_text()

# পুরনো হেলথ চেক ব্লক সরানো
health_old = '''health_check_code = """
# ---- Render Health Check Server ----
from flask import Flask
import threading

health_app = Flask(__name__)

@health_app.route("/")
def health():
    return "Nova is running!", 200

def run_health_server():
    port = int(os.getenv("PORT", 10000))
    health_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# হেলথ চেক সার্ভারটি একটি আলাদা থ্রেডে চালু করা
threading.Thread(target=run_health_server, daemon=True).start()
# -------------------------------------
"""'''

# নতুন কম্বাইন্ড সার্ভার কোড (Flask + WebSocket)
new_server_code = '''
# ---- Render Combined HTTP + WebSocket Server ----
from flask import Flask
from flask_sock import Sock
import threading
import json
import hmac
import hashlib

app = Flask(__name__)
sock = Sock(app)
SHARED_SECRET = os.getenv("AGENT_SHARED_SECRET", "your-secret-here")

# গ্লোবাল ক্লায়েন্ট সেট
ws_clients = set()

@app.route("/")
def health():
    return "Nova is running!", 200

@sock.route('/ws')
def ws_handler(ws):
    # সিকিউর হ্যান্ডশেক ভেরিফিকেশন
    token = ws.headers.get('X-Auth-Token')
    if token != SHARED_SECRET:
        ws.close()
        return
    
    ws_clients.add(ws)
    print("✅ Phone client connected.")
    try:
        while True:
            message = ws.receive()
            if message is None:
                break
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

threading.Thread(target=run_flask_server, daemon=True).start()
# ------------------------------------------------
'''

# ফাইলে পুরনো হেলথ চেক ব্লক রিপ্লেস করা
content = content.replace(health_old, new_server_code)

# bot.py থেকে ws_server.py এর ইমপোর্ট এবং থ্রেডিং সরানো (এখন দরকার নেই)
content = content.replace("import ws_server\n", "")
content = content.replace('threading.Thread(target=lambda: asyncio.run(ws_server.start_ws_server()), daemon=True).start()\n', '')

bot_path.write_text(content)
print("✅ bot.py সফলভাবে আপডেট হয়েছে (Flask + WebSocket একসাথে)।")
