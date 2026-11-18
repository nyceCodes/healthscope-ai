import argparse
import logging

from app.database.database import (
    Base,
    SessionLocal,
    engine,
    ensure_health_data_schema,
)
from app.services.who_gho_service import (
    WHO_INDICATORS,
    WhoGhoClient,
    ingest_who_gho,
)
from app.utils.datetime_utils import utc_now


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import the approved WHO GHO health indicators into SQLite."
    )
    parser.add_argument("--start-year", type=int, default=2000)
    parser.add_argument("--end-year", type=int, default=utc_now().year)
    parser.add_argument(
        "--indicator",
        action="append",
        choices=sorted(WHO_INDICATORS),
        help="Import only the selected indicator (may be provided multiple times).",
    )
    parser.add_argument("--connect-timeout", type=float, default=10)
    parser.add_argument("--read-timeout", type=float, default=60)
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    Base.metadata.create_all(bind=engine)
    ensure_health_data_schema(engine)
    db = SessionLocal()
    try:
        imports = ingest_who_gho(
            db,
            args.start_year,
            args.end_year,
            indicator_codes=args.indicator,
            client=WhoGhoClient(
                timeout=(args.connect_timeout, args.read_timeout),
                page_size=args.page_size,
            ),
        )
        for run in imports:
            print(
                f"{run.indicator_code}: {run.status}; "
                f"inserted={run.rows_inserted}, updated={run.rows_updated}, "
                f"missing={run.rows_missing}, rejected={run.rows_rejected}, "
                f"duplicates={run.rows_duplicate}"
            )
        return 0
    except Exception:
        logging.getLogger(__name__).exception("WHO GHO ingestion did not complete")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
