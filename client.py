import asyncio
import websockets
import json
import subprocess
import hmac
import hashlib
import os

# ⚠️ এখানে আপনার Render এর WebSocket URL বসান (wss://your-bot.onrender.com)
CLOUD_WS_URL = os.getenv("CLOUD_WS_URL", "wss://your-render-url.onrender.com")
# ⚠️ Render এর Env Var এ দেওয়া AGENT_SHARED_SECRET বসান
SHARED_SECRET = os.getenv("AGENT_SHARED_SECRET", "your-secret-here")

MAX_RECONNECT_ATTEMPTS = 10
INITIAL_BACKOFF = 1
MAX_BACKOFF = 60

def run_termux_command(cmd: list) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() or result.stderr.strip() or "(done)"
    except FileNotFoundError:
        return "ERROR: termux-api package missing. Run: pkg install termux-api"
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out"

def execute_tool(tool_name: str, args: dict) -> str:
    if tool_name == "battery_status":
        return run_termux_command(["termux-battery-status"])
    elif tool_name == "notify":
        return run_termux_command(["termux-notification", "--title", args.get("title", "Nova"), "--content", args.get("text", "")])
    elif tool_name == "speak":
        return run_termux_command(["termux-tts-speak", args.get("text", "")])
    elif tool_name == "get_clipboard":
        return run_termux_command(["termux-clipboard-get"])
    elif tool_name == "set_clipboard":
        return run_termux_command(["termux-clipboard-set", args.get("text", "")])
    elif tool_name == "get_location":
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
        return run_termux_command(["termux-camera-photo", "-c", "0", args.get("filename", "photo.jpg")])
    else:
        return f"ERROR: Unknown tool {tool_name}"

async def connect_to_cloud():
    attempt = 0
    backoff = INITIAL_BACKOFF
    
    while True:
        try:
            print(f"Connecting to {CLOUD_WS_URL} (Attempt {attempt + 1})...")
            
            # 🔐 সিকিউর হ্যান্ডশেক: হেডারে সিক্রেট পাঠানো
            async with websockets.connect(
                CLOUD_WS_URL,
                extra_headers={"X-Auth-Token": SHARED_SECRET},
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            ) as websocket:
                print("✅ Connected to cloud server.")
                attempt = 0
                backoff = INITIAL_BACKOFF
                
                async for message in websocket:
                    data = json.loads(message)
                    if data.get("type") == "execute_tool":
                        tool_name = data.get("tool")
                        args = data.get("args", {})
                        
                        # HMAC সিগনেচার ভেরিফাই
                        expected_sig = hmac.new(SHARED_SECRET.encode(), tool_name.encode(), hashlib.sha256).hexdigest()
                        if data.get("signature") != expected_sig:
                            print("⚠️ WARNING: Invalid signature. Ignoring command.")
                            continue
                        
                        print(f"Executing: {tool_name}")
                        result = execute_tool(tool_name, args)
                        
                        await websocket.send(json.dumps({
                            "type": "tool_result",
                            "tool": tool_name,
                            "result": result
                        }))
                        
        except (websockets.exceptions.ConnectionClosed, 
                websockets.exceptions.WebSocketException,
                OSError) as e:
            print(f"❌ Connection error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        attempt += 1
        if attempt > MAX_RECONNECT_ATTEMPTS:
            print("Max reconnect attempts reached. Exiting.")
            break
        
        wait_time = min(backoff, MAX_BACKOFF)
        print(f"Reconnecting in {wait_time} seconds...")
        await asyncio.sleep(wait_time)
        backoff *= 2

if __name__ == "__main__":
    asyncio.run(connect_to_cloud())
