# Market Monitor

Football betting **market monitoring** platform with Telegram alerts.

> ⚠️ This is NOT an auto-betting product. The system only observes bookmaker
> odds and notifies humans of unusual movements. All betting decisions and
> actions are made by humans, outside this system.

**Current focus: World Cup.** The database seeds boot the system in
`world_cup_only_mode` with `dry_run` on. **Follow [SETUP.md](SETUP.md)** for the
exact steps to plug in your API keys and Telegram bot — everything else is ready.

## Architecture (summary)

- **`apps/web`** — Next.js dashboard + control-plane API. Deploys to **Vercel**.
- **`services/worker`** — Python monitoring loop. Deploys to **Railway/Fly/VPS**
  (never Vercel — Vercel cron is production-only and unfit for continuous polling).
- **`packages/shared`** — TypeScript contracts shared with the web app
  (mirrored by hand in `services/worker/worker/models.py`).
- **`infra/sql`** — Supabase/Postgres migrations (schema, RLS, seeds).
- **`docs/MVP_BLUEPRINT.md`** — the full product/engineering blueprint. **Read this first.**

Data flow: Odds API → worker (normalize → detect → score) → Supabase →
Telegram + dashboard.

## Setup

1. **Supabase**: create a project, then apply `infra/sql/0001_init.sql`
   (SQL editor or `supabase db push`). Create your user via Auth, it lands in
   `public.users` as admin.
2. **Web**: `npm install` at repo root, copy `apps/web/.env.example` →
   `.env.local`, fill values, `npm run dev:web`. Deploy to Vercel with the same
   env vars (root directory: `apps/web`).
3. **Worker**: see `services/worker/README.md`. Needs The Odds API key
   (free tier) and a Telegram bot token from @BotFather. Put the target chat
   ids into `monitor_segments.telegram_chat_id` (one per segment).
4. **Go live**: the system starts in `dry_run = true`. Review a day of stored
   alerts on the dashboard, tune `min_alert_score`, then flip dry-run off from
   the Football settings page.

## Modes

- `football_enabled` — general football segment (default: EPL).
- `world_cup_enabled` — World Cup segment (own thresholds, bookmakers, chat).
- `world_cup_only_mode` — tournament lockdown: ONLY World Cup is monitored,
  general football is suppressed even if enabled; the full API budget goes to WC.
- `global_pause` — worker idles (still heartbeats).
- `dry_run` — full pipeline, no Telegram sends.

## Budget

The Odds API free tier ≈ 500 credits/month; one poll costs `markets × regions`
credits (default 3). The worker enforces `daily_credit_cap` (default 16) and
polls adaptively based on time-to-kickoff. See blueprint §3 and §15.
