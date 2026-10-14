"""BlueNexus reusable ESG calculation engine.

All values are project-specific. This module does not assert GRI compliance or AI causality.
"""
from dataclasses import dataclass, field
from typing import Optional
import math
import pandas as pd

WATER = 'Water'
ENERGY = 'Energy'
CARBON = 'Carbon'
QUALITY = 'Water Quality'
CHEMICALS = 'Chemicals'
AI = 'AI Impact'
ORDER = [WATER, ENERGY, CARBON, QUALITY, CHEMICALS, AI]

@dataclass
class Result:
    kpi_id: str
    category: str
    name: str
    value: Optional[float]
    unit: str
    status: str = 'Measured / calculated'
    note: str = ''
    required: str = ''

    def as_dict(self):
        return vars(self).copy()


def safe_div(a, b):
    return a / b if b is not None and b > 0 else None


def number(v):
    if v is None or pd.isna(v):
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def require_nonnegative(v, name):
    v = number(v)
    if v is not None and v < 0:
        raise ValueError(f'{name} must be nonnegative')
    return v


def normalize(data: dict) -> dict:
    """Normalize standard input fields. Missing is never zero."""
    fields = ['influent_m3','treated_m3','reclaimed_m3','customer_m3',
              'electricity_kwh','baseline_electricity_kwh','baseline_sec_kwh_m3',
              'baseline_influent_m3','baseline_treated_m3','baseline_reclaimed_m3',
              'freshwater_withdrawal_m3','baseline_freshwater_withdrawal_m3',
              'grid_ef_kgco2e_kwh','conductivity_in_us_cm','conductivity_out_us_cm',
              'ph_in','ph_out','renewable_kwh','total_water_supply_m3']
    out = dict(data)
    for f in fields:
        out[f] = require_nonnegative(out.get(f), f)
    for f in ('ph_in','ph_out'):
        if out[f] is not None and out[f] > 14:
            raise ValueError(f'{f} must be within 0–14')
    return out


