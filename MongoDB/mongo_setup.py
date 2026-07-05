"""
Loads the team's cleaned energy-demand CSV into MongoDB.

Collection design (denormalized, one document per hourly reading):

{
    "_id": ObjectId,
    "region": "PJM East",
    "timestamp": ISODate("2002-01-08T01:00:00Z"),
    "demand_mw": 29445.0,
    "features": {
        "hour": 1,
        "dayofweek": 1,
        "month": 1,
        "lag_1": 31187.0,
        "lag_24": 26862.0,
        "lag_7d": 30393.0,
        "ma_24": 33560.208333333336,
        "ma_7d": 32513.869047619046
    }
}

We embed the calendar/lag/moving-average features inside each reading instead
of splitting them into a separate collection (the way the SQL side splits
`readings` from `features`) because MongoDB favors denormalized documents:
every query in this project reads a reading together with its features, so
there is no benefit to a second collection/join, only extra round trips.
"""

import pandas as pd
from pymongo import MongoClient, ASCENDING

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "energy_db"
COLLECTION_NAME = "readings"
CSV_PATH = "../data/cleaned_data.csv"
REGION_NAME = "PJM East"
BATCH_SIZE = 5000


def build_document(row: pd.Series) -> dict:
    return {
        "region": REGION_NAME,
        "timestamp": row["Datetime"].to_pydatetime(),
        "demand_mw": float(row["PJME_MW"]),
        "features": {
            "hour": int(row["hour"]),
            "dayofweek": int(row["dayofweek"]),
            "month": int(row["month"]),
            "lag_1": float(row["lag_1"]),
            "lag_24": float(row["lag_24"]),
            "lag_7d": float(row["lag_7d"]),
            "ma_24": float(row["ma_24"]),
            "ma_7d": float(row["ma_7d"]),
        },
    }


def main():
    print("Reading CSV...")
    df = pd.read_csv(CSV_PATH, parse_dates=["Datetime"])
    print(f"Loaded {len(df)} rows from {CSV_PATH}")

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    collection.delete_many({})
    print(f"Cleared existing documents in {DB_NAME}.{COLLECTION_NAME}")

    documents = (build_document(row) for _, row in df.iterrows())

    batch = []
    inserted = 0
    for doc in documents:
        batch.append(doc)
        if len(batch) >= BATCH_SIZE:
            collection.insert_many(batch)
            inserted += len(batch)
            print(f"{inserted} documents inserted...")
            batch = []

    if batch:
        collection.insert_many(batch)
        inserted += len(batch)

    print(f"Finished! {inserted} documents inserted into {DB_NAME}.{COLLECTION_NAME}")

    collection.create_index([("timestamp", ASCENDING)], unique=True)
    print("Created ascending unique index on 'timestamp'")

    client.close()


if __name__ == "__main__":
    main()
