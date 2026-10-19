from pathlib import Path
import re

# --- ১. bot.py আপডেট করা ---
bot_path = Path("bot.py")
content = bot_path.read_text()

# ১.১. send() ফাংশনে HTML ফরম্যাটিং যোগ করা
old_send = '''def send(chat, text, markup=None):
    text = text or "(empty)"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for i, c in enumerate(chunks):
        p = {"chat_id": chat, "text": c}
        if markup and i == len(chunks) - 1:
            p["reply_markup"] = markup
        tg("sendMessage", **p)'''
new_send = '''def send(chat, text, markup=None):
    text = text or "(empty)"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for i, c in enumerate(chunks):
        p = {"chat_id": chat, "text": c, "parse_mode": "HTML"}
        if markup and i == len(chunks) - 1:
            p["reply_markup"] = markup
        res = tg("sendMessage", **p)
        if not res.get("ok"): # HTML ভাঙলে প্লেইন টেক্সটে পাঠানো
            p.pop("parse_mode")
            tg("sendMessage", **p)'''
content = content.replace(old_send, new_send)

# ১.২. ফাইল পাঠানোর ফাংশন যোগ করা
new_functions = '''
def send_document(chat, filepath, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    try:
        with open(filepath, "rb") as f:
            requests.post(url, data={"chat_id": chat, "caption": caption}, files={"document": f})
        return "File sent successfully."
    except Exception as e:
        return f"Error sending file: {e}"

def download_telegram_file(file_id, save_path):
    file_info = tg("getFile", file_id=file_id)
    if not file_info.get("ok"):
        return None
    file_path = file_info["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    r = requests.get(url)
    if r.status_code == 200:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(r.content)
        return save_path
    return None
'''
if "def send_document" not in content:
    content = content.replace("def work(chat, text):", new_functions + "\ndef work(chat, text):")

# ১.৩. handle() ফাংশনে ফাইল রিসিভ করার লজিক যোগ করা
old_handle = '''    text = ""
    if "text" in m:
        text = m["text"].strip()'''
new_handle = '''    text = ""
    if "document" in m:
        doc = m["document"]
        filename = doc.get("file_name", "uploaded_file")
        save_path = str(agent.WORKSPACE / filename)
        if download_telegram_file(doc["file_id"], save_path):
            send(chat, f"📁 File received and saved to workspace: <code>{filename}</code>")
            text = f"I have uploaded a file named '{filename}' to the workspace. Please analyze it or tell me what to do with it."
        else:
            send(chat, "❌ Failed to download the file.")
            return
    elif "photo" in m:
        photo = m["photo"][-1] # Get the highest resolution
        filename = f"photo_{photo['file_unique_id']}.jpg"
        save_path = str(agent.WORKSPACE / filename)
        if download_telegram_file(photo["file_id"], save_path):
            send(chat, f"📸 Photo received and saved as: <code>{filename}</code>")
            text = f"I have uploaded a photo named '{filename}'. Please analyze it."
        else:
            send(chat, "❌ Failed to download the photo.")
            return
    elif "text" in m:
        text = m["text"].strip()'''
content = content.replace(old_handle, new_handle)

# ১.৪. work() ফাংশনে ফাইল পাঠানোর লজিক যোগ করা (যদি reply-তে FILE_SEND থাকে)
old_work = '''    try:
        send(chat, reply)
    finally:
        busy.release()'''
new_work = '''    try:
        if reply and reply.startswith("FILE_SEND:"):
            filepath = reply.split("FILE_SEND:")[1].strip()
            send_document(chat, filepath, caption="Here is your file.")
        else:
            send(chat, reply)
    finally:
        busy.release()'''
content = content.replace(old_work, new_work)

bot_path.write_text(content)
print("✅ bot.py-তে File Upload/Download সফলভাবে যুক্ত হয়েছে।")

# --- ২. agent.py আপডেট করা (ফাইল পাঠানোর টুল) ---
agent_path = Path("agent.py")
content = agent_path.read_text()

new_tool = '''
@tool
def send_file_to_user(filepath: str) -> str:
    """Send a file from the workspace to the user on Telegram. 
    Provide the relative path (e.g., 'report.txt')."""
    return f"FILE_SEND:{filepath}"
'''

if "@tool\ndef send_file_to_user" not in content:
    content = content.replace('@tool\ndef schedule_task', new_tool + '\n@tool\ndef schedule_task')

# TOOLS ডিকশনারি আপডেট করা
old_tools_pattern = r'TOOLS = \{t\.name: t for t in \[.*?\]\}'
new_tools = 'TOOLS = {t.name: t for t in [run_shell, read_file, write_file, list_files, fetch_url,\n                             battery_status, notify, speak, get_clipboard,\n                             set_clipboard, get_location, vibrate, toggle_torch,\n                             set_volume, get_volume, get_sensor, take_photo,\n                             schedule_task, list_scheduled_tasks, cancel_scheduled_task,\n                             send_file_to_user]}'
content = re.sub(old_tools_pattern, new_tools, content, flags=re.DOTALL)

agent_path.write_text(content)
print("✅ agent.py-তে send_file_to_user টুল যুক্ত হয়েছে।")
