# app.py
# Streamlit UI for the FC Dossier Outreach Pipeline
# v1_2025-08-22: Initial version with processing and review workflow.

import streamlit as st
import pandas as pd

# It's recommended to move all backend functions into a separate file
# like 'backend.py' and import them here.
# For this self-contained example, we assume they are available.
import backend 
import config # To get the sheet name for the update function

# --- NEW: Validate config at the very beginning ---
# This is the simplest way to prevent a blank screen on startup.
if not config.validate_config():
    st.error("Your .env file is missing or has invalid configuration. Please check the console output and your .env file for more details.")
    st.warning("The application cannot start until the configuration is valid.")
    st.stop() # Stop the app from running further


# --- Streamlit App ---

# Initialize session state variables to track the app's state
if 'processing_started' not in st.session_state:
    st.session_state.processing_started = False
if 'leads_df' not in st.session_state:
    st.session_state.leads_df = pd.DataFrame()
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'gspread_client' not in st.session_state:
    st.session_state.gspread_client = None
if 'col_map' not in st.session_state:
    st.session_state.col_map = None


st.set_page_config(layout="wide")
st.title("FAST Capital Dossier & Outreach Pipeline")

# --- Main App Logic ---

# Only show the setup screen if processing hasn't started
if not st.session_state.processing_started:
    st.header("Step 1: Fetch and Process Leads")

    # Authenticate once and store the client and column map in the session state
    if st.session_state.gspread_client is None:
        with st.spinner("Authenticating with Google Sheets..."):
            st.session_state.gspread_client = backend.authenticate_gspread()
            if st.session_state.gspread_client:
                try:
                    spreadsheet = st.session_state.gspread_client.open(config.GOOGLE_SHEET_NAME)
                    worksheet = spreadsheet.sheet1
                    st.session_state.col_map = backend.get_column_map(worksheet)
                except Exception as e:
                    st.error(f"Could not open Google Sheet or get column map. Error: {e}")
                    st.session_state.gspread_client = None # Invalidate client on error

    if st.session_state.gspread_client and st.session_state.col_map:
        all_leads = backend.get_new_leads(st.session_state.gspread_client)
        
        if not all_leads.empty:
            st.info(f"Found {len(all_leads)} new leads in the Google Sheet.")
            batch_size = st.number_input(
                "How many leads would you like to process in this batch?",
                min_value=1,
                max_value=len(all_leads),
                value=min(5, len(all_leads)), # Default to 5 or the total number if less
                step=1
            )

            if st.button("Fetch and Process Leads", type="primary"):
                st.session_state.processing_started = True
                st.session_state.leads_df = all_leads.head(batch_size)
                
                # This block runs the backend processing for all selected leads at once
                with st.spinner("Generating dossiers and emails... This may take a few minutes."):
                    progress_bar = st.progress(0, text="Initializing...")
                    processed_list = []
                    total = len(st.session_state.leads_df)

                    for i, (index, lead) in enumerate(st.session_state.leads_df.iterrows()):
                        progress_text = f"Processing lead {i+1}/{total}: {lead['Prospect_Name']}"
                        progress_bar.progress((i + 1) / total, text=progress_text)

                        dossier = backend.gather_osint(
                            company_name=lead.get('Company_Name'),
                            prospect_name=lead.get('Prospect_Name'),
                            prospect_email=lead.get('Prospect_Email'),
                            prospect_phone=lead.get('Prospect_Phone')
                        )
                        email_assets = backend.create_outreach_assets(dossier, lead['Prospect_Name'])
                        
                        # Store all necessary data for the review step
                        processed_list.append({
                            'lead': lead, 
                            'dossier': dossier, 
                            'email': email_assets, 
                            'row_index': index + 2 # Google Sheets are 1-indexed, +1 for header
                        })

                    st.session_state.processed_data = processed_list
                st.success(f"Successfully processed {len(processed_list)} leads. Ready for review.")
                st.rerun()
        else:
            st.warning("No new leads found in the Google Sheet.")
    else:
        st.error("Failed to authenticate with Google Sheets. Check your .env configuration and GCP credentials.")

else:
    # This is the review and dispatch screen, shown after processing is complete
    st.header("Step 2: Review and Approve Emails")

    if st.session_state.current_index < len(st.session_state.processed_data):
        current_item = st.session_state.processed_data[st.session_state.current_index]
        lead_info = current_item['lead']
        dossier_info = current_item['dossier']
        email_info = current_item['email']
        row_num = current_item['row_index']

        st.subheader(f"Reviewing Lead {st.session_state.current_index + 1}/{len(st.session_state.processed_data)}: {lead_info['Prospect_Name']} at {lead_info['Company_Name']}")

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
                        success, msg = backend.update_google_sheet(st.session_state.gspread_client, row_num, "Sent", dossier_info, email_info, st.session_state.col_map)
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
                    success, msg = backend.update_google_sheet(st.session_state.gspread_client, row_num, "Skipped", dossier_info, email_info, st.session_state.col_map)
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
