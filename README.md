# IndiaMART AI Title Studio — Streamlit

## Local setup
1. Python 3.10+.
2. `pip install -r requirements.txt`
3. Set `GEMINI_API_KEY` as an environment variable.
4. Run `streamlit run app.py`.

Windows PowerShell:
`$env:GEMINI_API_KEY="YOUR_REAL_GEMINI_API_KEY"`

macOS/Linux:
`export GEMINI_API_KEY="YOUR_REAL_GEMINI_API_KEY"`

## Streamlit Community Cloud
Upload `app.py` and `requirements.txt` to GitHub, deploy at https://share.streamlit.io/, then add this in app Settings > Secrets:

`GEMINI_API_KEY = "YOUR_REAL_GEMINI_API_KEY"`

Never commit the key to GitHub or place it in app.py.

## Faster generation
The app reuses a cached Gemini client and requests a short output with low thinking. Network latency and provider access still affect timing. If the Google project returns HTTP 403, changing UI or latency settings cannot bypass the denial.

## Features
- Six assignment sample products
- High-contrast, accessible form text
- Basic explicit material-conflict check
- Concise output generation settings
- Responsive layout and title preview
