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
- Historical WHO life expectancy dataset and comparison routes.
- Existing scikit-learn life-expectancy prediction and prediction history.
- React dashboard with loading, error and source-status messages; it loads Philippines on startup.

The saved database currently contains 38 country snapshots, 2,938 WHO life-expectancy rows, and the original model. The WHO rows cover 2000–2015; 2,928 have a stored target value, while BMI is missing for every stored row. **The snapshots were recorded in June 2026.** These are historical observations, not live 2026 public-health figures. The disease.sh response also reflects its provider's reporting period and must not be presented as today's COVID situation.

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

Tests mock external APIs and use temporary in-memory SQLite databases to avoid changing saved records. Backend coverage includes validation, pagination, missing observations, ISO-3 normalization, idempotent persistence, error history, and API responses. The frontend interaction test covers indicator switching, reporting-year filtering, map country selection, and missing-data labeling. Run both suites with the commands above; run the frontend lint and production build with `npm run lint` and `npm run build`.

From `frontend/`, run `npm run test`, `npm run lint`, and `npm run build` to validate the map interactions, lint rules, TypeScript, and production bundle.

## Key endpoints

`GET /health/profile/{country}` · `GET /health/history/{country}` · `GET /health/rankings` · `GET /health/trends/{country}` · `GET /health/country-report/{country}` · `GET /health/risk-assessment/{country}` · `GET /health/life-expectancy/{country}` · `POST /health/predict-life-expectancy` · `GET /health/predictions`.

## Phase 2: World Bank health indicators

The dashboard's **Global health indicators** panel reads validated annual observations stored in SQLite. It supports switching between life expectancy, population, under-five mortality, and current health expenditure (% GDP), filtering by available reporting year, hovering for country values, and selecting a country profile. Countries with no value for the chosen year are shown as **No data**, not zero. Sources and reporting years are displayed, and World Bank annual observations are identified as historical, not live.

The integration uses the unauthenticated [World Bank Indicators API v2](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation) and the [World Development Indicators](https://databank.worldbank.org/source/world-development-indicators). Indicator definitions and upstream providers are available from the API metadata:

- `SP.DYN.LE00.IN` — life expectancy at birth, years.
- `SP.POP.TOTL` — de facto midyear population, people.
- `SH.DYN.MORT` — under-five mortality, deaths per 1,000 live births.
- `SH.XPD.CHEX.GD.ZS` — current health expenditure as a percentage of GDP (excludes capital expenditure).

The application startup adds the new normalized `health_countries`, `health_data_sources`, `health_indicators`, `health_indicator_observations`, and `health_data_imports` tables without deleting or rewriting any Phase 1 data. Observation rows are unique by country ISO-3 code, indicator code, and year. Re-imports update existing rows; missing source values are omitted and never converted to zero.

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

Responses include the source and reporting-year metadata for observations. API details and additive tables are described in [ARCHITECTURE.md](./ARCHITECTURE.md), [DESIGN.md](./DESIGN.md), [PRD.md](./PRD.md), [RULES.md](./RULES.md), and [SCHEMA.md](./SCHEMA.md).

The map geometry is Natural Earth 1:110m Admin 0 boundaries (https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/); it is bundled separately from health measurements. Boundary coverage and disputed/dependent territories may not align exactly with World Bank country metadata. World Bank updates are annual and latest reporting years vary by series and country; no observation should be interpreted as a live measurement or clinical advice.

## Phase 3: Country analytics

The **Country analytics** workspace adds Country Explorer, Trends, Compare, and Rankings views while retaining the existing map, saved-data dashboard, and ML predictor. The explorer searches by country name or ISO-3, shows available region metadata, and displays the latest stored observation for each of the four WDI indicators independently. Every value includes its actual reporting year, unit, and World Bank source; a missing value is shown as “No data,” never substituted from another year.

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

The training script prints a holdout MAE but the saved artifact contains no evaluation report. The source training file is not bundled, and the retained database has no BMI values, so MAE, RMSE, and R² cannot be reproduced from the checked-in data. The UI intentionally shows no performance score. Prediction history is stored in the shared SQLite database and is not user-authenticated; do not enter identifying information, and add authentication or disable shared history before exposing the API to public users.

Frontend route modules and visualization components load on demand. The production entry JavaScript decreased from 641.83 kB (194.98 kB gzip) to 231.19 kB (74.24 kB gzip); the largest deferred chart chunk is 341.95 kB (101.19 kB gzip). No dependencies were added. These numbers measure generated JavaScript chunks, not a guarantee of total transfer size for every route.

For production, configure the API before starting it:

```powershell
$env:HEALTHSCOPE_ENV = "production"
$env:HEALTHSCOPE_CORS_ORIGINS = "https://healthscope.example"
```

Production startup requires explicit trusted HTTP(S) origins and does not enable the development localhost-port regex. Set `VITE_API_BASE_URL` when building the frontend for a non-local API. CORS is a browser access policy, not authentication. The repository has no tracked `.env` files; keep real keys in ignored local environment files. The npm production dependency audit reported no advisories at the time of this Phase 4 check; a Python vulnerability scanner is not installed in the current environment.

Prediction requests reject invalid numeric values with a sanitized 422 response that omits submitted values. The prediction page has programmatically labeled inputs, loading/error/success states, keyboard focus styling, a skip link, and mobile layouts. No database schema change or dependency was needed.

## Project layout

- `backend/app/api`: FastAPI routes.
- `backend/app/services`: health profile aggregation, analytics, comparisons, predictions, rankings, snapshots.
- `backend/healthscope.db`: original SQLite data.
- `backend/saved_models`: original trained scikit-learn model.
- `frontend/src`: React routes, dashboard, predictive analytics, API client, types and charts.
- `docs/`: existing project planning and development documentation.
- `FIXES.md`: changes made in this repair.
