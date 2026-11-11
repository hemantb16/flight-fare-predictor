from datetime import date

import pytest

from flightfare.validation import parse_trip

TODAY = date(2026, 6, 1)


def good(**overrides):
    data = {
        "origin": "MUC",
        "destination": "BCN",
        "travel_date": "2026-07-15",
        "booking_date": "2026-06-01",
        "airline": "ZA",
        "cabin": "economy",
        "stops": "1",
        "time_slot": "evening",
        "passengers": "3",
    }
    data.update(overrides)
    return data


def test_valid_input_produces_trip():
    parsed = parse_trip(good(), today=TODAY)
    assert parsed.ok
    assert parsed.trip.days_before == 44
    assert parsed.trip.stops == 1
    assert parsed.passengers == 3


def test_booking_date_defaults_to_today():
    parsed = parse_trip(good(booking_date=""), today=TODAY)
    assert parsed.ok
    assert parsed.trip.booking_date == TODAY


def test_numeric_json_values_are_accepted():
    parsed = parse_trip(good(stops=0, passengers=2), today=TODAY)
    assert parsed.ok
    assert parsed.trip.stops == 0
    assert parsed.passengers == 2


def test_codes_are_case_insensitive():
    parsed = parse_trip(good(origin="muc", airline="za", cabin="ECONOMY"), today=TODAY)
    assert parsed.ok


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"origin": "XXX"}, "origin"),
        ({"destination": "MUC"}, "destination"),
        ({"travel_date": "not-a-date"}, "travel_date"),
        ({"travel_date": "2026-05-01"}, "travel_date"),
        ({"travel_date": "2027-12-01"}, "travel_date"),
        ({"booking_date": "31.12.2026"}, "booking_date"),
        ({"airline": "ZZ"}, "airline"),
        ({"cabin": "suite"}, "cabin"),
        ({"cabin": "first"}, "cabin"),  # Zephyr Air does not sell First
        ({"stops": "5"}, "stops"),
        ({"stops": "one"}, "stops"),
        ({"time_slot": "noon"}, "time_slot"),
        ({"passengers": "0"}, "passengers"),
        ({"passengers": "10"}, "passengers"),
    ],
)
def test_invalid_input_is_rejected(overrides, field):
    parsed = parse_trip(good(**overrides), today=TODAY)
    assert not parsed.ok
    assert field in parsed.errors
    assert parsed.trip is None


def test_missing_fields_report_every_error():
    parsed = parse_trip({}, today=TODAY)
    assert {"origin", "destination", "travel_date", "airline", "cabin", "stops", "time_slot"} <= set(
        parsed.errors
    )
