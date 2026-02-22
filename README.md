# sanic-websocket-chat

Hello this is a Single-file Sanic app with the full chat frontend embedded. It's features: join screen, color-coded usernames, typing indicators, auto-reconnect, chat history (last 50 on join), online count, dark responsive UI.

## NOTE:

It's fully multi-user, bidirectional. The broadcast() function sends every message to all connected WebSocket clients. If you're testing alone, open 2+ browser tabs to localhost:8000 — join with different names and you'll see messages flow between them in real time.
