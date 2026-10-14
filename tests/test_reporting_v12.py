from calculations import calculate
from reporting import build_priority_kpis,build_further_recommendations,reporting_draft,COLUMNS

def test_unified_columns_and_mapping():
    r=calculate({'influent_m3':100,'treated_m3':75,'electricity_kwh':100,'grid_ef_kgco2e_kwh':0.4})
    priority=build_priority_kpis(r)
    further=build_further_recommendations()
    assert list(priority.columns)==COLUMNS
    assert list(further.columns)==COLUMNS
    assert len(priority[['Category','KPI']].drop_duplicates())==len(priority)
    row=priority.loc[priority.KPI=='Electricity consumption'].iloc[0]
    assert row['Standard / Disclosure']=='GRI 302-1 (2016)'
    assert row['Result']=='100.00 kWh'
    assert 'boundary' in row['More Data Needed'].lower()
    assert 'WASH' in further.KPI.to_string()

def test_missing_data_explained():
    r=calculate({'influent_m3':100,'treated_m3':75})
    table=build_priority_kpis(r)
    row=table.loc[table.KPI=='Electricity consumption'].iloc[0]
    assert row['Result']=='Pending'
    assert row['Status']=='Data Required'
    assert 'electricity_kwh' in row['More Data Needed']
    report=reporting_draft('Client','2026',r,True)
    assert 'Further reporting recommendations' in report
