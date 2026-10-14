"""Editable ESG report with embedded static charts. Values are taken from the same assessment as the UI."""
from io import BytesIO
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from reporting import build_priority_kpis, build_further_recommendations

BLUE='1769AA'
COLORS={'Water':'#1675B9','Energy':'#D49A12','Carbon':'#238A65','Chemicals':'#8062B5'}

def _number(value):
    try:
        v=float(value)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):return None

def _format(value, unit=''):
    v=_number(value)
    return 'Data required' if v is None else f'{v:,.2f} {unit}'.strip()

def _bar_chart(labels, values, title, color, unit=''):
    clean=[(label,_number(value)) for label,value in zip(labels,values) if _number(value) is not None]
    if not clean:return None
    fig,ax=plt.subplots(figsize=(7.3,2.7))
    names,nums=zip(*clean)
    ys=list(range(len(nums)))
    ax.barh(ys,nums,color=[color if i else '#9BC4DD' for i in range(len(nums))],height=.52)
    ax.set_yticks(ys,names)
    ax.invert_yaxis()  # Previous above Current
    ax.set_title(title,loc='left',fontsize=12,fontweight='bold',color='#123B61',pad=13)
    ax.grid(axis='x',alpha=.15)
    ax.set_axisbelow(True)
    mx=max(nums) if nums else 1
    ax.set_xlim(0,max(mx*1.23,1))
    for y,val in zip(ys,nums):ax.text(val+max(mx*.025,.02),y,_format(val,unit),va='center',fontsize=9)
    for spine in ax.spines.values():spine.set_visible(False)
    fig.tight_layout()
    b=BytesIO();fig.savefig(b,format='png',dpi=165,bbox_inches='tight',facecolor='white');plt.close(fig);b.seek(0)
    return b

def _donut(rate):
    v=_number(rate)
    if v is None or not 0<=v<=100:return None
    fig,ax=plt.subplots(figsize=(4.5,2.8))
    ax.pie([v,100-v],startangle=90,colors=[COLORS['Water'],'#DFEAF2'],counterclock=False,wedgeprops={'width':.28,'edgecolor':'white'})
    ax.text(0,0,f'{v:.1f}%',ha='center',va='center',fontsize=20,color='#123B61',fontweight='bold')
    ax.set_title('Water recovery rate',fontsize=12,color='#123B61',fontweight='bold')
    b=BytesIO();fig.savefig(b,format='png',dpi=165,bbox_inches='tight',facecolor='white');plt.close(fig);b.seek(0)
    return b

def _table(doc,df,limit=None):
    rows=df.head(limit) if limit else df
    t=doc.add_table(rows=1,cols=len(df.columns));t.style='Light Shading Accent 1';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for cell,col in zip(t.rows[0].cells,df.columns):cell.text=str(col)
    for _,r in rows.iterrows():
        for cell,value in zip(t.add_row().cells,r):cell.text=str(value)
    doc.add_paragraph('')

def _chart(doc,image,caption):
    if image is None:return
    doc.add_picture(image,width=Inches(6.45))
    p=doc.add_paragraph(caption);p.style='Caption'

