import os
import json
import asyncio
from datetime import datetime
from uuid import uuid4
from sanic import Sanic, Request
from sanic.response import html, json as json_response

app = Sanic("WebSocketChat")

# --- State ---
connected_clients: dict[str, dict] = {}  # ws_id -> {ws, username, color}
chat_history: list[dict] = []
MAX_HISTORY = 200

COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
    "#1abc9c", "#e67e22", "#e84393", "#00cec9", "#6c5ce7",
    "#fd79a8", "#00b894", "#fdcb6e", "#fab1a0", "#74b9ff",
]
color_index = 0


def next_color():
    global color_index
    c = COLORS[color_index % len(COLORS)]
    color_index += 1
    return c


async def broadcast(message: dict, exclude=None):
    chat_history.append(message)
    if len(chat_history) > MAX_HISTORY:
        chat_history.pop(0)
    data = json.dumps(message)
    tasks = []
    for wid, info in connected_clients.items():
        if wid != exclude:
            tasks.append(info["ws"].send(data))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


@app.websocket("/ws")
async def chat(request: Request, ws):
    ws_id = str(uuid4())
    color = next_color()
    username = None

    try:
        async for raw in ws:
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "join":
                username = msg.get("username", "Anon").strip()[:20] or "Anon"
                connected_clients[ws_id] = {"ws": ws, "username": username, "color": color}

                # Send history + user info
                await ws.send(json.dumps({
                    "type": "init",
                    "history": chat_history[-50:],
                    "userCount": len(connected_clients),
                    "color": color,
                }))

                await broadcast({
                    "type": "system",
                    "text": f"{username} joined the chat",
                    "timestamp": datetime.now().isoformat(),
                    "userCount": len(connected_clients),
                })

            elif msg_type == "message" and username:
                text = msg.get("text", "").strip()[:1000]
                if text:
                    await broadcast({
                        "type": "message",
                        "username": username,
                        "text": text,
                        "color": color,
                        "timestamp": datetime.now().isoformat(),
                    })

            elif msg_type == "typing" and username:
                data = json.dumps({"type": "typing", "username": username})
                for wid, info in connected_clients.items():
                    if wid != ws_id:
                        await info["ws"].send(data)

    finally:
        connected_clients.pop(ws_id, None)
        if username:
            await broadcast({
                "type": "system",
                "text": f"{username} left the chat",
                "timestamp": datetime.now().isoformat(),
                "userCount": len(connected_clients),
            })


@app.get("/")
async def index(request: Request):
    return html(FRONTEND_HTML)


@app.get("/health")
async def health(request: Request):
    return json_response({"status": "ok", "clients": len(connected_clients)})


