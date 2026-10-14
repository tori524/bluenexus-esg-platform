import pandas as pd
import pytest
from period_data import prepare, select_period, aggregate, matching_periods
from calculations import calculate

def test_quarterly_period_and_ratio():
    df=pd.DataFrame({"plant":["A","A"],"date":["2026-01-01","2026-04-01"],"influent_m3":[100,300],"treated_m3":[75,240],"electricity_kwh":[90,300]})
    x,c=select_period(prepare(df,"Quarterly"),"A","2026-01-01","2026-06-30","Quarterly")
    assert c["missing"]==0
    d=aggregate(x)
    r={r.kpi_id:r.value for r in calculate(d)}
    assert r["W03"]==pytest.approx(78.75)
    assert r["E02"]==pytest.approx(390/315)

def test_quarterly_missing_and_partial_rejected():
    df=pd.DataFrame({"date":["2026-01-01"],"influent_m3":[100],"treated_m3":[75],"electricity_kwh":[90]})
    x=prepare(df,"Quarterly")
    _,c=select_period(x,"Client facility","2026-01-01","2026-06-30","Quarterly")
    assert c["missing"]==1
    with pytest.raises(ValueError):select_period(x,"Client facility","2026-01-02","2026-03-31","Quarterly")

def test_quality_is_average_not_sum():
    df=pd.DataFrame({"date":["2026-07-01","2026-07-02"],"influent_m3":[100,100],"treated_m3":[75,75],"electricity_kwh":[100,100],"ph_in":[8,9]})
    a=aggregate(prepare(df,"Daily"))
    assert a["ph_in"]==8.5

def test_baseline_is_volume_normalised():
    d={"influent_m3":200,"treated_m3":150,"electricity_kwh":120,"baseline_treated_m3":100,"baseline_electricity_kwh":100}
    r={x.kpi_id:x.value for x in calculate(d)}
    assert r["E03"]==150
    assert r["E04"]==30

def test_reclaimed_share_requires_supply():
    d={"influent_m3":100,"treated_m3":75,"reclaimed_m3":40,"electricity_kwh":80,"total_water_supply_m3":200}
    r={x.kpi_id:x.value for x in calculate(d)}
    assert r["W10"]==20
    d.pop("total_water_supply_m3")
    r={x.kpi_id:x.value for x in calculate(d)}
    assert r["W10"] is None
