"""Point-in-time manifests for analysis inputs.

On-chain series get revised when address labels, entity clustering or vendor
methodology change. A download URL and a date are not enough to rerun a study
later, so every input file gets a JSON manifest beside it that pins the exact
bytes (SHA-256) and the assumptions needed to use it without look-ahead.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

MANIFEST_VERSION = 1
SERIES_KINDS = ("raw", "entity_adjusted", "vendor_modeled")
FREQUENCIES = ("daily", "hourly", "block")
REQUIRED_FIELDS = (
    "manifest_version", "file", "sha256", "row_count", "columns",
    "source_url", "metric_id", "retrieved_at", "observation_timezone",
    "frequency", "availability_lag_days", "series_kind",
)


class ManifestError(ValueError):
    """Raised when an input file no longer matches its manifest."""


@dataclass(frozen=True)
class Manifest:
    file: str
    sha256: str
    row_count: int
    columns: list[str]
    source_url: str
    metric_id: str
    retrieved_at: str
    observation_timezone: str
    frequency: str
    availability_lag_days: int
    series_kind: str
    methodology_version: str | None = None
    transformations: list[str] = field(default_factory=list)
    manifest_version: int = MANIFEST_VERSION


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_path(data_path: Path) -> Path:
    return data_path.with_name(data_path.name + ".manifest.json")


def _utc_iso(ts: str | datetime) -> str:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        raise ManifestError(f"retrieved_at must include a timezone: {ts!r}")
    return t.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_values(d: dict) -> None:
    missing = [k for k in REQUIRED_FIELDS if d.get(k) in (None, "")]
    if missing:
        raise ManifestError(f"manifest missing required fields: {', '.join(missing)}")
    if d["series_kind"] not in SERIES_KINDS:
        raise ManifestError(f"series_kind must be one of {SERIES_KINDS}, got {d['series_kind']!r}")
    if d["frequency"] not in FREQUENCIES:
        raise ManifestError(f"frequency must be one of {FREQUENCIES}, got {d['frequency']!r}")
    lag = d["availability_lag_days"]
    if isinstance(lag, bool) or not isinstance(lag, int) or lag < 0:
        raise ManifestError("availability_lag_days must be a non-negative integer")
    if d["manifest_version"] != MANIFEST_VERSION:
        raise ManifestError(f"unsupported manifest_version {d['manifest_version']!r}")


def build_manifest(
    data_path: Path, *, source_url: str, metric_id: str, retrieved_at: str | datetime,
    observation_timezone: str, frequency: str, availability_lag_days: int, series_kind: str,
    methodology_version: str | None = None, transformations: list[str] | None = None,
) -> Manifest:
    data_path = Path(data_path)
    frame = pd.read_csv(data_path)
    m = Manifest(
        file=data_path.name, sha256=sha256_file(data_path), row_count=len(frame),
        columns=list(frame.columns), source_url=source_url, metric_id=metric_id,
        retrieved_at=_utc_iso(retrieved_at), observation_timezone=observation_timezone,
        frequency=frequency, availability_lag_days=availability_lag_days, series_kind=series_kind,
        methodology_version=methodology_version, transformations=list(transformations or []),
    )
    _check_values(asdict(m))
    return m


def write_manifest(data_path: Path, manifest: Manifest) -> Path:
    out = manifest_path(Path(data_path))
    out.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n")
    return out


def load_manifest(data_path: Path) -> dict:
    mpath = manifest_path(Path(data_path))
    if not mpath.exists():
        raise ManifestError(f"no manifest for {data_path} (expected {mpath.name})")
    return json.loads(mpath.read_text())


def validate(data_path: Path) -> dict:
    """Check that data_path still matches its manifest; return the manifest."""
    data_path = Path(data_path)
    d = load_manifest(data_path)
    _check_values(d)
    if d["file"] != data_path.name:
        raise ManifestError(f"manifest describes {d['file']!r}, not {data_path.name!r}")
    digest = sha256_file(data_path)
    if digest != d["sha256"]:
        raise ManifestError(
            f"{data_path.name} changed since it was recorded "
            f"(sha256 {digest[:12]} != manifest {d['sha256'][:12]}); re-record the source before rerunning"
        )
    rows = len(pd.read_csv(data_path))
    if rows != d["row_count"]:
        raise ManifestError(f"{data_path.name} has {rows} rows, manifest says {d['row_count']}")
    return d


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m onchain_research.manifest")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write", help="record a manifest beside a CSV input")
    w.add_argument("data", type=Path)
    w.add_argument("--source-url", required=True)
    w.add_argument("--metric-id", required=True)
    w.add_argument("--retrieved-at", help="ISO timestamp with timezone (default: now, UTC)")
    w.add_argument("--observation-timezone", default="UTC")
    w.add_argument("--frequency", choices=FREQUENCIES, required=True)
    w.add_argument("--availability-lag-days", type=int, required=True)
    w.add_argument("--series-kind", choices=SERIES_KINDS, required=True)
    w.add_argument("--methodology-version")
    w.add_argument("--transformation", action="append", default=[])
    v = sub.add_parser("validate", help="fail if a CSV no longer matches its manifest")
    v.add_argument("data", type=Path, nargs="+")
    a = p.parse_args(argv)
    if a.cmd == "write":
        retrieved = a.retrieved_at or datetime.now(timezone.utc)
        m = build_manifest(
            a.data, source_url=a.source_url, metric_id=a.metric_id, retrieved_at=retrieved,
            observation_timezone=a.observation_timezone, frequency=a.frequency,
            availability_lag_days=a.availability_lag_days, series_kind=a.series_kind,
            methodology_version=a.methodology_version, transformations=a.transformation,
        )
        print(write_manifest(a.data, m))
    else:
        for path in a.data:
            validate(path)
            print(f"ok {path}")


if __name__ == "__main__":
    main()
