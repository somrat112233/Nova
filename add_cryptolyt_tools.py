from pathlib import Path

# ============================================================
# PART 1: client.py-তে Cryptolyt কমান্ড যোগ করা
# ============================================================
client_path = Path.home() / "agi" / "client.py"
content = client_path.read_text()

crypto_tools = '''
    # ================== Cryptolyt Tools ==================
    elif tool_name == "cryptolyt_status":
        import sys
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        return str(cm.cryptolyt_status())
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
        lines = args.get("lines", 50)
        log_type = args.get("log_type", "main")
        return cm.cryptolyt_logs(lines, log_type)
    elif tool_name == "cryptolyt_signals":
        import sys
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        import json as _json
        return _json.dumps(cm.cryptolyt_parse_signals(args.get("lines", 500)), indent=2, ensure_ascii=False)
    elif tool_name == "cryptolyt_health":
        import sys
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        import json as _json
        return _json.dumps(cm.cryptolyt_health_check(), indent=2)
    elif tool_name == "cryptolyt_recent_trades":
        import sys
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        return cm.cryptolyt_recent_trades(args.get("lines", 200))
    elif tool_name == "cryptolyt_summary":
        import sys
        sys.path.insert(0, os.path.expanduser("~/agi"))
        import cryptolyt_manager as cm
        import json as _json
        return _json.dumps(cm.cryptolyt_summary(), indent=2, ensure_ascii=False)
'''

# Find where to insert - after the last elif in execute_tool
insertion_point = '''    elif tool_name == "termux_storage_info":
        try:
            import shutil
            total, used, free = shutil.disk_usage(os.path.expanduser("~"))
            return f"Storage:\\n  Total: {total // (1024**3)} GB\\n  Used: {used // (1024**3)} GB\\n  Free: {free // (1024**3)} GB"
        except Exception as e:
            return f"Error: {e}"'''

if insertion_point in content and "cryptolyt_status" not in content:
    content = content.replace(insertion_point, insertion_point + "\n" + crypto_tools)
    client_path.write_text(content)
    print("✅ client.py-তে Cryptolyt টুল যোগ করা হয়েছে।")
elif "cryptolyt_status" in content:
    print("ℹ️ Cryptolyt টুল আগেই যোগ করা আছে।")
else:
    print("⚠️ Insertion point পাওয়া যায়নি। manual check দরকার।")

# Allowlist-এ Cryptolyt টুল যোগ করা
content = client_path.read_text()
crypto_allowlist = '"cryptolyt_status", "cryptolyt_start", "cryptolyt_stop",\n    "cryptolyt_logs", "cryptolyt_signals", "cryptolyt_health",\n    "cryptolyt_recent_trades", "cryptolyt_summary"'

if "cryptolyt_status" not in content.split("ALLOWED_TOOLS")[1].split("}")[0]:
    content = content.replace(
        '"termux_scan_all", "termux_storage_info"\n}',
        '"termux_scan_all", "termux_storage_info",\n    ' + crypto_allowlist + '\n}'
    )
    client_path.write_text(content)
    print("✅ client.py-তে Allowlist আপডেট হয়েছে।")

# ============================================================
# PART 2: agent.py-তে Cryptolyt টুল ডেফিনিশন যোগ করা
# ============================================================
agent_path = Path.home() / "agi" / "agent.py"
content = agent_path.read_text()

crypto_agent_tools = '''
# ==================== Cryptolyt Tools ====================
@tool
def cryptolyt_status() -> str:
    """Check if the Cryptolyt trading bot is currently running on the phone."""
    return "Command sent to phone."

@tool
def cryptolyt_start() -> str:
    """Start the Cryptolyt trading bot on the phone."""
    return "Command sent to phone."

@tool
def cryptolyt_stop() -> str:
    """Stop the Cryptolyt trading bot on the phone."""
    return "Command sent to phone."

@tool
def cryptolyt_logs(lines: int = 50, log_type: str = "main") -> str:
    """Get recent logs from Cryptolyt. log_type can be 'main' or 'live'."""
    return "Command sent to phone."

@tool
def cryptolyt_signals(lines: int = 500) -> str:
    """Parse recent BUY/SELL/PROFIT/LOSS signals from Cryptolyt's log."""
    return "Command sent to phone."

@tool
def cryptolyt_health() -> str:
    """Check Cryptolyt's health (errors, warnings, last log time)."""
    return "Command sent to phone."

@tool
def cryptolyt_recent_trades(lines: int = 200) -> str:
    """Get recent trades/positions from Cryptolyt's log."""
    return "Command sent to phone."

@tool
def cryptolyt_summary() -> str:
    """Generate a complete Cryptolyt summary (status + signals + report)."""
    return "Command sent to phone."
'''

if "@tool\ndef cryptolyt_status" not in content:
    content = content.replace(
        '@tool\ndef send_file_to_user',
        crypto_agent_tools + '\n@tool\ndef send_file_to_user'
    )
    print("✅ agent.py-তে Cryptolyt টুল ডেফিনিশন যোগ করা হয়েছে।")

# TOOLS ডিকশনারি আপডেট
content = content.replace(
    'termux_delete_file, termux_search_files,\n    termux_scan_all, termux_storage_info\n]}',
    'termux_delete_file, termux_search_files,\n    termux_scan_all, termux_storage_info,\n    cryptolyt_status, cryptolyt_start, cryptolyt_stop,\n    cryptolyt_logs, cryptolyt_signals, cryptolyt_health,\n    cryptolyt_recent_trades, cryptolyt_summary\n]}'
)

# SYSTEM প্রম্পট আপডেট
content = content.replace(
    'termux_list_files, termux_read_file, termux_write_file, termux_delete_file, termux_search_files, termux_scan_all, termux_storage_info. ',
    'termux_list_files, termux_read_file, termux_write_file, termux_delete_file, termux_search_files, termux_scan_all, termux_storage_info, cryptolyt_status, cryptolyt_start, cryptolyt_stop, cryptolyt_logs, cryptolyt_signals, cryptolyt_health, cryptolyt_recent_trades, cryptolyt_summary. '
)

agent_path.write_text(content)
print("✅ agent.py আপডেট সম্পন্ন।")
