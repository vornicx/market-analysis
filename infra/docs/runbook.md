# Runbook

## Worker silent (heartbeat > 30 min on /status)
1. Check host (Railway/Fly) logs for crash loop.
2. `monitor_configs.global_pause` on? Then this is expected — banner shows PAUSED.
3. Supabase down/keys rotated? Worker logs will show auth errors; update env, redeploy.

## BUDGET_EXHAUSTED notice received
Daily cap hit. Polling resumes at UTC midnight automatically. If this happens
daily during normal operation, either reduce markets/bookmakers, raise
`daily_credit_cap` only if monthly headroom allows, or upgrade the Odds API tier.

## Telegram deliveries failing
- `telegram_deliveries.error` has the API description.
- 400 = formatting bug (HTML escaping) — fix, don't retry.
- 403 = bot kicked from chat or wrong chat id — re-add bot, verify `monitor_segments.telegram_chat_id`.
- 429 = slow down; check `max_alerts_per_cycle` behavior.

## Too many noisy alerts
1. Mark them `noise` on the dashboard (feedback page aggregates precision).
2. Raise the segment's `min_alert_score` first; only then tighten individual
   detector thresholds.
3. Verify `alert_suppression_minutes` isn't too low.

## Nothing is monitored despite flags on
Check the truth table: `world_cup_only_mode=true` with `world_cup_enabled=false`
monitors NOTHING by design — the status page shows a warning banner.

## Replaying an alert after threshold changes
`POST /api/alerts/{id}/replay` re-runs detectors on stored snapshots — zero
API credits spent.
