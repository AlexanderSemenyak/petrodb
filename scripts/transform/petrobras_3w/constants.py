"""Pinning + upstream identity for the Petrobras 3W pipeline.

The pin separates two upstream version namespaces (see ADR-0002):

- `PIN_GIT_TAG` — what `git clone --branch` accepts. Bytes-stable.
- `PIN_DATASET_VERSION` — the data-shape semver from `dataset/README.md`.
  This is what consumers care about; the git tag is the mechanism that
  delivers it byte-stably.

Both values are emitted in the validation log so a consumer can verify
which upstream snapshot backs the published data.
"""

UPSTREAM_REPO_URL = "https://github.com/petrobras/3W.git"
PIN_GIT_TAG = "v.1.70.0"
PIN_DATASET_VERSION = "2.0.0"

UPSTREAM_DATASET_INI_RELPATH = "dataset/dataset.ini"

# Public base URL where the dataset is served (Caddy → mounted parquet/ tree).
# The Observations hive partition by `event_class` is fixed by ADR-0001, so
# every Instance's published URL is fully determined here — `instances.parquet`
# materialises this as `source_url` even before the Observations files exist.
PUBLIC_BASE_URL = "https://dev-petrodb.ocortez.com/petrobras_3w"
