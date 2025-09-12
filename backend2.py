# backend2.py
# v3_2025-09-02: Migrate to google-genai Client API + fix model calls
# - Replaces legacy genai.configure() + GenerativeModel usage with genai.Client
# - Uses Google Search grounding tool via types.Tool(google_search=...)
# - Preserves enhanced synthesis prompt + EMAIL_GENERATION_RULES usage
# - Matches backend.py patterns while keeping backend2 customizations

import os
import json
import smtplib
import ssl
from email.message import EmailMessage
from typing import Dict, Any, List

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# ── Google GenAI SDK (GA) ────────────────────────────────────────────────────
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
MODEL_ID = getattr(config, "GEMINI_MODEL_ID", "gemini-2.5-pro")  # 2.5 Pro and Flash both support Search grounding

try:
    if not getattr(config, "GEMINI_API_KEY", None):
        raise ValueError("GEMINI_API_KEY not found in config or .env file.")
    # New SDK pattern: instantiate a client instead of genai.configure(...)
    GENAI_CLIENT = genai.Client(api_key=config.GEMINI_API_KEY)
    print("backend2: GenAI client configured (google-genai).")
except Exception as e:
    print(f"backend2 Error: Could not configure GenAI client: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# Google Sheets (Ingestion)
# ──────────────────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Canonical headers expected in the Google Sheet
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
    "Sources",
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
        print("backend2: Google Sheets authentication successful.")
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
        existing_headers = [h for h in worksheet.row_values(1) if h]
        existing_headers_set = set(existing_headers)
        missing_headers = [h for h in headers_to_ensure if h not in existing_headers_set]

        if missing_headers:
            print(f"backend2: Missing headers found: {missing_headers}. Appending them to the sheet.")
            new_header_row = existing_headers + missing_headers
            cell_list = [gspread.Cell(1, i + 1, value) for i, value in enumerate(new_header_row)]
            worksheet.update_cells(cell_list)
            return True, "Headers were missing and have been successfully added."
        else:
            return True, "All required headers are already present."

    except Exception as e:
        error_message = f"Backend Error: Failed to ensure headers in Google Sheet: {e}"
        print(error_message)
        return False, error_message


def prepare_worksheet_from_mapping(
    worksheet: gspread.Worksheet,
    user_mapping: Dict[str, str],
    required_headers: List[str],
) -> Dict[str, int]:
    """
    Processes the user's column mapping, creates new columns if needed,
    and returns a final map of required header -> column index (1-based).
    """
    try:
        current_headers = worksheet.row_values(1)
    except gspread.exceptions.GSpreadException as e:
        if "exceeds grid limits" in str(e):
            current_headers = []
        else:
            raise

    new_cols_to_add = []
    for req_col, mapped_val in user_mapping.items():
        create_option_str = f"[Create '{req_col}' Column]"
        if mapped_val == create_option_str and req_col not in current_headers:
            new_cols_to_add.append(req_col)

    if new_cols_to_add:
        start_col_index = len(current_headers) + 1
        cells_to_update = [gspread.Cell(1, start_col_index + i, col_name) for i, col_name in enumerate(new_cols_to_add)]
        if cells_to_update:
            worksheet.update_cells(cells_to_update, value_input_option='RAW')
            print(f"backend2: Added new columns: {new_cols_to_add}")
        current_headers = worksheet.row_values(1)

    final_column_map = {}
    for req_header in required_headers:
        sheet_col_name = user_mapping.get(req_header)
        if not sheet_col_name:
            raise ValueError(f"Mapping for required header '{req_header}' is missing.")
        if sheet_col_name.startswith("[Create"):
            sheet_col_name = req_header
        try:
            col_index = current_headers.index(sheet_col_name) + 1
            final_column_map[req_header] = col_index
        except ValueError:
            raise ValueError(f"Column '{sheet_col_name}' (mapped to '{req_header}') not found in the sheet.")
    return final_column_map


def get_new_leads(worksheet: gspread.Worksheet, user_mapping: Dict[str, str]) -> pd.DataFrame:
    """
    Fetches all records, renames columns based on user mapping,
    and filters for new leads (where Status is empty or "New").
    """
    try:
        all_records = worksheet.get_all_records(head=1)
        if not all_records:
            return pd.DataFrame()

        df = pd.DataFrame.from_records(all_records)

        rename_map = {}
        for req_col, mapped_val in user_mapping.items():
            sheet_col = mapped_val.replace(f"[Create '{req_col}' Column]", req_col)
            if sheet_col in df.columns:
                rename_map[sheet_col] = req_col

        df.rename(columns=rename_map, inplace=True)

        if "Status" not in df.columns:
            return df

        new_leads_df = df[
            df["Status"].fillna("").astype(str).str.strip().str.lower().isin(["", "new"])
        ].copy()

        return new_leads_df
    except Exception as e:
        raise IOError(f"Backend Error: Unexpected error while fetching leads: {e}")


def get_column_map(worksheet: gspread.Worksheet) -> Dict[str, int]:
    """Read the header row and return a dict mapping column names to indices (1-based)."""
    try:
        headers = worksheet.row_values(1)
        return {header: i + 1 for i, header in enumerate(headers) if header}
    except Exception as e:
        raise IOError(f"Backend Error: Failed to read header row from sheet: {e}")

def should_skip_lead(lead: pd.Series, skip_rules: List[Dict[str, Any]]) -> (bool, str):
    """
    Checks if a lead should be skipped based on the defined rules.
    Returns a tuple (should_skip, reason).
    """
    for rule in skip_rules:
        column_to_check = rule.get("column")
        keywords = rule.get("keywords", [])
        if column_to_check and column_to_check in lead and keywords:
            lead_value = str(lead[column_to_check]).lower()
            for keyword in keywords:
                if keyword.lower() in lead_value:
                    return True, f"Skipped because column '{column_to_check}' contained keyword '{keyword}'"
    return False, ""

def process_leads_for_review(worksheet: gspread.Worksheet, user_mapping: Dict[str, str]):
    """
    Fetches new leads, enriches them, generates email drafts, and updates the sheet
    with a 'REVIEW_PENDING' status.
    """
    print("backend2: Starting lead processing for review...")
    final_column_map = prepare_worksheet_from_mapping(worksheet, user_mapping, REQUIRED_HEADERS)
    new_leads_df = get_new_leads(worksheet, user_mapping)

    if new_leads_df.empty:
        print("backend2: No new leads to process.")
        return "No new leads found to process."

    processed_count = 0
    for index, row in new_leads_df.iterrows():
        sheet_row_index = index + 2
        prospect_name = row.get("Prospect_Name", "")
        company_name = row.get("Company_Name", "")
        prospect_email = row.get("Prospect_Email", "")
        prospect_phone = row.get("Prospect_Phone", "")

        print(f"backend2: Processing row {sheet_row_index}: {prospect_name} at {company_name}")

        dossier = gather_osint(company_name, prospect_name, prospect_email, prospect_phone)
        if dossier.get("error"):
            update_google_sheet(worksheet, sheet_row_index, f"Research Failed: {dossier['error']}", {}, {}, final_column_map)
            continue

        email_assets = create_outreach_assets(dossier, prospect_name)
        if email_assets.get("error"):
            update_google_sheet(worksheet, sheet_row_index, f"Synthesis Failed: {email_assets['error']}", dossier, {}, final_column_map)
            continue

        update_google_sheet(
            worksheet,
            sheet_row_index,
            "REVIEW_PENDING",
            dossier,
            email_assets,
            final_column_map,
        )
        processed_count += 1

    summary = f"Processed {processed_count} new leads. They are now ready for review."
    print(f"backend2: {summary}")
    return summary


def get_leads_for_review(worksheet: gspread.Worksheet) -> List[Dict[str, Any]]:
    """
    Fetches leads with 'REVIEW_PENDING' status for display in the UI.
    Returns a list of dicts, including the original row index.
    """
    all_records = worksheet.get_all_records(head=1)
    df = pd.DataFrame.from_records(all_records)
    review_df = df[df["Status"].fillna("").str.strip().str.lower() == "review_pending"].copy()

    # Add original sheet row index (pandas index is 0-based, sheet is 1-based with a header)
    review_df['sheet_row_index'] = review_df.index + 2
    return review_df.to_dict('records')


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
        print("backend2 WARNING: 'direct_marketing_samples.txt' not found. Proceeding without it.")
        return ""


def load_successful_emails() -> str:
    """Load successful email templates from 'successful_emails.txt'."""
    try:
        with open("successful_emails.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("backend2 WARNING: 'successful_emails.txt' not found. Proceeding without it.")
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
        _resp_text = getattr(response, "text", "")
        if not _resp_text:
            _resp_text = "{}"
        try:
            data = json.loads(_resp_text)
        except Exception:
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
        print(f"backend2 ERROR: GenAI call failed in gather_osint: {e}")
        return {"error": f"LLM research failed: {e}"}


# ──────────────────────────────────────────────────────────────────────────────
# Synthesis (email + dossier condensation)
# ──────────────────────────────────────────────────────────────────────────────
MASTER_SYNTHESIS_PROMPT = """
Act as a world-class business intelligence analyst and a master direct-response copywriter.
Your primary task is to synthesize the provided 'Raw Intelligence Report' and the strategic principles from the 'Library of Proven Email Principles' to create a new, highly-engaging, and personalized outreach email.

**Your Goal:** Generate a concise prospect dossier and a high-impact outreach email based ONLY on the provided intelligence. You are not just adapting a template; you are creating a fresh message based on proven persuasive strategies.

**1. Stylistic & Tonal Reference (The Gary Halbert / Dan Kennedy Style):**
This is your stylistic guide.
```
{marketing_samples}
```

**2. Library of Proven Email Principles & Strategies:**
Internalize the core strategies from these examples (e.g., the directness of "The Challenger," the professionalism of "The Consultative Advisor," the timeliness of "The Urgent Opportunity"). Do NOT simply copy-paste a template.
```
{successful_emails}
```

**3. Raw Intelligence Report (Your Source of Truth):**
This is your factual basis for personalization.
```json
{intelligence_report}
```

**Output Instructions:**
You MUST return a single, valid JSON object with the following five keys. Do not return any other text or formatting. Your output must demonstrate a synthesis of the intelligence report and the most applicable email strategy.

1.  "Prospect_Title": The prospect's most likely job title, inferred from the data.
2.  "Halbert_Hook": A single, specific, and verifiable event, challenge, or announcement from the report (e.g., "their recent $25M Series B funding round for expansion"). This is the reason for your outreach and should inform your choice of strategic principle.
3.  "Capital_Need_Hypothesis": A direct, one-sentence statement logically linking the hook to a potential need for working capital or growth financing.
4.  "Selected_Email_Subject": Create a short, personal, curiosity-driven subject line inspired by the chosen strategy and personalized with the 'Halbert_Hook' or prospect's details.
5.  "Selected_Email_Body": Write a new email body from scratch.
    - **Apply a principle:** Select the most effective psychological principle from the library for this specific prospect and apply it.
    - **Personalize it:** Seamlessly integrate the 'Halbert_Hook' and 'Capital_Need_Hypothesis'.
    - **Maintain a consistent tone:** The tone should reflect the principle you chose to apply.
    - **Use the placeholder:** The final body text MUST use "[First Name]" as a placeholder for the prospect's first name.
"""


def extract_first_name(full_name: str) -> str:
    if not full_name or not isinstance(full_name, str):
        return "there"
    return full_name.split()[0]


def create_outreach_assets(intelligence_report: Dict[str, Any], prospect_name: str, llm_rules: str = "") -> Dict[str, Any]:
    """
    Generate a condensed dossier + email assets from the prior OSINT report.
    Preserves backend2's EMAIL_GENERATION_RULES emphasis while producing the full 5-key JSON.
    """
    if GENAI_CLIENT is None:
        return {"error": "GenAI client is not configured. Check GEMINI_API_KEY and google-genai installation."}
    if not intelligence_report or (isinstance(intelligence_report, dict) and intelligence_report.get("error")):
        return {"error": f"Invalid intelligence report received: {getattr(intelligence_report, 'error', 'N/A')}"}

    marketing_samples = load_direct_marketing_samples()
    successful_emails = load_successful_emails()
    first_name = extract_first_name(prospect_name)

    try:
        report_str = json.dumps(intelligence_report, indent=2)
        # Inject EMAIL_GENERATION_RULES in addition to the master synthesis prompt
        prompt = (
            MASTER_SYNTHESIS_PROMPT.format(
                intelligence_report=report_str,
                marketing_samples=marketing_samples,
                successful_emails=successful_emails,
            )
            + "\n\n**Additional Email Generation Rules (must-follow):**\n" 
            + "```\n" + llm_rules + "\n```\n"
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

        # Backfill keys if the model omitted any (defensive)
        for key in [
            "Prospect_Title",
            "Halbert_Hook",
            "Capital_Need_Hypothesis",
            "Selected_Email_Subject",
            "Selected_Email_Body",
        ]:
            generated_assets.setdefault(key, "")

        if generated_assets.get("Selected_Email_Body"):
            generated_assets["Selected_Email_Body"] = generated_assets["Selected_Email_Body"].replace("[First Name]", first_name)

        return generated_assets
    except Exception as e:
        print(f"backend2 ERROR: GenAI call failed in create_outreach_assets: {e}")
        return {"error": f"LLM synthesis failed: {e}"}


# ──────────────────────────────────────────────────────────────────────────────
# Dispatch (Email)
# ──────────────────────────────────────────────────────────────────────────────

def send_and_update_email(
    worksheet: gspread.Worksheet,
    row_index: int,
    recipient_email: str,
    subject: str,
    body: str
):
    """
    Sends a single email and updates the corresponding row's status in the sheet.
    """
    col_map = get_column_map(worksheet)
    if send_email(recipient_email, subject, body):
        worksheet.update_cell(row_index, col_map["Status"], "Sent")
        return True, f"Email sent to {recipient_email} and status updated for row {row_index}."
    else:
        worksheet.update_cell(row_index, col_map["Status"], "Send Failed")
        return False, f"Failed to send email for row {row_index}."


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
        print(f"backend2: Email sent successfully to {recipient_email}.")
        return True
    except Exception as e:
        print(f"Backend ERROR: Failed to send email: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Sheet Update
# ──────────────────────────────────────────────────────────────────────────────

def skip_lead(
    worksheet: gspread.Worksheet,
    row_index: int,
    reason: str,
    col_map: Dict[str, int],
):
    """Updates a lead's status to 'Skipped' and logs the reason."""
    try:
        cells_to_update = [
            gspread.Cell(row_index, col_map["Status"], "Skipped"),
        ]
        if "Skip Reason" in col_map:
            cells_to_update.append(
                gspread.Cell(row_index, col_map["Skip Reason"], reason)
            )
        
        worksheet.update_cells(cells_to_update)
        return True, f"Successfully skipped row {row_index} with reason: {reason}."
    except Exception as e:
        return False, f"Failed to update sheet for skip: {e}"


def update_google_sheet(
    worksheet: gspread.Worksheet,
    row_index: int,
    status: str,
    dossier: Dict,
    email_assets: Dict,
    col_map: Dict[str, int],
):
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