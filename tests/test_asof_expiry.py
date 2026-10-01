import pandas as pd
import pytest
from onchain_research.asof import align_asof, main


def frames():
    prices=pd.DataFrame({'timestamp':['2026-01-01T00:00:00Z','2026-01-02T00:00:00Z','2026-01-04T00:00:00Z','2026-01-04T00:00:01Z'], 'close':[100,101,102,103]})
    features=pd.DataFrame({'timestamp':['2026-01-01T00:00:00Z'], 'value':[7]})
    return prices,features


def test_expiry_is_inclusive_and_measured_from_availability():
    p,f=frames()
    got=align_asof(p,f,lag_days=1,max_age_days=2)
    assert pd.isna(got.loc[0,'value'])
    assert got.loc[1,'value']==7
    assert got.loc[2,'value']==7
    assert got.loc[3,['value','feature_observed_at','feature_available_at']].isna().all()


def test_zero_age_matches_only_exact_available_time():
    p,f=frames()
    got=align_asof(p,f,lag_days=1,max_age_days=0)
    assert got.value.notna().tolist()==[False,True,False,False]


def test_default_preserves_no_expiry():
    p,f=frames()
    assert align_asof(p,f).value.notna().tolist()==[False,True,True,True]


@pytest.mark.parametrize('age',[-1,True,1.5,'2'])
def test_invalid_age_is_rejected(age):
    with pytest.raises(ValueError,match='max_age_days'):
        align_asof(*frames(),max_age_days=age)


def test_cli_wires_expiry(tmp_path):
    p,f=frames()
    prices=tmp_path/'prices.csv';features=tmp_path/'features.csv';out=tmp_path/'out.csv'
    p.to_csv(prices,index=False);f.to_csv(features,index=False)
    main(['--prices',str(prices),'--features',str(features),'--out',str(out),'--max-age-days','0'])
    got=pd.read_csv(out)
    assert got.value.notna().tolist()==[False,True,False,False]
