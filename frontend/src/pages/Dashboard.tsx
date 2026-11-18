import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import axios from "axios";

import {
    getCountryProfile,
    getCountryTrends,
    getRankings,
    getRiskAssessment,
    getCountryReport,
    getHealthCountries,
    getHealthIndicators,
    getIndicatorYears,
    getIndicatorObservations,
} from "../services/healthApi";

import type { HealthProfile }
from "../types/HealthProfile";

import type { TrendData }
from "../types/TrendData";

import type { Ranking }
from "../types/Ranking";

import type { RiskAssessment }
from "../types/RiskAssessment";

import type { CountryReport }
from "../types/CountryReport";

import type {
    HealthCountry,
    HealthIndicator,
    HealthObservation,
    WorldMapData,
} from "../types/HealthIndicator";

import "../styles/dashboard.css";

const TrendChart = lazy(() => import("../components/TrendChart"));
const WorldIndicatorMap = lazy(() => import("../components/WorldIndicatorMap"));
const GlobalAnalytics = lazy(() => import("../components/GlobalAnalytics"));

function errorText(err: unknown): string {
    if (axios.isAxiosError(err)) {
        if (!err.response) {
            return "Cannot connect to the backend. Check that uvicorn is running on port 8000.";
        }
        const detail: unknown = err.response.data?.detail;
        return typeof detail === "string" ? detail : `Request failed (${err.response.status}).`;
    }
    return err instanceof Error ? err.message : "Unexpected error occurred.";
}

