# backend.py
# v2_2025-08-22: Improved error handling to raise exceptions for Streamlit UI.

import os
import json
import smtplib
import ssl
from email.message import EmailMessage

import gspread
import pandas as pd
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from google.generativeai.types import GenerationConfig

# --- Configuration Loading ---
# This assumes you have a config.py file and a .env file set up correctly
import config

# --- Gemini API Configuration ---
try:
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in config or .env file.")
    genai.configure(api_key=config.GEMINI_API_KEY)
    # Standardize on the more powerful model used in other modules
    gemini_model = genai.GenerativeModel('gemini-2.5-pro')
    print("Backend: Gemini API configured successfully.")
except Exception as e:
    # This initial configuration error is critical, so we'll keep the print statement
    # as it happens on startup, before Streamlit might be fully running.
    print(f"Backend Error: Could not configure Gemini API: {e}")
    gemini_model = None

# --- Module 1: Ingestion Logic (from ingestion.py) ---

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def authenticate_gspread():
    """
    Authenticates with Google Sheets using credentials from config.
    V2 CHANGE: Raises exceptions on failure for the UI to catch.
    """
    try:
        creds_json_str = config.GCP_SERVICE_ACCOUNT_JSON
        if not creds_json_str:
            # Raise an exception that the Streamlit app can display
            raise ValueError("Backend Error: GCP_SERVICE_ACCOUNT_JSON not found in config. Please check your .env file.")
        
        creds_dict = json.loads(creds_json_str)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        print("Backend: Google Sheets authentication successful.")
        return gc
    except json.JSONDecodeError:
        # Raise a specific error for invalid JSON
        raise ValueError("Backend Error: GCP_SERVICE_ACCOUNT_JSON is not valid JSON. Please ensure it's a single, correctly formatted line in your .env file.")
    except Exception as e:
        # Re-raise other exceptions to be caught by the UI
        raise ConnectionError(f"Backend Error: An unexpected error occurred during Google Sheets authentication: {e}")


def get_new_leads(gc: gspread.Client):
    """Fetches new leads from the Google Sheet specified in config."""
    sheet_name = config.GOOGLE_SHEET_NAME
    if not sheet_name:
        raise ValueError("Backend Error: GOOGLE_SHEET_NAME is not set in config.")
    try:
        spreadsheet = gc.open(sheet_name)
        worksheet = spreadsheet.sheet1
        all_records = worksheet.get_all_records()
        if not all_records:
            return pd.DataFrame()

        df = pd.DataFrame(all_records)
        if 'Status' not in df.columns:
            return df # Return all if no Status column
        
        new_leads_df = df[df['Status'].astype(str).str.strip().isin(['', 'New', 'new'])].copy()
        return new_leads_df
    except Exception as e:
        raise IOError(f"Backend Error: An unexpected error occurred while fetching leads: {e}")

def get_column_map(worksheet):
    """Reads the header row and returns a dictionary mapping column names to indices."""
    try:
        headers = worksheet.row_values(1)
        return {header: i + 1 for i, header in enumerate(headers)}
    except Exception as e:
        raise IOError(f"Backend Error: Failed to read header row from sheet: {e}")

# --- Module 2: Enrichment Logic (from enrichment_alt.py) ---

