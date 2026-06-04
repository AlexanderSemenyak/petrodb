"""Build the `instances` catalog table from the staged upstream tree.

Scans every `<staging>/dataset/N/*.parquet` and emits one catalog row per
file. The transform is pure DuckDB SQL (per the operating principle in
CONTEXT.md): a single `read_parquet(..., filename=true)` pulls every
upstream row, the filename column is parsed into `instance_id`,
`well_kind`, `well_id`, and the per-file aggregates (`start_ts`,
`end_ts`, `duration_s`, `n_rows`, four `n_rows_*` counts) are computed
in the same query.

The `n_rows_transient` column is materialised as NULL for event classes
where `has_transient = false` (events 0, 3, 4), matching the convention
in CONTEXT.md so downstream consumers can distinguish "no transient
phase by design" from "the transient phase had zero rows".

`source_url` points at the future Observations file location. The URL
pattern is fixed by ADR-0001 so it can be computed here before
`observations/` exists.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from scripts.transform.petrobras_3w.constants import PUBLIC_BASE_URL


class NoInstanceFilesError(Exception):
    """The staged upstream tree contains no per-instance parquet files."""


def build(con: duckdb.DuckDBPyConnection, staging_dir: Path) -> None:
    """Create the `instances` table by aggregating every staged instance file.

    Requires the `event_types` table to already exist in `con` — the
    `has_transient` flag drives the NULL-vs-zero choice for
    `n_rows_transient`. Call this after `event_types_builder.build`.
    """
    staging_dir = Path(staging_dir)
    dataset_root = staging_dir / "dataset"
    instance_files = sorted(dataset_root.glob("*/*.parquet"))
    if not instance_files:
        raise NoInstanceFilesError(
            f"no instance files under {dataset_root} — staging may be incomplete"
        )

    glob_pattern = str(dataset_root / "*" / "*.parquet")

    con.execute(
        f"""
        CREATE OR REPLACE TABLE instances AS
        WITH raw AS (
            SELECT
                filename,
                CAST(regexp_extract(filename, '/dataset/([0-9]+)/', 1)
                     AS INTEGER) AS event_class,
                regexp_extract(filename, '/([^/]+)\\.parquet$', 1)
                    AS instance_id,
                regexp_extract(filename, '/([^/]+\\.parquet)$', 1)
                    AS source_file,
                "timestamp" AS ts,
                class
            FROM read_parquet('{glob_pattern}', filename=true)
        ),
        parsed AS (
            SELECT
                instance_id,
                source_file,
                event_class,
                CASE
                    WHEN starts_with(instance_id, 'WELL-')      THEN 'real'
                    WHEN starts_with(instance_id, 'SIMULATED_') THEN 'simulated'
                    WHEN starts_with(instance_id, 'DRAWN_')     THEN 'drawn'
                END AS well_kind,
                CASE
                    WHEN starts_with(instance_id, 'WELL-')
                    THEN CAST(regexp_extract(instance_id, '^WELL-0*([0-9]+)_', 1)
                              AS INTEGER)
                END AS well_id,
                ts,
                class
            FROM raw
        ),
        aggregated AS (
            SELECT
                p.instance_id,
                p.well_kind,
                p.well_id,
                p.event_class,
                p.source_file,
                MIN(p.ts) AS start_ts,
                MAX(p.ts) AS end_ts,
                COUNT(*) AS n_rows,
                SUM(CASE WHEN p.class IS NULL THEN 1 ELSE 0 END)
                    AS n_rows_warmup_null,
                -- The NORMAL precursor (class = 0) only exists for anomaly
                -- events. Event 0's `class = 0` rows are its labelled regime
                -- itself, so they go to `n_rows_steady`, not `n_rows_normal`
                -- — otherwise the four buckets would double-count for that
                -- event. See CONTEXT.md "events 0, 3, 4 carry only the
                -- steady class — no NORMAL precursor either".
                SUM(CASE WHEN p.class = 0 AND p.event_class <> 0 THEN 1 ELSE 0 END)
                    AS n_rows_normal,
                SUM(CASE WHEN p.class = p.event_class + 100 THEN 1 ELSE 0 END)
                    AS n_rows_transient_raw,
                SUM(CASE WHEN p.class = p.event_class THEN 1 ELSE 0 END)
                    AS n_rows_steady
            FROM parsed p
            GROUP BY p.instance_id, p.well_kind, p.well_id,
                     p.event_class, p.source_file
        )
        SELECT
            a.instance_id,
            a.well_kind,
            a.well_id,
            a.event_class,
            a.start_ts,
            a.end_ts,
            CAST(date_diff('second', a.start_ts, a.end_ts) AS BIGINT)
                AS duration_s,
            a.n_rows,
            a.n_rows_warmup_null,
            a.n_rows_normal,
            CASE WHEN et.has_transient
                 THEN a.n_rows_transient_raw
                 ELSE NULL
            END AS n_rows_transient,
            a.n_rows_steady,
            a.source_file,
            '{PUBLIC_BASE_URL}/observations/event_class='
                || a.event_class || '/' || a.instance_id || '.parquet'
                AS source_url
        FROM aggregated a
        LEFT JOIN event_types et ON et.event_class = a.event_class
        ORDER BY a.event_class, a.instance_id
        """
    )
