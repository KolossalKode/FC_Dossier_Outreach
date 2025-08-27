# app.py
# Streamlit UI for the FC Dossier Outreach Pipeline
# v2_2025-08-27: Dynamic sheet loading and header management.

import streamlit as st
import pandas as pd
import backend
import config

# --- Validate config at the very beginning ---
if not config.validate_config():
    st.error("Your .env file is missing or has invalid configuration. Please check the console output and your .env file for more details.")
    st.warning("The application cannot start until the configuration is valid.")
    st.stop()

# --- Streamlit App Initialization ---
st.set_page_config(layout="wide")
st.title("FAST Capital Dossier & Outreach Pipeline")

# --- Session State Initialization ---
# This ensures that variables persist across reruns
if 'processing_started' not in st.session_state:
    st.session_state.processing_started = False
if 'sheet_loaded' not in st.session_state:
    st.session_state.sheet_loaded = False
if 'gspread_client' not in st.session_state:
    st.session_state.gspread_client = None
if 'worksheet' not in st.session_state:
    st.session_state.worksheet = None
if 'col_map' not in st.session_state:
    st.session_state.col_map = None
if 'all_leads' not in st.session_state:
    st.session_state.all_leads = pd.DataFrame()
if 'leads_df' not in st.session_state:
    st.session_state.leads_df = pd.DataFrame()
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# --- Main App Logic ---

# STATE 1: Initial Setup - Get Google Sheet Name
if not st.session_state.sheet_loaded:
    st.header("Step 1: Connect to Google Sheet")

    sheet_name = st.text_input("Enter the name of your Google Sheet:", placeholder="e.g., 'My Leads Sheet'")

    if st.button("Load Sheet", type="primary"):
        if not sheet_name:
            st.warning("Please enter a sheet name.")
        else:
            with st.spinner("Connecting to Google Sheets..."):
                try:
                    # Authenticate and get client
                    st.session_state.gspread_client = backend.authenticate_gspread()

                    # Open the spreadsheet and get the first worksheet
                    spreadsheet = st.session_state.gspread_client.open(sheet_name)
                    st.session_state.worksheet = spreadsheet.sheet1
                    st.toast(f"Successfully opened sheet: '{sheet_name}'")

                    # Ensure headers are present, create them if not
                    success, msg = backend.ensure_headers(st.session_state.worksheet, backend.REQUIRED_HEADERS)
                    if not success:
                        raise Exception(msg)
                    st.toast(msg)

                    # Get the column map for updates later
                    st.session_state.col_map = backend.get_column_map(st.session_state.worksheet)

                    # Fetch all leads from the now-validated sheet
                    st.session_state.all_leads = backend.get_new_leads(st.session_state.worksheet)

                    st.session_state.sheet_loaded = True
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to load or prepare the sheet. Error: {e}")
                    # Reset client on failure to allow re-authentication
                    st.session_state.gspread_client = None


# STATE 2: Processing - After sheet is loaded, before processing starts
elif st.session_state.sheet_loaded and not st.session_state.processing_started:
    st.header("Step 2: Fetch and Process Leads")

    if not st.session_state.all_leads.empty:
        st.info(f"Found {len(st.session_state.all_leads)} new leads in the Google Sheet.")
        batch_size = st.number_input(
            "How many leads would you like to process in this batch?",
            min_value=1,
            max_value=len(st.session_state.all_leads),
            value=min(5, len(st.session_state.all_leads)),
            step=1
        )

        if st.button("Fetch and Process Leads", type="primary"):
            st.session_state.processing_started = True
            st.session_state.leads_df = st.session_state.all_leads.head(batch_size)

            with st.spinner("Generating dossiers and emails... This may take a few minutes."):
                progress_bar = st.progress(0, text="Initializing...")
                processed_list = []
                total = len(st.session_state.leads_df)

                for i, (index, lead) in enumerate(st.session_state.leads_df.iterrows()):
                    progress_text = f"Processing lead {i+1}/{total}: {lead.get('Prospect_Name', 'N/A')}"
                    progress_bar.progress((i + 1) / total, text=progress_text)

                    dossier = backend.gather_osint(
                        company_name=lead.get('Company_Name'),
                        prospect_name=lead.get('Prospect_Name'),
                        prospect_email=lead.get('Prospect_Email'),
                        prospect_phone=lead.get('Prospect_Phone')
                    )
                    email_assets = backend.create_outreach_assets(dossier, lead.get('Prospect_Name'))

                    processed_list.append({
                        'lead': lead,
                        'dossier': dossier,
                        'email': email_assets,
                        'row_index': index + 2  # GSheets are 1-indexed, +1 for header
                    })

                st.session_state.processed_data = processed_list
            st.success(f"Successfully processed {len(processed_list)} leads. Ready for review.")
            st.rerun()
    else:
        st.warning("No new leads found in the Google Sheet.")
        if st.button("Start Over"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

# STATE 3: Review - After processing is complete
elif st.session_state.processing_started:
    st.header("Step 3: Review and Approve Emails")

    if st.session_state.current_index < len(st.session_state.processed_data):
        current_item = st.session_state.processed_data[st.session_state.current_index]
        lead_info = current_item['lead']
        dossier_info = current_item['dossier']
        email_info = current_item['email']
        row_num = current_item['row_index']

        st.subheader(f"Reviewing Lead {st.session_state.current_index + 1}/{len(st.session_state.processed_data)}: {lead_info.get('Prospect_Name', 'N/A')} at {lead_info.get('Company_Name', 'N/A')}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Generated Dossier")
            st.json(dossier_info, expanded=True)
        with col2:
            st.markdown("#### Generated Email")
            st.text_input("Subject", email_info.get('Selected_Email_Subject', ''), disabled=True)
            st.text_area("Body", email_info.get('Selected_Email_Body', ''), height=400, disabled=True)

        # Action buttons
        approve_col, skip_col, spacer = st.columns([1, 1, 5])
        with approve_col:
            if st.button("✅ Approve & Send", use_container_width=True, type="primary"):
                with st.spinner("Sending email and updating sheet..."):
                    sent = backend.send_email(
                        recipient_email=lead_info.get('Prospect_Email'),
                        subject=email_info.get('Selected_Email_Subject'),
                        body=email_info.get('Selected_Email_Body')
                    )
                    if sent:
                        st.toast("Email sent successfully!")
                        # Use the worksheet from session state for the update
                        success, msg = backend.update_google_sheet(st.session_state.worksheet, row_num, "Sent", dossier_info, email_info, st.session_state.col_map)
                        if success:
                            st.toast("Google Sheet updated.")
                        else:
                            st.error(f"Sheet Update Failed: {msg}")
                    else:
                        st.error("Failed to send email. Check dispatch logs.")
                
                st.session_state.current_index += 1
                st.rerun()

        with skip_col:
            if st.button("⏩ Skip", use_container_width=True):
                with st.spinner("Updating sheet with 'Skipped' status..."):
                    # Use the worksheet from session state for the update
                    success, msg = backend.update_google_sheet(st.session_state.worksheet, row_num, "Skipped", dossier_info, email_info, st.session_state.col_map)
                    if success:
                        st.toast("Lead skipped. Google Sheet updated.")
                    else:
                        st.error(f"Sheet Update Failed: {msg}")

                st.session_state.current_index += 1
                st.rerun()
    else:
        st.success("🎉 All leads have been reviewed. Pipeline run complete!")
        if st.button("Start New Batch"):
            # Clear state to allow a new run without restarting the server
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
