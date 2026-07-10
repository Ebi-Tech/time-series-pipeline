"""
Combined Flask API for the Time Series Pipeline project.

Merges:
- Member 2's SQL (MySQL) routes, mounted under /sql/...
- Member 3's MongoDB routes, mounted under /mongo/...

Both sets of routes are kept functionally identical to the originals
(sql_routes.py and mongo_routes.py) so behavior for existing valid requests
is unchanged. They are combined into a single Flask app and a single file
so the whole API can be run with one command: `python app.py`.
"""

from datetime import datetime

import mysql.connector
from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request
from pymongo import MongoClient

app = Flask(__name__)

# ---------------------------------------------------------------------------
# MySQL setup
# ---------------------------------------------------------------------------
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "python_user",
    "password": "1234",
    "database": "energy_db",
}


def get_sql_db():
    return mysql.connector.connect(**MYSQL_CONFIG)


# ---------------------------------------------------------------------------
# MongoDB setup
# ---------------------------------------------------------------------------
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB_NAME = "energy_db"
MONGO_COLLECTION_NAME = "readings"

mongo_client = MongoClient(MONGO_URI)


def get_mongo_collection():
    return mongo_client[MONGO_DB_NAME][MONGO_COLLECTION_NAME]


def serialize_mongo(doc):
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    doc["timestamp"] = doc["timestamp"].isoformat()
    return doc


# ===========================================================================
# SQL ROUTES  (/sql/readings...)
# ===========================================================================

# 1. POST - Add a reading
@app.route("/sql/readings", methods=["POST"])
def sql_create_reading():
    data = request.json
    conn = get_sql_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO readings (region_id, timestamp, demand_mw) VALUES (%s, %s, %s)",
        (data["region_id"], data["timestamp"], data["demand_mw"]),
    )

    conn.commit()
    reading_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return jsonify({"status": "created", "id": reading_id})


# 2. GET - Single reading
@app.route("/sql/readings/<int:id>", methods=["GET"])
def sql_get_reading(id):
    conn = get_sql_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM readings WHERE reading_id=%s", (id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify(result)


# 3. GET - Latest reading
@app.route("/sql/readings/latest", methods=["GET"])
def sql_latest_reading():
    conn = get_sql_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1")
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify(result)


# 4. GET - Readings by date range
@app.route("/sql/readings/range", methods=["GET"])
def sql_readings_range():
    start = request.args.get("start")
    end = request.args.get("end")

    conn = get_sql_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM readings WHERE timestamp BETWEEN %s AND %s",
        (start, end),
    )
    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(result)


# 5. PUT - Update demand
@app.route("/sql/readings/<int:id>", methods=["PUT"])
def sql_update_reading(id):
    data = request.json

    conn = get_sql_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE readings SET demand_mw=%s WHERE reading_id=%s",
        (data["demand_mw"], id),
    )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"status": "updated"})


# 6. DELETE - Delete a reading
@app.route("/sql/readings/<int:id>", methods=["DELETE"])
def sql_delete_reading(id):
    conn = get_sql_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM readings WHERE reading_id=%s", (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"status": "deleted"})


# ===========================================================================
# MONGODB ROUTES  (/mongo/readings...)
# ===========================================================================

# 1. POST - Add a reading
@app.route("/mongo/readings", methods=["POST"])
def mongo_create_reading():
    data = request.json
    collection = get_mongo_collection()

    if not data or "timestamp" not in data or "demand_mw" not in data:
        return jsonify({"error": "timestamp and demand_mw are required"}), 400

    try:
        timestamp = datetime.fromisoformat(data["timestamp"])
        demand_mw = float(data["demand_mw"])
    except (ValueError, TypeError):
        return jsonify({"error": "invalid timestamp or demand_mw"}), 400

    document = {
        "region": data.get("region", "PJM East"),
        "timestamp": timestamp,
        "demand_mw": demand_mw,
        "features": data.get("features", {}),
    }

    result = collection.insert_one(document)

    return jsonify({"status": "created", "id": str(result.inserted_id)})


# 2. GET - Single reading
@app.route("/mongo/readings/<id>", methods=["GET"])
def mongo_get_reading(id):
    collection = get_mongo_collection()

    try:
        object_id = ObjectId(id)
    except InvalidId:
        return jsonify({"error": "invalid id"}), 400

    result = collection.find_one({"_id": object_id})

    if result is None:
        return jsonify({"error": "not found"}), 404

    return jsonify(serialize_mongo(result))


# 3. GET - Latest reading
@app.route("/mongo/readings/latest", methods=["GET"])
def mongo_latest_reading():
    collection = get_mongo_collection()
    result = collection.find_one(sort=[("timestamp", -1)])
    return jsonify(serialize_mongo(result))


# 4. GET - Readings by date range
@app.route("/mongo/readings/range", methods=["GET"])
def mongo_readings_range():
    start = request.args.get("start")
    end = request.args.get("end")

    collection = get_mongo_collection()

    cursor = collection.find(
        {"timestamp": {"$gte": datetime.fromisoformat(start), "$lte": datetime.fromisoformat(end)}}
    ).sort("timestamp", 1)

    return jsonify([serialize_mongo(doc) for doc in cursor])


# 5. PUT - Update demand
@app.route("/mongo/readings/<id>", methods=["PUT"])
def mongo_update_reading(id):
    data = request.json
    collection = get_mongo_collection()

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
def mongo_delete_reading(id):
    collection = get_mongo_collection()

    try:
        object_id = ObjectId(id)
    except InvalidId:
        return jsonify({"error": "invalid id"}), 400

    result = collection.delete_one({"_id": object_id})

    if result.deleted_count == 0:
        return jsonify({"error": "not found"}), 404

    return jsonify({"status": "deleted"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)