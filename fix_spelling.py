from pathlib import Path
import re

files = ["client.py", "agent.py", "cryptologyt_manager.py"]

for filename in files:
    path = Path.home() / "agi" / filename
    if not path.exists():
        continue
    
    content = path.read_text()
    
    # ৩. সব জায়গায় cryptolyt কে cryptologyt দিয়ে রিপ্লেস করা
    # (কেস সেনসিটিভ - ছোট হাতের অক্ষর)
    content = content.replace("cryptolyt", "cryptologyt")
    # (ক্যাপিটাল অক্ষর)
    content = content.replace("Cryptolyt", "Cryptologyt")
    
    path.write_text(content)
    print(f"✅ {filename} আপডেট করা হয়েছে।")

# ৪. সিস্টেম প্রম্পটে যদি টুলের নাম থাকে, সেটাও ঠিক হয়ে যাবে।
print("\n✅ সব ফাইলের স্পেলিং সফলভাবে ঠিক করা হয়েছে!")
