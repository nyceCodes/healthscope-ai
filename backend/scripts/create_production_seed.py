import argparse
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


_LOCAL_OR_OPERATIONAL_TABLES = (
    "prediction_history",
    "nutrition_searches",
    "health_data_imports",
    "health_data_import_checkpoints",
)


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    }


def _row_count(connection: sqlite3.Connection, table: str) -> int:
    quoted_table = table.replace('"', '""')
    return connection.execute(
        f'SELECT COUNT(*) FROM "{quoted_table}"'
    ).fetchone()[0]


def create_production_seed(source_path: Path, output_path: Path) -> dict[str, int]:
    source = source_path.expanduser().resolve()
    output = output_path.expanduser().resolve()
    if source == output:
        raise ValueError("The production seed output must not replace the source database")
    if not source.is_file():
        raise FileNotFoundError(f"Source database does not exist: {source}")

    output.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"{source.as_uri()}?mode=ro"
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)

    try:
        with closing(sqlite3.connect(source_uri, uri=True)) as source_db:
            source_tables = _tables(source_db)
            if "health_indicator_observations" not in source_tables:
                raise ValueError(
                    "Source database is missing health_indicator_observations"
                )
            source_counts = {
                table: _row_count(source_db, table)
                for table in source_tables
            }
            with closing(sqlite3.connect(temporary)) as seed_db:
                source_db.backup(seed_db)
                seed_tables = _tables(seed_db)
                removed_counts = {}
                for table in _LOCAL_OR_OPERATIONAL_TABLES:
                    if table in seed_tables:
                        removed_counts[table] = _row_count(seed_db, table)
                        seed_db.execute(f'DELETE FROM "{table}"')
                seed_db.commit()

                if seed_db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Production seed failed SQLite integrity_check")

                for table, source_count in source_counts.items():
                    expected_count = (
                        0
                        if table in _LOCAL_OR_OPERATIONAL_TABLES
                        else source_count
                    )
                    if _row_count(seed_db, table) != expected_count:
                        raise RuntimeError(
                            f"Production seed row-count verification failed for {table}"
                        )

        os.replace(temporary, output)
        return {
            "observations": source_counts["health_indicator_observations"],
            "excluded_predictions": removed_counts.get("prediction_history", 0),
        }
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a production SQLite copy without local history records."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "healthscope.db",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output database path (must differ from the source database)",
    )
    args = parser.parse_args()
    report = create_production_seed(args.source, args.output)
    print(
        f"Created {args.output}; preserved {report['observations']:,} World Bank "
        f"observations and excluded {report['excluded_predictions']:,} prediction "
        "history rows."
    )


if __name__ == "__main__":
    main()
