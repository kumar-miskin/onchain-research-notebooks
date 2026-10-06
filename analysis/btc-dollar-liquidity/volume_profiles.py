"""Dollar-volume profiles from local, rights-cleared daily OHLCV CSV files.

No remote data collection. Required columns: date, close, volume.
BTC-USD volume must be reported USD notional; equities/funds must use
matching split-normalized close and share volume. Source rights are separate.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

MAG7 = ['AAPL', 'AMZN', 'GOOGL', 'META', 'MSFT', 'NVDA', 'TSLA']
FUNDS = ['IBIT', 'FBTC', 'GBTC', 'ARKB', 'BITB', 'HODL', 'BRRR',
         'BTCO', 'EZBC', 'BTCW', 'BTC']


def load_series(directory, symbol, asof):
    d = pd.read_csv(Path(directory) / f'{symbol}.csv', parse_dates=['date'])
    if d.date.duplicated().any():
        raise ValueError(f'Duplicate daily dates for {symbol}')
    d = d.set_index('date').sort_index().loc[:asof]
    if d[['close', 'volume']].isna().any().any():
        raise ValueError(f'Missing prices/volumes for {symbol}')
    if (d.volume < 0).any() or (d.close <= 0).any():
        raise ValueError(f'Invalid price/volume for {symbol}')
    d['usd_volume'] = d.volume if symbol == 'BTC-USD' else d.close * d.volume
    return d


def weekly_sum(series, asof):
    """Exclude incomplete first and last Monday-Sunday weeks."""
    first = series.index.min()
    start = first + pd.Timedelta(days=(7 - first.weekday()) % 7)
    end = pd.Timestamp(asof)
    complete_sunday = end - pd.Timedelta(days=(end.weekday() + 1) % 7)
    return series.loc[start:].resample('W-SUN').sum(min_count=1).loc[:complete_sunday]


def turns(sma, prices, lag=13, confirmation=4, cooldown=26):
    """Exploratory, analyst-selected rule. Never backdate confirmation."""
    slope = sma.diff(lag)
    crosses = (slope > 0) & (slope.shift(1) <= 0)
    events, last = [], None
    for cross in crosses[crosses].index:
        signal = cross + pd.Timedelta(weeks=confirmation-1)
        if signal not in slope.index or not (slope.loc[cross:signal] > 0).all():
            continue
        if last is not None and (signal-last).days < cooldown * 7:
            continue
        row = {'signal': str(signal.date()), 'price': prices.loc[signal]}
        for h in [4, 13, 26, 52]:
            t = signal + pd.Timedelta(weeks=h)
            row[f'return_{h}w_pct'] = ((prices.loc[t]/prices.loc[signal]-1)*100
                                      if t in prices.index else np.nan)
        events.append(row)
        last = signal
    return pd.DataFrame(events)


def analyze(source, output, asof):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    data = {s: load_series(source, s, asof)
            for s in ['BTC-USD', 'MSTR'] + MAG7 + FUNDS}
    b = data['BTC-USD']
    expected = pd.date_range(b.index.min(), b.index.max(), freq='D')
    if not b.index.equals(expected):
        raise ValueError('BTC daily coverage is incomplete. Do not zero-fill unknown missing data.')
    sessions = b.index
    for symbol in MAG7:
        sessions = sessions.intersection(data[symbol].index)
    sessions = sessions.sort_values()
    components = pd.DataFrame(index=sessions)
    components['BTC spot'] = b.usd_volume.reindex(sessions)
    components['Listed funds / GBTC trust'] = 0.0
    for symbol in FUNDS:
        d = data[symbol]
        missing = sessions[(sessions >= d.index.min()) & (~sessions.isin(d.index))]
        if len(missing):
            raise ValueError(f'Missing after-launch sessions for {symbol}: {missing}')
        components['Listed funds / GBTC trust'] += d.usd_volume.reindex(sessions).fillna(0)
    components['MSTR equity proxy'] = data['MSTR'].usd_volume.loc['2020-08-11':].reindex(sessions).fillna(0)
    components['Gross BTC-linked activity'] = components.sum(axis=1)
    weeks = {c: weekly_sum(components[c], asof) for c in components}
    for symbol in MAG7:
        components[symbol] = data[symbol].usd_volume.reindex(sessions)
        weeks[symbol] = weekly_sum(components[symbol], asof)
    components['Mag7 basket'] = components[MAG7].sum(axis=1)
    weeks['Mag7 basket'] = pd.concat([weeks[s] for s in MAG7], axis=1).sum(axis=1, min_count=7)
    # All comparisons begin on the same full week in BTC's coverage.
    first = components.index.min()
    first_monday = first + pd.Timedelta(days=(7-first.weekday()) % 7)
    first_sunday = first_monday + pd.Timedelta(days=6)
    averages = pd.DataFrame({s: w.loc[first_sunday:].rolling(200, min_periods=200).mean()
                             for s, w in weeks.items()})
    averages.to_csv(out / '200week_profiles.csv')
    components.rolling(200).mean().to_csv(out / '200session_profiles.csv')
    components.groupby(components.index.year).mean().to_csv(out / 'annual_component_means.csv')
    price = b.close.reindex(sessions).resample('W-SUN').last()
    btc_sma = averages['BTC spot'].dropna()
    for lag in [1, 13]:
        turns(btc_sma, price.loc[btc_sma.index], lag).to_csv(out / f'exploratory_turns_lag{lag}.csv', index=False)
    latest = averages.iloc[-1].rename('usd_per_week')
    latest.to_csv(out / 'latest_200week_snapshot.csv')
    print(latest / 1e9)
    print('First complete BTC 200w value:', btc_sma.first_valid_index())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--asof', required=True, help='Last completed daily date YYYY-MM-DD')
    args = parser.parse_args()
    analyze(args.input_dir, args.output_dir, args.asof)
