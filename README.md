# ✈ FareCast: Flight Fare Predictor

**Know the fare before you book.** FareCast is a small web app that estimates the price of a one-way flight ticket from the trip details you enter: departure and arrival city, travel date, booking date, airline, cabin class, number of stops, departure time and passengers.

Next to the estimate, the result page shows how the same trip compares across airlines, nearby travel dates, and different booking windows, so you can see where the savings are.

![Python](https://img.shields.io/badge/python-3.12%2B-3776ab) ![Flask](https://img.shields.io/badge/flask-3.1-black) ![scikit--learn](https://img.shields.io/badge/scikit--learn-1.9-f7931e) ![License](https://img.shields.io/badge/license-MIT-blue)

> **Note:** the model is trained on a **simulated** dataset (see [How the data is generated](#how-the-data-is-generated)), and the airlines are fictional. Estimates show realistic patterns, but they are not real airline prices.

## Features

- **Search form** with validation, a swap-cities button, and a live "days before departure" hint. Cabin classes the chosen airline doesn't sell are disabled.
- **Result page** with the estimated fare per passenger, a likely price range, the trip total, the route, distance and approximate flight time.
- **Savings insights**: the same trip with every airline, ±3 days around your travel date, and booking 1 to 90 days ahead.
- **JSON API** at `POST /api/predict` for scripting.
- **Responsive design** with light and dark themes, built on system fonts.
- **Privacy-friendly**: no accounts, cookies, trackers, CDNs or web fonts. The page makes no third-party requests.
- **Reproducible model**: one command regenerates the dataset and retrains the model.

## Tech stack

| Layer   | Tech                                                                      |
| ------- | ------------------------------------------------------------------------- |
| Web     | Flask 3, Jinja templates, plain CSS and a little vanilla JS               |
| Server  | Waitress (pure-Python WSGI server that also runs on Windows)              |
| Model   | scikit-learn `HistGradientBoostingRegressor` + one-hot encoding pipeline  |
| Data    | Synthetic fares generated in code (NumPy / pandas)                        |
| Tests   | pytest                                                                    |

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

A trained model ships in `artifacts/`. If it is missing, `python -m flightfare` trains one automatically before starting, which takes about 10 seconds.

### Commands

| Command                                  | What it does                                                        |
| ---------------------------------------- | ------------------------------------------------------------------- |
| `python -m flightfare`                   | Start the server on `127.0.0.1:8000` (trains first if needed)       |
| `python -m flightfare --dev`             | Start Flask's auto-reloading development server                     |
| `python -m flightfare --host 0.0.0.0 --port 5000` | Listen on another interface or port                        |
| `python -m flightfare.train`             | Regenerate the dataset and retrain the model (overwrites artifacts) |
| `python -m flightfare.train --if-missing`| Train only when no model exists                                     |
| `python -m flightfare.train --rows 200000` | Train on a larger synthetic dataset                               |

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

Then open <http://localhost:8000>. The image runs as a non-root user and includes a health check on `/health`.

### Run the tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The tests cover model loading, agreement with the pricing rules, the result page, the JSON API and input validation.

## API

`POST /api/predict` with a JSON body:

```json
{
  "origin": "FRA",
  "destination": "JFK",
  "travel_date": "2026-12-11",
  "booking_date": "2026-11-11",
  "airline": "MA",
  "cabin": "economy",
  "stops": 0,
  "time_slot": "morning",
  "passengers": 2
}
```

`booking_date` defaults to today and `passengers` defaults to 1. Response:

```json
{
  "currency": "EUR",
  "fare_per_passenger": 887.4,
  "range": { "low": 781.35, "high": 1004.0 },
  "passengers": 2,
  "total": 1774.8,
  "trip": { "origin": "FRA", "destination": "JFK", "days_before": 30, "distance_km": 6189, "...": "..." }
}
```

Invalid input returns `400` with an `errors` object keyed by field name.

**Accepted values**

- **Cities:** `BER MUC FRA HAM DUS CGN STR LHR CDG AMS MAD BCN FCO VIE ZRH CPH LIS ATH IST DXB JFK BKK DEL SIN`
- **Airlines:** `AX` Aerolux, `MA` Meridian Airways (full-service), `SC` Skyway Connect (hybrid), `ZA` Zephyr Air, `BH` BudgetHop (low-cost)
- **Cabins:** `economy`, `premium`, `business`, `first`. Not every airline sells every cabin.
- **Stops:** `0`, `1`, `2` (2 or more)
- **Departure time:** `early` (00–06), `morning` (06–12), `afternoon` (12–17), `evening` (17–21), `night` (21–24)
- **Dates:** travel date must be on or after the booking date and at most 365 days later.

## How the data is generated

No freely licensed, login-free dataset of real ticket prices exists, so the training data is simulated in [`flightfare/pricing.py`](flightfare/pricing.py). The default run creates 60,000 random trips with a fixed seed. Each fare (EUR, one-way, per passenger) is the product of these factors:

| Factor | Logic |
| --- | --- |
| **Base fare** | `18 + 0.35 × distance^0.85`. Distance is the great-circle distance between the airports. Longer flights cost more, but less per km. |
| **Airline** | Aerolux ×1.30, Meridian ×1.15, Skyway ×1.00, Zephyr ×0.80, BudgetHop ×0.68 |
| **Cabin** | Economy ×1. Premium ×1.55 to 1.80, Business ×2.4 to 3.8, First ×4 to 6. The mark-up grows with distance. |
| **Stops** | Non-stop ×1.00, 1 stop ×0.84, 2+ stops ×0.74 |
| **Booking window** | U-shaped. Last-minute bookings cost up to about ×1.95. The cheapest window is about 3 to 10 weeks ahead, and prices rise slightly again beyond 4 months. |
| **Weekday** | Friday ×1.12 and Sunday ×1.10 are the most expensive. Tuesday ×0.92 and Wednesday ×0.93 are the cheapest. |
| **Season** | July and August ×1.25, June ×1.12, February and November ×0.86 to 0.87, plus an extra ×1.18 during the Christmas and New Year peak (18 Dec to 6 Jan). |
| **Time of day** | Morning ×1.08, evening ×1.06, afternoon ×1.00, early morning ×0.88, night ×0.85 |
| **Route demand** | The geometric mean of a popularity score for each airport (0.94 to 1.12) |
| **Noise** | Log-normal with σ = 0.09, which is about ±9 % of random variation per ticket |

### Model

[`flightfare/train.py`](flightfare/train.py) one-hot encodes the categorical features (origin, destination, airline, cabin, time slot). It passes the numeric ones through unchanged: distance, stops, days before departure, weekday, month and the holiday-peak flag. It then fits a `HistGradientBoostingRegressor` on `log(1 + price)`. Feature engineering lives in [`flightfare/features.py`](flightfare/features.py) and is shared by training and serving, so the two can't drift apart.

On a held-out 20 % test split, the current model scores:

| Metric | Value |
| --- | --- |
| R² | 0.98 |
| MAE | about €41 |
| MAPE | about 7.8 % (the built-in noise alone accounts for about 7 %) |

The "likely range" on the result page comes from the 10th and 90th percentiles of actual-to-predicted ratios on that test set. Metrics are saved to `artifacts/metrics.json` after every training run.

## Project structure

```
flightfare/
  catalog.py      airports, airlines, cabins, time slots, distance
  pricing.py      synthetic fare generator (documented pricing logic)
  features.py     shared feature engineering
  train.py        dataset generation + training + evaluation
  model.py        loads the saved pipeline and produces estimates
  validation.py   form / API input validation
  web.py          Flask routes (form, result page, JSON API, health)
  __main__.py     `python -m flightfare` entry point (Waitress)
  templates/      Jinja templates
  static/         CSS, JS, favicon
artifacts/        trained model (model.joblib) and metrics.json
tests/            pytest suite
```

## License

[MIT](LICENSE)
