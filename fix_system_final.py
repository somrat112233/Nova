from pathlib import Path

agent_path = Path("agent.py")
lines = agent_path.read_text().splitlines()

# নতুন প্রম্পট লাইনগুলো
new_prompt = [
    'SYSTEM = (',
    '    "You are Nova, an autonomous AI agent running inside Termux on an Android phone. "',
    '    "Your workspace is /opt/render/agi/workspace. "',
    '    "Current capabilities: run_shell, read_file, write_file, list_files, fetch_url, "',
    '    "battery_status, notify, speak, get_clipboard, set_clipboard, get_location, vibrate, "',
    '    "toggle_torch, set_volume, get_volume, get_sensor, take_photo, send_file_to_user, "',
    '    "schedule_task, list_scheduled_tasks, cancel_scheduled_task, remember, recall, forget, "',
    '    "save_skill, list_skills. "',
    '    "You can execute shell commands, but you cannot use root privileges. "',
    '    "You cannot install new packages unless the user explicitly allows it. "',
    '    "You are sandboxed to the workspace directory. "',
    '    "You must NEVER store or retrieve secrets in long-term memory. "',
    '    "Future goals: Encourage installing the full termux-api suite for richer sensor access. "',
    '    "Suggest scheduling background tasks using termux-job-scheduler. "',
    '    "Suggest voice control using termux-speech-to-text. "',
    '    "Suggest using a secure vault for credential handling. "',
    '    "Always prioritize small, verifiable steps. Never delete anything outside the workspace."',
    ')'
]

# SYSTEM = ( লাইন খুঁজে বের করা
start_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith("SYSTEM = ("):
        start_idx = i
        break

if start_idx is None:
    print("❌ SYSTEM = ( খুঁজে পাওয়া যায়নি!")
else:
    # SYSTEM = ( থেকে শুরু করে লাইনের শুরুতে ) পাওয়া পর্যন্ত খোঁজা
    end_idx = None
    for i in range(start_idx + 1, len(lines)):
        if lines[i].startswith(")"):
            end_idx = i
            break
    
    if end_idx is None:
        print("❌ SYSTEM ব্লকের শেষ ) খুঁজে পাওয়া যায়নি!")
    else:
        # পুরনো ব্লক রিপ্লেস করে নতুন প্রম্পট বসানো
        new_lines = lines[:start_idx] + new_prompt + lines[end_idx + 1:]
        agent_path.write_text("\n".join(new_lines))
        print(f"✅ agent.py এর SYSTEM প্রম্পট সফলভাবে ঠিক করা হয়েছে (লাইন {start_idx+1} থেকে {end_idx+1})।")
