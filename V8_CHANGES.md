# v8 changes and demo notes

- Landing hero now includes an in-hero Start Your Assessment link, short bullet copy, four metric/standard labels and BlueNexus contact information. No extracted logo.
- Sustainability Impact opens with five AquaxGo comparison areas and now provides six separate historical comparison charts: electricity, recovery rate, chemical mass, electricity-related carbon, downtime and manual interventions/O&M cost.
- Current Sustainability Performance includes a water-recovery donut, water volumes, daily electricity, treated-water, estimated Scope 2, reclaimed-water trends, and chemical mass/intensity when provided.
- All demo baseline inputs are **assumptions**: previous recovery 70%, previous energy intensity 1.50 kWh/m3. The demo-only button additionally fills synthetic chemical, downtime, intervention and O&M examples. These are not BlueNexus historical observations or independently verified AI savings.
- Chemical kg values must be supplied separately; the sample `dose_reported` fields are not treated as measured mass.
- Previous and current should use the same calendar duration. Energy and chemicals are adjusted by current treated volume; water recovery is compared as a rate. Changes in salinity, product quality and equipment are not controlled.

## Test results

- Python syntax: passed.
- Existing calculation unit tests: 5 passed.
- Plant A/B sample input and calculation smoke tests: passed for recovery, SEC, electricity difference, additional treated output, chemical difference (synthetic), Scope 2 (illustrative EF).
- Browser interaction / Streamlit rendering: not tested in this environment because Streamlit is not installed and network package installation is unavailable. Please test on your Mac.
