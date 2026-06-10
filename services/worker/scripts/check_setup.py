"""Pre-flight check: validates env vars and connectivity to Supabase, The Odds
API and Telegram WITHOUT spending any Odds API credits.

Run from services/worker:  python scripts/check_setup.py
"""
from __future__ import annotations

import sys

import httpx

sys.path.insert(0, ".")

OK = "  [OK]"
FAIL = "  [FAIL]"
results: list[bool] = []


def check(label: str, fn) -> None:
    try:
        detail = fn()
        print(f"{OK} {label}" + (f" — {detail}" if detail else ""))
        results.append(True)
    except Exception as exc:
        print(f"{FAIL} {label} — {exc}")
        results.append(False)


def env_loaded():
    from worker.settings import settings  # noqa: F401
    missing = [
        name
        for name, value in [
            ("SUPABASE_URL", settings.supabase_url),
            ("SUPABASE_SERVICE_ROLE_KEY", settings.supabase_service_role_key),
            ("ODDS_API_KEY", settings.odds_api_key),
            ("TELEGRAM_BOT_TOKEN", settings.telegram_bot_token),
        ]
        if not value or "YOUR_" in value or value.startswith("eyJ...") or value == "..."
    ]
    if missing:
        raise RuntimeError(f"placeholders or empty: {', '.join(missing)}")


def supabase_conn():
    from worker.persistence import get_db
    db = get_db()
    cfg = db.table("monitor_configs").select("*").eq("id", 1).single().execute().data
    mode = "WORLD_CUP_ONLY" if cfg["world_cup_only_mode"] else "NORMAL"
    return f"config loaded, mode={mode}, dry_run={cfg['dry_run']}"


def segments_have_chat_ids():
    from worker.persistence import get_db
    db = get_db()
    rows = db.table("monitor_segments").select("segment_key, telegram_chat_id").execute().data
    missing = [r["segment_key"] for r in rows if not r["telegram_chat_id"]]
    wc_missing = "world_cup" in missing
    if wc_missing:
        raise RuntimeError(
            "world_cup segment has no telegram_chat_id — set it: "
            "update monitor_segments set telegram_chat_id='-100...' where segment_key='world_cup';"
        )
    return "world_cup chat id set" + (f" (pending: {missing})" if missing else "")


def odds_api():
    from worker.settings import settings
    # /sports costs 0 credits
    resp = httpx.get(
        f"{settings.odds_api_base_url}/sports",
        params={"apiKey": settings.odds_api_key},
        timeout=15,
    )
    resp.raise_for_status()
    remaining = resp.headers.get("x-requests-remaining", "?")
    keys = {s["key"] for s in resp.json()}
    wc = "soccer_fifa_world_cup" in keys
    return f"credits remaining: {remaining}, world cup sport {'ACTIVE' if wc else 'not listed (check season)'}"


def telegram_bot():
    from worker.settings import settings
    resp = httpx.get(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe", timeout=15
    )
    body = resp.json()
    if not body.get("ok"):
        raise RuntimeError(body.get("description", "getMe failed"))
    return f"bot @{body['result']['username']}"


def telegram_chat_reachable():
    from worker.persistence import get_db
    from worker.settings import settings
    db = get_db()
    row = (
        db.table("monitor_segments")
        .select("telegram_chat_id")
        .eq("segment_key", "world_cup")
        .single()
        .execute()
        .data
    )
    chat_id = row["telegram_chat_id"]
    if not chat_id:
        raise RuntimeError("no chat id configured yet")
    resp = httpx.get(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/getChat",
        params={"chat_id": chat_id},
        timeout=15,
    )
    body = resp.json()
    if not body.get("ok"):
        raise RuntimeError(f"bot cannot see chat {chat_id}: {body.get('description')}")
    return f"chat '{body['result'].get('title', chat_id)}' reachable"


print("\nMarket Monitor — pre-flight check\n")
check("Env vars present (no placeholders)", env_loaded)
check("Supabase connection + config row", supabase_conn)
check("World Cup segment chat id", segments_have_chat_ids)
check("The Odds API key (0-credit call)", odds_api)
check("Telegram bot token", telegram_bot)
check("Telegram chat reachable by bot", telegram_chat_reachable)

print()
if all(results):
    print("All checks passed. Start the worker: python -m worker.main")
    print("Reminder: dry_run is ON by default — flip it from the dashboard to go live.")
    sys.exit(0)
print("Some checks failed — fix the items above and re-run.")
sys.exit(1)
