import re
from pathlib import Path

# --- Fix agent.py ---
agent_path = Path("agent.py")
if agent_path.exists():
    content = agent_path.read_text()
    # পুরনো Gemini ব্লকটি খুঁজে বের করা
    pattern = r'if os\.getenv\("AGENT_BACKEND"\) == "gemini":.*?llm = ChatGoogleGenerativeAI\(model="gemini-1\.5-flash-latest", google_api_key=gkey\)'
    replacement = """if os.getenv("AGENT_BACKEND") == "groq":
        from langchain_openai import ChatOpenAI
        gkey = os.getenv("GROQ_API_KEY")
        if not gkey:
            gkey = getpass.getpass("Enter your GROQ_API_KEY (saved to ~/agi/.env): ").strip()
            with open(ENV_FILE, "a") as f:
                f.write(f"\\nGROQ_API_KEY={gkey}\\n")
            os.chmod(ENV_FILE, 0o600)
        llm = ChatOpenAI(model=os.getenv("AGENT_GROQ_MODEL", "llama-3.3-70b-versatile"),
                         base_url="https://api.groq.com/openai/v1",
                         api_key=gkey, max_tokens=2048)"""
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    agent_path.write_text(content)
    print("✅ agent.py আপডেট হয়েছে।")

# --- Fix bot.py ---
bot_path = Path("bot.py")
if bot_path.exists():
    content = bot_path.read_text()
    # পুরনো Gemini ব্লকটি খুঁজে বের করা
    pattern = r'elif backend == "gemini":.*?llm = ChatGoogleGenerativeAI\(model="gemini-1\.5-flash-latest", google_api_key=key\)'
    replacement = """elif backend == "groq":
        from langchain_openai import ChatOpenAI
        key = os.getenv("GROQ_API_KEY")
        if not key:
            sys.exit("GROQ_API_KEY not found. Please add it to Render Environment Variables.")
        llm = ChatOpenAI(model=os.getenv("AGENT_GROQ_MODEL", "llama-3.3-70b-versatile"),
                         base_url="https://api.groq.com/openai/v1",
                         api_key=key, max_tokens=2048)"""
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    bot_path.write_text(content)
    print("✅ bot.py আপডেট হয়েছে।")
