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
- Anonymous life-expectancy predictions remain available in production, but production never saves prediction inputs or serves shared history. Local development history remains enabled by default and can be disabled with `HEALTHSCOPE_PREDICTION_HISTORY_ENABLED=false`; existing local records are not deleted. Use a production database without local prediction-history records.
- Prepare, but do not deploy, the frontend as a Vercel static Vite app and the API as a separate FastAPI service. Production requires an explicit frontend API URL, trusted CORS origins, and a sanitized, separately configured SQLite seed.
- The production seed must retain all stored World Bank observations and public reference tables while excluding local prediction history and user/operational records. The repository-local database remains unchanged.
- Expose a lightweight database-backed `/health` endpoint for provider health checks. Do not require World Bank API access during application startup.

## Task 1 — product and data audit

This section records the repository state reviewed on 2026-11-18 and the proposed V2 product direction. It does not claim that the proposed experience or data expansion is implemented.

### Verified current state

- The frontend currently has two top-level routes: Dashboard (`/`) and Predictive analytics (`/predictive-analytics`). The map and Country Explorer, Trends, Compare, and Rankings are sections/tabs within the dashboard, not separate audience workspaces. There is no public/professional mode, Reference Library, or in-product Sources & Methodology page.
- The backend has two groups of health routes: legacy country/COVID snapshot and model routes, and the stored WDI indicator/catalog/analytics routes. WDI reads are backed by SQLite; API ingestion is an explicit CLI operation, not a scheduled job.
- Read-only inspection of both local SQLite files found `integrity_check=ok`, 217 World Bank country/economy entries, four indicators, and 20,312 observations. Their covered years are 2000–2024. Current stored row counts are 5,425 life-expectancy observations (217 country/economy entries), 5,425 population observations (217), 4,900 under-five mortality observations (196), and 4,562 current health expenditure observations (193). The last two series have 525 and 863 missing country-year values respectively, represented by absent rows. These totals describe the local working copy, not a guaranteed live provider count.
- Import history currently records 10 successful and 4 failed runs. Failures are retained and imports are designed to be repeatable; the CLI has no automated refresh schedule.
- The latest successful imports for all four stored WDI indicators completed on 2026-11-12; their latest observation year is 2024. This is the local importer timestamp and stored reporting range, not proof that the upstream providers had no newer release.
- The legacy KaggleHub dataset (`kumarajarshi/life-expectancy-who`) has 2,938 country-year rows for 193 countries over 2000–2015. The local table has 10 missing life-expectancy targets and missing BMI in all 2,938 rows. It is a Kaggle-hosted WHO-labelled dataset, not a direct WHO API feed; source-release and licensing provenance are not stored per row. It is not suitable as a verified model-evaluation set in its current state.
- The legacy profile path still uses disease.sh COVID totals. Its saved snapshots contain 38 rows across five countries; their database timestamps run from 2026-06-04 to 2026-11-13. A retrieval timestamp is not necessarily the provider's observation date. Legacy code derives rates from reported totals, substitutes some absent values with zero, and exposes an experimental index plus threshold-based risk labels and recommendations. Those labels and recommendations are not validated epidemiology or clinical guidance.
- Prediction history contains three rows in the local database. SQLite files are Git-ignored; the separate local production-seed copy retains public indicator/reference data and contains zero prediction-history rows. Neither local database is evidence that individual/patient records are part of the product; the schema is country-level plus model-input history, with no patient identifiers.
- Tests and APIs establish WDI filtering, missing-value handling, comparisons, trends, rankings, and prediction input validation. They do not establish clinical validity, update freshness, population subgroup coverage, or the coverage of proposed new indicators.

### Product audiences and requirements

**Public experience**

- Explain who is represented and who is not; for current global data the unit of analysis is a country/economy and year, not an individual, age group, sex, or other population stratum.
- Answer what/when/where with a selected indicator, actual reporting year, geographic scope, observed trend, and explicit missingness.
- Explain why an indicator may matter using neutral, sourced context. Do not infer causes, prescribe interventions, or imply that a country rank is a judgement of health or policy performance.
- Explain how it is measured: definition, unit, numerator/denominator where applicable, source organization, estimate/measurement status, publication period, last import time, and known gaps.
- Use plain language, accessible map/table alternatives, and no patient-specific advice.