def calculate(data: dict) -> list[Result]:
    """Calculate KPIs. No silent defaults for missing measurements or emission factors.

    Historical baseline uses baseline period SEC * current output, not raw totals.
    This controls only for output volume, not feed quality, salinity, treatment standard etc.
    """
    d = normalize(data)
    R = []
    def add(id, cat, name, value, unit, note='', required='', status=None):
        if status is None:
            status = 'Not available' if value is None else 'Measured / calculated'
        R.append(Result(id,cat,name,value,unit,status,note,required))

    feed, output = d['influent_m3'],d['treated_m3']
    elec = d['electricity_kwh']
    recovery = safe_div(output,feed) if feed is not None and output is not None else None
    add('W02',WATER,'Effluent water output',output,'m³',required='treated_m3')
    add('W01',WATER,'Influent volume',feed,'m³',required='influent_m3')
    add('W03',WATER,'Treatment recovery rate',100*recovery if recovery is not None else None,'%',
        'Treated output / influent; not GRI water consumption.', 'influent_m3, treated_m3')
    add('W04',WATER,'Reclaimed water supplied',d['reclaimed_m3'],'m³',
        'Not automatically equal to freshwater avoided.', 'reclaimed_m3')
    add('W05',WATER,'Customer-end delivery',d['customer_m3'],'m³',required='customer_m3')
    supply=d['total_water_supply_m3']
    share=100*safe_div(d['reclaimed_m3'],supply) if d['reclaimed_m3'] is not None and supply is not None else None
    add('W10',WATER,'Reclaimed water share of client supply',share,'%',
        'Requires consistent supply boundary and no double counting.',
        'reclaimed_m3, total_water_supply_m3')
    fresh,basefresh=d['freshwater_withdrawal_m3'],d['baseline_freshwater_withdrawal_m3']
    avoided_fresh = basefresh-fresh if fresh is not None and basefresh is not None else None
    add('W06',WATER,'Freshwater withdrawal difference',avoided_fresh,'m³',
        'Requires comparable demand and boundaries; not assumed equal to reclaimed supply.',
        'baseline_freshwater_withdrawal_m3, freshwater_withdrawal_m3', 'Historical comparison' if avoided_fresh is not None else None)

    sec = safe_div(elec,output) if elec is not None and output is not None else None
    add('E01',ENERGY,'Electricity consumption',elec,'kWh',required='electricity_kwh')
    add('E02',ENERGY,'Specific electricity consumption',sec,'kWh/m³',
        'Period total electricity / period treated output.', 'electricity_kwh, treated_m3')
    bsec=d['baseline_sec_kwh_m3']
    if bsec is None and d['baseline_electricity_kwh'] is not None and d['baseline_treated_m3'] is not None:
        bsec=safe_div(d['baseline_electricity_kwh'],d['baseline_treated_m3'])
    baseline = output*bsec if output is not None and bsec is not None else None
    diff = baseline-elec if baseline is not None and elec is not None else None
    diff_pct = safe_div(100*diff,baseline) if diff is not None else None
    add('E03',ENERGY,'Volume-normalised historical baseline electricity',baseline,'kWh',
        'Baseline SEC × current treated volume. Only volume-normalised.',
        'treated_m3 and baseline_sec_kwh_m3 OR baseline electricity + baseline treated volume',
        'Historical comparison' if baseline is not None else None)
    add('E04',ENERGY,'Electricity difference vs historical baseline',diff,'kWh',
        'Positive = less electricity; not proof of AI causality.', 'E03, electricity_kwh',
        'Historical comparison' if diff is not None else None)
    add('E05',ENERGY,'Electricity difference rate',diff_pct,'%',
        'May be negative. Not a verified AI savings claim.', 'E03, E04',
        'Historical comparison' if diff_pct is not None else None)
    renewable=d['renewable_kwh']
    add('E06',ENERGY,'Renewable electricity share',
        100*safe_div(renewable,elec) if renewable is not None and elec is not None else None,'%',
        'Requires qualifying evidence of renewable electricity.', 'renewable_kwh, electricity_kwh')

    ef=d['grid_ef_kgco2e_kwh']
    emissions=elec*ef/1000 if elec is not None and ef is not None else None
    add('C01',CARBON,'Electricity-related emissions (location-based estimate)',emissions,'tCO₂e',
        'Not necessarily the client’s complete Scope 2 inventory; boundary, factor year and procurement need review.',
        'electricity_kwh, grid_ef_kgco2e_kwh, location/year')
    add('C02',CARBON,'Electricity emissions intensity',
        safe_div(emissions*1000,output) if emissions is not None and output is not None else None,
        'kgCO₂e/m³',required='C01, treated_m3')
    avoided=diff*ef/1000 if diff is not None and ef is not None else None
    add('C03',CARBON,'Estimated electricity-emissions difference',avoided,'tCO₂e',
        'Separate scenario comparison, not deducted from Scope 2; assumes same EF for baseline and actual.',
        'E04, grid_ef_kgco2e_kwh', 'Historical comparison' if avoided is not None else None)

    cin,cout=d['conductivity_in_us_cm'],d['conductivity_out_us_cm']
    reduction = (1-cout/cin)*100 if cin is not None and cout is not None and cin>0 else None
    add('Q01',QUALITY,'Conductivity reduction',reduction,'%',
        'Proxy for ionic content reduction; not full pollution compliance.',
        'conductivity_in_us_cm, conductivity_out_us_cm')
    add('Q02a',QUALITY,'Influent pH',d['ph_in'],'pH',required='ph_in')
    add('Q02b',QUALITY,'Effluent pH',d['ph_out'],'pH',required='ph_out')

    chemicals=d.get('chemicals_kg') or {}
    basechem=d.get('baseline_chemicals_kg') or {}
    baseline_volume=d['baseline_treated_m3']
    for chemical in sorted(set(chemicals)|set(basechem)):
        mass=require_nonnegative(chemicals.get(chemical),chemical)
        oldmass=require_nonnegative(basechem.get(chemical),f'baseline_{chemical}')
        add(f'H01:{chemical}',CHEMICALS,f'{chemical} consumption',mass,'kg',required=f'{chemical} kg')
        add(f'H02:{chemical}',CHEMICALS,f'{chemical} intensity',
            safe_div(mass,output) if mass is not None and output is not None else None,'kg/m³',
            'Compare chemical types separately; same basis and active concentration.',f'{chemical} kg, treated_m3')
        old_intensity=safe_div(oldmass,baseline_volume) if oldmass is not None and baseline_volume is not None else None
        adjusted=old_intensity*output if old_intensity is not None and output is not None else None
        saving=adjusted-mass if adjusted is not None and mass is not None else None
        add(f'AI02:{chemical}',AI,f'{chemical} difference vs historical baseline',saving,'kg',
            'Volume-normalised; requires comparable feed quality, dosing concentration and treatment standards.',
            f'current {chemical} kg, baseline {chemical} kg, baseline/current treated volume',
            'Historical comparison' if saving is not None else None)

    basefeed=d['baseline_influent_m3']; baseout=d['baseline_treated_m3']
    base_recovery=safe_div(baseout,basefeed) if baseout is not None and basefeed is not None else None
    extra = feed*(recovery-base_recovery) if feed is not None and recovery is not None and base_recovery is not None else None
    add('AI01',AI,'Additional treated output vs historical recovery',extra,'m³',
        'Assumes comparable feedwater and output quality; not proven AI-attributable.',
        'current influent/treated, baseline influent/treated',
        'Historical comparison' if extra is not None else None)
    return R


def validate_water_consistency(data: dict) -> list[str]:
    d=normalize(data); issues=[]
    for left,right in [('treated_m3','influent_m3'),('reclaimed_m3','treated_m3'),('customer_m3','reclaimed_m3')]:
        if d[left] is not None and d[right] is not None and d[left]>d[right]:
            issues.append(f'{left} > {right}: review metering boundary/storage; not automatically an error.')
    return issues


def aggregate_daily(df: pd.DataFrame) -> dict:
    """Aggregate standard daily records. No mean-of-ratios; partial missing columns stay unavailable."""
    required=['date','influent_m3','treated_m3','electricity_kwh']
    missing=[c for c in required if c not in df.columns]
    if missing:
        raise ValueError('Missing required CSV columns: '+', '.join(missing))
    x=df.copy()
    x['date']=pd.to_datetime(x['date'],errors='coerce')
    if x['date'].isna().any(): raise ValueError('Invalid dates detected')
    if x['date'].duplicated().any(): raise ValueError('Duplicate dates: filter to one facility before upload')
    output={}
    for key in ['influent_m3','treated_m3','reclaimed_m3','customer_m3','electricity_kwh']:
        if key not in x: continue
        nums=pd.to_numeric(x[key],errors='coerce')
        if nums.isna().any():
            output[key]=None  # never extrapolate missing daily totals
        else:
            output[key]=float(nums.sum())
    for key in ['conductivity_in_us_cm','conductivity_out_us_cm','ph_in','ph_out']:
        if key in x:
            nums=pd.to_numeric(x[key],errors='coerce')
            output[key]=float(nums.mean()) if nums.notna().all() else None
    return output
