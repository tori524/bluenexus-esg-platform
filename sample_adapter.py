"""BlueNexus anonymised sample adapter; no data files bundled."""
import pandas as pd

RENAME = {
    'influent_volume_m3':'influent_m3',
    'effluent_volume_m3':'treated_m3',
    'reclaimed_supply_volume_m3':'reclaimed_m3',
    'customer_end_volume_m3':'customer_m3',
    'daily_electricity_kwh':'electricity_kwh',
    'influent_conductivity_us_cm':'conductivity_in_us_cm',
    'effluent_conductivity_us_cm':'conductivity_out_us_cm',
    'influent_ph':'ph_in',
    'effluent_ph':'ph_out',
}

def prepare_upload(df):
    """Map source names to canonical fields without changing raw measurements."""
    x = df.copy()
    if 'plant' not in x.columns:
        x['plant'] = 'Uploaded facility'
    if 'date' not in x.columns:
        raise ValueError('Missing date column')
    x['date'] = pd.to_datetime(x['date'], errors='coerce')
    if x['date'].isna().any():
        raise ValueError('Some dates cannot be parsed')
    if x.duplicated(['plant','date']).any():
        raise ValueError('Duplicate plant/date observations; please resolve before continuing')
    x = x.rename(columns=RENAME)
    for col in RENAME.values():
        if col in x:
            x[col] = pd.to_numeric(x[col].replace('/',pd.NA),errors='coerce')
    return x

def filter_upload(df, plant, start, end):
    x = df.loc[df['plant'].eq(plant) & df['date'].between(pd.Timestamp(start),pd.Timestamp(end))].copy()
    if x.empty:
        raise ValueError('No records for the selected plant and dates')
    return x

def data_quality_summary(df):
    essential = ['influent_m3','treated_m3','electricity_kwh']
    out = []
    for field in essential + ['reclaimed_m3','conductivity_in_us_cm','conductivity_out_us_cm']:
        if field in df:
            out.append({'Field':field,'Missing records':int(df[field].isna().sum()),'Total records':len(df)})
    for flag in ['recovery_quality_flag','conductivity_quality_flag','water_balance_flag','data_quality_status']:
        if flag in df:
            for val,n in df[flag].fillna('Not provided').value_counts().items():
                out.append({'Field':f'{flag}: {val}','Missing records':int(n),'Total records':len(df)})
    return pd.DataFrame(out)