def load_master_prompt() -> str:
    """Loads the deep research prompt from the 'master_prompt.txt' file."""
    try:
        with open('master_prompt.txt', 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Raise an exception so the UI can report the missing file
        raise FileNotFoundError("Backend ERROR: 'master_prompt.txt' not found in the project directory.")

def gather_osint(company_name: str, prospect_name: str, prospect_email: str, prospect_phone: str) -> dict:
    """Performs deep research on a prospect using the Gemini API."""
    if not gemini_model:
        return {"error": "Gemini model is not configured."}

    master_prompt = load_master_prompt()
    # No need to check for empty prompt here, as load_master_prompt now raises an error

    formatted_prompt = master_prompt.format(
        prospect_name=prospect_name,
        company_name=company_name,
        prospect_email=prospect_email,
        prospect_phone=prospect_phone
    )

    try:
        generation_config = GenerationConfig(
            response_mime_type="application/json",
            temperature=0.7,
        )
        response = gemini_model.generate_content(
            formatted_prompt,
            generation_config=generation_config
        )
        return json.loads(response.text)
    except Exception as e:
        # Return a dictionary with an error key, as this happens during the main loop
        # and we want to report it per-lead rather than crashing the whole app.
        print(f"Backend ERROR: Gemini API call failed in gather_osint: {e}")
        return {"error": f"LLM research failed: {e}"}

# --- Module 3: Synthesis Logic (from synthesis.py) ---

MASTER_SYNTHESIS_PROMPT = """
Act as a world-class business intelligence analyst and a direct-response copywriter in the style of Gary Halbert.
Based ONLY on the structured 'Raw Intelligence Report' provided below, generate a concise prospect dossier and a compelling outreach email. Ground all outputs in the provided data. Do not invent facts.

**Raw Intelligence Report:**
```json
{intelligence_report}
```

**Output Instructions:**
You MUST return a single, valid JSON object with the following five keys. Do not return any other text or formatting.

1.  "Prospect_Title": The prospect's most likely job title, inferred from the data.
2.  "Halbert_Hook": A single, specific, and verifiable event, challenge, or announcement from the report (e.g., "their recent $25M Series B funding round for expansion"). This is the reason for your outreach.
3.  "Capital_Need_Hypothesis": A direct, one-sentence statement logically linking the hook to a potential need for working capital or growth financing.
4.  "Selected_Email_Subject": A short, personal, curiosity-driven subject line (e.g., "Question about SpaceX's expansion"). Avoid corporate jargon.
5.  "Selected_Email_Body": An email draft written in the voice of a helpful, high-integrity "Growth Funding Architect".
    - Start with a personal greeting using "[First Name]".
    - Immediately reference the 'Halbert_Hook'.
    - Briefly introduce the value proposition (fast, flexible growth funding).
    - Use short sentences and paragraphs.
    - End with a low-friction, "no-oriented" call-to-action (e.g., "Would you be opposed to a brief introductory call next week?").
    - **Use "[First Name]" as a placeholder for the prospect's first name only.**
"""

def extract_first_name(full_name: str) -> str:
    """Extracts the first name from a full name."""
    if not full_name or not isinstance(full_name, str):
        return "there"
    return full_name.split()[0]

def create_outreach_assets(intelligence_report: dict, prospect_name: str):
    """Uses the Gemini API to generate a dossier and email."""
    if not gemini_model:
        return {"error": "Gemini model is not configured."}
    if not intelligence_report or "error" in intelligence_report:
        return {"error": f"Invalid intelligence report received: {intelligence_report.get('error', 'N/A')}"}

    first_name = extract_first_name(prospect_name)
    
    try:
        report_str = json.dumps(intelligence_report, indent=2)
        prompt = MASTER_SYNTHESIS_PROMPT.format(intelligence_report=report_str)
        
        generation_config = GenerationConfig(response_mime_type="application/json")
        response = gemini_model.generate_content(prompt, generation_config=generation_config)
        
        generated_assets = json.loads(response.text)
        
        if 'Selected_Email_Body' in generated_assets:
            generated_assets['Selected_Email_Body'] = generated_assets['Selected_Email_Body'].replace("[First Name]", first_name)
        
        return generated_assets
    except Exception as e:
        print(f"Backend ERROR: Gemini API call failed in create_outreach_assets: {e}")
        return {"error": f"LLM synthesis failed: {e}"}

# --- Module 4: Dispatch Logic (from dispatch.py) ---

def send_email(recipient_email: str, subject: str, body: str):
    """Connects to a Google SMTP server and sends an email."""
    if not all([config.SENDER_EMAIL, config.SENDER_APP_PASSWORD]):
        print("Backend Error: SENDER_EMAIL or SENDER_APP_PASSWORD not set in config.")
        return False
    if not all([recipient_email, subject, body]):
        print("Backend Error: Missing recipient, subject, or body for email dispatch.")
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = config.SENDER_EMAIL
    msg['To'] = recipient_email
    
    signature = f"""
-- 
Sincerely,

Graham Gordon
FastCapitalNYC.com
Growth Funding Architect
(o)(917) 745-3378
info@fastcapitalnyc.com
Apply for Funding
"""
    full_body = body + "\n\n" + signature
    msg.set_content(full_body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT, context=context) as server:
            server.login(config.SENDER_EMAIL, config.SENDER_APP_PASSWORD)
            server.send_message(msg)
        print(f"Backend: Email sent successfully to {recipient_email}.")
        return True
    except Exception as e:
        print(f"Backend ERROR: Failed to send email: {e}")
        return False

# --- NEW: Google Sheet Update Function (Moved from app.py) ---

def update_google_sheet(gspread_client, row_index, status, dossier, email_assets, col_map):
    """Updates a single lead's row in the Google Sheet with the results."""
    try:
        spreadsheet = gspread_client.open(config.GOOGLE_SHEET_NAME)
        worksheet = spreadsheet.sheet1

        cells_to_update = [
            gspread.Cell(row_index, col_map['Status'], status),
            gspread.Cell(row_index, col_map['Prospect_Title'], email_assets.get('Prospect_Title', '')),
            gspread.Cell(row_index, col_map['Halbert_Hook'], email_assets.get('Halbert_Hook', '')),
            gspread.Cell(row_index, col_map['Capital_Need_Hypothesis'], email_assets.get('Capital_Need_Hypothesis', '')),
            gspread.Cell(row_index, col_map['Selected_Email_Subject'], email_assets.get('Selected_Email_Subject', '')),
            gspread.Cell(row_index, col_map['Selected_Email_Body'], email_assets.get('Selected_Email_Body', ''))
        ]

        # Safely add JSON data if the columns exist
        if 'Dossier_JSON' in col_map:
            cells_to_update.append(
                gspread.Cell(row_index, col_map['Dossier_JSON'], json.dumps(dossier, indent=2))
            )
        if 'Sources' in col_map:
            sources_data = dossier.get('dossier', {}).get('sources', [])
            cells_to_update.append(
                gspread.Cell(row_index, col_map['Sources'], json.dumps(sources_data, indent=2))
            )

        worksheet.update_cells(cells_to_update)
        return True, f"Successfully updated row {row_index} with status '{status}'."
    except Exception as e:
        # Return a tuple for consistent error handling in the UI
        return False, f"Failed to update sheet: {e}"
