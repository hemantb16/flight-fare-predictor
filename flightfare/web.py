"""Flask application: search form, result page and a small JSON API."""

from __future__ import annotations

from datetime import date, timedelta

from flask import Flask, jsonify, render_template, request

from .catalog import AIRLINES, CABINS, CITIES, STOPS, TIME_SLOTS, distance_km, route_type
from .features import Trip
from .model import FarePredictor
from .validation import MAX_DAYS_AHEAD, MAX_PASSENGERS, parse_trip

BOOKING_WINDOWS = [1, 7, 14, 30, 60, 90]


def format_eur(value: float) -> str:
    return f"€{value:,.0f}" if value >= 100 else f"€{value:,.2f}"


def estimate_duration(distance: float, stops: int) -> str:
    """Rough block time: cruise at ~820 km/h plus taxi/climb and layovers."""
    minutes = int(distance / 820 * 60 + 35 + stops * 110)
    hours, mins = divmod(round(minutes / 5) * 5, 60)
    return f"{hours}h {mins:02d}m"


def create_app(predictor: FarePredictor | None = None) -> Flask:
    app = Flask(__name__)
    app.config["PREDICTOR"] = predictor or FarePredictor.load()
    app.jinja_env.filters["eur"] = format_eur

    def get_predictor() -> FarePredictor:
        return app.config["PREDICTOR"]

    @app.context_processor
    def inject_catalog():
        cities = sorted(CITIES.values(), key=lambda c: (c.country != "Germany", c.name))
        return {
            "cities": cities,
            "airlines": list(AIRLINES.values()),
            "cabins": CABINS,
            "time_slots": TIME_SLOTS,
            "stops_options": STOPS,
            "max_passengers": MAX_PASSENGERS,
        }

    def form_defaults(today: date) -> dict:
        return {
            "origin": "BER",
            "destination": "LHR",
            "travel_date": (today + timedelta(days=30)).isoformat(),
            "booking_date": today.isoformat(),
            "airline": "SC",
            "cabin": "economy",
            "stops": "0",
            "time_slot": "morning",
            "passengers": "1",
        }

    def render_form(values: dict, errors: dict | None = None, status: int = 200):
        today = date.today()
        return (
            render_template(
                "index.html",
                values=values,
                errors=errors or {},
                today=today.isoformat(),
                max_date=(today + timedelta(days=MAX_DAYS_AHEAD)).isoformat(),
            ),
            status,
        )

    @app.get("/")
    def index():
        values = form_defaults(date.today())
        # Allow "Edit search" links to pre-fill the form.
        values.update({k: v for k, v in request.args.items() if k in values and v})
        return render_form(values)

    @app.get("/result")
    def result():
        parsed = parse_trip(request.args)
        if not parsed.ok:
            values = form_defaults(date.today())
            values.update({k: v for k, v in request.args.items() if k in values})
            return render_form(values, parsed.errors, status=400)

        trip, passengers = parsed.trip, parsed.passengers
        predictor = get_predictor()
        estimate = predictor.predict(trip)
        dist = distance_km(trip.origin, trip.destination)

        # Same trip with every airline that sells this cabin.
        airline_trips = [
            Trip(**{**trip.__dict__, "airline": code})
            for code, a in AIRLINES.items()
            if trip.cabin in a.cabins
        ]
        airline_rows = sorted(
            (
                {"airline": AIRLINES[t.airline], "fare": e.fare, "selected": t.airline == trip.airline}
                for t, e in zip(airline_trips, predictor.predict_many(airline_trips))
            ),
            key=lambda r: r["fare"],
        )

        # Nearby travel dates (same booking date), skipping dates in the past.
        date_trips = [
            Trip(**{**trip.__dict__, "travel_date": trip.travel_date + timedelta(days=offset)})
            for offset in range(-3, 4)
            if trip.travel_date + timedelta(days=offset) >= trip.booking_date
        ]
        date_rows = [
            {"date": t.travel_date, "fare": e.fare, "selected": t.travel_date == trip.travel_date}
            for t, e in zip(date_trips, predictor.predict_many(date_trips))
        ]

        # The same flight booked earlier or later.
        window_trips = [
            Trip(**{**trip.__dict__, "booking_date": trip.travel_date - timedelta(days=d)})
            for d in BOOKING_WINDOWS
        ]
        window_rows = [
            {"days": d, "fare": e.fare}
            for d, e in zip(BOOKING_WINDOWS, predictor.predict_many(window_trips))
        ]

        for rows in (airline_rows, date_rows, window_rows):
            top = max(r["fare"] for r in rows)
            for r in rows:
                r["pct"] = round(r["fare"] / top * 100)

        return render_template(
            "result.html",
            trip=trip,
            passengers=passengers,
            estimate=estimate,
            total=estimate.fare * passengers,
            origin=CITIES[trip.origin],
            destination=CITIES[trip.destination],
            airline=AIRLINES[trip.airline],
            cabin_label=CABINS[trip.cabin],
            slot_label=TIME_SLOTS[trip.time_slot],
            stops_label=STOPS[trip.stops],
            distance=round(dist),
            route=route_type(dist),
            duration=estimate_duration(dist, trip.stops),
            airline_rows=airline_rows,
            date_rows=date_rows,
            window_rows=window_rows,
            cheapest_airline=airline_rows[0],
            query=request.args.to_dict(),
        )

    @app.post("/api/predict")
    def api_predict():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"errors": {"body": "Send a JSON object."}}), 400
        parsed = parse_trip(payload)
        if not parsed.ok:
            return jsonify({"errors": parsed.errors}), 400
        trip = parsed.trip
        estimate = get_predictor().predict(trip)
        return jsonify(
            {
                "currency": "EUR",
                "fare_per_passenger": estimate.fare,
                "range": {"low": estimate.low, "high": estimate.high},
                "passengers": parsed.passengers,
                "total": round(estimate.fare * parsed.passengers, 2),
                "trip": {
                    "origin": trip.origin,
                    "destination": trip.destination,
                    "travel_date": trip.travel_date.isoformat(),
                    "booking_date": trip.booking_date.isoformat(),
                    "days_before": trip.days_before,
                    "distance_km": round(distance_km(trip.origin, trip.destination)),
                    "airline": trip.airline,
                    "cabin": trip.cabin,
                    "stops": trip.stops,
                    "time_slot": trip.time_slot,
                },
            }
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "model": get_predictor().metrics.get("trained_at")})

    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html"), 404

    return app
