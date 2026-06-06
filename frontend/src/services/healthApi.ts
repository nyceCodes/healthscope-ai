import axios from "axios";

const API = axios.create({
    baseURL: "http://127.0.0.1:8000"
});

export interface LifePredictionRequest {
    adult_mortality: number;
    bmi: number;
    gdp: number;
    schooling: number;
    population: number;
}

export const getCountryProfile = (
    country: string
) => {
    return API.get(
        `/health/profile/${country}`
    );
};

export const getRiskAssessment = (
    country: string
) => {
    return API.get(
        `/health/risk-assessment/${country}`
    );
};

export const getCountryTrends = (
    country: string
) => {
    return API.get(
        `/health/trends/${country}`
    );
};

export const getRankings = () => {
    return API.get(
        "/health/rankings"
    );
};

export const getCountryReport = (
    country: string
) => {

    return API.get(
        `/health/country-report/${country}`
    );

};

export const predictLifeExpectancy = (
    payload: LifePredictionRequest
) => {

    return API.post(
        "/health/predict-life-expectancy",
        payload
    );

};

export const getPredictionHistory = () => {

    return API.get(
        "/health/predictions"
    );

};