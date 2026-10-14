"""Client-facing GRI/AWS reporting support, not a compliance determination."""
from pathlib import Path
import pandas as pd

DISCLOSURES = [
 ('GRI 303-1','Water interactions and management','W03','Water sources, catchment context, management and stakeholder evidence'),
 ('GRI 303-2','Discharge impact management','Q01','Discharge standards, receiving waterbody, treatment approach'),
 ('GRI 303-3','Water withdrawal by source',None,'Withdrawal volumes by source, TDS class, water stress and boundary'),
 ('GRI 303-4','Water discharge by destination',None,'Discharge volumes by destination, TDS class, priority substances and limits'),
 ('GRI 303-5','Water consumption',None,'Complete withdrawal/discharge and storage context'),
 ('GRI 302-1 (2016)','Energy consumption','E01','Organisational energy boundary and other energy sources'),
 ('GRI 302-3 (2016)','Energy intensity','E02','Intensity denominator and energy boundary'),
 ('GRI 302-4 (2016)','Energy reduction','E04','Comparable verified baseline and required reduction methodology'),
 ('GRI 305-2','Energy indirect GHG emissions','C01','Grid factor source/year, inventory boundary, market-based information where applicable'),
 ('GRI 305-4','GHG emissions intensity','C02','Scope coverage and intensity denominator'),
 ('GRI 305-5','GHG emissions reductions','C03','Reduction methodology, comparability, scopes and attribution evidence'),
 ('AWS 3.0 1.3.3','Site water balance monitoring','W03','All inflows/outflows and significant storage changes'),
 ('AWS 3.0 1.3.5','Water quality monitoring','Q01','Relevant water quality parameters, pollutant loads and trends'),
 ('AWS 3.0 1.3.6','Potential pollution sources / chemical inventory',None,'On-site inventory of chemicals, fuels, wastes and potential pollutants'),
]

# Consolidated from teammate sections D/E/F; one entry per distinct reporting topic.
# They are proposed indicators/evidence prompts, not direct AWS certification scores.
FURTHER_RECOMMENDATIONS = [
 ('Water','Freshwater substitution','Reclaimed supply, previous freshwater demand, documented substitution baseline','GRI 303-1 / AWS 3.0 water balance'),
 ('Water','Water-quality compliance','Valid test samples, intended reuse/discharge limits, sample results','GRI 303-2, 303-4 / AWS water quality'),
 ('Water','Discharge exceedance incidents','Discharge monitoring, permit limits, incident and corrective-action logs','GRI 303-4 / AWS water quality'),
 ('Water','Water-stress exposure','Site/catchment location, withdrawal and consumption by source, water-stress assessment','GRI 303-3, 303-5 / AWS catchment risks'),
 ('Energy','Renewable electricity share','Electricity sourcing, qualifying contractual instruments and allocation records','Energy disclosure (not GRI 303)'),
 ('Water Stewardship','Water-stewardship targets and actions','Targets, due dates, action progress and evidence of outcomes','GRI 303-1 / AWS stewardship plan'),
 ('Water Stewardship','Catchment stakeholder engagement','Stakeholder register, meetings, feedback and resulting actions','GRI 303-1 / AWS stakeholder engagement'),
 ('Water Stewardship','Water governance and collective action','Initiative/partner records, action plans, progress and contributions','AWS water governance and collective action'),
 ('Water Stewardship','Site WASH provision','Worker coverage, facilities, inspections and maintenance records','AWS WASH'),
 ('Water Stewardship','Freshwater ecosystems and biodiversity','Catchment assessment, ecosystem baseline, planned/completed actions','AWS freshwater ecosystems'),
 ('Water Stewardship','Catchment climate and infrastructure risks','Catchment risk register, assessment, mitigation actions and review dates','AWS shared water challenges'),
]


def build_disclosure_index(results):
    by_id={r.kpi_id:r for r in results}
    rows=[]
    for code,title,kpi,missing in DISCLOSURES:
        r=by_id.get(kpi)
        rows.append({'Standard':code,'Requirement':title,'Linked KPI':r.name if r else 'Context / evidence required',
                     'KPI value':f'{r.value:,.2f} {r.unit}' if r and r.value is not None else 'Not available',
                     'Readiness':'Partial - further evidence required' if r and r.value is not None else 'Additional data required',
                     'Further evidence required':missing})
    return pd.DataFrame(rows)


