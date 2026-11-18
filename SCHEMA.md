# HealthScope AI Database Schema

Phase 2 created the global health-data tables additively in the existing SQLite database. Task 2 adds nullable provenance columns and a revision table. Existing profile/model tables (`country_snapshots`, `life_expectancy`, `nutrition_searches`, and `prediction_history`) are unchanged.

## `health_countries`

- `iso3` — primary key, uppercase ISO-3 code.
- `iso2` — optional ISO-2 code.
- `name`, `region`, `income_level` — World Bank metadata; WHO-only country references may have region but no income-level metadata.
- `updated_at` — metadata refresh time.

## `health_data_sources`

- `code` — primary key (`world-bank-wdi` or `who-gho-odata`).
- `name`, `url`, `updated_at` — provider provenance.

## `health_indicators`

- `code` — primary key, source-specific indicator code.
- `name`, `definition`, `unit` — source name, documented definition, and normalized unit label.
- `source_code` — foreign key to `health_data_sources`.
- `publisher`, `definition_url` — producing organization(s) and official metadata reference where known. WDI's historical backfill identifies its distribution source and explicitly records that historical source-organization detail was not captured.
- `dataset_code`, `dataset_name`, `dataset_version` — provider dataset identity. Version remains null when the source does not supply one.
- `updated_at` — metadata refresh time.

## `health_indicator_observations`

- `id` — primary key.
- `country_iso3` — foreign key to `health_countries`.
- `indicator_code` — foreign key to `health_indicators`.
- `year`, `value`, `unit` — reported annual observation.
- `source_code` — foreign key to `health_data_sources`.
- `imported_at` — ingestion timestamp.
- `source_reference` — source-row citation/comment or direct provider endpoint.
- `source_publication_date` — source publication date when explicitly supplied; not inferred from other timestamps.
- `source_record_timestamp` — provider row/update timestamp (WHO GHO `Date`); not the observation year or publication date.
- `source_value_text` — provider-formatted value, including any displayed interval.
- `denominator_value`, `denominator_definition` — numeric denominator if supplied and documented denominator description. Numeric denominators are not supplied for these GHO series and remain null.
- `dimensions_json` — source dimension type/value pairs. Neonatal mortality is fixed to both sexes and 0–27 days; other imported WHO series use the nondisaggregated row.
- `uncertainty_lower`, `uncertainty_upper` — optional paired source bounds. Bounds are retained but are not labeled a confidence interval unless the source specifies that interpretation.
- `estimate_status` — series-level status such as modeled estimate, WUENIC estimate, variable source method, or composite index.
- Unique constraint: (`country_iso3`, `indicator_code`, `year`); index on (`indicator_code`, `year`).

The current key is safe for the six imported WHO codes because each is filtered to one canonical dimension combination. It is not a general key for loading multiple sex/age strata under the same indicator code.

## `health_indicator_observation_revisions`

Captures the previous value, unit, source, import timestamp, and serialized provenance whenever a re-import changes a value or its provenance. Exact no-change refreshes do not create a revision. The current observation remains the unique country/indicator/year row.

## `health_data_imports`

Records each per-indicator run: source and indicator, start/completion time, `running`/`success`/`failed` status, received/inserted/updated/missing/rejected/duplicate counts, and an error summary. The nullable indicator foreign key is populated after provider metadata is validated where possible, so a failed metadata request can still be recorded with its provider, status, and error. WDI API/CSV and WHO GHO imports use the same observation schema.

## `health_data_import_checkpoints`

Records each completed API page for an indicator, country scope (empty for global imports), year batch, and page size. A unique key prevents duplicate checkpoints. Successful page writes and checkpoints are committed together; the CLI can resume by skipping completed pages. A small additive SQLite migration adds `page_size` when upgrading a checkpoint table created by the earlier Phase 2 implementation.

## Additive Task 2 migration

`ensure_health_data_schema()` adds missing nullable source, publisher, dataset, dimension, denominator, timestamp, uncertainty, and status columns to the existing SQLite tables with `ALTER TABLE`; it also adds `rows_duplicate` to old import logs. `Base.metadata.create_all()` creates the new revision table. Existing production data is not deleted or rewritten into a replacement table. Legacy WDI rows are backfilled with the WDI distribution endpoint, an empty dimension object, and an explicit `legacy_method_not_recorded` marker; no historical release or upstream producer is invented.

## Phase 3 API schemas (no database changes)

Phase 3 adds Pydantic response contracts in `backend/app/schemas/global_analytics.py`; it does not add SQL tables or alter existing rows.

- `TrendAnalysisRead` identifies the indicator and requested inclusive years; each `TrendSeriesRead` includes country metadata, observed rows, the actual first/last reporting years used for change, absolute change, and relative percent change where valid.
- `CountryComparisonRead` includes the shared indicator/year, the first country as `reference_iso3`, and a `ComparisonCountryRead` for every requested country. `observation` and differences are nullable where a country or baseline has no data.
- `IndicatorRankingRead` includes the indicator/year, sort direction, and ordered `RankingRowRead` values. Rows correspond only to stored non-null observations.

Country and indicator responses include publisher/dataset references; each observation response exposes source references, provider/publication/import timestamps, dimensions, denominator definitions, uncertainty bounds, and estimate status. `GET /health/data/coverage` returns country/indicator observation counts, actual observed years, unobserved gaps within the observed span, and a note that expected cadence is not inferred. No persisted aggregate or derived statistics are introduced.

## Phase 4 prediction contracts (no schema change)

`POST /health/predict-life-expectancy` retains the existing JSON feature keys: `adult_mortality`, `bmi`, `gdp`, `schooling`, and `population`. Values must be finite; adult mortality, GDP, and schooling are non-negative, while BMI and population are positive. Invalid values return HTTP 422 with location, message, and validation type only; submitted values are not copied into the error body.

