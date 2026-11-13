import argparse
import logging
from app.database.database import Base, SessionLocal, engine
from app.utils.datetime_utils import utc_now
from app.services.world_bank_service import (
    INDICATOR_UNITS,
    PAGE_SIZE,
    ingest_world_bank_csv,
    ingest_world_bank,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import World Bank health indicators into the local SQLite database."
    )
    parser.add_argument("--start-year", type=int, default=1960)
    parser.add_argument("--end-year", type=int, default=utc_now().year)
    parser.add_argument(
        "--batch-years",
        type=int,
        default=5,
        help="Split API imports into year ranges of this size (default: 5).",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=PAGE_SIZE,
        help="Maximum API observations per page (default: 500).",
    )
    parser.add_argument("--connect-timeout", type=float, default=10)
    parser.add_argument("--read-timeout", type=float, default=90)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip successfully checkpointed API pages (default: enabled).",
    )
    parser.add_argument(
        "--csv",
        help="Import from an official World Bank CSV file or bulk ZIP archive instead of the API.",
    )
    parser.add_argument(
        "--country",
        help="Limit the import to one ISO-3 country code (for example PHL).",
    )
    parser.add_argument(
        "--indicator",
        action="append",
        choices=sorted(INDICATOR_UNITS),
        help="Import only the selected indicator (may be provided multiple times).",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if args.csv:
            imports = ingest_world_bank_csv(
                db,
                args.csv,
                args.start_year,
                args.end_year,
                indicator_codes=args.indicator,
                country_iso3=args.country,
            )
        else:
            imports = ingest_world_bank(
                db,
                args.start_year,
                args.end_year,
                indicator_codes=args.indicator,
                country_iso3=args.country,
                batch_years=args.batch_years,
                per_page=args.per_page,
                resume=args.resume,
                timeout=(args.connect_timeout, args.read_timeout),
                retries=args.retries,
            )
        for run in imports:
            print(
                f"{run.indicator_code}: {run.status}; "
                f"inserted={run.rows_inserted}, updated={run.rows_updated}, "
                f"missing={run.rows_missing}, rejected={run.rows_rejected}"
            )
        return 0
    except Exception:
        logging.getLogger(__name__).exception("World Bank ingestion did not complete")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
