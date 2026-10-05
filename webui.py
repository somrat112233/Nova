import os, re, sys, json, secrets, threading, hmac
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent

if "Nova wants to run" not in (HERE / "agent.py").read_text():
    sys.exit("Shell confirmation patch missing in agent.py. Apply the confirmation step first.")

agent.MEMORY_FILE = HERE / "memory_web.json"
os.environ["AGENT_CONFIRM_SHELL"] = "1"
ENV_FILE = agent.ENV_FILE
HOST = os.getenv("AGENT_WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("AGENT_WEB_PORT", "8765"))


def save_env(key, value):
    with open(ENV_FILE, "a") as f:
        f.write(f"\n{key}={value}\n")
    os.chmod(ENV_FILE, 0o600)
    os.environ[key] = value


TOKEN = os.getenv("WEB_TOKEN")
if not TOKEN:
    TOKEN = secrets.token_urlsafe(24)
    save_env("WEB_TOKEN", TOKEN)


def build_llm():
    backend = os.getenv("AGENT_BACKEND", "gemini")
    if backend == "local":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="local", base_url="http://127.0.0.1:8080/v1",
                         api_key="none", max_tokens=1024, temperature=0.2)
    elif backend == "gemini":
        from langchain_openai import ChatOpenAI
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            sys.exit("GEMINI_API_KEY not found. Run 'nova \"hello\"' once to save it.")
        llm = ChatOpenAI(model=os.getenv("AGENT_GEMINI_MODEL", "gemini-3.8-flash"),
                         base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                         api_key=key, max_tokens=2048)
    else:
        agent.ensure_key()
        llm = agent.ChatAnthropic(model=agent.MODEL, max_tokens=2048)
    return llm.bind_tools(list(agent.TOOLS.values()))


LLM = build_llm()

lock = threading.Lock()
state = {"busy": False, "pending": None, "reply": None, "log": [], "event": None, "answer": False}
last_print = {"text": ""}


class FakeConsole:
    def __init__(self, real):
        self.real = real

    def print(self, *a, **k):
        text = re.sub(r"\[/?[a-z ]+\]", "", " ".join(str(x) for x in a))
        last_print["text"] = text
        if state["busy"]:
            state["log"].append(text[:300])
        self.real.print(*a, **k)


agent.console = FakeConsole
bash <<'WEBSETUP'
set -e
pkg install -y tmux
cat > ~/agi/webui.py <<'PYEOF'
import os, re, sys, json, secrets, threading, hmac
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent

if "Nova wants to run" not in (HERE / "agent.py").read_text():
    sys.exit("Shell confirmation patch missing in agent.py. Apply the confirmation step first.")

agent.MEMORY_FILE = HERE / "memory_web.json"
os.environ["AGENT_CONFIRM_SHELL"] = "1"
ENV_FILE = agent.ENV_FILE
HOST = os.getenv("AGENT_WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("AGENT_WEB_PORT", "8765"))


def save_env(key, value):
    with open(ENV_FILE, "a") as f:
        f.write(f"\n{key}={value}\n")
    os.chmod(ENV_FILE, 0o600)
    os.environ[key] = value


TOKEN = os.getenv("WEB_TOKEN")
if not TOKEN:
    TOKEN = secrets.token_urlsafe(24)
    save_env("WEB_TOKEN", TOKEN)


def build_llm():
    backend = os.getenv("AGENT_BACKEND", "gemini")
    if backend == "local":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="local", base_url="http://127.0.0.1:8080/v1",
                         api_key="none", max_tokens=1024, temperature=0.2)
    elif backend == "gemini":
        from langchain_openai import ChatOpenAI
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            sys.exit("GEMINI_API_KEY not found. Run 'nova \"hello\"' once to save it.")
        llm = ChatOpenAI(model=os.getenv("AGENT_GEMINI_MODEL", "gemini-3.8-flash"),
                         base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                         api_key=key, max_tokens=2048)
    else:
        agent.ensure_key()
        llm = agent.ChatAnthropic(model=agent.MODEL, max_tokens=2048)
    return llm.bind_tools(list(agent.TOOLS.values()))


LLM = build_llm()

lock = threading.Lock()
state = {"busy": False, "pending": None, "reply": None, "log": [], "event": None, "answer": False}
last_print = {"text": ""}


class FakeConsole:
    def __init__(self, real):
        self.real = real

    def print(self, *a, **k):
        text = re.sub(r"\[/?[a-z ]+\]", "", " ".join(str(x) for x in a))
        last_print["text"] = text
        if state["busy"]:
            state["log"].append(text[:300])
        self.real.print(*a, **k)


agent.console = FakeConsole(agent.console)


def web_input(prompt=""):
    ev = threading.Event()
    state["answer"] = False
    state["event"] = ev
    state["pending"] = last_print["text"]
    ev.wait(120)
    state["pending"] = None
    state["event"] = None
    return "y" if state["answer"] else "n"


agent.input = web_input


