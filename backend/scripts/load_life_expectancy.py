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

sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
    )
)

print("Downloading dataset...")

path = kagglehub.dataset_download(
    "kumarajarshi/life-expectancy-who"
)

csv_path = (
    path +
    "\\Life Expectancy Data.csv"
)

print("Reading CSV...")

df = pd.read_csv(csv_path)

print("Cleaning data...")

df = df.rename(
    columns={
        "Country": "country",
        "Year": "year",
        "Status": "status",
        "Life expectancy ": "life_expectancy",
        "Adult Mortality": "adult_mortality",
        "BMI ": "bmi",
        "GDP": "gdp",
        "Schooling": "schooling",
        "Population": "population",
    }
)

db: Session = SessionLocal()

print("Loading records...")

count = 0

for _, row in df.iterrows():

    record = LifeExpectancy(
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

    db.add(record)

    count += 1

db.commit()

db.close()

print(
    f"Loaded {count} records successfully."
)