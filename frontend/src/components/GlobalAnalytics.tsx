import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
    Bar,
    BarChart,
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";

import {
    getCountryIndicatorObservations,
    getIndicatorComparison,
    getIndicatorRankings,
    getIndicatorTrends,
} from "../services/healthApi";
import type {
    CountryComparison,
    HealthCountry,
    HealthCountryObservationSet,
    HealthIndicator,
    HealthObservation,
    IndicatorRanking,
    TrendAnalysis,
} from "../types/HealthIndicator";

type AnalyticsPage = "explorer" | "trends" | "compare" | "rankings";

const PLOT_COLORS = ["#60a5fa", "#34d399", "#fbbf24", "#f472b6", "#a78bfa"];
const MAX_COUNTRIES = 5;

function displayNumber(value: number, maximumFractionDigits = 2): string {
    return new Intl.NumberFormat(undefined, { maximumFractionDigits }).format(value);
}

function formatValue(value: number, unit: string): string {
    return `${displayNumber(value)} ${unit}`;
}

function safeExternalUrl(value: string | null | undefined): string | null {
    if (!value) return null;
    try {
        const url = new URL(value);
        return url.protocol === "https:" ? url.href : null;
    } catch {
        return null;
    }
}

function formatAbsoluteChange(value: number, indicator: HealthIndicator): string {
    const unit = indicator.code === "SH.XPD.CHEX.GD.ZS"
        ? Math.abs(value) === 1 ? "percentage point" : "percentage points"
        : indicator.unit;
    return `${displayNumber(value)} ${unit}`;
}

function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : "The analytics request failed.";
}

function latestForIndicator(
    observations: HealthObservation[],
    indicatorCode: string,
): HealthObservation | undefined {
    return observations
        .filter((row) => row.indicator_code === indicatorCode)
        .reduce<HealthObservation | undefined>(
            (latest, row) => !latest || row.year > latest.year ? row : latest,
            undefined,
        );
}

function countryLabel(country: HealthCountry): string {
    return `${country.name} (${country.iso3})`;
}

function resolveCountry(value: string, countries: HealthCountry[]): HealthCountry | undefined {
    const query = value.trim().toLocaleLowerCase();
    return countries.find(
        (country) =>
            country.iso3.toLocaleLowerCase() === query
            || country.name.toLocaleLowerCase() === query,
    );
}

function toCsv(rows: HealthObservation[]): string {
    const quote = (value: string | number) => `"${String(value).replaceAll('"', '""')}"`;
    return [
        [
            "country",
            "iso3",
            "indicator",
            "reporting_year",
            "value",
            "unit",
            "source",
            "source_reference",
            "source_publication_date",
            "source_record_timestamp",
            "source_value_text",
            "denominator_value",
            "denominator_definition",
            "uncertainty_lower",
            "uncertainty_upper",
            "estimate_status",
            "dimensions",
        ].map(quote).join(","),
        ...rows.map((row) => [
            row.country_name,
            row.country_iso3,
            row.indicator_name,
            row.year,
            row.value,
            row.unit,
            row.source,
            row.source_reference ?? "",
            row.source_publication_date ?? "",
            row.source_record_timestamp ?? "",
            row.source_value_text ?? "",
            row.denominator_value ?? "",
            row.denominator_definition ?? "",
            row.uncertainty_lower ?? "",
            row.uncertainty_upper ?? "",
            row.estimate_status ?? "",
            JSON.stringify(row.dimensions ?? {}),
        ].map(quote).join(",")),
    ].join("\r\n");
}

