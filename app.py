"""BlueNexus ESG client portal v9: current/previous, daily/monthly, four themes."""
from pathlib import Path
from datetime import date
import base64, html, hashlib
import pandas as pd
import plotly.graph_objects as plotly_go
import streamlit as st
from calculations import calculate, validate_water_consistency
from period_data import CHEMS,CHEM_COLS,REQUIRED,prepare,select_period,aggregate,matching_periods,monthly_trend,quarterly_trend
from reporting import build_disclosure_index,narrative,build_priority_kpis,build_further_recommendations,methodology_appendix,reporting_draft
from report_export import build_esg_report_docx
from chemical_dosing import dosing_summary
from equipment_monitoring import equipment_summary, equipment_daily, LABELS

ROOT=Path(__file__).parent
st.set_page_config(page_title='BlueNexus | ESG Reporting',page_icon=str(ROOT/'assets'/'favicon.png'),layout='wide',initial_sidebar_state='expanded')
COLORS={'Water':'#1675B9','Energy':'#D59616','Carbon':'#238A65','Chemicals':'#8062B5'}
LIGHT={'Water':'#E7F3FB','Energy':'#FFF5D9','Carbon':'#E3F5EC','Chemicals':'#F1EBFA'}
NAVY='#103B66'
FACTORS={'Singapore · 0.412':0.412,'Malaysia — Kulim · 0.540':0.540,'Malaysia — Peninsular · 0.774':0.774,'Malaysia — Sabah · 0.525':0.525,'Malaysia — Sarawak · 0.199':0.199,'Philippines — Mindanao · 0.8522':0.8522,'Philippines — Luzon–Visayas · 0.6935':0.6935,'China — Jiangsu · 0.5827':0.5827,'China — Zhejiang · 0.4974':0.4974,'UAE — Dubai · 0.3833':0.3833,'Custom':None}
ICONS={'Water':'<path d="M12 2C8 8 5 11 5 15a7 7 0 0 0 14 0c0-4-3-7-7-13Z"/>','Energy':'<path d="m13 2-3 8H5l6 12 3-8h5L13 2Z"/>','Carbon':'<path d="M20 4C9 4 5 10 5 15a5 5 0 0 0 5 5c7 0 11-6 10-16Z"/><path d="M4 21c3-7 8-10 13-12"/>','Chemicals':'<path d="M9 3h6M10 3v7l-5 8a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-8V3"/>','Overview':'<path d="m3 10 9-7 9 7v10H3z"/>','Data Input':'<path d="M4 4h16v16H4zM8 9h8M8 13h8M8 17h5"/>','Sustainability Impact':'<path d="M4 20V5M4 20h17M8 15l4-5 4 3 4-7"/>','GRI / AWS Reporting':'<path d="M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h7"/>','Maintenance':'<path d="M14 7a4 4 0 0 0-5 5l-6 6a2 2 0 0 0 3 3l6-6a4 4 0 0 0 5-5l-3 3-3-3 3-3Z"/>','Operations':'<path d="M4 7h16M4 12h16M4 17h16"/>'}

def svg(name,color=None,size=24):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color or COLORS.get(name,NAVY)}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'
def esc(s):return html.escape(str(s))
def fmt(v,unit='',digits=2):return 'Data needed' if v is None else f'{v:,.{digits}f} {unit}'.strip()
def notes(*items):
    st.markdown('<div class="bn-note"><ul>'+''.join('<li>'+esc(s)+'</li>' for s in items if s)+'</ul></div>',unsafe_allow_html=True)
def header(name,standard):
    color=COLORS[name]
    st.markdown(f'<div class="bn-section" style="background:{LIGHT[name]};border-left:5px solid {color}">{svg(name,color)}<b style="color:{color}">{name} · {esc(standard)}</b></div>',unsafe_allow_html=True)
def operations_header():
    st.markdown(
        '<div class="bn-section" style="background:#E8EEF5;border-left:5px solid #607D98">'
        +svg('Operations','#496A86')
        +'<b style="color:#36556F">Waterhaus™ Operations</b></div>',
        unsafe_allow_html=True)
    st.caption('Operational monitoring and maintenance evidence · not a separate ESG reporting dimension.')

def metric(name,value,unit='',note='',theme='Water'):
    color=COLORS[theme]
    st.markdown(f'<div class="bn-card" style="border-top:4px solid {color};background:{LIGHT[theme]}"><div class="bn-card-label">{esc(name)}</div><div class="bn-card-value">{esc(fmt(value,unit))}</div><div class="bn-card-note">{esc(note)}</div></div>',unsafe_allow_html=True)
def comparison(title,old,new,unit,theme):
    if old is None or new is None:return
    fig=plotly_go.Figure(plotly_go.Bar(y=['Previous','Current'],x=[old,new],orientation='h',marker_color=[LIGHT[theme],COLORS[theme]],marker_line_color=COLORS[theme],marker_line_width=1,text=[fmt(old,unit),fmt(new,unit)],textposition='auto'))
    fig.update_layout(title=title,margin=dict(l=15,r=20,t=48,b=12),height=235,showlegend=False,plot_bgcolor='white',paper_bgcolor='white',xaxis_title=unit,yaxis=dict(categoryorder='array',categoryarray=['Current','Previous']))
    st.plotly_chart(fig,use_container_width=True)
def trend(df,field,title,theme,frequency):
    if df is None or field not in df:return
    x=df.copy()
    if frequency=='Quarterly':x=quarterly_trend(x)
    elif frequency=='Monthly':x=monthly_trend(x)
    elif len(x)>90:x=monthly_trend(x)
    xcol='quarter' if 'quarter' in x else ('month' if 'month' in x else 'date')
    if x[field].notna().sum()<2:return
    fig=plotly_go.Figure(plotly_go.Scatter(x=x[xcol],y=x[field],mode='lines+markers',line=dict(color=COLORS[theme],width=3),marker=dict(size=5)))
    fig.update_layout(title=title,height=270,margin=dict(l=15,r=10,t=48,b=20),plot_bgcolor='white',paper_bgcolor='white',yaxis_title=field.replace('_',' ').title())
    st.plotly_chart(fig,use_container_width=True)
