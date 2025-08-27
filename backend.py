# backend.py
# v3_2025-08-25: Switch to google-genai SDK + proper Google Search grounding (Gemini 2.5).
# - Replaces deprecated google.generativeai usage that caused AttributeError: 'Tool'
# - Keeps all public function signatures used by app.py intact.

import os
import json
import smtplib
import ssl
from email.message import EmailMessage
from typing import Dict, Any, List

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# ── New: Google GenAI SDK (GA) ────────────────────────────────────────────────
# Docs: https://ai.google.dev/gemini-api/docs/libraries
# Grounding tool usage: https://ai.google.dev/gemini-api/docs/google-search
from google import genai
from google.genai import types

# --- Configuration Loading ---
import config


# ──────────────────────────────────────────────────────────────────────────────
# Gemini / GenAI client
# ──────────────────────────────────────────────────────────────────────────────
GENAI_CLIENT = None
MODEL_ID = getattr(config, "GEMINI_MODEL_ID", "gemini-2.5-pro")  # 2.5 Pro supports Search grounding

try:
    if not getattr(config, "GEMINI_API_KEY", None):
        raise ValueError("GEMINI_API_KEY not found in config or .env file.")
    # Use Developer API with API key (works with Search tool)
    GENAI_CLIENT = genai.Client(api_key=config.GEMINI_API_KEY)
    print("Backend: GenAI client configured (google-genai).")
