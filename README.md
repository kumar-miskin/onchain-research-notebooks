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

Prices: `timestamp,close`. Features: `timestamp,value`. Timestamps must include a timezone or are interpreted as UTC. The output retains `feature_observed_at` and `feature_available_at` so the alignment can be audited. Input rows with duplicate or null timestamps, null, infinite, or non-numeric price/feature values, or invalid lags are rejected: a later null release must not silently shadow a usable earlier value, and ties must not arbitrarily select one of two revisions. Unmatched prices before the first release remain unpaired in the output.

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

A rerun with `--check-manifests` fails if a file's bytes or row count changed, a required field is missing, or `--lag-days` disagrees with the recorded availability lag.

Writing or validating a manifest also checks the data against its own declaration: timestamps must parse, be unique, and align to the declared frequency boundaries in the declared `observation_timezone` (midnight local for `daily`, the top of the hour for `hourly`; `block` series are not wall-clock regular and skip the alignment check). An unknown timezone name is rejected. A manifest that says "daily, UTC" beside hourly rows, or beside rows stamped at midnight in another timezone, fails instead of silently changing what the availability lag means. Local-midnight series remain valid across daylight-saving transitions. The aligned output keeps both `feature_observed_at` and `feature_available_at`.

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

### Expire stale feature releases

An as-of join can carry an old feature indefinitely when a source stops
publishing. Set `--max-age-days N` to accept a release only within N elapsed
24-hour days of its `feature_available_at` time, inclusive. For example,
`--lag-days 1 --max-age-days 2` allows an observation one day after observation
and for two days after that release. The age is not measured from observation
itself and does not count local calendar days across DST. Zero requires an
exact availability-time match. Negative, fractional and boolean API values
are rejected. The default is no expiry for backward compatibility.

Expired rows keep their price but have missing feature value and provenance
columns, just like rows before the first release. They must not be treated as
zero or forward-filled back into a usable signal. Choose the age limit from
the source's publication contract, not by optimizing a backtest.
