"""Transformation : lecture, fusion et contrôles de qualité."""
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

BASE_DIR = Path(os.getenv("PROJECT_ROOT", "."))
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# Plages plausibles pour repérer des valeurs aberrantes
RANGES = {
    "temperature_2m": (10, 50),
    "relative_humidity_2m": (0, 100),
    "precipitation": (0, 200),
    "wind_speed_10m": (0, 150),
    "pm10": (0, 1000),
    "pm2_5": (0, 1000),
    "nitrogen_dioxide": (0, 1000),
    "ozone": (0, 1000),
    "us_aqi": (0, 500),
}


def read_hourly(path, city):
    """Lit un JSON brut et retourne un DataFrame horaire."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df.insert(0, "city", city)
    return df


def transform(weather_path, air_path, city="Dakar"):
    """Fusionne météo et qualité de l'air sur (ville, heure)."""
    weather = read_hourly(weather_path, city)
    air = read_hourly(air_path, city)
    df = weather.merge(air, on=["city", "time"], how="outer", validate="one_to_one")
    return df.sort_values("time").reset_index(drop=True)


def check_quality(df, expected_rows=24):
    """Retourne la liste des problèmes détectés (vide si tout va bien)."""
    problems = []
    if df.duplicated(["city", "time"]).any():
        problems.append("doublons sur (city, time)")
    if len(df) != expected_rows:
        problems.append(f"{len(df)} lignes au lieu de {expected_rows}")
    nulls = df.isna().sum()
    for col, n in nulls[nulls > 0].items():
        problems.append(f"{n} valeurs manquantes dans {col}")
    for col, (low, high) in RANGES.items():
        bad = df[(df[col] < low) | (df[col] > high)]
        if not bad.empty:
            problems.append(f"{len(bad)} valeurs hors plage dans {col}")
    return problems


if __name__ == "__main__":
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today() - timedelta(days=1)
    df = transform(RAW_DIR / f"weather_dakar_{day}.json", RAW_DIR / f"air_dakar_{day}.json")
    problems = check_quality(df)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / f"dakar_{day}.csv"
    df.to_csv(out, index=False)
    print(df.head())
    print(df.dtypes)
    print("Problèmes détectés :", problems or "aucun")
    print(f"Fichier écrit : {out}")