except Exception as e:
    print(f"Backend Error: Could not configure GenAI client: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Google Sheets (Ingestion)
# ──────────────────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# This is the canonical list of headers the application expects to find in the Google Sheet.
# The order defined here is the order in which they will be created if they are missing.
REQUIRED_HEADERS = [
    # Input columns
    "Prospect_Name",
    "Company_Name",
    "Prospect_Email",
    "Prospect_Phone",
    # Output columns
    "Status",
    "Prospect_Title",
    "Halbert_Hook",
    "Capital_Need_Hypothesis",
    "Selected_Email_Subject",
    "Selected_Email_Body",
    "Dossier_JSON",
    "Sources"
]


def authenticate_gspread():
    """
    Authenticates with Google Sheets using credentials from config.
    Raises exceptions for the Streamlit UI to surface.
    """
    try:
        creds_json_str = config.GCP_SERVICE_ACCOUNT_JSON
        if not creds_json_str:
            raise ValueError("Backend Error: GCP_SERVICE_ACCOUNT_JSON not found in config. Please check your .env file.")

        creds_dict = json.loads(creds_json_str)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        print("Backend: Google Sheets authentication successful.")
        return gc
    except json.JSONDecodeError:
        raise ValueError("Backend Error: GCP_SERVICE_ACCOUNT_JSON is not valid JSON. Ensure single-line, valid JSON in .env.")
    except Exception as e:
        raise ConnectionError(f"Backend Error: Unexpected error during Google Sheets authentication: {e}")


def ensure_headers(worksheet: gspread.Worksheet, headers_to_ensure: List[str]):
    """
    Ensures the first row of the worksheet contains all required headers.
    If any headers are missing, they are appended to the first row.
    Returns a tuple (success: bool, message: str).
    """
    try:
        # Get existing headers. gspread returns None for empty cells at the end, so filter them out.
        existing_headers = [h for h in worksheet.row_values(1) if h]

        # Use a set for efficient checking of what's already there
        existing_headers_set = set(existing_headers)
        missing_headers = [h for h in headers_to_ensure if h not in existing_headers_set]

        if missing_headers:
            print(f"Backend: Missing headers found: {missing_headers}. Appending them to the sheet.")
            # The new header row is the existing one plus the new ones
            new_header_row = existing_headers + missing_headers

            # Create a list of gspread.Cell objects to update the first row
            # This is more robust than updating a range by A1 notation.
            cell_list = [gspread.Cell(1, i + 1, value) for i, value in enumerate(new_header_row)]
            worksheet.update_cells(cell_list)

            print("Backend: Headers updated successfully.")
            return True, "Headers were missing and have been successfully added."
        else:
            print("Backend: All required headers are present.")
            return True, "All required headers are already present."

    except Exception as e:
        error_message = f"Backend Error: Failed to ensure headers in Google Sheet: {e}"
        print(error_message)
        return False, error_message


def get_new_leads(worksheet: gspread.Worksheet) -> pd.DataFrame:
    """Fetch new leads from the provided Google Sheet worksheet."""
    try:
        all_records = worksheet.get_all_records()
        if not all_records:
            return pd.DataFrame()

        df = pd.DataFrame(all_records)

        # ensure_headers() guarantees the 'Status' column exists in the sheet.
        # If no lead has a status yet, the column might be missing from the dataframe records.
        # In this case, all leads are considered new and we can return the full dataframe.
        if "Status" not in df.columns:
            return df

        # Filter for leads with an empty or "New" status.
        new_leads_df = df[df["Status"].astype(str).str.strip().isin(["", "New", "new"])].copy()
        return new_leads_df
    except Exception as e:
        raise IOError(f"Backend Error: Unexpected error while fetching leads from worksheet: {e}")


def get_column_map(worksheet: gspread.Worksheet) -> Dict[str, int]:
    """Read the header row and return a dict mapping column names to indices (1-based)."""
    try:
        headers = worksheet.row_values(1)
        return {header: i + 1 for i, header in enumerate(headers)}
    except Exception as e:
        raise IOError(f"Backend Error: Failed to read header row from sheet: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Enrichment (OSINT) with Google Search grounding
# ──────────────────────────────────────────────────────────────────────────────

def load_master_prompt() -> str:
    """Load the deep research prompt from 'master_prompt.txt'."""
    try:
        with open("master_prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError("Backend ERROR: 'master_prompt.txt' not found in the project directory.")

def load_direct_marketing_samples() -> str:
    """Load direct marketing samples from 'direct_marketing_samples.txt'."""
    try:
        with open("direct_marketing_samples.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("Backend WARNING: 'direct_marketing_samples.txt' not found. Proceeding without it.")
        return ""

def load_successful_emails() -> str:
    """Load successful email templates from 'successful_emails.txt'."""
    try:
        with open("successful_emails.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("Backend WARNING: 'successful_emails.txt' not found. Proceeding without it.")
        return ""

def _extract_sources_from_grounding(response) -> List[Dict[str, str]]:
    """
    Extract grounded web sources from response.candidates[0].grounding_metadata.grounding_chunks.
    Returns [{'title': str, 'uri': str}, ...] if present, else [].
    """
    try:
        if not response or not hasattr(response, "candidates") or not response.candidates:
            return []
        cand = response.candidates[0]
        gm = getattr(cand, "grounding_metadata", None)
        if not gm:
            return []
        sources = []
        for ch in getattr(gm, "grounding_chunks", []) or []:
            web = getattr(ch, "web", None)
            if web and getattr(web, "uri", None):
                sources.append({
                    "title": getattr(web, "title", "") or "",
                    "uri": getattr(web, "uri", ""),
                })
        return sources
    except Exception:
        return []

def gather_osint(company_name: str, prospect_name: str, prospect_email: str, prospect_phone: str) -> Dict[str, Any]:
    """
    Perform deep research on a prospect using Gemini 2.5 with Google Search grounding.
    Returns a dict parsed from model JSON and augments with 'dossier.sources' from grounding metadata (if present).
    """
    if GENAI_CLIENT is None:
        return {"error": "GenAI client is not configured. Check GEMINI_API_KEY and google-genai installation."}

    master_prompt = load_master_prompt()
    formatted_prompt = master_prompt.format(
        prospect_name=prospect_name or "",
        company_name=company_name or "",
        prospect_email=prospect_email or "",
        prospect_phone=prospect_phone or "",
    )

    try:
        # Enable Google Search grounding tool (new SDK).
        grounding_tool = types.Tool(google_search=types.GoogleSearch())

        gen_config = types.GenerateContentConfig(
            tools=[grounding_tool],
            temperature=0.2,
        )

        response = GENAI_CLIENT.models.generate_content(
            model=MODEL_ID,
            contents=formatted_prompt,
            config=gen_config,
        )

        # Parse model JSON
        _resp_text = getattr(response, "text", "") or ""
        if not _resp_text.strip():
            # If the model returned no direct text (can happen with tool use), fall back to an empty JSON object
            _resp_text = "{}"
        try:
            data = json.loads(_resp_text)
        except Exception:
            # Be permissive: keep the raw text so downstream synthesis can still proceed
            data = {"dossier": {"summary": _resp_text}}

        # Attach grounded sources into the expected location if present
        sources = _extract_sources_from_grounding(response)
        if sources:
            if isinstance(data, dict):
                if "dossier" in data and isinstance(data["dossier"], dict):
                    data["dossier"].setdefault("sources", sources)
                else:
                    data.setdefault("dossier", {})
                    data["dossier"].setdefault("sources", sources)

        return data

    except Exception as e:
        print(f"Backend ERROR: GenAI call failed in gather_osint: {e}")
        return {"error": f"LLM research failed: {e}"}


# ──────────────────────────────────────────────────────────────────────────────
# Synthesis (email + dossier condensation)
# ──────────────────────────────────────────────────────────────────────────────
MASTER_SYNTHESIS_PROMPT = """
Act as a world-class business intelligence analyst and a direct-response copywriter.
Your task is to generate a concise prospect dossier and a compelling outreach email based ONLY on the provided 'Raw Intelligence Report'.

**Exemplary Sales Letters for Stylistic and Tonal Reference:**
```
{marketing_samples}
```

**Proven Email Structures (Examples of successful emails):**
```
{successful_emails}
```

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
    if not full_name or not isinstance(full_name, str):
        return "there"
    return full_name.split()[0]

def create_outreach_assets(intelligence_report: Dict[str, Any], prospect_name: str) -> Dict[str, Any]:
    """
    Generate a condensed dossier + email assets from the prior OSINT report.
    Uses structured JSON output; no grounding tool here (synthesis only).
    """
    if GENAI_CLIENT is None:
        return {"error": "GenAI client is not configured. Check GEMINI_API_KEY and google-genai installation."}
    if not intelligence_report or ("error" in intelligence_report):
        return {"error": f"Invalid intelligence report received: {intelligence_report.get('error', 'N/A')}"}

    # Load the new context files
    marketing_samples = load_direct_marketing_samples()
    successful_emails = load_successful_emails()
    first_name = extract_first_name(prospect_name)

    try:
        report_str = json.dumps(intelligence_report, indent=2)
        prompt = MASTER_SYNTHESIS_PROMPT.format(
            intelligence_report=report_str,
            marketing_samples=marketing_samples,
            successful_emails=successful_emails
        )

        gen_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        )

        response = GENAI_CLIENT.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=gen_config,
        )

        generated_assets = json.loads(response.text)

        if "Selected_Email_Body" in generated_assets:
            generated_assets["Selected_Email_Body"] = generated_assets["Selected_Email_Body"].replace("[First Name]", first_name)

        return generated_assets
    except Exception as e:
        print(f"Backend ERROR: GenAI call failed in create_outreach_assets: {e}")
        return {"error": f"LLM synthesis failed: {e}"}


# ──────────────────────────────────────────────────────────────────────────────
# Dispatch (Email)
# ──────────────────────────────────────────────────────────────────────────────

def send_email(recipient_email: str, subject: str, body: str) -> bool:
    """Send email via SMTP using creds from config."""
    if not all([config.SENDER_EMAIL, config.SENDER_APP_PASSWORD]):
        print("Backend Error: SENDER_EMAIL or SENDER_APP_PASSWORD not set in config.")
        return False
    if not all([recipient_email, subject, body]):
        print("Backend Error: Missing recipient, subject, or body for email dispatch.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.SENDER_EMAIL
    msg["To"] = recipient_email

    signature = """
-- 
Sincerely,

Graham Gordon
FastCapitalNYC.com
Growth Funding Architect
(o)(917) 745-3378
info@fastcapitalnyc.com
Apply for Funding
""".strip("\n")
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


# ──────────────────────────────────────────────────────────────────────────────
# Sheet Update
# ──────────────────────────────────────────────────────────────────────────────

def update_google_sheet(worksheet: gspread.Worksheet, row_index: int, status: str, dossier: Dict, email_assets: Dict, col_map: Dict[str, int]):
    """Update a single lead row with results in the provided worksheet."""
    try:
        cells_to_update = [
            gspread.Cell(row_index, col_map["Status"], status),
            gspread.Cell(row_index, col_map["Prospect_Title"], email_assets.get("Prospect_Title", "")),
            gspread.Cell(row_index, col_map["Halbert_Hook"], email_assets.get("Halbert_Hook", "")),
            gspread.Cell(row_index, col_map["Capital_Need_Hypothesis"], email_assets.get("Capital_Need_Hypothesis", "")),
            gspread.Cell(row_index, col_map["Selected_Email_Subject"], email_assets.get("Selected_Email_Subject", "")),
            gspread.Cell(row_index, col_map["Selected_Email_Body"], email_assets.get("Selected_Email_Body", "")),
        ]

        # Safely add JSON data if the columns exist
        if "Dossier_JSON" in col_map:
            cells_to_update.append(
                gspread.Cell(row_index, col_map["Dossier_JSON"], json.dumps(dossier, indent=2))
            )
        if "Sources" in col_map:
            # Prefer nested dossier.sources if present
            sources_data = []
            if isinstance(dossier, dict):
                sources_data = (
                    dossier.get("dossier", {}).get("sources")
                    or dossier.get("sources")
                    or []
                )
            cells_to_update.append(
                gspread.Cell(row_index, col_map["Sources"], json.dumps(sources_data, indent=2))
            )

        worksheet.update_cells(cells_to_update)
        return True, f"Successfully updated row {row_index} with status '{status}'."
    except Exception as e:
        return False, f"Failed to update sheet: {e}"
