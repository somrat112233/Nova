import asyncio
import websockets
import json
import hmac
import hashlib
import os

WS_HOST = "0.0.0.0"
WS_PORT = int(os.getenv("PORT", 10000))
SHARED_SECRET = os.getenv("AGENT_SHARED_SECRET", "your-secret-here")
connected_clients = set()

async def handle_client(websocket):
    # 🔐 হেডার থেকে টোকেন ভেরিফাই করা
    token = websocket.request_headers.get("X-Auth-Token")
    if token != SHARED_SECRET:
        print("❌ Unauthorized connection attempt.")
        await websocket.close(code=1008, reason="Unauthorized")
        return

    connected_clients.add(websocket)
    print("✅ Phone client connected.")
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "tool_result":
                print(f"[Phone Result] {data.get('tool')}: {data.get('result')}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        print("❌ Phone client disconnected.")

async def send_command(tool_name: str, args: dict = None) -> str:
    if not connected_clients:
        return "ERROR: Phone client not connected."
    
    command = {
        "type": "execute_tool",
        "tool": tool_name,
        "args": args or {},
        "signature": hmac.new(SHARED_SECRET.encode(), tool_name.encode(), hashlib.sha256).hexdigest()
    }
    
    for ws in connected_clients:
        await ws.send(json.dumps(command))
    return "Command sent to phone."

async def start_ws_server():
    async with websockets.serve(handle_client, WS_HOST, WS_PORT):
        print(f"WebSocket server started on port {WS_PORT}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(start_ws_server())
