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

## Point-in-time manifests

On-chain series are revised when address labels, entity clustering or vendor methodology change, so a URL and a date cannot reproduce a result. Every input CSV has a `<file>.manifest.json` beside it recording the file's SHA-256, row count and columns, source URL and metric id, UTC retrieval time, observation timezone and frequency, the availability lag assumed, the series kind, methodology version and transformation steps.

```bash
python -m onchain_research.manifest write data/example_features.csv \
  --source-url 'synthetic://onchain-research-notebooks/example_features' \
  --metric-id synthetic_daily_value --retrieved-at 2026-09-21T00:00:00Z \
  --frequency daily --availability-lag-days 1 --series-kind raw

python -m onchain_research.manifest validate data/*.csv
python -m onchain_research.asof --check-manifests --lag-days 1 \
  --prices data/example_prices.csv --features data/example_features.csv --out aligned.csv
```

A rerun with `--check-manifests` fails if a file's bytes or row count changed, a required field is missing, or `--lag-days` disagrees with the recorded availability lag. The aligned output keeps both `feature_observed_at` and `feature_available_at`.

`series_kind` is one of:

- `raw`: address-level or block-level observations computed directly from the chain (for example, count of addresses with a non-zero balance). These are observations about addresses, not people.
- `entity_adjusted`: counts after a clustering heuristic groups addresses into entities. The heuristic is a model and changes over time; record its version.
- `vendor_modeled`: vendor estimates such as realized-cap variants or exchange-flow labels, which depend on proprietary labels and can be restated retroactively.

The CSVs are stored with `-text` in `.gitattributes` so line-ending conversion cannot change their checksums.

## Research rules

- Record the exact source URL, metric definition, license, retrieval time, and revisions policy.
- Never equate address counts with user counts.
- Treat entity-adjusted metrics as vendor models, not raw facts.
- Separate observation time from availability time.
- Do not infer causality from same-period correlation.

This repository uses public or synthetic data only.
