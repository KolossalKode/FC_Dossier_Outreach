# config.py
# Central configuration file for the dossier and outreach pipeline.
# v2_2025-08-18: Added JSON validation for GCP credentials.

import os
import json
from dotenv import load_dotenv

# --- Instructions ---
# 1. Create a file named '.env' in this directory.
# 2. Copy the template below, paste it into your .env file, and fill in your values.
# 3. NEVER commit the .env file to a public repository.
#
# --- .env Template ---
# # Module 1: Ingestion (Google Sheets)
# GCP_SERVICE_ACCOUNT_JSON='{"type": "service_account", "project_id": "...", ...}'
# GOOGLE_SHEET_NAME="FAST_MVP_Leads"
#
# # Module 3: Synthesis (Google Gemini)
# GEMINI_API_KEY="your_gemini_api_key"
#
# # Module 4: Dispatch (SMTP via Google)
# SENDER_EMAIL="your.email@example.com"
# SENDER_APP_PASSWORD="your_16_character_app_password"

# Load environment variables from the .env file
load_dotenv()

# --- Module 1: Ingestion (Google Sheets) ---
GCP_SERVICE_ACCOUNT_JSON = os.environ.get('GCP_SERVICE_ACCOUNT_JSON')
GOOGLE_SHEET_NAME = os.environ.get('GOOGLE_SHEET_NAME')

# --- Module 3: Synthesis (Google Gemini) ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- Module 4: Dispatch (SMTP via Google) ---
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
SENDER_APP_PASSWORD = os.environ.get('SENDER_APP_PASSWORD')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# --- Module 5: Email Generation Rules ---
# These rules are injected into the prompt for the LLM to ensure
# consistency and effectiveness in outreach emails.

EMAIL_RULE_1 = "- Let them know we only need a one-minute digital app and their last 6 months of business bank statements to price out options."
EMAIL_RULE_2 = "- Let them know we can provide up to $3 million on an unsecured basis and fund within 24-48 hours of starting the process."
EMAIL_RULE_3 = "- Let them know we have terms as long as 4 years and rates starting at 1% per month."
EMAIL_RULE_4 = """- Always end the email with a no-oriented question which asks if it would be ridiculous/ a waste of time etc to look at potential options which lets them say no while still agreeing to engage."""

# Combine rules into a single block for easy injection into the prompt.
EMAIL_GENERATION_RULES = f"""
**IMPORTANT RULES FOR THE EMAIL CONTENT:**
{EMAIL_RULE_1}
{EMAIL_RULE_2}
{EMAIL_RULE_3}
{EMAIL_RULE_4}
"""

# --- Validation Function ---
def validate_config():
    """Checks for presence and validity of essential configuration variables."""
    print("\n--- Validating Configuration ---")
    essential_vars = {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "SENDER_EMAIL": SENDER_EMAIL,
        "SENDER_APP_PASSWORD": SENDER_APP_PASSWORD,
        "GOOGLE_SHEET_NAME": GOOGLE_SHEET_NAME,
    }
    
    config_is_valid = True
    for var_name, value in essential_vars.items():
        if not value:
            print(f"  [FAIL] Missing essential config variable: {var_name}")
            config_is_valid = False
        else:
            print(f"  [OK] {var_name} is set.")

    # --- Specific Validation for GCP Credentials ---
    if not GCP_SERVICE_ACCOUNT_JSON:
        print(f"  [FAIL] Missing essential config variable: GCP_SERVICE_ACCOUNT_JSON")
        config_is_valid = False
    else:
        try:
            # This is the key improvement: we ensure the JSON is valid here.
            json.loads(GCP_SERVICE_ACCOUNT_JSON)
            print("  [OK] GCP_SERVICE_ACCOUNT_JSON is valid JSON.")
        except json.JSONDecodeError:
            print("  [FAIL] GCP_SERVICE_ACCOUNT_JSON is not valid JSON. Ensure it's a single line with no unescaped quotes.")
            config_is_valid = False

    if not config_is_valid:
        print("\n--- Configuration Incomplete or Invalid. Please correct the errors above. ---")
        return False
    
    print("\n--- Configuration Validated Successfully ---")
    return True

if __name__ == '__main__':
    # This block allows you to test your configuration independently.
    # To run:
    # 1. Ensure you have a .env file with your secrets.
    # 2. Run 'pip install python-dotenv'.
    # 3. Run 'python config.py'.
    validate_config()