**Professional/public-health experience**

- Support country profiles, disease/outcome measures, service coverage, workforce/infrastructure measures, historical patterns, comparable country-year analysis, downloadable observation-level data, and explicit methodology/data-quality context.
- Expose indicator definitions, units and denominators, actual years, source lineage, estimation or survey caveats, missingness, revisions where available, and provenance links. Allow experts to assess evidence; do not present aggregate data as patient-specific guidance or operational clinical decision support.
- Provide official reference links for indicator methodology and relevant WHO/WB publications. Clearly distinguish a contextual reference link from an endorsement or clinical protocol.
- Do not imply privileged or restricted professional data: there is no authentication or role-based access in the current application. Audience modes should be presentation/workflow presets unless access control is deliberately designed.

### Data-source inventory and expansion shortlist

**Existing source.** World Bank World Development Indicators (WDI), using the public Indicators API v2 or official WDI CSV/ZIP/DataBank exports. The current importer supports sequential paginated API requests and streamed WDI/DataBank CSV/ZIP imports, with validation, source labels, repeatable upserts, and import logs. These are stored measurements/estimates and are not fetched at page-render time. Publication timing differs by series and country; no automatic application refresh is configured.

The existing indicators are `SP.DYN.LE00.IN` (life expectancy at birth, years), `SP.POP.TOTL` (midyear population, people), `SH.DYN.MORT` (under-five mortality, deaths per 1,000 live births), and `SH.XPD.CHEX.GD.ZS` (current health expenditure, % GDP; not capital expenditure).

