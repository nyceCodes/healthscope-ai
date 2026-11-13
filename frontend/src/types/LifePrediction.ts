export interface LifePredictionRequest {
    adult_mortality: number;
    bmi: number;
    gdp: number;
    schooling: number;
    population: number;
}

export interface LifePredictionResponse {
    predicted_life_expectancy: number;
}