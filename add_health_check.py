from pathlib import Path

bot_path = Path("bot.py")
content = bot_path.read_text()

health_check_code = '''
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
'''

if "health_app = Flask(__name__)" not in content:
    # ইমপোর্ট সেকশনের পরে কোডটি বসানো
    content = content.replace("busy = threading.Lock()", health_check_code + "\nbusy = threading.Lock()")
    bot_path.write_text(content)
    print("✅ bot.py-তে Health Check Server যোগ করা হয়েছে।")
else:
    print("ℹ️ Health Check Server আগেই যোগ করা আছে।")
