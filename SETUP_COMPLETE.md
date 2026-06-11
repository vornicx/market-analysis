# Complete Setup Guide

This document covers all setup steps that remain after the SQL setup (0001_init.sql and 0002_hardening.sql) has been completed.

## Step 1: Your Telegram Bot Token

**Bot Token Provided:** `8684419264:AAEZrVE31cVT2DB4g0VLDgFNQMtvLBtsYQ4`
**Bot Name:** Market Analyst @ocjvbot

Next, you need to:

1. Add this bot to your target group/channel where you want alerts
2. Get the chat ID using @RawDataBot or the API
3. Update the database with the chat ID:
```sql
UPDATE public.monitor_segments
SET telegram_chat_id = '-100YOUR_CHAT_ID_HERE'
WHERE segment_key = 'world_cup';
```

## Step 2: Configure Environment Files

### Worker Environment (.env)

Copy `.env.example` to `.env` and replace placeholders:

```bash
cd services/worker
copy .env.example .env
```

Edit `.env` with:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Your service role key
- `ODDS_API_KEY`: Your API key from The Odds API
- `TELEGRAM_BOT_TOKEN`: Your bot token from Step 1
- `APP_BASE_URL`: Your app URL (e.g., `https://your-app.vercel.app`)

### Web App Environment (.env.local)

Copy `.env.example` to `.env.local`:

```bash
cd apps/web
copy .env.example .env.local
```

Edit `.env.local` with:
- `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your anon key
- `SUPABASE_SERVICE_ROLE_KEY`: Your service role key
- `WORKER_API_TOKEN`: Generate a long random string
- `NEXT_PUBLIC_APP_URL`: Your app URL (must match worker)

## Step 3: Set Up Development Environments

### Worker (Python)

```bash
cd services/worker
python -m venv .venv
.venv\Scripts\Activate.ps1  # On Windows
# On Linux/macOS:
source .venv/bin/activate

pip install -e .
```

### Web App (Node.js)

```bash
cd apps/web
npm install
```

## Step 4: Validation and Testing

### Worker Setup Validation

```bash
cd services/worker
python scripts/check_setup.py
```

This validates all 6 checks:
1. Environment variables
2. Supabase connection and config
3. World Cup segment chat ID
4. The Odds API (0-credit call)
5. Telegram bot token
6. Telegram chat accessibility

### Expected Output

```
[OK] Env vars present (no placeholders)
[OK] Supabase connection + config row
[OK] World Cup segment chat id
[OK] The Odds API key (0-credit call)
[OK] Telegram bot token
[OK] Telegram chat reachable by bot

All checks passed. Start the worker: python -m worker.main
Reminder: dry_run is ON by default — flip it from the dashboard to go live.
```

## Step 5: Start Development Servers

### Worker

```bash
cd services/worker
python -m worker.main
```

### Web App

```bash
cd apps/web
npm run dev:web
```

## Step 6: Production Deployment

### Worker (to Railway/Fly/VPS)

```bash
# Dockerfile-free Railway setup
# Point service at services/worker with start command: python -m worker.main
```

### Web App (to Vercel)

```bash
# Import this repo in Vercel
# Root Directory: apps/web
# Add the same environment variables from .env.local
```

## Step 7: Go Live

1. Review alerts in the dashboard for 1 day of data
2. Go to Settings → Football → "Dry run" and toggle OFF
3. Verify alerts are being sent to Telegram
4. Monitor system health and budgets

## Environment Variables Reference

| Variable | Worker | Web | Description |
|----------|--------|-----|-------------|
| SUPABASE_URL | ✅ | ✅ | Supabase project URL |
| SUPABASE_ANON_KEY | ❌ | ✅ | Browser-facing key |
| SUPABASE_SERVICE_ROLE_KEY | ✅ | ✅ | Server-only key (keep secure) |
| ODDS_API_KEY | ✅ | ❌ | The Odds API key |
| TELEGRAM_BOT_TOKEN | ✅ | ✅ | Telegram bot token |
| WORKER_API_TOKEN | ❌ | ✅ | Shared secret for API routes |
| APP_BASE_URL | ✅ | ✅ | Base URL for alert links |

## Troubleshooting

### Check Setup Script Issues

```bash
cd services/worker
python scripts/check_setup.py
```

Fix any failures before proceeding.

### Common Issues

1. **Invalid API keys**: Get fresh keys from the respective services
2. **Chat ID issues**: Verify the bot is a member and the chat ID format is correct
3. **Port conflicts**: Use different ports for local development if needed
4. **Missing dependencies**: Run `pip install -e .` in worker and `npm install` in web

## Complete Setup Checklist

- [ ] Get The Odds API key
- [ ] Create Telegram bot and get chat ID
- [ ] Configure Supabase environment variables
- [ ] Set up Python virtual environment and install worker dependencies
- [ ] Set up Node.js dependencies
- [ ] Configure worker `.env` file
- [ ] Configure web `.env.local` file
- [ ] Run `check_setup.py` - all 6 checks pass
- [ ] Start worker: `python -m worker.main`
- [ ] Start web app: `npm run dev:web`
- [ ] Review dashboard alerts in dry-run mode
- [ ] Turn off dry-run mode to go live
- [ ] Verify Telegram delivery

Good luck! If you encounter any issues, refer to this guide or check the detailed documentation in the repository.