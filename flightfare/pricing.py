"""Synthetic fare generator.

No freely licensed, login-free dataset or API of real ticket prices exists, so
the training data is simulated from a transparent pricing model over a realistic
route network (real airports, real airlines, plausible networks). Every factor
is listed below and documented in the README. Prices are EUR per passenger for a
one-way ticket, including taxes.

    fare = base(distance, carrier type)
           x airline price level x cabin(distance) x stops
           x booking window x weekday x season(destination) x holiday peaks
           x time of day x competition on the route x airport demand
           x random noise (log-normal, about 10 %)
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .catalog import AIRLINES, AIRPORTS, GERMAN, TIME_SLOTS, distance_km
from .features import Trip, build_features, is_christmas_peak, is_easter_peak
from .network import cabins_for, carriers_on_route, route_options

WEEKDAY_FACTOR = {0: 1.05, 1: 0.92, 2: 0.93, 3: 1.00, 4: 1.12, 5: 0.96, 6: 1.10}

# Month factors by destination type.
SEASON_FACTOR = {
    "city":   {1: 0.90, 2: 0.88, 3: 0.95, 4: 1.02, 5: 1.05, 6: 1.10, 7: 1.15, 8: 1.12, 9: 1.06, 10: 1.02, 11: 0.90, 12: 1.00},
    "summer": {1: 0.78, 2: 0.78, 3: 0.85, 4: 1.00, 5: 1.08, 6: 1.20, 7: 1.38, 8: 1.38, 9: 1.15, 10: 1.00, 11: 0.80, 12: 0.90},
    "winter": {1: 1.12, 2: 1.15, 3: 1.10, 4: 1.02, 5: 0.92, 6: 0.90, 7: 1.00, 8: 1.00, 9: 0.92, 10: 1.02, 11: 1.05, 12: 1.18},
}
CHRISTMAS_FACTOR = 1.20
EASTER_FACTOR = 1.12
TIME_SLOT_FACTOR = {"early": 0.88, "morning": 1.08, "afternoon": 1.00, "evening": 1.06, "night": 0.86}
STOPS_FACTOR = {0: 1.00, 1: 0.86, 2: 0.78}
NOISE_SIGMA = 0.10


def base_fare(distance: float, kind: str) -> float:
    """Economy base fare: a fixed part (lower for low-cost/leisure) plus a distance term."""
    fixed = 55.0 if kind == "full-service" else 30.0
    return fixed + 0.116 * distance**0.94


def cabin_factor(cabin: str, distance: float) -> float:
    longness = min(distance / 10000.0, 1.0)
    return {
        "economy": 1.0,
        "premium": 1.7 + 0.2 * longness,
        "business": 2.1 + 2.6 * longness,
        "first": 6.0 + 2.0 * longness,
    }[cabin]


def booking_window_factor(days_before: int, kind: str, cabin: str, distance: float) -> float:
    """U-shaped curve: last-minute is expensive, booking a few weeks ahead is cheapest.

    Low-cost carriers get steeper last-minute rises, business/first fares are
    flexible and barely move, and the cheapest window sits further out on
    long-haul routes.
    """
    amplitude = 1.10 if kind != "full-service" else 0.85
    if cabin in ("business", "first"):
        amplitude *= 0.4
    sweet_spot = 35 + 40 * min(distance / 10000.0, 1.0)
    last_minute = amplitude * math.exp(-days_before / 7.0)
    early_dip = -0.12 * math.exp(-((days_before - sweet_spot) ** 2) / (2 * 25**2))
    far_out = 0.06 * min(max(days_before - 150, 0) / 150.0, 1.0)
    return 1.0 + last_minute + early_dip + far_out


def season_factor(travel_date: date, destination: str) -> float:
    factor = SEASON_FACTOR[AIRPORTS[destination].season][travel_date.month]
    if is_christmas_peak(travel_date):
        factor *= CHRISTMAS_FACTOR
    elif is_easter_peak(travel_date):
        factor *= EASTER_FACTOR
    return factor


def competition_factor(carriers: int) -> float:
    """Monopoly routes are pricier; busy routes with many airlines are cheaper."""
    return 1.08 - 0.025 * min(carriers, 8)


def expected_fare(trip: Trip) -> float:
    """Noise-free fare for a trip (the 'true' price the model tries to learn)."""
    airline = AIRLINES[trip.airline]
    dist = distance_km(trip.origin, trip.destination)
    demand = math.sqrt(AIRPORTS[trip.origin].demand * AIRPORTS[trip.destination].demand)
    return (
        base_fare(dist, airline.kind)
        * airline.price
        * cabin_factor(trip.cabin, dist)
        * STOPS_FACTOR[trip.stops]
        * booking_window_factor(trip.days_before, airline.kind, trip.cabin, dist)
        * WEEKDAY_FACTOR[trip.travel_date.weekday()]
        * season_factor(trip.travel_date, trip.destination)
        * TIME_SLOT_FACTOR[trip.time_slot]
        * competition_factor(carriers_on_route(trip.origin, trip.destination))
        * demand
    )


CABIN_WEIGHTS = {"economy": 72, "premium": 12, "business": 12, "first": 4}


def random_trip(rng: random.Random, start: date, codes: list[str], weights: list[float]) -> Trip:
    while True:
        origin, destination = rng.choices(codes, weights=weights, k=2)
        options = route_options(origin, destination)
        if options:
            break
    option = rng.choice(options)
    airline = AIRLINES[option.airline]
    cabins = cabins_for(airline, distance_km(origin, destination))
    cabin = rng.choices(cabins, weights=[CABIN_WEIGHTS[c] for c in cabins])[0]
    booking_date = start + timedelta(days=rng.randrange(0, 730))
    days_before = min(int(rng.expovariate(1 / 50)), 365)
    return Trip(
        origin=origin,
        destination=destination,
        travel_date=booking_date + timedelta(days=days_before),
        booking_date=booking_date,
        airline=option.airline,
        cabin=cabin,
        stops=option.stops,
        time_slot=rng.choice(list(TIME_SLOTS)),
    )


def generate_dataset(n_rows: int = 150_000, seed: int = 42) -> pd.DataFrame:
    """Return a feature table plus a ``price`` column (EUR, one-way, per person)."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    start = date(2025, 1, 1)
    codes = list(AIRPORTS)
    # Bigger airports appear more often; German airports are over-sampled because
    # most searches in this app are expected to start or end in Germany.
    weights = [AIRPORTS[c].size * (2.5 if c in GERMAN else 1.0) for c in codes]
    trips = [random_trip(rng, start, codes, weights) for _ in range(n_rows)]
    df = build_features(trips)
    expected = np.array([expected_fare(t) for t in trips])
    noise = np_rng.lognormal(mean=0.0, sigma=NOISE_SIGMA, size=n_rows)
    df["travel_date"] = [t.travel_date.isoformat() for t in trips]
    df["price"] = np.round(expected * noise, 2)
    return df
