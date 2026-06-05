import joblib
import pandas as pd


class MLService:

    model = joblib.load(
        "saved_models/life_expectancy_model.pkl"
    )

    @staticmethod
    def predict_life_expectancy(
        adult_mortality,
        bmi,
        gdp,
        schooling,
        population
    ):

        data = pd.DataFrame([
            {
                "adult_mortality":
                    adult_mortality,

                "bmi":
                    bmi,

                "gdp":
                    gdp,

                "schooling":
                    schooling,

                "population":
                    population
            }
        ])

        prediction = (
            MLService.model.predict(
                data
            )[0]
        )

        return round(
            float(prediction),
            2
        )