"""Detector registry. Add a module, append to REGISTRY — nothing else changes."""
from .base import Detector
from .divergence import DivergenceDetector
from .drift import DriftDetector
from .persistence_amp import PersistenceAmpDetector
from .price_move import PriceMoveDetector
from .rarity import RarityDetector
from .reversal import ReversalDetector
from .sharp_leader import SharpLeaderDetector

REGISTRY: list[Detector] = [
    PriceMoveDetector(),       # D1 — unusual single-interval move (max 25)
    DivergenceDetector(),      # D2 — cross-book outlier (max 15)
    DriftDetector(),           # D3 — sustained directional movement (max 20)
    SharpLeaderDetector(),     # D4 — sharp leads, retail follows (max 30)
    PersistenceAmpDetector(),  # D5 — rapid move that held (max 15)
    ReversalDetector(),        # D6 — suppressor: fake-move penalty (-20)
    RarityDetector(),          # D7 — rarity vs trailing baseline (max 15)
]
