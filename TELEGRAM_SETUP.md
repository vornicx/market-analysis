# Telegram Bot Setup Guide

## Step 1: Create the Bot
1. Open Telegram and search for @BotFather
2. Start a chat with @BotFather
3. Send the command: `/newbot`
4. Choose a display name for your bot (e.g., "Market Monitor Bot")
5. Choose a username (e.g., "MarketMonitorBot")
6. BotFather will give you a token like: `123456:ABC-DEF...`

## Step 2: Get the Chat ID
1. Add @RawDataBot to the group/channel where you want alerts
2. Open @RawDataBot and send any message (like "hello")
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for "chat" -> "id" in the response
5. Group chat IDs typically start with `-100` (e.g., `-100123456789`)
6. Store this chat ID for later (Step 3 below)

## Step 3: Update the Database
In your Supabase SQL Editor, run:
```sql
UPDATE public.monitor_segments
SET telegram_chat_id = '-100YOUR_CHAT_ID_HERE'
WHERE segment_key = 'world_cup';
```

## What You Need to Store
- **Bot Token**: `123456:ABC-DEF...` (keep this secret)
- **Chat ID**: `-100123456789` (for the world_cup segment)

## Setup Complete!
You can now proceed to configure the environment files.