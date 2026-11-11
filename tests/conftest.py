from datetime import date, timedelta

import pytest

from flightfare.model import MODEL_PATH, FarePredictor
from flightfare.web import create_app


@pytest.fixture(scope="session")
def predictor():
    if not MODEL_PATH.exists():
        from flightfare.train import train

        train()
    return FarePredictor.load()


@pytest.fixture()
def client(predictor):
    app = create_app(predictor)
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture()
def valid_trip():
    today = date.today()
    return {
        "origin": "BER",
        "destination": "LHR",
        "travel_date": (today + timedelta(days=30)).isoformat(),
        "booking_date": today.isoformat(),
        "airline": "SC",
        "cabin": "economy",
        "stops": "0",
        "time_slot": "morning",
        "passengers": "2",
    }
