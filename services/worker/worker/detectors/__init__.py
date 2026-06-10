"""Detector registry. Add a module, append to REGISTRY — nothing else changes."""
from .base import Detector
from .price_move import PriceMoveDetector

REGISTRY: list[Detector] = [
    PriceMoveDetector(),
    # DivergenceDetector(),      # D2 — 14-day plan
    # DriftDetector(),           # D3 — 14-day plan
    # SharpLeaderDetector(),     # D4 — 14-day plan
    # PersistenceAmpDetector(),  # D5 — 30-day plan
    # ReversalDetector(),        # D6 — 30-day plan
    # RarityDetector(),          # D7 — 30-day plan
]
