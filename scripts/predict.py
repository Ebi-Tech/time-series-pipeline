"""
predict.py

Consolidates Tasks 1-3 into a single forecasting script:

1. Fetch a time-series record from the running API (Mongo endpoint).
2. Preprocess it into the exact feature vector the model was trained on.
3. Load the trained Ridge regression model (electricity_forecast_model.pkl).
4. Produce a demand forecast (PJME_MW) for that record.

Why the Mongo endpoint and not SQL:
The SQL schema normalizes a reading and its engineered features into two
separate tables (readings, features) linked by reading_id. The MongoDB
schema embeds the engineered features directly inside each reading document.
Since the model was trained on exactly the feature set that Mongo already
embeds (lag_1, lag_24, lag_7d, ma_24, ma_7d, hour, dayofweek, month), fetching
from /mongo/readings/latest gives a complete, ready-to-use feature vector in
a single API call. Fetching the same features from SQL would require a
second query to join `features` onto `readings` by reading_id, which adds
complexity without changing the prediction. This is a deliberate design
choice reflecting the read pattern each database is suited for, not an
oversight: SQL keeps the two tables normalized for referential integrity
(Tasks 2/3), while Mongo is used here for retrieval simplicity (Task 4).
"""

import sys

import joblib
import requests

API_BASE_URL = "http://localhost:5000"
MODEL_PATH = "models/electricity_forecast_model.pkl"

# Must match the exact order of columns the model was trained on in
# task1_time_series_forecasting.ipynb (see the `features` list, Cell 69).
FEATURE_ORDER = ["lag_1", "lag_24", "lag_7d", "ma_24", "ma_7d", "hour", "dayofweek", "month"]


def fetch_latest_record(base_url: str = API_BASE_URL) -> dict:
    """Fetch the most recent reading from the MongoDB API endpoint."""
    response = requests.get(f"{base_url}/mongo/readings/latest", timeout=10)
    response.raise_for_status()
    record = response.json()

    if not record:
        raise ValueError("No reading was returned by the API.")

    return record


def preprocess(record: dict) -> list:
    """
    Extract and order the engineered features from a fetched record into
    the exact vector shape the model expects.

    Mirrors the feature engineering performed in Task 1: the record's
    "features" sub-document already contains the lag features, moving
    averages, and calendar features (hour, dayofweek, month) computed the
    same way as in the notebook, so no recomputation is needed here.
    """
    features = record.get("features")
    if not features:
        raise ValueError("Record is missing the 'features' field required for prediction.")

    missing = [f for f in FEATURE_ORDER if f not in features]
    if missing:
        raise ValueError(f"Record is missing required feature(s): {missing}")

    return [[features[name] for name in FEATURE_ORDER]]


def load_model(model_path: str = MODEL_PATH):
    return joblib.load(model_path)


def main():
    print("Fetching latest record from API...")
    record = fetch_latest_record()
    print(f"Fetched reading from {record.get('timestamp')} (region: {record.get('region')})")

    print("Preprocessing features...")
    feature_vector = preprocess(record)
    print(f"Feature vector ({FEATURE_ORDER}): {feature_vector[0]}")

    print("Loading trained model...")
    model = load_model()

    print("Generating forecast...")
    prediction = model.predict(feature_vector)

    actual_demand = record.get("demand_mw")
    print("\n--- Forecast Result ---")
    print(f"Timestamp:         {record.get('timestamp')}")
    print(f"Actual demand_mw:  {actual_demand}")
    print(f"Predicted demand:  {prediction[0]:.2f} MW")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not reach the API. Make sure app.py is running (python app.py).")
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)