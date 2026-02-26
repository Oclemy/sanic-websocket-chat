# Sanic Websocket Chat

[![Run on Codely](https://codely.run/python/static/buttons/run-minimal.svg)](https://codely.run/python/projects/sanic-websocket-chat) [![Edit on Codely](https://codely.run/python/static/buttons/browse-minimal.svg)](https://codely.run/python/projects/sanic-websocket-chat) [![View Demo](https://codely.run/python/static/buttons/view_demo-minimal.svg)](https://codely.run/python/projects/sanic-websocket-chat)

Hello this is a Single-file Sanic app with the full chat frontend embedded. It's features: join screen, color-coded usernames, typing indicators, auto-reconnect, chat history (last 50 on join), online count, dark responsive UI.

## One-click Deploy

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/sanic-websocket-chat?referralCode=-Xd4K_&utm_medium=integration&utm_source=template&utm_campaign=generic)

## NOTE:

It's fully multi-user, bidirectional. The broadcast() function sends every message to all connected WebSocket clients. If you're testing alone, open 2+ browser tabs to localhost:8000 — join with different names and you'll see messages flow between them in real time.
