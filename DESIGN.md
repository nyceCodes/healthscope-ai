# HealthScope AI Design

## Global indicators

The dashboard adds a global indicator panel above the existing country profile. Users select one of four World Bank WDI or six WHO GHO indicators and an available reporting year; changing either control reloads only the stored observation API endpoint. The existing profile, rankings, charts, and prediction workflow remain available.

The map uses a five-step sequential blue scale spanning the selected indicator's observed minimum and maximum. The legend labels the value range and unit. Countries without a value for the selected indicator/year use a neutral slate fill and the label “No data”; nulls are never converted to zero. Hover or keyboard focus announces the country, value (or “No data”), unit, and year. Clicking a country opens its stored observations for the selected year.

## Transparency

The panel identifies the selected provider and publisher, shows the indicator definition, selected reporting year, and links to official metadata/source references. It describes the data as stored historical country-level observations and does not imply a common annual update schedule. Each country metric includes its own unit, year, provider, and source reference when available. The professional CSV export retains row-level citations, source timestamps, denominator descriptions, dimensions, and uncertainty bounds. Whether WDI observations were loaded through its API or an official archive does not change their source attribution.

## Geographic asset

The included Natural Earth 1:110m Admin 0 country GeoJSON is for display boundaries only and is served locally. It contains no health measurements. The map uses ISO-3 boundary properties to join observations; unmatched boundary features remain neutral.

## Existing visual behavior

Phase 1 sections and the life-expectancy prediction form are retained. The map layout collapses to a single column on small screens, and country paths support keyboard activation in addition to pointer interaction.

## Phase 3 analytics workspace

The dashboard's Country analytics section uses four keyboard-accessible navigation tabs:

- **Country Explorer**: searchable country name/ISO-3, country name/code/region, and one metric card for each stored WDI or WHO GHO indicator. Each card displays its own latest observed value, actual reporting year, unit, provider, and source reference when available. Indicator metadata links are shown with the selected historical chart; missing years are not replaced.
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

## Task 1 — audience and content design audit

Repository review on 2026-11-18 confirms that the current UI is a single dashboard with an analytics workspace and a separate prediction route; it does not yet have separate public/professional modes, an in-product reference library, or a methodology page. The country search relies on placeholder text rather than a visible associated label, and the dashboard combines audience and data types in one long experience. The choropleth uses five equal-width bins between the selected series' minimum and maximum; it does not communicate a stable cross-year scale and can be sensitive to outliers. This target design reuses current components and does not imply implementation.

### Experience map

- **Global Overview (public):** explain the platform scope, selected year, available indicator coverage and whether values are modeled or observed. Link directly into the explorer.
- **Public Health Explorer:** map plus keyboard-accessible country list/table, indicator, year, historical trend, a short neutral explanation, units/denominator, missingness, and “what this does not establish.”
- **Country Profiles:** show each indicator with its own reporting year, publisher, method/source link and coverage caveat. Keep values from distinct years visibly separate. Historical COVID totals must be clearly dated to the provider observation (or marked date unknown), not just the retrieval timestamp.
- **Professional Data Explorer:** expose code/definition, units and denominators, collection/estimate method, country/year availability, gaps and revision/source metadata. Use controlled terminology and allow row-level download with source/year attached.
- **Trends & Comparisons:** keep the existing same-indicator series/analytics patterns. Display selected interval, actual first/last observation years, gaps, baseline and absolute/relative units; the first comparison country remains an explicit reference, not a “winner.”
- **Reference Library:** curated official WHO and other publisher pages relevant to measures/topics. Distinguish primary data/methods, general guidance and clinical references; a link is not clinical validation or a recommendation.
- **Sources & Methodology:** searchable indicator/source catalog, calculations, update/revision policy, licensing, coverage limitations and model status.
- **Predictive Analytics:** retain a separate experimental route with input definitions, training-data provenance, measured model status and a prominent population-level/not-clinical disclaimer. Never attach the output to an individual or clinical action.

Audience selection may simplify wording and expose technical detail, but data access is currently public and there is no user role or professional authentication. Do not imply otherwise.

### Content and representation rules

Use the six public questions as content checks: WHO is actually represented; WHAT measure is shown; WHEN is its reporting period; WHERE is its geographic unit; WHY is it relevant without a causal claim; HOW is it calculated, sourced and limited. Current data is country-year aggregate; the neonatal WHO series is restricted to both sexes and 0–27 days, while the other imported indicators do not claim subgroup coverage. Do not invent demographic breakdowns.

Every displayed or downloaded value must stay paired with its measure definition, unit, actual year, geographic unit and source. State whether a series is a modeled estimate, survey-derived, administrative, composite or a reported total when known. Distinguish source publication/update period from HealthScope import time. For a null/missing row, show “No data” or a gap; never show zero. Use “percentage points” for absolute differences between percentages and “percent” for relative change.

Replace subjective rank language (“winner,” “healthiest,” “high risk”) with an explicit measure and order direction. The current legacy dashboard's “Experimental Health Index,” mortality/recovery percentages, risk level, recommendations and causal-sounding insight text are not supported public/professional content; hide or quarantine them until definitions, denominator, data recency, validation and independent expert review support their return. At minimum, reported deaths/reported cases is not a population mortality rate, and tests per population is not unique-person testing coverage.

Prefer a table or text summary equivalent to every map/chart, visible keyboard focus, non-color-only data distinction, readable gap/missing states, and responsive controls. Give every form field an accessible name independent of placeholder text. Make map binning explicit and avoid suggesting that dynamic color ranges are comparable between indicators or years. Document accessibility verification separately; visual use of a keyboard role alone does not establish WCAG conformance.

### Sources and maintenance notes

At the Task 1 audit, the four implemented global series came through WDI and WHO GHO was only a candidate connection. Task 2 adds six allowlisted WHO GHO series in the normalized observation store; the legacy KaggleHub “WHO” table remains a distinct dataset with incomplete features and no row-level release metadata. WHO GHO neonatal data retain the selected both-sex/0–27-day dimensions; no other arbitrary strata are loaded. No fixed refresh interval exists; ingestion is manual and provider update periods differ. WHO record timestamps are kept distinct from publication dates and import times; specific dataset versions and reuse terms are not supplied by this import and still need source review.
