"""Planned-vs-actual dosing evidence from BlueNexus daily plant records.

Reported dose unit is UNVERIFIED in Data Dictionary v2. We display an
explicit mg/L assumption, never convert these values to chemical mass.
"""
import pandas as pd

DOSE_FIELDS = {
    'NaOH': ('planned_naoh_dose_reported', 'actual_naoh_dose_reported'),
    'Antiscalant': ('planned_antiscalant_dose_reported', 'actual_antiscalant_dose_reported'),
    'Non-oxidizing biocide': ('planned_nonoxidizing_biocide_dose_reported', 'actual_nonoxidizing_biocide_dose_reported'),
    'Reducing agent': ('planned_reducing_agent_dose_reported', 'actual_reducing_agent_dose_reported'),
    'SDBS': ('planned_sdbs_dose_reported', 'actual_sdbs_dose_reported'),
}


def dosing_summary(records):
    """Summarise paired valid records only, with period coverage disclosed.

    Deviation is ratio of paired means, not total mass saved and not AI effect.
    """
    if records is None or records.empty:
        return pd.DataFrame()
    results = []
    total = len(records)
    for chemical, (planned, actual) in DOSE_FIELDS.items():
        if planned not in records or actual not in records:
            continue
        p = pd.to_numeric(records[planned].replace('/', pd.NA), errors='coerce')
        a = pd.to_numeric(records[actual].replace('/', pd.NA), errors='coerce')
        valid = p.notna() & a.notna() & (p >= 0) & (a >= 0)
        count = int(valid.sum())
        if not count:
            continue
        planned_mean = float(p[valid].mean())
        actual_mean = float(a[valid].mean())
        deviation = (actual_mean / planned_mean - 1) * 100 if planned_mean > 0 else None
        results.append({
            'Chemical': chemical,
            'Planned dose (mean)': round(planned_mean, 2),
            'Actual dose (mean)': round(actual_mean, 2),
            'Deviation (%)': round(deviation, 2) if deviation is not None else None,
            'Valid records': count,
            'Total records': total,
            'Coverage (%)': round(100 * count / total, 2),
        })
    return pd.DataFrame(results)
