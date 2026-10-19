import re
from pathlib import Path

# --- Fix agent.py ---
agent_path = Path("agent.py")
if agent_path.exists():
    content = agent_path.read_text()
    # পুরনো ChatOpenAI ব্লকটি খুঁজে বের করা
    pattern = r'    if os\.getenv\("AGENT_BACKEND"\) == "gemini":\s+from langchain_openai import ChatOpenAI.*?api_key=gkey, max_tokens=2048\)'
    replacement = """    if os.getenv("AGENT_BACKEND") == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        gkey = os.getenv("GEMINI_API_KEY")
        if not gkey:
            gkey = getpass.getpass("Enter your GEMINI_API_KEY (saved to ~/agi/.env): ").strip()
            with open(ENV_FILE, "a") as f:
                f.write(f"\\nGEMINI_API_KEY={gkey}\\n")
            os.chmod(ENV_FILE, 0o600)
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=gkey)"""
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # অপ্রয়োজনীয় gemini_fix ইমপোর্টটি মুছে ফেলা
    content = content.replace('try:\n    import gemini_fix\nexcept Exception as _e:\n    print("gemini_fix not loaded:", _e)\n', '')
    agent_path.write_text(content)
    print("✅ agent.py আপডেট হয়েছে।")

# --- Fix bot.py ---
bot_path = Path("bot.py")
if bot_path.exists():
    content = bot_path.read_text()
    # পুরনো ChatOpenAI ব্লকটি খুঁজে বের করা
    pattern = r'    elif backend == "gemini":\s+from langchain_openai import ChatOpenAI.*?api_key=key, max_tokens=2048\)'
    replacement = """    elif backend == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            sys.exit("GEMINI_API_KEY not found. Please add it to Render Environment Variables.")
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=key)"""
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    bot_path.write_text(content)
    print("✅ bot.py আপডেট হয়েছে।")
