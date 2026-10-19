from pathlib import Path
import re

bot_path = Path("bot.py")
content = bot_path.read_text()

# ১. আগের সব app এবং sock ডেফিনিশন মুছে ফেলা
content = re.sub(r'app = Flask\(__name__\)\s*\nsock = Sock\(app\)', '', content)
content = re.sub(r'app = Flask\(__name__\)', '', content)

# ২. WebSocket সেকশনের আগে সঠিকভাবে app এবং sock ডেফিনিশন বসানো
server_setup = '''
# ---- Render Combined HTTP + WebSocket Server ----
from flask import Flask
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)
'''

# হেলথ চেক সেকশনটি খুঁজে বের করে তার আগে সেটআপ বসানো
if "health_app = Flask(__name__)" in content:
    content = content.replace("health_app = Flask(__name__)", server_setup + "\n# health_app removed")
else:
    # যদি হেলথ চেক না থাকে, তবে ওয়েবসকেট রুটের আগে বসানো
    content = content.replace("@sock.route('/ws')", server_setup + "\n@sock.route('/ws')")

bot_path.write_text(content)
print("✅ bot.py-তে Flask app এবং Sock সঠিকভাবে সেট করা হয়েছে।")
