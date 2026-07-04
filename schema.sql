CREATE TABLE regions (
    region_id INT AUTO_INCREMENT PRIMARY KEY,
    region_name VARCHAR(100)
);

CREATE TABLE readings (
    reading_id INT AUTO_INCREMENT PRIMARY KEY,
    region_id INT,
    timestamp DATETIME,
    demand_mw FLOAT,
    FOREIGN KEY (region_id) REFERENCES regions(region_id)
);

CREATE TABLE features (
    feature_id INT AUTO_INCREMENT PRIMARY KEY,
    reading_id INT,
    hour INT,
    dayofweek INT,
    month INT,
    lag_1 FLOAT,
    lag_24 FLOAT,
    lag_7d FLOAT,
    ma_24 FLOAT,
    ma_7d FLOAT,
    FOREIGN KEY (reading_id) REFERENCES readings(reading_id)
);