# synthesis.py
# Module 3: Generates dossier and email copy using an LLM.
# v2_2025-08-18: Refactored to use Gemini's native JSON mode for reliability.

import os
import json
import pandas as pd
import google.generativeai as genai

# --- Configuration ---
# It's critical to set your GEMINI_API_KEY as an environment variable.
try:
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not found.")
    genai.configure(api_key=GEMINI_API_KEY)
    # Using a newer, faster, and more cost-effective model
    model = genai.GenerativeModel('gemini-2.5-pro')
    print("Gemini API configured successfully with 'gemini-2.5-pro'.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    model = None # Set model to None if configuration fails

# --- Master Prompt Template ---

MASTER_SYNTHESIS_PROMPT = """
Act as a world-class business intelligence analyst and a direct-response copywriter in the style of Gary Halbert.

**Your Task:**
Based ONLY on the structured 'Raw Intelligence Report' provided below, generate a concise prospect dossier and a compelling outreach email. Ground all outputs in the provided data. Do not invent facts.

**Raw Intelligence Report:**
```json
{intelligence_report}
```

**Output Instructions:**
You MUST return a single, valid JSON object with the following five keys. Do not return any other text or formatting.

1.  **"Prospect_Title"**: The prospect's most likely job title, inferred from the data.
2.  **"Halbert_Hook"**: A single, specific, and verifiable event, challenge, or announcement from the report (e.g., "their recent $25M Series B funding round for expansion"). This is the reason for your outreach.
3.  **"Capital_Need_Hypothesis"**: A direct, one-sentence statement logically linking the hook to a potential need for working capital or growth financing.
4.  **"Selected_Email_Subject"**: A short, personal, curiosity-driven subject line (e.g., "Question about SpaceX's expansion"). Avoid corporate jargon.
5.  **"Selected_Email_Body"**: An email draft written in the voice of a helpful, high-integrity "Growth Funding Architect".
    - Immediately reference the 'Halbert_Hook'.
    - Briefly introduce the value proposition (fast, flexible growth funding).
    - Use short sentences and paragraphs.
    - End with a low-friction, "no-oriented" call-to-action (e.g., "Would you be opposed to a brief introductory call next week?").
    - **Crucially, use "[Prospect Name]" as a placeholder for the prospect's name.**
"""

# --- Core Synthesis Function ---

def create_outreach_assets(intelligence_report: dict, prospect_name: str):
    """
    Uses the Gemini API with JSON mode to reliably generate a dossier and email.

    Args:
        intelligence_report (dict): The structured data from enrichment.py.
        prospect_name (str): The name of the prospect for email personalization.

    Returns:
        dict: A dictionary containing the generated assets, or an error dictionary.
    """
    if not model:
        return {"error": "Gemini model is not configured. Cannot proceed."}
    
    # --- Input Validation ---
    if not intelligence_report or "error" in intelligence_report:
        error_msg = intelligence_report.get("error", "Empty intelligence report received.")
        print(f"  [SYNTHESIZE] Skipping: Invalid intelligence report. Reason: {error_msg}")
        return {"error": f"Invalid input: {error_msg}"}
        
    print("  [SYNTHESIZE] Generating dossier and email draft...")
    
    try:
        report_str = json.dumps(intelligence_report, indent=2)
        prompt = MASTER_SYNTHESIS_PROMPT.format(intelligence_report=report_str)
        
        # --- Simplified & Reliable API Call using JSON Mode ---
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # The response is now guaranteed to be a valid JSON string
        generated_assets = json.loads(response.text)
        
        # Personalize the email body by replacing the placeholder
        if 'Selected_Email_Body' in generated_assets and prospect_name:
            generated_assets['Selected_Email_Body'] = generated_assets['Selected_Email_Body'].replace("[Prospect Name]", prospect_name)

        print("    -> Successfully generated and personalized assets.")
        return generated_assets
        
    except Exception as e:
        print(f"    [ERROR] Failed during Gemini API call or JSON parsing: {e}")
        return {"error": f"LLM synthesis failed: {e}"}

if __name__ == '__main__':
    print("--- Running Synthesis Module Standalone Test ---")

    # Mock data, similar to the output of previous modules
    mock_report = {
      "recent_news": [{
          "source": "DuckDuckGo",
          "title": "SpaceX Announces $850M Funding Round to Fuel Starship and Starlink",
          "link": "[https://www.fake-tech-news.com/spacex-funding-2025](https://www.fake-tech-news.com/spacex-funding-2025)",
          "snippet": "Elon Musk's SpaceX has closed a massive $850 million equity funding round..."
      }],
      "prospect_role": [{
          "source": "DuckDuckGo",
          "title": "Elon Musk, CEO of SpaceX - LinkedIn",
          "link": "[https://www.linkedin.com/in/fakeprofile-elonmusk](https://www.linkedin.com/in/fakeprofile-elonmusk)",
          "snippet": "Elon Musk. Chief Executive Officer at SpaceX."
      }]
    }
    mock_prospect_name = "Elon"

    if model:
        final_assets = create_outreach_assets(mock_report, mock_prospect_name)
        print("\n--- Final Generated Assets (JSON) ---")
        print(json.dumps(final_assets, indent=2))
    else:
        print("\n--- Test Skipped: Gemini API not configured ---")

