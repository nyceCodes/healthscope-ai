# HealthScope AI Architecture

## Phase 2 data path

The existing FastAPI services and React dashboard remain in place. Global indicator data is loaded only by the explicit backend ingestion command:

1. `backend/app/services/world_bank_service.py` supports both World Bank Indicators API v2 requests and local official WDI CSV/ZIP archives or filtered DataBank exports. The API client requests country metadata, indicator definitions, and paginated observations; the CSV reader streams archive rows, normalizes DataBank `Series Code` and `[YRyyyy]` headers, and validates requested year columns.
2. The API importer makes sequential five-year requests using 500-row pages by default, with bounded exponential retries and jitter. It logs HTTP status, elapsed time, pagination metadata, and exceptions. The ingestion service validates response structure, ISO-3 identifiers, years, and finite non-negative numeric values. Null observations are counted and omitted.
3. SQLAlchemy upserts country, indicator, source, and observation rows into the existing SQLite database. A unique country/indicator/year key makes refreshes repeatable.
4. Every successfully stored API page is committed with an additive checkpoint row; the CLI resumes by skipping completed pages, and re-imports remain idempotent.
5. `backend/app/api/health_data_routes.py` returns stored observations and provenance through typed FastAPI/Pydantic endpoints. Dashboard requests do not call the World Bank.
6. React displays those API observations on the Natural Earth country-boundary map. The geometry is a static frontend asset; metric values always come from the backend API.

## Database and migration strategy

`Base.metadata.create_all()` creates only the new Phase 2 tables when the application starts; it does not drop or rewrite existing Phase 1 tables. The current SQLite database path and existing snapshots, WHO life-expectancy rows, and ML model are retained. The change is additive, so no table-copy migration is required.

## Components

- `backend/app/models/health_indicator.py`: normalized global health-data tables.
- `backend/app/services/world_bank_service.py`: API client, five-year/page batching, validation, normalization, upserts, checkpointing, and import history.
- `backend/scripts/ingest_world_bank.py`: initial and repeatable API or local CSV/ZIP import CLI.
- `backend/app/api/health_data_routes.py`: read-only stored-data endpoints.
- `frontend/src/components/WorldIndicatorMap.tsx`: accessible SVG choropleth, hover details, and legend.
- `frontend/src/pages/Dashboard.tsx`: indicator/year selection and country observations.

## Sources

- World Bank Indicators API v2: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
- World Development Indicators bulk archive: https://databank.worldbank.org/source/world-development-indicators
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

`backend/app/database/database.py` uses `HEALTHSCOPE_DATABASE_PATH` when configured and retains the repository database path only for development. Production requires an absolute existing path distinct from the tracked local database. Before `Base.metadata.create_all`, startup rejects a populated `prediction_history` table. `GET /health` checks SQLite with `SELECT 1`; the app starts with `debug=False`. The trained model is loaded from a path relative to the service module, and application import does not run World Bank ingestion or contact external APIs.

`backend/scripts/create_production_seed.py` opens the local database read-only, creates an atomic copy, clears local prediction/search history and import-operation logs from the copy, and verifies that all other row counts—including the 20,312 World Bank observations—are preserved. It never writes to the original database. The ignored `backend/deployment/healthscope.db` output is the seed for an ephemeral instance or first-time initialization of a persistent volume.

The frontend is a static Vite build. `VITE_API_BASE_URL` is mandatory at build time; localhost is used only by the Vite development server. `frontend/vercel.json` implements the Vite SPA fallback for direct route navigation and refresh. The map GeoJSON is served from the bundled `frontend/public/data` asset path; charts and pages remain lazy-loaded. Vercel is compatible with the frontend; Railway is the recommended low-cost backend option because its Hobby plan supports persistent volumes. See the deployment commands and currently checked plan limits in the README.
