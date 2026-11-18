# HealthScope AI

A full-stack exploratory healthcare data application built with **FastAPI, SQLAlchemy, SQLite, React, TypeScript, Recharts, and a scikit-learn model**.

This is the user's original HealthScope AI project, repaired in November 2026. The existing SQLite database and trained model are retained. It has not been rebuilt or substituted with a demo app.

## Run on Windows (VS Code)

1. Extract the project; open the `healthscope-ai` folder in VS Code.
2. Double-click `run-backend.bat` or open a terminal and run:

   ```bat
   cd backend
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   python -m uvicorn main:app --reload
   ```

   For a **fresh extraction**, if the virtual environment is not present, first run `py -m venv .venv`. The `.bat` file handles creation/install automatically. Visit **http://127.0.0.1:8000/docs**.

3. Double-click `run-frontend.bat` or open a **second** terminal:

   ```bat
   cd frontend
   npm install
   npm run dev
   ```

   Open the URL printed by Vite, normally **http://localhost:5173** (or `5174` if 5173 is occupied).

**If you are merging these files into an existing checkout**, you can keep your existing `.venv`, `node_modules`, and `.git`; don't overwrite or delete them. The provided ZIP intentionally omits those environment-specific and large generated directories.

## What works

- Country health profile search (`GET /health/profile/{country}`), including saved snapshot fallback when the disease.sh provider is unavailable.
- Country rankings (one latest snapshot per country), saved-snapshot trends, country reports and risk flags.
- Stored World Bank WDI and WHO Global Health Observatory indicators, country-year coverage reporting, historical WHO-labelled life-expectancy dataset and comparison routes.
- Existing scikit-learn life-expectancy prediction and prediction history.
- React dashboard with loading, error and source-status messages; it loads Philippines on startup.

The deployment seed currently contains 47,303 country-indicator observations (20,312 WDI and 26,991 WHO GHO), 221 country references, 10 indicators, 38 country snapshots, 2,938 legacy WHO-labelled life-expectancy rows, and the original model. The legacy WHO-labelled table is distinct from the direct GHO observations; it covers 2000–2015, has 2,928 stored target values, and has no BMI values. **The snapshots were recorded in June 2026.** These are historical observations, not live 2026 public-health figures. The disease.sh response also reflects its provider's reporting period and must not be presented as today's COVID situation.

### Data sources / optional key

- `disease.sh/v3/covid-19/countries/{country}`: reported COVID-19 totals and country population. The route has timeouts and checks the HTTP response.
- REST Countries **v5**: optional country metadata (canonical country, population, region, capital). The earlier unauthenticated `/v3.1/name/` endpoint is retired. V5 requires a **real API key**. See https://restcountries.com/docs/countries.

To enable optional v5 metadata, copy `backend/.env.example` to `backend/.env` and set `REST_COUNTRIES_API_KEY=YOUR_KEY`. Never commit `.env` to GitHub. The sample `rc_live_demo` key does not return country-specific production data and is intentionally ignored.

**No key required to run the app for the countries in the saved database.** For countries without snapshots, an accessible disease.sh response is required; otherwise the API returns a descriptive `503` rather than inventing health data.

### API errors

- HTTP 200: returned live-retrieved provider data or an archived saved snapshot. Check `data_source`, `data_status`, and `data_as_of` for its provenance.
- HTTP 503: no matching archived snapshot and live COVID provider unavailable.
- HTTP 500: unexpected application failure (server terminal logs an exception).

### Health index methodology

The "health index" is a **custom exploratory metric**, not a validated public-health or clinical risk score. It is derived from reported COVID recovery and mortality ratios and a tests-per-population proxy, with the last input capped at 100. The overall score is bounded to 0–100. **Tests-per-population is not the percentage of distinct people tested.** Stored historical snapshot rows retain original values; scores in updated profile, ranking, trend and report API responses are recalculated using the bounded formula.

The dashboard's "Rule-Based Insights" and risk recommendations are illustrative threshold rules, not advice or AI-generated medical conclusions.

## Tests

