from calculations import calculate, aggregate_daily
import pandas as pd

def get(rows, id):
    return next(r.value for r in rows if r.kpi_id==id)

def test_core():
    d=dict(influent_m3=120000,treated_m3=90000,electricity_kwh=120000,
           baseline_treated_m3=100000,baseline_electricity_kwh=150000,
           grid_ef_kgco2e_kwh=.4,chemicals_kg={'NaOH':900},baseline_chemicals_kg={'NaOH':1200})
    r=calculate(d)
    assert get(r,'W03')==75
    assert abs(get(r,'E02')-4/3)<1e-10
    assert get(r,'E03')==135000
    assert get(r,'E04')==15000
    assert get(r,'C01')==48
    assert get(r,'C03')==6
    assert abs(get(r,'AI02:NaOH')-180)<1e-10

def test_missing_is_not_zero():
    r=calculate({'influent_m3':100,'treated_m3':75})
    assert get(r,'E01') is None
    assert get(r,'C01') is None

def test_aggregate():
    df=pd.DataFrame({'date':['2026-01-01','2026-01-02'],'influent_m3':[100,200],
                     'treated_m3':[75,150],'electricity_kwh':[100,200]})
    assert aggregate_daily(df)['treated_m3']==225

from sample_adapter import prepare_upload,filter_upload,data_quality_summary
from reporting import build_disclosure_index

def test_bluenexus_upload_mapping_and_filter():
    x=pd.DataFrame({'plant':['Plant A','Plant B','Plant A'], 'date':['2026-07-01','2026-07-01','2026-07-02'],
        'influent_volume_m3':[100,200,110], 'effluent_volume_m3':[75,150,80],
        'daily_electricity_kwh':[120,240,130], 'influent_conductivity_us_cm':['/','2000','1900']})
    mapped=prepare_upload(x)
    selected=filter_upload(mapped,'Plant A','2026-07-01','2026-07-02')
    assert len(selected)==2
    assert aggregate_daily(selected)['electricity_kwh']==250
    assert aggregate_daily(selected)['conductivity_in_us_cm'] is None
    assert int(data_quality_summary(selected).loc[lambda d:d.Field=='conductivity_in_us_cm','Missing records'].iloc[0])==1

def test_disclosure_gap_and_scenario():
    r=calculate({'influent_m3':100,'treated_m3':75,'electricity_kwh':100,
        'baseline_treated_m3':100,'baseline_electricity_kwh':200})
    idx=build_disclosure_index(r)
    assert idx.loc[idx.Standard=='GRI 303-3','Readiness'].iloc[0]=='Additional data required'
    assert get(r,'E04')==50
