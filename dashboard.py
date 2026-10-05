from flask import Response, jsonify, request
from pathlib import Path
import json
import os
import subprocess

# এজেন্টের গ্লোবাল স্টেট (bot.py থেকে আপডেট হবে)
DASHBOARD_STATE = {
    "busy": False,
    "current_task": "",
    "last_reply": "",
    "recent_logs": [],
    "battery": "Unknown",
    "location": "Unknown"
}

def register_dashboard_routes(app, shared_secret, workspace_path):
    """Flask অ্যাপে ড্যাশবোর্ডের রুটগুলো যোগ করে"""
    
    @app.route("/dashboard")
    def dashboard():
        token = request.args.get("token", "")
        if token != shared_secret:
            return Response("Unauthorized. Add ?token=YOUR_SECRET to the URL.", status=401)
        return Response(DASHBOARD_HTML, mimetype="text/html")
    
    @app.route("/api/dashboard_data")
    def dashboard_data():
        token = request.args.get("token", "")
        if token != shared_secret:
            return jsonify({"error": "unauthorized"}), 401
        
        # ওয়ার্কস্পেস ফাইল লিস্ট
        files = []
        ws = Path(workspace_path)
        if ws.exists():
            for f in ws.rglob("*"):
                if f.is_file():
                    files.append({"name": str(f.relative_to(ws)), "size": f.stat().st_size})
        
        # মেমোরি (knowledge.json)
        memory = []
        kb_path = Path(workspace_path).parent / "knowledge.json"
        if kb_path.exists():
            try:
                memory = json.loads(kb_path.read_text())[-20:]
            except Exception:
                pass
        
        # শিডিউল করা টাস্ক (schedule.json)
        schedule = []
        sched_path = Path(workspace_path).parent / "schedule.json"
        if sched_path.exists():
            try:
                schedule = json.loads(sched_path.read_text())
            except Exception:
                pass
        
        return jsonify({
            "state": DASHBOARD_STATE,
            "files": files[:50],
            "memory": memory,
            "schedule": schedule,
            "workspace": str(workspace_path)
        })

    @app.route("/api/run_command", methods=["POST"])
    def run_command():
        token = request.args.get("token", "")
        if token != shared_secret:
            return jsonify({"error": "unauthorized"}), 401
        data = request.json or {}
        cmd = data.get("command", "").strip()
        if not cmd:
            return jsonify({"error": "empty command"}), 400
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=workspace_path)
            output = (r.stdout + r.stderr).strip() or "(no output)"
            return jsonify({"output": output[:3000]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nova Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, 'Segoe UI', Roboto, sans-serif;
    background: #0a0e27;
    color: #e0e0e0;
    min-height: 100vh;
    padding: 16px;
  }
  .header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 20px; background: linear-gradient(135deg, #1a1f3a, #2a1f4a);
    border-radius: 12px; margin-bottom: 16px; border: 1px solid #3a3f5a;
  }
  .header h1 { font-size: 20px; color: #fff; }
  .status-badge {
    padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;
  }
  .status-idle { background: #1a4a2a; color: #4ade80; }
  .status-busy { background: #4a3a1a; color: #fbbf24; animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.6} }
  .grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
  @media (min-width: 768px) { .grid { grid-template-columns: 1fr 1fr; } }
  .card {
    background: #141829; border: 1px solid #232842;
    border-radius: 12px; padding: 16px;
  }
  .card h2 {
    font-size: 14px; color: #8b9dc3; margin-bottom: 12px;
    text-transform: uppercase; letter-spacing: 1px;
  }
  .stat { font-size: 24px; font-weight: 700; color: #fff; margin-bottom: 4px; }
  .stat-label { font-size: 12px; color: #6b7a99; }
  .list { list-style: none; max-height: 240px; overflow-y: auto; }
  .list li {
    padding: 8px 10px; background: #1a1f33; border-radius: 6px;
    margin-bottom: 6px; font-size: 13px; word-break: break-word;
    border-left: 3px solid #4a5a9a;
  }
  .log-line { font-family: monospace; font-size: 12px; color: #8ba88b; }
  .terminal {
    background: #000; border-radius: 8px; padding: 12px; 
    font-family: monospace; font-size: 12px;
    color: #4ade80; max-height: 200px; overflow-y: auto; margin-bottom: 10px;
  }
  input, button {
    padding: 10px 14px; border-radius: 8px; border: 1px solid #2a3050;
    background: #1a1f33; color: #e0e0e0; font-size: 14px;
  }
  input { width: 100%; margin-bottom: 8px; }
  button {
    background: linear-gradient(135deg, #4a5a9a, #6a4a9a);
    color: white; border: none; cursor: pointer; font-weight: 600;
  }
  button:hover { opacity: 0.9; }
  .badge {
    display: inline-block; padding: 3px 8px; border-radius: 4px;
    font-size: 11px; background: #2a3050; color: #8b9dc3; margin-left: 6px;
  }
  .empty { color: #4a5570; font-style: italic; font-size: 13px; }
</style>
</head>
<body>
  <div class="header">
    <h1>🤖 Nova Dashboard</h1>
    <span id="statusBadge" class="status-badge status-idle">Loading...</span>
  </div>

  <div class="grid">
    <div class="card">
      <h2>📊 Agent Status</h2>
      <div class="stat" id="agentStatus">-</div>
      <div class="stat-label">Current State</div>
      <div style="margin-top:12px">
        <div class="stat-label">Current Task:</div>
        <div id="currentTask" style="font-size:13px;color:#a0a0a0;margin-top:4px">-</div>
      </div>
    </div>

    <div class="card">
      <h2>📱 Phone Status</h2>
      <div class="stat" id="battery">-</div>
      <div class="stat-label">Battery</div>
      <div style="margin-top:12px">
        <div class="stat-label">Location:</div>
        <div id="location" style="font-size:13px;color:#a0a0a0;margin-top:4px">-</div>
      </div>
    </div>

    <div class="card">
      <h2>⏰ Scheduled Tasks <span class="badge" id="schedCount">0</span></h2>
      <ul class="list" id="scheduleList"><li class="empty">No scheduled tasks</li></ul>
    </div>

    <div class="card">
      <h2>🧠 Memory Notes <span class="badge" id="memCount">0</span></h2>
      <ul class="list" id="memoryList"><li class="empty">No memory notes</li></ul>
    </div>

    <div class="card">
      <h2>📁 Workspace Files <span class="badge" id="fileCount">0</span></h2>
      <ul class="list" id="fileList"><li class="empty">No files</li></ul>
    </div>

    <div class="card">
      <h2>💻 Remote Shell</h2>
      <div class="terminal" id="terminal">Ready...</div>
      <input id="cmdInput" placeholder="Type shell command..." />
      <button onclick="runCmd()">Run Command</button>
    </div>
  </div>

<script>
  const TOKEN = new URLSearchParams(location.search).get('token') || '';
  
  function formatBytes(b) {
    if (b < 1024) return b + ' B';
    if (b < 1048576) return (b/1024).toFixed(1) + ' KB';
    return (b/1048576).toFixed(1) + ' MB';
  }

  async function fetchData() {
    try {
      const r = await fetch('/api/dashboard_data?token=' + TOKEN);
      if (!r.ok) return;
      const d = await r.json();
      
      const st = d.state;
      document.getElementById('agentStatus').textContent = st.busy ? 'BUSY' : 'IDLE';
      document.getElementById('currentTask').textContent = st.current_task || 'Waiting for input...';
      
      const badge = document.getElementById('statusBadge');
      badge.textContent = st.busy ? 'Working...' : 'Online';
      badge.className = 'status-badge ' + (st.busy ? 'status-busy' : 'status-idle');
      
      document.getElementById('battery').textContent = st.battery || 'Unknown';
      document.getElementById('location').textContent = st.location || 'Unknown';
      
      // Schedule
      const sl = document.getElementById('scheduleList');
      document.getElementById('schedCount').textContent = d.schedule.length;
      sl.innerHTML = d.schedule.length ? d.schedule.map(t => 
        `<li><b>${t.id}</b> — ${t.tool} <span class="badge">every ${t.interval}m</span></li>`
      ).join('') : '<li class="empty">No scheduled tasks</li>';
      
      // Memory
      const ml = document.getElementById('memoryList');
      document.getElementById('memCount').textContent = d.memory.length;
      ml.innerHTML = d.memory.length ? d.memory.map(m => 
        `<li><b>${m.topic || 'note'}:</b> ${m.fact || ''}</li>`
      ).join('') : '<li class="empty">No memory notes</li>';
      
      // Files
      const fl = document.getElementById('fileList');
      document.getElementById('fileCount').textContent = d.files.length;
      fl.innerHTML = d.files.length ? d.files.map(f => 
        `<li>${f.name} <span class="badge">${formatBytes(f.size)}</span></li>`
      ).join('') : '<li class="empty">No files</li>';
      
      // Logs
      if (st.recent_logs && st.recent_logs.length) {
        document.getElementById('terminal').innerHTML = 
          st.recent_logs.slice(-8).map(l => `<div class="log-line">${l}</div>`).join('');
      }
    } catch (e) { console.error(e); }
  }
  
  async function runCmd() {
    const cmd = document.getElementById('cmdInput').value.trim();
    if (!cmd) return;
    const term = document.getElementById('terminal');
    term.innerHTML = `<div class="log-line">$ ${cmd}</div><div class="log-line">Running...</div>`;
    try {
      const r = await fetch('/api/run_command?token=' + TOKEN, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({command: cmd})
      });
      const d = await r.json();
      term.innerHTML = `<div class="log-line">$ ${cmd}</div><div class="log-line">${d.output || d.error || 'no output'}</div>`;
      document.getElementById('cmdInput').value = '';
    } catch (e) {
      term.innerHTML = `<div class="log-line">Error: ${e}</div>`;
    }
  }
  
  document.getElementById('cmdInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') runCmd();
  });
  
  setInterval(fetchData, 5000);
  fetchData();
</script>
</body>
</html>
"""
