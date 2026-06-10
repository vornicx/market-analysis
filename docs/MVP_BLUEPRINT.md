# Football Market Monitor — MVP Blueprint

> Odds-movement monitoring with Telegram alerts. **Not an auto-betting system.** Humans make every betting decision. This document is the engineering source of truth for the MVP.

- Stack: Next.js (Vercel) + Supabase (Postgres/Auth/Realtime) + Python worker (Railway/Fly/VPS) + Telegram Bot API + optional LLM (Claude Haiku).
- Odds source: The Odds API (free tier, 500 credits/month assumed).
- Date written: 2026-06-10.

---

## SECTION 1 — PRODUCT MODEL

### What it is
An internal operations tool that continuously samples bookmaker odds for football matches, computes deterministic anomaly signals over the odds time series, scores them, and pushes decision-ready alerts to Telegram. A web dashboard (Vercel) is the control plane: configure segments, thresholds, bookmakers; review alerts and evidence; record feedback on alert quality.

### What it is NOT
- It does **not** place bets, hold funds, talk to bookmaker accounts, or automate wagers in any form.
- It does not predict match outcomes. It detects *market behavior*, not football outcomes.
- It is not a public product. MVP serves 1–5 trusted operators (admin users).
- The LLM is not a detector. It only annotates alerts that deterministic logic already produced.

### Who uses it
| Role | What they do |
|---|---|
| Operator (you) | Receives Telegram alerts, opens dashboard, decides whether to act manually at a bookmaker |
| Admin | Same as operator + edits config, toggles segments, manages thresholds, reviews worker health |

MVP: every user is an admin. Roles exist in the schema so this can tighten later.

### Football Monitoring vs World Cup Monitoring
Both live inside the single Football domain. They are **segments** of the same pipeline, not separate systems:

| Dimension | General Football | World Cup |
|---|---|---|
| Sport keys | configurable list (e.g. `soccer_epl`, `soccer_spain_la_liga`) | `soccer_fifa_world_cup` (+ qualifier keys if desired) |
| Enable flag | `football_enabled` | `world_cup_enabled` |
| Config | own thresholds, bookmakers, markets, polling | own thresholds, bookmakers, markets, polling |
| Alert label | `GENERAL FOOTBALL` | `WORLD CUP` (distinct emoji/prefix, optionally distinct Telegram chat) |
| Override | suppressed when `world_cup_only_mode=true` | unaffected by `world_cup_only_mode` |

`world_cup_only_mode=true` ⇒ worker monitors ONLY World Cup events, even if `football_enabled=true`. This is the "tournament lockdown" switch for when the entire API budget should serve the World Cup.

### Operational workflow (detection → alert → human decision)
1. Worker polls The Odds API on a budget-governed schedule for enabled segments.
2. Snapshots are normalized and persisted (`odds_snapshots`).
3. Feature extraction computes deltas/z-scores per (event, market, selection, bookmaker) against recent windows.
4. Deterministic detectors fire signals; the scorer combines them into `alert_score` (0–100).
5. If score ≥ segment's `min_alert_score` and not deduped/suppressed: an `alerts` row is written with full evidence.
6. (Optional) LLM annotates the alert with a one-paragraph classification — never blocks delivery.
7. Telegram message is sent to the segment's chat. Delivery recorded in `telegram_deliveries`.
8. Human opens the alert (Telegram or dashboard), inspects evidence (price path, cross-book table), and decides. Any bet is placed manually, outside this system.
9. Human records feedback (`useful / noise / late / wrong`) — fuel for threshold tuning.

---

## SECTION 2 — SYSTEM ARCHITECTURE

### Planes
| Plane | Component | Why |
|---|---|---|
| Control plane | Next.js on Vercel | Config CRUD, alert review, feedback, status. Request/response workloads — exactly what Vercel is good at. |
| Monitoring plane | Python worker (Railway/Fly.io/any VPS) | Long-running loop, in-memory state between polls, precise scheduling, retries. Must NOT live on Vercel. |
| Data plane | Supabase Postgres | Single source of truth: config, snapshots, alerts, audit. Realtime channels push new alerts to the dashboard. Auth for operators. |
| Alerting plane | Telegram Bot API (called from the worker) | Push delivery to phones; trivial API; per-segment chats. |
| LLM layer (optional) | Anthropic API (Claude Haiku) called from worker, post-detection | Cheap annotation. Failure-isolated: alert ships with or without it. |

### Why Vercel is control plane only
- Vercel functions are request-scoped and time-limited; a polling loop needs persistent state (last snapshot in memory, budget counters, backoff state) and sub-minute scheduling.
- **Vercel cron only runs on production deployments**, has minute-level granularity at best, no overlap protection, and no guarantee of execution continuity. Acceptable for "nudge" jobs (e.g. a daily digest), never for the monitor loop.
- The worker needs to outlive deployments and keep its own clock. A $5 Railway/Fly container does this trivially.

Vercel cron in this design is limited to one optional job: a daily health digest that checks `worker_runs` freshness and pings Telegram if the worker is silent (a watchdog *for* the worker, not part of it).

### ASCII diagram
```
                   ┌──────────────────────────┐
                   │   The Odds API (free)    │
                   └────────────▲─────────────┘
                                │ budget-governed polls
┌───────────────────────────────┴───────────────────────────────┐
│                  PYTHON WORKER  (Railway/Fly/VPS)             │
│  scheduler → poller → normalizer → feature extractor          │
│       → detectors → scorer → alert builder → dedupe           │
│       → [optional LLM annotator] → telegram sender            │
│  heartbeat / budget governor / retry / graceful shutdown      │
└──────┬──────────────────────────────────────┬─────────────────┘
       │ reads config, writes                 │ sendMessage
       │ snapshots/alerts/runs                ▼
┌──────▼───────────────┐            ┌──────────────────┐
│  SUPABASE (Postgres) │            │  TELEGRAM BOT    │
│  config • snapshots  │            │  general chat    │
│  alerts • evidence   │            │  world-cup chat  │
│  feedback • audit    │            └────────┬─────────┘
│  auth • realtime     │                     │ push
└──────▲───────────────┘                     ▼
       │ RLS-scoped reads/writes        ┌─────────┐
┌──────┴───────────────┐                │ HUMANS  │──manual decision,
│ NEXT.JS on VERCEL    │◀───────────────│ (1–5)   │  outside system
│ dashboard + config   │  open alert    └─────────┘
│ API routes + auth    │
│ (cron: watchdog only)│
└──────────────────────┘
```

