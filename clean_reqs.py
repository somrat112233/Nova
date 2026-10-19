from pathlib import Path

req_path = Path("requirements.txt")
lines = req_path.read_text().splitlines()
new_lines = []

# অপ্রয়োজনীয় ভারী প্যাকেজের তালিকা
heavy_packages = ["pandas", "matplotlib", "scipy", "numpy", "contourpy", "fonttools", "kiwisolver", "mplfinance", "pyparsing"]

for line in lines:
    pkg_name = line.split("==")[0].split(">=")[0].strip().lower()
    if pkg_name not in heavy_packages and "android" not in line.lower():
        new_lines.append(line)

req_path.write_text("\n".join(new_lines) + "\n")
print("✅ requirements.txt থেকে অপ্রয়োজনীয় ভারী প্যাকেজ মুছে ফেলা হয়েছে।")
print("--- বর্তমান requirements.txt ---")
print("\n".join(new_lines))
