"""Synthetic fare generator.

There is no freely licensed, login-free dataset of real ticket prices, so the
training data is simulated from a transparent pricing model. Every factor is
listed below and documented in the README. Prices are in EUR per passenger for a
one-way ticket.

    fare = base(distance)
           x airline x cabin(distance) x stops x booking_window
           x weekday x season x time_of_day x route_demand
           x random noise (log-normal, ~9 %)
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .catalog import AIRLINES, CITIES, TIME_SLOTS, distance_km
from .features import Trip, build_features, is_holiday_peak

WEEKDAY_FACTOR = {0: 1.05, 1: 0.92, 2: 0.93, 3: 1.00, 4: 1.12, 5: 0.95, 6: 1.10}
MONTH_FACTOR = {
    1: 0.88, 2: 0.86, 3: 0.95, 4: 1.06, 5: 1.05, 6: 1.12,
    7: 1.25, 8: 1.24, 9: 1.04, 10: 1.00, 11: 0.87, 12: 1.08,
}
TIME_SLOT_FACTOR = {"early": 0.88, "morning": 1.08, "afternoon": 1.00, "evening": 1.06, "night": 0.85}
STOPS_FACTOR = {0: 1.00, 1: 0.84, 2: 0.74}
NOISE_SIGMA = 0.09


def base_fare(distance: float) -> float:
    """Economy base fare: a fixed component plus a sub-linear distance term."""
    return 18.0 + 0.35 * distance**0.85


def cabin_factor(cabin: str, distance: float) -> float:
    # Premium cabins carry a bigger mark-up on long flights.
    longness = min(distance / 8000.0, 1.0)
    return {
        "economy": 1.0,
        "premium": 1.55 + 0.25 * longness,
        "business": 2.4 + 1.4 * longness,
        "first": 4.0 + 2.0 * longness,
    }[cabin]


def booking_window_factor(days_before: int) -> float:
    """U-shaped curve: last-minute is expensive, 3-10 weeks ahead is cheapest."""
    last_minute = 0.95 * math.exp(-days_before / 7.0)
    early_dip = -0.10 * math.exp(-((days_before - 45) ** 2) / (2 * 25**2))
    far_out = 0.06 * min(max(days_before - 120, 0) / 180.0, 1.0)
    return 1.0 + last_minute + early_dip + far_out


def season_factor(d: date) -> float:
    return MONTH_FACTOR[d.month] * (1.18 if is_holiday_peak(d) else 1.0)


def expected_fare(trip: Trip) -> float:
    """Noise-free fare for a trip (the 'true' price the model tries to learn)."""
    dist = distance_km(trip.origin, trip.destination)
    demand = math.sqrt(CITIES[trip.origin].demand * CITIES[trip.destination].demand)
    fare = (
        base_fare(dist)
        * AIRLINES[trip.airline].price_factor
        * cabin_factor(trip.cabin, dist)
        * STOPS_FACTOR[trip.stops]
        * booking_window_factor(trip.days_before)
        * WEEKDAY_FACTOR[trip.travel_date.weekday()]
        * season_factor(trip.travel_date)
        * TIME_SLOT_FACTOR[trip.time_slot]
        * demand
    )
    return fare


def random_trip(rng: random.Random, start: date) -> Trip:
    origin, destination = rng.sample(list(CITIES), 2)
    dist = distance_km(origin, destination)
    airline = rng.choice(list(AIRLINES))
    cabins = AIRLINES[airline].cabins
    cabin_weights = {"economy": 70, "premium": 15, "business": 11, "first": 4}
    cabin = rng.choices(cabins, weights=[cabin_weights[c] for c in cabins])[0]
    # Longer routes are more likely to involve connections.
    if dist < 1500:
        stops = rng.choices([0, 1, 2], weights=[75, 22, 3])[0]
    elif dist < 4000:
        stops = rng.choices([0, 1, 2], weights=[55, 37, 8])[0]
    else:
        stops = rng.choices([0, 1, 2], weights=[40, 45, 15])[0]
    # Booking dates spread over two years; booking windows skew short.
    booking_date = start + timedelta(days=rng.randrange(0, 730))
    days_before = min(int(rng.expovariate(1 / 45)), 365)
    travel_date = booking_date + timedelta(days=days_before)
    return Trip(
        origin=origin,
        destination=destination,
        travel_date=travel_date,
        booking_date=booking_date,
        airline=airline,
        cabin=cabin,
        stops=stops,
        time_slot=rng.choice(list(TIME_SLOTS)),
    )


def generate_dataset(n_rows: int = 60_000, seed: int = 42) -> pd.DataFrame:
    """Return a feature table plus a ``price`` column (EUR, one-way, per person)."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    start = date(2024, 1, 1)
    trips = [random_trip(rng, start) for _ in range(n_rows)]
    df = build_features(trips)
    expected = np.array([expected_fare(t) for t in trips])
    noise = np_rng.lognormal(mean=0.0, sigma=NOISE_SIGMA, size=n_rows)
    df["travel_date"] = [t.travel_date.isoformat() for t in trips]
    df["price"] = np.round(expected * noise, 2)
    return df
