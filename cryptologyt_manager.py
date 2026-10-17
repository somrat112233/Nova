"""
Cryptologyt Manager v3.0 - Nova থেকে Cryptologyt Trading Bot নিয়ন্ত্রণ
"""
import os
import re
import json
import time
import subprocess
import signal
from pathlib import Path
from datetime import datetime

# ============ Configuration ============
CRYPTOLYT_DIR = os.path.expanduser("~/cryptologyt")
AGI_DIR = os.path.expanduser("~/agi")
LOG_DIR = os.path.join(CRYPTOLYT_DIR, "logs")
NOVA_LOG_DIR = os.path.join(AGI_DIR, "logs")
REPORT_DIR = os.path.join(AGI_DIR, "reports")

CRYPTOLYT_LOG = os.path.join(LOG_DIR, "cryptologyt.log")
CRYPTOLYT_LIVE_LOG = os.path.join(LOG_DIR, "live.log")
PID_FILE = os.path.join(AGI_DIR, ".cryptologyt.pid")
SUMMARY_FILE = os.path.join(REPORT_DIR, "cryptologyt_summary.json")

# Entry command (Termux-friendly polling mode)
CRYPTOLYT_CMD = ["python", os.path.join(CRYPTOLYT_DIR, "main.py")]

os.makedirs(NOVA_LOG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)


def _read_pid():
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return None


def _is_running():
    """Cryptologyt প্রসেস চলছে কিনা চেক"""
    pid = _read_pid()
    if pid:
        try:
            os.kill(pid, 0)
            return True, pid
        except ProcessLookupError:
            os.remove(PID_FILE)
    # pgrep fallback
    try:
        r = subprocess.run(["pgrep", "-f", "cryptologyt/main.py"],
                           capture_output=True, text=True, timeout=5)
        if r.stdout.strip():
            return True, int(r.stdout.strip().split("\n")[0])
    except Exception:
        pass
    return False, None


def cryptologyt_status():
    """Cryptologyt-এর স্ট্যাটাস"""
    running, pid = _is_running()
    info = {
        "running": running,
        "pid": pid,
        "timestamp": datetime.now().isoformat(),
        "cryptologyt_dir": CRYPTOLYT_DIR,
    }
    if running and pid:
        try:
            r = subprocess.run(["ps", "-p", str(pid), "-o", "pcpu,pmem,etime"],
                               capture_output=True, text=True, timeout=5)
            info["process_stats"] = r.stdout.strip()
        except Exception:
            pass
    return info


def cryptologyt_start():
    """Cryptologyt চালু করে"""
    running, pid = _is_running()
    if running:
        return f"⚠️ Cryptologyt already running (PID: {pid})"
    if not os.path.exists(os.path.join(CRYPTOLYT_DIR, "main.py")):
        return f"❌ main.py not found in {CRYPTOLYT_DIR}"
    try:
        log_file = open(CRYPTOLYT_LOG, "a")
        log_file.write(f"\n\n{'='*60}\n[{datetime.now()}] Nova started Cryptologyt\n{'='*60}\n")
        log_file.flush()
        proc = subprocess.Popen(
            CRYPTOLYT_CMD,
            stdout=log_file, stderr=subprocess.STDOUT,
            cwd=CRYPTOLYT_DIR, start_new_session=True
        )
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))
        time.sleep(3)
        running, _ = _is_running()
        if running:
            return f"✅ Cryptologyt started (PID: {proc.pid})"
        return "⚠️ Cryptologyt start command sent, verifying..."
    except Exception as e:
        return f"❌ Failed to start: {e}"


def cryptologyt_stop():
    """Cryptologyt বন্ধ করে (graceful → force)"""
    running, pid = _is_running()
    if not running:
        return "ℹ️ Cryptologyt is not running."
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(1)
            running, _ = _is_running()
            if not running:
                break
        else:
            os.kill(pid, signal.SIGKILL)
            time.sleep(1)
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return f"✅ Cryptologyt stopped (was PID: {pid})"
    except Exception as e:
        return f"❌ Failed to stop: {e}"


