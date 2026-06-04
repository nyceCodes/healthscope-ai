# Day 02 - Data Source Architecture & Backend Services

## Objectives

* Select healthcare-related public APIs
* Design service architecture
* Configure database layer
* Create initial data models
* Establish analytics framework

---

## Architecture Decisions

Shifted project scope from a simple health dashboard to a broader healthcare intelligence platform.

The platform will integrate:

* Population Intelligence
* Disease Intelligence
* Nutrition Intelligence
* Healthcare Analytics

---

## Public API Evaluation

Selected:

### REST Countries

Purpose:

* Population
* Region
* Capital
* Geographic information

### Disease.sh

Purpose:

* Cases
* Deaths
* Recoveries
* Testing metrics

### Open Food Facts

Purpose:

* Nutritional information
* Product health data
* Food intelligence capabilities

---

## Backend Architecture

Implemented service layer pattern:

CountryService

Responsible for:

* Country demographic retrieval

DiseaseService

Responsible for:

* Disease metric retrieval

NutritionService

Responsible for:

* Food and nutrition data retrieval

AnalyticsService

Responsible for:

* Health metric calculations
* Future risk-scoring models

---

## Database Foundation

Configured SQLAlchemy.

Created:

Database Engine

Session Factory

Declarative Base

---

## Models Created

### CountrySnapshot

Stores:

* Country metrics
* Health indicators
* Future trend data

### NutritionSearch

Stores:

* Nutrition search history
* Future analytics usage

---

## Challenges

Required reevaluation of project scope to ensure the platform provides meaningful analytics rather than simply displaying API responses.

---

## Lessons Learned

* Public API selection directly influences product capabilities.
* Service-oriented architecture improves maintainability.
* Healthcare analytics requires aggregation from multiple domains.

---

## Next Steps

* Create unified health profile model
* Implement data normalization layer
* Build analytics calculations
* Expose first meaningful API endpoint
