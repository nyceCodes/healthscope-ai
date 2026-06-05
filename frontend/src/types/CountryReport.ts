export interface CountryReport {
    country: string;

    health_profile: {
        health_index: number;
        recovery_rate: number;
        mortality_rate: number;
    };

    life_expectancy: {
        year: number;
        value: number;
        schooling: number;
        gdp: number;
    };

    global_comparison: {
        top_country: string;
        life_expectancy_gap: number;
    };

    insights: string[];
}