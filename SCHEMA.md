# HealthScope AI Database Schema

Phase 2 creates the following tables additively in the existing SQLite database. Existing tables (`country_snapshots`, `life_expectancy`, `nutrition_searches`, and `prediction_history`) are unchanged.

## `health_countries`

- `iso3` — primary key, uppercase ISO-3 code.
- `iso2` — optional ISO-2 code.
- `name`, `region`, `income_level` — World Bank country metadata.
- `updated_at` — metadata refresh time.

## `health_data_sources`

- `code` — primary key (currently `world-bank-wdi`).
- `name`, `url`, `updated_at` — provider provenance.

## `health_indicators`

- `code` — primary key, World Bank indicator code.
- `name`, `definition`, `unit` — API metadata plus normalized unit label.
- `source_code` — foreign key to `health_data_sources`.
- `updated_at` — metadata refresh time.

## `health_indicator_observations`

- `id` — primary key.
- `country_iso3` — foreign key to `health_countries`.
- `indicator_code` — foreign key to `health_indicators`.
- `year`, `value`, `unit` — reported annual observation.
- `source_code` — foreign key to `health_data_sources`.
- `imported_at` — ingestion timestamp.
- Unique constraint: (`country_iso3`, `indicator_code`, `year`); index on (`indicator_code`, `year`).

## `health_data_imports`

Records each per-indicator run: source and indicator, start/completion time, `running`/`success`/`failed` status, received/inserted/updated/missing/rejected counts, and an error summary. The nullable indicator foreign key is populated after provider metadata is validated, so a failed metadata request can still be recorded with its provider, status, and error. API and local CSV/ZIP imports use the same source records and observation schema.

## `health_data_import_checkpoints`

Records each completed API page for an indicator, country scope (empty for global imports), year batch, and page size. A unique key prevents duplicate checkpoints. Successful page writes and checkpoints are committed together; the CLI can resume by skipping completed pages. A small additive SQLite migration adds `page_size` when upgrading a checkpoint table created by the earlier Phase 2 implementation.

## Phase 3 API schemas (no database changes)

Phase 3 adds Pydantic response contracts in `backend/app/schemas/global_analytics.py`; it does not add SQL tables or alter existing rows.

- `TrendAnalysisRead` identifies the indicator and requested inclusive years; each `TrendSeriesRead` includes country metadata, observed rows, the actual first/last reporting years used for change, absolute change, and relative percent change where valid.
- `CountryComparisonRead` includes the shared indicator/year, the first country as `reference_iso3`, and a `ComparisonCountryRead` for every requested country. `observation` and differences are nullable where a country or baseline has no data.
- `IndicatorRankingRead` includes the indicator/year, sort direction, and ordered `RankingRowRead` values. Rows correspond only to stored non-null observations.

The existing country observation response remains the country-profile history contract and includes country metadata plus sourced/year-stamped rows. No persisted aggregate or derived statistics are introduced.

## Phase 4 prediction contracts (no schema change)

`POST /health/predict-life-expectancy` retains the existing JSON feature keys: `adult_mortality`, `bmi`, `gdp`, `schooling`, and `population`. Values must be finite; adult mortality, GDP, and schooling are non-negative, while BMI and population are positive. Invalid values return HTTP 422 with location, message, and validation type only; submitted values are not copied into the error body.

The success response remains `{"predicted_life_expectancy": number}`. `GET /health/predictions` continues to return records from the existing `prediction_history` table, including model inputs, prediction, and creation timestamp. This history is shared across the API deployment and has no user ownership/authentication in the current schema; do not expose it publicly as user-specific data.

No evaluation metrics are persisted with the model artifact. The current WHO table contains 2,938 records from 2000–2015 but has null BMI in every row, so its original complete training split and holdout score are not reproducible from this database. The application reports no MAE/RMSE/R² rather than deriving a misleading score.
