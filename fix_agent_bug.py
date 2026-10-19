import re
from pathlib import Path

agent_path = Path("agent.py")
content = agent_path.read_text()

# ভাঙা Groq API Key সেভিং ব্লকটি খুঁজে বের করা
pattern = r'if not gkey:\s*gkey = getpass\.getpass\(.*?\)\.strip\(\)\s*with open\(ENV_FILE, "a"\) as f:\s*f\.write\(".*?\)'

replacement = '''if not gkey:
            gkey = getpass.getpass("Enter your GROQ_API_KEY (saved to ~/agi/.env): ").strip()
            with open(ENV_FILE, "a") as f:
                f.write("\\nGROQ_API_KEY=" + gkey + "\\n")
            os.chmod(ENV_FILE, 0o600)'''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)
agent_path.write_text(content)
print("✅ agent.py এর ২৪৬ নম্বর লাইনের সিনট্যাক্স এরর ঠিক করা হয়েছে।")
