# HealthScope AI Architecture

## Phase 2 data path

The existing FastAPI services and React dashboard remain in place. Global indicator data is loaded only by the explicit backend ingestion command:

1. `backend/app/services/world_bank_service.py` supports World Bank Indicators API v2 and official WDI CSV/ZIP or DataBank exports. The API client fetches WDI metadata and paginated rows; the CSV parser streams rows, validates export headers and requested years, and uses the same country normalization/upserts.
2. `backend/app/services/who_gho_service.py` is a separate, allowlisted WHO GHO OData adapter for six verified indicators. It validates metadata, country type/ISO-3, reporting year, unit, canonical dimension values, numeric bounds, and records the source's row timestamp separately from the reporting year/import time. WHO pagination supports both continuation links and `$skip` offset paging; missing ISO-3 country metadata is resolved through the WHO `RegionCountry` endpoint.
3. Both importers write the normalized `health_indicator_observations` table through `observation_service.py`. The uniqueness key remains country/indicator/year because each WHO code imports only one approved dimension set; neonatal mortality is explicitly limited to both sexes and 0–27 days. The source values are not combined with WDI or other WHO dimensions.
4. Changed measurement values or provenance are captured in `health_indicator_observation_revisions` before upsert. Identical refreshes update local import time without generating revisions. Import-run records count received, inserted, updated, missing, rejected, and duplicate rows.
5. `coverage_service.py` summarizes actual country/indicator observed years. It calls gaps “unobserved years within the observed span,” not expected missing annual reports. The reproducible CSV is `backend/reports/health_data_coverage.csv`.
6. `backend/app/api/health_data_routes.py` exposes all stored sources through typed catalog, observation, history, analytics, and `/coverage` endpoints. Dashboard requests never call the World Bank or WHO providers.
7. React displays the stored observations on the Natural Earth map and analytics workspace. The UI identifies the selected source, publisher, and official metadata link; exports include row-level provenance fields.

## Database and migration strategy

`Base.metadata.create_all()` creates new tables, and `ensure_health_data_schema()` applies nullable provenance columns and the duplicate counter to existing SQLite tables with additive `ALTER TABLE` statements. No existing table is copied or replaced. Legacy WDI rows are backfilled with the WDI distribution endpoint and are explicitly marked as lacking a captured historical upstream producer/method; their prior source release is not inferred. Snapshots, the separate KaggleHub-loaded WHO-labelled life-expectancy rows, and the ML model remain unchanged.

The observation model records source references, source record timestamp, source publication date where supplied, provider display text, denominator value/definition when supplied, source dimensions, uncertainty bounds, and estimate status. GHO currently exposes a record timestamp (`Date`) but not a publication date or dataset version for these rows; those fields remain null rather than being inferred. The numeric denominator is also not exposed for the imported GHO series, while the denominator definition is documented per indicator.

## Task 2 WHO GHO data inventory and boundaries

The verified import snapshot was generated on 2026-11-18 from the official WHO GHO OData API, restricted to reporting years 2000–2026. It added 26,991 observations across six allowlisted indicators and four WHO country references not present in the pre-existing WDI country catalog. The combined seed has 47,303 observations, 10 indicators, 221 country/economy references, and two provider records.

| Code | Stored unit | Observations | Countries | Stored year span |
|---|---|---:|---:|---|
| `MDG_0000000026` | Deaths per 100,000 live births | 4,680 | 195 | 2000–2023 |
| `WHOSIS_000003` | Deaths per 1,000 live births | 5,000 | 200 | 2000–2024 |
| `WHS4_100` | Percent | 5,051 | 195 | 2000–2025 |
| `MDG_0000000020` | Cases per 100,000 population per year | 5,013 | 196 | 2000–2025 |
| `MDG_0000000025` | Percent of births | 2,567 | 193 | 2000–2024 |
| `UHC_INDEX_REPORTED` | Index (0–100) | 4,680 | 195 | 2000–2023 |

These are actual stored row/year bounds, not statements of complete annual reporting. Skilled birth attendance is notably irregular by country/year; WDI and WHO update schedules differ and the system has no scheduled refresh. Review [README.md](./README.md) for definitions, units, observed coverage, known gaps, and release caveats.

The WHO adapter rejects unsupported codes and non-country rows. It imports the neonatal series only for `SEX_BTSX` and `AGEGROUP_DAYS0-27`, and stores both the dimension type and value codes. No other arbitrary strata are aggregated. Duplicate rows for a country/code/year are reconciled only when their source record timestamp is decisive; a conflicting duplicate with a tied or missing timestamp fails that indicator import. The shared unique key prevents duplicates in SQLite.

