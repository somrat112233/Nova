from pathlib import Path

agent_path = Path("agent.py")
content = agent_path.read_text()

# ১. ইমপোর্ট সেকশনে BeautifulSoup যোগ করা
if "from bs4 import BeautifulSoup" not in content:
    content = content.replace("import requests", "import requests\nfrom bs4 import BeautifulSoup")

# ২. পুরনো fetch_url ফাংশনটি খুঁজে বের করে নতুনটি বসানো
old_fetch = '''@tool
def fetch_url(url: str) -> str:
    """Fetch a web page or API URL and return the first 6000 characters of text."""
    r = requests.get(url, timeout=20, headers={"User-Agent": "termux-agent"})
    return r.text[:6000]'''

new_fetch = '''@tool
def fetch_url(url: str) -> str:
    """Fetch a web page or API URL, clean the HTML using BeautifulSoup, and return the first 6000 characters of readable text."""
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (Android 14; Mobile)"})
        soup = BeautifulSoup(r.text, "html.parser")
        # স্ক্রিপ্ট এবং স্টাইল ট্যাগগুলো মুছে ফেলা
        for script in soup(["script", "style"]):
            script.extract()
        # পরিষ্কার টেক্সট বের করা
        text = soup.get_text(separator="\\n")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\\n".join(chunk for chunk in chunks if chunk)
        return text[:6000] or "No readable text found."
    except Exception as e:
        return f"Error fetching URL: {e}"'''

if old_fetch in content:
    content = content.replace(old_fetch, new_fetch)
    agent_path.write_text(content)
    print("✅ agent.py-তে BeautifulSoup সফলভাবে যুক্ত করা হয়েছে।")
else:
    print("❌ পুরনো fetch_url ফাংশনটি খুঁজে পাওয়া যায়নি।")
    # Fallback: if the exact string didn't match, just append import
    if "from bs4 import BeautifulSoup" not in content:
        content = content.replace("import requests", "import requests\nfrom bs4 import BeautifulSoup")
        agent_path.write_text(content)
        print("✅ BeautifulSoup ইমপোর্ট যুক্ত করা হয়েছে (কিন্তু fetch_url আপডেট হয়নি)।")