def work(text):
    try:
        history = agent.load_history()
        reply = agent.run_agent(LLM, history, text)
        agent.save_history(history)
    except Exception as e:
        reply = f"Error: {e}"
    with lock:
        state["reply"] = reply or "(empty)"
        state["busy"] = False


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nova</title>
<style>
body{margin:0;font-family:sans-serif;background:#111;color:#eee;display:flex;flex-direction:column;height:100dvh}
#chat{flex:1;overflow-y:auto;padding:10px}
.m{margin:8px 0;padding:8px 10px;border-radius:10px;white-space:pre-wrap;word-break:break-word}
.u{background:#2a4a7a;margin-left:15%}
.n{background:#2b2b2b;margin-right:5%}
.l{color:#8a8;font-size:12px;font-family:monospace;padding:2px 10px}
#cf{display:none;background:#4a3a10;padding:10px;word-break:break-word}
#cf button{padding:10px 18px;margin:8px 8px 0 0;font-size:16px}
#bar{display:flex;gap:6px;padding:8px;background:#1b1b1b}
#t{flex:1;min-width:0;padding:10px;font-size:16px;border-radius:8px;border:0}
#bar button{padding:10px 12px;font-size:16px}
</style></head><body>
<div id="chat"></div>
<div id="cf"><div id="cmd"></div><button id="ok">Allow</button><button id="no">Deny</button></div>
<div id="bar"><input id="t" placeholder="Message Nova..." autocomplete="off"><button id="s">Send</button><button id="r">Reset</button></div>
<script>
var T = location.hash.slice(1);
try { if (T) localStorage.setItem('nt', T); else T = localStorage.getItem('nt') || ''; } catch (e) {}
var chat = document.getElementById('chat'), cf = document.getElementById('cf');
var cmd = document.getElementById('cmd'), t = document.getElementById('t');
var timer = null, shown = 0;
function add(cls, text) {
  var d = document.createElement('div'); d.className = 'm ' + cls; d.textContent = text;
  chat.appendChild(d); chat.scrollTop = chat.scrollHeight; return d;
}
function api(path, body) {
  return fetch(path, {method: body === undefined ? 'GET' : 'POST',
    headers: {'X-Token': T, 'Content-Type': 'application/json'},
    body: body === undefined ? undefined : JSON.stringify(body)})
  .then(function (r) { return r.json().then(function (j) { j._code = r.status; return j; }); });
}
function stop() { if (timer) { clearInterval(timer); timer = null; } cf.style.display = 'none'; }
function poll() {
  api('/status').then(function (s) {
    if (s._code === 401) { stop(); add('n', 'Unauthorized. Open the URL printed in Termux (it ends with #token).'); return; }
    for (; shown < s.log.length; shown++) add('l', s.log[shown]);
    if (s.pending) { cmd.textContent = s.pending; cf.style.display = 'block'; } else { cf.style.display = 'none'; }
    if (!s.busy) { stop(); if (s.reply) add('n', s.reply); }
  }).catch(function () {});
}
function send() {
  var v = t.value.trim(); if (!v) return;
  t.value = ''; add('u', v); shown = 0;
  api('/chat', {text: v}).then(function (j) {
    if (j._code === 200) { stop(); timer = setInterval(poll, 1000); }
    else { add('n', j.error || 'Error'); }
  });
}
document.getElementById('s').onclick = send;
t.addEventListener('keydown', function (e) { if (e.key === 'Enter') send(); });
document.getElementById('ok').onclick = function () { api('/confirm', {allow: true}); cf.style.display = 'none'; };
document.getElementById('no').onclick = function () { api('/confirm', {allow: false}); cf.style.display = 'none'; };
document.getElementById('r').onclick = function () {
  api('/reset', {}).then(function (j) { chat.innerHTML = ''; add('n', j.error || 'Memory cleared.'); });
};
add('n', 'Nova ready.');
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _auth(self):
        given = self.headers.get("X-Token", "")
        return hmac.compare_digest(given.encode(), TOKEN.encode())

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif path == "/status":
            if not self._auth():
                return self._json(401, {"error": "unauthorized"})
            with lock:
                self._json(200, {k: state[k] for k in ("busy", "pending", "reply", "log")})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._auth():
            return self._json(401, {"error": "unauthorized"})
        try:
            length = min(int(self.headers.get("Content-Length", 0)), 100000)
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._json(400, {"error": "bad request"})
        path = urlparse(self.path).path
        if path == "/chat":
            text = str(body.get("text", "")).strip()
            if not text:
                return self._json(400, {"error": "empty message"})
            with lock:
                if state["busy"]:
                    return self._json(409, {"error": "Nova is still working on the previous task."})
                state.update(busy=True, reply=None, log=[], pending=None)
            threading.Thread(target=work, args=(text,), daemon=True).start()
            self._json(200, {"ok": True})
        elif path == "/confirm":
            ev = state.get("event")
            if ev:
                state["answer"] = bool(body.get("allow"))
                ev.set()
            self._json(200, {"ok": True})
        elif path == "/reset":
            if state["busy"]:
                return self._json(409, {"error": "Nova is busy, try again after it finishes."})
            agent.save_history([])
            self._json(200, {"ok": True})
        else:
            self._json(404, {"error": "not found"})


if __name__ == "__main__":
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    srv.daemon_threads = True
    print(f"Nova web UI (backend: {os.getenv('AGENT_BACKEND', 'gemini')})")
    print(f"Open on this phone:  http://127.0.0.1:{PORT}/#{TOKEN}")
    if HOST != "127.0.0.1":
        print(f"LAN mode: http://<phone-wifi-ip>:{PORT}/#{TOKEN}")
    print("Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