Source datasets/version fields are populated where the provider identifies them; `dataset_version` is null for GHO because the API returned no version. WUENIC is explicitly named for DTP3; the other source datasets have indicator-specific names and publishers. WHO provider record timestamps are not mislabeled as publication dates.

The GHO API documentation is at https://www.who.int/data/gho/info/gho-odata-api; the metadata registry is https://www.who.int/data/gho/indicator-metadata-registry. Source-specific reuse/licensing and complete attribution terms remain unresolved and require review before public production release.

## Components

- `backend/app/models/health_indicator.py`: normalized global health-data tables.
- `backend/app/services/world_bank_service.py`: WDI API/CSV client, validation, upserts, checkpointing, and import history.
- `backend/app/services/who_gho_service.py`: six-series WHO OData adapter, source-specific dimension policy, paging, validation, and import history.
- `backend/app/services/observation_service.py`: shared idempotent upsert and change-history capture.
- `backend/app/services/coverage_service.py`: country/indicator observed-year summary.
- `backend/app/database/database.py`: additive health-data provenance migration.
- `backend/scripts/ingest_world_bank.py`: initial and repeatable API or local CSV/ZIP import CLI.
- `backend/scripts/ingest_who_gho.py`: WHO GHO import CLI.
- `backend/scripts/report_health_data_coverage.py`: reproducible coverage CSV generation.
- `backend/app/api/health_data_routes.py`: read-only stored-data endpoints.
- `frontend/src/components/WorldIndicatorMap.tsx`: accessible SVG choropleth, hover details, and legend.
- `frontend/src/pages/Dashboard.tsx`: indicator/year selection and country observations.

## Sources

- World Bank Indicators API v2: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
- World Development Indicators bulk archive: https://databank.worldbank.org/source/world-development-indicators
- WHO GHO OData API: https://www.who.int/data/gho/info/gho-odata-api
- WHO GHO Indicator metadata registry: https://www.who.int/data/gho/indicator-metadata-registry
- Natural Earth 1:110m Admin 0 country boundaries: https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/

## Phase 3 analytics

The analytics workspace consumes the same stored SQLite observations and shares the dashboard's country, indicator, and selected-year state. It does not create tables, contact the World Bank at runtime, or download the whole observation dataset.

- `GET /health/data/countries/{iso3}/observations` returns one country's stored indicator history and country metadata. The explorer selects the latest actually stored observation independently for each metric and displays that observation's year and source; it does not fill gaps from another year.
- `GET /health/data/analytics/trends` accepts an indicator code, 1–5 ISO-3 country codes, and inclusive start/end years. It returns only matching observations, including empty series for countries with no data in the requested period. Change values use each series' first and last observed rows in the selected range. A change is unavailable with fewer than two distinct observed years; relative change is unavailable when the baseline is zero.
- `GET /health/data/analytics/compare` accepts 2–5 ISO-3 codes, one indicator, and one reporting year. It returns every requested country, using a null observation when data is missing. Numeric differences are against the first selected country, use the same indicator/unit/year, and relative differences are omitted for a zero or missing baseline.
- `GET /health/data/analytics/rankings` accepts one indicator, reporting year, and ascending/descending order. It sorts stored non-null values only; countries without an observation are excluded from the ordered rows.

Request and response models live in `backend/app/schemas/global_analytics.py`; database queries and reproducible calculations live in `backend/app/services/global_analytics_service.py`. Routes validate ISO-3 country count, identifier existence, and year ranges before calling the service.

`frontend/src/components/GlobalAnalytics.tsx` provides the Country Explorer, Trends, Compare, and Rankings views. Recharts is reused for interactive line and bar plots. CSV export includes the actual observed country, indicator, reporting year, value, unit, and source. Trend plots omit unobserved values; they are not interpolated. The country-comparison percentage difference is a relative percent, while the absolute difference for healthcare expenditure (% GDP) is labeled in percentage points.

The map adds native country selection from all ISO-3 countries plus keyboard-accessible zoom controls. The selector makes Singapore and other small/unrenderable map geometries selectable without changing the map projection or shipping another geography asset. Map click, hover, ISO-3 matching, and coloring remain in place.

No analytics table or migration is introduced. Existing experimental health-index and machine-learning workflows remain separate from World Bank measurements.

## Phase 4 predictive analytics and production settings

`frontend/src/App.tsx` uses lazy React Router routes for the existing dashboard and the dedicated `/predictive-analytics` page. The map, analytics workspace, and historical chart are also dynamically imported. The prediction form is separate from the country-profile request, so it remains accessible when profile providers fail.

