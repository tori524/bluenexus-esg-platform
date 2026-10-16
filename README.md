# BlueNexus ESG Impact & Reporting — Public Demo

Streamlit prototype for Waterhaus™ operational KPIs, illustrative AquaxGo™ baseline comparisons, and GRI/AWS-aligned reporting drafts.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

See [DEPLOYMENT.md](DEPLOYMENT.md) for Streamlit Community Cloud instructions.

## Data privacy

Only synthetic demonstration CSV files are bundled. Do not commit or upload proprietary BlueNexus or client operating records without permission. Baseline estimates are illustrative, not verified AI savings.

## Chemical dosing evidence (v13.1)
Upload BlueNexus `plant_daily_performance.csv` or its cleaned version using Current Operations -> CSV / Excel upload. The Sustainability Impact -> Chemicals section automatically shows paired planned and actual dosing values, percentage deviation, and record coverage. The reported dose unit is **unverified** by Data Dictionary v2; mg/L is an explicit *assumption for visual labelling only*. Dosing is never converted to kg or claimed as verified AI chemical savings. The separate chemical consumption (kg) workflow remains available.


Equipment monitoring: upload Plant A/B equipment CSV separately in Current/Previous Operations or use the private merged CSV. Pump runtime counter change and average frequency/temperature/vibration signals are supporting evidence only; units are unverified. Demo previous equipment values are synthetic. The real merged CSV is not bundled for public GitHub upload.


### v13.4 - Single merged CSV workflow
Upload one merged operational CSV in Current or Previous Data Input. Equipment pump runtime, frequency, temperature and vibration are extracted from that same file (where present) and shown under the separate grey-blue Waterhaus™ Operations section. The standalone equipment CSV uploader has been removed. These equipment signals are supporting evidence and are **not** a fifth ESG dimension. Unverified sensor units remain labelled accordingly.
