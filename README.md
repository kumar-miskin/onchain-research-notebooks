# On-chain Research Notebooks

Reproducible utilities and analyses for public Bitcoin on-chain data. The first module aligns daily on-chain observations with market prices without silently leaking future information.

## First research question

How sensitive is a valuation conclusion to publication lag? An on-chain observation dated Monday may not have been usable at Monday's close. `asof.py` shifts feature availability by a configurable lag before backward as-of joining to price data.

```bash
python -m onchain_research.asof \
  --prices data/example_prices.csv \
  --features data/example_features.csv \
  --lag-days 1 \
  --out aligned.csv
```

## Input contracts

Prices: `timestamp,close`. Features: `timestamp,value`. Timestamps must include a timezone or are interpreted as UTC. The output retains `feature_observed_at` and `feature_available_at` so the alignment can be audited.

## Research rules

- Record the exact source URL, metric definition, license, retrieval time, and revisions policy.
- Never equate address counts with user counts.
- Treat entity-adjusted metrics as vendor models, not raw facts.
- Separate observation time from availability time.
- Do not infer causality from same-period correlation.

This repository uses public or synthetic data only.