FRONTEND_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WebSocket Chat</title>
<style>
  :root {
    --bg: #0f0f17; --surface: #1a1a2e; --surface2: #16213e;
    --border: #2a2a4a; --text: #e0e0e0; --muted: #888;
    --accent: #7c3aed; --accent2: #a78bfa; --green: #10b981;
    --radius: 12px;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--text); height: 100dvh;
    display: flex; flex-direction: column; overflow: hidden;
  }
  header {
    background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 14px 20px; display: flex; align-items: center;
    justify-content: space-between; flex-shrink: 0;
  }
  header h1 { font-size: 1.15rem; font-weight: 600; }
  header h1 span { color: var(--accent2); }
  .status {
    display: flex; align-items: center; gap: 6px;
    font-size: 0.8rem; color: var(--muted);
  }
  .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--green); animation: pulse 2s infinite;
  }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

  /* Join screen */
  #joinScreen {
    flex: 1; display: flex; align-items: center; justify-content: center;
  }
  .join-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; padding: 40px; text-align: center;
    max-width: 380px; width: 90%;
  }
  .join-card h2 { margin-bottom: 6px; font-size: 1.4rem; }
  .join-card p { color: var(--muted); font-size: 0.9rem; margin-bottom: 24px; }
  .join-card input {
    width: 100%; padding: 12px 16px; border-radius: var(--radius);
    border: 1px solid var(--border); background: var(--bg);
    color: var(--text); font-size: 1rem; outline: none;
    margin-bottom: 16px; transition: border 0.2s;
  }
  .join-card input:focus { border-color: var(--accent); }
  .btn {
    width: 100%; padding: 12px; border: none; border-radius: var(--radius);
    background: var(--accent); color: #fff; font-size: 1rem;
    font-weight: 600; cursor: pointer; transition: background 0.2s;
  }
  .btn:hover { background: #6d28d9; }

  /* Chat */
  #chatScreen { flex: 1; display: none; flex-direction: column; }
  #messages {
    flex: 1; overflow-y: auto; padding: 16px 20px;
    display: flex; flex-direction: column; gap: 6px;
    scroll-behavior: smooth;
  }
  #messages::-webkit-scrollbar { width: 6px; }
  #messages::-webkit-scrollbar-thumb {
    background: var(--border); border-radius: 3px;
  }
  .msg {
    max-width: 75%; padding: 10px 14px; border-radius: 16px;
    font-size: 0.92rem; line-height: 1.45; word-break: break-word;
    animation: fadeIn 0.25s ease;
  }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; } }
  .msg.mine {
    align-self: flex-end; background: var(--accent);
    border-bottom-right-radius: 4px; color: #fff;
  }
  .msg.theirs {
    align-self: flex-start; background: var(--surface2);
    border-bottom-left-radius: 4px;
  }
  .msg .author {
    font-size: 0.75rem; font-weight: 700; margin-bottom: 2px;
    display: block;
  }
  .msg .time {
    font-size: 0.65rem; opacity: 0.55; margin-top: 3px; display: block;
    text-align: right;
  }
  .msg.system {
    align-self: center; background: none; color: var(--muted);
    font-size: 0.78rem; padding: 4px 0; max-width: 100%;
  }
  #typingIndicator {
    padding: 2px 20px 6px; font-size: 0.78rem; color: var(--muted);
    height: 22px; flex-shrink: 0;
  }

  /* Input bar */
  .input-bar {
    padding: 12px 16px; background: var(--surface);
    border-top: 1px solid var(--border); display: flex;
    gap: 10px; align-items: center; flex-shrink: 0;
  }
  .input-bar input {
    flex: 1; padding: 12px 16px; border-radius: 24px;
    border: 1px solid var(--border); background: var(--bg);
    color: var(--text); font-size: 0.95rem; outline: none;
    transition: border 0.2s;
  }
  .input-bar input:focus { border-color: var(--accent); }
  .send-btn {
    width: 44px; height: 44px; border-radius: 50%;
    background: var(--accent); border: none; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.2s; flex-shrink: 0;
  }
  .send-btn:hover { background: #6d28d9; }
  .send-btn svg { fill: #fff; width: 20px; height: 20px; }

  @media (max-width: 600px) {
    .msg { max-width: 88%; }
    .join-card { padding: 28px 20px; }
  }
</style>
</head>
<body>
  <header>
    <h1>&#x1f4ac; <span>WS</span>Chat</h1>
    <div class="status">
      <div class="dot" id="statusDot"></div>
      <span id="userCount">0 online</span>
    </div>
  </header>

  <div id="joinScreen">
    <div class="join-card">
      <h2>Welcome!</h2>
      <p>Pick a username and jump into the conversation.</p>
      <input type="text" id="usernameInput" placeholder="Your name..." maxlength="20" autofocus>
      <button class="btn" id="joinBtn">Join Chat</button>
    </div>
  </div>

  <div id="chatScreen">
    <div id="messages"></div>
    <div id="typingIndicator"></div>
    <div class="input-bar">
      <input type="text" id="msgInput" placeholder="Type a message..." maxlength="1000">
      <button class="send-btn" id="sendBtn">
        <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
      </button>
    </div>
  </div>

<script>
  const $ = id => document.getElementById(id);
  let ws, myColor, myName, typingTimeout, lastTypingSent = 0;

  function connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws`);

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'join', username: myName }));
    };

    ws.onmessage = e => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'init') {
        myColor = msg.color;
        $('userCount').textContent = msg.userCount + ' online';
        msg.history.forEach(renderMsg);
        scrollBottom();
      } else if (msg.type === 'typing') {
        showTyping(msg.username);
      } else {
        if (msg.userCount !== undefined) {
          $('userCount').textContent = msg.userCount + ' online';
        }
        renderMsg(msg);
        scrollBottom();
      }
    };

    ws.onclose = () => {
      renderMsg({ type: 'system', text: 'Disconnected. Reconnecting...' });
      $('statusDot').style.background = '#ef4444';
      setTimeout(connect, 2000);
    };
  }

  function renderMsg(msg) {
    const el = document.createElement('div');
    el.classList.add('msg');

    if (msg.type === 'system') {
      el.classList.add('system');
      el.textContent = msg.text;
    } else {
      const isMe = msg.username === myName && msg.color === myColor;
      el.classList.add(isMe ? 'mine' : 'theirs');
      const t = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '';
      el.innerHTML = (isMe ? '' : `<span class="author" style="color:${msg.color}">${esc(msg.username)}</span>`)
        + esc(msg.text) + `<span class="time">${t}</span>`;
    }
    $('messages').appendChild(el);
  }

  function scrollBottom() {
    const m = $('messages');
    requestAnimationFrame(() => m.scrollTop = m.scrollHeight);
  }

  function esc(s) {
    const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
  }

  function showTyping(name) {
    $('typingIndicator').textContent = `${name} is typing...`;
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => $('typingIndicator').textContent = '', 2000);
  }

  function sendMsg() {
    const text = $('msgInput').value.trim();
    if (!text || !ws || ws.readyState !== 1) return;
    ws.send(JSON.stringify({ type: 'message', text }));
    $('msgInput').value = '';
  }

  function join() {
    myName = $('usernameInput').value.trim() || 'Anon';
    $('joinScreen').style.display = 'none';
    $('chatScreen').style.display = 'flex';
    connect();
    $('msgInput').focus();
  }

  $('joinBtn').onclick = join;
  $('usernameInput').onkeydown = e => { if (e.key === 'Enter') join(); };
  $('sendBtn').onclick = sendMsg;
  $('msgInput').onkeydown = e => { if (e.key === 'Enter') sendMsg(); };
  $('msgInput').oninput = () => {
    if (Date.now() - lastTypingSent > 1500 && ws?.readyState === 1) {
      ws.send(JSON.stringify({ type: 'typing' }));
      lastTypingSent = Date.now();
    }
  };
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, auto_reload=False)
