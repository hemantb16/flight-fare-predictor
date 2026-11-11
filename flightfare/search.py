"""Turn a validated search into priced itineraries and savings insights."""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from datetime import timedelta

from .catalog import AIRLINES, TIME_SLOTS, distance_km
from .features import Trip
from .model import Estimate, FarePredictor
from .network import Option, cabins_for, route_options
from .validation import Search

BOOKING_WINDOWS = [1, 7, 14, 30, 60, 90]


@dataclass(frozen=True)
class Itinerary:
    option: Option
    time_slot: str
    estimate: Estimate

    @property
    def airline(self):
        return AIRLINES[self.option.airline]


def matching_options(search: Search) -> list[Option]:
    dist = distance_km(search.origin, search.destination)
    return [
        o
        for o in route_options(search.origin, search.destination)
        if (search.airline is None or o.airline == search.airline)
        and (search.max_stops is None or o.stops <= search.max_stops)
        and search.cabin in cabins_for(AIRLINES[o.airline], dist)
    ]


def _trip(search: Search, option: Option, slot: str) -> Trip:
    return Trip(
        origin=search.origin,
        destination=search.destination,
        travel_date=search.travel_date,
        booking_date=search.booking_date,
        airline=option.airline,
        cabin=search.cabin,
        stops=option.stops,
        time_slot=slot,
    )


SLOT_WEIGHTS = {"early": 1, "morning": 4, "afternoon": 3, "evening": 3, "night": 1}


def scheduled_slot(option: Option, search: Search) -> str:
    """A stable, plausible departure slot for an itinerary, like a real timetable.

    Derived from a checksum of route, airline and stops, so the same flight
    always departs in the same part of the day.
    """
    key = f"{search.origin}{search.destination}{option.airline}{option.stops}".encode()
    ticket = zlib.crc32(key) % sum(SLOT_WEIGHTS.values())
    for slot, weight in SLOT_WEIGHTS.items():
        if ticket < weight:
            return slot
        ticket -= weight
    return "afternoon"


def price_itineraries(predictor: FarePredictor, search: Search) -> list[Itinerary]:
    """Estimate per matching (airline, stops) option, sorted by price.

    With a preferred departure time every option is priced in that slot.
    Otherwise each option keeps its own scheduled slot.
    """
    options = matching_options(search)
    slots = [search.time_slot or scheduled_slot(o, search) for o in options]
    estimates = predictor.predict_many([_trip(search, o, s) for o, s in zip(options, slots)])
    itineraries = [Itinerary(o, s, e) for o, s, e in zip(options, slots, estimates)]
    return sorted(itineraries, key=lambda i: (i.estimate.fare, i.option.stops))


def _with_pct(rows: list[dict]) -> list[dict]:
    top = max(r["fare"] for r in rows)
    for r in rows:
        r["pct"] = round(r["fare"] / top * 100)
    return rows


def insights(predictor: FarePredictor, search: Search, pick: Itinerary) -> dict[str, list[dict]]:
    base = _trip(search, pick.option, pick.time_slot)

    date_trips = [
        base.replace(travel_date=search.travel_date + timedelta(days=d))
        for d in range(-3, 4)
        if search.travel_date + timedelta(days=d) >= search.booking_date
    ]
    dates = [
        {"date": t.travel_date, "fare": e.fare, "selected": t.travel_date == search.travel_date}
        for t, e in zip(date_trips, predictor.predict_many(date_trips))
    ]

    window_trips = [base.replace(booking_date=search.travel_date - timedelta(days=d)) for d in BOOKING_WINDOWS]
    windows = [
        {"days": d, "fare": e.fare, "selected": False}
        for d, e in zip(BOOKING_WINDOWS, predictor.predict_many(window_trips))
    ]

    slot_trips = [base.replace(time_slot=s) for s in TIME_SLOTS]
    slots = [
        {"label": TIME_SLOTS[t.time_slot].split(" (")[0], "fare": e.fare, "selected": t.time_slot == pick.time_slot}
        for t, e in zip(slot_trips, predictor.predict_many(slot_trips))
    ]
    return {"dates": _with_pct(dates), "windows": _with_pct(windows), "slots": _with_pct(slots)}