COLUMNS=['Standard / Disclosure','Category','KPI','Result','Status','More Data Needed']
# Mapping identifies support for a disclosure; it does not assert complete compliance.
PRIORITY_MAPPING={
 'W01':('GRI 303-1 / AWS 3.0','Confirm treatment-system boundary and water sources; not automatically GRI withdrawal.'),
 'W02':('GRI 303-1 / AWS 3.0','Define treated effluent destination; not automatically GRI discharge.'),
 'W03':('GRI 303-1 / AWS 3.0','Document recovery boundary and treatment process.'),
 'W04':('GRI 303-1 / AWS 3.0','Evidence of actual reuse and water-management context.'),
 'W05':('GRI 303-1 / AWS 3.0','Customer-end meter and reconciliation records.'),
 'W10':('GRI 303-1 / AWS 3.0','Client total water supply and reclaimed supply under a consistent boundary.'),
 'W06':('GRI 303-1 / AWS 3.0','Comparable freshwater withdrawal records and baseline methodology.'),
 'Q01':('GRI 303-2 / AWS 3.0','Water-quality monitoring, applicable reuse/discharge criteria and sample evidence.'),
 'Q02a':('GRI 303-2 / AWS 3.0','Water-quality sample coverage and applicable limits.'),
 'Q02b':('GRI 303-2 / AWS 3.0','Water-quality sample coverage and applicable limits.'),
 'E01':('GRI 302-1 (2016)','Organisation-wide energy boundary and other energy sources.'),
 'E02':('GRI 302-3 (2016)','Energy boundary and denominator definition.'),
 'E03':('GRI 302-4 (2016)','Historical baseline evidence and comparability.'),
 'E04':('GRI 302-4 (2016)','Validated comparable baseline and reduction attribution.'),
 'E05':('GRI 302-4 (2016)','Validated comparable baseline and reduction attribution.'),
 'E06':('GRI 302-1 (2016)','Renewable electricity records and contractual instruments.'),
 'C01':('GRI 305-2','Applicable emission factor, year, grid boundary and inventory scope.'),
 'C02':('GRI 305-4','GHG scope coverage and intensity denominator.'),
 'C03':('GRI 305-5','Baseline, emissions methodology and evidence of attribution.'),
}

def build_priority_kpis(results):
    """One row per unique operating KPI, with relevant disclosure support and evidence gaps."""
    rows=[];seen=set()
    for r in results:
        if r.kpi_id in seen or r.category=='AI Impact':continue
        if r.category not in ('Water','Energy','Carbon','Chemicals','Water Quality'):continue
        seen.add(r.kpi_id)
        cat='Water' if r.category=='Water Quality' else r.category
        if r.kpi_id.startswith(('H01:','H02:')):
            standard='AWS 3.0 / GRI 303 context'
            evidence='Chemical inventory, units, dosing records and applicable pollution-risk context.'
        else:
            standard,evidence=PRIORITY_MAPPING.get(r.kpi_id,('Operational KPI / context','Methodology and supporting operational records.'))
        if r.value is None:
            status='Data Required';result='Pending'
            required=(r.required or '').strip()
            more=(required+'; '+evidence) if required else evidence
        else:
            status='Supporting KPI' if cat in ('Water','Chemicals') else 'Calculated — verify boundary'
            result=f'{r.value:,.2f} {r.unit}'
            more=evidence
        rows.append(dict(zip(COLUMNS,[standard,cat,r.name,result,status,more])))
    order={'Water':0,'Energy':1,'Carbon':2,'Chemicals':3}
    rows.sort(key=lambda x:(order.get(x['Category'],9),x['KPI']))
    return pd.DataFrame(rows,columns=COLUMNS)

def build_further_recommendations():
    rows=[]
    for category,kpi,evidence,standard in FURTHER_RECOMMENDATIONS:
        rows.append(dict(zip(COLUMNS,[standard,category,kpi,'Pending','Recommended — data required',evidence])))
    return pd.DataFrame(rows,columns=COLUMNS)


def methodology_appendix(matrix_path):
    """Downloadable CSV with reviewed definitions, formulas and boundaries, not executable code."""
    df=pd.read_csv(matrix_path,encoding='utf-8-sig').fillna('')
    columns=['kpi_id','module','kpi_name','definition','formula_description','required_inputs','output_unit',
             'gri_mapping','aws_mapping','mapping_type','validation_rule','evidence_requirement',
             'calculation_review','implementation_note']
    return df[[c for c in columns if c in df.columns]].drop_duplicates(subset=['kpi_id'])


def narrative(company,period,scenario):
    lead=f'{company or "The client"} assessed its water treatment performance for {period or "the selected period"} using client-provided operational information.'
    if scenario:
        lead+=' Historical comparisons are volume-normalised scenarios; they do not establish that AquaxGo caused the observed differences.'
    return lead+' Review reporting boundaries, water sources, discharge destinations, applicable emission factors and supporting evidence before formal disclosures.'


def reporting_draft(company,period,results,scenario=False):
    """Plain-text draft containing real calculated values, not claims of GRI/AWS compliance."""
    priority=build_priority_kpis(results)
    disclosure=build_disclosure_index(results)
    further=build_further_recommendations()
    lines=['BLUENEXUS - ESG REPORTING DRAFT',f'Client: {company or "Not specified"}',f'Period: {period or "Selected period"}',
           '', '1. Reporting context',narrative(company,period,scenario),'',
           '2. Priority operational KPIs (not necessarily complete GRI disclosures)']
    for row in priority.to_dict('records'):
        lines.append(f"- {row['Category']} | {row['KPI']}: {row['Result']} ({row['Status']})")
    lines += ['','3. GRI / AWS disclosure support and outstanding evidence']
    for row in disclosure.to_dict('records'):
        lines.append(f"- {row['Standard']} | {row['Requirement']} | {row['Readiness']} | Needed: {row['Further evidence required']}")
    lines += ['','4. Further reporting recommendations (not verified results)']
    for row in further.to_dict('records'):
        lines.append(f"- {row['KPI']}: {row['More Data Needed']}")
    lines += ['','5. Methodology and limitations',
              '- Use the separate KPI Methodology Appendix for formulas and input requirements.',
              '- A calculated KPI does not demonstrate full GRI compliance or AWS certification.',
              '- Estimated historical inputs must not be described as verified AI-attributable savings.']
    return '\n'.join(lines)
