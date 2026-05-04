"""Write Argentina destination tables to Parquet via pure DuckDB SQL.

`wells.parquet`, `well_operator_history.parquet`, and
`well_events.parquet` are emitted as single files. The next issue adds
the hive-partitioned `monthly_production/anio=YYYY/data.parquet` tree.
"""

from pathlib import Path

import duckdb


def write_wells(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "wells.parquet"
    con.execute(f"COPY (SELECT * FROM wells) TO '{target}' (FORMAT PARQUET)")


def write_operator_history(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "well_operator_history.parquet"
    con.execute(
        f"COPY (SELECT * FROM well_operator_history) TO '{target}' (FORMAT PARQUET)"
    )


def write_well_events(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "well_events.parquet"
    con.execute(f"COPY (SELECT * FROM well_events) TO '{target}' (FORMAT PARQUET)")
