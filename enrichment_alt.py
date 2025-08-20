# enrichment_alt.py
# Module 2 (Alternative): Executes a deep research OSINT prompt using Gemini.
# v2_2025-08-20: Removed dependency on pre-supplied industry data.

import os
import json
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

# --- Configuration ---
try:
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not found.")
    genai.configure(api_key=GEMINI_API_KEY)
    
    model = genai.GenerativeModel('gemini-2.5-pro')
    print("Gemini API configured successfully with 'gemini-2.5-pro'.")

except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    model = None

# --- Core Functions ---

def load_master_prompt() -> str:
    """
    Loads the deep research prompt from the 'master_prompt.txt' file.
    """
    try:
        with open('master_prompt.txt', 'r') as f:
            return f.read()
    except FileNotFoundError:
        print("[ERROR] Critical: 'master_prompt.txt' not found in the project directory.")
        return ""

# --- FIX: Removed 'industry' from the function signature ---
def gather_osint(company_name: str, prospect_name: str, prospect_email: str, prospect_phone: str) -> dict:
    """
    Performs deep, grounded research on a prospect using the Gemini API.
    """
    print(f"\n--- [Module 2 ALT] Starting Deep Research for: {prospect_name} at {company_name} ---")
    
    if not model:
        return {"error": "Gemini model is not configured. Check API key and configuration."}

    master_prompt = load_master_prompt()
    if not master_prompt:
        return {"error": "Could not load the master prompt file."}

    # --- FIX: Removed 'industry' from the .format() call ---
    formatted_prompt = master_prompt.format(
        prospect_name=prospect_name,
        company_name=company_name,
        prospect_email=prospect_email,
        prospect_phone=prospect_phone
    )

    print("  -> Prompt formatted. Sending request to Gemini 1.5 Pro...")

    try:
        generation_config = GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=8192,  # Increase the token limit to prevent truncation
        )
        
        response = model.generate_content(
            formatted_prompt,
            generation_config=generation_config
        )
        
        print("  -> Received response from Gemini.")
        
        response_text = response.text
        dossier = json.loads(response_text)
        
        print("  -> Successfully parsed JSON dossier.")
        return dossier

    except json.JSONDecodeError:
        print("[ERROR] Failed to decode JSON from Gemini's response.")
        print(f"         Raw Response Text: {response_text[:500]}...")
        return {"error": "Failed to parse JSON response from LLM."}
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during the Gemini API call: {e}")
        return {"error": str(e)}

# --- Standalone Utility / Test ---
if __name__ == '__main__':
    print("\n--- Running Enrichment_Alt Module Standalone Utility ---")
    
    try:
        test_company = input("Enter the company name: ")
        test_prospect = input("Enter the prospect's full name: ")
        test_email = input("Enter the prospect's email: ")
        test_phone = input("Enter the prospect's phone number: ")

        if not all([test_company, test_prospect, test_email, test_phone]):
            print("\n[ERROR] All fields are required. Exiting.")
        else:
            # --- FIX: Removed 'industry' from the test function call ---
            intelligence_dossier = gather_osint(test_company, test_prospect, test_email, test_phone)
            
            if "error" not in intelligence_dossier:
                print("\n--- Test Succeeded: Generated Dossier ---")
                print(json.dumps(intelligence_dossier, indent=2))
                print("\n--- Hook Hypothesis ---")
                if intelligence_dossier.get('hook_hypothesis'):
                    print(f"Primary Angle: {intelligence_dossier['hook_hypothesis'].get('primary_angle')}")
                    print(f"Hypothesis: {intelligence_dossier['hook_hypothesis'].get('primary_hypothesis')}")
            else:
                print(f"\n--- Test Failed ---")
                print(f"Error: {intelligence_dossier['error']}")

    except KeyboardInterrupt:
        print("\n\nTest cancelled by user. Exiting.")
