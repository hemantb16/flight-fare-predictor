"""Feature engineering shared by training and inference.

Both the synthetic data generator and the web app describe a trip with the same
raw fields (see :class:`Trip`). ``build_features`` turns trips into the model's
feature table so training and serving can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from .catalog import distance_km

CATEGORICAL_FEATURES = ["origin", "destination", "airline", "cabin", "time_slot"]
NUMERIC_FEATURES = [
    "distance_km",
    "stops",
    "days_before",
    "weekday",
    "month",
    "holiday_peak",
]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES


@dataclass(frozen=True)
class Trip:
    origin: str
    destination: str
    travel_date: date
    booking_date: date
    airline: str
    cabin: str
    stops: int
    time_slot: str

    @property
    def days_before(self) -> int:
        return (self.travel_date - self.booking_date).days


def is_holiday_peak(d: date) -> bool:
    """Christmas / New Year travel peak (18 Dec – 6 Jan)."""
    return (d.month == 12 and d.day >= 18) or (d.month == 1 and d.day <= 6)


def trip_to_row(trip: Trip) -> dict:
    return {
        "origin": trip.origin,
        "destination": trip.destination,
        "airline": trip.airline,
        "cabin": trip.cabin,
        "time_slot": trip.time_slot,
        "distance_km": round(distance_km(trip.origin, trip.destination), 1),
        "stops": int(trip.stops),
        "days_before": int(trip.days_before),
        "weekday": trip.travel_date.weekday(),
        "month": trip.travel_date.month,
        "holiday_peak": int(is_holiday_peak(trip.travel_date)),
    }


def build_features(trips: list[Trip]) -> pd.DataFrame:
    return pd.DataFrame([trip_to_row(t) for t in trips], columns=FEATURES)
