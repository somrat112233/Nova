from pathlib import Path
import re

# --- ১. agent.py ফিক্স (Groq বেকএন্ড চেক এবং Neon DB সেফটি) ---
agent_path = Path("agent.py")
content = agent_path.read_text()

# ১.১. ensure_key ফাংশনটি ঠিক করা যাতে Groq থাকলে Anthropic কী না চায়
old_ensure_key = r'def ensure_key\(\):\s*if os\.getenv\("AGENT_BACKEND"\) in \("local", "gemini"\) or os\.getenv\("ANTHROPIC_API_KEY"\):\s*return'
new_ensure_key = '''def ensure_key():
    backend = os.getenv("AGENT_BACKEND", "anthropic")
    if backend in ("local", "gemini", "groq") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GROQ_API_KEY"):
        return'''
content = re.sub(old_ensure_key, new_ensure_key, content)

# ১.২. NeonMemoryStore ক্লাসে URL চেক করা
old_neon_init = '''    def __init__(self, connection_string):
        self.conn_string = connection_string
        self._init_table()'''
new_neon_init = '''    def __init__(self, connection_string):
        self.conn_string = connection_string
        if not self.conn_string:
            print("WARNING: NEON_DATABASE_URL is not set. Memory will not be persistent.")
            self.enabled = False
            return
        self.enabled = True
        self._init_table()'''
content = content.replace(old_neon_init, new_neon_init)

# ১.৩. _init_table এবং load/save_history ফাংশনে self.enabled চেক করা
content = content.replace('    def _init_table(self):\n        try:', '    def _init_table(self):\n        if not self.enabled: return\n        try:')
content = content.replace('    def load_history(self, session_id: str):\n        try:', '    def load_history(self, session_id: str):\n        if not self.enabled: return []\n        try:')
content = content.replace('    def save_history(self, session_id: str, history: list):\n        try:', '    def save_history(self, session_id: str, history: list):\n        if not self.enabled: return\n        try:')

agent_path.write_text(content)
print("✅ agent.py সফলভাবে প্যাচ করা হয়েছে।")

# --- ২. bot.py ফিক্স (Groq বেকএন্ড চেক) ---
bot_path = Path("bot.py")
if bot_path.exists():
    content = bot_path.read_text()
    # build_llm ফাংশনে agent.ensure_key() কল করার আগে চেক করা
    old_build = '    else:\n        agent.ensure_key()\n        llm = agent.ChatAnthropic(model=agent.MODEL, max_tokens=2048)'
    new_build = '''    else:
        backend = os.getenv("AGENT_BACKEND", "anthropic")
        if backend != "groq":
            agent.ensure_key()
        llm = agent.ChatAnthropic(model=agent.MODEL, max_tokens=2048)'''
    content = content.replace(old_build, new_build)
    bot_path.write_text(content)
    print("✅ bot.py সফলভাবে প্যাচ করা হয়েছে।")
