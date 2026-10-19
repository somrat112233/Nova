from pathlib import Path
import re

# --- ১. client.py আপডেট করা (Device ID পাঠানো এবং Command Allowlist চেক) ---
client_path = Path("client.py")
content = client_path.read_text()

# Device ID জেনারেট করা (ফোনের ইউনিক আইডি)
device_id_code = '''
import uuid
import hashlib

# ফোনের ইউনিক Device ID তৈরি করা (প্রথমবার তৈরি হলে সেভ হবে)
DEVICE_ID_FILE = os.path.expanduser("~/.nova_device_id")

def get_device_id():
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE) as f:
            return f.read().strip()
    # ফোনের MAC + Android ID + Random UUID মিলিয়ে ইউনিক আইডি
    unique_data = f"{uuid.getnode()}-{uuid.uuid4().hex[:8]}"
    device_id = hashlib.sha256(unique_data.encode()).hexdigest()[:16]
    with open(DEVICE_ID_FILE, "w") as f:
        f.write(device_id)
    return device_id

DEVICE_ID = get_device_id()
print(f"📱 Device ID: {DEVICE_ID}")
'''

if "DEVICE_ID_FILE" not in content:
    content = content.replace("CLOUD_WS_URL = ", device_id_code + "\nCLOUD_WS_URL = ")

# WebSocket হেডারে Device ID পাঠানো
content = content.replace(
    'extra_headers={"X-Auth-Token": SHARED_SECRET},',
    'extra_headers={"X-Auth-Token": SHARED_SECRET, "X-Device-ID": DEVICE_ID},'
)

# ক্লায়েন্ট সাইডে Allowlist চেক (অতিরিক্ত নিরাপত্তা স্তর)
allowlist_check = '''
# অনুমোদিত কমান্ডের তালিকা (ক্লায়েন্ট সাইডে অতিরিক্ত নিরাপত্তা)
ALLOWED_TOOLS = {
    "battery_status", "notify", "speak", "get_clipboard", "set_clipboard",
    "get_location", "vibrate", "toggle_torch", "set_volume", "get_volume",
    "get_sensor", "take_photo", "schedule_task", "list_scheduled_tasks",
    "cancel_scheduled_task"
}

'''
if "ALLOWED_TOOLS" not in content:
    content = content.replace("def run_termux_command(cmd: list) -> str:", allowlist_check + "def run_termux_command(cmd: list) -> str:")

# execute_tool ফাংশনে Allowlist চেক যোগ করা
old_exec = 'def execute_tool(tool_name: str, args: dict) -> str:\n    if tool_name == "battery_status":'
new_exec = '''def execute_tool(tool_name: str, args: dict) -> str:
    if tool_name not in ALLOWED_TOOLS:
        return f"❌ BLOCKED: Tool '{tool_name}' is not in the client allowlist."
    if tool_name == "battery_status":'''
content = content.replace(old_exec, new_exec)

client_path.write_text(content)
print("✅ client.py-তে Device ID এবং Allowlist যুক্ত হয়েছে।")

# --- ২. bot.py আপডেট করা (সার্ভার সাইডে Device ID ভেরিফিকেশন) ---
bot_path = Path("bot.py")
content = bot_path.read_text()

# ডিভাইস ভেরিফিকেশন লজিক
device_auth_code = '''
# সার্ভার সাইডে অনুমোদিত ডিভাইস এবং কমান্ড
ALLOWED_DEVICES = os.getenv("ALLOWED_DEVICE_IDS", "").split(",")  # কমা দিয়ে আলাদা করা
SERVER_ALLOWED_TOOLS = {
    "battery_status", "notify", "speak", "get_clipboard", "set_clipboard",
    "get_location", "vibrate", "toggle_torch", "set_volume", "get_volume",
    "get_sensor", "take_photo", "schedule_task", "list_scheduled_tasks",
    "cancel_scheduled_task", "run_shell", "read_file", "write_file"
}
'''

if "ALLOWED_DEVICES" not in content:
    content = content.replace("ws_clients = set()", device_auth_code + "\nws_clients = set()")

# WebSocket হ্যান্ডলারে Device ID চেক যোগ করা
old_handler = '''@sock.route('/ws')
def ws_handler(ws):
    token = request.headers.get('X-Auth-Token')
    if token != SHARED_SECRET:
        print("❌ Unauthorized connection attempt.")
        ws.close()
        return
    ws_clients.add(ws)
    print("✅ Phone client connected.")'''

new_handler = '''@sock.route('/ws')
def ws_handler(ws):
    token = request.headers.get('X-Auth-Token')
    device_id = request.headers.get('X-Device-ID', 'unknown')
    
    # সিক্রেট টোকেন চেক
    if token != SHARED_SECRET:
        print(f"❌ Unauthorized: Invalid token from device {device_id}")
        ws.close()
        return
    
    # Device ID Allowlist চেক (যদি Env Var এ সেট থাকে)
    if ALLOWED_DEVICES and ALLOWED_DEVICES[0] and device_id not in ALLOWED_DEVICES:
        print(f"❌ Unauthorized Device: {device_id} is not in allowlist.")
        ws.close()
        return
    
    ws_clients.add(ws)
    print(f"✅ Phone client connected: {device_id}")'''

content = content.replace(old_handler, new_handler)

bot_path.write_text(content)
print("✅ bot.py-তে Device ID ভেরিফিকেশন যুক্ত হয়েছে।")
