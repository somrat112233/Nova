import re
from pathlib import Path

# --- Fix agent.py ---
agent_path = Path("agent.py")
if agent_path.exists():
    content = agent_path.read_text()
    
    # ১. প্রয়োজনীয় ইমপোর্ট যোগ করা
    if "import psycopg2" not in content:
        content = content.replace("import os, sys, json, subprocess, getpass", "import os, sys, json, subprocess, getpass\nimport psycopg2\nfrom psycopg2.extras import Json")
    
    # ২. NeonMemoryStore ক্লাস এবং load/save ফাংশন রিপ্লেস করা
    neon_class = '''
class NeonMemoryStore:
    def __init__(self, connection_string):
        self.conn_string = connection_string
        self._init_table()

    def _init_table(self):
        try:
            with psycopg2.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS chat_history (
                            id SERIAL PRIMARY KEY,
                            session_id TEXT NOT NULL,
                            message_json JSONB NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        );
                    """)
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON chat_history(session_id);")
                    conn.commit()
        except Exception as e:
            print(f"Neon DB Init Error: {e}")

    def load_history(self, session_id: str):
        try:
            with psycopg2.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT message_json FROM chat_history WHERE session_id = %s ORDER BY id ASC", (session_id,))
                    rows = cur.fetchall()
                    if not rows: return []
                    from langchain_core.messages import messages_from_dict
                    return messages_from_dict([row[0] for row in rows])
        except Exception as e:
            print(f"Error loading history: {e}")
            return []

    def save_history(self, session_id: str, history: list):
        try:
            from langchain_core.messages import messages_to_dict
            with psycopg2.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM chat_history WHERE session_id = %s", (session_id,))
                    for msg in history:
                        msg_dict = messages_to_dict([msg])[0]
                        cur.execute("INSERT INTO chat_history (session_id, message_json) VALUES (%s, %s)", (session_id, Json(msg_dict)))
                    conn.commit()
        except Exception as e:
            print(f"Error saving history: {e}")

memory_store = NeonMemoryStore(os.getenv("NEON_DATABASE_URL"))

def load_history():
    return memory_store.load_history("default_session")

def save_history(history):
    memory_store.save_history("default_session", history)
'''
    # পুরনো load_history এবং save_history ফাংশন রিপ্লেস করা
    content = re.sub(r'def load_history\(\):.*?def save_history\(history\):.*?MEMORY_FILE\.write_text\(json\.dumps\(messages_to_dict\(history\)\)\)', neon_class, content, flags=re.DOTALL)
    agent_path.write_text(content)
    print("✅ agent.py আপডেট হয়েছে (Neon Memory Layer যুক্ত হয়েছে)।")

# --- Fix bot.py ---
bot_path = Path("bot.py")
if bot_path.exists():
    content = bot_path.read_text()
    
    # WebSocket সার্ভার চালু করা (থ্রেডে)
    if "import ws_server" not in content:
        content = content.replace("import agent", "import agent\nimport ws_server\nimport asyncio")
        if "if __name__ == \"__main__\":" in content:
            content = content.replace("if __name__ == \"__main__\":", "if __name__ == \"__main__\":\n    threading.Thread(target=lambda: asyncio.run(ws_server.start_ws_server()), daemon=True).start()")
        else:
            # যদি __main__ ব্লক না থাকে, তবে স্ক্রিপ্টের একদম শেষে যোগ করা
            content += "\n\nimport threading\nthreading.Thread(target=lambda: asyncio.run(ws_server.start_ws_server()), daemon=True).start()\n"
    
    bot_path.write_text(content)
    print("✅ bot.py আপডেট হয়েছে (WebSocket Server যুক্ত হয়েছে)।")
