from pathlib import Path
import re

bot_path = Path("bot.py")
lines = bot_path.read_text().splitlines()
new_lines = []

# পুরনো ভাঙা Flask/WebSocket/Health Check লাইনগুলো মুছে ফেলা
skip = False
for line in lines:
    if "# ---- Render" in line or "app = Flask" in line or "sock = Sock" in line or "@app.route" in line or "@sock.route" in line or "health_" in line or "run_flask_server" in line or "threading.Thread" in line:
        skip = True
    if not skip:
        new_lines.append(line)
    if "app.run(" in line and skip:
        skip = False

content = "\n".join(new_lines)

# WebSocket এবং Flask সার্ভারের সঠিক কোড ব্লক
server_code = '''
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
'''

# ফাইলের শেষে সঠিক কোডটি বসানো (টেলিগ্রাম লুপের আগে)
if "if __name__ == \"__main__\":" in content:
    content = content.replace("if __name__ == \"__main__\":", server_code + "\nif __name__ == \"__main__\":")
else:
    content += "\n" + server_code

# নিশ্চিত করা যে ws_server.py আর ইমপোর্ট হচ্ছে না
content = content.replace("import ws_server\n", "")

bot_path.write_text(content)
print("✅ bot.py এর Flask এবং WebSocket সেটআপ সফলভাবে ঠিক করা হয়েছে।")