def build_esg_report_docx(company,period,assessment):
    """Generate DOCX bytes. Does not mutate assessment or imply assurance."""
    results=assessment['results']; by={r.kpi_id:r.value for r in results}
    cur=assessment.get('current') or {};old=assessment.get('previous') or {}
    estimated=bool(assessment.get('estimated',False));ef=_number(assessment.get('ef'))
    doc=Document();sec=doc.sections[0];sec.top_margin=Inches(.72);sec.bottom_margin=Inches(.68)
    sec.left_margin=Inches(.85);sec.right_margin=Inches(.85)
    normal=doc.styles['Normal'];normal.font.name='Aptos';normal.font.size=Pt(9)
    normal.paragraph_format.space_after=Pt(6)
    for style,size in [('Title',23),('Heading 1',15),('Heading 2',11)]:
        s=doc.styles[style];s.font.name='Aptos Display';s.font.size=Pt(size);s.font.color.rgb=RGBColor.from_string('123B61')
    doc.add_paragraph('BLUENEXUS  |  WATERHAUS™ + AQUAXGO™','Subtitle')
    doc.add_heading('Sustainability Impact & ESG Reporting Draft',0)
    doc.add_paragraph(f'Client / project: {company or "Not specified"}    |    Reporting period: {period or "Selected period"}')
    doc.add_paragraph('Draft for client review — not an assurance statement or certification.')
    doc.add_heading('1. Executive summary',level=1)
    summary=[('Effluent water',by.get('W02'),'m³'),('Water recovery rate',by.get('W03'),'%'),('Energy intensity',by.get('E02'),'kWh/m³'),('Electricity-related Scope 2 estimate',by.get('C01'),'tCO₂e')]
    for name,value,unit in summary:doc.add_paragraph(f'{name}: {_format(value,unit)}',style='List Bullet')
    doc.add_paragraph('Results describe the selected water-treatment system boundary. They do not automatically represent the client’s complete GRI 303 water balance or Scope 2 inventory.')
    doc.add_heading('2. AquaxGo™ historical comparison',level=1)
    doc.add_paragraph('Previous values are adjusted for current effluent volume where intensity-based comparison is appropriate. Differences are not proof that AquaxGo alone caused the change.')
    if estimated:doc.add_paragraph('BASELINE STATUS: Illustrative / estimated historical data. Scenario results must not be presented as verified AI savings.')
    else:doc.add_paragraph('BASELINE STATUS: Client-reported historical data; comparability and attribution have not been independently verified.')
    current_e=cur.get('electricity_kwh');base_e=by.get('E03')
    _chart(doc,_bar_chart(['Previous (adjusted)','Current'],[base_e,current_e],'Electricity comparison',COLORS['Energy'],'kWh'),'Historical electricity intensity applied to current effluent volume; water quality and operating conditions may differ.')
    previous_rate=100*old['treated_m3']/old['influent_m3'] if _number(old.get('influent_m3')) and _number(old.get('treated_m3')) else None
    _chart(doc,_bar_chart(['Previous','Current'],[previous_rate,by.get('W03')],'Water recovery comparison',COLORS['Water'],'%'),'Recovery = effluent water / influent water; not the same as GRI 303 water consumption.')
    if ef is not None:
        previous_carbon=_number(base_e)*ef/1000 if _number(base_e) is not None else None
        _chart(doc,_bar_chart(['Previous (adjusted)','Current'],[previous_carbon,by.get('C01')],'Electricity-related emissions comparison',COLORS['Carbon'],'tCO₂e'),'Uses the selected emission factor; avoided emissions are separate from actual Scope 2 inventory emissions.')
    cur_chems=cur.get('chemicals_kg') or {};prev_chems=old.get('chemicals_kg') or {}
    for name in sorted(set(cur_chems)|set(prev_chems)):
        base=_number(prev_chems.get(name));new=_number(cur_chems.get(name));oq=_number(old.get('treated_m3'));cq=_number(cur.get('treated_m3'))
        adjusted=base/oq*cq if base is not None and oq and cq is not None else None
        _chart(doc,_bar_chart(['Previous (adjusted)','Current'],[adjusted,new],f'{name} chemical consumption',COLORS['Chemicals'],'kg'),'Chemical-specific mass; historical intensity is adjusted to current effluent volume. Different chemicals are not aggregated.')
    for field,label,unit in [('downtime_hours','Unplanned downtime','hours'),('manual_interventions','Manual interventions','count'),('om_costs','O&M costs','currency units')]:
        _chart(doc,_bar_chart(['Previous','Current'],[old.get(field),cur.get(field)],label,COLORS['Energy'],unit),'Use comparable operating periods and the same measurement boundary. An increase is not a saving.')
    doc.add_heading('3. Current sustainability performance',level=1)
    _chart(doc,_donut(by.get('W03')),'Recovery is a treatment efficiency metric, not freshwater substitution.')
    _chart(doc,_bar_chart(['Influent','Effluent','Reclaimed'],[by.get('W01'),by.get('W02'),by.get('W04')],'Water volumes',COLORS['Water'],'m³'),'These flows are not necessarily additive and may reflect different metering boundaries.')
    for title,keys in [('Water quality',['Q01','Q02a','Q02b']),('Energy and carbon',['E01','E02','C01','C02'])]:
        doc.add_heading(title,level=2)
        for key in keys:
            r=next((x for x in results if x.kpi_id==key),None)
            if r:doc.add_paragraph(f'{r.name}: {_format(r.value,r.unit)}',style='List Bullet')
    doc.add_heading('4. GRI / AWS reporting support',level=1)
    doc.add_paragraph('The tables identify possible disclosure links and outstanding evidence. Calculated KPIs do not establish complete GRI disclosures or AWS certification.')
    priority=build_priority_kpis(results);further=build_further_recommendations()
    # Six columns on landscape appendix pages to preserve readability
    doc.add_heading('Priority reporting KPIs',level=2)
    _table(doc,priority)
    doc.add_heading('Further reporting recommendations',level=2)
    _table(doc,further)
    doc.add_heading('5. Methodology, sources & limitations',level=1)
    for line in [
        'Current operational values: client-uploaded or manually entered water-treatment measurements; source and coverage should be reviewed.',
        'Historical values: client-reported or estimated pre-AquaxGo values; compare like-for-like dates, quality, treatment requirements and equipment boundaries.',
        f'Emission factor: {_format(ef,"kgCO₂e/kWh")}; confirm region, reporting year, source and inventory boundary before disclosure.',
        'Electricity and chemical savings: previous intensity multiplied by current effluent volume, minus actual use.',
        'Quality readings: period averages/representative values; sample-level compliance requires raw test results and applicable limits.',
        'Missing values are not zeros. Claims of avoided emissions or AI attribution require a defensible counterfactual and evidence.',
        'See the separately downloadable KPI Methodology Appendix for formulas and validation rules.'
    ]:doc.add_paragraph(line,style='List Bullet')
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER;footer.text='BlueNexus | Client-facing reporting draft | Review before publication'
    b=BytesIO();doc.save(b);return b.getvalue()
