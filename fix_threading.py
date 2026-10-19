from pathlib import Path
import re

bot_path = Path("bot.py")
content = bot_path.read_text()

# ১. আগের Flask সার্ভার ফাংশন এবং থ্রেড কল মুছে ফেলা
content = re.sub(r'def run_flask_server\(\):.*?threading\.Thread\(target=run_flask_server, daemon=True\)\.start\(\)', '', content, flags=re.DOTALL)

# ২. Telegram পোলিং লুপটি খুঁজে বের করে একটি ফাংশনে রূপান্তর করা
match = re.search(r'(print\(f?"Nova Telegram bot running.*?while True:.*)', content, re.DOTALL)
if match:
    polling_block = match.group(1)
    content = content.replace(polling_block, '')
    
    # লুপটিকে ইন্ডেন্ট করে ফাংশনের ভেতরে বসানো
    indented_block = '\n'.join('    ' + line for line in polling_block.splitlines())
    telegram_func = f"\ndef run_telegram_bot():\n    print('Starting Telegram bot thread...')\n{indented_block}\n"
    content += telegram_func
    print("✅ Telegram পোলিং লুপ সফলভাবে আলাদা ফাংশনে রূপান্তরিত হয়েছে।")
else:
    print("❌ Telegram পোলিং লুপ খুঁজে পাওয়া যায়নি। ম্যানুয়ালি চেক করুন।")

# ৩. আগের কোনো __main__ ব্লক থাকলে মুছে ফেলা
content = content.replace('if __name__ == "__main__":', '')

# ৪. নতুন সঠিক স্টার্টআপ ব্লক যোগ করা
startup_code = '''
if __name__ == "__main__":
    import threading
    print("🚀 Starting Telegram bot in background thread...")
    threading.Thread(target=run_telegram_bot, daemon=True).start()
    
    port = int(os.getenv("PORT", 10000))
    print(f"🌐 Starting Flask server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
'''
content += startup_code
bot_path.write_text(content)
print("✅ bot.py সফলভাবে আপডেট হয়েছে। Flask এখন Main Thread এ চলবে।")
