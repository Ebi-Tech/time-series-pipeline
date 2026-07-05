from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request
from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "energy_db"
COLLECTION_NAME = "readings"


def get_collection():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME][COLLECTION_NAME]


def serialize(doc):
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    doc["timestamp"] = doc["timestamp"].isoformat()
    return doc


# 1. POST - Add a reading
@app.route("/mongo/readings", methods=["POST"])
def create_reading():
    data = request.json
    collection = get_collection()

    document = {
        "region": data.get("region", "PJM East"),
        "timestamp": datetime.fromisoformat(data["timestamp"]),
        "demand_mw": float(data["demand_mw"]),
        "features": data.get("features", {}),
    }

    result = collection.insert_one(document)

    return jsonify({"status": "created", "id": str(result.inserted_id)})


# 2. GET - Single reading
@app.route("/mongo/readings/<id>", methods=["GET"])
def get_reading(id):
    collection = get_collection()

    try:
        object_id = ObjectId(id)
    except InvalidId:
        return jsonify({"error": "invalid id"}), 400

    result = collection.find_one({"_id": object_id})

    if result is None:
        return jsonify({"error": "not found"}), 404

    return jsonify(serialize(result))


# 3. GET - Latest reading
@app.route("/mongo/readings/latest", methods=["GET"])
def latest_reading():
    collection = get_collection()

    result = collection.find_one(sort=[("timestamp", -1)])

    return jsonify(serialize(result))


# 4. GET - Readings by date range
@app.route("/mongo/readings/range", methods=["GET"])
def readings_range():
    start = request.args.get("start")
    end = request.args.get("end")

    collection = get_collection()

    cursor = collection.find(
        {"timestamp": {"$gte": datetime.fromisoformat(start), "$lte": datetime.fromisoformat(end)}}
    ).sort("timestamp", 1)

    return jsonify([serialize(doc) for doc in cursor])


# 5. PUT - Update demand
@app.route("/mongo/readings/<id>", methods=["PUT"])
def update_reading(id):
    data = request.json
    collection = get_collection()

    try:
        object_id = ObjectId(id)
    except InvalidId:
        return jsonify({"error": "invalid id"}), 400

    result = collection.update_one({"_id": object_id}, {"$set": {"demand_mw": float(data["demand_mw"])}})

    if result.matched_count == 0:
        return jsonify({"error": "not found"}), 404

    return jsonify({"status": "updated"})


# 6. DELETE - Delete a reading
@app.route("/mongo/readings/<id>", methods=["DELETE"])
def delete_reading(id):
    collection = get_collection()

    try:
        object_id = ObjectId(id)
    except InvalidId:
        return jsonify({"error": "invalid id"}), 400

    result = collection.delete_one({"_id": object_id})

    if result.deleted_count == 0:
        return jsonify({"error": "not found"}), 404

    return jsonify({"status": "deleted"})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
