import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

const api = vi.hoisted(() => ({
    getCountryProfile: vi.fn(),
    getCountryTrends: vi.fn(),
    getRankings: vi.fn(),
    getRiskAssessment: vi.fn(),
    getCountryReport: vi.fn(),
    predictLifeExpectancy: vi.fn(),
    getPredictionHistory: vi.fn(),
    getHealthCountries: vi.fn(),
    getHealthIndicators: vi.fn(),
    getIndicatorYears: vi.fn(),
    getIndicatorObservations: vi.fn(),
    getCountryIndicatorObservations: vi.fn(),
    getIndicatorTrends: vi.fn(),
    getIndicatorComparison: vi.fn(),
    getIndicatorRankings: vi.fn(),
}));

vi.mock("../services/healthApi", () => api);

import Dashboard from "./Dashboard";

const population = {
    code: "SP.POP.TOTL",
    name: "Population, total",
    definition: "Total population, midyear estimate.",
    unit: "people",
    source: "World Bank World Development Indicators",
    latest_year: 2024,
};
const lifeExpectancy = {
    code: "SP.DYN.LE00.IN",
    name: "Life expectancy at birth, total (years)",
    definition: "Expected years lived by a newborn under current mortality patterns.",
    unit: "years",
    source: "World Bank World Development Indicators",
    latest_year: 2022,
};

const geography = {
    type: "FeatureCollection",
    features: [
        {
            type: "Feature",
            properties: { ADMIN: "Philippines", ISO_A3: "PHL" },
            geometry: {
                type: "Polygon",
                coordinates: [[[120, 20], [125, 20], [125, 15], [120, 20]]],
            },
        },
        {
            type: "Feature",
            properties: { ADMIN: "United States", ISO_A3: "USA" },
            geometry: {
                type: "Polygon",
                coordinates: [[[-125, 48], [-120, 48], [-120, 45], [-125, 48]]],
            },
        },
    ],
};

