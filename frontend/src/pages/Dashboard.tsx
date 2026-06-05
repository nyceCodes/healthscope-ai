import { useEffect, useState } from "react";

import {
    getCountryProfile,
    getCountryTrends,
    getRankings,
    getRiskAssessment,
    getCountryReport,
    predictLifeExpectancy
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

import TrendChart from "../components/TrendChart";

import "../styles/dashboard.css";

function Dashboard() {

    const [country, setCountry] =
        useState("Philippines");

    const [profile, setProfile] =
        useState<HealthProfile | null>(
            null
        );

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

    const [prediction, setPrediction] =
        useState<number | null>(
            null
        );

    const [predictionForm, setPredictionForm] =
        useState({
            adult_mortality: 100,
            bmi: 25,
            gdp: 12000,
            schooling: 15,
            population: 1000000
        });

    const loadCountry = async () => {

        const response =
            await getCountryProfile(
                country
            );

        setProfile(
            response.data
        );

        const trendResponse =
            await getCountryTrends(
                country
            );

        setTrendData(
            trendResponse.data
        );

        const riskResponse =
            await getRiskAssessment(
                country
            );

        setRiskAssessment(
            riskResponse.data
        );

        const reportResponse =
            await getCountryReport(
                country
            );

        setCountryReport(
            reportResponse.data
        );
    };

    const runPrediction = async () => {

        const response =
            await predictLifeExpectancy(
                predictionForm
            );

        setPrediction(
            response.data
                .predicted_life_expectancy
        );

    };

    useEffect(() => {

        getRankings()
            .then((res) =>
                setRankings(
                    res.data
                )
            );

    }, []);

    return (

        <div className="dashboard">

            <h1>
                HealthScope AI
            </h1>

            <div className="search-form">

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
                    type="button"
                    onClick={loadCountry}
                >
                    Search
                </button>

            </div>

            {profile && (

                <>

                    <div className="profile-card">

                        <h2>
                            {profile.country}
                        </h2>

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
                                <h3>
                                    Health Index
                                </h3>

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

                    {countryReport && (

                        <div className="insights-card">

                            <h2>
                                AI Insights
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

                    {countryReport && (

                        <div className="country-report-card">

                            <h2>
                                Country Intelligence
                            </h2>

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
                                        {countryReport.life_expectancy.gdp.toLocaleString()}
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

                    {countryReport && (

                        <div className="prediction-card">

                            <h2>
                                Life Expectancy Predictor
                            </h2>

                            <div className="prediction-fields">

                                <label>
                                    Adult Mortality
                                    <input
                                        type="number"
                                        value={predictionForm.adult_mortality}
                                        onChange={(e) =>
                                            setPredictionForm({
                                                ...predictionForm,
                                                adult_mortality:
                                                    Number(
                                                        e.target.value
                                                    )
                                            })
                                        }
                                    />
                                </label>

                                <label>
                                    BMI
                                    <input
                                        type="number"
                                        value={predictionForm.bmi}
                                        onChange={(e) =>
                                            setPredictionForm({
                                                ...predictionForm,
                                                bmi:
                                                    Number(
                                                        e.target.value
                                                    )
                                            })
                                        }
                                    />
                                </label>

                                <label>
                                    GDP
                                    <input
                                        type="number"
                                        value={predictionForm.gdp}
                                        onChange={(e) =>
                                            setPredictionForm({
                                                ...predictionForm,
                                                gdp:
                                                    Number(
                                                        e.target.value
                                                    )
                                            })
                                        }
                                    />
                                </label>

                                <label>
                                    Schooling
                                    <input
                                        type="number"
                                        value={predictionForm.schooling}
                                        onChange={(e) =>
                                            setPredictionForm({
                                                ...predictionForm,
                                                schooling:
                                                    Number(
                                                        e.target.value
                                                    )
                                            })
                                        }
                                    />
                                </label>

                                <label>
                                    Population
                                    <input
                                        type="number"
                                        value={predictionForm.population}
                                        onChange={(e) =>
                                            setPredictionForm({
                                                ...predictionForm,
                                                population:
                                                    Number(
                                                        e.target.value
                                                    )
                                            })
                                        }
                                    />
                                </label>

                            </div>

                            <button
                                type="button"
                                onClick={runPrediction}
                            >
                                Predict
                            </button>

                            {prediction && (

                                <div className="prediction-result">

                                    <strong>
                                        Predicted Life Expectancy:
                                    </strong>
                                    {" "}
                                    {prediction}
                                    {" "}
                                    years

                                </div>

                            )}

                        </div>

                    )}

                    {trendData.length > 0 && (

                        <div className="trend-chart">

                            <h3>
                                Trend
                            </h3>

                            <TrendChart
                                data={trendData}
                            />

                        </div>

                    )}

                    {rankings.length > 0 && (

                        <div className="rankings-panel">

                            <h3>
                                Top Health Rankings
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

        </div>

    );

}

export default Dashboard;