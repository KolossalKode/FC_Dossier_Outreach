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

# --- First Name Extraction Function ---

def extract_first_name(full_name: str) -> str:
    """
    Extracts the first name from a full name using best practices.
    
    Args:
        full_name (str): The prospect's full name (e.g., "John Smith", "Mary Jane Wilson")
    
    Returns:
        str: The first name only (e.g., "John", "Mary")
    
    Examples:
        "John Smith" → "John"
        "Mary Jane Wilson" → "Mary"
        "Dr. Robert Johnson" → "Robert"
        "A. B. Smith" → "A"
        "John" → "John" (single name)
        "" → "there" (fallback for empty names)
    """
    if not full_name or full_name.strip() == "":
        return "there"  # Fallback for empty names
    
    # Clean the name
    name = full_name.strip()
    
    # Remove common prefixes
    prefixes = ["Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Professor", "Sir", "Madam"]
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):].strip()
    
    # Split by spaces and take the first part
    name_parts = name.split()
    
    if not name_parts:
        return "there"
    
    first_name = name_parts[0].strip()
    
    # Handle single letters (initials) - try to get the next part
    if len(first_name) == 1 and len(name_parts) > 1:
        second_part = name_parts[1].strip()
        if len(second_part) > 1:  # If second part is not also an initial
            first_name = second_part
    
    # Clean up the first name
    first_name = first_name.strip(".,")  # Remove trailing punctuation
    
    # If we still have a single letter, use "there" as fallback
    if len(first_name) <= 1:
        return "there"
    
    return first_name

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
    - Start with a personal greeting using "[First Name]" (e.g., "Hi John," or "Hi Mary,").
    - Immediately reference the 'Halbert_Hook'.
    - Briefly introduce the value proposition (fast, flexible growth funding).
    - Use short sentences and paragraphs.
    - End with a low-friction, "no-oriented" call-to-action (e.g., "Would you be opposed to a brief introductory call next week?").
    - **Use "[First Name]" as a placeholder for the prospect's first name only.**
"""

# --- Core Synthesis Function ---

def create_outreach_assets(intelligence_report: dict, prospect_name: str):
    """
    Uses the Gemini API with JSON mode to reliably generate a dossier and email.
    Now includes intelligent first name extraction for better personalization.

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
    
    # --- Extract First Name for Personalization ---
    first_name = extract_first_name(prospect_name)
    print(f"  [SYNTHESIZE] Extracted first name: '{first_name}' from full name: '{prospect_name}'")
        
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
        
        # Personalize the email body by replacing the first name placeholder
        if 'Selected_Email_Body' in generated_assets and first_name:
            generated_assets['Selected_Email_Body'] = generated_assets['Selected_Email_Body'].replace("[First Name]", first_name)
            
            # Also replace the old placeholder for backward compatibility
            generated_assets['Selected_Email_Body'] = generated_assets['Selected_Email_Body'].replace("[Prospect Name]", first_name)
        
        # Store the extracted first name for reference
        generated_assets['extracted_first_name'] = first_name
        generated_assets['original_full_name'] = prospect_name

        print(f"    -> Successfully generated and personalized assets using first name: '{first_name}'")
        return generated_assets
        
    except Exception as e:
        print(f"    [ERROR] Failed during Gemini API call or JSON parsing: {e}")
        return {"error": f"LLM synthesis failed: {e}"}

if __name__ == '__main__':
    print("--- Running Synthesis Module Standalone Test ---")
    print("--- Testing First Name Extraction ---")
    
    # Test various name formats
    test_names = [
        "John Smith",
        "Mary Jane Wilson", 
        "Dr. Robert Johnson",
        "A. B. Smith",
        "John",
        "Prof. Sarah Williams",
        "Mr. Michael Brown",
        "Elizabeth",
        ""
    ]
    
    for test_name in test_names:
        first_name = extract_first_name(test_name)
        print(f"'{test_name}' → '{first_name}'")

    print("\n--- Testing Email Generation ---")

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
    
    # Test with different name formats
    test_prospect_names = ["Elon Musk", "Dr. Sarah Johnson", "Michael"]
    
    if model:
        for prospect_name in test_prospect_names:
            print(f"\n--- Testing with prospect: '{prospect_name}' ---")
            final_assets = create_outreach_assets(mock_report, prospect_name)
            
            if "error" not in final_assets:
                print(f"Extracted first name: {final_assets.get('extracted_first_name', 'N/A')}")
                print(f"Email body preview: {final_assets.get('Selected_Email_Body', 'N/A')[:100]}...")
            else:
                print(f"Error: {final_assets['error']}")
    else:
        print("\n--- Test Skipped: Gemini API not configured ---")

