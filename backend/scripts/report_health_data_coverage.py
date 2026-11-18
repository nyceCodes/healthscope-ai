import argparse
import csv
from pathlib import Path

from app.database.database import (
    Base,
    SessionLocal,
    engine,
    ensure_health_data_schema,
)
from app.services.coverage_service import build_data_coverage


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write a country/indicator reporting-year availability CSV."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "reports"
        / "health_data_coverage.csv",
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_health_data_schema(engine)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        coverage = build_data_coverage(db)
        with output.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "indicator_code",
                    "country_iso3",
                    "country_name",
                    "observation_count",
                    "first_year",
                    "last_year",
                    "observed_years",
                    "unobserved_years_within_span",
                    "cadence_note",
                ],
            )
            writer.writeheader()
            for row in coverage:
                writer.writerow(
                    {
                        "indicator_code": row.indicator_code,
                        "country_iso3": row.country_iso3,
                        "country_name": row.country_name,
                        "observation_count": row.observation_count,
                        "first_year": row.first_year,
                        "last_year": row.last_year,
                        "observed_years": ";".join(
                            str(year) for year in row.observed_years
                        ),
                        "unobserved_years_within_span": ";".join(
                            str(year)
                            for year in row.unobserved_years_within_span
                        ),
                        "cadence_note": row.cadence_note,
                    }
                )
        print(f"Wrote {len(coverage)} country-indicator rows to {output}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
