from datetime import date, timedelta

from flightfare.features import FEATURES, Trip, build_features, easter_sunday, is_holiday
from flightfare.model import FarePredictor
from flightfare.pricing import expected_fare, generate_dataset

TODAY = date(2026, 3, 2)


def make_trip(**overrides) -> Trip:
    base = dict(
        origin="FRA",
        destination="JFK",
        travel_date=TODAY + timedelta(days=45),
        booking_date=TODAY,
        airline="LH",
        cabin="economy",
        stops=0,
        time_slot="afternoon",
    )
    base.update(overrides)
    return Trip(**base)


def test_model_loads(predictor):
    assert isinstance(predictor, FarePredictor)
    assert predictor.metrics["r2"] > 0.95
    assert predictor.band_low < 1 < predictor.band_high


def test_easter_and_holidays():
    assert easter_sunday(2026) == date(2026, 4, 5)
    assert easter_sunday(2027) == date(2027, 3, 28)
    assert is_holiday(date(2026, 12, 24))
    assert is_holiday(date(2026, 4, 3))
    assert not is_holiday(date(2026, 10, 14))


def test_feature_table_has_expected_columns():
    df = build_features([make_trip()])
    assert list(df.columns) == FEATURES
    assert df.loc[0, "days_before"] == 45
    assert df.loc[0, "airline_kind"] == "full-service"


def test_synthetic_dataset_is_reproducible():
    a = generate_dataset(n_rows=300, seed=7)
    b = generate_dataset(n_rows=300, seed=7)
    assert a.equals(b)
    assert (a["price"] > 0).all()


def test_prediction_is_close_to_pricing_logic(predictor):
    for trip in [make_trip(), make_trip(origin="CGN", destination="PMI", airline="FR"), make_trip(cabin="business")]:
        estimate = predictor.predict(trip)
        truth = expected_fare(trip)
        assert abs(estimate.fare - truth) / truth < 0.15, trip
        assert estimate.low < estimate.fare < estimate.high


def test_prediction_follows_pricing_rules(predictor):
    economy = predictor.predict(make_trip()).fare
    business = predictor.predict(make_trip(cabin="business")).fare
    last_minute = predictor.predict(make_trip(travel_date=TODAY + timedelta(days=1))).fare
    full_service = predictor.predict(make_trip(origin="CGN", destination="PMI", airline="LH", stops=1)).fare
    low_cost = predictor.predict(make_trip(origin="CGN", destination="PMI", airline="FR")).fare
    summer_beach = predictor.predict(
        make_trip(origin="CGN", destination="PMI", airline="FR", travel_date=date(2026, 7, 29))
    ).fare

    assert business > economy * 2.5
    assert last_minute > economy * 1.3
    assert low_cost < full_service
    assert summer_beach > low_cost * 1.15
