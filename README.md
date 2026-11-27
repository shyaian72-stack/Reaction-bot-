# Telegram Auto Reaction Bot — Render

## Features
- Watches new posts in channels where the bot is an administrator.
- Adds one 🔥 reaction per new post (not ten; Telegram can reject multiple reactions with `REACTIONS_TOO_MANY`).
- Admin commands: `/start`, `/admin`, `/on`, `/off`, `/status`.
- Web health endpoints: `/` and `/health`.
- Render configuration included in `render.yaml`.

## 1. Telegram setup
1. Create a bot using [@BotFather](https://t.me/BotFather).
2. Add the bot to your channel as an administrator and allow it to manage reactions if that permission is offered.
3. Find your numeric Telegram user ID for `ADMIN_ID`.
4. If a bot token was ever posted publicly, revoke it in BotFather and use a new one.

## 2. Deploy to Render
1. Upload these files to a GitHub repository: `main.py`, `requirements.txt`, `render.yaml`.
2. In Render, choose **New + → Blueprint** and select that repository, or create a **Web Service** from the repository.
3. Set environment variables in Render:
   - `BOT_TOKEN` = your new BotFather token
   - `ADMIN_ID` = your numeric Telegram user ID
4. Build command: `pip install -r requirements.txt`
5. Start command: `python main.py`
6. Deploy. Open `https://YOUR-SERVICE.onrender.com/health`. A healthy response contains `"status":"ok"`.

## 3. UptimeRobot
1. Create an HTTP(s) monitor.
2. Monitor URL: `https://YOUR-SERVICE.onrender.com/health`
3. Set an interval allowed by your UptimeRobot plan.
4. Save the monitor.

Important: UptimeRobot pings can sometimes help wake a sleeping free service, but they do not guarantee 24/7 uptime. Render free services may sleep or have usage limits.

## 4. Important notes
- Keep `BOT_TOKEN` secret. Do not commit it into GitHub or send it in chat.
- The bot only reacts to new channel posts received while it is running; it does not backfill old posts.
- The bot requests one 🔥 reaction. `is_big=True` asks Telegram for a big reaction effect, but Telegram client settings/API behavior determine what users see.
- Avoid running another polling instance with the same token; it can cause `409 Conflict`.
