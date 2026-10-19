import re
from pathlib import Path

# --- Fix agent.py ---
agent_path = Path("agent.py")
if agent_path.exists():
    content = agent_path.read_text()
    # ভাঙা Groq ব্লকটি খুঁজে বের করা এবং সঠিক কোড দিয়ে রিপ্লেস করা
    pattern = r'if os\.getenv\("AGENT_BACKEND"\) == "groq":.*?api_key=gkey, max_tokens=2048\)'
    
    replacement = '''if os.getenv("AGENT_BACKEND") == "groq":
        from langchain_openai import ChatOpenAI
        gkey = os.getenv("GROQ_API_KEY")
        if not gkey:
            gkey = getpass.getpass("Enter your GROQ_API_KEY (saved to ~/agi/.env): ").strip()
            with open(ENV_FILE, "a") as f:
                f.write("\\nGROQ_API_KEY=" + gkey + "\\n")
            os.chmod(ENV_FILE, 0o600)
        llm = ChatOpenAI(model=os.getenv("AGENT_GROQ_MODEL", "llama-3.3-70b-versatile"),
                         base_url="https://api.groq.com/openai/v1",
                         api_key=gkey, max_tokens=2048)'''
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    agent_path.write_text(content)
    print("✅ agent.py এর সিনট্যাক্স এরর ঠিক করা হয়েছে।")

# --- Fix bot.py ---
bot_path = Path("bot.py")
if bot_path.exists():
    content = bot_path.read_text()
    pattern = r'elif backend == "groq":.*?api_key=key, max_tokens=2048\)'
    
    replacement = '''elif backend == "groq":
        from langchain_openai import ChatOpenAI
        key = os.getenv("GROQ_API_KEY")
        if not key:
            sys.exit("GROQ_API_KEY not found. Please add it to Render Environment Variables.")
        llm = ChatOpenAI(model=os.getenv("AGENT_GROQ_MODEL", "llama-3.3-70b-versatile"),
                         base_url="https://api.groq.com/openai/v1",
                         api_key=key, max_tokens=2048)'''
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    bot_path.write_text(content)
    print("✅ bot.py আপডেট করা হয়েছে।")