`POST /health/predict-life-expectancy` continues to use the original serialized Random Forest artifact and five existing features. The request schema now requires finite numeric values, non-negative mortality/GDP/schooling, and positive BMI/population. The UI validates the same constraints, verifies response shapes at runtime, and treats prediction success independently from history-refresh failure. `GET /health/predictions` remains backed by the existing `prediction_history` table.

The saved estimator uses 100 trees and `random_state=42`; the training script uses a random 80/20 split and prints MAE. It does not persist evaluation statistics. The SQLite copy contains 2,938 rows from 2000–2015, but all BMI values are null, so the training split and score cannot be reproduced from this database. The UI does not report unverified MAE, RMSE, or R². The loader now normalizes CSV headers before assigning columns, fixing the whitespace-mismatched BMI header for future imports; no existing rows were rewritten or reloaded.

`backend/app/config.py` validates CORS and prediction-history settings. Development defaults allow local Vite origins and local prediction history; production requires a comma-separated `HEALTHSCOPE_CORS_ORIGINS` list, has no localhost regex, and always disables shared prediction history. `HEALTHSCOPE_PREDICTION_HISTORY_ENABLED=false` can also disable local history; setting it to `true` cannot enable history in production. The anonymous prediction endpoint still returns model results in production but does not save inputs. `GET /health/predictions` returns 404 when history is disabled, including when old rows exist. Existing local history rows are not deleted or returned. Use a production database that does not contain local user-generated history; do not package the local SQLite database as deployment data.

Credentials are disabled and CORS methods/headers are restricted to the application's GET/POST JSON API. CORS does not protect API calls from non-browser clients; prediction-history access is controlled independently by the application policy.

`backend/app/api/error_handlers.py` returns concise 422 validation details without echoing submitted values, including non-finite numeric inputs. Existing external API clients retain their request timeouts. SQLite query plans use the existing indicator/year index for annual rankings; the legacy 2,938-row country history query scans a small table, so no additional index or cache was justified.

The production build splits route and visualization modules. On the audited build, the entry chunk decreased from 641.83 kB (194.98 kB gzip) to 231.19 kB (74.24 kB gzip); the largest deferred chart chunk is 341.95 kB (101.19 kB gzip). This is an entry-chunk comparison, not a claim that every route's total transfer is smaller.

Keyboard access includes the application skip link and route navigation, labeled numeric fields, focus-visible outlines, and the existing keyboard-selectable map plus country selector. Prediction success, history loading, and failures are announced in separate live/alert regions. The prediction page reflows to a single-column form on narrow screens.

## Phase 5B deployment configuration

`backend/app/database/database.py` uses `HEALTHSCOPE_DATABASE_PATH` when configured and retains the repository database path only for development. Production requires an absolute existing path distinct from the local development database file. Before `Base.metadata.create_all`, startup rejects a populated `prediction_history` table. `GET /health` checks SQLite with `SELECT 1`; the app starts with `debug=False`. The trained model is loaded from a path relative to the service module, and application import does not run World Bank ingestion or contact external APIs.

`backend/scripts/create_production_seed.py` opens the selected source read-only, creates an atomic copy, clears prediction/search history and import-operation logs from the copy, and verifies that all other row counts—including the 47,303 WDI/WHO GHO observations—are preserved. It never writes to the source database. The committed `backend/deployment/healthscope.db` output is the seed for an ephemeral instance or first-time initialization of a persistent volume.

The frontend is a static Vite build. `VITE_API_BASE_URL` is mandatory at build time; localhost is used only by the Vite development server. `frontend/vercel.json` implements the Vite SPA fallback for direct route navigation and refresh. The map GeoJSON is served from the bundled `frontend/public/data` asset path; charts and pages remain lazy-loaded. Vercel is compatible with the frontend; Railway is the recommended low-cost backend option because its Hobby plan supports persistent volumes. See the deployment commands and currently checked plan limits in the README.

## Task 1 — pre-expansion product/data architecture audit

Reviewed against the repository and read-only database inspection on 2026-11-18, before Task 2 data expansion. Counts and connector status in this section are the original audit snapshot; implementation status is updated in the Task 2 sections above.

### Current implementation map

