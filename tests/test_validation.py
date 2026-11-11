from datetime import date

import pytest

from flightfare.validation import parse_search, resolve_airport

TODAY = date(2026, 6, 1)


def good(**overrides):
    data = {
        "origin": "Munich (MUC)",
        "destination": "Barcelona (BCN)",
        "travel_date": "2026-07-15",
        "cabin": "economy",
        "airline": "any",
        "stops": "any",
        "time_slot": "any",
        "passengers": "3",
    }
    data.update(overrides)
    return data


def test_valid_input_produces_search():
    parsed = parse_search(good(), today=TODAY)
    assert parsed.ok, parsed.errors
    s = parsed.search
    assert (s.origin, s.destination) == ("MUC", "BCN")
    assert s.days_before == 44
    assert s.airline is None and s.max_stops is None and s.time_slot is None
    assert s.passengers == 3


def test_booking_date_is_today_by_default():
    assert parse_search(good(), today=TODAY).search.booking_date == TODAY


@pytest.mark.parametrize("value", ["MUC", "muc", "Munich (MUC)", "Munich", " munich "])
def test_airports_resolve_from_code_label_or_city(value):
    assert resolve_airport(value) == "MUC"


def test_numeric_json_values_are_accepted():
    parsed = parse_search(good(stops=0, passengers=2, airline="LH"), today=TODAY)
    assert parsed.ok, parsed.errors
    assert parsed.search.max_stops == 0
    assert parsed.search.passengers == 2


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"origin": "Atlantis"}, "origin"),
        ({"destination": "MUC"}, "destination"),
        ({"travel_date": "not-a-date"}, "travel_date"),
        ({"travel_date": "2026-05-01"}, "travel_date"),
        ({"travel_date": "2027-12-01"}, "travel_date"),
        ({"cabin": "suite"}, "cabin"),
        ({"cabin": "first"}, "cabin"),  # no First on a short European route
        ({"airline": "ZZ"}, "airline"),
        ({"airline": "QF"}, "airline"),  # Qantas doesn't fly Munich – Barcelona
        ({"stops": "5"}, "stops"),
        ({"time_slot": "noon"}, "time_slot"),
        ({"passengers": "0"}, "passengers"),
        ({"passengers": "10"}, "passengers"),
        ({"origin": "HAM", "destination": "BRE"}, "destination"),  # no flights on this route
    ],
)
def test_invalid_input_is_rejected(overrides, field):
    parsed = parse_search(good(**overrides), today=TODAY)
    assert not parsed.ok
    assert field in parsed.errors
    assert parsed.search is None


def test_unserved_route_suggests_a_hub():
    parsed = parse_search(good(origin="HAM", destination="BRE"), today=TODAY)
    assert "Try a nearby hub" in parsed.errors["destination"]


def test_missing_fields_report_errors():
    parsed = parse_search({}, today=TODAY)
    assert {"origin", "destination", "travel_date"} <= set(parsed.errors)