describe("global health indicator dashboard", () => {
    beforeEach(() => {
        Object.values(api).forEach((mock) => mock.mockReset());
        api.getCountryProfile.mockRejectedValue(new Error("Phase 1 profile unavailable in this map test"));
        api.getRankings.mockResolvedValue({ data: [] });
        api.getPredictionHistory.mockResolvedValue({ data: [] });
        api.getHealthCountries.mockResolvedValue({
            data: [
                { iso3: "PHL", iso2: "PH", name: "Philippines", region: null, income_level: null },
                { iso3: "SGP", iso2: "SG", name: "Singapore", region: "East Asia & Pacific", income_level: null },
                { iso3: "USA", iso2: "US", name: "United States", region: null, income_level: null },
            ],
        });
        api.getHealthIndicators.mockResolvedValue({ data: [population, lifeExpectancy] });
        api.getIndicatorYears.mockImplementation((code: string) => Promise.resolve({
            data: code === population.code ? [2024, 2023] : [2022, 2021],
        }));
        api.getIndicatorObservations.mockImplementation((code: string, year: number) => {
            const indicator = code === population.code ? population : lifeExpectancy;
            return Promise.resolve({
                data: {
                    indicator,
                    year,
                    observations: [{
                        country_iso3: "PHL",
                        country_name: "Philippines",
                        indicator_code: code,
                        indicator_name: indicator.name,
                        value: code === population.code ? 117_000_000 : 71.8,
                        year,
                        unit: indicator.unit,
                        source: indicator.source,
                        imported_at: "2025-01-01T00:00:00",
                    }],
                },
            });
        });
        api.getCountryIndicatorObservations.mockImplementation((iso3: string) => Promise.resolve({
            data: {
                country: {
                    iso3,
                    iso2: iso3 === "PHL" ? "PH" : iso3 === "SGP" ? "SG" : "US",
                    name: iso3 === "PHL" ? "Philippines" : iso3 === "SGP" ? "Singapore" : "United States",
                    region: iso3 === "SGP" ? "East Asia & Pacific" : null,
                    income_level: null,
                },
                observations: [
                    {
                        country_iso3: iso3,
                        country_name: iso3 === "PHL" ? "Philippines" : iso3 === "SGP" ? "Singapore" : "United States",
                        indicator_code: lifeExpectancy.code,
                        indicator_name: lifeExpectancy.name,
                        value: 71.8,
                        year: 2022,
                        unit: "years",
                        source: lifeExpectancy.source,
                        imported_at: "2025-01-01T00:00:00",
                    },
                ],
            },
        }));
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(geography),
        }));
    });

    afterEach(() => {
        cleanup();
        vi.unstubAllGlobals();
    });

    it("switches indicator and year, selects a country, and labels missing map data", async () => {
        render(<Dashboard />);

        expect(await screen.findByRole("img", {
            name: "Population, total by country for 2024",
        }, { timeout: 5000 })).toBeTruthy();
        fireEvent.click(screen.getByRole("button", { name: "Zoom in on map" }));
        expect(
            screen.getByRole("img", {
                name: "Population, total by country for 2024",
            }).querySelector("g")?.getAttribute("transform"),
        ).toContain("scale(1.5)");

        const indicatorSelect = screen.getByLabelText("Indicator");
        fireEvent.change(indicatorSelect, { target: { value: lifeExpectancy.code } });
        expect(await screen.findByRole("img", {
            name: "Life expectancy at birth, total (years) by country for 2022",
        }, { timeout: 5000 })).toBeTruthy();

        const yearSelect = screen.getByLabelText("Reporting year");
        fireEvent.change(yearSelect, { target: { value: "2021" } });
        await waitFor(() => {
            expect(api.getIndicatorObservations).toHaveBeenLastCalledWith(
                lifeExpectancy.code,
                2021,
            );
        });
        expect(await screen.findByRole("img", {
            name: "Life expectancy at birth, total (years) by country for 2021",
        }, { timeout: 5000 })).toBeTruthy();

        fireEvent.mouseEnter(screen.getByRole("button", {
            name: "United States: No data",
        }));
        expect(screen.getByText("No data · 2021")).toBeTruthy();

        fireEvent.click(screen.getByRole("button", {
            name: "Philippines: 71.8 years",
        }));
        await waitFor(() => {
            expect(api.getCountryIndicatorObservations).toHaveBeenLastCalledWith("PHL");
        });
        expect(await screen.findByRole("heading", { name: "Philippines" })).toBeTruthy();
        const lifeExpectancyCard = screen.getByRole("heading", {
            name: lifeExpectancy.name,
        }).parentElement;
        expect(lifeExpectancyCard?.textContent).toContain("71.8 years");
    });

    it("lets a user select Singapore from the linked country selector", async () => {
        render(<Dashboard />);

        const countrySelector = await screen.findByLabelText("Select any country");
        fireEvent.change(countrySelector, { target: { value: "SGP" } });

        await waitFor(() => {
            expect(api.getCountryIndicatorObservations).toHaveBeenLastCalledWith("SGP");
        });
        expect(await screen.findByRole("heading", { name: "Singapore" })).toBeTruthy();
    });

    it("explains when an indicator has no stored observations", async () => {
        api.getHealthIndicators.mockResolvedValue({
            data: [{ ...population, latest_year: null }],
        });
        api.getIndicatorYears.mockResolvedValue({ data: [] });

        render(<Dashboard />);

        expect(await screen.findByText(
            /No observations are stored for Population, total\./,
        )).toBeTruthy();
    });

    it("initially selects an indicator that has stored observations", async () => {
        api.getHealthIndicators.mockResolvedValue({
            data: [
                { ...population, latest_year: null },
                lifeExpectancy,
            ],
        });

        render(<Dashboard />);

        expect(await screen.findByRole("img", {
            name: "Life expectancy at birth, total (years) by country for 2022",
        }, { timeout: 5000 })).toBeTruthy();
    });

    it("keeps the profile visible and reports independent catalog and trend failures", async () => {
        api.getCountryProfile.mockResolvedValue({
            data: {
                country: "Philippines",
                population: 117_000_000,
                region: "",
                capital: "",
                cases: 0,
                deaths: 0,
                recovered: 0,
                active: 0,
                tests: 0,
                recovery_rate: 0,
                mortality_rate: 0,
                health_index: 50,
                data_source: "saved snapshot",
                data_status: "Historical",
            },
        });
        api.getHealthIndicators.mockRejectedValue(new Error("Indicator catalogue unavailable"));
        api.getCountryTrends.mockRejectedValue(new Error("Trend service unavailable"));
        api.getRiskAssessment.mockRejectedValue(new Error("Risk service unavailable"));
        api.getCountryReport.mockRejectedValue(new Error("Report service unavailable"));

        render(<Dashboard />);

        expect(await screen.findByRole("heading", { name: "Philippines" })).toBeTruthy();
        expect(await screen.findByText(/Indicator list unavailable/)).toBeTruthy();
        expect(await screen.findByText(/Saved snapshot trend unavailable/)).toBeTruthy();
    });
});
