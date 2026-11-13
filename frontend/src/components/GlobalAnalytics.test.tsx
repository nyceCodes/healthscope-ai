import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";

const api = vi.hoisted(() => ({
    getCountryIndicatorObservations: vi.fn(),
    getIndicatorTrends: vi.fn(),
    getIndicatorComparison: vi.fn(),
    getIndicatorRankings: vi.fn(),
}));

vi.mock("../services/healthApi", () => api);

import GlobalAnalytics from "./GlobalAnalytics";
import type {
    CountryComparison,
    HealthCountry,
    HealthCountryObservationSet,
    HealthIndicator,
    HealthObservation,
    IndicatorRanking,
    TrendAnalysis,
} from "../types/HealthIndicator";

const countries: HealthCountry[] = [
    { iso3: "PHL", iso2: "PH", name: "Philippines", region: "East Asia & Pacific", income_level: null },
    { iso3: "SGP", iso2: "SG", name: "Singapore", region: "East Asia & Pacific", income_level: null },
    { iso3: "USA", iso2: "US", name: "United States", region: "North America", income_level: null },
];

const indicators: HealthIndicator[] = [
    { code: "SP.DYN.LE00.IN", name: "Life expectancy", definition: "Expected years lived.", unit: "years", source: "World Bank WDI", latest_year: 2022 },
    { code: "SP.POP.TOTL", name: "Population", definition: "Midyear population.", unit: "people", source: "World Bank WDI", latest_year: 2024 },
    { code: "SH.DYN.MORT", name: "Under-five mortality", definition: "Deaths per 1,000 live births.", unit: "deaths per 1,000 live births", source: "World Bank WDI", latest_year: 2022 },
    { code: "SH.XPD.CHEX.GD.ZS", name: "Health expenditure", definition: "Health spending as a share of GDP.", unit: "% of GDP", source: "World Bank WDI", latest_year: 2022 },
];

function observation(
    countryIso3: string,
    code: string,
    year: number,
    value: number,
): HealthObservation {
    const indicator = indicators.find((item) => item.code === code)!;
    const country = countries.find((item) => item.iso3 === countryIso3)!;
    return {
        country_iso3: country.iso3,
        country_name: country.name,
        indicator_code: indicator.code,
        indicator_name: indicator.name,
        value,
        year,
        unit: indicator.unit,
        source: indicator.source,
        imported_at: "2025-01-01T00:00:00",
    };
}

function countryData(iso3: string): HealthCountryObservationSet {
    const country = countries.find((item) => item.iso3 === iso3)!;
    const values: Record<string, Array<[number, number]>> = iso3 === "SGP"
        ? {
            "SP.DYN.LE00.IN": [[2020, 80], [2022, 82]],
            "SP.POP.TOTL": [[2024, 6_000_000]],
            "SH.DYN.MORT": [[2022, 2.4]],
            "SH.XPD.CHEX.GD.ZS": [[2022, 5.5]],
        }
        : {
            "SP.DYN.LE00.IN": [[2021, 70], [2022, 72]],
            "SP.POP.TOTL": [[2024, 100_000_000]],
            "SH.DYN.MORT": [[2022, 20]],
            "SH.XPD.CHEX.GD.ZS": [[2022, 4.5]],
        };
    return {
        country,
        observations: Object.entries(values).flatMap(([code, rows]) =>
            rows.map(([year, value]) => observation(iso3, code, year, value)),
        ),
    };
}

function trendData(
    codes: string[],
    start: number,
    end: number,
    code = indicators[0].code,
): TrendAnalysis {
    const indicator = indicators.find((item) => item.code === code) ?? indicators[0];
    return {
        indicator,
        start_year: start,
        end_year: end,
        series: codes.map((iso3) => {
            const rows = indicator.code === "SH.XPD.CHEX.GD.ZS"
                ? (iso3 === "SGP" ? [[2021, 5.4], [2022, 5.5]] : [[2021, 4.4], [2022, 4.5]])
                : (iso3 === "SGP" ? [[2021, 81], [2022, 82]] : [[2021, 70], [2022, 72]]);
            const observations = rows
                .filter(([year]) => year >= start && year <= end)
                .map(([year, value]) => observation(iso3, indicator.code, year, value));
            const first = observations[0];
            const last = observations[observations.length - 1];
            const change = first && last && first.year !== last.year
                ? last.value - first.value
                : null;
            return {
                country: countries.find((item) => item.iso3 === iso3)!,
                observations,
                change_from_year: change === null ? null : first.year,
                change_to_year: change === null ? null : last.year,
                absolute_change: change,
                percent_change: change === null ? null : change / first.value * 100,
            };
        }),
    };
}

function comparisonData(codes: string[], code = indicators[0].code): CountryComparison {
    const indicator = indicators.find((item) => item.code === code) ?? indicators[0];
    const referenceValue = code === "SH.XPD.CHEX.GD.ZS" ? 4.5 : 72;
    const reference = observation("PHL", indicator.code, 2022, referenceValue);
    return {
        indicator,
        year: 2022,
        reference_iso3: codes[0],
        countries: codes.map((iso3) => {
            const value = iso3 === "SGP"
                ? (code === "SH.XPD.CHEX.GD.ZS" ? 5.5 : 82)
                : iso3 === "PHL" ? referenceValue : null;
            const row = value === null ? null : observation(iso3, indicator.code, 2022, value);
            return {
                country: countries.find((item) => item.iso3 === iso3)!,
                observation: row,
                difference_from_reference: row ? row.value - reference.value : null,
                percent_difference_from_reference: row
                    ? (row.value - reference.value) / reference.value * 100
                    : null,
            };
        }),
    };
}

