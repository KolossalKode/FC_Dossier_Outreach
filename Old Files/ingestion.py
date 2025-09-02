# ingestion.py
# Module 1: Fetches new leads from a specified Google Sheet.
# v2_2025-08-18: Refactored to use environment variables for configuration.

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import os
import json

# --- Configuration ---
# Define the scope of access for the Google API. This generally doesn't change.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def authenticate_gspread():
    """
    Authenticates with Google Sheets and Drive using credentials
    stored in an environment variable.

    Returns:
        gspread.Client: An authorized gspread client object.
        None: If authentication fails.
    """
    try:
        print("Attempting to authenticate with Google services via environment variable...")
        # Fetch the JSON credentials stored as a string in the environment variable
        creds_json_str = os.environ.get('GCP_SERVICE_ACCOUNT_JSON')
        if not creds_json_str:
            print("Error: Environment variable 'GCP_SERVICE_ACCOUNT_JSON' not found.")
            print("Please set this variable with the content of your service account JSON file.")
            return None

        # Convert the JSON string into a dictionary
        creds_dict = json.loads(creds_json_str)
        
        # Create credentials from the dictionary
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        print("Authentication successful.")
        return gc
    except json.JSONDecodeError:
        print("Error: Failed to parse the 'GCP_SERVICE_ACCOUNT_JSON' environment variable.")
        print("Please ensure it's a valid JSON string.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during authentication: {e}")
        return None

def get_new_leads(gc: gspread.Client):
    """
    Fetches all records from the Google Sheet specified by an environment variable
    and filters for new leads. New leads are identified by an empty or 'New' value
    in the 'Status' column.

    Args:
        gc (gspread.Client): The authorized gspread client.

    Returns:
        pandas.DataFrame: A DataFrame containing only the leads that need processing.
                          Returns an empty DataFrame if no new leads or on error.
    """
    sheet_name = os.environ.get('GOOGLE_SHEET_NAME')
    if not sheet_name:
        print("Error: Environment variable 'GOOGLE_SHEET_NAME' is not set.")
        return pd.DataFrame()

    try:
        print(f"Accessing Google Sheet: '{sheet_name}'...")
        spreadsheet = gc.open(sheet_name)
        worksheet = spreadsheet.sheet1
        
        all_records = worksheet.get_all_records()
        if not all_records:
            print("Sheet is empty. No leads to process.")
            return pd.DataFrame()

        df = pd.DataFrame(all_records)
        print(f"Successfully loaded {len(df)} total records from the sheet.")

        if 'Status' not in df.columns:
            print("Warning: 'Status' column not found. The pipeline may not be able to track progress.")
            return df

        new_leads_df = df[df['Status'].isin(['', 'New', None])].copy()
        
        if not new_leads_df.empty:
            print(f"Found {len(new_leads_df)} new leads to process.")
        else:
            print("No new leads found with 'New' or empty status.")
            
        return new_leads_df

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Error: Spreadsheet '{sheet_name}' not found. Check the 'GOOGLE_SHEET_NAME' variable.")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred while fetching leads: {e}")
        return pd.DataFrame()

if __name__ == '__main__':
    # This block allows you to test this module independently.
    # To run this test:
    # 1. Set the 'GCP_SERVICE_ACCOUNT_JSON' environment variable.
    #    (e.g., export GCP_SERVICE_ACCOUNT_JSON='{...your json content...}')
    # 2. Set the 'GOOGLE_SHEET_NAME' environment variable.
    #    (e.g., export GOOGLE_SHEET_NAME='FAST_MVP_Leads')
    # 3. Run the script: python ingestion.py
    
    print("--- Running Ingestion Module Standalone Test ---")
    
    gspread_client = authenticate_gspread()
    
    if gspread_client:
        leads_to_process = get_new_leads(gspread_client)
        
        if not leads_to_process.empty:
            print("\n--- New Leads Found ---")
            print(leads_to_process.head())
            print(f"\nTotal to process: {len(leads_to_process)}")
        else:
            print("\n--- No New Leads to Process ---")

