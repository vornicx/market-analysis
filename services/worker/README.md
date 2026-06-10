# Worker — football odds market monitor

Long-running Python service. Polls The Odds API on an adaptive, budget-governed
schedule, runs deterministic anomaly detectors, writes alerts to Supabase, and
delivers them to Telegram. **No betting functionality exists or should be added.**

## Run locally

```powershell
cd services/worker
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env   # fill in values
python -m worker.main
```

## Deploy

Any container host that sends SIGTERM on redeploy works (Railway, Fly.io, a VPS
with systemd). Do **not** deploy this to Vercel — it is a continuous loop, not a
request handler.

Dockerfile-free Railway setup: point the service at this directory with start
command `python -m worker.main`.

## Behavior config

Everything except secrets lives in the database (`monitor_configs`,
`monitor_segments`) and is re-read every cycle — dashboard toggles apply within
one `worker_poll_floor_seconds` interval without a restart. `dry_run` defaults
to true: nothing reaches Telegram until you flip it off deliberately.

## Detectors (all live)

| # | Module | Signal | Max points |
|---|---|---|---|
| D1 | `price_move` | unusual single-interval move | +25 |
| D2 | `divergence` | cross-book outlier vs consensus | +15 |
| D3 | `drift` | sustained directional movement | +20 |
| D4 | `sharp_leader` | sharp book leads, retail follows | +30 |
| D5 | `persistence_amp` | rapid move that held next poll | +15 |
| D6 | `reversal` | suppressor: retraced/fake move | −20 |
| D7 | `rarity` | move size vs trailing baseline | +15 |

Score = clamp(sum, 0, 100). Bands: high ≥ 80, medium ≥ 60, low < 60. A segment's
`min_alert_score` gates alerting; thresholds live per segment in
`monitor_segments.thresholds`.

## Tests

```powershell
pip install -e ".[dev]"
pytest -q          # 46 tests, no network/DB needed
ruff check worker tests
```

## Adding a detector

1. Create `worker/detectors/your_detector.py` implementing the `Detector` protocol.
2. Append an instance to `REGISTRY` in `worker/detectors/__init__.py`.
3. Add its threshold block to `monitor_segments.thresholds` (per segment).
