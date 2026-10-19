from pathlib import Path
bot_path = Path("bot.py")
content = bot_path.read_text()

# flask_sock ইমপোর্ট নিশ্চিত করা
if "from flask_sock import Sock" not in content:
    content = content.replace("from flask import Flask", "from flask import Flask\nfrom flask_sock import Sock")

# app এবং sock ইনিশিয়ালাইজ করা
if "sock = Sock(app)" not in content:
    content = content.replace("app = Flask(__name__)", "app = Flask(__name__)\nsock = Sock(app)")

# WebSocket রুট যুক্ত করা (যদি না থাকে)
if "@sock.route('/ws')" not in content:
    ws_route = '''
@sock.route('/ws')
def ws_handler(ws):
    from flask import request
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

'''
    # app.route('/') এর আগে রুটটি বসানো
    content = content.replace('@app.route("/")', ws_route + '@app.route("/")')

bot_path.write_text(content)
print("✅ bot.py-তে WebSocket রুট যুক্ত করা হয়েছে।")
