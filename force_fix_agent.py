from pathlib import Path

agent_path = Path("agent.py")
lines = agent_path.read_text().splitlines()
new_lines = []
i = 0

while i < len(lines):
    line = lines[i]
    # Groq API Key সেভ করার সময় ভাঙা f.write(" লাইনটি খোঁজা
    if 'f.write("' in line and 'GROQ_API_KEY' not in line:
        # সঠিক লাইনটি বসানো
        new_lines.append('                f.write("\\nGROQ_API_KEY=" + gkey + "\\n")')
        # ভাঙা অংশের বাকি লাইনগুলো স্কিপ করা (যেমন খালি লাইন বা ")" )
        i += 1
        while i < len(lines) and '")' not in lines[i] and not lines[i].strip().endswith(')'):
            i += 1
        i += 1 # শেষ কোটেশন লাইনটি স্কিপ করা
        continue
    new_lines.append(line)
    i += 1

agent_path.write_text("\n".join(new_lines))
print("✅ agent.py এর ২৪৬ নম্বর লাইনের সিনট্যাক্স এরর নিখুঁতভাবে ঠিক করা হয়েছে।")
