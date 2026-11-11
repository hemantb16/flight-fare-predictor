"""Parsing and validating searches submitted from the form or the JSON API."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from .catalog import AIRLINES, AIRPORTS, CABINS, TIME_SLOTS, distance_km
from .network import cabins_for, route_options

MAX_DAYS_AHEAD = 365
MAX_PASSENGERS = 9
STOP_FILTERS = {"any": "Any number of stops", "0": "Non-stop only", "1": "Up to 1 stop"}

_CODE_IN_LABEL = re.compile(r"\(([A-Za-z]{3})\)\s*$")


@dataclass(frozen=True)
class Search:
    origin: str
    destination: str
    travel_date: date
    booking_date: date
    cabin: str
    airline: str | None  # None = any airline
    max_stops: int | None  # None = any
    time_slot: str | None  # None = any time
    passengers: int

    @property
    def days_before(self) -> int:
        return (self.travel_date - self.booking_date).days


@dataclass
class ParsedSearch:
    search: Search | None = None
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def resolve_airport(value: str) -> str | None:
    """Accept an IATA code ("BER"), a form label ("Berlin (BER)") or a city name."""
    value = (value or "").strip()
    if not value:
        return None
    match = _CODE_IN_LABEL.search(value)
    code = (match.group(1) if match else value).upper()
    if code in AIRPORTS:
        return code
    by_city = [a.code for a in AIRPORTS.values() if a.city.lower() == value.lower()]
    return by_city[0] if len(by_city) == 1 else None


def nearest_hub(code: str) -> str:
    hubs = [a for a in AIRPORTS.values() if a.size == 3 and a.code != code]
    return min(hubs, key=lambda a: distance_km(code, a.code)).label


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_search(data, today: date | None = None) -> ParsedSearch:
    """Validate a mapping of raw values. Returns a search or per-field errors."""
    today = today or date.today()
    errors: dict[str, str] = {}

    def text(name: str) -> str:
        value = data.get(name)
        return "" if value is None else str(value).strip()

    origin = resolve_airport(text("origin"))
    destination = resolve_airport(text("destination"))
    if origin is None:
        errors["origin"] = "Choose a departure airport from the list."
    if destination is None:
        errors["destination"] = "Choose an arrival airport from the list."
    elif origin == destination:
        errors["destination"] = "Arrival must differ from departure."

    # The booking date is today. The API accepts an explicit one for testing and "what if" checks.
    booking_date = _parse_date(text("booking_date")) if text("booking_date") else today
    if booking_date is None:
        errors["booking_date"] = "Enter a valid booking date (YYYY-MM-DD)."
        booking_date = today

    travel_date = _parse_date(text("travel_date"))
    if travel_date is None:
        errors["travel_date"] = "Pick a travel date."
    elif travel_date < booking_date:
        errors["travel_date"] = "Travel date is in the past."
    elif travel_date > booking_date + timedelta(days=MAX_DAYS_AHEAD):
        errors["travel_date"] = "Fares can be estimated up to a year ahead."

    cabin = text("cabin").lower() or "economy"
    if cabin not in CABINS:
        errors["cabin"] = "Choose a cabin class."

    airline = text("airline").upper()
    airline = None if airline in ("", "ANY") else airline
    if airline is not None and airline not in AIRLINES:
        errors["airline"] = "Choose an airline."

    stops_raw = text("stops").lower() or "any"
    if stops_raw not in STOP_FILTERS:
        errors["stops"] = "Choose how many stops are OK."
    max_stops = None if stops_raw == "any" else int(stops_raw) if stops_raw in STOP_FILTERS else None

    slot = text("time_slot").lower() or "any"
    if slot != "any" and slot not in TIME_SLOTS:
        errors["time_slot"] = "Choose a departure time."
    time_slot = None if slot == "any" else slot

    try:
        passengers = int(text("passengers") or "1")
        if not 1 <= passengers <= MAX_PASSENGERS:
            raise ValueError
    except ValueError:
        passengers = 1
        errors["passengers"] = f"Passengers must be between 1 and {MAX_PASSENGERS}."

    # Route-level checks only make sense once the basic fields are valid.
    if not errors:
        options = route_options(origin, destination)
        dist = distance_km(origin, destination)
        if not options:
            errors["destination"] = (
                f"No airline in our network flies {AIRPORTS[origin].city} – {AIRPORTS[destination].city}. "
                f"Try a nearby hub such as {nearest_hub(origin if AIRPORTS[origin].size < 3 else destination)}."
            )
        else:
            if airline is not None:
                options = tuple(o for o in options if o.airline == airline)
                if not options:
                    errors["airline"] = f"{AIRLINES[airline].name} doesn't fly this route."
            if not errors and max_stops is not None:
                options = tuple(o for o in options if o.stops <= max_stops)
                if not options:
                    errors["stops"] = "No flights with that few stops on this route. Allow more stops."
            if not errors and not any(cabin in cabins_for(AIRLINES[o.airline], dist) for o in options):
                errors["cabin"] = f"{CABINS[cabin]} isn't sold on this route with these filters."

    if errors:
        return ParsedSearch(errors=errors)
    return ParsedSearch(
        Search(origin, destination, travel_date, booking_date, cabin, airline, max_stops, time_slot, passengers)
    )
