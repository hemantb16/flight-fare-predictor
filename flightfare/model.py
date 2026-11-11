"""Loading the trained model and turning trips into fare estimates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

from .features import Trip, build_features

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "model.joblib"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"


@dataclass(frozen=True)
class Estimate:
    fare: float
    low: float
    high: float


class FarePredictor:
    """Wraps the scikit-learn pipeline, which predicts log(1 + price)."""

    def __init__(self, pipeline, metrics: dict):
        self.pipeline = pipeline
        self.metrics = metrics
        # Typical relative error band taken from the held-out test set.
        self.band_low = metrics.get("ratio_p10", 0.9)
        self.band_high = metrics.get("ratio_p90", 1.1)

    @classmethod
    def load(cls, model_path: Path = MODEL_PATH, metrics_path: Path = METRICS_PATH) -> "FarePredictor":
        if not model_path.exists():
            raise FileNotFoundError(
                f"No trained model at {model_path}. Run `python -m flightfare.train` first."
            )
        metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
        return cls(joblib.load(model_path), metrics)

    def predict_many(self, trips: list[Trip]) -> list[Estimate]:
        raw = np.expm1(self.pipeline.predict(build_features(trips)))
        return [
            Estimate(
                fare=round(float(p), 2),
                low=round(float(p * self.band_low), 2),
                high=round(float(p * self.band_high), 2),
            )
            for p in np.maximum(raw, 1.0)
        ]

    def predict(self, trip: Trip) -> Estimate:
        return self.predict_many([trip])[0]