def val(key,label,required=False,quality=False,help_text=None):
    k='field_'+key
    st.session_state.setdefault(k,'')
    raw=st.text_input(label+(' *' if required else ''),key=k,placeholder='Period average / representative value' if quality else 'Reporting-period total',help=help_text)
    if not raw.strip():return None
    try:
        n=float(raw.replace(',',''))
        if not 0<=n<float('inf') or (quality and 'pH' in label and n>14):raise ValueError()
        return n
    except ValueError:
        st.error(label+': enter a non-negative number.')
        return None

def setfields(prefix,values):
    for key,value in values.items():
        if isinstance(value,(int,float)) and pd.notna(value):st.session_state['field_'+prefix+'_'+key]=f'{value:.2f}'
    for chemical,col in CHEM_COLS.items():
        v=values.get(col)
        if v is not None and pd.notna(v):st.session_state['field_'+prefix+'_'+col]=f'{v:.2f}'

def parse_upload(prefix):
    uploaded=st.file_uploader('Upload CSV / Excel *',type=['csv','xlsx'],key='file_'+prefix)
    if uploaded is None:return None,None,None
    try:
        uploaded.seek(0)
        raw=pd.read_excel(uploaded) if uploaded.name.lower().endswith('xlsx') else pd.read_csv(uploaded)
        frequency=st.session_state['freq_'+prefix]
        x=prepare(raw,frequency)
        plants=sorted(x.plant.unique())
        plant=st.selectbox('Facility',plants,key='plant_'+prefix)
        min_date=x.date.min().date();max_date=x.date.max().date()
        if frequency=='Quarterly':
            min_date=x.date.min().to_period('Q').start_time.date()
            max_date=x.date.max().to_period('Q').end_time.date()
        if frequency=='Monthly':
            min_date=date(min_date.year,min_date.month,1)
            import calendar
            max_date=date(max_date.year,max_date.month,calendar.monthrange(max_date.year,max_date.month)[1])
        # Merged equipment files may span more dates than water/energy measurements.
        # Default to the continuous period with all required operational fields present.
        facility_rows=x.loc[x.plant.eq(plant)].sort_values('date')
        measured=facility_rows.dropna(subset=REQUIRED)
        if not measured.empty:
            # Prefer the latest contiguous sequence of complete observations.
            # This avoids selecting January-August when water/energy exist only in July-August.
            keys=measured['date'].dt.to_period('Q' if frequency=='Quarterly' else 'M' if frequency=='Monthly' else 'D')
            ordinals=keys.astype('int64')
            runs=ordinals.diff().ne(1).cumsum()
            latest_run=measured.loc[runs.eq(runs.iloc[-1])]
            first=latest_run.date.min()
            last=latest_run.date.max()
            if frequency=='Quarterly':
                default_start=first.to_period('Q').start_time.date()
                default_end=last.to_period('Q').end_time.date()
            elif frequency=='Monthly':
                default_start=first.to_period('M').start_time.date()
                default_end=last.to_period('M').end_time.date()
            else:
                default_start=first.date()
                default_end=last.date()
            if (default_start,default_end)!=(min_date,max_date):
                st.caption('Default dates use the latest continuous period with complete water and electricity readings. Equipment records outside this period remain available in the uploaded file.')
        else:
            default_start,default_end=min_date,max_date
            st.warning('No complete water and electricity observations found for this facility. Equipment data alone cannot calculate the core water/energy KPIs.')
        # Key changes when the uploaded file, facility or frequency changes, preventing stale date selections.
        file_id=hashlib.sha256(uploaded.getvalue()).hexdigest()[:12]
        date_key=f'dates_{prefix}_{file_id}_{plant}_{frequency}'
        selected_dates=st.date_input('Select reporting period',(default_start,default_end),min_value=min_date,max_value=max_date,key=date_key)
        if len(selected_dates)!=2:return None,None,None
        selected,coverage=select_period(x,plant,selected_dates[0],selected_dates[1],frequency)
        if coverage['missing']:
            st.error(f"Missing {coverage['missing']} {frequency.lower()} records. Complete the period before calculating.")
            return None,selected,coverage
        vals=aggregate(selected)
        # A complete date range does not guarantee complete measurements.
        # Make missing measurement coverage visible instead of silently treating it as zero.
        incomplete=[name for name in REQUIRED if name not in selected or selected[name].isna().any()]
        if incomplete:
            counts={name:int(selected[name].notna().sum()) if name in selected else 0 for name in REQUIRED}
            st.warning('Some core water/energy measurements are missing for the selected period: '
                       +', '.join(incomplete)+'. Valid records: '
                       +', '.join(f'{name} {count}/{len(selected)}' for name,count in counts.items())
                       +'. Select a fully measured period to calculate all core KPIs.')
        sig=hashlib.sha256(uploaded.getvalue()+str((plant,selected_dates,frequency)).encode()).hexdigest()
        if st.session_state.get('sig_'+prefix)!=sig:
            setfields(prefix,vals)
            available=[name for name,col in CHEM_COLS.items() if vals.get(col) is not None]
            st.session_state['chemselect_'+prefix]=available
            st.session_state['sig_'+prefix]=sig
            st.session_state['selected_'+prefix]=selected
            st.session_state['coverage_'+prefix]=coverage
            # Source widget is not mutated after creation; upload is client-reported.
            st.rerun()
        st.success(f"{coverage['observed']} {frequency.lower()} records loaded. Review the fields below.")
        return vals,selected,coverage
    except (ValueError,TypeError,KeyError) as exc:
        st.error('Upload issue: '+str(exc))
        return None,None,None


def equipment_from_merged(prefix):
    """Equipment evidence comes from the same selected CSV as performance data."""
    if st.session_state.get('input_'+prefix) != 'CSV / Excel upload':
        return None
    source=st.session_state.get('selected_'+prefix)
    if source is None or source.empty:
        return None
    evidence=equipment_summary(source)
    if evidence.empty:
        return None
    field_map={'Pump Runtime (cumulative change)':'pump_runtime_change',
               'Pump Frequency (average signal)':'pump_frequency',
               'Pump Temperature (average signal)':'pump_temperature',
               'Pump Vibration (average signal)':'pump_vibration'}
    signature=hashlib.sha256(pd.util.hash_pandas_object(source,index=True).values.tobytes()).hexdigest()
    if st.session_state.get('equipment_signature_'+prefix)!=signature:
        for _,row in evidence.iterrows():
            field=field_map.get(row['Metric'])
            if field:
                st.session_state['field_'+prefix+'_'+field]=f"{row['Value']:.2f}"
        st.session_state['equipment_signature_'+prefix]=signature
    return evidence

