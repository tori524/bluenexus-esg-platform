import pandas as pd
import pytest
from period_data import prepare,select_period,aggregate,matching_periods
from calculations import calculate

def test_daily_monthly_aggregation_consistent():
    daily=pd.DataFrame({'plant':['A']*2,'date':['2026-07-01','2026-07-02'],'influent_m3':[100,300],'treated_m3':[70,240],'electricity_kwh':[90,300]})
    monthly=pd.DataFrame({'plant':['A'],'date':['2026-07'],'influent_m3':[400],'treated_m3':[310],'electricity_kwh':[390]})
    d=aggregate(select_period(prepare(daily,'Daily'),'A','2026-07-01','2026-07-02','Daily')[0])
    m=aggregate(select_period(prepare(monthly,'Monthly'),'A','2026-07-01','2026-07-31','Monthly')[0])
    assert d['influent_m3']==m['influent_m3']==400
    assert d['treated_m3']==m['treated_m3']==310
    for v in (d,m):
        result={r.kpi_id:r.value for r in calculate(v)}
        assert result['W03']==pytest.approx(77.5)
        assert result['E02']==pytest.approx(390/310)

def test_missing_records_are_flagged():
    df=pd.DataFrame({'date':['2026-07-01'],'influent_m3':[100],'treated_m3':[75],'electricity_kwh':[100]})
    _,coverage=select_period(prepare(df,'Daily'),'Client facility','2026-07-01','2026-07-03','Daily')
    assert coverage['missing']==2

def test_historical_matching_dates():
    assert matching_periods({'start':pd.Timestamp('2026-07-01'),'end':pd.Timestamp('2026-08-31')},{'start':pd.Timestamp('2025-07-01'),'end':pd.Timestamp('2025-08-31')})
    assert not matching_periods({'start':pd.Timestamp('2026-07-01'),'end':pd.Timestamp('2026-08-31')},{'start':pd.Timestamp('2025-01-01'),'end':pd.Timestamp('2025-12-31')})
