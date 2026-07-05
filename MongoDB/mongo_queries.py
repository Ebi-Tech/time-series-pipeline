"""Three sample MongoDB queries against the `energy_db.readings` collection."""

from datetime import datetime
from pprint import pprint

from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
collection = client["energy_db"]["readings"]

# 1. Simple find + sort: latest reading in the collection
print("=== Query 1: Latest reading ===")
latest = collection.find_one(sort=[("timestamp", -1)])
pprint(latest)

# 2. Range + condition: high-demand hours in the first week of July 2018 (summer peak)
print("\n=== Query 2: Readings in a date range with demand_mw > 45000 ===")
cursor = collection.find(
    {
        "timestamp": {
            "$gte": datetime(2018, 7, 1),
            "$lte": datetime(2018, 7, 7),
        },
        "demand_mw": {"$gt": 45000},
    }
).sort("timestamp", 1)
for doc in cursor:
    print(doc["timestamp"], doc["demand_mw"])

# 3. Aggregation pipeline: average demand per month across the whole series
print("\n=== Query 3: Average demand_mw grouped by month ===")
pipeline = [
    {"$group": {"_id": "$features.month", "avg_demand_mw": {"$avg": "$demand_mw"}, "count": {"$sum": 1}}},
    {"$sort": {"_id": 1}},
]
for doc in collection.aggregate(pipeline):
    print(f"Month {doc['_id']}: avg={doc['avg_demand_mw']:.2f} MW over {doc['count']} readings")

client.close()
