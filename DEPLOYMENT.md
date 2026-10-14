# Publish on Streamlit Community Cloud

1. Create a NEW GitHub repository named `bluenexus-esg-platform` (do not overwrite another site).
2. Upload the contents of this folder to the repository ROOT, including `app.py`, `requirements.txt`, `assets/`, `data/`, and `.streamlit/config.toml`.
3. Visit https://share.streamlit.io/ and sign in with GitHub.
4. Choose **Create app** / **Deploy**, select your repository and branch `main`, and set the main file path to `app.py`.
5. Deploy, then open the resulting `*.streamlit.app` URL and test the data upload and Word export.

## Public-demo precautions
- Included example CSV files are illustrative/synthetic. Do not upload confidential Plant A/B or customer files to a public repository.
- Uploaded operational data may be processed by the hosting platform; do not use confidential customer data in this public demonstration without approval and suitable controls.
- This is a proof of concept, not a verified ESG assurance or AWS certification service.
- If deployment fails, inspect Streamlit app logs and verify Python package installation.
