import sys
from pathlib import Path

sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
    )
)

import pandas as pd
import kagglehub

from sqlalchemy.orm import Session

from app.database.database import SessionLocal

from app.models.life_expectancy import (
    LifeExpectancy
)


def normalize_life_expectancy_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = (
        normalized.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
    )
    return normalized


def load_life_expectancy_data() -> None:
    print("Downloading dataset...")
    path = kagglehub.dataset_download("kumarajarshi/life-expectancy-who")
    csv_path = path + "\\Life Expectancy Data.csv"

    print("Reading CSV...")
    frame = normalize_life_expectancy_columns(pd.read_csv(csv_path))

    db: Session = SessionLocal()
    try:
        print("Loading records...")
        for _, row in frame.iterrows():
            db.add(
                LifeExpectancy(
                    country=row.get("country"),
                    year=row.get("year"),
                    status=row.get("status"),
                    life_expectancy=row.get("life_expectancy"),
                    adult_mortality=row.get("adult_mortality"),
                    bmi=row.get("bmi"),
                    gdp=row.get("gdp"),
                    schooling=row.get("schooling"),
                    population=row.get("population"),
                )
            )
        db.commit()
        print(f"Loaded {len(frame)} records successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    load_life_expectancy_data()