function downloadCsv(rows: HealthObservation[], filename: string): void {
    const url = URL.createObjectURL(new Blob([toCsv(rows)], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

function chartRows(analysis: TrendAnalysis | null): Record<string, number | null>[] {
    if (!analysis) return [];
    const years = Array.from(
        { length: analysis.end_year - analysis.start_year + 1 },
        (_, index) => analysis.start_year + index,
    );
    return years.map((year) => {
        const row: Record<string, number | null> = { year };
        analysis.series.forEach((series) => {
            row[series.country.iso3] = series.observations.find(
                (observation) => observation.year === year,
            )?.value ?? null;
        });
        return row;
    });
}

interface GlobalAnalyticsProps {
    countries: HealthCountry[];
    indicators: HealthIndicator[];
    indicatorCode: string;
    year: number | null;
    years: number[];
    selectedIso3: string | null;
    onSelectIndicator: (code: string) => void;
    onSelectYear: (year: number) => void;
    onSelectCountry: (iso3: string) => void;
}

export default function GlobalAnalytics({
    countries,
    indicators,
    indicatorCode,
    year,
    years,
    selectedIso3,
    onSelectIndicator,
    onSelectYear,
    onSelectCountry,
}: GlobalAnalyticsProps) {
    const [page, setPage] = useState<AnalyticsPage>("explorer");
    const [yearRange, setYearRange] = useState<{
        indicatorCode: string;
        start: number | null;
        end: number | null;
    }>({ indicatorCode: "", start: null, end: null });
    const [countrySearch, setCountrySearch] = useState<string | null>(null);
    const [countryData, setCountryData] = useState<HealthCountryObservationSet | null>(null);
    const [countryLoading, setCountryLoading] = useState(false);
    const [countryError, setCountryError] = useState("");
    const [trendCountries, setTrendCountries] = useState<string[]>(["PHL"]);
    const [comparisonCountries, setComparisonCountries] = useState<string[]>(["PHL", "SGP"]);
    const [countryToAdd, setCountryToAdd] = useState("");
    const [selectionError, setSelectionError] = useState("");
    const [trends, setTrends] = useState<TrendAnalysis | null>(null);
    const [trendsLoading, setTrendsLoading] = useState(false);
    const [trendsError, setTrendsError] = useState("");
    const [comparison, setComparison] = useState<CountryComparison | null>(null);
    const [comparisonTrends, setComparisonTrends] = useState<TrendAnalysis | null>(null);
    const [comparisonLoading, setComparisonLoading] = useState(false);
    const [comparisonError, setComparisonError] = useState("");
    const [ranking, setRanking] = useState<IndicatorRanking | null>(null);
    const [rankingLoading, setRankingLoading] = useState(false);
    const [rankingError, setRankingError] = useState("");
    const [rankingOrder, setRankingOrder] = useState<"ascending" | "descending">("descending");
    const [rankingSearch, setRankingSearch] = useState("");

    const countryIso3 = selectedIso3 ?? "PHL";
    const orderedYears = useMemo(() => [...years].sort((a, b) => a - b), [years]);
    const startYear = yearRange.indicatorCode === indicatorCode && yearRange.start !== null
        ? yearRange.start
        : orderedYears[0] ?? null;
    const endYear = yearRange.indicatorCode === indicatorCode && yearRange.end !== null
        ? yearRange.end
        : orderedYears[orderedYears.length - 1] ?? null;

    useEffect(() => {
        if (page !== "explorer" || !countryIso3) return;
        let cancelled = false;
        const loadCountry = async () => {
            await Promise.resolve();
            if (cancelled) return;
            setCountryLoading(true);
            setCountryData(null);
            setCountryError("");
            try {
                const response = await getCountryIndicatorObservations(countryIso3);
                if (!cancelled) setCountryData(response.data);
            } catch (error: unknown) {
                if (!cancelled) setCountryError(errorMessage(error));
            } finally {
                if (!cancelled) setCountryLoading(false);
            }
        };
        void loadCountry();
        return () => {
            cancelled = true;
        };
    }, [countryIso3, page]);

    useEffect(() => {
        if (page !== "trends") return;
        let cancelled = false;
        const loadTrends = async () => {
            await Promise.resolve();
            if (cancelled) return;
            setTrends(null);
            if (
                !indicatorCode
                || startYear === null
                || endYear === null
                || startYear > endYear
                || trendCountries.length === 0
            ) {
                setTrendsLoading(false);
                return;
            }
            setTrendsLoading(true);
            setTrendsError("");
            try {
                const response = await getIndicatorTrends(
                    indicatorCode,
                    trendCountries,
                    startYear,
                    endYear,
                );
                if (!cancelled) setTrends(response.data);
            } catch (error: unknown) {
                if (!cancelled) setTrendsError(errorMessage(error));
            } finally {
                if (!cancelled) setTrendsLoading(false);
            }
        };
        void loadTrends();
        return () => {
            cancelled = true;
        };
    }, [endYear, indicatorCode, page, startYear, trendCountries]);

    useEffect(() => {
        if (page !== "compare") return;
        let cancelled = false;
        const loadComparison = async () => {
            await Promise.resolve();
            if (cancelled) return;
            setComparison(null);
            setComparisonTrends(null);
            if (!indicatorCode || year === null || comparisonCountries.length < 2) {
                setComparisonLoading(false);
                return;
            }
            setComparisonLoading(true);
            setComparisonError("");
            const minYear = years.length ? Math.min(...years) : year;
            const maxYear = years.length ? Math.max(...years) : year;
            try {
                const [comparisonResponse, trendsResponse] = await Promise.all([
                    getIndicatorComparison(indicatorCode, comparisonCountries, year),
                    getIndicatorTrends(indicatorCode, comparisonCountries, minYear, maxYear),
                ]);
                if (cancelled) return;
                setComparison(comparisonResponse.data);
                setComparisonTrends(trendsResponse.data);
            } catch (error: unknown) {
                if (!cancelled) setComparisonError(errorMessage(error));
            } finally {
                if (!cancelled) setComparisonLoading(false);
            }
        };
        void loadComparison();
        return () => {
            cancelled = true;
        };
    }, [comparisonCountries, indicatorCode, page, year, years]);

    useEffect(() => {
        if (page !== "rankings") return;
        let cancelled = false;
        const loadRanking = async () => {
            await Promise.resolve();
            if (cancelled) return;
            setRanking(null);
            if (!indicatorCode || year === null) {
                setRankingLoading(false);
                return;
            }
            setRankingLoading(true);
            setRankingError("");
            try {
                const response = await getIndicatorRankings(indicatorCode, year, rankingOrder);
                if (!cancelled) setRanking(response.data);
            } catch (error: unknown) {
                if (!cancelled) setRankingError(errorMessage(error));
            } finally {
                if (!cancelled) setRankingLoading(false);
            }
        };
        void loadRanking();
        return () => {
            cancelled = true;
        };
    }, [indicatorCode, page, rankingOrder, year]);

    const indicator = indicators.find((item) => item.code === indicatorCode);
    const profileObservations = useMemo(
        () => countryData?.observations ?? [],
        [countryData],
    );
    const countryProfile = countryData?.country
        ?? countries.find((item) => item.iso3 === countryIso3);
    const profileTrendRows = useMemo(() => {
        const rows = profileObservations
            .filter((row) => row.indicator_code === indicatorCode)
            .sort((a, b) => a.year - b.year);
        const first = rows[0];
        const last = rows[rows.length - 1];
        if (!first || !last) return [];
        const byYear = new Map(rows.map((row) => [row.year, row.value]));
        return Array.from(
            { length: last.year - first.year + 1 },
            (_, index) => {
                const trendYear = first.year + index;
                return { year: trendYear, value: byYear.get(trendYear) ?? null };
            },
        );
    }, [indicatorCode, profileObservations]);
    const trendRows = useMemo(() => chartRows(trends), [trends]);
    const comparisonTrendRows = useMemo(
        () => chartRows(comparisonTrends),
        [comparisonTrends],
    );
    const filteredRankingRows = (ranking?.rows ?? []).filter(({ observation }) =>
        observation.country_name.toLocaleLowerCase().includes(rankingSearch.toLocaleLowerCase())
        || observation.country_iso3.toLocaleLowerCase().includes(rankingSearch.toLocaleLowerCase()),
    );

    const chooseCountry = (country: HealthCountry) => {
        setCountrySearch(null);
        setCountryError("");
        onSelectCountry(country.iso3);
    };

    const submitCountrySearch = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const found = resolveCountry(countrySearch ?? countryProfile?.name ?? countryIso3, countries);
        if (!found) {
            setCountryError("Select a country from the available list.");
            return;
        }
        chooseCountry(found);
    };

    const addCountryToSelection = (
        event: FormEvent<HTMLFormElement>,
        selected: string[],
        setSelected: (codes: string[]) => void,
    ) => {
        event.preventDefault();
        const country = resolveCountry(countryToAdd, countries);
        if (!country) {
            setSelectionError("Choose a country by name or ISO-3 code.");
            return;
        }
        if (selected.includes(country.iso3)) {
            setSelectionError(`${country.name} is already selected.`);
            return;
        }
        if (selected.length >= MAX_COUNTRIES) {
            setSelectionError("Select no more than five countries.");
            return;
        }
        setSelected([...selected, country.iso3]);
        setCountryToAdd("");
        setSelectionError("");
    };

    const removeCountry = (
        iso3: string,
        selected: string[],
        setSelected: (codes: string[]) => void,
    ) => {
        setSelected(selected.filter((code) => code !== iso3));
    };

    const renderCountryChips = (
        selected: string[],
        setSelected: (codes: string[]) => void,
    ) => (
        <ul className="selected-country-list" aria-label="Selected countries">
            {selected.map((iso3) => {
                const country = countries.find((item) => item.iso3 === iso3);
                return (
                    <li key={iso3}>
                        {country?.name ?? iso3}
                        <button
                            type="button"
                            aria-label={`Remove ${country?.name ?? iso3}`}
                            onClick={() => removeCountry(iso3, selected, setSelected)}
                        >
                            Remove
                        </button>
                    </li>
                );
            })}
        </ul>
    );

    return (
        <section className="global-analytics" aria-labelledby="analytics-heading">
            <header className="analytics-header">
                <h2 id="analytics-heading">Country analytics</h2>
                <p>Stored WDI and WHO GHO observations with reporting years and source attribution.</p>
            </header>

            <datalist id="health-countries">
                {countries.map((country) => (
                    <option key={country.iso3} value={country.name}>
                        {country.iso3}
                    </option>
                ))}
            </datalist>
            <div className="analytics-shared-controls">
                <label>
                    Health indicator
                    <select
                        value={indicatorCode}
                        onChange={(event) => onSelectIndicator(event.target.value)}
                        disabled={!indicators.length}
                    >
                        {indicators.map((item) => (
                            <option key={item.code} value={item.code}>{item.name}</option>
                        ))}
                    </select>
                </label>
                <label>
                    Analytics reporting year
                    <select
                        value={year ?? ""}
                        onChange={(event) => onSelectYear(Number(event.target.value))}
                        disabled={!years.length}
                    >
                        {years.map((availableYear) => (
                            <option key={availableYear} value={availableYear}>{availableYear}</option>
                        ))}
                    </select>
                </label>
            </div>

            <nav className="analytics-nav" aria-label="Global analytics pages" role="tablist">
                {([
                    ["explorer", "Country Explorer"],
                    ["trends", "Trends"],
                    ["compare", "Compare"],
                    ["rankings", "Rankings"],
                ] as const).map(([key, label]) => (
                    <button
                        key={key}
                        id={`analytics-tab-${key}`}
                        type="button"
                        role="tab"
                        aria-controls={`analytics-panel-${key}`}
                        aria-selected={page === key}
                        onClick={() => setPage(key)}
                        onKeyDown={(event) => {
                            const tabs: AnalyticsPage[] = [
                                "explorer",
                                "trends",
                                "compare",
                                "rankings",
                            ];
                            const currentIndex = tabs.indexOf(key);
                            const nextIndex = event.key === "ArrowRight"
                                ? (currentIndex + 1) % tabs.length
                                : event.key === "ArrowLeft"
                                    ? (currentIndex + tabs.length - 1) % tabs.length
                                    : event.key === "Home"
                                        ? 0
                                        : event.key === "End"
                                            ? tabs.length - 1
                                            : currentIndex;
                            if (nextIndex === currentIndex) return;
                            event.preventDefault();
                            const next = tabs[nextIndex];
                            setPage(next);
                            document.getElementById(`analytics-tab-${next}`)?.focus();
                        }}
                    >
                        {label}
                    </button>
                ))}
            </nav>

            {page === "explorer" && (
                <section
                    id="analytics-panel-explorer"
                    role="tabpanel"
                    aria-labelledby="analytics-tab-explorer"
                    className="analytics-panel"
                >
                    <form className="country-picker" onSubmit={submitCountrySearch}>
                        <label htmlFor="explorer-country">Search for a country</label>
                        <div>
                            <input
                                id="explorer-country"
                                list="health-countries"
                                value={countrySearch ?? countryProfile?.name ?? ""}
                                onChange={(event) => setCountrySearch(event.target.value)}
                                placeholder="Country name or ISO-3 code"
                            />
                            <button type="submit">View country</button>
                        </div>
                    </form>

                    {countryError && <p className="api-error" role="alert">{countryError}</p>}
                    {countryLoading && <p role="status">Loading country observations…</p>}
                    {!countryLoading && countryData && countryProfile && (
                        <>
                            <div className="country-profile-heading">
                                <div>
                                    <h3>{countryProfile.name}</h3>
                                    <p>{countryProfile.iso3}{countryProfile.region ? ` · ${countryProfile.region}` : ""}</p>
                                </div>
                            </div>
                            <div className="metric-grid">
                                {indicators.map((item) => {
                                    const observation = latestForIndicator(
                                        profileObservations,
                                        item.code,
                                    );
                                    return (
                                        <article className="analytics-metric" key={item.code}>
                                            <h4>{item.name}</h4>
                                            <strong>
                                                {observation
                                                    ? formatValue(observation.value, observation.unit)
                                                    : "No data"}
                                            </strong>
                                            <small>
                                                {observation
                                                    ? `Reporting year ${observation.year} · ${observation.source}`
                                                    : "No stored observation"}
                                            </small>
                                            {observation?.source_reference && (
                                                <small>
                                                    {safeExternalUrl(observation.source_reference) ? (
                                                        <a
                                                            href={safeExternalUrl(observation.source_reference) ?? undefined}
                                                            target="_blank"
                                                            rel="noreferrer"
                                                        >
                                                            Observation source
                                                        </a>
                                                    ) : (
                                                        `Source note: ${observation.source_reference}`
                                                    )}
                                                </small>
                                            )}
                                        </article>
                                    );
                                })}
                            </div>
                            {indicator && (
                                <section className="analytics-chart-card" aria-label="Country historical trend">
                                    <h3>{indicator.name} historical trend</h3>
                                    <p className="source-note">
                                        Source: {indicator.source}. Each point uses its actual reporting year; missing years are not interpolated.
                                        {indicator.definition_url && (
                                            <>
                                                {" "}
                                                <a
                                                    href={indicator.definition_url}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                >
                                                    Official indicator metadata
                                                </a>
                                            </>
                                        )}
                                    </p>
                                    <div className="chart-frame">
                                        <ResponsiveContainer width="100%" height={300}>
                                            <LineChart data={profileTrendRows}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="year" />
                                                <YAxis width={72} />
                                                <Tooltip formatter={(value) => [formatValue(Number(value), indicator.unit), indicator.name]} />
                                                <Line
                                                    type="linear"
                                                    dataKey="value"
                                                    name={indicator.name}
                                                    stroke={PLOT_COLORS[0]}
                                                    dot={false}
                                                    connectNulls={false}
                                                />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>
                                    {(() => {
                                        const rows = profileObservations
                                            .filter((row) => row.indicator_code === indicator.code)
                                            .sort((a, b) => a.year - b.year);
                                        const first = rows[0];
                                        const last = rows[rows.length - 1];
                                        if (!first || !last) {
                                            return <p className="empty-data-note">No historical observations are available.</p>;
                                        }
                                        if (first.year === last.year) {
                                            return <p className="change-summary">Only one observed year ({first.year}); change is unavailable.</p>;
                                        }
                                        const absoluteChange = last.value - first.value;
                                        const percentChange = first.value !== 0
                                            ? absoluteChange / first.value * 100
                                            : null;
                                        return (
                                            <p className="change-summary">
                                                Change from {first.year} to {last.year}:{" "}
                                                {formatAbsoluteChange(absoluteChange, indicator)}
                                                {percentChange === null
                                                    ? " · relative percent change unavailable (baseline is zero)"
                                                    : ` · ${displayNumber(percentChange)}% relative change`}
                                            </p>
                                        );
                                    })()}
                                </section>
                            )}
                        </>
                    )}
                    {!countryLoading && !countryError && !countryData && (
                        <p className="empty-data-note">Country observations are not available.</p>
                    )}
                </section>
            )}

            {page === "trends" && (
                <section
                    id="analytics-panel-trends"
                    role="tabpanel"
                    aria-labelledby="analytics-tab-trends"
                    className="analytics-panel"
                >
                    <p className="source-note">
                        {indicator?.name} · {indicator?.unit} · Source: {indicator?.source ?? "—"}.
                        Missing observations are shown as gaps and are never interpolated.
                    </p>
                    <form
                        className="country-picker"
                        onSubmit={(event) => addCountryToSelection(event, trendCountries, setTrendCountries)}
                    >
                        <label htmlFor="trend-country">Add country (up to five)</label>
                        <div>
                            <input
                                id="trend-country"
                                list="health-countries"
                                value={countryToAdd}
                                onChange={(event) => setCountryToAdd(event.target.value)}
                                placeholder="Country name or ISO-3 code"
                            />
                            <button type="submit">Add country</button>
                        </div>
                    </form>
                    {renderCountryChips(trendCountries, setTrendCountries)}
                    {selectionError && <p className="api-error" role="alert">{selectionError}</p>}
                    <div className="analytics-shared-controls">
                        <label>
                            Start year
                            <select
                                value={startYear ?? ""}
                                onChange={(event) => setYearRange({
                                    indicatorCode,
                                    start: Number(event.target.value),
                                    end: endYear,
                                })}
                            >
                                {orderedYears.map((availableYear) => (
                                    <option key={availableYear} value={availableYear}>{availableYear}</option>
                                ))}
                            </select>
                        </label>
                        <label>
                            End year
                            <select
                                value={endYear ?? ""}
                                onChange={(event) => setYearRange({
                                    indicatorCode,
                                    start: startYear,
                                    end: Number(event.target.value),
                                })}
                            >
                                {orderedYears.map((availableYear) => (
                                    <option key={availableYear} value={availableYear}>{availableYear}</option>
                                ))}
                            </select>
                        </label>
                    </div>
                    {startYear !== null && endYear !== null && startYear > endYear && (
                        <p className="api-error" role="alert">Start year must not be after end year.</p>
                    )}
                    {trendsLoading && <p role="status">Loading trend observations…</p>}
                    {trendsError && <p className="api-error" role="alert">{trendsError}</p>}
                    {!trendsLoading && trends && (
                        <>
                            <div className="chart-frame">
                                <ResponsiveContainer width="100%" height={340}>
                                    <LineChart data={trendRows}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis dataKey="year" />
                                        <YAxis width={72} />
                                        <Tooltip formatter={(value) => [formatValue(Number(value), trends.indicator.unit)]} />
                                        {trends.series.map((series, index) => (
                                            <Line
                                                key={series.country.iso3}
                                                type="linear"
                                                dataKey={series.country.iso3}
                                                name={series.country.name}
                                                stroke={PLOT_COLORS[index % PLOT_COLORS.length]}
                                                dot={false}
                                                connectNulls={false}
                                            />
                                        ))}
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="table-scroll">
                                <table>
                                    <caption>Observed change across available endpoints in the selected year range</caption>
                                    <thead>
                                        <tr>
                                            <th scope="col">Country</th>
                                            <th scope="col">Reporting years</th>
                                            <th scope="col">Absolute change</th>
                                            <th scope="col">Relative change</th>
                                            <th scope="col">Year coverage</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {trends.series.map((series) => (
                                            <tr key={series.country.iso3}>
                                                <th scope="row">{countryLabel(series.country)}</th>
                                                <td>
                                                    {series.change_from_year === null
                                                        ? "No data"
                                                        : `${series.change_from_year}–${series.change_to_year}`}
                                                </td>
                                                <td>
                                                    {series.absolute_change === null
                                                        ? "No data"
                                                        : formatAbsoluteChange(series.absolute_change, trends.indicator)}
                                                </td>
                                                <td>
                                                    {series.percent_change === null
                                                        ? "No data"
                                                        : `${displayNumber(series.percent_change)}%`}
                                                </td>
                                                <td>
                                                    {series.observations.length} / {trends.end_year - trends.start_year + 1} years
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            <div className="table-scroll">
                                <table>
                                    <caption>Year-by-year observations (no values are interpolated)</caption>
                                    <thead>
                                        <tr>
                                            <th scope="col">Country</th>
                                            <th scope="col">ISO-3</th>
                                            <th scope="col">Reporting year</th>
                                            <th scope="col">Value</th>
                                            <th scope="col">Unit</th>
                                            <th scope="col">Source</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {trends.series.flatMap((series) =>
                                            series.observations.map((observation) => (
                                                <tr key={`${observation.country_iso3}-${observation.year}`}>
                                                    <th scope="row">{observation.country_name}</th>
                                                    <td>{observation.country_iso3}</td>
                                                    <td>{observation.year}</td>
                                                    <td>{displayNumber(observation.value)}</td>
                                                    <td>{observation.unit}</td>
                                                    <td>{observation.source}</td>
                                                </tr>
                                            )),
                                        )}
                                    </tbody>
                                </table>
                            </div>
                            <button
                                type="button"
                                disabled={!trends.series.some((series) => series.observations.length)}
                                onClick={() => downloadCsv(
                                    trends.series.flatMap((series) => series.observations),
                                    `${indicatorCode}-${startYear}-${endYear}-trends.csv`,
                                )}
                            >
                                Export displayed observations as CSV
                            </button>
                        </>
                    )}
                </section>
            )}

            {page === "compare" && (
                <section
                    id="analytics-panel-compare"
                    role="tabpanel"
                    aria-labelledby="analytics-tab-compare"
                    className="analytics-panel"
                >
                    <p className="source-note">
                        Comparing {indicator?.name} in the same reporting year and unit. Differences are relative to the first selected country; they do not imply performance or causation.
                    </p>
                    <form
                        className="country-picker"
                        onSubmit={(event) => addCountryToSelection(event, comparisonCountries, setComparisonCountries)}
                    >
                        <label htmlFor="compare-country">Add country (two to five)</label>
                        <div>
                            <input
                                id="compare-country"
                                list="health-countries"
                                value={countryToAdd}
                                onChange={(event) => setCountryToAdd(event.target.value)}
                                placeholder="Country name or ISO-3 code"
                            />
                            <button type="submit">Add country</button>
                        </div>
                    </form>
                    {renderCountryChips(comparisonCountries, setComparisonCountries)}
                    {comparisonCountries.length < 2 && (
                        <p className="api-error" role="alert">Select at least two countries to compare.</p>
                    )}
                    {selectionError && <p className="api-error" role="alert">{selectionError}</p>}
                    {comparisonLoading && <p role="status">Loading comparison…</p>}
                    {comparisonError && <p className="api-error" role="alert">{comparisonError}</p>}
                    {!comparisonLoading && comparison && indicator && (
                        <>
                            <div className="table-scroll">
                                <table>
                                    <caption>{comparison.indicator.name} · reporting year {comparison.year} · {comparison.indicator.source}</caption>
                                    <thead>
                                        <tr>
                                            <th scope="col">Country</th>
                                            <th scope="col">Value</th>
                                            <th scope="col">Difference vs. {comparison.reference_iso3}</th>
                                            <th scope="col">Relative difference</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {comparison.countries.map((item) => (
                                            <tr key={item.country.iso3}>
                                                <th scope="row">{countryLabel(item.country)}</th>
                                                <td>
                                                    {item.observation
                                                        ? `${formatValue(item.observation.value, item.observation.unit)} · ${item.observation.year}`
                                                        : "No data"}
                                                </td>
                                                <td>
                                                    {item.difference_from_reference === null
                                                        ? "No data"
                                                        : formatAbsoluteChange(item.difference_from_reference, comparison.indicator)}
                                                </td>
                                                <td>
                                                    {item.percent_difference_from_reference === null
                                                        ? "No data"
                                                        : `${displayNumber(item.percent_difference_from_reference)}%`}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            <h3>Historical comparison</h3>
                            {comparisonTrends && (
                                <div className="chart-frame">
                                    <ResponsiveContainer width="100%" height={320}>
                                        <LineChart data={comparisonTrendRows}>
                                            <CartesianGrid strokeDasharray="3 3" />
                                            <XAxis dataKey="year" />
                                            <YAxis width={72} />
                                            <Tooltip formatter={(value) => [formatValue(Number(value), comparison.indicator.unit)]} />
                                            {comparisonTrends.series.map((series, index) => (
                                                <Line
                                                    key={series.country.iso3}
                                                    type="linear"
                                                    dataKey={series.country.iso3}
                                                    name={series.country.name}
                                                    stroke={PLOT_COLORS[index % PLOT_COLORS.length]}
                                                    dot={false}
                                                    connectNulls={false}
                                                />
                                            ))}
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            )}
                        </>
                    )}
                </section>
            )}

            {page === "rankings" && (
                <section
                    id="analytics-panel-rankings"
                    role="tabpanel"
                    aria-labelledby="analytics-tab-rankings"
                    className="analytics-panel"
                >
                    <p className="source-note">
                        {indicator?.name} · {indicator?.unit} · reporting year {year ?? "—"} · Source: {indicator?.source ?? "—"}.
                        Rankings sort measured values only; they do not represent overall health or imply that higher is better.
                        Population is not a healthcare-quality measure, and expenditure share is not a performance score.
                    </p>
                    <div className="analytics-shared-controls">
                        <label>
                            Sort values
                            <select
                                value={rankingOrder}
                                onChange={(event) => setRankingOrder(event.target.value as "ascending" | "descending")}
                            >
                                <option value="descending">Highest to lowest</option>
                                <option value="ascending">Lowest to highest</option>
                            </select>
                        </label>
                        <label>
                            Search countries
                            <input
                                value={rankingSearch}
                                onChange={(event) => setRankingSearch(event.target.value)}
                                placeholder="Country or ISO-3"
                            />
                        </label>
                    </div>
                    {rankingLoading && <p role="status">Loading country rankings…</p>}
                    {rankingError && <p className="api-error" role="alert">{rankingError}</p>}
                    {!rankingLoading && ranking && (
                        <>
                            <p className="source-note">
                                {ranking.rows.length} countries with observations; countries without a value for {ranking.year} are excluded.
                            </p>
                            {filteredRankingRows.length === 0
                                ? <p className="empty-data-note">No matching countries have data for this indicator and year.</p>
                                : (
                                    <div className="chart-frame">
                                        <ResponsiveContainer width="100%" height={Math.max(300, Math.min(700, filteredRankingRows.slice(0, 20).length * 34))}>
                                            <BarChart
                                                data={filteredRankingRows.slice(0, 20).map(({ rank, observation }) => ({
                                                    country: observation.country_name,
                                                    value: observation.value,
                                                    rank,
                                                }))}
                                                layout="vertical"
                                                margin={{ left: 16, right: 24 }}
                                            >
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis type="number" />
                                                <YAxis type="category" dataKey="country" width={130} />
                                                <Tooltip formatter={(value) => [formatValue(Number(value), ranking.indicator.unit)]} />
                                                <Bar dataKey="value" fill={PLOT_COLORS[0]} />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                )}
                            <div className="table-scroll">
                                <table>
                                    <caption>{ranking.indicator.name} · {ranking.year} · {ranking.indicator.source}</caption>
                                    <thead>
                                        <tr>
                                            <th scope="col">Rank</th>
                                            <th scope="col">Country</th>
                                            <th scope="col">ISO-3</th>
                                            <th scope="col">Value</th>
                                            <th scope="col">Reporting year</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filteredRankingRows.map(({ rank, observation }) => (
                                            <tr key={observation.country_iso3}>
                                                <td>{rank}</td>
                                                <th scope="row">
                                                    <button
                                                        type="button"
                                                        className="table-link"
                                                        onClick={() => {
                                                            const country = countries.find((item) => item.iso3 === observation.country_iso3);
                                                            if (country) {
                                                                chooseCountry(country);
                                                                setPage("explorer");
                                                            }
                                                        }}
                                                    >
                                                        {observation.country_name}
                                                    </button>
                                                </th>
                                                <td>{observation.country_iso3}</td>
                                                <td>{formatValue(observation.value, observation.unit)}</td>
                                                <td>{observation.year}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </section>
            )}
        </section>
    );
}
