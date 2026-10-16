"""Waterhaus equipment monitoring. Signals are supporting evidence, not downtime or AI savings.

Runtime is a cumulative counter: only last-minus-first is meaningful. Signal
units and calibration require confirmation from the plant operator.
"""
import pandas as pd

SIGNALS = {
    'Plant A': {
        'runtime': ['p_1_rohigh_pressure_pump_runtime_cumulative', 'p_2_rohigh_pressure_pump_runtime_cumulative'],
        'frequency': ['p_1_rohigh_pressure_pump_frequency_feedback','p_2_rohigh_pressure_pump_frequency_feedback'],
        'temperature': ['1_rohigh_pressure_pump_hz_temp_o','2_rohigh_pressure_pump_hz_temp_o'],
        'vibration': [],
    },
    'Plant B': {
        'runtime': [f'c_m_ro{i}_high_pressure_pump_runtime_cumulative' for i in range(1,5)],
        'frequency': [f'c_m_ro{i}_high_pressure_pump_fre_out' for i in range(1,5)],
        'temperature': ['c4_m4_ro1_high_pressure_pump_wd'],
        'vibration': ['c4_m4_ro1_high_pressure_pump_xsd','c4_m4_ro1_high_pressure_pump_ysd','c4_m4_ro1_high_pressure_pump_zsd'],
    },
}
LABELS={'runtime':'Pump Runtime (cumulative change)','frequency':'Pump Frequency (average signal)','temperature':'Pump Temperature (average signal)','vibration':'Pump Vibration (average signal)'}


def equipment_summary(records, plant=None):
    """Return evidence summary, no inferred unit for unverified sensors."""
    if records is None or records.empty:
        return pd.DataFrame(columns=['Metric','Value','Unit / status','Valid readings','Source'])
    x=records.copy()
    if 'plant' not in x or 'date' not in x:
        return pd.DataFrame(columns=['Metric','Value','Unit / status','Valid readings','Source'])
    if plant is not None:
        x=x.loc[x.plant.eq(plant)]
    if x.empty:return pd.DataFrame(columns=['Metric','Value','Unit / status','Valid readings','Source'])
    rows=[]
    for plant_name,g in x.groupby('plant'):
        specs=SIGNALS.get(plant_name,{})
        g=g.copy();g['date']=pd.to_datetime(g['date'],errors='coerce');g=g.sort_values('date')
        for metric,cols in specs.items():
            cols=[c if c in g else 'equipment_'+c for c in cols if c in g or 'equipment_'+c in g]
            if not cols:continue
            values=g[cols].apply(pd.to_numeric,errors='coerce')
            if metric=='runtime':
                changes=[]
                for col in cols:
                    valid=values[col].dropna()
                    if len(valid)<2:continue
                    diffs=valid.diff().dropna()
                    if (diffs<0).any():continue  # counter reset: cannot safely infer runtime
                    changes.append(float(valid.iloc[-1]-valid.iloc[0]))
                if not changes:continue
                result=sum(changes);n=len(changes)
                unit='Counter units (unverified); sum across pumps'
            else:
                valid=values.stack().dropna()
                if valid.empty or (valid==0).all():continue  # all-zero signal is not reliable evidence
                result=float(valid.mean());n=int(valid.size)
                unit='Sensor units unverified; mean of valid readings'
            rows.append({'Plant':plant_name,'Metric':LABELS[metric], 'Value':round(result,2),'Unit / status':unit,'Valid readings':n,'Source':', '.join(cols)})
    return pd.DataFrame(rows)


def equipment_daily(records):
    """Produce a simple daily trend per plant/metric for valid sensor readings."""
    rows=[]
    if records is None or records.empty or not {'plant','date'}.issubset(records.columns):return pd.DataFrame()
    for plant,g in records.groupby('plant'):
        for metric,cols in SIGNALS.get(plant,{}).items():
            if metric=='runtime':continue  # never chart cumulative runtime as daily hours
            cols=[c if c in g else 'equipment_'+c for c in cols if c in g or 'equipment_'+c in g]
            if not cols:continue
            v=g[cols].apply(pd.to_numeric,errors='coerce').mean(axis=1)
            for day,val in zip(g['date'],v):
                if pd.notna(val):rows.append({'plant':plant,'date':day,'metric':LABELS[metric],'value':float(val)})
    return pd.DataFrame(rows)
