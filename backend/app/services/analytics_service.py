class AnalyticsService:

    @staticmethod
    def recovery_rate(data):

        cases = data.get("cases", 0)

        if cases == 0:
            return 0

        return round(
            data.get("recovered", 0) / cases * 100,
            2
        )

    @staticmethod
    def mortality_rate(data):

        cases = data.get("cases", 0)

        if cases == 0:
            return 0

        return round(
            data.get("deaths", 0) / cases * 100,
            2
        )

    @staticmethod
    def testing_coverage(data):

        population = data.get("population", 0)

        if population == 0:
            return 0

        return round(
            data.get("tests", 0) / population * 100,
            2
        )

    @staticmethod
    def health_index(data):

        recovery = AnalyticsService.recovery_rate(data)

        mortality = AnalyticsService.mortality_rate(data)

        testing = AnalyticsService.testing_coverage(data)

        score = (
            recovery * 0.5
            +
            testing * 0.3
            -
            mortality * 0.2
        )

        return round(max(score, 0), 2)