### Data flow, end to end
`poll → raw JSON → normalize to (event, bookmaker, market, selection, price) rows → diff vs last snapshot → feature_windows upsert → detectors → score → alerts insert (idempotency key) → telegram send → telegram_deliveries insert → dashboard realtime update`.

Config flows the other way: dashboard writes `monitor_configs`/`monitor_segments`; worker re-reads config at the top of every cycle (no restart needed for toggle changes).

---

## SECTION 3 — MVP SCOPE

### Budget reality (the binding constraint)
The Odds API free tier ≈ **500 credits/month**. One request costs `markets × regions` credits. With 3 markets (`h2h,spreads,totals`) and 1 region (`eu`): **3 credits per poll per sport key**.

500 / 30 days ≈ 16.6 credits/day ⇒ **~5 polls/day per sport key** if one sport, or split across two.

### Default MVP scope (opinionated)
| Axis | Default | Rationale |
|---|---|---|
| Sport keys | 1 general league (`soccer_epl`) + `soccer_fifa_world_cup` when active | One liquid league proves the pipeline; WC segment exercised separately |
| Bookmakers | ≤ 6 from `eu` region incl. Pinnacle (sharp anchor), bet365, Unibet, William Hill, Marathonbet, Betsson | Cross-book signals need a sharp reference + retail books |
| Markets | `h2h`, `spreads`, `totals` | Matches Odds API schema; covers 1X2/handicap/OU |
| Regions | `eu` only | Each extra region multiplies credit cost |
| Polling | Event-window adaptive (below) | Flat polling wastes budget on dead hours |
| History | Snapshots retained 30 days, features 14 days | Enough for rarity baselines |

### Adaptive polling cadence (per enabled segment)
| Time to kickoff of nearest event | Cadence |
|---|---|
| > 48h | no polling (events refreshed 1×/day via cheap `/events` call) |
| 48–24h | every 8h |
| 24–6h | every 3h |
| 6–1h | every 60 min |
| < 1h | every 30 min (budget permitting) |
| in-play / finished | stop (MVP is pre-match only) |

Budget governor enforces a **hard daily credit cap** (`daily_credit_cap`, default 16) and a soft monthly cap (450, leaving 50 headroom). When the daily cap is hit, polling pauses until midnight UTC and a `BUDGET_EXHAUSTED` notice goes to Telegram once.

### Tradeoffs accepted
- Sparse sampling means "rapid move" resolution is 30–60 min, not seconds. Fine: the goal is decision-grade alerts, not HFT.
- One league limits signal variety, but multiplies sample depth per event — better baselines.
- Pre-match only: in-play monitoring is a different (paid) data problem; the schema supports it later via `events.status`.
- Paid tier ($30/mo ≈ 20k credits) is the obvious first upgrade; the architecture doesn't change, only `daily_credit_cap`.

---

## SECTION 4 — CONFIGURATION MODEL

Single global config row + one row per segment. Worker reads both each cycle. Exact fields:

### `monitor_configs` (singleton, `id=1`)
| Field | Type | Default | Meaning |
|---|---|---|---|
| `football_enabled` | bool | true | Master switch for general football segment |
| `world_cup_enabled` | bool | false | Master switch for WC segment |
| `world_cup_only_mode` | bool | false | If true: only WC monitored, general football ignored regardless of `football_enabled` |
| `global_pause` | bool | false | Kill switch: worker idles entirely (still heartbeats) |
| `dry_run` | bool | true | Full pipeline runs, alerts persisted, **Telegram not sent** (deliveries logged as `dry_run`) |
| `llm_enabled` | bool | false | Toggle LLM annotation layer |
| `daily_credit_cap` | int | 16 | Hard daily Odds API credit budget |
| `monthly_credit_cap` | int | 450 | Soft monthly budget |
| `odds_api_region` | text | `eu` | Region param for Odds API |
| `worker_poll_floor_seconds` | int | 300 | Worker never cycles faster than this |
| `alert_suppression_minutes` | int | 90 | Per (event, market, selection) re-alert window |
| `updated_by`, `updated_at` | uuid, timestamptz | — | Audit |

### `monitor_segments` (one row per segment: `general_football`, `world_cup`)
| Field | Type | Default (general / WC) | Meaning |
|---|---|---|---|
| `segment_key` | text PK | `general_football` / `world_cup` | Stable identifier |
| `display_label` | text | `GENERAL FOOTBALL` / `WORLD CUP` | Alert label |
| `sport_keys` | text[] | `{soccer_epl}` / `{soccer_fifa_world_cup}` | Odds API sport keys |
| `bookmaker_keys` | text[] | `{pinnacle,bet365,unibet,williamhill,marathonbet,betsson}` | Allowed books |
| `sharp_bookmaker_keys` | text[] | `{pinnacle}` | Books treated as "sharp leaders" |
| `market_keys` | text[] | `{h2h,spreads,totals}` | Markets to fetch/score |
| `polling_profile` | jsonb | the cadence table above as `{gt48h:0, h48_24:480, h24_6:180, h6_1:60, lt1h:30}` (minutes; 0 = off) | Adaptive cadence |
| `min_alert_score` | int | 55 / 50 | Alert floor (WC slightly more sensitive) |
| `thresholds` | jsonb | see Section 5 defaults | Per-detector thresholds; WC can override any key |
| `telegram_chat_id` | text | per segment | Destination chat/channel |
| `enabled` | bool (derived check) | — | Effective enablement computed by worker from flags (see Section 6 truth table), but a per-segment `enabled` column exists as an extra manual gate |
| `updated_by`, `updated_at` | | | Audit |

