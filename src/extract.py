"""Extraction des données météo et qualité de l'air (Open-Meteo)."""
import json
import os
from datetime import date, timedelta
from pathlib import Path

import requests

CITIES = {
    "Dakar": {"latitude": 14.6937, "longitude": -17.4441, "timezone": "Africa/Dakar"},
}

SOURCES = {
    "weather": {
        "url": "https://api.open-meteo.com/v1/forecast",
        "variables": ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"],
    },
    "air": {
        "url": "https://air-quality-api.open-meteo.com/v1/air-quality",
        "variables": ["pm10", "pm2_5", "nitrogen_dioxide", "ozone", "us_aqi"],
    },
}

BASE_DIR = Path(os.getenv("PROJECT_ROOT", "."))
RAW_DIR = BASE_DIR / "data" / "raw"

def fetch(url, city, variables, day):
    """Télécharge les données horaires d'une journée complète."""
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(variables),
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
        "timezone": city["timezone"],
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def extract(day=None):
    """Sauvegarde le JSON brut de chaque source et chaque ville."""
    day = day or date.today() - timedelta(days=1)  # la veille, journée complète
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for city_name, city in CITIES.items():
        for kind, source in SOURCES.items():
            data = fetch(source["url"], city, source["variables"], day)
            path = RAW_DIR / f"{kind}_{city_name.lower()}_{day.isoformat()}.json"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            paths.append(path)
            print(f"OK {path}")
    return paths


if __name__ == "__main__":
    extract()