from pathlib import Path

bot_path = Path("bot.py")
content = bot_path.read_text()

# dashboard import এবং রেজিস্ট্রেশন যোগ করা
if "from dashboard import register_dashboard_routes" not in content:
    content = content.replace(
        "app = Flask(__name__)",
        "app = Flask(__name__)\nfrom dashboard import register_dashboard_routes, DASHBOARD_STATE\nregister_dashboard_routes(app, SHARED_SECRET, str(agent.WORKSPACE))"
    )

# DASHBOARD_STATE আপডেট করার লজিক যোগ করা (busy, task, logs)
old_send = "def send(chat, text, markup=None):"
new_send = '''def update_dashboard(task="", reply=""):
    """ড্যাশবোর্ডের স্টেট আপডেট করে"""
    try:
        from dashboard import DASHBOARD_STATE
        if task:
            DASHBOARD_STATE["current_task"] = task[:200]
            DASHBOARD_STATE["busy"] = True
        if reply:
            DASHBOARD_STATE["last_reply"] = reply[:200]
            DASHBOARD_STATE["busy"] = False
            DASHBOARD_STATE["recent_logs"].append(f"[Reply] {reply[:100]}")
            DASHBOARD_STATE["recent_logs"] = DASHBOARD_STATE["recent_logs"][-20:]
    except Exception:
        pass

def send(chat, text, markup=None):'''
content = content.replace(old_send, new_send, 1)

# work() ফাংশনে ড্যাশবোর্ড আপডেট কল যোগ করা
content = content.replace(
    'def work(chat, text):\n    try:',
    'def work(chat, text):\n    update_dashboard(task=text)\n    try:'
)
content = content.replace(
    '        send(chat, reply)\n    finally:',
    '        update_dashboard(reply=reply)\n        send(chat, reply)\n    finally:'
)

bot_path.write_text(content)
print("✅ bot.py-তে ড্যাশবোর্ড রুট এবং স্টেট আপডেট যুক্ত হয়েছে।")