Telegram recipients: one `telegram_chat_id` per segment (separate channels keep WC alerts physically separable). The bot token is worker-side env (`TELEGRAM_BOT_TOKEN`), never in DB.

Resolution rules (worker, every cycle):
```
if global_pause: idle
active_segments = []
if world_cup_only_mode:
    if world_cup_enabled and seg(world_cup).enabled: active_segments=[world_cup]
else:
    if football_enabled and seg(general).enabled: += general_football
    if world_cup_enabled and seg(world_cup).enabled: += world_cup
```

---

## SECTION 5 — DETECTION ENGINE

All detectors operate on **implied probability** (`p = 1/decimal_odds`), not raw prices — moves are comparable across odds ranges. Each detector returns `(fired: bool, weight_points: float, evidence: dict)`.

Per-selection state available to detectors (from `feature_windows`):
`p_now`, `p_prev` (last poll), `p_open` (first snapshot), deltas over 1/3/6/24h lookbacks, per-book series, consensus median across books, trailing 14-day move-size distribution per market type.

### D1 — PRICE_MOVE (unusual single-interval move)
- **Data:** `Δp = p_now − p_prev` per (book, selection).
- **Compute:** absolute Δp and Δp z-score vs segment's trailing move distribution.
- **Threshold (default `thresholds.price_move`):** `abs_dp_min: 0.03` (3 pts of implied prob) OR `z_min: 3.0`.
- **Points:** up to **25** (linear from threshold to 2× threshold).
- **FP risks:** team news (lineups ~1h pre-kickoff), normal liquidity-driven repricing on small books. Mitigation: require ≥2 books moved OR sharp book among movers for full points; single-retail-book moves get 50% points.

