# HealthScope AI Data and Engineering Rules

## Data integrity

- Use World Bank Indicators API v2 or official downloaded WDI CSV/ZIP files as the source for Phase 2 observations; do not generate or substitute production measurements.
- Require a valid three-letter ISO-3 country code and a four-digit reporting year.
- Store finite, non-negative numeric values only. Keep null source values absent and expose missingness as “No data”.
- Keep indicator code, unit, source, reporting year, and import timestamp with every observation.
- Enforce one observation per country, indicator, and year. Refresh using upsert, not append-only duplicates.
- Exclude World Bank aggregate regions from country-level records.
- Preserve existing SQLite rows and tables. Schema changes must be additive unless an explicitly reviewed migration is supplied.
- Log provider, parsing, and persistence failures and retain import status. Do not silently report successful ingestion after a failed request.
- Stream downloaded archives and validate their headers and reporting-year columns before importing; accept both standard WDI and filtered DataBank export headers. Local fallback must use the same validation, country normalization, source attribution, and unique-key upserts as API ingestion.
- Keep API ingestion sequential and bounded. Persist a checkpoint only in the same commit as its observation page, and resume only pages recorded as complete.

## API and presentation

- Dashboard components read indicator observations from the backend; do not make provider API calls during page rendering.
- Validate API response shapes and use explicit HTTP errors for unknown countries or indicators.
- Never label annual or historical observations as live.
- Do not compare indicators with different reporting years without showing their individual years.
- Keep Phase 1 routes and ML behavior compatible.

## Phase 3 analytics

- Filter analytics queries in SQL by country, indicator, and year/range. Do not transfer the global observation table to the browser.
- Preserve the selected country even when a map boundary is too small to click; provide an accessible ISO-3 selector.
- For a country profile, use the latest stored row for each indicator independently and print that row's reporting year. Never substitute the requested or latest global year when that country/indicator lacks an observation.
- Return missing comparison observations as null and render them as “No data.” Exclude missing rows from rankings.
- Calculate absolute change as last observed value minus first observed value within the selected inclusive range. Require two distinct observed years. Calculate relative percentage change only when the first value is nonzero.
- Compare only one indicator definition, unit, and reporting year at a time. Label differences for `% of GDP` measurements as percentage points; do not confuse this with relative percent change.
- A sorted indicator ranking is not a composite health or performance assessment. State the measurement unit and source and avoid a universal “healthiest” interpretation.
- Keep UI/API errors visible, chart gaps honest, and CSV rows limited to the observations actually displayed.

## Phase 4 model, security, and performance

- Preserve the existing saved life-expectancy estimator and its exact five-feature order: adult mortality, BMI, GDP, schooling, and population.
- Require finite values; adult mortality, GDP, and schooling must be non-negative, and BMI and population must be positive. Apply validation in both the Pydantic request model and frontend form.
- Never publish MAE, RMSE, R², or other model metrics unless they are reproducible against the actual saved estimator and matching holdout data. No BMI values exist in the retained WHO table, so evaluation cannot be reconstructed from that table.
- Describe the output as an experimental historical population-level estimate, not clinical advice, causation, or a validated individual forecast.
- Do not echo submitted values in validation error responses or silently convert prediction/history failures into success.
- Configure production CORS through explicit trusted HTTP(S) origins. Development localhost patterns must not be enabled in production. CORS is not authentication.
- Prediction history is shared by the unauthenticated API. Do not collect identifying information; require user authentication or disable shared history before public deployment.
- Use route-level and visualization lazy loading based on measured build output; do not increase the warning threshold to hide large chunks.
- Add indexes, caching, or infrastructure only when query or runtime measurements justify them. Keep existing SQLite rows unchanged unless an explicit data migration is reviewed.
- Normalize source CSV headers before loading features so whitespace differences do not silently remove model inputs. Do not rerun an append-only legacy loader against the existing database without a separately planned deduplication/reconciliation.
- Keep environment files and credentials ignored by Git; do not commit local databases, model inputs, or secrets unintentionally.
