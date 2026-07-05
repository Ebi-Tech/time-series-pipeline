# MongoDB part (Task 2 & 3)

## Collection design

One collection, `energy_db.readings`, one document per hourly reading.
Denormalized on purpose: the calendar/lag/moving-average features that the
SQL side keeps in a separate `features` table are embedded here, because
every query in this project needs a reading together with its features and
MongoDB has no cheap join.

```json
{
  "_id": "ObjectId('...')",
  "region": "PJM East",
  "timestamp": "2002-01-08T01:00:00",
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
```

Index: ascending unique index on `timestamp` (supports the "latest" and
"range" queries, and prevents duplicate hourly readings).

## Files

- `mongo_setup.py` — reads `../data/cleaned_data.csv` and loads it into
  `energy_db.readings`, then creates the index.
- `mongo_routes.py` — Flask app exposing 6 endpoints (runs on port 5001 so
  it doesn't collide with the SQL Flask app).
- `mongo_queries.py` — 3 sample queries (latest reading, ranged filter,
  aggregation) run directly against the collection.
- `sample_documents.json` — example documents for the report/README.

## One-time setup

1. Install MongoDB Community Server. Either:
   - **Windows service (normal case):**
     ```
     winget install --id MongoDB.Server -e
     winget install --id MongoDB.Shell -e
     ```
     Accept the UAC prompt when it appears. This installs `mongod` as a
     Windows service (`MongoDB`) listening on `localhost:27017`, started
     automatically on boot.
   - **Portable, no admin rights** (what this machine actually uses, since
     this session had no interactive desktop to approve the UAC prompt):
     download `mongodb-windows-x86_64-8.3.4.zip` from
     `https://fastdl.mongodb.org/windows/`, extract it, then run
     ```
     mongod.exe --dbpath <some-folder-for-data> --port 27017
     ```
     in its own terminal window and leave it running. There's no service to
     restart — just re-run that command each time you want the database up.
2. Install the Python driver and Flask:
   ```
   pip install pymongo flask
   ```
3. Load the data:
   ```
   cd MongoDB
   python mongo_setup.py
   ```

## Running the API

```
cd MongoDB
python mongo_routes.py
```

Endpoints (base `http://localhost:5001`):

| Method | Path                      | Purpose                    |
|--------|---------------------------|-----------------------------|
| POST   | `/mongo/readings`         | Create a reading            |
| GET    | `/mongo/readings/<id>`    | Get one reading by id       |
| GET    | `/mongo/readings/latest`  | Get the most recent reading |
| GET    | `/mongo/readings/range?start=...&end=...` | Readings between two ISO timestamps |
| PUT    | `/mongo/readings/<id>`    | Update `demand_mw`           |
| DELETE | `/mongo/readings/<id>`    | Delete a reading             |

## Sample queries

Run `python mongo_queries.py` for the three demo queries; results are also
in the group report.