- `frontend/src/App.tsx` exposes `/` and `/predictive-analytics`. The global map and Country Explorer/Trends/Compare/Rankings are dashboard sections, not distinct public and professional applications. There is no authentication, role-based authorization, Reference Library, or Sources & Methodology route.
- `backend/main.py` registers `health_profile_routes.py` under `/health` for the older COVID snapshot/profile, custom score, risk, report, and model flows; `health_data_routes.py` under `/health/data` serves the stored WDI and WHO GHO catalogs and queries.
- The WDI path is explicit CLI import (`scripts/ingest_world_bank.py`) → API or local WDI CSV/ZIP parser → SQLAlchemy upsert/import/checkpoint records → typed FastAPI reads → React map/analytics. Task 2 adds the separate WHO GHO path described above; neither source is called during page rendering, and there is no scheduler.
- The legacy country profile is a separate pipeline: disease.sh at profile request time, optional keyed REST Countries metadata, saved country snapshots as fallback. It must not be conflated with WDI annual observations or described as a stable annual global series.
- The two local SQLite files inspected are Git-ignored. Both pass SQLite integrity checks and contain 20,312 WDI observations. The development source contains three prediction-history rows; the separate generated seed contains zero. No patient-identifier model/table was found.

### Data inventory and source boundaries

WDI currently stores 217 country/economy entries and 20,312 country-indicator-year observations for 2000–2024, across life expectancy (5,425 rows/217 entries), population (5,425/217), under-five mortality (4,900/196), and health expenditure share (4,562/193). Fourteen import attempts are logged (10 success, 4 failed). These counts are a snapshot of the local database, not API guarantees. Import is manual; source release calendars vary.

The separate legacy life-expectancy table has 2,938 KaggleHub-loaded rows, 193 countries, 2000–2015; BMI is missing in every row. It lacks per-observation source/version/licensing fields and should not be represented as a direct WHO feed without provenance verification. The model artifact cannot be independently evaluated from this local data.

At Task 1 time, WHO GHO OData was a candidate adapter because it supports indicator/dimension discovery and filtered observations. Task 2 implemented a bounded six-series adapter with country/dimension filtering, explicit metadata, uncertainty fields, duplicate/revision policy, and a separate source code. It intentionally retains a single approved dimension combination per WHO code; expanding to arbitrary dimensions still requires a new observation identity design.

The eight WDI metadata-verified candidates and their caveats are specified in PRD.md: maternal mortality, neonatal mortality, DPT immunization, TB incidence, skilled birth attendance, UHC service coverage, physician density, and nurse/midwife density. The WDI indicator metadata lookups succeeded; observation requests returned HTTP 502 during this audit. Therefore no empirical coverage or update-interval claim is made for those candidates. Gate any addition on a disposable-database coverage/data-quality profile and official source review.

### Target service boundaries (reuse first)

1. **Source catalog and methodology** — extend indicator/source metadata to include publisher, canonical definition/method link, collection/estimate type, source release/vintage, update notes, and reuse terms where supplied. Distinguish the distribution source (WDI) from an underlying publisher (for example WHO/UNICEF).
2. **Ingestion** — retain a normalized database boundary. The existing WDI allowlist/importer remains; the WHO GHO connector is a separate adapter with provider-specific paging, dimension mapping, and provenance validation. Neither is a frontend dependency or runtime page fetch.
3. **Observations and analytics** — continue SQL-filtered, typed read endpoints for country, indicator, year and ranges. Store source years and missingness honestly; only compare equivalent series. A future subgroup-capable schema needs an explicit dimension key and uniqueness strategy before loading multi-sex/age data.
4. **Experience layer** — reuse map, GlobalAnalytics, charting, API client, and predictor. Present audience-specific navigation/labels and staged workspaces, but treat the mode as a workflow/presentation change, not authorization.
5. **Legacy boundary** — preserve route compatibility while quarantining or clearly labeling the disease.sh/COVID-derived index, heuristic “risk,” and recommendations. They are not validated public-health or clinical assessments.

No new package was needed for Task 2. Additive migrations now extend source lineage and reporting-vintage fields. Arbitrary disaggregation or subnational geography still requires an explicit observation-identity migration. Keep import idempotence, failure logging, sanitized production seed generation, and production history policy as release boundaries.

### Target information architecture

Global Overview → Public Health Explorer → Country Profiles for public exploration; Professional Data Explorer → Trends & Comparisons → Reference Library for expert workflow; Sources & Methodology is a cross-cutting destination; Predictive Analytics remains isolated and explicitly experimental. Existing dashboard sections map to the first explorer/profile and analysis views. No professional data gate is implied by these labels.

For rollout order, acceptance gates, audience requirements, proposed indicator inventory, and the risk register, see PRD.md “Task 1 — product and data audit.”
