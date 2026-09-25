import json
import shutil
from pathlib import Path

import pytest

from onchain_research.asof import check_inputs
from onchain_research.manifest import (
    ManifestError, build_manifest, manifest_path, validate, write_manifest,
)

DATA = Path(__file__).resolve().parents[1] / "data"
KW = dict(
    source_url="synthetic://test", metric_id="m", retrieved_at="2026-09-21T09:30:00+02:00",
    observation_timezone="UTC", frequency="daily", availability_lag_days=1, series_kind="raw",
)


@pytest.fixture
def csv(tmp_path):
    p = tmp_path / "features.csv"
    p.write_text("timestamp,value\n2026-01-01T00:00:00Z,1.0\n2026-01-02T00:00:00Z,2.0\n")
    return p


def test_manifest_is_deterministic(csv):
    a = write_manifest(csv, build_manifest(csv, **KW)).read_bytes()
    b = write_manifest(csv, build_manifest(csv, **KW)).read_bytes()
    assert a == b
    d = json.loads(a)
    assert d["row_count"] == 2 and d["columns"] == ["timestamp", "value"]
    assert d["retrieved_at"] == "2026-09-21T07:30:00Z"


def test_changed_checksum_fails(csv):
    write_manifest(csv, build_manifest(csv, **KW))
    csv.write_text(csv.read_text().replace("2.0", "2.5"))
    with pytest.raises(ManifestError, match="changed since it was recorded"):
        validate(csv)


def test_missing_manifest_fails(csv):
    with pytest.raises(ManifestError, match="no manifest"):
        validate(csv)


@pytest.mark.parametrize("field", ["availability_lag_days", "source_url", "series_kind", "retrieved_at"])
def test_missing_required_field_fails(csv, field):
    write_manifest(csv, build_manifest(csv, **KW))
    mp = manifest_path(csv)
    d = json.loads(mp.read_text())
    del d[field]
    mp.write_text(json.dumps(d))
    with pytest.raises(ManifestError, match=field):
        validate(csv)


def test_rejects_unknown_series_kind_and_naive_timestamp(csv):
    with pytest.raises(ManifestError, match="series_kind"):
        build_manifest(csv, **{**KW, "series_kind": "cleaned"})
    with pytest.raises(ManifestError, match="timezone"):
        build_manifest(csv, **{**KW, "retrieved_at": "2026-09-21T09:30:00"})


def test_lag_mismatch_blocks_rerun(tmp_path):
    for name in ("example_prices.csv", "example_features.csv"):
        shutil.copy(DATA / name, tmp_path / name)
        shutil.copy(manifest_path(DATA / name), manifest_path(tmp_path / name))
    check_inputs(tmp_path / "example_prices.csv", tmp_path / "example_features.csv", 1)
    with pytest.raises(ManifestError, match="disagrees"):
        check_inputs(tmp_path / "example_prices.csv", tmp_path / "example_features.csv", 0)


def test_shipped_examples_match_their_manifests():
    for name in ("example_prices.csv", "example_features.csv"):
        assert validate(DATA / name)["series_kind"] == "raw"
