"""Generate the synthetic dataset, train the fare model and save the artifacts.

Usage:
    python -m flightfare.train               # (re)train and overwrite artifacts
    python -m flightfare.train --if-missing  # only train when no model exists
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from .features import CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES
from .model import ARTIFACT_DIR, METRICS_PATH, MODEL_PATH, PROJECT_ROOT
from .pricing import generate_dataset

DATA_PATH = PROJECT_ROOT / "data" / "flights.csv"
SEED = 42


def build_pipeline() -> Pipeline:
    # Categories are ordinal-encoded and handled natively by the gradient-boosting
    # model, which is faster and more accurate here than one-hot encoding.
    preprocess = ColumnTransformer(
        [
            (
                "cat",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                CATEGORICAL_FEATURES,
            ),
            ("num", "passthrough", NUMERIC_FEATURES),
        ]
    )
    n_cat = len(CATEGORICAL_FEATURES)
    model = HistGradientBoostingRegressor(
        max_iter=900,
        learning_rate=0.08,
        max_leaf_nodes=63,
        l2_regularization=0.1,
        categorical_features=[i < n_cat for i in range(n_cat + len(NUMERIC_FEATURES))],
        random_state=SEED,
    )
    return Pipeline([("preprocess", preprocess), ("model", model)])


def train(n_rows: int = 150_000) -> dict:
    started = time.perf_counter()
    print(f"Generating {n_rows:,} synthetic flights ...")
    df = generate_dataset(n_rows=n_rows, seed=SEED)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_PATH, index=False)

    X, y = df[FEATURES], df["price"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)

    print("Training HistGradientBoostingRegressor ...")
    pipeline = build_pipeline()
    pipeline.fit(X_train, np.log1p(y_train))

    pred = np.expm1(pipeline.predict(X_test))
    ratio = y_test.to_numpy() / pred
    metrics = {
        "rows": n_rows,
        "test_rows": len(X_test),
        "mae_eur": round(float(mean_absolute_error(y_test, pred)), 2),
        "mape": round(float(mean_absolute_percentage_error(y_test, pred)), 4),
        "r2": round(float(r2_score(y_test, pred)), 4),
        "ratio_p10": round(float(np.percentile(ratio, 10)), 4),
        "ratio_p90": round(float(np.percentile(ratio, 90)), 4),
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH, compress=3)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    elapsed = time.perf_counter() - started
    print(
        f"Done in {elapsed:.1f}s  |  MAE EUR {metrics['mae_eur']}  |  "
        f"MAPE {metrics['mape']:.1%}  |  R2 {metrics['r2']}"
    )
    print(f"Saved {MODEL_PATH.relative_to(PROJECT_ROOT)} and {METRICS_PATH.relative_to(PROJECT_ROOT)}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the flight fare model.")
    parser.add_argument("--if-missing", action="store_true", help="skip if a model already exists")
    parser.add_argument("--rows", type=int, default=150_000, help="number of synthetic flights")
    args = parser.parse_args()
    if args.if_missing and MODEL_PATH.exists():
        print(f"Model already present at {MODEL_PATH.relative_to(PROJECT_ROOT)}; skipping training.")
        return
    train(n_rows=args.rows)


if __name__ == "__main__":
    main()
