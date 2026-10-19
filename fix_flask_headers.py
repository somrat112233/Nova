from pathlib import Path
bot_path = Path("bot.py")
content = bot_path.read_text()

# হেডার চেকিং লাইনটি খুঁজে বের করে ফিক্স করা
old_header = "    token = ws.headers.get('X-Auth-Token')"
new_header = "    from flask import request\n    token = request.headers.get('X-Auth-Token')"

if old_header in content:
    content = content.replace(old_header, new_header)
    bot_path.write_text(content)
    print("✅ bot.py-তে হেডার চেকিং ফিক্স করা হয়েছে।")
else:
    print("ℹ️ হেডার চেকিং আগেই ফিক্স করা আছে।")
