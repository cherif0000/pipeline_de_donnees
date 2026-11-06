"""Chargement dans PostgreSQL (entrepôt en étoile) avec upsert idempotent."""
import os
import sys
from datetime import date, timedelta

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from src.extract import CITIES
from src.transform import RAW_DIR, check_quality, transform

load_dotenv()

COUNTRIES = {"Dakar": "Sénégal"}

FACT_COLUMNS = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "relative_humidity_pct",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_kmh",
    "pm10": "pm10",
    "pm2_5": "pm2_5",
    "nitrogen_dioxide": "nitrogen_dioxide",
    "ozone": "ozone",
    "us_aqi": "us_aqi",
}


def get_engine():
    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )
    return create_engine(url)


def aqi_category_id(aqi):
    """Catégorie US AQI : 1 = Bon ... 6 = Dangereux."""
    if pd.isna(aqi):
        return None
    for category_id, upper in ((1, 50), (2, 100), (3, 150), (4, 200), (5, 300)):
        if aqi <= upper:
            return category_id
    return 6


def upsert_city(conn, name, info):
    row = conn.execute(
        text("""
            INSERT INTO dim_city (city_name, country, latitude, longitude, timezone)
            VALUES (:name, :country, :lat, :lon, :tz)
            ON CONFLICT (city_name) DO UPDATE
               SET latitude = EXCLUDED.latitude,
                   longitude = EXCLUDED.longitude,
                   timezone = EXCLUDED.timezone
            RETURNING city_id
        """),
        {"name": name, "country": COUNTRIES[name], "lat": info["latitude"],
         "lon": info["longitude"], "tz": info["timezone"]},
    ).one()
    return row[0]


def upsert_dates(conn, df):
    rows = []
    for d in sorted(df["time"].dt.date.unique()):
        rows.append({
            "date_id": int(d.strftime("%Y%m%d")), "full_date": d,
            "year": d.year, "month": d.month, "day": d.day,
            "dow": d.isoweekday(), "weekend": d.isoweekday() >= 6,
        })
    conn.execute(
        text("""
            INSERT INTO dim_date (date_id, full_date, year, month, day, day_of_week, is_weekend)
            VALUES (:date_id, :full_date, :year, :month, :day, :dow, :weekend)
            ON CONFLICT (date_id) DO NOTHING
        """),
        rows,
    )


def load_facts(conn, df, city_id):
    out = df.rename(columns=FACT_COLUMNS).copy()
    out["city_id"] = city_id
    out["date_id"] = out["time"].dt.strftime("%Y%m%d").astype(int)
    out["hour"] = out["time"].dt.hour
    out["aqi_category_id"] = pd.Series(
        [aqi_category_id(v) for v in out["us_aqi"]], index=out.index, dtype=object)
    cols = ["city_id", "date_id", "hour", "aqi_category_id", *FACT_COLUMNS.values()]
    out = out[cols].astype(object)
    out = out.where(out.notna(), None)          # NaN -> NULL
    records = out.to_dict("records")

    value_cols = list(FACT_COLUMNS.values()) + ["aqi_category_id"]
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in value_cols)
    sql = text(f"""
        INSERT INTO fact_air_weather_hourly ({", ".join(cols)})
        VALUES ({", ".join(":" + c for c in cols)})
        ON CONFLICT (city_id, date_id, hour) DO UPDATE
           SET {updates}, loaded_at = now()
    """)
    conn.execute(sql, records)
    return len(records)


def run(day, city="Dakar"):
    df = transform(RAW_DIR / f"weather_{city.lower()}_{day}.json",
                   RAW_DIR / f"air_{city.lower()}_{day}.json", city=city)
    problems = check_quality(df)
    if problems:
        sys.exit(f"Chargement annulé, problèmes de qualité : {problems}")
    engine = get_engine()
    with engine.begin() as conn:                # transaction : tout ou rien
        city_id = upsert_city(conn, city, CITIES[city])
        upsert_dates(conn, df)
        n = load_facts(conn, df, city_id)
    print(f"{n} lignes chargées pour {city} le {day}")


if __name__ == "__main__":
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today() - timedelta(days=1)
    run(day)