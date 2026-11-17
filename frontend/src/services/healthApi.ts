import axios from "axios";
import type {
    HealthCountry,
    HealthCountryObservationSet,
    HealthIndicator,
    HealthObservationSet,
    CountryComparison,
    IndicatorRanking,
    TrendAnalysis,
} from "../types/HealthIndicator";
import type { LifePredictionRequest, LifePredictionResponse } from "../types/LifePrediction";
import type { PredictionHistory } from "../types/PredictionHistory";

export type { LifePredictionRequest, LifePredictionResponse } from "../types/LifePrediction";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim()
    || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

const API = axios.create({
    baseURL: API_BASE_URL,
    timeout: 12000
});

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

    return API.post<LifePredictionResponse>(
        "/health/predict-life-expectancy",
        payload
    );

};

export const getPredictionHistory = () => {

    return API.get<PredictionHistory[]>(
        "/health/predictions"
    );

};

export const getHealthCountries = () =>
    API.get<HealthCountry[]>("/health/data/countries");

export const getHealthIndicators = () =>
    API.get<HealthIndicator[]>("/health/data/indicators");

export const getIndicatorYears = (indicatorCode: string) =>
    API.get<number[]>(`/health/data/indicators/${encodeURIComponent(indicatorCode)}/years`);

export const getIndicatorObservations = (
    indicatorCode: string,
    year: number,
) =>
    API.get<HealthObservationSet>(
        `/health/data/indicators/${encodeURIComponent(indicatorCode)}/observations`,
        { params: { year } },
    );

export const getCountryIndicatorObservations = (
    iso3: string,
    year?: number,
) =>
    API.get<HealthCountryObservationSet>(
        `/health/data/countries/${encodeURIComponent(iso3)}/observations`,
        { params: year === undefined ? undefined : { year } },
    );

export const getCountryIndicatorHistory = (
    iso3: string,
    indicatorCode: string,
) =>
    API.get(
        `/health/data/countries/${encodeURIComponent(iso3)}/indicators/${encodeURIComponent(indicatorCode)}/history`,
    );

export const getIndicatorTrends = (
    indicatorCode: string,
    countries: string[],
    startYear: number,
    endYear: number,
) => {
    const params = new URLSearchParams({
        indicator_code: indicatorCode,
        start_year: String(startYear),
        end_year: String(endYear),
    });
    countries.forEach((country) => params.append("countries", country));
    return API.get<TrendAnalysis>("/health/data/analytics/trends", { params });
};

export const getIndicatorComparison = (
    indicatorCode: string,
    countries: string[],
    year: number,
) => {
    const params = new URLSearchParams({
        indicator_code: indicatorCode,
        year: String(year),
    });
    countries.forEach((country) => params.append("countries", country));
    return API.get<CountryComparison>("/health/data/analytics/compare", { params });
};

export const getIndicatorRankings = (
    indicatorCode: string,
    year: number,
    order: "ascending" | "descending",
) =>
    API.get<IndicatorRanking>("/health/data/analytics/rankings", {
        params: { indicator_code: indicatorCode, year, order },
    });