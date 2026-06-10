from typing import Protocol

from ..models import DetectorResult, FeatureCtx


class Detector(Protocol):
    name: str

    def detect(self, ctx: FeatureCtx) -> DetectorResult: ...
