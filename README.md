# Time Series Pipeline — Electricity Demand Forecasting

Group project for the Data Engineering formative: a full pipeline that takes
hourly electricity demand data (PJM East, `PJME_hourly.csv`) from raw CSV to
a trained forecasting model served behind a REST API.

## Project Structure

```
time-series-pipeline/
├── data/
│   ├── PJME_hourly.csv          # raw source data
│   └── cleaned_data.csv         # cleaned + feature-engineered (Task 1 output)
├── models/
│   └── electricity_forecast_model.pkl   # trained Ridge regression model
├── MongoDB/
│   ├── mongo_setup.py           # loads cleaned_data.csv into MongoDB
│   ├── mongo_routes.py          # standalone Mongo Flask routes (reference)
│   ├── mongo_queries.py         # 3 sample queries + results
│   ├── query_results.md
│   └── sample_documents.json
├── SQL/
│   ├── schema.sql                # 3-table relational schema
│   ├── load_data.py              # loads cleaned_data.csv into MySQL
│   └── sql_routes.py             # standalone SQL Flask routes (reference)
├── notebooks/
│   └── task1_time_series_forecasting.ipynb   # EDA, feature engineering, model training
├── app.py                        # combined Flask API (SQL + Mongo routes)
├── predict.py                    # Task 4: fetch → preprocess → predict
├── requirements.txt               # pinned dependencies (pip freeze)
└── README.md
```

## Prerequisites

- **Python 3.10+** (tested with 3.14 on macOS). Use `python3` / `pip3` on
  macOS/Linux; `python` may not resolve.
- **MongoDB Community Server** running locally on port 27017.
- **MySQL Server** running locally, with a database named `energy_db`.
- **Homebrew** (macOS) is the easiest way to install/manage both database
  servers below.

## Setup

### 1. Create a virtual environment and install dependencies

macOS's system Python is "externally managed" (PEP 668), so installing
packages directly with `pip3 install` will fail with an
`externally-managed-environment` error. Use a virtual environment instead:

```bash
python3 -m venv venv
source venv/bin/activate        # re-run this every time you open a new terminal
pip install -r requirements.txt
```

`requirements.txt` (generated with `pip freeze` from the working
environment) pins the exact versions used to build and test this project.

### 2. Install and start MongoDB (macOS / Homebrew)

If `brew services list` doesn't show `mongodb-community`, it isn't
installed yet:

```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

Verify it's running:

```bash
brew services list   # should show mongodb-community as "started"
```

If you're not on macOS, install MongoDB Community Server for your OS from
the official MongoDB docs and ensure it's listening on `localhost:27017`.

### 3. Install and start MySQL

```bash
brew install mysql
brew services start mysql
```

Then create the database:

```bash
mysql -u root -p -e "CREATE DATABASE energy_db;"
```

Update the credentials in `app.py` (`MYSQL_CONFIG`) to match your local
MySQL user/password if they differ from the defaults.

### 4. Load the data into both databases

**MongoDB:**

```bash
cd MongoDB
python3 mongo_setup.py
```

A `Connection refused` error here means MongoDB isn't running, go back to
step 2.

**MySQL:**

```bash
mysql -u root -p energy_db < SQL/schema.sql
cd SQL
python3 load_data.py
```

### 5. Run the API

```bash
python3 app.py
```

This starts a single Flask server on `http://localhost:5000` exposing both
sets of endpoints:

| Method | SQL endpoint | Mongo endpoint |
|---|---|---|
| POST | `/sql/readings` | `/mongo/readings` |
| GET | `/sql/readings/<id>` | `/mongo/readings/<id>` |
| GET | `/sql/readings/latest` | `/mongo/readings/latest` |
| GET | `/sql/readings/range?start=...&end=...` | `/mongo/readings/range?start=...&end=...` |
| PUT | `/sql/readings/<id>` | `/mongo/readings/<id>` |
| DELETE | `/sql/readings/<id>` | `/mongo/readings/<id>` |

### 6. Run a prediction

With `app.py` running in one terminal, open a second terminal, activate the
venv again (`source venv/bin/activate`), and run:

```bash
python3 predict.py
```

This fetches the latest reading from the API, builds the feature vector the
model expects, and prints a demand forecast alongside the actual recorded
value for comparison.

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `zsh: command not found: python` | macOS aliases the command as `python3`, not `python` | Use `python3` / `pip3` throughout |
| `ModuleNotFoundError: No module named 'pandas'` (or similar) | Dependencies not installed in the active environment | `source venv/bin/activate` then `pip install -r requirements.txt` |
| `error: externally-managed-environment` | macOS/Homebrew Python blocks global `pip install` (PEP 668) | Use a virtual environment (see Setup step 1) instead of installing globally |
| `pymongo.errors.ServerSelectionTimeoutError: ... Connection refused` | MongoDB server isn't installed or isn't running | Run `brew services list` to check; install/start with the commands in Setup step 2 |
| `mysql.connector.errors.*` connection errors | MySQL isn't running, or `energy_db` doesn't exist, or credentials in `app.py` don't match | Confirm `brew services list` shows mysql started; re-check `MYSQL_CONFIG` in `app.py` |
| `predict.py` fails with a connection error | `app.py` isn't running | Start `python3 app.py` in a separate terminal first, then re-run `predict.py` |

## Why predict.py queries MongoDB, not SQL

Both databases were required for Tasks 2 and 3 to demonstrate two different
schema design approaches on the same dataset: a normalized relational model
(`regions`, `readings`, `features` tables with foreign keys) and a
denormalized document model (each reading embeds its own features).

Task 4 only requires fetching from "your API," not both. We chose the Mongo
endpoint because the model was trained on exactly the feature set
(`lag_1, lag_24, lag_7d, ma_24, ma_7d, hour, dayofweek, month`) that Mongo
already embeds directly in each document. Fetching the same features from
SQL would require a second query to join the `features` table onto
`readings` via `reading_id`, adding complexity without changing the result.
This reflects a real difference in what each schema is optimized for: SQL
keeps data normalized for integrity, Mongo optimizes for read simplicity,
and we picked the one suited to this specific read pattern.

## Model

- **Algorithm:** Ridge Regression (scikit-learn), selected over a Linear
  Regression baseline after tuning `alpha` across `[0.01, 0.1, 1, 10, 100]`
  using a chronological (non-shuffled) train/test split.
- **Features:** `lag_1`, `lag_24`, `lag_7d`, `ma_24`, `ma_7d`, `hour`,
  `dayofweek`, `month`
- **Target:** `PJME_MW` (hourly electricity demand in megawatts)
- **Artifact:** `models/electricity_forecast_model.pkl` (saved with `joblib`)

See `notebooks/task1_time_series_forecasting.ipynb` for the full EDA,
feature engineering rationale, and experiment comparison table.

## Team Contributions

| Member | Task | Contribution |
|---|---|---|
| Member 1 | Task 1 | EDA, feature engineering, model training & tuning (notebook, cleaned_data.csv, model artifact) |
| Member 2 | Task 2/3 (SQL) | Relational schema design, ERD, SQL CRUD routes |
| Member 3 | Task 2/3 (MongoDB) | Document schema design, data loader, sample queries, Mongo CRUD routes |
| Member 4 | Task 3/4 + Report | Combined API (app.py), prediction script (predict.py), repo structure, README, final report |