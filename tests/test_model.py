from datetime import date, timedelta

from flightfare.catalog import distance_km
from flightfare.features import FEATURES, Trip, build_features
from flightfare.model import FarePredictor
from flightfare.pricing import expected_fare, generate_dataset

TODAY = date(2026, 3, 2)


def make_trip(**overrides) -> Trip:
    base = dict(
        origin="FRA",
        destination="JFK",
        travel_date=TODAY + timedelta(days=40),
        booking_date=TODAY,
        airline="MA",
        cabin="economy",
        stops=0,
        time_slot="afternoon",
    )
    base.update(overrides)
    return Trip(**base)


def test_model_loads(predictor):
    assert isinstance(predictor, FarePredictor)
    assert predictor.metrics["r2"] > 0.9
    assert predictor.band_low < 1 < predictor.band_high


def test_distance_is_plausible():
    assert 6000 < distance_km("FRA", "JFK") < 6400
    assert 400 < distance_km("BER", "MUC") < 550


def test_feature_table_has_expected_columns():
    df = build_features([make_trip()])
    assert list(df.columns) == FEATURES
    assert df.loc[0, "days_before"] == 40


def test_synthetic_dataset_is_reproducible():
    a = generate_dataset(n_rows=200, seed=7)
    b = generate_dataset(n_rows=200, seed=7)
    assert a.equals(b)
    assert (a["price"] > 0).all()


def test_prediction_is_close_to_pricing_logic(predictor):
    trip = make_trip()
    estimate = predictor.predict(trip)
    truth = expected_fare(trip)
    assert abs(estimate.fare - truth) / truth < 0.15
    assert estimate.low < estimate.fare < estimate.high


def test_prediction_follows_pricing_rules(predictor):
    economy = predictor.predict(make_trip()).fare
    business = predictor.predict(make_trip(cabin="business")).fare
    short_haul = predictor.predict(make_trip(destination="CDG")).fare
    last_minute = predictor.predict(make_trip(travel_date=TODAY + timedelta(days=1))).fare
    budget = predictor.predict(make_trip(destination="CDG", airline="BH")).fare

    assert business > economy * 2
    assert short_haul < economy
    assert last_minute > economy * 1.3
    assert budget < short_haul
