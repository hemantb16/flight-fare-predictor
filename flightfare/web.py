"""Flask application: search form, result page and a small JSON API."""

from __future__ import annotations

from datetime import date, timedelta

from flask import Flask, jsonify, render_template, request

from .catalog import AIRLINES, AIRPORTS, CABINS, STOPS, TIME_SLOTS, distance_km, route_type
from .model import FarePredictor
from .network import cabins_for, route_options
from .search import insights, price_itineraries
from .validation import MAX_DAYS_AHEAD, MAX_PASSENGERS, STOP_FILTERS, parse_search, resolve_airport

FORM_FIELDS = ("origin", "destination", "travel_date", "cabin", "airline", "stops", "time_slot", "passengers")
VISIBLE_RESULTS = 8


def format_eur(value: float) -> str:
    return f"€{value:,.0f}"


def create_app(predictor: FarePredictor | None = None) -> Flask:
    app = Flask(__name__)
    app.config["PREDICTOR"] = predictor or FarePredictor.load()
    app.jinja_env.filters["eur"] = format_eur

    def get_predictor() -> FarePredictor:
        return app.config["PREDICTOR"]

    @app.context_processor
    def inject_catalog():
        airports = sorted(AIRPORTS.values(), key=lambda a: (a.country != "Germany", a.country, a.city))
        return {
            "airports": airports,
            "airlines": sorted(AIRLINES.values(), key=lambda a: a.name),
            "cabins": CABINS,
            "time_slots": TIME_SLOTS,
            "stop_filters": STOP_FILTERS,
            "max_passengers": MAX_PASSENGERS,
        }

    def form_defaults() -> dict:
        return {
            "origin": AIRPORTS["BER"].label,
            "destination": AIRPORTS["LHR"].label,
            "travel_date": (date.today() + timedelta(days=30)).isoformat(),
            "cabin": "economy",
            "airline": "any",
            "stops": "any",
            "time_slot": "any",
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

    def submitted_values() -> dict:
        values = form_defaults()
        values.update({k: v for k, v in request.args.items() if k in FORM_FIELDS})
        return values

    @app.get("/")
    def index():
        return render_form(submitted_values())

    @app.get("/result")
    def result():
        parsed = parse_search(request.args)
        if not parsed.ok:
            return render_form(submitted_values(), parsed.errors, status=400)

        search = parsed.search
        predictor = get_predictor()
        itineraries = price_itineraries(predictor, search)
        best = itineraries[0]
        dist = distance_km(search.origin, search.destination)
        query = {k: v for k, v in request.args.items() if k in FORM_FIELDS}

        return render_template(
            "result.html",
            search=search,
            best=best,
            itineraries=itineraries,
            visible=VISIBLE_RESULTS,
            insights=insights(predictor, search, best),
            total=best.estimate.fare * search.passengers,
            origin=AIRPORTS[search.origin],
            destination=AIRPORTS[search.destination],
            cabin_label=CABINS[search.cabin],
            slot_labels=TIME_SLOTS,
            stops_labels=STOPS,
            distance=round(dist),
            route=route_type(dist),
            nonstop_carriers=len({i.option.airline for i in itineraries if i.option.stops == 0}),
            query=query,
        )

    @app.get("/api/route")
    def api_route():
        """Airlines and cabins on a route, used by the form to narrow its menus."""
        origin = resolve_airport(request.args.get("origin", ""))
        destination = resolve_airport(request.args.get("destination", ""))
        labels = {
            "origin_label": AIRPORTS[origin].label if origin else None,
            "destination_label": AIRPORTS[destination].label if destination else None,
        }
        if not origin or not destination or origin == destination:
            return jsonify({"airlines": [], "cabins": [], "nonstop": False, **labels})
        dist = distance_km(origin, destination)
        options = route_options(origin, destination)
        airlines = {}
        for o in options:
            entry = airlines.setdefault(o.airline, {"code": o.airline, "name": AIRLINES[o.airline].name, "stops": []})
            entry["stops"].append(o.stops)
        cabins = sorted({c for code in airlines for c in cabins_for(AIRLINES[code], dist)}, key=list(CABINS).index)
        return jsonify(
            {
                "distance_km": round(dist),
                "airlines": sorted(airlines.values(), key=lambda a: a["name"]),
                "cabins": cabins,
                "nonstop": any(o.stops == 0 for o in options),
                **labels,
            }
        )

    @app.post("/api/predict")
    def api_predict():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"errors": {"body": "Send a JSON object."}}), 400
        parsed = parse_search(payload)
        if not parsed.ok:
            return jsonify({"errors": parsed.errors}), 400
        search = parsed.search
        itineraries = price_itineraries(get_predictor(), search)

        def as_json(i):
            return {
                "airline": i.option.airline,
                "airline_name": i.airline.name,
                "stops": i.option.stops,
                "via": list(i.option.via),
                "duration": i.option.duration,
                "time_slot": i.time_slot,
                "fare": i.estimate.fare,
                "range": {"low": i.estimate.low, "high": i.estimate.high},
            }

        best = itineraries[0]
        return jsonify(
            {
                "currency": "EUR",
                "origin": search.origin,
                "destination": search.destination,
                "travel_date": search.travel_date.isoformat(),
                "days_before": search.days_before,
                "distance_km": round(distance_km(search.origin, search.destination)),
                "cabin": search.cabin,
                "passengers": search.passengers,
                "cheapest": as_json(best),
                "total": round(best.estimate.fare * search.passengers, 2),
                "itineraries": [as_json(i) for i in itineraries],
            }
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "model": get_predictor().metrics.get("trained_at")})

    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html"), 404

    return app
