"""DAG quotidien : extraction, transformation avec contrôle qualité, chargement."""
from datetime import datetime, timedelta

from airflow.sdk import dag, task


@dag(
    dag_id="climat_dakar_daily",
    schedule="0 6 * * *",              # chaque jour à 06:00 UTC
    start_date=datetime(2026, 11, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["climat", "dakar"],
)
def climat_dakar_daily():
    @task
    def extract_task():
        from datetime import date

        from src.extract import extract

        day = date.today() - timedelta(days=1)      # la veille : journée complète
        extract(day)
        return day.isoformat()

    @task
    def transform_task(day: str):
        from datetime import date

        from src.transform import PROCESSED_DIR, RAW_DIR, check_quality, transform

        d = date.fromisoformat(day)
        df = transform(RAW_DIR / f"weather_dakar_{d}.json",
                       RAW_DIR / f"air_dakar_{d}.json")
        problems = check_quality(df)
        if problems:
            raise ValueError(f"Contrôle qualité échoué : {problems}")
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(PROCESSED_DIR / f"dakar_{d}.csv", index=False)
        return day

    @task
    def load_task(day: str):
        from datetime import date

        from src.load import run

        run(date.fromisoformat(day))

    load_task(transform_task(extract_task()))


climat_dakar_daily()