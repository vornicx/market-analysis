---
name: project-market-monitor
description: Market Monitor project context — World Cup focus, GitHub remote, user language
metadata:
  type: project
---

Football odds market-monitoring MVP (NOT auto-betting). Monorepo: Next.js dashboard (Vercel) + Python worker + Supabase + Telegram.

- Current focus (since 2026-06-10): **World Cup mode** — DB seeds boot with `world_cup_only_mode=true`, `dry_run=true`.
- GitHub remote: https://github.com/vornicx/market-analysis.git — pushes work (2026-06-10: cleared a stale L4s4rt3 credential with `git credential reject`; current credential authenticates fine).
- User communicates in Spanish; respond in Spanish.
- Setup guide for plugging in API keys: SETUP.md; pre-flight validation: services/worker/scripts/check_setup.py.

**Status 2026-06-10:** Supabase schema applied successfully (after renaming reserved column `window` → `window_key`, commit 3a76a0c). DB is seeded in WC-only mode + dry_run. Pending: user creates auth user, fills `services/worker/.env` and `apps/web/.env.local`, sets `telegram_chat_id` on world_cup segment, then run `python scripts/check_setup.py` and first worker start. World Cup 2026 starts 2026-06-11 — time-sensitive.
