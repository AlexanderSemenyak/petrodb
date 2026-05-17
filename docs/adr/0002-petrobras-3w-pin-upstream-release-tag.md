# Pin Petrobras 3W upstream to a release tag, not `main`

**Status:** accepted

## Context

Petrobras 3W uses semantic versioning (`VERSIONING.md` upstream). Past minor releases have reshaped instance contents in-place: 1.1.0 added/removed instances, adjusted expert labels, and corrected historian-tag misconfigurations that retroactively changed sensor values. The same `instance_id` can therefore have different bytes between upstream commits, with no rename or URL change to signal it. Petrodb publishes parquet at stable URLs, so silently-changing bytes would propagate as silently-changing training data to downstream consumers.

## Decision

The Petrobras 3W pipeline reads from a pinned upstream release tag (currently `v2.0.0`). Refreshes are event-driven (when upstream cuts a new tag and we've reviewed the release notes), not calendar-driven. The current pinned tag is recorded in `parquet/petrobras_3w/README.md` and emitted in the pipeline's validation logs.

## Considered alternatives

- **Track upstream `main`.** Rejected — re-pulling at any time risks silently mutating already-published `instance_id`s (sensor-value corrections, label adjustments). Consumers relying on bytes-stable URLs would observe non-reproducible behaviour.
- **Pin to a commit SHA.** Strongest reproducibility, but upstream cuts release tags deliberately at coherent dataset states; an arbitrary SHA boundary is harder to reason about and harder to compare against the release notes. The marginal reproducibility gain over a tag is small enough not to justify the extra friction.

## Consequences

- Pre-publish validation rule 7 (real-Well coverage equals upstream's stated count) implicitly enforces the pin — an accidental tag change shows up as a row-count mismatch, not a silent corruption.
- Petrodb's release cadence for this dataset is bounded above by upstream's release cadence. If upstream goes dormant we publish stale data; that's acceptable for the reproducibility guarantee it buys.
- The pinned tag is part of the dataset's published metadata; bumping it is a deliberate, reviewable action with release-note context, not an automated refresh.
