CREATE TABLE IF NOT EXISTS dim_city (
    city_id    SERIAL PRIMARY KEY,
    city_name  TEXT NOT NULL UNIQUE,
    country    TEXT NOT NULL,
    latitude   DOUBLE PRECISION NOT NULL,
    longitude  DOUBLE PRECISION NOT NULL,
    timezone   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id      INTEGER PRIMARY KEY,          -- format AAAAMMJJ
    full_date    DATE NOT NULL UNIQUE,
    year         SMALLINT NOT NULL,
    month        SMALLINT NOT NULL,
    day          SMALLINT NOT NULL,
    day_of_week  SMALLINT NOT NULL,            -- 1 = lundi ... 7 = dimanche
    is_weekend   BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_aqi_category (
    category_id    SMALLINT PRIMARY KEY,
    category_name  TEXT NOT NULL,
    min_aqi        SMALLINT NOT NULL,
    max_aqi        SMALLINT NOT NULL
);

INSERT INTO dim_aqi_category (category_id, category_name, min_aqi, max_aqi) VALUES
    (1, 'Bon', 0, 50),
    (2, 'Modéré', 51, 100),
    (3, 'Mauvais pour les groupes sensibles', 101, 150),
    (4, 'Mauvais', 151, 200),
    (5, 'Très mauvais', 201, 300),
    (6, 'Dangereux', 301, 500)
ON CONFLICT (category_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS fact_air_weather_hourly (
    city_id                INTEGER NOT NULL REFERENCES dim_city(city_id),
    date_id                INTEGER NOT NULL REFERENCES dim_date(date_id),
    hour                   SMALLINT NOT NULL CHECK (hour BETWEEN 0 AND 23),
    aqi_category_id        SMALLINT REFERENCES dim_aqi_category(category_id),
    temperature_c          REAL,
    relative_humidity_pct  REAL,
    precipitation_mm       REAL,
    wind_speed_kmh         REAL,
    pm10                   REAL,
    pm2_5                  REAL,
    nitrogen_dioxide       REAL,
    ozone                  REAL,
    us_aqi                 SMALLINT,
    loaded_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (city_id, date_id, hour)
);