def factor_input():
    a,b=st.columns(2)
    with a:choice=st.selectbox('Location / grid',list(FACTORS),key='factor_choice')
    with b:
        if FACTORS[choice] is None:
            st.number_input('Emission factor (kgCO₂e/kWh) *',min_value=0.0,format='%.4f',key='factor_custom')
        else:st.metric('Emission factor (kgCO₂e/kWh)',f'{FACTORS[choice]:.4f}')
    st.text_input('Factor source and year',key='factor_source',placeholder='Official source and year')
    notes('Reference factors are illustrative until the source, year and geographic boundary are checked.', 'The same factor is reused for baseline comparison unless different factors are documented.')

def enter_fields(prefix):
    values={}
    header('Water','GRI 303 / AWS 3.0')
    a,b,c=st.columns(3)
    with a:values['influent_m3']=val(prefix+'_influent_m3','Influent water (m³)',True,help_text='Total water entering the treatment system')
    with b:values['treated_m3']=val(prefix+'_treated_m3','Effluent water (m³)',True,help_text='Total treated water produced by the system')
    with c:values['reclaimed_m3']=val(prefix+'_reclaimed_m3','Reclaimed supply (m³)',help_text='Reclaimed water supplied for reuse')
    a,b,c=st.columns(3)
    with a:values['customer_m3']=val(prefix+'_customer_m3','Customer delivery (m³)',help_text='Water received or metered at the customer end')
    with b:values['freshwater_withdrawal_m3']=val(prefix+'_freshwater_withdrawal_m3','Freshwater withdrawal (m³)',help_text='Client freshwater withdrawal, not treatment effluent')
    with c:values['conductivity_in_us_cm']=val(prefix+'_conductivity_in_us_cm','Influent conductivity (µS/cm)',quality=True)
    a,b,c=st.columns(3)
    with a:values['conductivity_out_us_cm']=val(prefix+'_conductivity_out_us_cm','Effluent conductivity (µS/cm)',quality=True)
    with b:values['ph_in']=val(prefix+'_ph_in','Influent pH',quality=True)
    with c:values['ph_out']=val(prefix+'_ph_out','Effluent pH',quality=True)
    values['total_water_supply_m3']=val(prefix+'_total_water_supply_m3','Total client water supply (m³)',help_text='All sources supplying the client; used for reclaimed water share')
    header('Energy','GRI 302 / 103')
    a,b=st.columns(2)
    with a:values['electricity_kwh']=val(prefix+'_electricity_kwh','Electricity used (kWh)',True)
    with b:values['renewable_kwh']=val(prefix+'_renewable_kwh','Renewable electricity (kWh)')
    header('Carbon','GRI 305')
    st.caption('Scope 2 uses electricity from Energy. Enter the emission factor once below.')
    if prefix=='current':
        factor_input()
    header('Chemicals','AWS 3.0 / GRI 303')
    # The BlueNexus sample contains dose measurements, not verified kg of chemical.
    # Present the recognised measurements in the input form without silently
    # converting them into chemical mass or treating planned doses as a baseline.
    if st.session_state.get('input_'+prefix)=='CSV / Excel upload':
        selected_dosing_records=st.session_state.get('selected_'+prefix)
        if selected_dosing_records is not None:
            detected_doses=dosing_summary(selected_dosing_records)
            if not detected_doses.empty:
                st.markdown('**Chemical dosing recognised from your CSV**')
                st.dataframe(detected_doses,hide_index=True,use_container_width=True)
                notes('Planned and actual doses were read automatically from your uploaded records.',
                      'Dose unit is assumed mg/L, but is not verified by BlueNexus.',
                      'Coverage is the share of records with both planned and actual values.',
                      'Dosing values are not automatically converted into chemical consumption (kg).')
            else:
                st.caption('No paired planned/actual chemical dosing records were found in this upload.')
    chosen=st.multiselect('Chemicals used — consumption in kg',CHEMS+['Other'],key='chemselect_'+prefix)
    values['chemicals_kg']={}
    for chemical in chosen:
        key=CHEM_COLS.get(chemical,'chemical_other_kg')
        mass=val(prefix+'_'+key,chemical+' consumed (kg)')
        if mass is not None:values['chemicals_kg'][chemical]=mass
    operations_header()
    a,b,c=st.columns(3)
    with a:values['downtime_hours']=val(prefix+'_downtime_hours','Unplanned downtime (hours)')
    with b:values['manual_interventions']=val(prefix+'_manual_interventions','Manual interventions (count)')
    with c:values['om_costs']=val(prefix+'_om_costs','O&M Costs (same currency)')
    st.markdown('**Equipment Monitoring**')
    notes('Pump signals are automatically read from the merged CSV, or may be entered manually.',
          'Runtime is a change in cumulative counter, not downtime.',
          'Sensor units are unverified. Previous demo signals are synthetic.')
    e1,e2=st.columns(2)
    for i,(key,label) in enumerate([('pump_runtime_change','Pump runtime — cumulative counter change'),
                                    ('pump_frequency','Pump frequency — average signal'),
                                    ('pump_temperature','Pump temperature — average signal'),
                                    ('pump_vibration','Pump vibration — average signal')]):
        with (e1 if i%2==0 else e2):values[key]=val(prefix+'_'+key,label)
    return values