**Official WHO source.** WHO documents its [Global Health Observatory OData API](https://www.who.int/data/gho/info/gho-odata-api), with indicator and dimension discovery, indicator observations, and filters for dimensions and time. It can expose disaggregated series, but indicator identifiers, dimensions, completeness, update dates, reuse terms, and pagination/export behavior must be checked per series before ingestion. The current WDI schema/importer does not ingest WHO GHO observations directly.

The following eight additions are a **shortlist for pilot profiling**, not approved/imported data. Their codes, names, definitions, and source organizations were found in WDI indicator metadata during this audit. Observation queries could not be completed (HTTP 502 from the API data endpoint), so country coverage, latest year, gaps, and empirical reporting regularity remain unverified. Confirm those dimensions from actual API pages and an official bulk extract before selecting the launch set.

| Candidate WDI code | Indicator and unit | Underlying source/quality consideration | Ingestion path and priority |
|---|---|---|---|
| `SH.STA.MMRT` | Maternal mortality ratio, modeled estimate per 100,000 live births | WHO/UNICEF/UNFPA/World Bank inter-agency modeled estimates; communicate modeling and revisions | WDI API or official WDI CSV/ZIP; high public-health value, pilot first |
| `SH.DYN.NMRT` | Neonatal mortality per 1,000 live births | UN Inter-agency Group for Child Mortality Estimation; estimates may be revised | WDI API or official WDI CSV/ZIP; high value, pilot first |
| `SH.IMM.IDPT` | DPT immunization coverage, % of children ages 12–23 months | WHO/UNICEF estimates; distinguish estimated coverage from registry/survey observations | WDI API or official WDI CSV/ZIP; high value, pilot first |
| `SH.TBS.INCD` | Tuberculosis incidence per 100,000 people | WHO Global TB Report estimates; revisions and estimation methods matter | WDI API or official WDI CSV/ZIP; high disease-burden value |
| `SH.STA.BRTC.ZS` | Births attended by skilled health staff, % of total | UNICEF/DHS and other survey sources; collection intervals and definitions vary | WDI API or official WDI CSV/ZIP; useful, but irregular survey years |
| `SH.UHC.SRVS.CV.XD` | UHC service coverage index, 0–100 | WHO Global Health Observatory; composite index with periodic/uneven updates; metadata currently identifies a WDI Database Archives source | WDI API and official archive must be tested; retain source/vintage and methodology link |
| `SH.MED.PHYS.ZS` | Physicians per 1,000 people | WHO workforce statistics, OECD, and country data; reporting years and comparability vary | WDI API or official WDI CSV/ZIP; useful workforce measure, likely sparse |
| `SH.MED.NUMW.P3` | Nurses and midwives per 1,000 people | WHO workforce statistics, OECD, and country data; occupational definitions vary | WDI API or official WDI CSV/ZIP; useful workforce measure, likely sparse |

These are not all direct WHO feeds: WDI acts as the harmonized distribution layer for many WHO/UN estimates. Prefer one canonical indicator/source series rather than importing a duplicate direct GHO series under a second code. Use direct GHO ingestion only when its dimensions or timeliness add a documented benefit and can be preserved without collapsing meaningful subgroup differences. WDI/WHO publication schedules vary; the application should disclose provider reporting years and import timestamps rather than promise that every series updates annually. A quarterly source-freshness review and import after a provider release is a proposed operating policy, not current automation.

### Prioritized feature specification

1. **P0 — Trust and safety baseline.** Make the unit of analysis, observed year, measurement/model status, source, denominator, missingness, and source date visible. Do not show the legacy health index, “risk assessment,” causal insight, or intervention recommendation as public/professional findings until reviewed and methodologically supported. Separate provider observation date from retrieval timestamp; never turn unknown values into zero.
2. **P1 — Public Global Overview and Health Explorer.** Reuse the WDI map and controls. Add plain-language measure explanations, year-aware trends, scope/missingness summaries, accessible non-map alternatives, and a concise “what this can/cannot say” note.
3. **P1 — Country Profiles.** Compose existing WDI Country Explorer observations with explicit source years and source links. Keep legacy COVID snapshots visibly historical/provider-reported or remove them from the evidence-led profile until date/provenance semantics are reliable. Never imply that different indicators share one reporting year.
4. **P2 — Professional Data Explorer and Trends & Comparisons.** Reuse the existing explorer, trends, comparison, rankings and CSV export. Add source/methodology, estimate/survey status, coverage and missingness, data quality notes, and provenance to each result/export. Add disease burden/workforce measures only after pilot profiling.
5. **P2 — Reference Library and Sources & Methodology.** Curate official WHO/WDI definitions and methods per indicator and linked resources per topic. Display publication/update cadence as provider-specific; include app import timestamp and a data revision note where available.
6. **P3 — Predictive Analytics.** Keep as an isolated experimental experience. Label its country-year training basis and unsupported input extrapolation; no patient-specific output, clinical recommendations, or performance claims without reproducible evaluation and expert review.

### Proposed information architecture

- **Global Overview** — public landing, indicator coverage and selected reporting year.
- **Public Health Explorer** — map, year, indicator, historical series, plain-language context and missing-data explanation.
- **Country Profiles** — country/economy context and individually year-stamped measures.
- **Professional Data Explorer** — technical filters, metadata, coverage, provenance and export.
- **Trends & Comparisons** — observed series and same-indicator/same-year comparisons.
- **Reference Library** — official topic and clinical/public-health reference links, clearly marked as references.
- **Predictive Analytics** — separate experimental model route, not integrated into clinical decisions.
- **Sources & Methodology** — indicator catalog, calculations, update policy, limitations, licensing and release metadata.

Reuse the current Dashboard, `GlobalAnalytics`, map, API client, WDI endpoints/services, and prediction route. Audience entry points and page groupings are proposed changes; no new application code is part of this audit.

### Implementation dependencies and acceptance criteria

- No new package is required for the proposed initial experience. Existing React/TypeScript/Vite, FastAPI/Pydantic, SQLAlchemy/SQLite, and charts cover the workflows.
- WDI additions require allowlisted codes, verified definitions/units, importer metadata, and tests for missing values, annual coverage and idempotent updates. Current importer metadata/CLI choices are explicitly enumerated and need extension.
- Direct WHO GHO ingestion is a separate follow-on adapter: map GHO country/indicator/dimension/time metadata to stable internal identifiers; retain disaggregation and source release; test paging, schema drift, nulls and revisions before enabling it.
- If subgroup or subnational data is included, define geography and dimension representation before importing. Existing country–indicator–year uniqueness cannot represent multiple sex/age strata without data loss or collisions.
- Before a candidate goes live: import it into a disposable database; report row count, distinct country/economy count, observed year range, latest year, missingness by year/country, value/unit sanity checks, source metadata, and overlap/comparability against WDI/WHO source documentation. Do not infer quality from indicator-catalog presence alone.
- For each view/export, users can identify the indicator, unit, actual reporting year, source/publisher, missingness, and whether values are observed or modeled. No blank is rendered as zero.
- Rankings describe only a selected measure and never claim “healthiest,” causal effect, or policy performance. Rates show the denominator; percentages distinguish percent from percentage points.
- Public and professional views contain no patient-level records or patient-specific instructions. A reference link is not represented as clinical validation.
- Cross-country comparison is limited to the same indicator definition, unit, and reporting year, or explicitly displays the differing years and non-comparability.
- Import or API failure is visible and cannot produce a success-shaped empty chart or outdated value labelled current.
- Existing production/local SQLite data is not altered by this planning/audit document.

### Risk register

| Risk | Current evidence/impact | Mitigation or release gate |
|---|---|---|
| Sparse/revised observations | Country and year coverage differs by WDI series; candidate row queries were not available during this audit | Pilot profile every series; show observed coverage, gaps, revisions and import date |
| Unsupported clinical or causal language | Legacy API/UI includes arbitrary low/moderate/high scores, recommendations and causal-sounding insights based on aggregate thresholds | Remove/quarantine pending evidence and expert review; prefer descriptive, attributed wording |
| Stale or misdated data | Live COVID provider, cached snapshots and profile retrieval timestamps are mixed; snapshot set is small and old/unknown relative to source time | Display actual observation date or explicitly state it is unknown; do not call retrieval time the data date |
| Provenance/licensing | Kaggle-hosted WHO-labelled data has no recorded release/license lineage; direct WHO/WDI asset terms vary | Verify source and reuse terms per dataset; preserve attribution and license in catalog and exports |
| Incomparable series | Survey, administrative, modeled and composite indicators can use different years, populations and methods | Keep method/status and denominator metadata; never silently join duplicates or compare unlike periods |
| Provider/API maintenance | WDI/WHO endpoints, codes, output formats and publishing calendars may change; current WDI API has recorded timeouts/failures | Bounded retries, import logs, source freshness monitoring, schema tests, official archive fallback |
| Misuse of model | Training set/version and held-out metric are not reproducible from the local data; BMI is null in every local training row | Retain experimental-only status and isolate from professional findings pending data/model audit |
| Boundary mismatch | Natural Earth boundary identifiers and WDI economies do not map one-to-one in every case | Show unmatched/no-data states and document disputed/territory limitations |

### Task 2 follow-up — bounded data expansion

The Task 1 WDI candidate coverage could not be verified at the time because its observation requests returned HTTP 502. Task 2 instead implemented the first six approved indicator concepts through the official WHO GHO OData source, as separate source-specific series; it did not import hundreds of codes or merge them with WDI values. The exact WHO codes, definitions, observed country/year counts, provenance fields, limitations, and generated coverage file are documented in [README.md](./README.md), [ARCHITECTURE.md](./ARCHITECTURE.md), [RULES.md](./RULES.md), and [SCHEMA.md](./SCHEMA.md).

The Task 2 import is country-level and manual. Neonatal mortality retains the selected both-sex/0–27-day dimensions; no arbitrary subgroup aggregation is performed. The source does not supply dataset versions or publication dates for these rows, and its reuse/attribution terms still require review before public production release. The product remains descriptive and is not clinically validated.
