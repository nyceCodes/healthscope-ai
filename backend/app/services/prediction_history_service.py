from app.models.prediction_history import (
    PredictionHistory
)


class PredictionHistoryService:

    @staticmethod
    def save_prediction(
        db,
        adult_mortality,
        bmi,
        gdp,
        schooling,
        population,
        prediction
    ):

        record = PredictionHistory(

            adult_mortality=
                adult_mortality,

            bmi=
                bmi,

            gdp=
                gdp,

            schooling=
                schooling,

            population=
                population,

            prediction=
                prediction

        )

        db.add(record)

        db.commit()

        db.refresh(record)

        return record
    
    @staticmethod
    def get_predictions(db):

        return (

            db.query(
                PredictionHistory
            )

            .order_by(
                PredictionHistory.created_at.desc()
            )

            .all()

        )