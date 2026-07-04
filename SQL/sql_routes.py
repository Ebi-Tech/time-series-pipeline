from flask import Flask, jsonify, request
import mysql.connector

app = Flask(__name__)

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="python_user",
        password="1234",
        database="energy_db"
    )

# 1. POST - Add a reading
@app.route("/sql/readings", methods=["POST"])
def create_reading():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO readings (region_id, timestamp, demand_mw) VALUES (%s, %s, %s)",
        (data["region_id"], data["timestamp"], data["demand_mw"])
    )

    conn.commit()
    reading_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return jsonify({"status": "created", "id": reading_id})

# 2. GET - Single reading
@app.route("/sql/readings/<int:id>", methods=["GET"])
def get_reading(id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM readings WHERE reading_id=%s",
        (id,)
    )

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify(result)

# 3. GET - Latest reading
@app.route("/sql/readings/latest", methods=["GET"])
def latest_reading():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1"
    )

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify(result)

# 4. GET - Readings by date range
@app.route("/sql/readings/range", methods=["GET"])
def readings_range():
    start = request.args.get("start")
    end = request.args.get("end")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM readings WHERE timestamp BETWEEN %s AND %s",
        (start, end)
    )

    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(result)

# 5. PUT - Update demand
@app.route("/sql/readings/<int:id>", methods=["PUT"])
def update_reading(id):
    data = request.json

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE readings SET demand_mw=%s WHERE reading_id=%s",
        (data["demand_mw"], id)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"status": "updated"})

# 6. DELETE - Delete a reading
@app.route("/sql/readings/<int:id>", methods=["DELETE"])
def delete_reading(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM readings WHERE reading_id=%s",
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"status": "deleted"})

if __name__ == "__main__":
    app.run(debug=True)