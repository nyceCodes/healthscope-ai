import { useCallback, useEffect, useState, type FormEvent } from "react";
import axios from "axios";

import {
    getPredictionHistory,
    predictLifeExpectancy,
} from "../services/healthApi";
import type { LifePredictionRequest } from "../types/LifePrediction";
import type { PredictionHistory } from "../types/PredictionHistory";
import "../styles/predictiveAnalytics.css";

const FEATURES: {
    key: keyof LifePredictionRequest;
    label: string;
    unit: string;
    description: string;
    min: number;
    strictlyPositive?: boolean;
    initial: string;
}[] = [
    {
        key: "adult_mortality",
        label: "Adult mortality",
        unit: "probability per 1,000 population (ages 15–60)",
        description: "Probability of dying between ages 15 and 60 in the WHO dataset.",
        min: 0,
        initial: "100",
    },
    {
        key: "bmi",
        label: "Average BMI",
        unit: "kg/m²",
        description: "Average body mass index in the source dataset.",
        min: 0,
        strictlyPositive: true,
        initial: "25",
    },
    {
        key: "gdp",
        label: "GDP per capita",
        unit: "US dollars per person",
        description: "GDP per capita as recorded in the source dataset.",
        min: 0,
        initial: "12000",
    },
    {
        key: "schooling",
        label: "Schooling",
        unit: "years",
        description: "Average years of schooling in the source dataset.",
        min: 0,
        initial: "15",
    },
    {
        key: "population",
        label: "Population",
        unit: "people",
        description: "Country-year population count.",
        min: 0,
        strictlyPositive: true,
        initial: "1000000",
    },
];

type FormValues = Record<keyof LifePredictionRequest, string>;

function isHistory(data: unknown): data is PredictionHistory[] {
    return Array.isArray(data) && data.every((item: unknown) => {
        if (typeof item !== "object" || item === null) return false;
        const row = item as Record<string, unknown>;
        return (
            typeof row.id === "number"
            && typeof row.adult_mortality === "number"
            && typeof row.bmi === "number"
            && typeof row.gdp === "number"
            && typeof row.schooling === "number"
            && typeof row.population === "number"
            && typeof row.prediction === "number"
            && typeof row.created_at === "string"
            && [
                row.adult_mortality,
                row.bmi,
                row.gdp,
                row.schooling,
                row.population,
                row.prediction,
            ].every((value) => typeof value === "number" && Number.isFinite(value))
            && Number.isFinite(Date.parse(row.created_at))
        );
    });
}

function predictionValue(data: unknown): number {
    if (typeof data !== "object" || data === null) {
        throw new Error("The prediction service returned an unexpected response.");
    }
    const prediction = (data as Record<string, unknown>).predicted_life_expectancy;
    if (typeof prediction !== "number" || !Number.isFinite(prediction)) {
        throw new Error("The prediction service returned an invalid result.");
    }
    return prediction;
}

function errorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (!error.response) {
            return "Cannot connect to the prediction service. Check the backend connection and try again.";
        }
        if (error.response.status === 422) {
            return "Check that every input is finite and non-negative; BMI and population must be greater than zero.";
        }
        const detail: unknown = error.response.data?.detail;
        return typeof detail === "string"
            ? detail
            : `The prediction service returned an error (${error.response.status}).`;
    }
    return error instanceof Error ? error.message : "The prediction request failed.";
}

function initialValues(): FormValues {
    return {
        adult_mortality: "100",
        bmi: "25",
        gdp: "12000",
        schooling: "15",
        population: "1000000",
    };
}

