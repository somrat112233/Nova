from pathlib import Path
import re

# --- ১. agent.py আপডেট করা (নতুন টুল) ---
agent_path = Path("agent.py")
content = agent_path.read_text()

new_tools_def = '''
@tool
def schedule_task(interval_minutes: int, tool_name: str, args: dict = None, task_id: str = None) -> str:
    """Schedule a recurring task on the phone. 
    interval_minutes: How often to run (e.g., 30).
    tool_name: The name of the tool to run (e.g., 'battery_status', 'get_location').
    args: Optional dictionary of arguments for the tool.
    task_id: Optional unique ID. If not provided, one will be generated."""
    return "Command sent to phone."

@tool
def list_scheduled_tasks() -> str:
    """List all currently scheduled background tasks on the phone."""
    return "Command sent to phone."

@tool
def cancel_scheduled_task(task_id: str) -> str:
    """Cancel a scheduled task by its task_id."""
    return "Command sent to phone."
'''

# নতুন টুল ডেফিনিশন যোগ করা
if "@tool\ndef schedule_task" not in content:
    content = content.replace('@tool\ndef take_photo', new_tools_def + '\n@tool\ndef take_photo')

# TOOLS ডিকশনারি আপডেট করা
old_tools_pattern = r'TOOLS = \{t\.name: t for t in \[.*?\]\}'
new_tools = 'TOOLS = {t.name: t for t in [run_shell, read_file, write_file, list_files, fetch_url,\n                             battery_status, notify, speak, get_clipboard,\n                             set_clipboard, get_location, vibrate, toggle_torch,\n                             set_volume, get_volume, get_sensor, take_photo,\n                             schedule_task, list_scheduled_tasks, cancel_scheduled_task]}'
content = re.sub(old_tools_pattern, new_tools, content, flags=re.DOTALL)

agent_path.write_text(content)
print("✅ agent.py-তে Scheduler টুল যুক্ত হয়েছে।")

# --- ২. client.py আপডেট করা (লোকাল শিডিউলার) ---
client_path = Path("client.py")
content = client_path.read_text()

# execute_tool ফাংশনে নতুন কমান্ড যোগ করা
old_execute = '    elif tool_name == "take_photo":\n        return run_termux_command(["termux-camera-photo", "-c", "0", args.get("filename", "photo.jpg")])'
new_execute = '''    elif tool_name == "take_photo":
        return run_termux_command(["termux-camera-photo", "-c", "0", args.get("filename", "photo.jpg")])
    elif tool_name == "schedule_task":
        import uuid
        tid = args.get("task_id") or str(uuid.uuid4())[:8]
        interval = args.get("interval_minutes", 60)
        t_name = args.get("tool_name")
        t_args = args.get("args", {})
        
        tasks = load_schedule()
        tasks.append({"id": tid, "interval": interval, "tool": t_name, "args": t_args, "next_run": time.time() + (interval * 60)})
        save_schedule(tasks)
        return f"Task {tid} scheduled to run every {interval} minutes."
    elif tool_name == "list_scheduled_tasks":
        tasks = load_schedule()
        if not tasks: return "No scheduled tasks."
        return "\\n".join([f"- {t['id']}: {t['tool']} every {t['interval']} mins" for t in tasks])
    elif tool_name == "cancel_scheduled_task":
        tid = args.get("task_id")
        tasks = load_schedule()
        tasks = [t for t in tasks if t['id'] != tid]
        save_schedule(tasks)
        return f"Task {tid} cancelled."'''

content = content.replace(old_execute, new_execute)

# শিডিউলার লোড/সেভ ফাংশন এবং লুপ যোগ করা
scheduler_code = '''
import json
import time
import threading

SCHEDULE_FILE = "schedule.json"

def load_schedule():
    if os.path.exists(SCHEDULE_FILE):
        try:
            return json.load(open(SCHEDULE_FILE))
        except:
            return []
    return []

def save_schedule(tasks):
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(tasks, f)

def scheduler_loop(websocket_holder):
    while True:
        try:
            tasks = load_schedule()
            now = time.time()
            updated = False
            for t in tasks:
                if now >= t["next_run"]:
                    print(f"⏰ Running scheduled task: {t['id']} ({t['tool']})")
                    # টাস্কটি এক্সিকিউট করে ক্লাউডে পাঠানো
                    result = execute_tool(t["tool"], t["args"])
                    # ক্লাউডে ফলাফল পাঠানো (WebSocket দিয়ে)
                    if websocket_holder.get("ws"):
                        try:
                            ws = websocket_holder["ws"]
                            asyncio.run_coroutine_threadsafe(ws.send(json.dumps({
                                "type": "tool_result",
                                "tool": t["tool"],
                                "result": f"[Scheduled Task {t['id']}] {result}"
                            })), asyncio.get_event_loop())
                        except Exception as e:
                            print(f"Error sending scheduled result: {e}")
                    
                    t["next_run"] = now + (t["interval"] * 60)
                    updated = True
            if updated:
                save_schedule(tasks)
        except Exception as e:
            print(f"Scheduler error: {e}")
        time.sleep(30) # প্রতি ৩০ সেকেন্ডে চেক করবে

# গ্লোবাল ভেরিয়েবল ওয়েবসকেট হোল্ড করার জন্য
ws_holder = {"ws": None}
'''

if "SCHEDULE_FILE" not in content:
    content = content.replace("async def connect_to_cloud():", scheduler_code + "\nasync def connect_to_cloud():")

# connect_to_cloud ফাংশনে ws_holder আপডেট করা
content = content.replace("                async with websockets.connect(", "                ws_holder[\"ws\"] = websocket\n                async with websockets.connect(")
content = content.replace("if __name__ == \"__main__\":\n    asyncio.run(connect_to_cloud())", 
                          "if __name__ == \"__main__\":\n    threading.Thread(target=scheduler_loop, args=(ws_holder,), daemon=True).start()\n    asyncio.run(connect_to_cloud())")

client_path.write_text(content)
print("✅ client.py-তে Background Scheduler যুক্ত হয়েছে।")