### D2 — CROSS_BOOK_DIVERGENCE
- **Data:** all books' `p_now` for the same selection.
- **Compute:** `div = p_book − median(p_all_books)`; flag max divergent book.
- **Threshold:** `divergence_min: 0.04`. Direction matters: a book *lagging* a confirmed move is steam-chasing material; a book *leading* is the interesting one.
- **Points:** up to **15**.
- **FP risks:** stale/suspended lines at one book (Odds API `last_update` per book — discard books with stale `last_update` > 2× poll interval); structural margin differences (mitigated by de-vigging: normalize p's to sum to 1 within a market before comparing).

### D3 — SUSTAINED_DRIFT
- **Data:** last N polls (default 3) of consensus median.
- **Compute:** same-sign Δp for ≥ `drift_polls_min: 3` consecutive polls, cumulative `drift_cum_min: 0.04`.
- **Points:** up to **20**.
- **FP risks:** slow natural drift toward kickoff (favorites often shorten). Mitigation: compare against per-league average pre-kickoff drift curve once data exists; MVP just uses the cumulative threshold.

### D4 — SHARP_LEADER (whale/sharp heuristic)
- **Data:** per-book time series; `sharp_bookmaker_keys`.
- **Compute:** sharp book moved ≥ `sharp_dp_min: 0.025` in poll T, AND ≥ `follower_count_min: 2` retail books moved same direction by poll T+1. (With sparse polling, "T+1" = next snapshot.)
- **Points:** up to **30** — the strongest signal. We never see actual stakes; sharp-book-leads-retail-follows is the best free proxy for informed money.
- **FP risks:** Pinnacle reacting to public news simultaneously with retail (looks like leading); Odds API update timestamps coarse. Mitigation: use per-book `last_update` ordering within the snapshot, not just poll order.

### D5 — RAPID_PERSISTENT (rapid move with persistence)
- **Data:** D1 fire + the following snapshot.
- **Compute:** D1-size move that retains ≥ `persistence_ratio_min: 0.7` of its magnitude at the next poll.
- **Points:** up to **15** (added on the *confirming* poll — this is a second-look amplifier).
- **FP risks:** none new; it strictly reduces noise vs D1 alone, at the cost of one-poll latency.

### D6 — REVERSAL (fake move detector — a *suppressor*)
- **Compute:** move ≥ threshold then ≥ `reversal_ratio: 0.6` retraced within `reversal_window_polls: 2`.
- **Effect:** **−20 points** applied to any pending alert on that selection, and emits an informational `REVERSAL` tag if an alert already fired (dashboard annotation; optional low-priority Telegram note, off by default).
- **FP risks:** genuine two-way action looks like reversal; acceptable — reversal alerts are informational only.

### D7 — RARITY (vs recent baseline)
- **Data:** trailing 14-day distribution of |Δp| per (segment, market_key).
- **Compute:** percentile of current move; fires at `rarity_pctile_min: 97`.
- **Points:** up to **15**.
- **FP risks:** cold start (first 2 weeks have thin baselines) — detector is automatically inert until ≥ `rarity_min_samples: 300` historical moves exist for the bucket.

### Scoring model
```
raw = D1 + D2 + D3 + D4 + D5 + D7 − D6_penalty        # max 120 before clamp
alert_score = clamp(round(raw), 0, 100)
confidence_band = high   if score ≥ 80
                = medium if score ≥ 60
                = low    otherwise
alert_type = dominant detector:
  SHARP_MOVE (D4 dominant) | STEAM_MOVE (D3/D5) | PRICE_SPIKE (D1)
  | BOOK_DIVERGENCE (D2) | RARE_MOVE (D7) | REVERSAL (info-only)
alert_reason_summary = template, e.g.
  "Pinnacle shortened Real Madrid ML 2.10→1.92 (Δp +4.5pts); 3 books followed within 1 poll; move is 99th pctile for h2h."
evidence payload (jsonb) = { detector outputs, per-book price path (last 6 polls),
  consensus series, thresholds used, config snapshot hash }
```
Alert emitted iff `alert_score ≥ segment.min_alert_score` AND passes dedupe/suppression (Section 15).

---

## SECTION 6 — WORLD CUP SEGMENT

- **Tagging:** WC matches are simply events fetched under sport key `soccer_fifa_world_cup`. Every event row carries `segment_key`, stamped at ingest from the segment that fetched it. No fuzzy competition-name matching — the sport key IS the tag. (Future tournaments = new segment rows with their own sport keys; zero code changes.)
- **`world_cup_enabled`:** gates whether the WC segment participates in cycle planning at all (no event refresh, no polls, no credits spent).
- **`world_cup_only_mode` truth table:**

| football_enabled | world_cup_enabled | world_cup_only_mode | Monitored |
|---|---|---|---|
| T | T | F | both |
| T | F | F | general only |
| T | T | **T** | **WC only** |
| F | T | T | WC only |
| T | F | T | **nothing** (misconfig — worker logs `WARN` + dashboard status banner) |

- **Worker filtering:** the cycle planner iterates `active_segments` only; each segment polls its own `sport_keys` with its own `bookmaker_keys`/`market_keys` and budget share. In only-mode, 100% of the daily credit cap goes to WC. When both run, default split 50/50, overridable via `polling_profile`.
- **Alert labeling:** every alert row has `segment_key`; Telegram messages render `display_label` (`🏆 WORLD CUP` vs `⚽ GENERAL FOOTBALL`) and go to the segment's own `telegram_chat_id`. Dashboard alert list has a segment filter chip.
- **Threshold independence:** `monitor_segments.thresholds` and `min_alert_score` are per-segment. WC defaults: `min_alert_score: 50`, `price_move.abs_dp_min: 0.025` — more sensitive, because WC markets are high-liquidity and news-dense, and during the tournament we *want* more eyes-on alerts. Rarity baselines are also per-segment, so WC moves aren't judged against EPL noise floors.

---

## SECTION 7 — DATABASE SCHEMA

Full DDL lives in `infra/sql/0001_init.sql`. Summary (PK `id uuid default gen_random_uuid()` unless noted; all tables have `created_at timestamptz default now()`):

| Table | Key fields | Indexes / notes |
|---|---|---|
| `users` | mirrors `auth.users`: `id uuid PK (FK auth.users)`, `email`, `role text check in ('admin','viewer')`, `display_name` | Trigger on auth signup. Retention: forever. |
| `monitor_configs` | singleton (`id int PK check (id=1)`) — fields per Section 4 | Updated only via API routes (audited). |
| `monitor_segments` | `segment_key text PK` — fields per Section 4 | |
| `competitions` | `sport_key text unique`, `title`, `segment_key FK` | Seeded; tiny. |
| `events` | `provider_event_id text`, `sport_key`, `segment_key`, `home_team`, `away_team`, `commence_time timestamptz`, `status text check in ('upcoming','live','finished','cancelled')` | `unique(provider_event_id, sport_key)` = **idempotency key** for ingest (upsert). idx on `(segment_key, commence_time)`. Retention: 90d after commence. |
| `bookmakers` | `bookmaker_key text unique`, `title`, `is_sharp bool` | Seeded. |
| `markets` | `market_key text unique` (`h2h`,`spreads`,`totals`), `description` | Seeded. |
| `selections` | `event_id FK`, `market_key FK`, `name` (team/Draw/Over/Under), `line numeric null` (handicap/total) | `unique(event_id, market_key, name, coalesce(line,0))`. |
| `odds_snapshots` | `event_id FK`, `bookmaker_key`, `market_key`, `selection_id FK`, `price_decimal numeric(8,3)`, `implied_prob numeric(6,5)`, `book_last_update timestamptz`, `polled_at timestamptz`, `poll_cycle_id uuid` | **Append-only.** idx `(selection_id, bookmaker_key, polled_at desc)`. Idempotency: `unique(selection_id, bookmaker_key, poll_cycle_id)`. Retention: 30d (cron `delete where polled_at < now()-'30 days'`). |
| `feature_windows` | `selection_id FK`, `bookmaker_key null` (null = consensus), `window text` (`poll`,`1h`,`6h`,`24h`), `dp numeric`, `z numeric`, `pctile numeric`, `computed_at` | Upsert on `(selection_id, bookmaker_key, window)`. Retention 14d. |
| `alerts` | `segment_key`, `event_id FK`, `market_key`, `selection_id FK`, `alert_type text`, `alert_score int`, `confidence_band text`, `reason_summary text`, `status text check in ('new','acknowledged','dismissed','replayed')`, `dedupe_key text` | **`unique(dedupe_key)`** where `dedupe_key = sha1(segment|event|market|selection|direction|time_bucket(suppression_window))` — insert-or-skip makes alerting idempotent across worker restarts. idx `(segment_key, created_at desc)`. Retention: forever (it's the product's memory). |
| `alert_evidence` | `alert_id FK unique`, `payload jsonb` (detector outputs, price paths, thresholds snapshot) | 1:1; separate table keeps `alerts` rows light for list queries. |
| `alert_feedback` | `alert_id FK`, `user_id FK`, `verdict text check in ('useful','noise','late','wrong')`, `note text` | `unique(alert_id, user_id)`. |
| `llm_analyses` | `alert_id FK unique`, `classification text`, `summary text`, `confidence text`, `model`, `tokens_in int`, `tokens_out int`, `raw jsonb`, `status text ('ok','failed','skipped')` | |
| `telegram_deliveries` | `alert_id FK`, `chat_id`, `message_id bigint null`, `status text ('sent','failed','dry_run','suppressed')`, `error text`, `attempts int` | Idempotency: `unique(alert_id, chat_id)` — one delivery per alert per chat; retries update `attempts`. |
| `worker_runs` | `started_at`, `finished_at`, `cycle_type text ('poll','event_refresh','idle')`, `segments text[]`, `credits_used int`, `snapshots_written int`, `alerts_created int`, `status text ('ok','error','partial')`, `error text` | Heartbeat = latest row. Retention 30d. idx `(started_at desc)`. |
| `audit_logs` | `actor_id uuid null` (null = worker), `action text`, `entity text`, `entity_id text`, `before jsonb`, `after jsonb` | Written by API routes on every config mutation and by worker on budget/pause state changes. Retention: forever. |

### RLS strategy
- RLS **enabled on every table**.
- Authenticated users with `role='admin'`: full select; insert on `alert_feedback`; update on `alerts.status`. Config mutations go **only** through Next.js API routes using the service-role key after an explicit admin check (so every change is audited) — no direct table UPDATE policy for config tables.
- `viewer` role (future): select-only on alerts/events/status.
- Worker uses the **service-role key** (bypasses RLS) from a non-Vercel environment; key never ships to the browser.
- `anon`: no access to anything.

### Auditability requirements
Every config mutation produces an `audit_logs` row with before/after JSON and actor. Worker state transitions (pause honored, budget exhausted, dry-run toggled effective) also log. Alert lifecycle is reconstructible from `alerts` + `telegram_deliveries` + `alert_feedback` timestamps.

---

## SECTION 8 — WEB DASHBOARD

Next.js App Router, Tailwind, server components for reads + route handlers for writes, Supabase Realtime for live alerts. Utilitarian: dense tables, status pills, no marketing chrome.

| Page | Route | Purpose / key components | Filters | Actions | Loading / empty | Realtime |
|---|---|---|---|---|---|---|
| Login | `/login` | Supabase email+password (magic link optional). Single card form. | — | sign in | spinner on submit | — |
| Overview | `/` | 4 stat cards (alerts 24h, worker last-seen pill, credits used today/cap, active segments), latest-10 alerts table, mode banner (DRY RUN / PAUSED / WC-ONLY in loud colors) | — | quick links | skeleton cards | new alerts prepend via Realtime on `alerts` |
| Football settings | `/settings/football` | form bound to `monitor_segments['general_football']` + global flags it owns: `football_enabled` toggle; sport keys, bookmakers (checkbox grid), markets, polling profile editor, threshold JSON editor with validation, min score slider, chat id | — | save (PATCH → audit) | form skeleton | — |
| World Cup settings | `/settings/world-cup` | same form for `world_cup` + `world_cup_enabled`, `world_cup_only_mode` toggles with an inline warning when only-mode suppresses general football | — | save | form skeleton | — |
| Alerts list | `/alerts` | paged table: time, segment chip, match, market, selection, type, score (colored), band, status, feedback summary | segment, type, band, status, date range, min score | row click → detail; bulk acknowledge | table skeleton; empty: "No alerts match — lower filters or check worker status" | prepend new rows |
| Alert detail | `/alerts/[id]` | header (match, score badge, band), reason summary, evidence: per-book price-path table + sparkline, cross-book table at trigger, detector breakdown (points per detector), LLM card (if any), delivery log, feedback widget | — | acknowledge, dismiss, submit feedback, **replay** (admin) | section skeletons | feedback/LLM card updates live |
| Feedback review | `/feedback` | table of alerts with feedback verdict vs score/band; precision-by-band summary cards | verdict, segment, band, date | export CSV | skeleton | — |
| System status | `/status` | worker heartbeat (last run, age, status), credits today/month vs caps with progress bars, last 50 `worker_runs` table, current resolved mode (the truth-table outcome), Telegram delivery success rate 24h | run status | "force config reload" hint (worker reads each cycle anyway) | skeleton | heartbeat row updates |
| Audit/history | `/audit` | `audit_logs` table: time, actor, action, entity, before→after diff viewer | actor, entity, action, date | — | skeleton; empty: "No changes recorded" | — |

All write actions show optimistic pending state + toast on confirm/error. Admin check on every mutating route.

---

## SECTION 9 — TELEGRAM ALERTS

**Opinion: use `parse_mode=HTML`, not MarkdownV2.** MarkdownV2 requires escaping 18 characters (`_ * [ ] ( ) ~ \` > # + - = | { } . !`) including inside team names ("Atlético", "1. FC Köln", "Brighton & Hove" — `&` breaks HTML too but only 3 entities need escaping: `& < >`). HTML escaping is mechanical and safe; MarkdownV2 escaping bugs silently kill messages with a 400. The worker ships an `escape_html()` helper applied to every dynamic string.

### Compact format (default; high band uses expanded)
```
⚽ GENERAL FOOTBALL · SHARP MOVE · 82/100 (HIGH)
Arsenal vs Chelsea — EPL
h2h · Arsenal ML
2.10 → 1.92 (Δp +4.5pts) · Pinnacle led, 3 books followed
🕑 2026-06-10 14:32 UTC · ko in 5h 12m
🔗 dash.example.com/alerts/9f3a…
```

### Expanded format (band=high, or `/expand` future)
```
🏆 WORLD CUP · STEAM MOVE · 88/100 (HIGH)

Brazil vs France — FIFA World Cup, Semi-final
Market: totals · Over 2.5
Pattern: sustained drift + sharp leader

Consensus: 1.95 → 1.78 over 3 polls (Δp +4.9pts, 99th pctile)
Pinnacle:  1.93 → 1.75 (led at 13:02 UTC)
bet365:    1.95 → 1.80   Unibet: 1.97 → 1.82
No reversal after 1 poll (persistence 0.94)

Score 88 · confidence HIGH · detectors: D4(28) D3(18) D1(20) D7(14) D5(8)
🕑 2026-06-10 13:35 UTC · kickoff in 3h 40m
🔗 dash.example.com/alerts/7bc1…
```
General-football compact example shown above; WC alerts always carry the `🏆 WORLD CUP` prefix and route to the WC chat — separable by chat *and* by label.

### Delivery rules
- **Dedupe:** `alerts.dedupe_key` unique constraint (Section 7) — a key includes a time bucket sized by `alert_suppression_minutes` (90 min), so the same (event, market, selection, direction) can't alert twice inside the window. DB-level, so it survives worker restarts.
- **Anti-spam:** max `max_alerts_per_event_per_day: 5` and `max_alerts_per_cycle: 8` (config-able); overflow alerts are persisted with `telegram_deliveries.status='suppressed'` and visible on the dashboard.
- **Resend/escalation:** if a suppressed-window selection *upgrades a band* (medium→high), one escalation message is allowed, prefixed `⬆ ESCALATION`. Failed sends retry 3× with exponential backoff (2s/8s/30s); permanent failure logged and surfaced on `/status`.
- **Formatting pitfalls:** 4096-char message limit (expanded format budgeted < 1500); escape `& < >` everywhere; don't put `<` in team-name comparisons; disable link previews (`disable_web_page_preview=true`); one message per alert — never edit-in-place for MVP.

---

## SECTION 10 — LLM ANALYSIS LAYER

Position in pipeline: **after** alert insert, **before** Telegram send, with a 6-second budget — if it misses, the alert ships without annotation and `llm_analyses.status='skipped'`. Never gates, never scores, never suppresses.

- Model: `claude-haiku-4-5` (cheap, fast). `max_tokens: 300`, `temperature: 0`.
- Input: a compacted evidence digest (NOT raw snapshots): ~400 tokens.

### Prompt (exact)
```
System:
You are an odds-market analyst assistant. You receive a pre-computed anomaly
report from a deterministic detection system for a pre-match football betting
market. Your job is ONLY to classify and summarize. You must not invent facts,
news, injuries, or numbers not present in the input. If evidence is ambiguous,
classify as "needs human review". Output ONLY valid JSON matching the schema.

User:
ANOMALY REPORT
segment: {segment_label}
match: {home} vs {away} ({competition}, kickoff {kickoff_utc})
market: {market_key} / selection: {selection_name} {line}
detectors_fired: {detector_summary e.g. "SHARP_LEADER(28pts): pinnacle led -0.18
price, 3 followers; SUSTAINED_DRIFT(18pts): 3 polls same direction cum dp 4.9"}
price_path_consensus: {compact series e.g. "1.95@-6h 1.91@-3h 1.84@-1h 1.78@now"}
cross_book_now: {book:price pairs}
score: {score}/100 band {band}
Respond with JSON only.
```

### JSON schema (validated worker-side with `jsonschema`)
```json
{
  "type": "object",
  "required": ["classification", "summary", "confidence", "caveats"],
  "additionalProperties": false,
  "properties": {
    "classification": {"enum": [
      "possible_sharp_move", "possible_market_correction",
      "possible_news_driven_move", "possible_noise", "needs_human_review"]},
    "summary": {"type": "string", "maxLength": 280},
    "confidence": {"enum": ["low", "medium", "high"]},
    "caveats": {"type": "array", "items": {"type": "string"}, "maxItems": 3}
  }
}
```

- **Token minimization:** digest not raw data; no chat history; one-shot; `max_tokens` clamp; only band ≥ medium alerts annotated (configurable `llm_min_band`).
- **Hallucination safeguards:** temperature 0; "do not invent" instruction; schema validation with one retry on invalid JSON then `failed`; summary length clamp; the Telegram template renders the LLM text under an explicit `🤖 LLM (advisory):` label so humans never confuse it with measured evidence; classification can never alter `alert_score`.
- **Fallback:** API error/timeout/invalid-JSON ⇒ alert ships unannotated; `llm_analyses.status` records why; dashboard alert detail shows "LLM unavailable".

---

## SECTION 11 — API AND ROUTES

All under `apps/web/src/app/api`. Auth: Supabase session cookie; every mutating route verifies `users.role='admin'`. Worker-facing routes authenticate with `x-worker-token` shared secret (env `WORKER_API_TOKEN`). Errors uniformly:
```json
{ "error": { "code": "FORBIDDEN", "message": "Admin role required" } }
```
Codes: `UNAUTHENTICATED` 401, `FORBIDDEN` 403, `NOT_FOUND` 404, `VALIDATION` 422, `CONFLICT` 409, `INTERNAL` 500.

| Route | Method | Purpose | Notes |
|---|---|---|---|
| `/api/config` | GET | global config + both segments | admin |
| `/api/config` | PATCH | partial update global flags | zod-validated; writes audit row |
| `/api/config/segments/[segmentKey]` | PATCH | update one segment | validates thresholds JSON shape |
| `/api/config/toggle` | POST | body `{"flag":"football_enabled"\|"world_cup_enabled"\|"world_cup_only_mode"\|"global_pause"\|"dry_run","value":bool}` | dedicated route so toggles are one-click + audited individually |
| `/api/alerts` | GET | paged list; query `segment,type,band,status,minScore,from,to,cursor` | |
| `/api/alerts/[id]` | GET | alert + evidence + llm + deliveries + feedback | |
| `/api/alerts/[id]` | PATCH | `{"status":"acknowledged"\|"dismissed"}` | |
| `/api/alerts/[id]/feedback` | POST | `{"verdict":"useful","note":"..."}` | upsert per user |
| `/api/alerts/[id]/replay` | POST | re-run detectors on stored snapshots for this alert's selection; creates a `replayed` alert linked via evidence | admin; for tuning thresholds against history |
| `/api/worker/heartbeat` | POST | worker posts run summaries (also written directly to DB; route exists for environments where worker can't reach DB directly — MVP: worker writes DB, route optional) | `x-worker-token` |
| `/api/worker/status` | GET | latest run, credits used, resolved mode | dashboard + watchdog |
| `/api/health` | GET | `{ ok: true, db: true }` | unauthenticated, for uptime checks |

Example — toggle:
```
POST /api/config/toggle
{ "flag": "world_cup_only_mode", "value": true }
→ 200 { "config": { ...updated config... }, "resolvedMode": "WORLD_CUP_ONLY" }
→ 422 { "error": { "code": "VALIDATION", "message": "Unknown flag 'wc_mode'" } }
```

---

## SECTION 12 — PYTHON WORKER DESIGN

```
services/worker/
  pyproject.toml
  .env.example
  worker/
    __init__.py
    main.py            # entrypoint: loop, signal handling
    settings.py        # env vars (pydantic-settings)
    config.py          # fetch monitor_configs + segments from Supabase; resolve modes
    budget.py          # credit governor (daily/monthly caps, persisted via worker_runs)
    scheduler.py       # adaptive cadence: which segments are due this cycle
    odds_client.py     # The Odds API client (httpx, retries, credit accounting)
    normalize.py       # raw JSON -> typed Snapshot rows (implied prob, de-vig)
    persistence.py     # supabase-py upserts: events, selections, snapshots, runs
    features.py        # delta/z/percentile computation per selection
    detectors/
      __init__.py      # registry
      base.py          # Detector protocol: detect(ctx) -> DetectorResult
      price_move.py    # D1 (reference implementation)
      divergence.py    # D2 (stub)
      drift.py         # D3 (stub)
      sharp_leader.py  # D4 (stub)
      persistence_amp.py  # D5 (stub)
      reversal.py      # D6 (stub)
      rarity.py        # D7 (stub)
    scoring.py         # combine detector results -> score/band/type/summary
    alerting.py        # dedupe key, suppression, alerts+evidence insert
    llm.py             # optional annotator (anthropic), schema validation, timeout
    telegram.py        # HTML escaping, send with retry, delivery logging
    models.py          # dataclasses/pydantic: Snapshot, FeatureCtx, DetectorResult, Alert
  tests/
```

### Main loop (pseudocode)
```python
def run():
    install_sigterm_handler()           # sets shutdown_event
    while not shutdown_event.is_set():
        run_id = persistence.start_run()
        try:
            cfg = config.load()         # fresh every cycle — toggles apply without restart
            if cfg.global_pause:
                persistence.finish_run(run_id, "idle"); sleep_until_next(cfg); continue
            segments = config.resolve_active_segments(cfg)   # Section 4/6 truth table
            due = scheduler.due_segments(segments, events_cache, budget)
            for seg in due:
                if budget.exhausted(): break
                raw = odds_client.fetch_odds(seg)            # counts credits
                snaps = normalize.to_snapshots(raw, seg)
                persistence.upsert_events_selections_snapshots(snaps)  # idempotent
                ctxs = features.compute(snaps, lookback_store)
                for ctx in ctxs:
                    results = [d.detect(ctx) for d in detectors.for_segment(seg)]
                    scored = scoring.assemble(results, seg)
                    if scored and scored.score >= seg.min_alert_score:
                        alert = alerting.create(scored, ctx, seg)    # None if deduped
                        if alert:
                            if cfg.llm_enabled: llm.annotate(alert, timeout=6)
                            telegram.deliver(alert, seg, dry_run=cfg.dry_run)
            persistence.finish_run(run_id, "ok", stats)
        except Exception as e:
            log.exception(e); persistence.finish_run(run_id, "error", err=str(e))
        sleep_interruptible(cfg.worker_poll_floor_seconds)
```

- **Config loading:** Supabase REST via service key; cached only within a cycle.
- **Event filtering:** daily cheap `/v4/sports/{key}/events` refresh per active segment (low/zero credit cost) keeps `events` current; odds polls request only sport keys with events inside the 48h window.
- **Idempotent persistence:** every write is an upsert on the natural keys from Section 7; a crashed cycle re-run cannot duplicate snapshots (poll_cycle_id) or alerts (dedupe_key).
- **Retries:** httpx transport retries (3, backoff) for Odds API/Supabase/Telegram; 429 from Odds API ⇒ treat as budget signal, back off to next window.
- **Graceful shutdown:** SIGTERM sets event; loop finishes current segment, writes `worker_runs` row, exits 0 — safe for platform redeploys.
- **Observability:** structured JSON logs (stdout, picked up by host); every cycle = `worker_runs` row (the heartbeat); credits/snapshots/alerts counters per run; optional Sentry DSN env.
- **Mode handling:** exactly the truth table in Section 6, implemented once in `config.resolve_active_segments()` with unit tests over all 8 flag combinations.

---

## SECTION 13 — MONOREPO STRUCTURE

```
market-monitor/
  package.json            # npm workspaces root, shared scripts
  .gitignore
  README.md               # setup, deploy, runbook
  docs/
    MVP_BLUEPRINT.md      # this document
  apps/
    web/                  # Next.js dashboard + control-plane API (Vercel)
      package.json
      next.config.mjs
      tsconfig.json
      .env.example
      src/
        app/              # routes per Section 8 + /api per Section 11
        lib/
          supabase/       # server.ts (anon+cookies), admin.ts (service role)
          auth.ts         # requireAdmin()
          api.ts          # error envelope helpers
        components/       # tables, badges, toggles
  packages/
    shared/               # typed contracts shared by web (and mirrored in worker models.py)
      package.json
      src/
        types.ts          # MonitorConfig, MonitorSegment, Alert, AlertEvidence...
        constants.ts      # segment keys, alert types, bands, error codes
  services/
    worker/               # Python monitoring service (Section 12) — deployed off-Vercel
  infra/
    sql/
      0001_init.sql       # full schema + RLS + seeds
    docs/
      runbook.md          # ops: budget exhausted, worker silent, telegram failures
```
Notes: TS types in `packages/shared` are the canonical contract; the worker mirrors them in `models.py` (no codegen for MVP — one file each, kept in sync by convention and a checklist in PR template). `infra/sql` migrations are applied with the Supabase CLI (`supabase db push`) or psql.

---

## SECTION 14 — INITIAL SCAFFOLDING

Generated in this repository — see the actual files:
- Root: `package.json`, `.gitignore`, `README.md`
- `apps/web`: Next.js skeleton, Supabase server/admin clients, login, overview, settings pages (football + world cup), alerts list/detail, status page, API routes (`config`, `config/toggle`, `alerts`, `alerts/[id]`, `alerts/[id]/feedback`, `health`), `.env.example`
- `packages/shared`: `types.ts`, `constants.ts`
- `services/worker`: full skeleton per Section 12 with working config loader, Odds API client, normalizer, D1 `price_move` detector implemented end-to-end, scorer, Telegram sender with HTML escaping + retry, dedupe-aware alert writer, `.env.example`
- `infra/sql/0001_init.sql`: complete schema, RLS policies, seed rows (segments, config singleton, bookmakers, markets)

---

## SECTION 15 — OPERATIONAL SAFETY

| Mechanism | Implementation |
|---|---|
| Dry-run | `monitor_configs.dry_run` (default **true** — you must consciously go live). Pipeline runs fully; deliveries logged `dry_run`; dashboard banner. |
| Pause switch | `global_pause`: worker idles but heartbeats, so pause ≠ dead. Per-segment `enabled` for finer control. |
| Alert dedupe | DB unique `dedupe_key` (event, market, selection, direction, time bucket). |
| Suppression windows | `alert_suppression_minutes` (90) per selection+direction; band-upgrade escalation is the only bypass. |
| API budgeting | `budget.py` reads credits used from today's `worker_runs`; hard daily cap, soft monthly cap; Odds API response headers (`x-requests-remaining`) reconciled each call. |
| Quota exhausted fallback | stop polling, single `BUDGET_EXHAUSTED` Telegram notice, status banner, resume at UTC midnight; event-refresh (cheap) continues so the schedule stays warm. |
| Rate limiting | worker floor `worker_poll_floor_seconds`; Telegram ≤ 1 msg/sec, ≤ `max_alerts_per_cycle`; API routes rely on Vercel + admin-only auth (tiny user base). |
| Worker heartbeat | every cycle writes `worker_runs`; dashboard shows age; optional Vercel cron watchdog pings Telegram if heartbeat > 30 min stale. |
| Error logging | structured JSON logs + `worker_runs.error` + optional Sentry. |
| Audit logs | every config mutation + worker state transitions (Section 7). |
| Manual replay | `/api/alerts/[id]/replay` re-runs detectors over stored snapshots — threshold tuning without spending credits. |

---

## SECTION 16 — DEVELOPMENT ROADMAP

### 7-day MVP
- D1: repo, schema applied to Supabase, seeds, env plumbing.
- D2: worker skeleton — config loader, Odds API client, normalizer, snapshots persisting (dry data flowing).
- D3: features + D1 PRICE_MOVE + scorer + alerts table writes (dry_run).
- D4: Telegram sender + dedupe/suppression; first real dry-run alerts reviewed.
- D5: web — auth, overview, alerts list/detail (read-only).
- D6: settings pages + toggle API + audit; truth-table unit tests.
- D7: deploy (Vercel + Railway), watchdog, go live on EPL in dry-run; flip dry_run off after reviewing a day of output.

### 14-day stabilization
D2/D3/D4 detectors (divergence, drift, sharp leader); rarity data accumulation; feedback page; status page polish; replay endpoint; threshold tuning from feedback; budget governor hardening against header drift.

### 30-day hardening
D5/D6/D7 detectors live; LLM layer behind flag; WC segment dress rehearsal (enable on qualifiers/friendlies sport keys); retention crons; Sentry; runbook complete; consider paid Odds API tier; precision-by-band review and threshold lockdown for the World Cup.

### Ship first / defer
**First:** schema, worker pipeline with ONE detector, Telegram, dry-run, dashboard read views, toggles. **Defer:** LLM, replay UI polish, viewer role, extra leagues, more channels (email/Discord), in-play, paid tier.

### Risks
- **Technical #1:** free-tier credit math makes the system feel blind (sparse polling hides fast moves). Mitigation: adaptive windows now; $30 tier is the real fix and changes nothing architecturally.
- **Technical #2:** Odds API book coverage/`last_update` staleness corrupting divergence/sharp signals. Mitigation: staleness filter, de-vig, Pinnacle anchor.
- **Product #1:** alert precision — too much noise and operators mute the channel (product death). Mitigation: dry-run first, feedback loop, conservative `min_alert_score`, anti-spam caps.
- **Product #2:** sparse pre-match-only signals may rarely be actionable in time. Validation metric below tells us within 30 days.

### Validation metrics
- Precision proxy: % alerts marked `useful` (target ≥ 40% by day 30; high band ≥ 60%).
- Latency: alert `created_at` − move's first snapshot (target ≤ 1 polling interval).
- Coverage: % of post-hoc-visible big closing-line moves (≥ 5 pts implied) that alerted.
- Ops: worker uptime ≥ 99%, zero duplicate Telegram messages, budget never hard-exceeded.