function rankingData(): IndicatorRanking {
    const indicator = indicators[0];
    return {
        indicator,
        year: 2022,
        order: "descending",
        rows: [
            { rank: 1, observation: observation("SGP", indicator.code, 2022, 82) },
            { rank: 2, observation: observation("PHL", indicator.code, 2022, 72) },
        ],
    };
}

function renderAnalytics(onSelectCountry = vi.fn()) {
    function Harness() {
        const [selectedIso3, setSelectedIso3] = useState<string | null>(null);
        const [selectedIndicator, setSelectedIndicator] = useState(indicators[0].code);
        return (
            <GlobalAnalytics
                countries={countries}
                indicators={indicators}
                indicatorCode={selectedIndicator}
                year={2022}
                years={[2022, 2021, 2020]}
                selectedIso3={selectedIso3}
                onSelectIndicator={setSelectedIndicator}
                onSelectYear={vi.fn()}
                onSelectCountry={(iso3) => {
                    setSelectedIso3(iso3);
                    onSelectCountry(iso3);
                }}
            />
        );
    }

    return render(<Harness />);
}

describe("global analytics", () => {
    beforeEach(() => {
        Object.values(api).forEach((mock) => mock.mockReset());
        api.getCountryIndicatorObservations.mockImplementation((iso3: string) =>
            Promise.resolve({ data: countryData(iso3) }),
        );
        api.getIndicatorTrends.mockImplementation(
            (code: string, codes: string[], start: number, end: number) =>
                Promise.resolve({ data: trendData(codes, start, end, code) }),
        );
        api.getIndicatorComparison.mockImplementation(
            (code: string, codes: string[]) =>
                Promise.resolve({ data: comparisonData(codes, code) }),
        );
        api.getIndicatorRankings.mockResolvedValue({ data: rankingData() });
    });

    afterEach(() => cleanup());

    it("searches by ISO-3 and shows actual metric years, units, region, and source", async () => {
        const onSelectCountry = vi.fn();
        renderAnalytics(onSelectCountry);
        const input = screen.getByLabelText("Search for a country");
        fireEvent.change(input, { target: { value: "SGP" } });
        fireEvent.click(screen.getByRole("button", { name: "View country" }));

        expect(onSelectCountry).toHaveBeenCalledWith("SGP");
        await waitFor(() => {
            expect(api.getCountryIndicatorObservations).toHaveBeenLastCalledWith("SGP");
        });
        expect(await screen.findByRole("heading", { name: "Singapore" })).toBeTruthy();
        expect(screen.getByText("SGP · East Asia & Pacific")).toBeTruthy();
        expect(screen.getByText("82 years")).toBeTruthy();
        expect(screen.getAllByText("Reporting year 2022 · World Bank WDI").length).toBe(3);
        expect(screen.getByText("6,000,000 people")).toBeTruthy();
    });

    it("updates historical requests for year filters and displays only observed years", async () => {
        renderAnalytics();
        fireEvent.click(screen.getByRole("tab", { name: "Trends" }));

        await waitFor(() => {
            expect(api.getIndicatorTrends).toHaveBeenLastCalledWith(
                indicators[0].code,
                ["PHL"],
                2020,
                2022,
            );
        });
        fireEvent.change(screen.getByLabelText("Start year"), { target: { value: "2021" } });
        await waitFor(() => {
            expect(api.getIndicatorTrends).toHaveBeenLastCalledWith(
                indicators[0].code,
                ["PHL"],
                2021,
                2022,
            );
        });
        const observationsTable = screen.getByRole("table", {
            name: "Year-by-year observations (no values are interpolated)",
        });
        expect(within(observationsTable).getByText("2021")).toBeTruthy();
        expect(within(observationsTable).getByText("2022")).toBeTruthy();
        expect(within(observationsTable).queryByText("2020")).toBeNull();
    });

    it("shows missing comparison data without replacing it and keeps rankings searchable", async () => {
        renderAnalytics();
        fireEvent.click(screen.getByRole("tab", { name: "Compare" }));
        const addCountry = screen.getByLabelText("Add country (two to five)");
        fireEvent.change(addCountry, { target: { value: "USA" } });
        fireEvent.click(screen.getByRole("button", { name: "Add country" }));

        await waitFor(() => {
            expect(api.getIndicatorComparison).toHaveBeenLastCalledWith(
                indicators[0].code,
                ["PHL", "SGP", "USA"],
                2022,
            );
        });
        expect(screen.getAllByText("No data").length).toBeGreaterThan(0);

        fireEvent.click(screen.getByRole("tab", { name: "Rankings" }));
        await screen.findByRole("table", { name: /Life expectancy/ });
        fireEvent.change(screen.getByLabelText("Search countries"), {
            target: { value: "SGP" },
        });
        const table = screen.getByRole("table", { name: /Life expectancy/ });
        expect(within(table).getByText("Singapore")).toBeTruthy();
        expect(within(table).queryByText("Philippines")).toBeNull();
    });

    it("labels absolute healthcare-expenditure differences as percentage points", async () => {
        renderAnalytics();
        fireEvent.click(screen.getByRole("tab", { name: "Compare" }));
        fireEvent.change(screen.getByLabelText("Health indicator"), {
            target: { value: "SH.XPD.CHEX.GD.ZS" },
        });

        await waitFor(() => {
            expect(api.getIndicatorComparison).toHaveBeenLastCalledWith(
                "SH.XPD.CHEX.GD.ZS",
                ["PHL", "SGP"],
                2022,
            );
        });
        expect(await screen.findByText("1 percentage point")).toBeTruthy();
        expect(screen.getByText("22.22%")).toBeTruthy();
    });
});
