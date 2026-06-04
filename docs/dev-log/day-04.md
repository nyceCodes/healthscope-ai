# Day 04 - Persistence Layer & Historical Health Analytics

## Objectives

- Persist healthcare analytics data to SQLite
- Create historical data storage mechanism
- Implement snapshot retrieval APIs
- Introduce database-backed analytics architecture

---

## Accomplishments

### SQLite Integration

Configured SQLAlchemy persistence layer.

Implemented:

- Database Engine
- Session Management
- ORM Models
- Automatic Table Creation

---

### CountrySnapshot Model

Created CountrySnapshot model to store historical healthcare metrics.

Stored Fields:

- Country
- Population
- Cases
- Deaths
- Recovered
- Active Cases
- Tests
- Recovery Rate
- Mortality Rate
- Health Index
- Timestamp

---

### Snapshot Service

Implemented SnapshotService.

Responsibilities:

- Create snapshot records
- Persist health profile data
- Isolate database operations from API routes

Architecture:

Route
↓
Service
↓
Database

---

### Historical Analytics Endpoint

Implemented:

GET /health/history/{country}

Example:

GET /health/history/Philippines

Returns historical healthcare snapshots ordered by creation date.

---

### Data Lifecycle

Established complete analytics pipeline:

External APIs
↓
Data Aggregation
↓
Health Profile
↓
Analytics Engine
↓
SQLite Persistence
↓
Historical Retrieval

---

## Challenges

### Missing Table Error

Encountered:

sqlite3.OperationalError:
no such table: country_snapshots

Root Cause:

SQLAlchemy model definitions were not registered before:

Base.metadata.create_all()

executed.

Resolution:

Imported:

- CountrySnapshot
- NutritionSearch

before table initialization.

This allowed SQLAlchemy metadata to properly discover and create tables.

---

## Lessons Learned

- SQLAlchemy only creates tables for imported models.
- Persistence enables future analytics capabilities such as trends and rankings.
- Service-layer architecture keeps API routes lightweight and maintainable.
- Historical storage transforms an API consumer into an analytics platform.

---

## Key Achievement

Successfully stored and retrieved healthcare snapshots from SQLite.

Verified:

GET /health/profile/Philippines

creates a database record.

GET /health/history/Philippines

retrieves historical records.

---

## Next Steps

- Country rankings
- Multi-country comparisons
- Trend analytics
- Dashboard-ready APIs