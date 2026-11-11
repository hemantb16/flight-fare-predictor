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
def valid_search():
    return {
        "origin": "Berlin (BER)",
        "destination": "LHR",
        "travel_date": (date.today() + timedelta(days=30)).isoformat(),
        "cabin": "economy",
        "airline": "any",
        "stops": "any",
        "time_slot": "any",
        "passengers": "2",
    }
