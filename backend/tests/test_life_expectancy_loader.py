import pandas as pd

from scripts.load_life_expectancy import normalize_life_expectancy_columns


def test_life_expectancy_loader_normalizes_whitespace_and_feature_names():
    frame = pd.DataFrame(
        [[25.0, 1000.0]],
        columns=[" BMI ", " Adult Mortality "],
    )

    normalized = normalize_life_expectancy_columns(frame)

    assert normalized.columns.tolist() == ["bmi", "adult_mortality"]
    assert normalized.iloc[0].tolist() == [25.0, 1000.0]
