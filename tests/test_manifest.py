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


def _write(tmp_path, rows, name="series.csv"):
    p = tmp_path / name
    p.write_text("timestamp,value\n" + "".join(f"{t},{v}\n" for t, v in rows))
    return p


def test_hourly_rows_labeled_daily_fail(tmp_path):
    csv = _write(tmp_path, [("2026-01-01T00:00:00Z", 1.0), ("2026-01-01T06:00:00Z", 2.0)])
    with pytest.raises(ManifestError, match="aligned"):
        build_manifest(csv, **KW)


def test_dst_shortened_local_day_is_not_rejected(tmp_path):
    # America/New_York local midnights around spring forward are 23h apart.
    csv = _write(tmp_path, [("2026-03-07T05:00:00Z", 1.0), ("2026-03-08T05:00:00Z", 2.0),
                            ("2026-03-09T04:00:00Z", 3.0)])
    build_manifest(csv, **{**KW, "observation_timezone": "America/New_York"})


def test_daily_rows_off_midnight_fail(tmp_path):
    csv = _write(tmp_path, [("2026-01-01T09:30:00Z", 1.0), ("2026-01-02T09:30:00Z", 2.0)])
    with pytest.raises(ManifestError, match="aligned"):
        build_manifest(csv, **KW)


def test_local_midnight_matches_declared_timezone_not_utc(tmp_path):
    # Midnight in America/New_York is 05:00Z (EST). Declaring UTC must fail;
    # declaring America/New_York must pass.
    csv = _write(tmp_path, [("2026-01-01T05:00:00Z", 1.0), ("2026-01-02T05:00:00Z", 2.0)])
    with pytest.raises(ManifestError, match="aligned"):
        build_manifest(csv, **KW)
    build_manifest(csv, **{**KW, "observation_timezone": "America/New_York"})


def test_unknown_observation_timezone_fails(tmp_path):
    csv = _write(tmp_path, [("2026-01-01T00:00:00Z", 1.0)])
    with pytest.raises(ManifestError, match="observation_timezone"):
        build_manifest(csv, **{**KW, "observation_timezone": "Mars/Olympus"})


def test_block_frequency_skips_wall_clock_alignment(tmp_path):
    csv = _write(tmp_path, [("2026-01-01T03:17:41Z", 1.0), ("2026-01-01T03:19:02Z", 2.0)])
    build_manifest(csv, **{**KW, "frequency": "block"})


def test_duplicate_and_unparsable_timestamps_fail(tmp_path):
    dup = _write(tmp_path, [("2026-01-01T00:00:00Z", 1.0), ("2026-01-01T01:00:00+01:00", 2.0)])
    with pytest.raises(ManifestError, match="duplicate"):
        build_manifest(dup, **KW)
    bad = _write(tmp_path, [("not-a-date", 1.0)])
    with pytest.raises(ManifestError, match="unparsable"):
        build_manifest(bad, **KW)


def test_validate_also_checks_series_consistency(csv):
    write_manifest(csv, build_manifest(csv, **KW))
    # Data is stamped at UTC midnight: valid under UTC, not under New_York.
    mp = manifest_path(csv)
    d = json.loads(mp.read_text())
    d["observation_timezone"] = "America/New_York"
    mp.write_text(json.dumps(d))
    with pytest.raises(ManifestError, match="aligned"):
        validate(csv)


@pytest.mark.parametrize("frequency", ["daily", "hourly"])
@pytest.mark.parametrize("stamp", ["2026-01-01T00:00:00.500Z", "2026-01-01T00:00:00.000000001Z"])
def test_subsecond_rows_are_off_frequency_boundary(tmp_path, frequency, stamp):
    csv = _write(tmp_path, [(stamp, 1.0)])
    with pytest.raises(ManifestError, match="aligned"):
        build_manifest(csv, **{**KW, "frequency": frequency})
