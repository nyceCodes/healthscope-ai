class IntelligenceService:

    @staticmethod
    def generate_insights(
        report
    ):

        insights = []

        gap = (
            report["global_comparison"]
            ["life_expectancy_gap"]
        )

        if gap > 15:

            insights.append(
                "Life expectancy is significantly below top-performing countries."
            )

        schooling = (
            report["life_expectancy"]
            ["schooling"]
        )

        if schooling < 13:

            insights.append(
                "Education levels may be limiting long-term health outcomes."
            )

        health_index = (
            report["health_profile"]
            ["health_index"]
        )

        if (
            health_index is not None
            and
            health_index < 75
        ):

            insights.append(
                "Health index indicates room for improvement in national health outcomes."
            )

        return insights