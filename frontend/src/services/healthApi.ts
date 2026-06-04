import axios from "axios";

const API = axios.create({
    baseURL: "http://127.0.0.1:8000"
});

export const getCountryProfile = (
    country: string
) => {
    return API.get(
    `/health/profile/${country}`
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