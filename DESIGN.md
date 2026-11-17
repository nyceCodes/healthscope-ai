# HealthScope AI Design

## Global indicators

The dashboard adds a global indicator panel above the existing country profile. Users select an indicator and an available reporting year; changing either control reloads only the stored observation API endpoint. The existing profile, rankings, charts, and prediction workflow remain available.

The map uses a five-step sequential blue scale spanning the selected indicator's observed minimum and maximum. The legend labels the value range and unit. Countries without a value for the selected indicator/year use a neutral slate fill and the label “No data”; nulls are never converted to zero. Hover or keyboard focus announces the country, value (or “No data”), unit, and year. Clicking a country opens its stored observations for the selected year.

## Transparency

The panel identifies World Bank World Development Indicators as the source, shows the indicator definition, selected reporting year, and warns that annual observations are historical rather than live. Each country metric includes its own unit, year, and source. If an earlier year is selected, the latest available year is also shown. Whether observations were loaded through the API or an official WDI archive does not change the stored source attribution or dashboard display.

## Geographic asset

The included Natural Earth 1:110m Admin 0 country GeoJSON is for display boundaries only and is served locally. It contains no health measurements. The map uses ISO-3 boundary properties to join observations; unmatched boundary features remain neutral.

## Existing visual behavior

Phase 1 sections and the life-expectancy prediction form are retained. The map layout collapses to a single column on small screens, and country paths support keyboard activation in addition to pointer interaction.

## Phase 3 analytics workspace

The dashboard's Country analytics section uses four keyboard-accessible navigation tabs:

- **Country Explorer**: searchable country name/ISO-3, country name/code/region, and one metric card for each stored World Bank indicator. Each card displays its own latest observed value, actual reporting year, unit, and source. The historical line chart follows the selected indicator and labels change across the first and last available observations; it does not replace missing years.
- **Trends**: one-to-five countries, an indicator shared with the map, inclusive start/end-year filters, an overlay line chart, a year-by-year table, observed-range absolute/relative changes, and a CSV export of the returned observations.
- **Compare**: two-to-five countries, the shared indicator/year controls, a side-by-side value/difference table, explicit “No data” entries, and a historical multi-country line chart. The first selected country is the difference reference.
- **Rankings**: shared indicator/year controls, ascending/descending numeric sort, country search, a bar chart for up to 20 visible matching rows, and a complete searchable table. Links select the country in the Explorer.

Plots and tables retain the observation's reporting year. Missing observations create chart gaps and are never filled or treated as zero. Percentage changes are relative changes; healthcare-expenditure absolute changes are explicitly in percentage points. Rankings describe measured values, not overall health or quality. The existing experimental index remains clearly separate.

The map includes an ISO-3 country dropdown for all stored countries and buttons to zoom/reset the choropleth. It remains responsive; the selector supports Singapore even when its polygon is too small to click reliably. Analytics use shared catalog/year requests from the dashboard rather than fetching the same metadata again.

## Phase 4 predictive analytics

The top navigation offers Dashboard and Predictive analytics routes. The predictor is independent of country-profile loading and presents five labeled, unit-bearing fields: adult-mortality probability per 1,000 population between ages 15 and 60, average BMI (kg/m²), GDP per capita (US dollars), schooling (years), and population (people). Zero/negative BMI and population, negative other values, blank values, and non-finite values are rejected before submission. The API validates the same rules.

While a request is pending, the action is disabled and a status is announced. A valid response is checked for a finite numeric result before display. If the prediction succeeds but history refresh fails, the result stays visible and a separate history error with retry is shown. Empty history, loading, and errors each have explicit text. History entries show value and timestamp, not a fabricated country label.

The model panel identifies the retained 100-tree Random Forest and its historical country-year target coverage (2000–2015), describes every input and unit, and states that estimates are experimental and not clinical advice. It does not show a performance score: the training script prints holdout MAE but does not store it, and the current database has no BMI values for a valid metric reproduction.

Prediction history is enabled by default only for local development and can be disabled with `HEALTHSCOPE_PREDICTION_HISTORY_ENABLED=false`. In production, history reads return 404 and anonymous predictions are computed without storing their inputs, even if the setting is true. Existing local rows are left intact; deploy a production database without local user-generated history. Anonymous prediction results remain available.

## Phase 5B deployment behavior

The React/Vite app remains a static single-page application. Its API origin is supplied through `VITE_API_BASE_URL` at build time; only development builds use the localhost fallback. Vercel's configured SPA rewrite serves the app shell for direct navigation and refresh on client-side routes. The existing map GeoJSON stays under `frontend/public/data`, and page/chart lazy loading is unchanged.

Production API startup uses an explicitly configured SQLite file and rejects a database that contains prediction-history rows. The separate seed builder preserves public reference observations without modifying the source database. `GET /health` returns a minimal readiness result after checking database connectivity; API debug mode is disabled.

## Phase 4 responsiveness and accessibility

Route modules and the map/charts use lazy imports with visible loading states. The shared navigation includes a skip link, keyboard-operable links, and visible focus styling. Prediction inputs have associated labels and descriptions; result, pending, and error states use live/status semantics. Forms and history cards collapse to a single column on mobile; tables elsewhere retain horizontal scrolling. These are implementation measures, not a formal WCAG conformance certification.
