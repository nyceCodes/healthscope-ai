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