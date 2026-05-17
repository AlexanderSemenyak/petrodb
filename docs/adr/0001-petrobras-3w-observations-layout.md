# Petrobras 3W observations layout: one file per Instance, hive on `event_class`

**Status:** accepted

## Context

The Petrobras 3W dataset is a corpus of ~2,228 labeled 1-Hz sensor-data windows ("Instances"), totalling ~1.74 GB compressed. Instance length varies from ~21k rows (~6 h) to ~243k rows (~3 days). The ML workload that dominates is event-detector training, which has two distinct access patterns: (a) "load all instances of event class N" and (b) "load one specific Instance for visualization or single-window training." Petrodb is published as static Parquet files behind Cloudflare with a soft per-file size target of 50 MB (CONTEXT.md `Argentina dataset — pre-publish validation` rule 6).

## Decision

Publish `observations/` as `observations/event_class=N/<instance_id>.parquet` — hive-partitioned by `event_class` only, with one file per Instance preserving upstream's per-instance file boundaries. Inside each file, in addition to the 30 upstream columns, store `instance_id`, `well_id`, `well_kind` as constant columns (RLE-encoded, negligible cost) so the dataset stays self-describing under any future restructuring.

## Considered alternatives

- **Single coalesced `observations.parquet`** with row-group sort on `(event_class, instance_id, timestamp)`. Best for corpus-wide aggregate scans; rejected because the 1.74 GB single file busts the per-file cache target and a cold CDN miss serves the entire file even when DuckDB only needs a row-group range.
- **Hive on `event_class` only, coalesced within partition** (10 files, ~50–500 MB each). Rejected: partition 0 (NORMAL, 594 instances) alone is hundreds of MB; busts the cache target; also discards the per-Instance file boundary, which is the natural unit of the ML workload.
- **Hive on `(event_class × well_id)`** (~100–150 partitions of ~10–20 MB). Fits the cache target and is efficient for combined class+well filters, but the dominant pattern is single-Instance fetch — pulling a 15 MB partition to read a 0.5 MB Instance is wasted bandwidth and worse cold-start latency.
- **Thin mirror of upstream** (`dataset/N/*.parquet`). Rejected: leaves `well_id`, `event_class`, `well_kind`, `instance_id` encoded only in filenames and directory names, requiring tribal knowledge to query. Contradicts petrodb's mission of clean, non-redundant relational schemas (CONTEXT.md, line 3).

## Consequences

- Corpus-wide aggregate scans require 2,228 parallel HTTP requests rather than a single large GET. DuckDB httpfs handles this concurrently, and the catalog tables (`instances.parquet`, `wells.parquet`, `event_types.parquet`) answer most aggregate questions without touching `observations/` at all.
- The published URL space is committed: `observations/event_class=N/<instance_id>.parquet` becomes part of the public API. Reorganizing later breaks consumers.
- Adding `instance_id` / `well_id` / `well_kind` as constant columns means future coalescing (if ever needed) is a transparent operation — no schema migration for downstream consumers.
