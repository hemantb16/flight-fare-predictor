"""Start the web server: ``python -m flightfare``.

Trains the model first if no saved artifacts exist, then serves the app with
Waitress (a production-grade, pure-Python WSGI server that also runs on Windows).
"""

from __future__ import annotations

import argparse
import os

from .model import MODEL_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Flight Fare Predictor web app.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--dev", action="store_true", help="use Flask's auto-reloading dev server")
    args = parser.parse_args()

    if not MODEL_PATH.exists():
        from .train import train

        print("No trained model found; training one now ...")
        train()

    from .web import create_app

    app = create_app()
    if args.dev:
        app.run(host=args.host, port=args.port, debug=True)
        return

    from waitress import serve

    print(f"Flight Fare Predictor running at http://{args.host}:{args.port}")
    serve(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
