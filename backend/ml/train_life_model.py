import sys
from pathlib import Path

sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
    )
)

import pandas as pd
import kagglehub

from sklearn.model_selection import (
    train_test_split
)

from sklearn.ensemble import (
    RandomForestRegressor
)

from sklearn.metrics import (
    mean_absolute_error
)

import joblib

print(
    "Downloading WHO dataset..."
)

path = kagglehub.dataset_download(
    "kumarajarshi/life-expectancy-who"
)

csv_path = (
    path +
    "\\Life Expectancy Data.csv"
)

print(
    "Reading dataset..."
)

df = pd.read_csv(csv_path)

print(df.columns.tolist())

print(
    "Cleaning dataset..."
)

df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)
print(df.columns.tolist())

features = [
    "adult_mortality",
    "bmi",
    "gdp",
    "schooling",
    "population"
]

target = "life_expectancy"

df = df[
    features +
    [target]
].dropna()

X = df[features]

y = df[target]

print(
    f"Training rows: {len(df)}"
)

X_train, X_test, y_train, y_test = (
    train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )
)

print(
    "Training model..."
)

model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

model.fit(
    X_train,
    y_train
)

predictions = model.predict(
    X_test
)

mae = mean_absolute_error(
    y_test,
    predictions
)

print(
    f"Mean Absolute Error: {mae:.2f}"
)

joblib.dump(
    model,
    "saved_models/life_expectancy_model.pkl"
)

print(
    "Model saved successfully."
)