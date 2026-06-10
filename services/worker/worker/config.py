"""Load behavior config from Supabase and resolve segment activation."""
from __future__ import annotations

import logging

from supabase import Client

from .models import GlobalConfig, Segment

log = logging.getLogger(__name__)


def load_config(db: Client) -> tuple[GlobalConfig, dict[str, Segment]]:
    cfg_row = db.table("monitor_configs").select("*").eq("id", 1).single().execute().data
    seg_rows = db.table("monitor_segments").select("*").execute().data
    config = GlobalConfig.model_validate(cfg_row)
    segments = {r["segment_key"]: Segment.model_validate(r) for r in seg_rows}
    return config, segments


def resolve_active_segments(
    config: GlobalConfig, segments: dict[str, Segment]
) -> list[Segment]:
    """The single source of truth for the mode truth table (see blueprint §6)."""
    if config.global_pause:
        return []

    active: list[Segment] = []
    wc = segments.get("world_cup")
    general = segments.get("general_football")

    if config.world_cup_only_mode:
        if config.world_cup_enabled and wc and wc.enabled:
            active.append(wc)
        else:
            log.warning(
                "world_cup_only_mode is on but world_cup segment is not active — "
                "nothing will be monitored"
            )
        return active

    if config.football_enabled and general and general.enabled:
        active.append(general)
    if config.world_cup_enabled and wc and wc.enabled:
        active.append(wc)
    return active
