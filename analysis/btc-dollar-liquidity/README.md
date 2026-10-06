# BTC-linked dollar trading profiles

Analysis-only code for Macro Receipts Issue 2. It reads local OHLCV CSVs; it does not download data, embed secrets, redistribute raw histories or supply an automated Yahoo collector.

## Run

Install `pandas` and `numpy` in your own environment. Supply one rights-cleared CSV per ticker, named `<ticker>.csv`, with `date,close,volume`. Then:

```sh
python3 volume_profiles.py --input-dir /path/to/local/data --output-dir ./output --asof 2026-10-05
```

Tickers: BTC-USD, MSTR, AAPL, AMZN, GOOGL, META, MSFT, NVDA, TSLA; IBIT, FBTC, GBTC, ARKB, BITB, HODL, BRRR, BTCO, EZBC, BTCW, BTC. BTC is the Grayscale mini trust, not the cryptocurrency ticker BTC-USD. Source column semantics and instrument identities must be confirmed before use.

BTC volume is assumed already in USD. For shares, USD turnover is split-normalized Close x share Volume, an estimate at closing price. Do not use dividend-adjusted price or mismatched split units. All comparisons use the intersection of actual daily dates for the seven selected equity tickers and BTC. Bitcoin weekends and US equity holidays are excluded. Weekly sums cover only these matched sessions in complete Monday-Sunday weeks. The 200-week arithmetic mean needs 200 full weeks. Daily SMAs average the latest 200 matched sessions, never calendar-day zero-filled weekends. MSTR enters August 11, 2020; GBTC includes prior trust trading.

## Limits

The preparer must verify that all seven equity CSVs contain complete session calendars; their intersection is the common calendar. Missing sessions in all seven cannot be detected by the intersection alone. Missing after-launch fund dates on that calendar cause an error. BTC missing daily observations cause an error. Only pre-launch dates contribute zero; weekends and equity holidays do not enter the matched averages.

Gross BTC-linked activity adds spot, selected listed funds and MSTR share trading. This is not unique liquidity or net inflows. Hedge activity can overlap. MSTR has corporate equity effects. Derivatives, other companies, options and unlisted/global funds are excluded. This is a selected basket, not an exhaustive market.

The flip rule is exploratory: SMA exceeds its value 13 weeks ago for four readings; confirmed on the fourth reading; 26-week cooldown. The 1-week-slope alternative shows parameter sensitivity. Only three completed slower-rule episodes existed in this study. No out-of-sample predictive validity or trading recommendation is claimed. At each step, SMA change is (new week minus week exiting 200 weeks ago)/200.

## Data rights

The study used Yahoo Finance daily history, retrieved October 6, 2026. Yahoo and underlying data providers retain their rights. This package contains no raw data or bulk derived time series. Obtain lawful, appropriately licensed inputs independently. Source attribution is not permission. Yahoo's current terms restrict automated collection without prior permission and commercial reuse; this code does not authorize either. Review source terms before downloading, publishing charts, derived data or using results commercially.

- https://legal.yahoo.com/us/en/yahoo/terms/otos/
- https://legal.yahoo.com/us/en/yahoo/permissions/requests/index.html
- https://help.yahoo.com/kb/SLN2311.html

The author elected to publish attributed computed charts, acknowledging source restrictions. That decision is not a general data license for users of this code.

## Generate graphs

After generating local analysis tables, run:

```sh
python3 plot_profiles.py --input-dir ./output
```

This renders the actual-dollar 200-week comparison ($B/week, linear axis) and the stacked 200-week/200-session channel chart. It makes no network requests. Use appropriately licensed local inputs; no fetching instructions are included. Public charts should credit Yahoo Finance as the research source and state the retrieval date.
