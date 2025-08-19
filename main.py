# main.py
# The orchestrator that runs the entire dossier and outreach pipeline.
# v2_2025-08-18: Refactored for dynamic columns and efficient batch updates.

import os
import logging
from time import sleep
import gspread

# Import individual modules of the pipeline
import config
import ingestion
import enrichment
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

            intelligence_report = enrichment.enrich_lead(lead)
            if "error" in intelligence_report:
                raise ValueError(f"Enrichment failed: {intelligence_report['error']}")

            outreach_assets = synthesis.create_outreach_assets(intelligence_report, prospect_name)
            if "error" in outreach_assets:
                raise ValueError(f"Synthesis failed: {outreach_assets['error']}")

            email_sent = dispatch.send_email(
                recipient_email=lead.get('Prospect_Email'),
                subject=outreach_assets.get('Selected_Email_Subject'),
                body=outreach_assets.get('Selected_Email_Body')
            )

            if not email_sent:
                raise ConnectionError("Dispatch failed. Check dispatch logs for details.")

            # --- Efficient Batch Update ---
            # Prepare all cell updates for this lead
            cells_to_update = [
                gspread.Cell(row_num, col_map['Status'], "Sent"),
                gspread.Cell(row_num, col_map['Prospect_Title'], outreach_assets.get('Prospect_Title', '')),
                gspread.Cell(row_num, col_map['Halbert_Hook'], outreach_assets.get('Halbert_Hook', '')),
                gspread.Cell(row_num, col_map['Capital_Need_Hypothesis'], outreach_assets.get('Capital_Need_Hypothesis', '')),
                gspread.Cell(row_num, col_map['Selected_Email_Subject'], outreach_assets.get('Selected_Email_Subject', '')),
                gspread.Cell(row_num, col_map['Selected_Email_Body'], outreach_assets.get('Selected_Email_Body', ''))
            ]
            worksheet.update_cells(cells_to_update)
            logging.info(f"Successfully processed and sent email to {prospect_name}. Sheet updated.")

        except Exception as e:
            error_message = f"Failed: {e}"
            logging.error(f"Error processing lead {prospect_name}: {error_message}", exc_info=True)
            worksheet.update_cell(row_num, col_map['Status'], error_message[:499]) # Limit error msg length for cell
        
        finally:
            sleep(5) # Delay to respect API rate limits

    logging.info("--- Pipeline run has completed. ---")

if __name__ == '__main__':
    run_pipeline()
