import pandas as pd
import mysql.connector

# Read CSV
df = pd.read_csv("../data/cleaned_data.csv")

print("CSV loaded successfully.")
print("Number of rows:", len(df))

# Connect to MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="python_user",
    password="1234",
    database="energy_db"
)

cursor = conn.cursor()

# Insert one region
cursor.execute("INSERT INTO regions (region_name) VALUES (%s)", ("PJM East",))
region_id = cursor.lastrowid

count = 0

for _, row in df.iterrows():

    cursor.execute(
        """
        INSERT INTO readings (region_id, timestamp, demand_mw)
        VALUES (%s, %s, %s)
        """,
        (
            region_id,
            row["Datetime"],
            float(row["PJME_MW"])
        )
    )

    reading_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO features
        (reading_id, hour, dayofweek, month,
         lag_1, lag_24, lag_7d, ma_24, ma_7d)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            reading_id,
            int(row["hour"]),
            int(row["dayofweek"]),
            int(row["month"]),
            float(row["lag_1"]),
            float(row["lag_24"]),
            float(row["lag_7d"]),
            float(row["ma_24"]),
            float(row["ma_7d"])
        )
    )

    count += 1

    if count % 1000 == 0:
        print(f"{count} rows inserted...")

conn.commit()

cursor.close()
conn.close()

print("Finished!")