# IndiaMART AI Title Studio (Streamlit)

## Files
- `app.py`: Streamlit UI and Gemini Interactions API integration
- `requirements.txt`: Python dependencies

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (recommended).
4. Install dependencies:
   `pip install -r requirements.txt`
5. Set your API key as an environment variable.

   Windows PowerShell:
   `$env:GEMINI_API_KEY="YOUR_REAL_GEMINI_API_KEY"`

   macOS/Linux:
   `export GEMINI_API_KEY="YOUR_REAL_GEMINI_API_KEY"`

6. Run:
   `streamlit run app.py`

## Deploy to Streamlit Community Cloud
1. Create a private or public GitHub repository and upload `app.py` and `requirements.txt`.
2. Go to https://share.streamlit.io/ and deploy the repository.
3. In the deployed app, open **Settings / Manage app → Secrets**.
4. Add this TOML secret:
   `GEMINI_API_KEY = "YOUR_REAL_GEMINI_API_KEY"`
5. Save and reboot the app.

Never commit your API key to GitHub or paste it into `app.py`.

## Model and access
This app uses Gemini Interactions API with `gemini-3.8-flash`.
If Google denies access to your project (HTTP 403), the app cannot bypass that restriction.
Check your project and API key in https://aistudio.google.com/app/apikey or contact Google support.

## Assignment evaluation
Test the six supplied examples plus edge cases:
- missing specifications
- obvious spelling errors
- unsupported claims
- conflicting material details (e.g. product name says plastic but Material says stainless steel)