The success response remains `{"predicted_life_expectancy": number}`. Local development can read/write the existing `prediction_history` table. In production, the same anonymous prediction route returns a result without persisting inputs, and `GET /health/predictions` returns 404. Production startup rejects a database containing prediction-history records. No schema migration is required.

No evaluation metrics are persisted with the model artifact. The current KaggleHub-loaded WHO-labelled table contains 2,938 records from 2000–2015 but has null BMI in every row, so its original complete training split and holdout score are not reproducible from this database. The application reports no MAE/RMSE/R² rather than deriving a misleading score.

## Phase 5B production SQLite seed

`python -m scripts.create_production_seed --output deployment/healthscope.db` creates a separate copy of the selected database. The source is opened read-only and is never overwritten. The copy preserves country snapshots, KaggleHub-loaded WHO-labelled life-expectancy rows, source/indicator references, WDI/WHO GHO observations, and any public-data revision records. It empties `prediction_history`, `nutrition_searches`, `health_data_imports`, and `health_data_import_checkpoints`; application startup can recreate empty operational tables. The builder checks SQLite integrity and verifies row counts.

The Task 2 seed contains 47,303 observations (20,312 WDI and 26,991 WHO GHO), 221 country/economy entries, 10 indicators, two source records, 38 country snapshots, and 2,938 legacy KaggleHub-loaded WHO-labelled rows. It contains zero prediction-history records, nutrition searches, or import-operation rows. The local development database is Git-ignored; never use it as production data.

Production requires `HEALTHSCOPE_DATABASE_PATH` to name an absolute, existing SQLite file distinct from the local database. A persistent volume can be initialized from the seed once and retained across deploys. Ephemeral storage must be initialized from the packaged seed on each new instance; runtime writes will not survive restarts. Neither WDI nor WHO ingestion runs automatically.

## Task 1 pre-expansion data audit (historical snapshot)

The database was inspected read-only on 2026-11-18 before Task 2 import. Both local SQLite files reported `integrity_check=ok`. The main development database at that point contained:

| Table/data | Current rows | Coverage/notes |
|---|---:|---|
| `health_countries` | 217 | World Bank country/economy entries; this is not a count of sovereign states |
| `health_indicators` | 4 | World Bank WDI indicators listed in this document |
| `health_indicator_observations` | 20,312 | 2000–2024 |
| `SP.DYN.LE00.IN` | 5,425 | 217 entries; annual rows 2000–2024 |
| `SP.POP.TOTL` | 5,425 | 217 entries; annual rows 2000–2024 |
| `SH.DYN.MORT` | 4,900 | 196 entries; 525 absent entry-years across the 25-year range |
| `SH.XPD.CHEX.GD.ZS` | 4,562 | 193 entries; 863 absent entry-years across the 25-year range |
| `health_data_imports` | 14 | 10 success, 4 failed; manual/import-time records |
| `country_snapshots` | 38 | 5 countries; source-observation date is not separately represented |
| `life_expectancy` | 2,938 | KaggleHub WHO-labelled dataset, 193 countries, 2000–2015; BMI null in all rows and target null in 10 |
| `prediction_history` | 3 | Local user-entered model-input history; zero in generated production seed |

These are pre-expansion point-in-time counts; the observed row count does not mean every country has every year or that all years have identical methodology. WDI candidate observation requests returned HTTP 502 in that audit. Task 2 subsequently chose six verified WHO GHO series as separate indicators and imported them as documented below.

### Provenance limitations recorded before Task 2

- The pre-Task2 schema captured source code/import time but lacked provider publisher, source references, release timestamps, dimensions, uncertainty bounds, denominators, and revision history. Task 2 adds these fields where available; historical WDI rows still cannot be backfilled with their exact old source vintage or original producer.
- `health_indicator_observations` remains one row per country + indicator + year, with a non-null `Float` value; source nulls are omitted and missingness is implicit in no row. The six imported WHO codes each have one canonical dimension selection. Arbitrary sex/age/population-group strata and subnational geography are not represented.
- Dataset versions and source-publication dates remain null when the provider does not publish those fields; `source_record_timestamp` is not a substitute.
- Legacy `life_expectancy` has no source or release columns and no unique country-year constraint. Its current records came from a KaggleHub dataset loader; do not label those rows as direct WHO API observations. The local table cannot reproduce the model training sample because BMI is missing throughout.
- `country_snapshots.created_at` is a local snapshot/retrieval timestamp, not a guarantee of upstream observation time. `prediction_history` stores submitted model feature values and outputs and must not be used as seed content.

### Future additions only after design review

For WDI-sourced candidates, extend the current indicator metadata and allowlisted importer without changing the observation grain, provided each candidate truly represents a country/economy-year series. Retain source organization, original source/method URL, normalized unit, exact definition, publication/estimate type, and revision/attribution note when available.

Before importing additional WHO dimensions or arbitrary disaggregated series, design an explicit observation-dimension identity and unique key that preserves indicator + geography + period + dimension values + source/vintage. A nullable sex/age column added to the current unique key is not sufficient because SQLite permits multiple `NULL` values in a unique constraint. Decide whether dimensions belong in a normalized dimension table or a canonical serialized key and prove idempotent upsert behavior with tests. Keep country/economy and subnational geography identifiers distinct.

Do not add patient, person, encounter, or re-identification fields for this product direction. Maintain source release/import history separately from measurement time; do not overload `imported_at` to represent data collection/publication time. Any schema changes require an additive, reviewed migration and tests against a copy, not changes to the local production/source database during product planning. Review reuse/licensing and attribution terms before publishing new source data.
