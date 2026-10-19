from pathlib import Path
import re

# --- ১. bot.py ফিক্স (শুধু Groq ব্যবহার করবে) ---
bot_path = Path("bot.py")
if bot_path.exists():
    content = bot_path.read_text()
    
    # build_llm ফাংশনের পুরো বডি রিপ্লেস করে শুধু Groq রাখা
    pattern = r'def build_llm\(\):.*?return llm\.bind_tools\(list\(agent\.TOOLS\.values\(\)\)\)'
    replacement = '''def build_llm():
    from langchain_openai import ChatOpenAI
    key = os.getenv("GROQ_API_KEY")
    if not key:
        sys.exit("GROQ_API_KEY not found. Please add it to Render Environment Variables.")
    llm = ChatOpenAI(model=os.getenv("AGENT_GROQ_MODEL", "llama-3.3-70b-versatile"),
                     base_url="https://api.groq.com/openai/v1",
                     api_key=key, max_tokens=2048)
    return llm.bind_tools(list(agent.TOOLS.values()))'''
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    bot_path.write_text(content)
    print("✅ bot.py আপডেট হয়েছে। এখন শুধু Groq ব্যবহার হবে।")

# --- ২. agent.py ফিক্স (Anthropic চাওয়া বন্ধ করা) ---
agent_path = Path("agent.py")
if agent_path.exists():
    content = agent_path.read_text()
    
    # ensure_key() ফাংশনটি বাইপাস করা (যাতে Anthropic কী না চায়)
    pattern = r'def ensure_key\(\):.*?(?=def text_of\(msg\):)'
    replacement = '''def ensure_key():
    # Groq ব্যবহার করছি, তাই Anthropic কী চাওয়ার দরকার নেই
    pass

'''
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # main() ফাংশন থেকে ensure_key() কল সরিয়ে ফেলা
    content = content.replace("    ensure_key()\n", "")
    
    agent_path.write_text(content)
    print("✅ agent.py আপডেট হয়েছে। Anthropic এর প্রম্পট সরানো হয়েছে।")
