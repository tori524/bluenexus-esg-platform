"""Canonical daily/monthly/quarterly data validation, coverage and aggregation."""
import calendar
import pandas as pd
from sample_adapter import RENAME

CHEMS=['NaOH','Antiscalant','Non-oxidizing biocide','Reducing agent','SDBS']
CHEM_COLS={'NaOH':'chemical_naoh_kg','Antiscalant':'chemical_antiscalant_kg','Non-oxidizing biocide':'chemical_biocide_kg','Reducing agent':'chemical_reducing_agent_kg','SDBS':'chemical_sdbs_kg'}
REQUIRED=['influent_m3','treated_m3','electricity_kwh']
SUM_FIELDS=REQUIRED+['reclaimed_m3','customer_m3','renewable_kwh','downtime_hours','manual_interventions','om_costs','freshwater_withdrawal_m3','total_water_supply_m3']+list(CHEM_COLS.values())
QUALITY=['conductivity_in_us_cm','conductivity_out_us_cm','ph_in','ph_out']

def prepare(df,frequency):
    if frequency not in ('Daily','Monthly','Quarterly'): raise ValueError('Select Daily, Monthly or Quarterly')
    x=df.copy().rename(columns=RENAME)
    if 'date' not in x: raise ValueError('Missing date column')
    x['date']=pd.to_datetime(x.date,errors='coerce')
    if x.date.isna().any(): raise ValueError('Invalid date entries')
    if 'plant' not in x: x['plant']='Client facility'
    x['plant']=x['plant'].fillna('Client facility').astype(str)
    if frequency=='Quarterly':
        x['period_key']=x.date.dt.to_period('Q').astype(str)
    elif frequency=='Monthly':
        # Monthly dates may be YYYY-MM or the first/last day of a month.
        x['period_key']=x.date.dt.to_period('M').astype(str)
    else:x['period_key']=x.date.dt.strftime('%Y-%m-%d')
    if x.duplicated(['plant','period_key']).any():raise ValueError('Duplicate facility/date or facility/month records')
    for col in SUM_FIELDS+QUALITY:
        if col in x:
            x[col]=pd.to_numeric(x[col].replace('/',pd.NA),errors='coerce')
            if x[col].dropna().lt(0).any():raise ValueError(f'{col}: negative values found')
    for col in REQUIRED:
        if col not in x:raise ValueError(f'Missing required field: {col}')
    return x

def select_period(df,plant,start,end,frequency):
    x=df.loc[df.plant.eq(plant)].copy()
    start,end=pd.Timestamp(start),pd.Timestamp(end)
    if start>end:raise ValueError('Start date must be before end date')
    if frequency=='Quarterly':
        if start != start.to_period('Q').start_time or end != end.to_period('Q').end_time.normalize():
            raise ValueError('Quarterly data requires complete calendar quarters.')
        x=x.loc[x.date.dt.to_period('Q').between(start.to_period('Q'),end.to_period('Q'))]
        expected=len(pd.period_range(start.to_period('Q'),end.to_period('Q'),freq='Q'))
    elif frequency=='Monthly':
        if start.day!=1 or end.day!=calendar.monthrange(end.year,end.month)[1]:
            raise ValueError('Monthly data requires full calendar months. Select first day to last day.')
        x=x.loc[x.date.dt.to_period('M').between(start.to_period('M'),end.to_period('M'))]
        expected=len(pd.period_range(start.to_period('M'),end.to_period('M'),freq='M'))
    else:
        x=x.loc[x.date.between(start,end)]
        expected=(end-start).days+1
    if x.empty:raise ValueError('No records in the selected period')
    observed=x.period_key.nunique()
    missing=max(0,expected-observed)
    return x,{'expected':expected,'observed':observed,'missing':missing,'coverage':observed/expected if expected else 0,'frequency':frequency,'start':start,'end':end}

def aggregate(df):
    out={}
    for field in SUM_FIELDS:
        if field not in df:continue
        col=pd.to_numeric(df[field],errors='coerce')
        out[field]=float(col.sum()) if col.notna().all() else None
    for field in QUALITY:
        if field not in df:continue
        col=pd.to_numeric(df[field],errors='coerce')
        # Period representative reading: weighted by sample counts if supplied.
        # pH arithmetic averages are descriptive, not a chemical mean or compliance test.
        weights=pd.to_numeric(df.get(field+'_sample_count',pd.Series(1,index=df.index)),errors='coerce')
        valid=col.notna() & weights.notna() & (weights>0)
        out[field]=float((col[valid]*weights[valid]).sum()/weights[valid].sum()) if valid.all() and valid.any() else None
    out['chemicals_kg']={name:out[col] for name,col in CHEM_COLS.items() if col in out and out[col] is not None}
    return out

def matching_periods(current,previous):
    a,b=current['start'],current['end'];c,d=previous['start'],previous['end']
    # Same calendar boundaries; leap-year shifts need explicit review.
    return (a.month,a.day,b.month,b.day)==(c.month,c.day,d.month,d.day) and a.year>c.year

def monthly_trend(df):
    x=df.copy();x['month']=x.date.dt.to_period('M').astype(str)
    fields=[f for f in SUM_FIELDS if f in x]
    return x.groupby('month',as_index=False)[fields].sum(min_count=1)

def quarterly_trend(df):
    x=df.copy();x['quarter']=x.date.dt.to_period('Q').astype(str)
    fields=[f for f in SUM_FIELDS if f in x]
    return x.groupby('quarter',as_index=False)[fields].sum(min_count=1)
