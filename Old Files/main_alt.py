# main_alt.py
# An alternative orchestrator to test the enrichment_alt.py module.
# v2_2025-08-20: Modified to call the new deep research module.

import os
import logging
import json
from time import sleep
import gspread

# Import individual modules of the pipeline
import config
import ingestion
# --- CHANGE 1: Import the new enrichment module under the original alias ---
import enrichment_alt as enrichment 
import synthesis
import dispatch
print("Script is starting...")

# --- Logging & Directory Configuration ---
def setup_logging():
    """Ensures the 'logs' directory exists and configures logging."""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        print(f"Created directory: {log_dir}")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "pipeline.log")),
            logging.StreamHandler()
        ]
    )

def get_user_approval(lead_info, email_content):
    """
    Prompts user to approve or skip an email before sending.
    
    Args:
        lead_info: The lead data from the spreadsheet
        email_content: The generated email content from synthesis
    
    Returns:
        str: 'approve' or 'skip'
    """
    print(f"\n{'='*80}")
    print(f"REVIEW EMAIL FOR: {lead_info.get('Prospect_Name', 'N/A')} at {lead_info.get('Company_Name', 'N/A')}")
    print(f"{'='*80}")
    print(f"Subject: {email_content.get('Selected_Email_Subject', 'N/A')}")
    print(f"\nEmail Body:")
    print(f"{email_content.get('Selected_Email_Body', 'N/A')}")
    print(f"\n{'='*80}")
    
    while True:
        choice = input("\nWhat would you like to do?\n1. Approve & Send\n2. Skip this lead\nEnter choice (1 or 2): ").strip()
        
        if choice == '1':
            return 'approve'
        elif choice == '2':
            return 'skip'
        else:
            print("Invalid choice. Please enter 1 or 2.")

def get_column_map(worksheet):
    """Reads the header row and returns a dictionary mapping column names to indices."""
    try:
        headers = worksheet.row_values(1)
        return {header: i + 1 for i, header in enumerate(headers)}
    except Exception as e:
        logging.error(f"Failed to read header row from sheet: {e}")
        return None

