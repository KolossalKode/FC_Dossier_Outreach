# Fast Capital Pipeline

An automated sales and outreach pipeline designed to identify, research, and contact new business leads for growth capital opportunities. The script uses a combination of web scraping and AI to enrich lead data and generate highly personalized outreach emails, with a human-in-the-loop approval step to ensure quality.

## Features

*   **Automated Lead Ingestion**: Fetches new leads directly from a specified Google Sheet.
*   **AI-Powered Enrichment**: Uses DuckDuckGo and Google searches to gather intelligence on leads, then leverages the Google Gemini API to determine the company's industry.
*   **AI-Powered Synthesis**: Generates a complete prospect dossier and a personalized, compelling outreach email for each lead.
*   **Human-in-the-Loop Approval**: Requires manual user approval in the terminal for each email before it is sent, preventing errors and ensuring high-quality outreach.
*   **Automated Dispatch**: Sends approved emails via a configured SMTP account (e.g., Google Workspace).
*   **Comprehensive Logging**: Updates the source Google Sheet with the status of each lead (`Sent`, `Skipped`, `Error`) and populates it with all the generated intelligence.

---

## How It Works: The Pipeline

The script operates as a multi-stage pipeline, processing each new lead from start to finish.

1.  **Configuration & Setup**
    *   Loads all necessary API keys, sheet names, and email credentials from the `.env` file.
    *   Validates that all required configuration variables are present.
    *   Initializes a `pipeline.log` file for detailed logging.

2.  **Ingestion (`ingestion.py`)**
    *   Authenticates with the Google Sheets API using your service account credentials.
    *   Reads all rows from the target sheet and filters for leads where the `Status` column is empty or marked as "New".

3.  **Enrichment (`enrichment.py`)**
    *   For each new lead, the `Status` is immediately updated to "Processing...".
    *   A series of web searches are performed to gather intelligence on the prospect and their company.
    *   The search results are passed to the Gemini AI to accurately determine the company's industry.

4.  **Synthesis (`synthesis.py`)**
    *   The complete "intelligence report" is sent to the Gemini AI with a detailed prompt instructing it to act as a business analyst and expert copywriter.
    *   The AI generates a structured dossier, including the prospect's likely title, a "Halbert Hook" (a verifiable event to justify outreach), a capital need hypothesis, and a personalized email subject and body.

5.  **Approval (`main.py`)**
    *   The generated email is printed to the terminal for your review.
    *   The script waits for you to input `1` to **Approve & Send** or `2` to **Skip**. This is a critical quality control step.

6.  **Dispatch (`dispatch.py`)**
    *   If approved, the email is sent to the prospect using the configured SMTP credentials.

7.  **Logging (`main.py`)**
    *   The lead's row in the Google Sheet is updated with the final status ("Sent" or "Skipped").
    *   All the generated data (title, hook, hypothesis, and the exact email content) is written back to the corresponding columns in the sheet for tracking and analysis.

---

## Prerequisites & Setup

Follow these steps to get the pipeline running.

### 1. Install Dependencies

It is highly recommended to use a Python virtual environment.

```bash
# Create and activate a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`

# Install required packages
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a file named `.env` in the root of the project directory. Copy the contents of `.env.example` (or the template below) into it and fill in your actual credentials.

**Never commit your `.env` file to version control.**

```ini
# .env file template

# Module 1: Ingestion (Google Sheets)
# The full JSON content of your Google Cloud Platform service account key
GCP_SERVICE_ACCOUNT_JSON='{"type": "service_account", "project_id": "...", ...}'
GOOGLE_SHEET_NAME="Your Google Sheet Name"

# Module 3: Synthesis (Google Gemini)
GEMINI_API_KEY="your_gemini_api_key_here"

# Module 4: Dispatch (SMTP via Google)
# IMPORTANT: SENDER_APP_PASSWORD must be a 16-digit Google App Password, not your regular account password.
SENDER_EMAIL="your.email@yourdomain.com"
SENDER_APP_PASSWORD="your_16_character_app_password"
SENDER_NAME="Your Name"
SENDER_COMPANY="Your Company"
SENDER_PHONE="(123) 456-7890"
SENDER_INFO_EMAIL="info@yourcompany.com"

# (Optional) For testing the dispatch module standalone
TEST_RECIPIENT_EMAIL="test.recipient@example.com"
```

### 3. Set up Google Sheet

Ensure your Google Sheet has the following columns. The script dynamically finds them by name, so the order does not matter.

*   `Prospect_Name`
*   `Company_Name`
*   `Prospect_Email`
*   `Status` (This is required for the script to track progress)
*   `Prospect_Title` (Will be populated by the script)
*   `Halbert_Hook` (Will be populated by the script)
*   `Capital_Need_Hypothesis` (Will be populated by the script)
*   `Selected_Email_Subject` (Will be populated by the script)
*   `Selected_Email_Body` (Will be populated by the script)
*   `Dossier_JSON` (Optional: Will be populated with the full raw intelligence report if the column exists)

---

## Usage

To run the pipeline, execute the `main.py` script from your terminal:

```bash
python main.py
```

The script will find any new leads and begin the process. You will be prompted for approval for each email before it is sent.