function Dashboard() {

    const [country, setCountry] =
        useState("Philippines");

    const [profile, setProfile] =
        useState<HealthProfile | null>(
            null
        );
    const [countrySectionErrors, setCountrySectionErrors] = useState({
        trends: "",
        risk: "",
        report: "",
    });

    const [trendData, setTrendData] =
        useState<TrendData[]>([]);

    const [rankings, setRankings] =
        useState<Ranking[]>([]);

    const [riskAssessment, setRiskAssessment] =
        useState<RiskAssessment | null>(
            null
        );

    const [countryReport, setCountryReport] =
        useState<CountryReport | null>(
            null
        );

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [rankingsError, setRankingsError] = useState("");
    const [healthCountries, setHealthCountries] = useState<HealthCountry[]>([]);
    const [healthIndicators, setHealthIndicators] = useState<HealthIndicator[]>([]);
    const [selectedIndicatorCode, setSelectedIndicatorCode] = useState("");
    const [indicatorYears, setIndicatorYears] = useState<number[]>([]);
    const [selectedYear, setSelectedYear] = useState<number | null>(null);
    const [mapObservations, setMapObservations] = useState<HealthObservation[]>([]);
    const [worldMap, setWorldMap] = useState<WorldMapData | null>(null);
    const [selectedMapCountry, setSelectedMapCountry] = useState<string | null>(null);
    const [mapLoading, setMapLoading] = useState(false);
    const [mapError, setMapError] = useState("");
    const [catalogError, setCatalogError] = useState("");
    const [boundaryError, setBoundaryError] = useState("");

    const loadCountry = useCallback(async (requestedCountry: string) => {
        const name = requestedCountry.trim();
        if (!name) {
            setError("Enter a country name.");
            return;
        }
        setLoading(true);
        setError("");
        setProfile(null);
        setTrendData([]);
        setRiskAssessment(null);
        setCountryReport(null);
        setCountrySectionErrors({ trends: "", risk: "", report: "" });
        try {
            const response = await getCountryProfile(name);
            setProfile(response.data);
            const [trends, risk, report] = await Promise.allSettled([
                getCountryTrends(name),
                getRiskAssessment(name),
                getCountryReport(name),
            ]);
            if (trends.status === "fulfilled") setTrendData(trends.value.data);
            if (risk.status === "fulfilled") setRiskAssessment(risk.value.data);
            if (report.status === "fulfilled") setCountryReport(report.value.data);
            setCountrySectionErrors({
                trends: trends.status === "rejected" ? errorText(trends.reason) : "",
                risk: risk.status === "rejected" ? errorText(risk.reason) : "",
                report: report.status === "rejected" ? errorText(report.reason) : "",
            });
        } catch (err) {
            setError(errorText(err));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        const initialLoad = window.setTimeout(() => { void loadCountry("Philippines"); }, 0);
        getRankings()
            .then((response) => setRankings(response.data))
            .catch((err: unknown) => setRankingsError(errorText(err)));
        return () => window.clearTimeout(initialLoad);
    }, [loadCountry]);

    useEffect(() => {
        let cancelled = false;
        Promise.allSettled([getHealthCountries(), getHealthIndicators()])
            .then(([countriesResult, indicatorsResult]) => {
                if (cancelled) return;
                const errors: string[] = [];
                if (countriesResult.status === "fulfilled") {
                    setHealthCountries(countriesResult.value.data);
                } else {
                    errors.push(`Country list unavailable: ${errorText(countriesResult.reason)}`);
                }
                if (indicatorsResult.status === "fulfilled") {
                    setHealthIndicators(indicatorsResult.value.data);
                } else {
                    errors.push(`Indicator list unavailable: ${errorText(indicatorsResult.reason)}`);
                }
                setCatalogError(errors.join(" "));
                if (
                    indicatorsResult.status === "fulfilled"
                    && indicatorsResult.value.data.length > 0
                ) {
                    setMapLoading(true);
                    setSelectedIndicatorCode((current) =>
                        indicatorsResult.value.data.some((item) => item.code === current)
                            ? current
                            : (indicatorsResult.value.data.find((item) => item.latest_year !== null)
                                ?? indicatorsResult.value.data[0]).code,
                    );
                }
            });

        fetch("/data/ne_110m_admin_0_countries.geojson")
            .then((response) => {
                if (!response.ok) throw new Error("Could not load world map boundaries.");
                return response.json() as Promise<WorldMapData>;
            })
            .then((data) => {
                if (!cancelled) {
                    setWorldMap(data);
                    setBoundaryError("");
                }
            })
            .catch((err: unknown) => {
                if (!cancelled) {
                    setBoundaryError(
                        err instanceof Error
                            ? err.message
                            : "Could not load world map boundaries.",
                    );
                }
            });
        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        if (!selectedIndicatorCode) return;
        let cancelled = false;
        getIndicatorYears(selectedIndicatorCode)
            .then((response) => {
                if (cancelled) return;
                setIndicatorYears(response.data);
                setSelectedYear(response.data[0] ?? null);
                if (response.data.length === 0) setMapLoading(false);
            })
            .catch((err: unknown) => {
                if (!cancelled) {
                    setMapError(errorText(err));
                    setMapLoading(false);
                }
            });
        return () => {
            cancelled = true;
        };
    }, [selectedIndicatorCode]);

    useEffect(() => {
        if (!selectedIndicatorCode || selectedYear === null) return;
        let cancelled = false;
        getIndicatorObservations(selectedIndicatorCode, selectedYear)
            .then((response) => {
                if (!cancelled) setMapObservations(response.data.observations);
            })
            .catch((err: unknown) => {
                if (!cancelled) setMapError(errorText(err));
            })
            .finally(() => {
                if (!cancelled) setMapLoading(false);
            });
        return () => {
            cancelled = true;
        };
    }, [selectedIndicatorCode, selectedYear]);

    const selectedIndicator = healthIndicators.find(
        (indicator) => indicator.code === selectedIndicatorCode,
    );
    const selectedMapObservation = mapObservations.find(
        (observation) => observation.country_iso3 === selectedMapCountry,
    );

    return (

        <div className="dashboard">

            <h1>
                HealthScope AI
            </h1>

            <p className="dashboard-subtitle">Country health indicators, historical comparisons, and life expectancy modeling.</p>

            <form className="search-form" onSubmit={(e) => { e.preventDefault(); void loadCountry(country); }}>

                <input
                    type="text"
                    value={country}
                    onChange={(e) =>
                        setCountry(
                            e.target.value
                        )
                    }
                    placeholder="Enter a country"
                />

                <button
                    type="submit"
                    disabled={loading}
                >
                    {loading ? "Loading..." : "Search"}
                </button>

            </form>

            <section className="global-health-data" aria-labelledby="global-data-heading">
                <h2 id="global-data-heading">Global health indicators</h2>
                <p className="source-note">
                    Stored country-level observations from World Bank WDI and WHO GHO. Source update periods vary; values are not live readings.
                </p>
                <div className="indicator-controls">
                    <label>
                        Indicator
                        <select
                            value={selectedIndicatorCode}
                            onChange={(event) => {
                                setSelectedIndicatorCode(event.target.value);
                                setSelectedYear(null);
                                setIndicatorYears([]);
                                setMapObservations([]);
                                setMapLoading(true);
                                setMapError("");
                                setSelectedMapCountry(null);
                            }}
                            disabled={healthIndicators.length === 0}
                        >
                            {healthIndicators.map((indicator) => (
                                <option key={indicator.code} value={indicator.code}>
                                    {indicator.name}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label>
                        Reporting year
                        <select
                            value={selectedYear ?? ""}
                            onChange={(event) => {
                                setSelectedYear(Number(event.target.value));
                                setMapObservations([]);
                                setMapLoading(true);
                                setMapError("");
                            }}
                            disabled={indicatorYears.length === 0}
                        >
                            {indicatorYears.map((year) => (
                                <option key={year} value={year}>{year}</option>
                            ))}
                        </select>
                    </label>
                </div>
                {selectedIndicator && selectedYear !== null && (
                    <p className="indicator-definition">
                        {selectedIndicator.definition}
                        {" "}Source: {selectedIndicator.source}.
                        {selectedIndicator.publisher ? ` Publisher: ${selectedIndicator.publisher}.` : ""}
                        {selectedIndicator.dataset_name ? ` Dataset: ${selectedIndicator.dataset_name}.` : ""}
                        {" "}Reporting year: {selectedYear}.
                        {selectedIndicator.latest_year !== null && selectedYear < selectedIndicator.latest_year
                            ? ` Historical selection; latest year available is ${selectedIndicator.latest_year}.`
                            : ""}
                        {selectedIndicator.definition_url && (
                            <>
                                {" "}
                                <a
                                    href={selectedIndicator.definition_url}
                                    target="_blank"
                                    rel="noreferrer"
                                >
                                    Official metadata
                                </a>
                            </>
                        )}
                        {selectedMapObservation?.source_reference?.startsWith("https://") && (
                            <>
                                {" "}
                                <a
                                    href={selectedMapObservation.source_reference}
                                    target="_blank"
                                    rel="noreferrer"
                                >
                                    Selected observation source
                                </a>
                            </>
                        )}
                    </p>
                )}
                {catalogError && <p className="api-error" role="alert">{catalogError}</p>}
                {boundaryError && <p className="api-error" role="alert">{boundaryError}</p>}
                {mapError && <p className="api-error" role="alert">{mapError}</p>}
                {mapLoading && <p className="loading-status" role="status">Loading indicator observations…</p>}
                {!mapLoading && healthIndicators.length === 0 && !mapError && !catalogError && (
                    <p className="empty-data-note">
                        No indicators are stored yet. Run the documented source-specific import command to load official observations.
                    </p>
                )}
                {!mapLoading && selectedIndicator && indicatorYears.length === 0 && !mapError && !catalogError && (
                    <p className="empty-data-note" role="status">
                        No observations are stored for {selectedIndicator.name}. Run its documented source-specific import or refresh before exploring this indicator.
                    </p>
                )}
                {worldMap && selectedIndicator && selectedYear !== null && (
                    <Suspense fallback={<p className="loading-status" role="status">Loading map…</p>}>
                        <WorldIndicatorMap
                            geography={worldMap}
                            countries={healthCountries}
                            indicator={selectedIndicator}
                            year={selectedYear}
                            observations={mapObservations}
                            selectedCountry={selectedMapCountry}
                            onSelectCountry={(iso3, name) => {
                                setSelectedMapCountry(iso3);
                                setCountry(name);
                            }}
                        />
                    </Suspense>
                )}
            </section>

            <Suspense fallback={<p className="loading-status" role="status">Loading analytics…</p>}>
                <GlobalAnalytics
                    countries={healthCountries}
                    indicators={healthIndicators}
                    indicatorCode={selectedIndicatorCode}
                    year={selectedYear}
                    years={indicatorYears}
                    selectedIso3={selectedMapCountry}
                    onSelectIndicator={(code) => {
                        setSelectedIndicatorCode(code);
                        setSelectedYear(null);
                        setIndicatorYears([]);
                        setMapObservations([]);
                        setMapLoading(true);
                        setMapError("");
                    }}
                    onSelectYear={(year) => {
                        setSelectedYear(year);
                        setMapObservations([]);
                        setMapLoading(true);
                        setMapError("");
                    }}
                    onSelectCountry={(iso3) => {
                        setSelectedMapCountry(iso3);
                        setCountry(
                            healthCountries.find((item) => item.iso3 === iso3)?.name ?? iso3,
                        );
                    }}
                />
            </Suspense>

            {error && <div className="api-error" role="alert">{error}</div>}
            {loading && <p className="loading-status" role="status">Loading health profile…</p>}

            {profile && (

                <>

                    <div className="profile-card">

                        <h2>{profile.country}</h2>
                        <p className="source-note">
                            Source: {profile.data_source}. {profile.data_status}.
                            {profile.data_as_of && ` Saved/retrieved: ${new Date(profile.data_as_of).toLocaleString()}.`}
                        </p>

                        <div className="cards">

                            <div className="card">
                                <h3>
                                    Population
                                </h3>

                                <p>
                                    {profile.population.toLocaleString()}
                                </p>
                            </div>

                            <div className="card">
                                <h3>Experimental Health Index</h3>

                                <p>
                                    {profile.health_index}
                                </p>
                            </div>

                            <div className="card">
                                <h3>
                                    Recovery Rate
                                </h3>

                                <p>
                                    {profile.recovery_rate}%
                                </p>
                            </div>

                            <div className="card">
                                <h3>
                                    Mortality Rate
                                </h3>

                                <p>
                                    {profile.mortality_rate}%
                                </p>
                            </div>

                        </div>

                    </div>

                    {riskAssessment && (

                        <div className="risk-card">

                            <h2>
                                Risk Assessment
                            </h2>

                            <h3>
                                {riskAssessment.risk_level}
                            </h3>

                            <h4>
                                Reasons
                            </h4>

                            <ul>

                                {riskAssessment.reasons.map(
                                    (
                                        reason,
                                        index
                                    ) => (

                                        <li
                                            key={index}
                                        >
                                            {reason}
                                        </li>

                                    )
                                )}

                            </ul>

                            <h4>
                                Recommendations
                            </h4>

                            <ul>

                                {riskAssessment.recommendations.map(
                                    (
                                        recommendation,
                                        index
                                    ) => (

                                        <li
                                            key={index}
                                        >
                                            {recommendation}
                                        </li>

                                    )
                                )}

                            </ul>

                        </div>

                    )}
                    {countrySectionErrors.risk && (
                        <p className="api-error" role="alert">
                            Risk assessment unavailable: {countrySectionErrors.risk}
                        </p>
                    )}

                    {countryReport && (

                        <div className="insights-card">

                            <h2>
                                Rule-Based Insights
                            </h2>

                            <ul>

                                {countryReport.insights.map(
                                    (
                                        insight,
                                        index
                                    ) => (

                                        <li
                                            key={index}
                                        >
                                            {insight}
                                        </li>

                                    )
                                )}
                            </ul>

                        </div>

                    )}
                    {countrySectionErrors.report && (
                        <p className="api-error" role="alert">
                            Country report unavailable: {countrySectionErrors.report}
                        </p>
                    )}

                    {countryReport && (

                        <div className="country-report-card">

                            <h2>
                                Country Intelligence
                            </h2>
                            <p className="source-note">WHO life expectancy historical dataset ({countryReport.life_expectancy.year}). Not current-year statistics.</p>

                            <div className="cards">

                                <div className="card">

                                    <h3>
                                        Life Expectancy
                                    </h3>

                                    <p>
                                        {countryReport.life_expectancy.value}
                                    </p>

                                </div>

                                <div className="card">

                                    <h3>
                                        Schooling
                                    </h3>

                                    <p>
                                        {countryReport.life_expectancy.schooling}
                                    </p>

                                </div>

                                <div className="card">

                                    <h3>
                                        GDP
                                    </h3>

                                    <p>
                                        {countryReport.life_expectancy.gdp?.toLocaleString() ?? "N/A"}
                                    </p>

                                </div>

                                <div className="card">

                                    <h3>
                                        Global Gap
                                    </h3>

                                    <p>
                                        {countryReport.global_comparison.life_expectancy_gap}
                                        {" "}years
                                    </p>

                                </div>

                            </div>

                            <div
                                style={{
                                    marginTop: "1rem"
                                }}
                            >

                                <strong>
                                    Global Leader:
                                </strong>
                                {" "}
                                {countryReport.global_comparison.top_country}

                            </div>

                        </div>

                    )}

                    {trendData.length > 0 && (

                        <div className="trend-chart">

                            <h3>
                                Experimental Health Index · Saved Snapshot Trend
                            </h3>

                            <Suspense fallback={<p className="loading-status" role="status">Loading chart…</p>}>
                                <TrendChart data={trendData} />
                            </Suspense>

                        </div>

                    )}
                    {countrySectionErrors.trends && (
                        <p className="api-error" role="alert">
                            Saved snapshot trend unavailable: {countrySectionErrors.trends}
                        </p>
                    )}

                    {rankings.length > 0 && (

                        <div className="rankings-panel">

                            <h3>
                                Experimental Health Index Order (Saved Data)
                            </h3>

                            <div className="rankings-list">

                                {rankings
                                    .slice(0, 10)
                                    .map(
                                        (
                                            item,
                                            index
                                        ) => (

                                            <div
                                                className="ranking-row"
                                                key={`${item.country}-${index}`}
                                            >

                                                <span>
                                                    {index + 1}.
                                                </span>

                                                <span>
                                                    {item.country}
                                                </span>

                                                <span>
                                                    {item.health_index}
                                                </span>

                                            </div>

                                        )
                                    )}
                            </div>

                        </div>

                    )}

                </>

            )}
            {rankingsError && <p className="api-error" role="alert">{rankingsError}</p>}

        </div>

    );

}

export default Dashboard;