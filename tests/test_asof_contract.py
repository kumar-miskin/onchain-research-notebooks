import pandas as pd
import pytest

from onchain_research.asof import align_asof


PRICES = pd.DataFrame({'timestamp': ['2026-01-01T00:00:00Z', '2026-01-02T00:00:00Z'], 'close': [100, 110]})
FEATURES = pd.DataFrame({'timestamp': ['2026-01-01T00:00:00Z'], 'value': [7]})


@pytest.mark.parametrize('bad', [
    pd.DataFrame({'timestamp': ['2026-01-01T00:00:00Z'] * 2, 'value': [7, 8]}),
    pd.DataFrame({'timestamp': ['not-a-date'], 'value': [7]}),
    pd.DataFrame({'timestamp': ['2026-01-01T00:00:00Z'], 'value': [float('nan')]}),
])
def test_bad_feature_timestamps_or_values_fail(bad):
    with pytest.raises(ValueError):
        align_asof(PRICES, bad)


def test_null_feature_value_does_not_leak_future_or_shadow_previous_release():
    f = pd.DataFrame({'timestamp': ['2026-01-01T00:00:00Z', '2026-01-02T00:00:00Z'],
                      'value': [7., float('nan')]})
    with pytest.raises(ValueError, match='null'):
        align_asof(PRICES, f)


def test_empty_feature_table_and_duplicate_price_timestamp_fail():
    with pytest.raises(ValueError, match='empty'):
        align_asof(PRICES, FEATURES.iloc[:0])
    with pytest.raises(ValueError, match='duplicate'):
        align_asof(pd.concat([PRICES, PRICES.iloc[[0]]]), FEATURES)
