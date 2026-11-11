# farecast. Flight Fare Predictor

**What should this flight cost?** farecast estimates one-way ticket prices across **96 real airports** and **57 real airlines**. Enter a route, date, cabin and number of passengers. It lists every airline that plausibly flies the route, non-stop or through its hub, with an estimated fare for each. It also shows how the price moves with nearby dates, how far ahead you book, and time of day.

![Python](https://img.shields.io/badge/python-3.12%2B-3776ab) ![Flask](https://img.shields.io/badge/flask-3.1-black) ![scikit--learn](https://img.shields.io/badge/scikit--learn-1.9-f7931e) ![License](https://img.shields.io/badge/license-MIT-blue)

> **Note on the data.** No free, openly licensed source of real ticket prices exists. Free flight-price APIs have closed or turned partner-only, and public datasets are either scraped with unclear licences or US-domestic aggregates. farecast therefore trains on **simulated fares** over a realistic network. Airports, distances and airlines are real, and the pricing rules mirror how fares actually behave (see [How the data is generated](#how-the-data-is-generated)). Estimates are indicative, not live offers.

## Features

- **Search** by city or airport code with autocomplete. A route hint shows the distance, the number of airlines and whether a non-stop flight exists. Airline and cabin menus narrow to what's actually sold on the route.
- **Optional preferences**: a specific airline, a maximum number of stops, and departure time.
- **Boarding-pass result** with the cheapest estimate, likely price range and trip total.
- **Flight list** of every matching itinerary, showing airline, stops, connecting hub, approximate duration, departure time and fare.
- **Savings insights** for ±3 days, booking 1–90 days ahead, and each time of day.
- **Realistic network**:
  - Full-service carriers fly non-stop from their hubs and connect elsewhere (Lufthansa via Frankfurt or Munich, Emirates via Dubai, …).
  - Low-cost carriers (Ryanair, easyJet, Wizz Air, Eurowings, …) only fly point-to-point inside their network.
  - Leisure airlines (Condor, TUI fly, SunExpress) fly from home bases to holiday spots.
- **JSON API** (`POST /api/predict`, `GET /api/route`).
- **Minimal, responsive design** with light and dark themes and system fonts only.
- **Privacy-friendly**: no accounts, cookies, trackers, CDNs or web fonts. Pages make no third-party requests.
- **Reproducible**: one command regenerates the dataset and retrains the model.

## Tech stack

| Layer   | Tech                                                                         |
| ------- | ---------------------------------------------------------------------------- |
| Web     | Flask 3, Jinja templates, plain CSS, a little vanilla JS                     |
| Server  | Waitress (pure-Python WSGI server that also runs on Windows)                 |
| Model   | scikit-learn `HistGradientBoostingRegressor` with native categorical support |
| Data    | Simulated fares over a real airport/airline network (NumPy / pandas)         |
| Tests   | pytest                                                                       |

## Getting started

**Requirements:** Python 3.12 or newer (developed on 3.14).

```bash
git clone https://github.com/hemantb16/flight-fare-predictor.git
cd flight-fare-predictor
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

Install the dependencies and start the app:

```bash
pip install -r requirements.txt
python -m flightfare
```

Open <http://127.0.0.1:8000>.

A trained model ships in `artifacts/`. If it is missing, `python -m flightfare` trains one automatically before starting, which takes about 15 seconds.

### Commands

| Command                                     | What it does                                                        |
| ------------------------------------------- | ------------------------------------------------------------------- |
| `python -m flightfare`                      | Start the server on `127.0.0.1:8000` (trains first if needed)       |
| `python -m flightfare --dev`                | Flask's auto-reloading development server                           |
| `python -m flightfare --host 0.0.0.0 --port 5000` | Listen on another interface or port                           |
| `python -m flightfare.train`                | Regenerate the dataset and retrain (overwrites artifacts)           |
| `python -m flightfare.train --if-missing`   | Train only when no model exists                                     |
| `python -m flightfare.train --rows 400000`  | Train on a larger simulated dataset                                 |

`HOST` and `PORT` environment variables are also respected.

### Run with Docker

```bash
docker compose up --build
```

Or, without Compose:

```bash
docker build -t flight-fare-predictor .
docker run --rm -p 8000:8000 flight-fare-predictor
```

Then open <http://localhost:8000>. The image runs as a non-root user and has a health check on `/health`.

### Run the tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The tests cover the route network rules, model loading and agreement with the pricing rules, holiday dates, input validation, the result page and the JSON API.

## API

### `POST /api/predict`

```json
{
  "origin": "FRA",
  "destination": "JFK",
  "travel_date": "2026-12-11",
  "cabin": "economy",
  "passengers": 2,
  "airline": "any",
  "stops": "any",
  "time_slot": "any"
}
```

| Field         | Values                                                                                     |
| ------------- | ------------------------------------------------------------------------------------------ |
| `origin`, `destination` | IATA code (`"FRA"`), label (`"Frankfurt (FRA)"`) or city name (`"Frankfurt"`)      |
| `travel_date` | `YYYY-MM-DD`, today up to 365 days ahead                                                   |
| `cabin`       | `economy` (default), `premium`, `business`, `first`. Availability depends on airline and distance |
| `passengers`  | 1–9 (default 1)                                                                            |
| `airline`     | `any` (default) or an IATA airline code such as `LH`, `FR`, `EK`                           |
| `stops`       | `any` (default), `0` (non-stop only), `1` (up to one stop)                                 |
| `time_slot`   | `any` (default), `early`, `morning`, `afternoon`, `evening`, `night`                       |
| `booking_date`| Optional, defaults to today. Useful for "what if I had booked earlier" checks.             |

The response holds the cheapest itinerary, the trip total, and all matching itineraries sorted by fare:

```json
{
  "currency": "EUR",
  "origin": "FRA", "destination": "JFK", "travel_date": "2026-12-11",
  "days_before": 30, "distance_km": 6189, "cabin": "economy", "passengers": 2,
  "cheapest": {
    "airline": "IB", "airline_name": "Iberia", "stops": 1, "via": ["MAD"],
    "duration": "11h 30m", "time_slot": "early",
    "fare": 343.52, "range": { "low": 299.41, "high": 395.25 }
  },
  "total": 687.04,
  "itineraries": ["… 16 itineraries, cheapest first …"]
}
```

This example was produced with `"booking_date": "2026-11-11"`. Invalid input returns `400` with an `errors` object keyed by field name.

### `GET /api/route?origin=FRA&destination=JFK`

Returns the distance, the airlines serving the route (and with how many stops), the cabins on sale, and whether a non-stop flight exists.

## How the data is generated

The network lives in [`flightfare/catalog.py`](flightfare/catalog.py) and [`flightfare/network.py`](flightfare/network.py):

- **Airports**: 96 real airports with approximate coordinates, a size class (major hub, large or regional) and a season profile (city, summer beach, or winter sun).
- **Full-service airlines** fly non-stop from their hubs. Medium-haul flights need a large airport at the far end. Flights over 6,000 km need a major hub or a large holiday airport. Elsewhere they connect through a hub when the detour stays reasonable. Two-stop itineraries are only offered where the airline has nothing more direct.
- **Low-cost and leisure airlines** fly point-to-point between their bases and their network, without connections.

About 0.5 % of airport pairs have no plausible itinerary (for example Hamburg–Bremen). The form then suggests a nearby hub.

[`flightfare/pricing.py`](flightfare/pricing.py) simulates 150,000 bookings (fixed seed). Each fare (EUR, one-way, per passenger) is the product of these factors:

| Factor | Logic |
| --- | --- |
| **Base fare** | `fixed + 0.116 × distance^0.94`. The fixed part is €55 for full-service and €30 for low-cost/leisure carriers. |
| **Airline** | Price level per carrier, e.g. Wizz Air ×0.55, Ryanair ×0.58, Eurowings ×0.78, Turkish ×0.95, Lufthansa ×1.15, SWISS ×1.20 |
| **Cabin** | Premium Economy ×1.7–1.9, Business ×2.1–4.7 and First ×6–8, rising with distance. Premium Economy and First only exist on long-haul routes. |
| **Stops** | Non-stop ×1.00, 1 stop ×0.86, 2 stops ×0.78 |
| **Booking window** | U-shaped. Last-minute fares cost up to roughly double, and the rise is steeper for low-cost carriers and much flatter for Business and First. The cheapest window is about 5 weeks ahead on short-haul and about 10 weeks on long-haul, with a slight rise beyond 5 months. |
| **Weekday** | Friday ×1.12 and Sunday ×1.10 are the most expensive. Tuesday ×0.92 and Wednesday ×0.93 are the cheapest. |
| **Season** | Depends on the destination type. Beach destinations peak in July and August (×1.38), winter-sun destinations (Canaries, Dubai, Thailand, Caribbean) in Dec–Mar, and cities follow a milder curve. |
| **Holidays** | Christmas and New Year (18 Dec – 6 Jan) ×1.20. Easter week, computed for every year, ×1.12. |
| **Time of day** | Morning ×1.08, evening ×1.06, afternoon ×1.00, early morning ×0.88, night ×0.86 |
| **Competition** | Routes with more airlines are cheaper: ×1.055 with one carrier down to ×0.88 with eight or more. |
| **Airport demand** | The geometric mean of each airport's popularity score (0.92–1.12) |
| **Noise** | Log-normal with σ = 0.10, about ±10 % random variation |

With these rules, typical economy fares about six weeks out come to roughly:

- €55 for Eurowings Berlin–Munich
- €70 for Ryanair Cologne–Palma
- €110 for Lufthansa Berlin–Munich
- €350 for Condor Frankfurt–New York
- €520 for Lufthansa Frankfurt–New York
- €800 for Singapore Airlines Frankfurt–Singapore

### Model

[`flightfare/train.py`](flightfare/train.py) fits a `HistGradientBoostingRegressor` on `log(1 + price)`. Its inputs are:

- **Categorical features**, handled natively: origin, destination, airline, airline type, cabin, departure time and destination season.
- **Numeric features**: distance, stops, days before departure, weekday, month, holiday flag and number of carriers on the route.

Feature engineering lives in [`flightfare/features.py`](flightfare/features.py) and is shared by training and serving.

On a held-out 20 % test split, the current model scores:

| Metric | Value |
| --- | --- |
| R² | 0.98 |
| MAE | about €58 |
| MAPE | about 8.7 % (the built-in noise alone accounts for about 8 %) |

The likely range on the result page comes from the 10th and 90th percentiles of actual-to-predicted ratios on the test set. Metrics are saved to `artifacts/metrics.json` after each training run.

When no departure time is chosen, each itinerary gets a fixed departure slot derived from the route, airline and stops, much like a timetable. The insights then show what the other times of day would cost.

## Project structure

```
flightfare/
  catalog.py      airports, airlines, cabins, time slots, distance
  network.py      which airlines fly a route, non-stop or via hubs
  pricing.py      fare simulator (documented pricing rules)
  features.py     shared feature engineering, holiday calendar
  train.py        dataset generation + training + evaluation
  model.py        loads the saved pipeline and produces estimates
  validation.py   form / API input validation
  search.py       prices every matching itinerary + insights
  web.py          Flask routes (form, results, JSON API, health)
  __main__.py     `python -m flightfare` entry point (Waitress)
  templates/      Jinja templates
  static/         CSS, JS, favicon
artifacts/        trained model (model.joblib) and metrics.json
tests/            pytest suite
```

## License

[MIT](LICENSE)
