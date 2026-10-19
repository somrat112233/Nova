from pathlib import Path

agent_path = Path.home() / "agi" / "agent.py"
content = agent_path.read_text()

# ১. টুলের ডকস্ট্রিং আরও স্পষ্ট করা
old_desc = '''@tool
def cryptologyt_status() -> str:
    """Check if the Cryptologyt trading bot is currently running on the phone."""
    return "Command sent to phone."'''

new_desc = '''@tool
def cryptologyt_status() -> str:
    """MUST USE THIS TOOL when the user asks about 'cryptologyt', 'cryptolyt', 'crypto bot', or trading bot status. It checks if the bot is running on the phone."""
    return "Command sent to phone."'''

content = content.replace(old_desc, new_desc)

# ২. সিস্টেম প্রম্পটে নির্দেশনা যোগ করা
old_prompt = 'cryptologyt_status, cryptologyt_start, cryptologyt_stop,'
new_prompt = 'cryptologyt_status (use this for ANY question about cryptologyt), cryptologyt_start, cryptologyt_stop,'

content = content.replace(old_prompt, new_prompt)

agent_path.write_text(content)
print("✅ agent.py-তে cryptologyt টুলের বর্ণনা এবং সিস্টেম প্রম্পট আপডেট করা হয়েছে।")
