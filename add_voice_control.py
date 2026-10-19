from pathlib import Path
import re

bot_path = Path("bot.py")
content = bot_path.read_text()

# পুরনো টেক্সট হ্যান্ডলিং ব্লকটি খুঁজে বের করা
old_block = '''    m = u.get("message")
    if not m or "text" not in m:
        return
    uid = m["from"]["id"]
    chat = m["chat"]["id"]
    text = m["text"].strip()'''

# নতুন ব্লক যেখানে টেক্সট এবং ভয়েস দুটোই হ্যান্ডল করা হবে
new_block = '''    m = u.get("message")
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
        return'''

# পুরনো ব্লকটি রিপ্লেস করা
if old_block in content:
    content = content.replace(old_block, new_block)
    bot_path.write_text(content)
    print("✅ bot.py-তে Voice Control সফলভাবে যুক্ত করা হয়েছে।")
else:
    print("❌ পুরনো টেক্সট হ্যান্ডলিং ব্লকটি খুঁজে পাওয়া যায়নি। ম্যানুয়ালি চেক করুন।")
