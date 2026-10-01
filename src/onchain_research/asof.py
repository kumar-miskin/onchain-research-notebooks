from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from math import isfinite


def _utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True)


def align_asof(prices: pd.DataFrame, features: pd.DataFrame, lag_days: int = 1, max_age_days: int | None = None) -> pd.DataFrame:
    """Join each price to one available observation, rejecting ambiguous inputs.

    A duplicate timestamp with different values has no deterministic meaning
    under merge_asof: whichever row happens to sort last silently wins. A null
    value in a later release can similarly hide an earlier valid observation.
    Reject both rather than manufacturing an apparently point-in-time result.
    max_age_days optionally expires releases after that many elapsed days
    since availability (inclusive), without dropping the price observation.
    """
    if isinstance(lag_days, bool) or not isinstance(lag_days, int) or lag_days < 0:
        raise ValueError("lag_days must be a non-negative integer")
    if max_age_days is not None and (isinstance(max_age_days, bool) or not isinstance(max_age_days, int) or max_age_days < 0):
        raise ValueError("max_age_days must be a non-negative integer or None")
    if prices.empty or features.empty:
        raise ValueError("price and feature tables must not be empty")
    for name, frame, required in (
        ("prices", prices, ("timestamp", "close")),
        ("features", features, ("timestamp", "value")),
    ):
        missing = set(required) - set(frame.columns)
        if missing:
            raise ValueError(f"{name} missing columns: {', '.join(sorted(missing))}")
        if frame["timestamp"].isna().any() or frame["timestamp"].duplicated().any():
            raise ValueError(f"{name} has null or duplicate timestamps")
        measure = required[1]
        if frame[measure].isna().any():
            raise ValueError(f"{name} has null {measure} values")
        measure_values = pd.to_numeric(frame[measure], errors="coerce")
        if measure_values.isna().any() or not measure_values.map(isfinite).all():
            raise ValueError(f"{name} has non-finite or non-numeric {measure} values")
    p = prices.assign(timestamp=_utc(prices.timestamp)).sort_values("timestamp")
    f = features.assign(feature_observed_at=_utc(features.timestamp)).drop(columns="timestamp")
    if p.timestamp.isna().any() or f.feature_observed_at.isna().any():
        raise ValueError("parsed timestamps must not be null")
    if p.timestamp.duplicated().any() or f.feature_observed_at.duplicated().any():
        raise ValueError("price or feature timestamps duplicate after normalization")
    f["feature_available_at"] = f.feature_observed_at + pd.Timedelta(days=lag_days)
    f = f.sort_values("feature_available_at")
    return pd.merge_asof(
        p, f, left_on="timestamp", right_on="feature_available_at",
        direction="backward",
        tolerance=None if max_age_days is None else pd.Timedelta(days=max_age_days),
    )


def check_inputs(prices: Path, features: Path, lag_days: int) -> None:
    """Validate both inputs against their manifests before a rerun."""
    from onchain_research.manifest import ManifestError, validate
    validate(prices)
    fm = validate(features)
    if fm["availability_lag_days"] != lag_days:
        raise ManifestError(
            f"--lag-days {lag_days} disagrees with the recorded availability lag "
            f"({fm['availability_lag_days']} days) for {features.name}"
        )


def main(argv: list[str] | None = None) -> None:
    p=argparse.ArgumentParser(); p.add_argument("--prices", type=Path, required=True); p.add_argument("--features", type=Path, required=True); p.add_argument("--lag-days", type=int, default=1); p.add_argument("--out", type=Path, required=True)
    p.add_argument("--max-age-days", type=int, help="maximum elapsed days since feature availability, inclusive; default has no expiry")
    p.add_argument("--check-manifests", action="store_true", help="validate inputs against their .manifest.json files first")
    a=p.parse_args(argv)
    if a.check_manifests: check_inputs(a.prices, a.features, a.lag_days)
    align_asof(pd.read_csv(a.prices), pd.read_csv(a.features), a.lag_days, a.max_age_days).to_csv(a.out,index=False)

if __name__ == "__main__": main()
