"""Write Petrobras 3W destination tables to Parquet via pure DuckDB SQL.

This slice emits `event_types.parquet` (#19) and `instances.parquet`
(#20). Later slices (#21, #22) add `wells.parquet` and the
hive-partitioned `observations/` tree alongside them.
"""

from __future__ import annotations

from pathlib import Path

import duckdb


def write_event_types(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "event_types.parquet"
    con.execute(
        f"COPY (SELECT * FROM event_types ORDER BY event_class) "
        f"TO '{target}' (FORMAT PARQUET)"
    )


def write_instances(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "instances.parquet"
    con.execute(
        f"COPY (SELECT * FROM instances ORDER BY event_class, instance_id) "
        f"TO '{target}' (FORMAT PARQUET)"
    )
