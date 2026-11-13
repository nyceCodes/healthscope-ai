"""Exploratory COVID-derived scores — not validated clinical risk measures."""


class AnalyticsService:
    @staticmethod
    def _number(data, field):
        value = data.get(field)
        return float(value) if isinstance(value, (int, float)) and value >= 0 else 0.0

    @staticmethod
    def recovery_rate(data):
        cases = AnalyticsService._number(data, "cases")
        if not cases:
            return 0.0
        return round(AnalyticsService._number(data, "recovered") / cases * 100, 2)

    @staticmethod
    def mortality_rate(data):
        cases = AnalyticsService._number(data, "cases")
        if not cases:
            return 0.0
        return round(AnalyticsService._number(data, "deaths") / cases * 100, 2)

    @staticmethod
    def testing_coverage(data):
        """Capped testing-volume/population proxy (NOT unique-person coverage)."""
        population = AnalyticsService._number(data, "population")
        if not population:
            return 0.0
        tests_per_population = AnalyticsService._number(data, "tests") / population * 100
        return round(min(tests_per_population, 100), 2)

    @staticmethod
    def health_index(data):
        recovery = AnalyticsService.recovery_rate(data)
        mortality = AnalyticsService.mortality_rate(data)
        testing = AnalyticsService.testing_coverage(data)
        score = recovery * 0.5 + testing * 0.3 - mortality * 0.2
        return round(min(100, max(score, 0)), 2)

    @staticmethod
    def index_from_snapshot(snapshot):
        """Recalculate legacy stored scores at read time without modifying rows."""
        return AnalyticsService.health_index({
            name: getattr(snapshot, name) for name in
            ("cases", "deaths", "recovered", "tests", "population")
        })