def cryptologyt_logs(lines: int = 50, log_type: str = "main"):
    """লগ পড়া (main অথবা live)"""
    path = CRYPTOLYT_LIVE_LOG if log_type == "live" else CRYPTOLYT_LOG
    if not os.path.exists(path):
        return f"❌ Log not found: {path}"
    try:
        r = subprocess.run(["tail", "-n", str(lines), path],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "(empty log)"
    except Exception as e:
        return f"❌ Error: {e}"


def cryptologyt_parse_signals(lines: int = 500):
    """লগ থেকে BUY/SELL/PROFIT/LOSS সিগন্যাল পার্স"""
    path = CRYPTOLYT_LOG
    if not os.path.exists(path):
        return {"error": "log not found"}
    try:
        with open(path, "r", errors="replace") as f:
            content = f.read()
        recent = "\n".join(content.splitlines()[-lines:])

        # Common patterns
        buy = re.findall(r"\b(?:BUY|LONG)\b[^\n]{0,80}", recent, re.IGNORECASE)
        sell = re.findall(r"\b(?:SELL|SHORT)\b[^\n]{0,80}", recent, re.IGNORECASE)
        profit = re.findall(r"\b(?:PROFIT|TP HIT|TAKE PROFIT)[^\n]{0,80}", recent, re.IGNORECASE)
        loss = re.findall(r"\b(?:LOSS|SL HIT|STOP LOSS)[^\n]{0,80}", recent, re.IGNORECASE)
        errors = re.findall(r"\[ERROR\][^\n]{0,150}", recent)
        warnings = re.findall(r"\[WARNING\][^\n]{0,150}", recent)

        return {
            "lines_scanned": len(recent.splitlines()),
            "buy_count": len(buy),
            "sell_count": len(sell),
            "profit_events": len(profit),
            "loss_events": len(loss),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "recent_buy": buy[-5:],
            "recent_sell": sell[-5:],
            "recent_errors": errors[-3:],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


def cryptologyt_recent_trades(lines: int = 200):
    """সাম্প্রতিক ট্রেড/পজিশন এক্সিকিউশন"""
    path = CRYPTOLYT_LOG
    if not os.path.exists(path):
        return "Log not found"
    try:
        r = subprocess.run(["tail", "-n", str(lines), path],
                           capture_output=True, text=True, timeout=10)
        trades = [ln for ln in r.stdout.splitlines()
                  if re.search(r"(BUY|SELL|LONG|SHORT|POSITION|CLOSED|FILLED)", ln, re.I)]
        return "\n".join(trades[-30:]) if trades else "No recent trades found."
    except Exception as e:
        return f"Error: {e}"


def cryptologyt_summary():
    """Cryptologyt-এর সম্পূর্ণ সামারি তৈরি (স্ট্যাটাস + সিগন্যাল + রিপোর্ট)"""
    report = {
        "generated_at": datetime.now().isoformat(),
        "status": cryptologyt_status(),
        "signals": cryptologyt_parse_signals(500),
    }
    with open(SUMMARY_FILE, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return report


def cryptologyt_health_check():
    """দীর্ঘ সময় ধরে চেক করে দেখা ক্র্যাশ করছে কিনা"""
    path = CRYPTOLYT_LOG
    if not os.path.exists(path):
        return "Log not found"
    try:
        with open(path, "r", errors="replace") as f:
            tail = f.readlines()[-100:]
        text = "".join(tail)
        errors = len(re.findall(r"\[ERROR\]", text))
        warnings = len(re.findall(r"\[WARNING\]", text))
        # শেষ লাইনের টাইমস্ট্যাম্প
        last_ts = None
        for line in reversed(tail):
            m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
            if m:
                last_ts = m.group(1)
                break
        return {
            "last_log_time": last_ts,
            "errors_in_last_100_lines": errors,
            "warnings_in_last_100_lines": warnings,
            "health": "OK" if errors < 5 else "DEGRADED" if errors < 20 else "CRITICAL",
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print("=== Cryptologyt Manager Test ===\n")
    print("Status:", json.dumps(cryptologyt_status(), indent=2))
    print("\nHealth:", json.dumps(cryptologyt_health_check(), indent=2))
    print("\nSignals:", json.dumps(cryptologyt_parse_signals(), indent=2, ensure_ascii=False))
    print("\nLast 10 log lines:")
    print(cryptologyt_logs(10))
