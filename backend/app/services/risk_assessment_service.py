class RiskAssessmentService:

    @staticmethod
    def assess_risk(
        report
    ):

        score = 0

        reasons = []

        recommendations = []

        life_expectancy = (
            report["life_expectancy"]["value"]
        )

        health_index = (
            report["health_profile"]["health_index"]
        )

        schooling = (
            report["life_expectancy"]["schooling"]
        )

        if life_expectancy < 75:
            score += 1

            reasons.append(
                "Life expectancy is below leading countries."
            )

            recommendations.append(
                "Improve preventive healthcare access."
            )

        if health_index is not None and health_index < 75:

            score += 1

            reasons.append(
                "Health index is below benchmark."
            )

            recommendations.append(
                "Increase public health investment."
            )

        if schooling < 13:

            score += 1

            reasons.append(
                "Schooling levels are relatively low."
            )

            recommendations.append(
                "Improve educational attainment."
            )

        if score == 0:

            risk_level = "Low"

        elif score == 1:

            risk_level = "Moderate"

        else:

            risk_level = "High"

        return {
            "risk_level": risk_level,
            "reasons": reasons,
            "recommendations": recommendations
        }