# Style
st.markdown('''<style>
[data-testid="stSidebar"]{background:linear-gradient(rgba(5,22,43,.85),rgba(5,22,43,.9)),url('data:image/jpeg;base64,HERO') center/cover!important}
[data-testid="stSidebar"] *{color:white}
[data-testid="stSidebar"] button{border-radius:5px!important;border:1px solid #477398!important;text-align:left!important;background:#174872!important;min-height:46px}
[data-testid="stSidebar"] button:hover{background:#25699B!important}
.block-container{max-width:1400px;padding-top:1.4rem}
.bn-note{background:#F1F7FC;border:1px solid #D9E9F4;border-radius:9px;padding:8px 18px;color:#38516A;margin:8px 0 18px}
.bn-note ul{margin:5px 0;padding-left:18px}.bn-note li{margin:5px 0;line-height:1.5}
.bn-section{display:flex;gap:12px;align-items:center;padding:14px 18px;border-radius:9px;margin:24px 0 12px;font-size:1.05rem}
.bn-card{padding:20px;border-radius:10px;min-height:144px;margin:6px 0 12px}
.bn-card-label{font-size:1.03rem;font-weight:750;color:#103B66}.bn-card-value{font-size:1.45rem;font-weight:750;color:#103B66;margin:10px 0}.bn-card-note{font-size:.75rem;color:#64798A}
.bn-flow{display:flex;align-items:center;gap:10px;width:100%;margin:18px 0 25px}
.bn-flow-card{flex:1 1 0;min-width:0;min-height:146px;box-sizing:border-box;background:#E7F3FB;border:1px solid #A8CEE5;border-radius:12px;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:16px;padding:15px 10px;text-align:center;color:#103B66;font-size:.96rem;font-weight:650;line-height:1.25}
.bn-flow-card svg{flex-shrink:0}
.bn-flow-arrow{flex:0 0 17px;text-align:center;color:#1675B9;font-size:24px;font-weight:800}
@media(max-width:900px){.bn-flow{flex-wrap:wrap;justify-content:center}.bn-flow-card{flex:1 1 155px;max-width:220px}.bn-flow-arrow{flex:0 0 16px}}
@media(max-width:480px){.bn-flow-card{flex:1 1 100%;max-width:none;min-height:95px}.bn-flow-arrow{flex:0 0 100%;transform:rotate(90deg);line-height:18px}}
.bn-hero{padding:4rem;border-radius:0;background:linear-gradient(90deg,#071A31 0%,rgba(8,30,57,.88) 55%,rgba(8,30,57,.3) 100%),url('data:image/jpeg;base64,HERO') right center/cover;min-height:85vh;color:white}
.bn-hero h1{color:white;font-size:3.1rem;line-height:1.12;max-width:800px}.bn-hero p{color:#D8EAF7}
</style>'''.replace('HERO',base64.b64encode((ROOT/'assets'/'water_hero.jpg').read_bytes()).decode()),unsafe_allow_html=True)
for key,default in {'entered':False,'page':'Overview','ready':False,'current_source':'Measured / client-reported','source_previous':'Estimated historical data','source_current':'Measured / client-reported','freq_current':'Daily','freq_previous':'Daily','input_current':'CSV / Excel upload','input_previous':'Manual input','factor_choice':'Custom','factor_custom':0.40,'company':'Demo Facility','period_label':'2026','selected_current':None,'selected_previous':None,'coverage_current':None,'coverage_previous':None}.items():st.session_state.setdefault(key,default)
if 'next_page' in st.session_state:st.session_state.page=st.session_state.pop('next_page')
def go(page):st.session_state.next_page=page;st.rerun()

if not st.session_state.entered:
    st.markdown('<style>[data-testid="stSidebar"],[data-testid="collapsedControl"]{display:none!important}</style>',unsafe_allow_html=True)
    st.markdown("""<style>
    [data-testid="stMainBlockContainer"]{max-width:100%!important;padding:0!important}
    [data-testid="stMain"]{background:linear-gradient(90deg,rgba(4,17,35,.75),rgba(4,17,35,.1)),url('data:image/jpeg;base64,HERO') center center/cover no-repeat!important}
    .bn-landing-title{padding:11vh 5vw 1.5rem;color:white}
    .bn-landing-title h1{color:white;font-size:clamp(2.3rem,5vw,4.5rem);line-height:1.1;max-width:750px}
    .bn-landing-title p{color:#D5E9F9}
    [data-testid="stMain"] .stButton button,[data-testid="stMain"] [data-testid="stPopover"] button{min-height:48px}
    </style>""".replace('HERO',base64.b64encode((ROOT/'assets'/'water_hero.jpg').read_bytes()).decode()),unsafe_allow_html=True)
    st.markdown('<div class="bn-landing-title"><div style="color:#B5DDF7;font-weight:700">BLUENEXUS · WATERHAUS™ + AQUAXGO™</div><h1>From Autonomous Water Treatment<br>to ESG Reporting</h1><p>GRI- and AWS-aligned sustainability reporting</p></div>',unsafe_allow_html=True)
    inset,a,b,c=st.columns([0.38,1.2,1.05,3.1],gap='small')
    with a:
        if st.button('Start Assessment →',type='primary',use_container_width=True):st.session_state.entered=True;st.rerun()
    with b:
        with st.popover('Contact Us',use_container_width=True):
            st.markdown('**Get in Touch**')
            st.markdown('**Visit Us**  \n51 Goldhill Plaza #07-07  \nSingapore 308900')
            st.markdown('**Email Us**  \n[info@bluenexus.tech](mailto:info@bluenexus.tech)')
            st.markdown('**Follow Us**  \n[LinkedIn](https://www.linkedin.com/company/bluenexus-technologies/)')
    st.stop()

with st.sidebar:
    st.markdown('<h2 style="color:white">BlueNexus</h2><div style="color:#B8DDF6">ESG IMPACT & REPORTING</div>',unsafe_allow_html=True)
    for page in ['Overview','Data Input','Sustainability Impact','GRI / AWS Reporting']:
        st.markdown('<div style="height:5px"></div>',unsafe_allow_html=True)
        if st.button(page,key='nav_'+page,use_container_width=True,type='primary' if st.session_state.page==page else 'secondary',icon={'Overview':':material/home:','Data Input':':material/database:','Sustainability Impact':':material/monitoring:','GRI / AWS Reporting':':material/description:'}[page]):go(page)
    st.divider()
    if st.session_state.ready:st.success('Assessment ready')
    else:st.info('Enter facility data to begin')

