from pathlib import Path
import re

client_path = Path.home() / "agi" / "client.py"
content = client_path.read_text()

# যদি ইতিমধ্যেই যোগ হয়ে থাকে, বাদ দিন
if "cryptolyt_status" in content and "import cryptolyt_manager" in content:
    print("ℹ️ Cryptolyt টুল আগেই যোগ করা আছে।")
    exit(0)

# Cryptolyt টুল কোড ব্লক (execute_tool ফাংশনের জন্য)
crypto_block = '''
    # ==================== Cryptolyt Tools ====================
    elif tool_name == "cryptolyt_status":
        import sys, json
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        return json.dumps(cm.cryptolyt_status(), indent=2)
    elif tool_name == "cryptolyt_start":
        import sys
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        return cm.cryptolyt_start()
    elif tool_name == "cryptolyt_stop":
        import sys
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        return cm.cryptolyt_stop()
    elif tool_name == "cryptolyt_logs":
        import sys
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        return cm.cryptolyt_logs(args.get("lines", 50), args.get("log_type", "main"))
    elif tool_name == "cryptolyt_signals":
        import sys, json
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        return json.dumps(cm.cryptolyt_parse_signals(args.get("lines", 500)), indent=2, ensure_ascii=False)
    elif tool_name == "cryptolyt_health":
        import sys, json
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        return json.dumps(cm.cryptolyt_health_check(), indent=2)
    elif tool_name == "cryptolyt_recent_trades":
        import sys
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        return cm.cryptolyt_recent_trades(args.get("lines", 200))
    elif tool_name == "cryptolyt_summary":
        import sys, json
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        return json.dumps(cm.cryptolyt_summary(), indent=2, ensure_ascii=False)
'''

# শেষ "else:" (Unknown tool) এর আগে cryptolyt block বসান
# execute_tool ফাংশনের শেষে সাধারণত "Unknown tool" থাকে
pattern = r'(\n\s+else:\s*\n\s+return f"ERROR: Unknown tool \{tool_name\}")'
match = re.search(pattern, content)

if match:
    insertion_pos = match.start()
    content = content[:insertion_pos] + "\n" + crypto_block + content[insertion_pos:]
    client_path.write_text(content)
    print("✅ client.py-তে Cryptolyt টুল সফলভাবে যোগ করা হয়েছে।")
else:
    # Alternative: খুঁজে দেখুন কোথায় "termux_storage_info" ব্লক শেষ হয়েছে
    fallback_pattern = r'(elif tool_name == "termux_storage_info":.*?return f"Error: \{e\}")'
    fb_match = re.search(fallback_pattern, content, re.DOTALL)
    if fb_match:
        insertion_pos = fb_match.end()
        content = content[:insertion_pos] + "\n" + crypto_block + content[insertion_pos:]
        client_path.write_text(content)
        print("✅ client.py-তে Cryptolyt টুল fallback দিয়ে যোগ করা হয়েছে।")
    else:
        print("❌ কোনো insertion point পাওয়া যায়নি।")
