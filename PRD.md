# HealthScope AI Product Requirements

## Phase 2: Global health data

### Goal

Let users explore and compare validated country health measurements from the World Bank through the existing interactive React dashboard and FastAPI/SQLite application.

### Included indicators

| Code | Indicator | Unit | Definition |
|---|---|---|---|
| `SP.DYN.LE00.IN` | Life expectancy at birth, total | years | Expected years lived by a newborn if prevailing mortality patterns continue. |
| `SP.POP.TOTL` | Population, total | people | De facto midyear population estimate. |
| `SH.DYN.MORT` | Under-five mortality rate | deaths per 1,000 live births | Probability per 1,000 that a newborn dies before age five under the year's age-specific mortality rates. |
| `SH.XPD.CHEX.GD.ZS` | Current health expenditure | % of GDP | Current health consumption expenditure relative to GDP; excludes capital expenditure. |

Definitions follow World Bank indicator metadata. Series are provided through the World Development Indicators API; their underlying providers differ by indicator.

### Requirements

- Import data only through the backend, using the World Bank API or an official downloaded WDI CSV/ZIP archive; the frontend reads from SQLite-backed API routes.
- Select an indicator and a year with stored observations.
- Show per-country values, units, reporting year, and source.
- Make missing observations visible without substituting zero.
- Preserve the existing Phase 1 database tables and model prediction workflow.
- Make imports repeatable, log failures, and retain import metadata.
- Support streamed local archive imports when API calls time out, without fabricating or substituting values.
- Split API refreshes into configurable year batches and pages, with bounded retries and resumable page checkpoints.

## Limitations

World Bank series are annual and updated on the provider's publication schedule. Latest years vary by indicator and country. A blank World Bank observation is missing, not zero. The low-resolution Natural Earth map may not represent every disputed boundary or dependent territory as a separately selectable country. Indicator values are not clinical advice.

## Phase 3: Advanced global health analytics

### Country Explorer

- Search stored countries by name or ISO-3 and display country name, code, and region where available.
- Show life expectancy, population, under-five mortality, and current health expenditure using the latest stored observation for each indicator independently.
- Display each value's actual year, unit, and source, historical trend, and change between available observations.
- Represent absent measurements as “No data”; never substitute an earlier year or interpolate.

### Trends and comparison

- Overlay one to five country time series for one indicator within an inclusive start/end year.
- Expose year-by-year values and downloadable CSV observations with source and unit metadata.
- Report absolute changes and relative percentage changes only when at least two distinct observed years exist and the baseline permits calculation.
- Compare two to five countries for one indicator and reporting year, with side-by-side values, observed historical trends, differences against the first selected country, and explicit missing values.
- Compare only identical indicator codes, units, and years. Healthcare-expenditure absolute differences use percentage-point units, distinct from relative percentages.

### Rankings and map

- Sort stored values for a selected indicator/year in either direction, search countries, show a bar chart and country-selection action, and exclude countries without an observation.
- Describe numeric ordering without claiming that all higher/lower values indicate better health.
- Keep the world choropleth, hover and ISO-3 join; add an accessible country selector and zoom controls so Singapore and other small countries remain selectable.

### Analytical integrity

All statistics derive from SQL-stored observations and are deterministic. Do not interpolate, infer causation, generate medical conclusions, or relabel the experimental health index as a validated measure. No database schema change or full-dataset request is required for these views.

## Phase 4: Predictive analytics and production hardening

### Predictive analytics

- Provide a dedicated, navigable prediction page that does not depend on a successful country-profile lookup.
- Collect the existing five model features with visible names, units, labels, and descriptions: adult mortality, BMI, GDP per capita, schooling, and population.
- Reject blank, negative, or non-finite inputs; require positive BMI and population.
- Display the existing model's finite predicted life-expectancy output, prediction history, loading/success/error states, and a model-information/limitations panel.
- State that the model is experimental, based on historical country-year records ending in 2015, and not a clinical or individual forecast.
- Display evaluation metrics only when they can be reproduced from the actual model and evaluation data. The current model artifact has no saved metrics, and the retained database has no BMI values, so no score is displayed.
- Keep the original model and prediction-history table. No table or dependency is added.

### Performance and reliability

- Lazy-load routes and heavy visualization modules; do not merely raise the bundle warning threshold.
- Validate API response shapes used by the prediction page and keep a successful result visible if history refresh fails.
- Return sanitized 422 validation errors without echoing invalid submitted values.
- Use the existing SQLite indexes and measured query plans; add no index/cache without evidence.

### Deployment and accessibility

- Configure production CORS with explicit trusted origins; development localhost allowances are not used in production.
- Keep real credentials out of Git and document the required frontend API URL.
- Provide keyboard navigation, skip navigation, focus visibility, labeled inputs, announced loading/errors/results, and responsive form layout.
- Prediction history remains shared and unauthenticated in the current architecture; public use requires authentication or a deliberate alternative history policy.
