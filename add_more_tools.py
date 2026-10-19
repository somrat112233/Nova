from pathlib import Path
import re

# --- ১. client.py আপডেট করা ---
client_path = Path("client.py")
content = client_path.read_text()

# execute_tool ফাংশনে নতুন কমান্ড যোগ করা
old_execute = '    elif tool_name == "get_location":\n        return run_termux_command(["termux-location", "-p", "network"])'
new_execute = '''    elif tool_name == "get_location":
        return run_termux_command(["termux-location", "-p", "network"])
    elif tool_name == "vibrate":
        duration = str(args.get("duration_ms", 1000))
        return run_termux_command(["termux-vibrate", "-d", duration])
    elif tool_name == "toggle_torch":
        state = args.get("state", "on")
        return run_termux_command(["termux-torch", state])
    elif tool_name == "set_volume":
        stream = args.get("stream", "music")
        vol = str(args.get("volume", 50))
        return run_termux_command(["termux-volume", stream, vol])
    elif tool_name == "get_volume":
        return run_termux_command(["termux-volume"])
    elif tool_name == "get_sensor":
        sensor = args.get("sensor_name", "accelerometer")
        return run_termux_command(["termux-sensor", "-s", sensor, "-n", "1"])
    elif tool_name == "take_photo":
        return run_termux_command(["termux-camera-photo", "-c", "0", args.get("filename", "photo.jpg")])'''

content = content.replace(old_execute, new_execute)
client_path.write_text(content)
print("✅ client.py-তে নতুন টুল যুক্ত হয়েছে।")

# --- ২. agent.py আপডেট করা ---
agent_path = Path("agent.py")
content = agent_path.read_text()

# নতুন টুলের ডেফিনিশন
new_tools_def = '''
@tool
def vibrate(duration_ms: int = 1000) -> str:
    """Vibrate the phone for a specified duration in milliseconds (default 1000)."""
    return "Command sent to phone."

@tool
def toggle_torch(state: str = "on") -> str:
    """Turn the phone torch on or off. State should be 'on' or 'off'."""
    return "Command sent to phone."

@tool
def set_volume(stream: str = "music", volume: int = 50) -> str:
    """Set the volume for a specific stream (music, ring, alarm, notification, call). Volume is 0-100."""
    return "Command sent to phone."

@tool
def get_volume() -> str:
    """Get the current volume levels of the phone (music, ring, alarm, etc.)."""
    return "Command sent to phone."

@tool
def get_sensor(sensor_name: str = "accelerometer") -> str:
    """Get a single reading from a phone sensor (e.g., accelerometer, light, proximity, gyroscope)."""
    return "Command sent to phone."

@tool
def take_photo(filename: str = "photo.jpg") -> str:
    """Take a photo using the phone's rear camera and save it to the workspace (filename)."""
    return "Command sent to phone."
'''

# TOOLS ডিকশনারি আপডেট করা
old_tools = 'TOOLS = {t.name: t for t in [run_shell, read_file, write_file, list_files, fetch_url,\n                             battery_status, notify, speak, get_clipboard,\n                             set_clipboard, get_location]}'
new_tools = 'TOOLS = {t.name: t for t in [run_shell, read_file, write_file, list_files, fetch_url,\n                             battery_status, notify, speak, get_clipboard,\n                             set_clipboard, get_location, vibrate, toggle_torch,\n                             set_volume, get_volume, get_sensor, take_photo]}'

# নতুন টুলের ডেফিনিশন get_location ফাংশনের পরে যোগ করা
if "@tool\ndef vibrate" not in content:
    content = content.replace('@tool\ndef get_location() -> str:\n    """Get the phone\'s current GPS/network location as JSON."""\n    return _termux(["termux-location", "-p", "network"])', 
                            '@tool\ndef get_location() -> str:\n    """Get the phone\'s current GPS/network location as JSON."""\n    return _termux(["termux-location", "-p", "network"])' + new_tools_def)

if old_tools in content:
    content = content.replace(old_tools, new_tools)
else:
    # যদি হুবহু না মেলে, তবে regex দিয়ে খোঁজা
    content = re.sub(r'TOOLS = \{t\.name: t for t in \[.*?\]\}', new_tools, content, flags=re.DOTALL)

agent_path.write_text(content)
print("✅ agent.py-তে নতুন টুল যুক্ত হয়েছে।")
