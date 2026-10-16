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
