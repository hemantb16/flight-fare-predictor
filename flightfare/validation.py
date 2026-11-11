"""Parsing and validating trip details submitted from the form or the JSON API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from .catalog import AIRLINES, CABINS, CITIES, TIME_SLOTS
from .features import Trip

MAX_DAYS_AHEAD = 365
MAX_PASSENGERS = 9


@dataclass
class ParsedRequest:
    trip: Trip | None = None
    passengers: int = 1
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        return None


def parse_trip(data, today: date | None = None) -> ParsedRequest:
    """Validate a mapping of raw string values. Returns a trip or field errors."""
    today = today or date.today()
    errors: dict[str, str] = {}

    def text(name: str) -> str:
        value = data.get(name)
        return "" if value is None else str(value).strip()

    origin = text("origin").upper()
    destination = text("destination").upper()
    if origin not in CITIES:
        errors["origin"] = "Choose a departure city."
    if destination not in CITIES:
        errors["destination"] = "Choose an arrival city."
    if "origin" not in errors and origin == destination:
        errors["destination"] = "Arrival city must differ from the departure city."

    booking_raw = text("booking_date")
    booking_date = _parse_date(booking_raw) if booking_raw else today
    if booking_date is None:
        errors["booking_date"] = "Enter a valid booking date."

    travel_date = _parse_date(text("travel_date"))
    if travel_date is None:
        errors["travel_date"] = "Enter a valid travel date."
    elif booking_date is not None:
        if travel_date < booking_date:
            errors["travel_date"] = "Travel date cannot be before the booking date."
        elif travel_date > booking_date + timedelta(days=MAX_DAYS_AHEAD):
            errors["travel_date"] = f"Fares can be estimated up to {MAX_DAYS_AHEAD} days ahead."

    airline = text("airline").upper()
    cabin = text("cabin").lower()
    if airline not in AIRLINES:
        errors["airline"] = "Choose an airline."
    if cabin not in CABINS:
        errors["cabin"] = "Choose a cabin class."
    elif airline in AIRLINES and cabin not in AIRLINES[airline].cabins:
        offered = ", ".join(CABINS[c] for c in AIRLINES[airline].cabins)
        errors["cabin"] = f"{AIRLINES[airline].name} only offers: {offered}."

    try:
        stops = int(text("stops"))
        if stops not in (0, 1, 2):
            raise ValueError
    except ValueError:
        stops = 0
        errors["stops"] = "Choose the number of stops."

    time_slot = text("time_slot").lower()
    if time_slot not in TIME_SLOTS:
        errors["time_slot"] = "Choose a departure time."

    passengers_raw = text("passengers") or "1"
    try:
        passengers = int(passengers_raw)
        if not 1 <= passengers <= MAX_PASSENGERS:
            raise ValueError
    except ValueError:
        passengers = 1
        errors["passengers"] = f"Passengers must be between 1 and {MAX_PASSENGERS}."

    if errors:
        return ParsedRequest(passengers=passengers, errors=errors)
    trip = Trip(
        origin=origin,
        destination=destination,
        travel_date=travel_date,
        booking_date=booking_date,
        airline=airline,
        cabin=cabin,
        stops=stops,
        time_slot=time_slot,
    )
    return ParsedRequest(trip=trip, passengers=passengers)
