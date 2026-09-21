import pandas as pd
from onchain_research.asof import align_asof


def test_future_feature_is_not_leaked():
    prices=pd.DataFrame({"timestamp":["2026-01-01T00:00:00Z","2026-01-02T00:00:00Z"],"close":[100,110]})
    features=pd.DataFrame({"timestamp":["2026-01-01T00:00:00Z"],"value":[7]})
    got=align_asof(prices,features,lag_days=1)
    assert pd.isna(got.loc[0,"value"])
    assert got.loc[1,"value"] == 7
