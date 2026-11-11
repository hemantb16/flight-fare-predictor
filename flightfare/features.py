"""Feature engineering shared by training and inference.

The synthetic data generator and the web app describe a trip with the same
raw fields (see :class:`Trip`). ``build_features`` turns trips into the model's
feature table, so training and serving cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache

import pandas as pd

from .catalog import AIRLINES, AIRPORTS, distance_km
from .network import carriers_on_route

CATEGORICAL_FEATURES = [
    "origin",
    "destination",
    "airline",
    "airline_kind",
    "cabin",
    "time_slot",
    "destination_season",
]
NUMERIC_FEATURES = [
    "distance_km",
    "stops",
    "days_before",
    "weekday",
    "month",
    "holiday",
    "carriers_on_route",
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

    def replace(self, **changes) -> "Trip":
        return Trip(**{**self.__dict__, **changes})


@lru_cache(maxsize=None)
def easter_sunday(year: int) -> date:
    """Gregorian Easter (anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month, day = divmod(h + l_ - 7 * m + 114, 31)
    return date(year, month, day + 1)


def is_christmas_peak(d: date) -> bool:
    """Christmas / New Year travel peak (18 Dec – 6 Jan)."""
    return (d.month == 12 and d.day >= 18) or (d.month == 1 and d.day <= 6)


def is_easter_peak(d: date) -> bool:
    """Easter holidays: the week before Good Friday to a week after Easter Monday."""
    easter = easter_sunday(d.year)
    return easter - timedelta(days=9) <= d <= easter + timedelta(days=8)


def is_holiday(d: date) -> bool:
    return is_christmas_peak(d) or is_easter_peak(d)


def trip_to_row(trip: Trip) -> dict:
    return {
        "origin": trip.origin,
        "destination": trip.destination,
        "airline": trip.airline,
        "airline_kind": AIRLINES[trip.airline].kind,
        "cabin": trip.cabin,
        "time_slot": trip.time_slot,
        "destination_season": AIRPORTS[trip.destination].season,
        "distance_km": round(distance_km(trip.origin, trip.destination), 1),
        "stops": int(trip.stops),
        "days_before": int(trip.days_before),
        "weekday": trip.travel_date.weekday(),
        "month": trip.travel_date.month,
        "holiday": int(is_holiday(trip.travel_date)),
        "carriers_on_route": carriers_on_route(trip.origin, trip.destination),
    }


def build_features(trips: list[Trip]) -> pd.DataFrame:
    return pd.DataFrame([trip_to_row(t) for t in trips], columns=FEATURES)