def run_pipeline():
    """Executes the full ingestion, enrichment, synthesis, and dispatch pipeline."""
    setup_logging()
    logging.info("--- Starting the Dossier & Outreach Pipeline ---")

    if not config.validate_config():
        logging.critical("Pipeline stopped due to invalid configuration.")
        return

    gspread_client = ingestion.authenticate_gspread()
    if not gspread_client:
        logging.critical("Pipeline stopped: Google Sheets authentication failure.")
        return
    
    leads_df = ingestion.get_new_leads(gspread_client)
    if leads_df.empty:
        logging.info("No new leads to process. Pipeline run complete.")
        return

    # --- NEW: Ask user for the batch size ---
    try:
        total_leads = len(leads_df)
        prompt = (
            f"Found {total_leads} new leads. How many would you like to process in this batch? "
            f"(Enter a number or 'all'): "
        )
        batch_size_str = input(prompt).strip().lower()
        if batch_size_str == 'all':
            batch_size = total_leads
        else:
            batch_size = int(batch_size_str)

        # Slice the DataFrame to the requested batch size
        leads_df = leads_df.head(batch_size)
    except (ValueError, TypeError):
        logging.error("Invalid input. Please enter a number or 'all'. Exiting.")
        return
        
    try:
        spreadsheet = gspread_client.open(config.GOOGLE_SHEET_NAME)
        worksheet = spreadsheet.sheet1
        col_map = get_column_map(worksheet)
        if not col_map or 'Status' not in col_map:
            logging.critical("Could not find 'Status' column in the sheet. Halting.")
            return
    except gspread.exceptions.SpreadsheetNotFound:
        logging.critical(f"Spreadsheet '{config.GOOGLE_SHEET_NAME}' not found. Halting.")
        return
    except Exception as e:
        logging.critical(f"Could not open worksheet. Halting. Error: {e}")
        return

    logging.info(f"--- Processing {len(leads_df)} new leads ---")

    for index, lead in leads_df.iterrows():
        row_num = index + 2
        prospect_name = lead.get('Prospect_Name', 'N/A')
        
        logging.info(f"--- Processing Lead #{row_num-1}: {prospect_name} ---")
        
        try:
            worksheet.update_cell(row_num, col_map['Status'], "Processing...")

            # --- FIX: Removed the 'industry' argument from the function call ---
            intelligence_report = enrichment.gather_osint( # type: ignore
                company_name=lead.get('Company_Name'),
                prospect_name=lead.get('Prospect_Name'),
                prospect_email=lead.get('Prospect_Email'),
                prospect_phone=lead.get('Prospect_Phone'),
            )
            
            if "error" in intelligence_report:
                raise ValueError(f"Enrichment failed: {intelligence_report['error']}")

            outreach_assets = synthesis.create_outreach_assets(intelligence_report, prospect_name)
            if "error" in outreach_assets:
                raise ValueError(f"Synthesis failed: {outreach_assets['error']}")

            # --- Get User Approval ---
            approval_result = get_user_approval(lead, outreach_assets)
            
            # --- Prepare data for sheet update (dossier and assets) ---
            # This data will be saved whether the email is sent or skipped.
            cells_to_update = [
                gspread.Cell(row_num, col_map['Prospect_Title'], outreach_assets.get('Prospect_Title', '')),
                gspread.Cell(row_num, col_map['Halbert_Hook'], outreach_assets.get('Halbert_Hook', '')),
                gspread.Cell(row_num, col_map['Capital_Need_Hypothesis'], outreach_assets.get('Capital_Need_Hypothesis', '')),
                gspread.Cell(row_num, col_map['Selected_Email_Subject'], outreach_assets.get('Selected_Email_Subject', '')),
                gspread.Cell(row_num, col_map['Selected_Email_Body'], outreach_assets.get('Selected_Email_Body', ''))
            ]
            if 'Dossier_JSON' in col_map:
                cells_to_update.append(
                    gspread.Cell(row_num, col_map['Dossier_JSON'], json.dumps(intelligence_report, indent=2))
                )
            if 'Sources' in col_map:
                # Safely extract the sources list from the dossier
                sources_data = intelligence_report.get('dossier', {}).get('sources', [])
                cells_to_update.append(
                    gspread.Cell(row_num, col_map['Sources'], json.dumps(sources_data, indent=2))
                )

            if approval_result == 'skip':
                cells_to_update.append(gspread.Cell(row_num, col_map['Status'], "Skipped"))
                worksheet.update_cells(cells_to_update)
                logging.info(f"Lead {prospect_name} was skipped by user. Dossier saved.")
                continue
            
            elif approval_result == 'approve':
                logging.info(f"Email approved for {prospect_name}. Sending...")
                
                email_sent = dispatch.send_email(
                    recipient_email=lead.get('Prospect_Email'),
                    subject=outreach_assets.get('Selected_Email_Subject'),
                    body=outreach_assets.get('Selected_Email_Body')
                )

                if not email_sent:
                    raise ConnectionError("Dispatch failed. Check dispatch logs for details.")

                # Add the final status and update the sheet
                cells_to_update.append(gspread.Cell(row_num, col_map['Status'], "Sent"))
                worksheet.update_cells(cells_to_update)
                logging.info(f"Successfully processed and sent email to {prospect_name}. Sheet updated.")

        except Exception as e:
            error_message = f"Failed: {e}"
            logging.error(f"Error processing lead {prospect_name}: {error_message}", exc_info=True)
            worksheet.update_cell(row_num, col_map['Status'], error_message[:499])
        
        finally:
            sleep(5)

    logging.info("--- Pipeline run has completed. ---")

if __name__ == '__main__':
    run_pipeline()