page=st.session_state.page
if page=='Overview':
    st.title('Waterhaus™ & AquaxGo™ | ESG Impact & Reporting')
    notes('Measure Waterhaus and AquaxGo environmental performance.','Compare operations before and after AquaxGo.','Prepare GRI- and AWS-aligned reporting drafts.')
    cols=st.columns(4)
    descriptions={'Water':('GRI 303 / AWS 3.0','Recovery, reuse and water quality'),'Energy':('GRI 302 / 103','Electricity and efficiency'),'Carbon':('GRI 305','Scope 2 and emissions difference'),'Chemicals':('AWS 3.0 / GRI 303','Chemical use and reduction')}
    for col,name in zip(cols,COLORS):
        with col:
            std,desc=descriptions[name]
            st.markdown(f'<div class="bn-card" style="background:{LIGHT[name]};border-top:5px solid {COLORS[name]}">{svg(name)}<h3>{name}</h3><b>{std}</b><p>{desc}</p></div>',unsafe_allow_html=True)
    st.subheader('How It Works')
    flow=['Input Data','Calculate KPIs','Compare AquaxGo Impact','GRI / AWS Mapping','Export ESG Report']
    flow_icons=['Data Input','Energy','Sustainability Impact','GRI / AWS Reporting','GRI / AWS Reporting']
    cards=[]
    for i,(step,icon_name) in enumerate(zip(flow,flow_icons)):
        cards.append(f'<div class="bn-flow-card">{svg(icon_name,"#1675B9",30)}<span>{esc(step)}</span></div>')
        if i<len(flow)-1:cards.append('<div class="bn-flow-arrow" aria-hidden="true">&#8594;</div>')
    st.markdown('<div class="bn-flow">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    if st.button('Enter Your Data →',type='primary'):go('Data Input')

elif page=='Data Input':
    if st.session_state.pop('pending_demo_source',False):st.session_state.source_previous='Estimated historical data'
    if st.session_state.pop('pending_current_demo',False):
        q=float(st.session_state.get('field_current_treated_m3') or 100000)
        examples={'customer_m3':q*0.98,'freshwater_withdrawal_m3':q*0.30,'total_water_supply_m3':q*1.65,
                  'conductivity_in_us_cm':2400,'conductivity_out_us_cm':100,'ph_in':8.2,'ph_out':7.1,
                  'downtime_hours':10,'manual_interventions':30,'om_costs':8000}
        for k,v in examples.items():
            key='field_current_'+k
            if not st.session_state.get(key):st.session_state[key]=f'{v:.2f}'
        for chemical,value in [('NaOH',850),('Antiscalant',120)]:
            col=CHEM_COLS[chemical];key='field_current_'+col
            if not st.session_state.get(key):st.session_state[key]=f'{value:.2f}'
        st.session_state['chemselect_current']=sorted(set(st.session_state.get('chemselect_current',[]))|{'NaOH','Antiscalant'})
        st.session_state.demo_current_used=True
        st.session_state.source_current='Estimated'
    st.title('Enter Your Facility Data')
    notes('Enter totals for the selected reporting period, not daily averages.','* marks the minimum data needed for water and energy calculations.','Other fields enable additional ESG and AquaxGo comparisons.')
    with st.container(border=True):
        st.subheader('Project details')
        a,b=st.columns(2)
        with a:st.text_input('Client / project',key='company')
        with b:st.text_input('Reporting period label',key='period_label')
    st.subheader('1. Current Operations')
    st.radio('Input method',['Manual input','CSV / Excel upload'],key='input_current',horizontal=True)
    st.radio('Data frequency',['Daily','Monthly','Quarterly'],key='freq_current',horizontal=True)
    st.radio('Current data source',['Measured / client-reported','Estimated'],key='source_current',horizontal=True)
    if st.session_state.input_current=='Manual input':
        st.date_input('Current period',value=(date(2026,7,1),date(2026,8,31)),key='manual_dates_current')
    if st.session_state.input_current=='CSV / Excel upload':
        a,b=st.columns(2)
        with a:
            template=ROOT/'data'/'Sample_Operational_Data.csv'
            st.download_button('Download Sample CSV',template.read_bytes(),file_name=template.name,mime='text/csv')
        with b:
            guide=ROOT/'data'/'Data_Input_Guide.xlsx'
            st.download_button('Download Data Input Guide',guide.read_bytes(),file_name=guide.name,mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        parse_upload('current')
    if st.button('Fill Missing Current Fields (Demo)',help='Adds synthetic examples only to empty fields; does not overwrite measured values.'):
        st.session_state.pending_current_demo=True
        st.rerun()
    if st.session_state.get('demo_current_used'):
        notes('Demo additions are synthetic, not BlueNexus measurements.',
              'Missing client supply, freshwater, quality, chemical and operations inputs use illustrative assumptions.',
              'Existing uploaded measurements are not overwritten; review the filled fields before reporting.')
    # Equipment signals are recognised from the same merged operational upload.
    current_equipment=equipment_from_merged('current')
    current=enter_fields('current')
    if current_equipment is not None and not current_equipment.empty:
        st.caption('Pump signals above were automatically filled from the merged operational CSV. Units require verification.')
    st.divider()
    st.subheader('2. Previous Operations — Before AquaxGo')
    notes('Use the same calendar period before AquaxGo was installed.','Current and previous uploads may have different frequencies.','Historical estimates are allowed but will be labelled as assumptions.')
    st.radio('Input method',['Manual input','CSV / Excel upload'],key='input_previous',horizontal=True)
    st.radio('Data frequency',['Daily','Monthly','Quarterly'],key='freq_previous',horizontal=True)
    if st.session_state.input_previous=='Manual input':
        st.date_input('Previous period',value=(date(2025,7,1),date(2025,8,31)),key='manual_dates_previous')
    st.radio('Historical data source',['Actual historical data','Estimated historical data'],key='source_previous',horizontal=True)
    if st.button('Fill with Demo Data'):
        # Explicit illustrative scenario; never asserted as historical BlueNexus data.
        q=current.get('treated_m3') or 100000
        feed=current.get('influent_m3') or q/0.75
        demo={'treated_m3':q,'influent_m3':q/0.70,'electricity_kwh':q*1.50,'reclaimed_m3':q*0.70/0.75,'customer_m3':q*0.97,'freshwater_withdrawal_m3':(current.get('freshwater_withdrawal_m3') or q*.30)*1.10,'total_water_supply_m3':(current.get('total_water_supply_m3') or q*1.65)*1.10,'conductivity_in_us_cm':current.get('conductivity_in_us_cm') or 2400,'conductivity_out_us_cm':125,'ph_in':8.3,'ph_out':7.2,'downtime_hours':16,'manual_interventions':60,'om_costs':max(12000,(current.get('om_costs') or 8000)*1.25),'pump_runtime_change':(current.get('pump_runtime_change') or 800)*1.10,'pump_frequency':(current.get('pump_frequency') or 48)*1.05,'pump_temperature':(current.get('pump_temperature') or 55)*1.08,'pump_vibration':(current.get('pump_vibration') or 2.8)*1.15}
        for chemical,mass in current.get('chemicals_kg',{}).items():
            demo[CHEM_COLS.get(chemical,'chemical_other_kg')]=mass/0.85
        setfields('previous',demo)
        st.session_state['chemselect_previous']=sorted(set(st.session_state.get('chemselect_previous',[]))|set(cur for cur in current.get('chemicals_kg',{})))
        st.session_state.pending_demo_source=True
        st.session_state.demo_used=True
        st.rerun()
    if st.session_state.get('demo_used'):
        notes('Historical demo assumes 70% water recovery and 1.50 kWh/m³ electricity intensity.',
              'Chemical consumption is assumed 15% lower after AquaxGo, for the same chemical type.',
              'Illustrative downtime baseline: 16 hours; manual interventions baseline: 60.',
              'Illustrative O&M baseline: at least 12,000 or 125% of current costs; compare consistent currency and scope.',
              'Previous equipment demo: runtime counter change +10%, frequency +5%, temperature +8%, vibration +15% versus current (or illustrative fallback).',
              'Equipment signals are not verified reductions in downtime or maintenance costs.',
              'All demo comparisons are illustrative and are not verified AquaxGo-attributable savings.')
    if st.session_state.input_previous=='CSV / Excel upload':parse_upload('previous')
    previous_equipment=equipment_from_merged('previous')
    previous=enter_fields('previous')
    if previous_equipment is not None and not previous_equipment.empty:
        st.caption('Previous pump signals were automatically filled from the uploaded historical merged CSV.')
    st.divider()
    choice=st.session_state.factor_choice
    ef=FACTORS[choice] if FACTORS[choice] is not None else st.session_state.factor_custom
    if st.button('Calculate Sustainability Impact →',type='primary',use_container_width=True):
        missing=[name for name in REQUIRED if current.get(name) is None or previous.get(name) is None]
        if missing:st.error('Complete required current and previous fields: '+', '.join(missing))
        elif not current['influent_m3'] or not current['treated_m3'] or not previous['influent_m3'] or not previous['treated_m3']:st.error('Influent and treated volumes must be greater than zero.')
        elif st.session_state.input_current=='CSV / Excel upload' and st.session_state.get('coverage_current') is None:st.error('Upload complete current data first.')
        elif st.session_state.input_previous=='CSV / Excel upload' and st.session_state.get('coverage_previous') is None:st.error('Upload complete previous data first.')
        else:
            cc=st.session_state.get('coverage_current');pc=st.session_state.get('coverage_previous')
            from datetime import datetime
            def manual_coverage(which):
                dates=st.session_state.get('manual_dates_'+which,())
                if len(dates)!=2:return None
                return {'start':pd.Timestamp(dates[0]),'end':pd.Timestamp(dates[1])}
            cc=cc if st.session_state.input_current=='CSV / Excel upload' else manual_coverage('current')
            pc=pc if st.session_state.input_previous=='CSV / Excel upload' else manual_coverage('previous')
            if not cc or not pc:st.error('Select start and end dates for both periods.')
            elif not matching_periods(cc,pc):st.error('Current and previous periods must cover matching calendar dates in different years.')
            else:
                d=dict(current)
                for name in ['treated_m3','influent_m3','reclaimed_m3','freshwater_withdrawal_m3','electricity_kwh']:
                    d['baseline_'+name]=previous.get(name)
                d['baseline_chemicals_kg']=previous.get('chemicals_kg',{})
                d['grid_ef_kgco2e_kwh']=ef
                if current.get('total_water_supply_m3') and current.get('reclaimed_m3') is not None:
                    d['reclaimed_water_share_pct']=100*current['reclaimed_m3']/current['total_water_supply_m3']
                try:
                    res=calculate(d)
                    # Use period-specific emission factors when a complete EF column is uploaded.
                    source_df=st.session_state.get('selected_current') if st.session_state.input_current=='CSV / Excel upload' else None
                    if source_df is not None and 'grid_ef_kgco2e_kwh' in source_df and source_df['grid_ef_kgco2e_kwh'].notna().all():
                        total_emissions=float((source_df.electricity_kwh*source_df.grid_ef_kgco2e_kwh).sum()/1000)
                        for rr in res:
                            if rr.kpi_id=='C01':rr.value=total_emissions;rr.note='Calculated using each uploaded period emission factor; verify source and year.'
                            if rr.kpi_id=='C02':rr.value=total_emissions*1000/d['treated_m3']
                            if rr.kpi_id=='C03':rr.value=None;rr.note='Baseline emissions comparison needs consistent historical factor methodology.'
                    issues=validate_water_consistency(d)
                    st.session_state.assessment={'current':current,'previous':previous,'inputs':d,'results':res,'issues':issues,'ef':ef,'factor':choice,'estimated':st.session_state.source_previous=='Estimated historical data' or st.session_state.source_current=='Estimated' or st.session_state.get('demo_current_used',False) or st.session_state.get('demo_used',False),'current_df':st.session_state.get('selected_current') if st.session_state.input_current=='CSV / Excel upload' else None,'current_frequency':st.session_state.freq_current,'previous_df':st.session_state.get('selected_previous') if st.session_state.input_previous=='CSV / Excel upload' else None,'previous_frequency':st.session_state.freq_previous,'equipment_current':current_equipment,'equipment_previous':previous_equipment}
                    st.session_state.ready=True
                    go('Sustainability Impact')
                except ValueError as exc:st.error(str(exc))

elif page=='Sustainability Impact':
    st.title('Sustainability Impact')
    if not st.session_state.ready:st.info('Enter current and previous data first.');st.stop()
    a=st.session_state.assessment;cur=a['current'];old=a['previous'];res=a['results'];lookup={r.kpi_id:r.value for r in res}
    def get(k):return lookup.get(k)
    notes('Previous values are shown above Current in every comparison.','Historical comparisons are not proof that AquaxGo caused the difference.','Estimated historical inputs produce illustrative scenario results.' if a['estimated'] else 'Historical data is client-reported, not independently assured.')
    st.header('AquaxGo Improvement Potential')
    # Six impact indicators across sustainability and operational improvements.
    def difference(field):
        before,now=old.get(field),cur.get(field)
        return before-now if before is not None and now is not None else None
    chemical_names=sorted(set(cur.get('chemicals_kg',{}))|set(old.get('chemicals_kg',{})))
    chem_savings={name:get('AI02:'+name) for name in chemical_names}
    def impact_card(title,value,unit,description,theme):
        if value is None:
            metric(title,None,unit,'Enter matching Current and Previous data. '+description,theme)
        elif value>=0:
            metric(title,value,unit,'Estimated improvement vs comparable baseline. '+description,theme)
        else:
            metric(title.replace('Savings','Increase').replace('Reduction','Increase').replace('Improvement','Decline'),abs(value),unit,
                   'Performance worsened vs the baseline; not a saving. '+description,theme)
    chemical_card_value=next(iter(chem_savings.values())) if len(chem_savings)==1 else None
    impact=[('Energy Savings',get('E04'),'kWh','Volume-adjusted electricity difference.','Energy'),
            ('Estimated Scope 2 Emissions Reduction',get('C03'),'tCO₂e','Electricity-related scenario difference; same emission factor assumed. Not a verified AI reduction.','Carbon'),
            ('Chemical Savings',chemical_card_value,'kg','Multiple chemicals are shown separately below.' if len(chem_savings)>1 else 'Chemical-specific comparison.','Chemicals'),
            ('Water Recovery Improvement',get('AI01'),'m³','Additional effluent at current influent volume.','Water'),
            ('Downtime Reduction',difference('downtime_hours'),'hours','Same reporting duration required.','Water'),
            ('Operational Cost Savings',difference('om_costs'),'currency units','Same currency and cost boundary required.','Energy')]
    cards=st.columns(3)
    for i,(name,value,unit,description,theme) in enumerate(impact):
        with cards[i%3]:impact_card(name,value,unit,description,theme)
    if chem_savings:
        st.caption('Chemical savings are reported separately by chemical; different chemical types are not combined.')
        ccols=st.columns(min(3,len(chem_savings)))
        for i,(name,value) in enumerate(chem_savings.items()):
            with ccols[i%len(ccols)]:impact_card(name+' Chemical Savings',value,'kg','Volume-adjusted.','Chemicals')
    manual_diff=difference('manual_interventions')
    if manual_diff is not None:
        st.caption(f'Manual interventions: {fmt(abs(manual_diff),"count")} '+('fewer' if manual_diff>=0 else 'more')+' than previous operations.')
    st.subheader('Before vs After AquaxGo')
    c1,c2=st.columns(2)
    with c1:
        comparison('Energy · Electricity (kWh)',get('E03'),cur.get('electricity_kwh'),'kWh','Energy')
        previous_rate=100*old['treated_m3']/old['influent_m3'];current_rate=get('W03')
        comparison('Water · Recovery rate (%)',previous_rate,current_rate,'%','Water')
        comparison('Maintenance · Downtime',old.get('downtime_hours'),cur.get('downtime_hours'),'hours','Water')
    with c2:
        comparison('Carbon · Electricity-related emissions',get('E03')*a['ef']/1000 if get('E03') is not None else None,get('C01'),'tCO₂e','Carbon')
        for name in chemical_names:
            mass=cur.get('chemicals_kg',{}).get(name);baseline=old.get('chemicals_kg',{}).get(name)
            adjusted=baseline/old['treated_m3']*cur['treated_m3'] if baseline is not None else None
            comparison('Chemicals · '+name,adjusted,mass,'kg','Chemicals')

    ops1,ops2=st.columns(2)
    with ops1:comparison('Operations · Manual Interventions',old.get('manual_interventions'),cur.get('manual_interventions'),'count','Energy')
    with ops2:comparison('Operations · O&M Costs',old.get('om_costs'),cur.get('om_costs'),'currency units','Energy')
    st.subheader('Waterhaus™ Equipment Monitoring — Supporting Evidence')
    notes('Pump runtime, frequency, temperature and vibration are equipment indicators.',
          'Sensor units and runtime-counter units require confirmation.',
          'These signals do not independently prove AI savings or downtime reduction.')
    equipment_charts = [
        ('pump_runtime_change', 'Pump Runtime — Counter Change'),
        ('pump_frequency', 'Pump Frequency — Average'),
        ('pump_temperature', 'Pump Temperature — Average'),
        ('pump_vibration', 'Pump Vibration — Average'),
    ]
    for start in (0, 2):
        left, right = st.columns(2)
        for column, (field, label) in zip((left, right), equipment_charts[start:start + 2]):
            with column:
                comparison(label, old.get(field), cur.get(field), 'unverified units', 'Water')
    ev=a.get('equipment_current')
    if ev is not None and not ev.empty:
        st.dataframe(ev[['Plant','Metric','Value','Unit / status','Valid readings']],hide_index=True,use_container_width=True)
    st.divider();st.header('Current Sustainability Performance')
    header('Water','GRI 303 / AWS 3.0')
    c1,c2,c3=st.columns(3)
    with c1:metric('Effluent water',get('W02'),'m³',theme='Water')
    with c2:metric('Recovery rate',get('W03'),'%','Effluent / influent',theme='Water')
    with c3:metric('Reclaimed water',get('W04'),'m³',theme='Water')
    if get('W10') is not None:
        metric('Reclaimed water share',get('W10'), '%',theme='Water')
    c1,c2=st.columns(2)
    with c1:
        if get('W03') is not None:
            pct=get('W03');fig=plotly_go.Figure(plotly_go.Pie(labels=['Recovered','Other'],values=[max(0,min(100,pct)),max(0,100-pct)],hole=.68,marker_colors=[COLORS['Water'],'#DCECF6'],sort=False))
            fig.update_layout(title='Water Recovery',height=300,margin=dict(l=5,r=5,t=45,b=5),annotations=[dict(text=f'{pct:.1f}%',showarrow=False,font_size=24)])
            st.plotly_chart(fig,use_container_width=True)
    with c2:
        water=[('Influent',get('W01')),('Effluent',get('W02')),('Reclaimed',get('W04'))]
        water=[(n,v) for n,v in water if v is not None]
        if water:
            fig=plotly_go.Figure(plotly_go.Bar(x=[n for n,v in water],y=[v for n,v in water],marker_color=[COLORS['Water'] if i==0 else '#70B3DA' for i in range(len(water))]))
            fig.update_layout(title='Water Volumes',height=300,margin=dict(l=5,r=5,t=45,b=10))
            st.plotly_chart(fig,use_container_width=True)
    st.markdown('**Water Quality**')
    qc=st.columns(3)
    for col,(name,value,unit) in zip(qc,[('Conductivity reduction',get('Q01'),'%'),('Influent pH',get('Q02a'),'pH'),('Effluent pH',get('Q02b'),'pH')]):
        with col:metric(name,value,unit,theme='Water')
    trend(a['current_df'],'treated_m3','Effluent Water Trend','Water',a['current_frequency'])
    header('Energy','GRI 302 / 103')
    c1,c2=st.columns(2)
    with c1:metric('Electricity used',get('E01'),'kWh',theme='Energy')
    with c2:metric('Energy intensity',get('E02'),'kWh/m³',theme='Energy')
    trend(a['current_df'],'electricity_kwh','Electricity Trend','Energy',a['current_frequency'])
    header('Carbon','GRI 305')
    c1,c2=st.columns(2)
    with c1:metric('Scope 2 estimate',get('C01'),'tCO₂e',theme='Carbon')
    with c2:metric('Emissions intensity',get('C02'),'kgCO₂e/m³',theme='Carbon')
    if a['current_df'] is not None and 'electricity_kwh' in a['current_df']:
        temp=a['current_df'].copy();temp['scope2_tco2e']=temp.electricity_kwh*a['ef']/1000
        trend(temp,'scope2_tco2e','Scope 2 Emissions Trend','Carbon',a['current_frequency'])
    header('Chemicals','AWS 3.0 / GRI 303')
    # Operational dosing is a separate evidence view; never treat dose as kg.
    if a['current_df'] is not None:
        dose_table = dosing_summary(a['current_df'])
        if not dose_table.empty:
            st.markdown('### Actual Dosing Performance')
            notes(
                'Automatically read from the uploaded BlueNexus CSV: planned vs actual dosing.',
                'Assumed dose unit: mg/L (engineering assumption only; Data Dictionary v2 does not verify the unit).',
                'Results are mean reported doses for paired valid records, not chemical consumption in kg.',
                'Deviation = (mean actual / mean planned − 1) × 100. Negative means below plan, not verified AI savings.',
                'Coverage counts paired records within the selected facility and reporting period.'
            )
            st.dataframe(dose_table, hide_index=True, use_container_width=True)
            fig = plotly_go.Figure()
            fig.add_bar(name='Planned', x=dose_table['Chemical'], y=dose_table['Planned dose (mean)'], marker_color='#C7B5E5')
            fig.add_bar(name='Actual', x=dose_table['Chemical'], y=dose_table['Actual dose (mean)'], marker_color=COLORS['Chemicals'])
            fig.update_layout(barmode='group', title='Planned vs Actual Dosing (assumed mg/L)',
                              yaxis_title='Mean reported dose (assumed mg/L)',
                              xaxis_tickangle=0, height=360,
                              margin=dict(l=10, r=10, t=55, b=55),
                              legend=dict(orientation='h', y=1.12))
            st.plotly_chart(fig, use_container_width=True)
            low = dose_table.loc[dose_table['Coverage (%)'] < 80, 'Chemical'].tolist()
            if low:
                st.caption('Limited coverage: ' + ', '.join(low) + '. Do not interpret these as full-period chemical performance.')
    st.markdown('### Chemical Consumption & Historical Comparison')
    if chemical_names:
        rows=[]
        for name in chemical_names:
            value=cur.get('chemicals_kg',{}).get(name)
            if value is not None:rows.append({'Chemical':name,'Consumption (kg)':value})
        if rows:
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
            fig=plotly_go.Figure(plotly_go.Bar(y=[r['Chemical'] for r in rows],x=[r['Consumption (kg)'] for r in rows],orientation='h',marker_color=COLORS['Chemicals']))
            fig.update_layout(title='Chemical Consumption by Type',height=max(250,70*len(rows)),margin=dict(l=10,r=10,t=45,b=10))
            st.plotly_chart(fig,use_container_width=True)
    else:st.info('Enter chemical mass by type to show chemical consumption and intensity.')
    for issue in a['issues']:st.warning(issue)

elif page=='GRI / AWS Reporting':
    st.title('GRI / AWS Reporting Centre')
    if not st.session_state.ready:
        st.info('Complete an assessment first.')
        st.stop()
    a=st.session_state.assessment
    notes('See which results are available now.','Review further reporting recommendations and missing evidence.','Download a draft report or the calculation methodology.')

    st.subheader('1. Priority Reporting KPIs')
    st.caption('Core operational results from your assessment. A calculated KPI does not mean a complete GRI/AWS disclosure.')
    priority=build_priority_kpis(a['results'])
    st.dataframe(priority,hide_index=True,use_container_width=True,height=450)
    st.download_button('Download Priority KPIs CSV',priority.to_csv(index=False).encode('utf-8-sig'),file_name='Priority_Reporting_KPIs.csv',mime='text/csv')

    st.subheader('2. Further Reporting Recommendations')
    st.caption('Additional topics from the GRI/AWS research, without repeating priority KPI calculations.')
    further=build_further_recommendations()
    st.dataframe(further,hide_index=True,use_container_width=True,height=410)
    st.download_button('Download Further Recommendations CSV',further.to_csv(index=False).encode('utf-8-sig'),file_name='Further_Reporting_Recommendations.csv',mime='text/csv')

    st.subheader('3. ESG Report Export')
    notes('Draft reporting text uses available calculated results.','Further topics are recommendations, not completed disclosures.','Detailed formulas are in the downloadable appendix.')
    company=st.session_state.get('company','')
    period=st.session_state.get('period_label','')
    report_text=reporting_draft(company,period,a['results'],scenario=a['estimated'])
    st.download_button('Download ESG Reporting Draft',report_text.encode('utf-8'),file_name='BlueNexus_ESG_Reporting_Draft.txt',mime='text/plain')
    try:
        word_bytes=build_esg_report_docx(company,period,a)
        st.download_button('Download ESG Report with Charts (.docx)',word_bytes,
                           file_name='BlueNexus_ESG_Report_Draft.docx',
                           mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    except Exception as exc:
        st.warning('Word report export is unavailable: '+str(exc))
    appendix=methodology_appendix(ROOT/'data'/'KPI_Master_Matrix.csv')
    st.download_button('Download KPI Methodology Appendix',appendix.to_csv(index=False).encode('utf-8-sig'),file_name='KPI_Methodology_Appendix.csv',mime='text/csv')
    with st.expander('Preview reporting narrative'):
        st.write(narrative(company,period,a['estimated']))
    st.caption('GRI 302 references use the 2016 version. Check the reporting-year applicability of newer energy standards. AWS evidence mapping is not certification.')