From `backend/`:

```bat
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests mock external APIs and use temporary in-memory SQLite databases to avoid changing saved records. Backend coverage includes validation, pagination, missing observations, ISO-3 normalization, idempotent persistence, error history, deployment seeding, and API responses. The frontend interaction test covers indicator switching, reporting-year filtering, map country selection, and missing-data labeling. Run both suites with the commands above; run the frontend lint and production build with `npm run lint` and `npm run build`.

From `frontend/`, run `npm run test` and `npm run lint`. Production builds require the API URL; in PowerShell, set `$env:VITE_API_BASE_URL = "https://api.example.test"` before `npm run build`. The build checks that the variable is present, then validates TypeScript and creates the production bundle.

## Key endpoints

`GET /health` · `GET /health/profile/{country}` · `GET /health/history/{country}` · `GET /health/rankings` · `GET /health/trends/{country}` · `GET /health/country-report/{country}` · `GET /health/risk-assessment/{country}` · `GET /health/life-expectancy/{country}` · `POST /health/predict-life-expectancy` · `GET /health/predictions` (local development only).

## Phase 2: Global health indicator ingestion

The dashboard's **Global health indicators** panel reads validated observations stored in SQLite. It supports the four WDI indicators and six separately identified WHO GHO indicators, filtering by available reporting year, hovering for country values, and selecting a country profile. Countries with no value for the chosen year are shown as **No data**, not zero. Provider, publisher, reporting year, indicator metadata, and source references are exposed; observations are historical, not live.

The integration uses the unauthenticated [World Bank Indicators API v2](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation) and the [World Development Indicators](https://databank.worldbank.org/source/world-development-indicators). Indicator definitions and upstream providers are available from the API metadata:

- `SP.DYN.LE00.IN` — life expectancy at birth, years.
- `SP.POP.TOTL` — de facto midyear population, people.
- `SH.DYN.MORT` — under-five mortality, deaths per 1,000 live births.
- `SH.XPD.CHEX.GD.ZS` — current health expenditure as a percentage of GDP (excludes capital expenditure).

The application startup adds the normalized `health_countries`, `health_data_sources`, `health_indicators`, `health_indicator_observations`, import, and observation-revision tables. Its explicit SQLite migration adds nullable provenance columns to existing health-data tables without rebuilding them. Observation rows are unique by country ISO-3 code, indicator code, and year. Changed values or provenance are recorded in `health_indicator_observation_revisions` before upsert; unchanged re-imports do not create revision rows. Missing source values are omitted and never converted to zero.

### Import or refresh

Run from `backend/` with the project Python environment:

```bat
python -m scripts.ingest_world_bank
```

This imports all configured indicators from 1960 through the current year. Repeat the command to refresh; it does not add duplicate observation rows. Options:

```bat
python -m scripts.ingest_world_bank --start-year 2000 --end-year 2024
python -m scripts.ingest_world_bank --indicator SP.DYN.LE00.IN
```

API imports are processed in sequential five-year batches and pages of 500 observations. Each completed page is committed and recorded in `health_data_import_checkpoints`; reruns resume by skipping completed pages. Use `--no-resume` to deliberately refresh completed pages. Timeout, retry count, page size, and year-batch size are configurable with `--connect-timeout`, `--read-timeout`, `--retries`, `--per-page`, and `--batch-years`. Retries use bounded exponential backoff with jitter. The command logs response status, elapsed time, pagination metadata, and errors; it exits non-zero if an indicator import fails. Each attempt is recorded in `health_data_imports`. The frontend does not trigger an ingestion or request the provider directly.

If API requests are unavailable or time out, download the official WDI CSV/ZIP archive from the [World Bank WDI DataBank](https://databank.worldbank.org/source/world-development-indicators), or export selected countries, indicators, and years there as CSV. Extract nothing; pass the downloaded ZIP or CSV path to the same importer:

```bat
python -m scripts.ingest_world_bank --csv C:\data\WDI_csv.zip --start-year 2000 --end-year 2024
python -m scripts.ingest_world_bank --csv C:\data\WDI_csv.zip --country PHL --indicator SP.POP.TOTL --start-year 2022 --end-year 2024
```

The CSV path streams ZIP members row by row, validates WDI and DataBank export headers (including `Series Code` and year columns such as `2024 [YR2024]`), imports country metadata where included, skips aggregate regions, and uses the same ISO-3 validation and idempotent database upserts as the API path. No CSV data is bundled with the application; production values must come from an official World Bank download.

### Data API

- `GET /health/data/countries`
- `GET /health/data/indicators`
- `GET /health/data/indicators/{indicator_code}/years`
- `GET /health/data/indicators/{indicator_code}/observations?year={year}` (latest stored year when omitted)
- `GET /health/data/countries/{iso3}/observations?year={year}`
- `GET /health/data/countries/{iso3}/indicators/{indicator_code}/history`
- `GET /health/data/coverage?indicator_code={code}&country_iso3={ISO3}`

Responses include the source and reporting-year metadata for observations. API details and additive tables are described in [ARCHITECTURE.md](./ARCHITECTURE.md), [DESIGN.md](./DESIGN.md), [PRD.md](./PRD.md), [RULES.md](./RULES.md), and [SCHEMA.md](./SCHEMA.md).

### WHO GHO additions and coverage

The bounded importer `python -m scripts.ingest_who_gho` adds only the six approved WHO Global Health Observatory OData series below. It retains the existing four WDI series as separate indicator codes and sources; similarly named or methodologically different series are not merged. The `dptv` metadata entry returned no observations during validation, so the imported immunization series is the populated WUENIC code `WHS4_100`.

| WHO GHO code | Measure and unit | WHO GHO observations | Countries | Stored year span |
|---|---|---:|---:|---|
| `MDG_0000000026` | Maternal mortality ratio, deaths per 100,000 live births | 4,680 | 195 | 2000–2023 |
| `WHOSIS_000003` | Neonatal mortality rate, deaths per 1,000 live births | 5,000 | 200 | 2000–2024 |
| `WHS4_100` | DTP3 immunization coverage among 1-year-olds, percent (WUENIC) | 5,051 | 195 | 2000–2025 |
| `MDG_0000000020` | Tuberculosis incidence, cases per 100,000 population per year | 5,013 | 196 | 2000–2025 |
| `MDG_0000000025` | Births attended by skilled health personnel, percent of births | 2,567 | 193 | 2000–2024 |
| `UHC_INDEX_REPORTED` | UHC Service Coverage Index (SDG 3.8.1), index 0–100 | 4,680 | 195 | 2000–2023 |

These are counts from the staged import completed 2026-11-18, not a guarantee of current or complete coverage. In particular, skilled-birth-attendance reports are irregular (Philippines has seven observations in 2000–2022, while Singapore has observations through 2024); an absent row means only that the provider returned no observation. The generated [country/indicator/year coverage CSV](./backend/reports/health_data_coverage.csv) lists observed years and gaps within each observed span without assuming every indicator is expected annually or inventing a coverage percentage.

The WHO adapter filters to country records and validates each approved code, canonical unit, ISO-3, reporting-year range, dimensions, finite numeric value, and uncertainty bounds. The neonatal series is intentionally restricted to both sexes and 0–27 days, retained in the observation dimensions; it does not combine arbitrary sex/age strata. Maternal and neonatal mortality and TB incidence are estimates; DTP3 is a WHO/UNICEF WUENIC estimate; skilled birth-attendance source methods vary by country/year; and UHC is a composite index, not a percentage of individuals covered. The indicators are descriptive population-level measures, not clinical advice or patient-specific data.

The GHO observation API's `Date` is stored as a **provider record timestamp**, not treated as an observation or publication date. Reporting year is stored separately; `imported_at` records the local import time. The API did not provide a publication date or version for these observations, so `source_publication_date` and `dataset_version` remain null. Denominator definitions, source comments/references, provider display values, uncertainty bounds, and available dimensions are retained. The API does not provide numeric denominator values for these imported series, so that field remains null.

Run an offline/build-time import only; normal API/dashboard requests never contact WHO:

```bat
python -m scripts.ingest_who_gho --start-year 2000 --end-year 2026
python -m scripts.ingest_who_gho --indicator WHOSIS_000003
python -m scripts.report_health_data_coverage --output reports\health_data_coverage.csv
```

The importer follows WHO OData offset paging (the service does not always return a continuation URL), uses bounded HTTP retries, and records received/inserted/updated/missing/rejected/duplicate counts. Unknown ISO-3 codes are resolved through the WHO `RegionCountry` metadata endpoint; source rows without valid country metadata are rejected. Revisions preserve the previous value and provenance before an upsert. `GET /health/data/coverage` exposes the same country/indicator observed-year summary through FastAPI; the standard indicator, history, trends, comparisons, and rankings endpoints expose WHO rows using their separate codes.

No automated refresh schedule is configured. WDI and WHO series have different provider release cadences and latest years; imports are explicit and data-specific. GHO currently supplies no release/version field for these rows. WHO data reuse/attribution terms were not conclusively resolved by the API documentation, so license/redistribution review remains required before public production release. The app does not claim clinical validation or expert review of professional reference content.

The map geometry is Natural Earth 1:110m Admin 0 boundaries (https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/); it is bundled separately from health measurements. Boundary coverage and disputed/dependent territories may not align exactly with WDI/WHO country metadata. No observation should be interpreted as a live measurement or clinical advice.

## Phase 3: Country analytics

The **Country analytics** workspace adds Country Explorer, Trends, Compare, and Rankings views while retaining the existing map, saved-data dashboard, and ML predictor. The explorer searches by country name or ISO-3, shows available region metadata, and displays the latest stored observation for each WDI or WHO GHO indicator independently. Every value includes its actual reporting year, unit, and provider; a missing value is shown as “No data,” never substituted from another year.

Trends overlays up to five countries, filters an inclusive year range, shows actual year-by-year rows, reports observed-endpoint absolute/relative changes, and exports those observations as CSV. Compare accepts two to five countries, uses one indicator and year, shows missing values and differences from the first selected country, and overlays historical trends. Ranking filters by indicator/year and sort order, supports country search, and excludes missing observations. These are numeric indicator rankings, not an overall “healthiest country” score. In particular, population is not health quality, and expenditure share is not a performance score. Healthcare expenditure absolute differences are percentage points; relative changes are percentages.

The analytics API reads the existing SQLite observations using country/indicator/year filters:

- `GET /health/data/analytics/trends?indicator_code=SP.DYN.LE00.IN&countries=PHL&countries=SGP&start_year=2000&end_year=2024`
- `GET /health/data/analytics/compare?indicator_code=SP.DYN.LE00.IN&year=2022&countries=PHL&countries=SGP`
- `GET /health/data/analytics/rankings?indicator_code=SP.DYN.LE00.IN&year=2022&order=descending`

Trends allow 1–5 ISO-3 country codes; comparisons require 2–5. Data gaps remain gaps; no interpolation is performed. Changes require two distinct observed years; relative change is unavailable when the baseline is zero. The map keeps its choropleth and hover behavior and adds a searchable native country list and zoom/reset controls, making Singapore accessible despite its small geometry. No schema migration or new dependency is required.

Test/validation commands:

```bat
cd backend
python -m pytest -q
cd ..\frontend
npm test
npm run lint
npm run build
```

## Phase 4: Predictive analytics and hardening

The **Predictive analytics** route is available from the dashboard navigation and can be opened directly at `/predictive-analytics`. It uses the retained `RandomForestRegressor` (100 trees, `random_state=42`) with the five original features: adult-mortality probability per 1,000 population between ages 15 and 60, average BMI (kg/m²), GDP per capita (US dollars), schooling (years), and population (people). Inputs must be finite and non-negative; BMI and population must be positive. The result is an experimental historical estimate, not a future-year or individual clinical forecast.

The training script prints a holdout MAE but the saved artifact contains no evaluation report. The source training file is not bundled, and the retained database has no BMI values, so MAE, RMSE, and R² cannot be reproduced from the checked-in data. The UI intentionally shows no performance score. Anonymous predictions remain available in all environments. Prediction history is enabled by default for local development; set `HEALTHSCOPE_PREDICTION_HISTORY_ENABLED=false` to disable it. Production always disables history reads and does not save anonymous prediction inputs, even if the history setting is `true`. Existing local history rows are not deleted, but must not be included in production database data.

Frontend route modules and visualization components load on demand. The production entry JavaScript decreased from 641.83 kB (194.98 kB gzip) to 231.19 kB (74.24 kB gzip); the largest deferred chart chunk is 341.95 kB (101.19 kB gzip). No dependencies were added. These numbers measure generated JavaScript chunks, not a guarantee of total transfer size for every route.

For production, configure the API before starting it:

```powershell
$env:HEALTHSCOPE_ENV = "production"
$env:HEALTHSCOPE_CORS_ORIGINS = "https://healthscope.example"
$env:HEALTHSCOPE_PREDICTION_HISTORY_ENABLED = "false"
$env:HEALTHSCOPE_DATABASE_PATH = "/var/data/healthscope.db"
```

Production startup requires explicit trusted HTTP(S) origins and an absolute initialized database path distinct from the local development database. It refuses to start if the configured database contains prediction-history rows. It does not enable the development localhost-origin regex. Production forces prediction history off regardless of its setting. CORS is a browser access policy, not authentication.

The root `backend/.env.example` contains local defaults and commented production settings. `frontend/.env.example` documents `VITE_API_BASE_URL`; Vite embeds this value into the public frontend bundle, so it is configuration, not a secret. Do not put credentials in any `VITE_` variable.

### Public SQLite seed

`backend/healthscope.db` is the ignored local development database and is never required for deployment. The packaged `backend/deployment/healthscope.db` is the sanitized production seed (16.0 MB at the Task 2 import). It preserves 47,303 WDI/WHO GHO observations across 10 indicators, 221 country references, 2,938 legacy WHO-labelled life-expectancy rows, and 38 country snapshots. It contains no prediction history, nutrition searches, or import-operation logs.

To regenerate the seed locally from the local database, run from `backend/`:

```sh
python -m scripts.create_production_seed --source healthscope.db --output deployment/healthscope.db
```

For a data refresh, first work on a SQLite backup/staging copy rather than importing into a production database. After the WHO import and coverage report, build the seed from that staged file:

```powershell
New-Item -ItemType Directory -Force staging | Out-Null
python -c "import sqlite3; source=sqlite3.connect('file:healthscope.db?mode=ro', uri=True); target=sqlite3.connect(r'staging\healthscope-task2.db'); source.backup(target); target.close(); source.close()"
$env:HEALTHSCOPE_DATABASE_PATH = (Resolve-Path .\staging\healthscope-task2.db).Path
python -m scripts.ingest_who_gho --start-year 2000 --end-year 2026
python -m scripts.report_health_data_coverage --output reports\health_data_coverage.csv
python -m scripts.create_production_seed --source $env:HEALTHSCOPE_DATABASE_PATH --output deployment\healthscope.db
```

The builder opens the chosen source read-only, writes atomically to the separate output, verifies SQLite integrity and row counts, and does not change the source database. The seed contains aggregate reference observations only; its builder removes prediction history, nutrition searches, and import-operation logs. The committed SQLite seed is required by the configured Render start command. Cloud build and startup do not run the builder or contact live external APIs.

Production startup requires `HEALTHSCOPE_DATABASE_PATH` to be an absolute writable path distinct from the local database. The configured database is initialized by copying the packaged seed before starting the application. Runtime prediction history is disabled in production, and startup fails closed if any prediction-history records are present. On ephemeral storage, copying the seed at each service start restores the reference observations; other runtime SQLite changes are intentionally not persistent.

### Hosting preparation (not deployed)

- **Frontend — Vercel:** Set the project root to `frontend`, build with `npm run build`, and use `dist` as the output directory. Set `VITE_API_BASE_URL` to the HTTPS FastAPI origin in the Vercel Production environment (and a separate API origin for previews if used). [`frontend/vercel.json`](./frontend/vercel.json) provides the documented SPA rewrite so `/predictive-analytics` and refreshes serve `index.html`. The Vercel Hobby plan is currently listed at $0/month for personal projects, subject to its quotas and terms ([pricing](https://vercel.com/pricing), [Vite SPA routing](https://vercel.com/docs/frameworks/frontend/vite)).
- **Backend — Railway:** Railway currently offers a Hobby plan at $5/month with $5 of included usage, then resource-based billing. Hobby volumes support up to 5 GB; volume storage is metered separately. Use one service replica with SQLite on the mounted volume. The Free plan has only $1/month of included usage and a 0.5 GB volume limit, so it is suitable for experiments, not dependable public availability ([pricing](https://railway.com/pricing), [volume limits](https://docs.railway.com/reference/volumes), [Python version selection](https://railpack.com/languages/python)).
- **Backend — Render Free:** [`render.yaml`](./render.yaml) configures the backend root, pinned Python version, free web service, `/health` check, seed initialization, and binding to the provider's `PORT`. Set `HEALTHSCOPE_CORS_ORIGINS` to the exact HTTPS frontend origin when creating the service. The service uses `/tmp/healthscope.db` (ephemeral); startup recopies the packaged seed, predictions remain anonymous, and database changes do not persist. Render Free services spin down after 15 minutes idle and cannot attach persistent disks, so expect cold starts and do not use this option when durable writes or continuous availability are required ([limitations](https://render.com/docs/free), [persistent disks](https://render.com/docs/disks)).
- **Railway backend:** Set the root directory to `backend`; build with `pip install -r requirements.txt`. Set `HEALTHSCOPE_DATABASE_PATH=/data/healthscope.db`, attach a volume at `/data`, and set the start command to `cp deployment/healthscope.db "$HEALTHSCOPE_DATABASE_PATH" && exec uvicorn main:app --host 0.0.0.0 --port "$PORT"`. Configure the production environment variables above. `backend/.python-version` pins the tested Python runtime.

Hosting prices and plan limits can change. No hosting resources have been created and no deployment has been performed.

The FastAPI process binds to `0.0.0.0` and the provider's `PORT`. `GET /health` runs a lightweight SQLite `SELECT 1` for platform health checks. Production startup does not fetch World Bank data; it serves the initialized local seed. The retained model loads by a path relative to `backend/app/services/ml_service.py`. Production `debug` is explicitly off, so unhandled errors return generic server responses rather than tracebacks. Python production dependencies are exact pins in `backend/requirements.txt`, and `backend/.python-version` selects the tested Python version.

Prediction requests reject invalid numeric values with a sanitized 422 response that omits submitted values. The prediction page has programmatically labeled inputs, loading/error/success states, keyboard focus styling, a skip link, and mobile layouts. No database schema change or dependency was needed.

## Project layout

- `backend/app/api`: FastAPI routes.
- `backend/app/services`: WDI and WHO GHO ingestion, coverage, provenance/revision upserts, health profile aggregation, analytics, comparisons, predictions, rankings, snapshots.
- `backend/healthscope.db`: local development SQLite data; ignored by Git.
- `backend/deployment/healthscope.db`: committed sanitized production seed.
- `backend/scripts/create_production_seed.py`: creates a sanitized, separate deployment database.
- `backend/scripts/ingest_who_gho.py`: imports the six allowlisted WHO GHO series.
- `backend/scripts/report_health_data_coverage.py`: writes the country/indicator reporting-year inventory.
- `backend/reports/health_data_coverage.csv`: generated Task 2 coverage report.
- `backend/saved_models`: original trained scikit-learn model.
- `frontend/src`: React routes, dashboard, predictive analytics, API client, types and charts.
- `docs/`: existing project planning and development documentation.
- `FIXES.md`: changes made in this repair.
