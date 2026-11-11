"""Static reference data: airports, airlines, cabins and departure time slots.

Airlines are fictional. Coordinates are approximate airport locations and are
only used to compute great-circle route distances.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    code: str
    name: str
    country: str
    lat: float
    lon: float
    demand: float  # relative popularity of the airport (1.0 = average)


@dataclass(frozen=True)
class Airline:
    code: str
    name: str
    kind: str  # "full-service", "hybrid" or "low-cost"
    price_factor: float
    cabins: tuple[str, ...]


CITIES: dict[str, City] = {
    c.code: c
    for c in [
        City("BER", "Berlin", "Germany", 52.366, 13.503, 1.00),
        City("MUC", "Munich", "Germany", 48.354, 11.786, 1.04),
        City("FRA", "Frankfurt", "Germany", 50.038, 8.562, 1.02),
        City("HAM", "Hamburg", "Germany", 53.630, 9.988, 0.97),
        City("DUS", "Düsseldorf", "Germany", 51.289, 6.767, 0.96),
        City("CGN", "Cologne", "Germany", 50.866, 7.143, 0.94),
        City("STR", "Stuttgart", "Germany", 48.690, 9.222, 0.95),
        City("LHR", "London", "United Kingdom", 51.470, -0.454, 1.12),
        City("CDG", "Paris", "France", 49.010, 2.548, 1.10),
        City("AMS", "Amsterdam", "Netherlands", 52.310, 4.768, 1.06),
        City("MAD", "Madrid", "Spain", 40.472, -3.561, 1.02),
        City("BCN", "Barcelona", "Spain", 41.297, 2.078, 1.08),
        City("FCO", "Rome", "Italy", 41.800, 12.239, 1.07),
        City("VIE", "Vienna", "Austria", 48.110, 16.570, 1.00),
        City("ZRH", "Zurich", "Switzerland", 47.458, 8.548, 1.09),
        City("CPH", "Copenhagen", "Denmark", 55.618, 12.656, 1.01),
        City("LIS", "Lisbon", "Portugal", 38.774, -9.134, 1.04),
        City("ATH", "Athens", "Greece", 37.936, 23.947, 1.03),
        City("IST", "Istanbul", "Türkiye", 41.275, 28.752, 0.98),
        City("DXB", "Dubai", "United Arab Emirates", 25.253, 55.365, 1.08),
        City("JFK", "New York", "United States", 40.641, -73.778, 1.12),
        City("BKK", "Bangkok", "Thailand", 13.690, 100.750, 1.02),
        City("DEL", "Delhi", "India", 28.556, 77.100, 0.95),
        City("SIN", "Singapore", "Singapore", 1.364, 103.991, 1.06),
    ]
}

AIRLINES: dict[str, Airline] = {
    a.code: a
    for a in [
        Airline("AX", "Aerolux", "full-service", 1.30, ("economy", "premium", "business", "first")),
        Airline("MA", "Meridian Airways", "full-service", 1.15, ("economy", "premium", "business", "first")),
        Airline("SC", "Skyway Connect", "hybrid", 1.00, ("economy", "premium", "business")),
        Airline("ZA", "Zephyr Air", "low-cost", 0.80, ("economy", "premium")),
        Airline("BH", "BudgetHop", "low-cost", 0.68, ("economy",)),
    ]
}

CABINS: dict[str, str] = {
    "economy": "Economy",
    "premium": "Premium Economy",
    "business": "Business",
    "first": "First",
}

# Departure time slots: key -> (label, hour range)
TIME_SLOTS: dict[str, str] = {
    "early": "Early morning (00:00–06:00)",
    "morning": "Morning (06:00–12:00)",
    "afternoon": "Afternoon (12:00–17:00)",
    "evening": "Evening (17:00–21:00)",
    "night": "Night (21:00–24:00)",
}

STOPS: dict[int, str] = {0: "Non-stop", 1: "1 stop", 2: "2+ stops"}


def distance_km(origin: str, destination: str) -> float:
    """Great-circle distance between two airports (haversine formula)."""
    a, b = CITIES[origin], CITIES[destination]
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def route_type(distance: float) -> str:
    if distance < 1500:
        return "short-haul"
    if distance < 4000:
        return "medium-haul"
    return "long-haul"