export default function PredictiveAnalytics() {
    const [values, setValues] = useState<FormValues>(initialValues);
    const [prediction, setPrediction] = useState<number | null>(null);
    const [predictionError, setPredictionError] = useState("");
    const [history, setHistory] = useState<PredictionHistory[]>([]);
    const [historyLoading, setHistoryLoading] = useState(true);
    const [historyError, setHistoryError] = useState("");
    const [predicting, setPredicting] = useState(false);

    const loadHistory = useCallback(async () => {
        setHistoryLoading(true);
        setHistoryError("");
        try {
            const response = await getPredictionHistory();
            if (!isHistory(response.data)) {
                throw new Error("The prediction history service returned an unexpected response.");
            }
            setHistory(response.data);
        } catch (error: unknown) {
            setHistoryError(errorMessage(error));
        } finally {
            setHistoryLoading(false);
        }
    }, []);

    useEffect(() => {
        const timer = window.setTimeout(() => {
            void loadHistory();
        }, 0);
        return () => window.clearTimeout(timer);
    }, [loadHistory]);

    const submitPrediction = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setPredictionError("");
        setPrediction(null);

        const invalidFeature = FEATURES.find(({ key, min, strictlyPositive }) => {
            const rawValue = values[key].trim();
            const value = Number(rawValue);
            return (
                rawValue === ""
                || !Number.isFinite(value)
                || value < min
                || (strictlyPositive === true && value === 0)
            );
        });
        if (invalidFeature) {
            setPredictionError(
                `${invalidFeature.label} must be a finite number and ${invalidFeature.strictlyPositive ? "greater than zero" : "at least zero"}.`,
            );
            return;
        }

        const payload: LifePredictionRequest = {
            adult_mortality: Number(values.adult_mortality),
            bmi: Number(values.bmi),
            gdp: Number(values.gdp),
            schooling: Number(values.schooling),
            population: Number(values.population),
        };

        setPredicting(true);
        let predictionSucceeded = false;
        try {
            const response = await predictLifeExpectancy(payload);
            setPrediction(predictionValue(response.data));
            predictionSucceeded = true;
        } catch (error: unknown) {
            setPredictionError(errorMessage(error));
        } finally {
            setPredicting(false);
        }
        if (predictionSucceeded) await loadHistory();
    };

    return (
        <div className="predictive-analytics">
            <header className="predictive-header">
                <h1>Predictive Analytics</h1>
                <p>
                    Explore an illustrative estimate from the existing historical
                    life-expectancy model.
                </p>
            </header>

            <section className="prediction-card" aria-labelledby="prediction-form-heading">
                <h2 id="prediction-form-heading">Life expectancy estimate</h2>
                <p className="prediction-disclaimer">
                    This population-level model is experimental. It is not a
                    clinical tool, individual forecast, or medical advice.
                </p>
                <p className="prediction-disclaimer">
                    Prefilled values are editable examples, not current
                    measurements for the selected country.
                </p>
                <form onSubmit={submitPrediction} noValidate>
                    <div className="prediction-grid">
                        {FEATURES.map(({ key, label, unit, description, min }) => {
                            const inputId = `prediction-${key}`;
                            return (
                                <div className="prediction-field" key={key}>
                                    <label htmlFor={inputId}>
                                        {label} <span>({unit})</span>
                                    </label>
                                    <input
                                        id={inputId}
                                        name={key}
                                        type="number"
                                        min={min}
                                        step="any"
                                        required
                                        value={values[key]}
                                        aria-describedby={`${inputId}-help`}
                                        onChange={(event) => {
                                            setValues((current) => ({
                                                ...current,
                                                [key]: event.target.value,
                                            }));
                                        }}
                                    />
                                    <small id={`${inputId}-help`}>{description}</small>
                                </div>
                            );
                        })}
                    </div>
                    <button className="predict-btn" type="submit" disabled={predicting}>
                        {predicting ? "Calculating estimate…" : "Estimate life expectancy"}
                    </button>
                </form>

                {predicting && <p role="status">Calculating prediction…</p>}
                {predictionError && <p className="api-error" role="alert">{predictionError}</p>}
                {prediction !== null && (
                    <section className="prediction-result" aria-live="polite">
                        <h3>Estimated life expectancy</h3>
                        <p>{new Intl.NumberFormat(undefined, {
                            maximumFractionDigits: 2,
                        }).format(prediction)} years</p>
                    </section>
                )}
            </section>

            <section className="model-info-card" aria-labelledby="model-info-heading">
                <h2 id="model-info-heading">Model, data, and limitations</h2>
                <p>
                    The saved scikit-learn Random Forest regressor uses 100 trees
                    and random seed 42. Its target is historical country-year
                    life expectancy from the WHO Life Expectancy dataset
                    (2000–2015); it is not a future-year forecasting model.
                </p>
                <p>
                    Source dataset:{" "}
                    <a
                        href="https://www.kaggle.com/datasets/kumarajarshi/life-expectancy-who"
                        target="_blank"
                        rel="noreferrer"
                    >
                        Life Expectancy (WHO) on Kaggle
                    </a>.
                </p>
                <h3>Model inputs</h3>
                <ul className="model-feature-list">
                    {FEATURES.map(({ key, label, unit, description }) => (
                        <li key={key}>
                            <strong>{label} — {unit}.</strong> {description}
                        </li>
                    ))}
                </ul>
                <h3>Evaluation status</h3>
                <p>
                    No verified MAE, RMSE, or R² is published. The training script
                    prints a holdout MAE but does not store it with the model, and
                    the retained database has no BMI values to reproduce the
                    training split. No accuracy score is inferred or fabricated.
                </p>
                <p>
                    The model reflects historical country-level associations,
                    not causation or individual health outcomes. Input values
                    outside the training data distribution may be unreliable.
                    Do not use the result for diagnosis or care decisions.
                </p>
            </section>

            <section className="prediction-history-card" aria-labelledby="prediction-history-heading">
                <h2 id="prediction-history-heading">Prediction history</h2>
                <p className="history-privacy-note">
                    History is stored in this deployment’s shared database and is
                    not tied to a signed-in user. Do not enter personally
                    identifying information.
                </p>
                {historyLoading && <p role="status">Loading prediction history…</p>}
                {historyError && <p className="api-error" role="alert">{historyError}</p>}
                {historyError && (
                    <button
                        type="button"
                        className="predict-btn"
                        onClick={() => void loadHistory()}
                        disabled={historyLoading}
                    >
                        Retry loading history
                    </button>
                )}
                {!historyLoading && !historyError && history.length === 0 && (
                    <p>No saved predictions yet.</p>
                )}
                {!historyLoading && history.length > 0 && (
                    <ol className="prediction-history-list">
                        {history.slice(0, 10).map((item) => (
                            <li className="history-row" key={item.id}>
                                <strong>{item.prediction} years</strong>
                                <time dateTime={item.created_at}>
                                    {new Date(item.created_at).toLocaleString()}
                                </time>
                            </li>
                        ))}
                    </ol>
                )}
            </section>
        </div>
    );
}
