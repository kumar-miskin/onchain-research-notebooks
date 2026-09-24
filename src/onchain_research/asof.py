from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd


def _utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True)


def align_asof(prices: pd.DataFrame, features: pd.DataFrame, lag_days: int = 1) -> pd.DataFrame:
    if lag_days < 0: raise ValueError("lag_days must be non-negative")
    p = prices.assign(timestamp=_utc(prices.timestamp)).sort_values("timestamp")
    f = features.assign(feature_observed_at=_utc(features.timestamp)).drop(columns="timestamp")
    f["feature_available_at"] = f.feature_observed_at + pd.Timedelta(days=lag_days)
    f = f.sort_values("feature_available_at")
    return pd.merge_asof(p, f, left_on="timestamp", right_on="feature_available_at", direction="backward")


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
    p.add_argument("--check-manifests", action="store_true", help="validate inputs against their .manifest.json files first")
    a=p.parse_args(argv)
    if a.check_manifests: check_inputs(a.prices, a.features, a.lag_days)
    align_asof(pd.read_csv(a.prices), pd.read_csv(a.features), a.lag_days).to_csv(a.out,index=False)

if __name__ == "__main__": main()
