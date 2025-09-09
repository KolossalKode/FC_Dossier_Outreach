# app.py
# Streamlit UI for the FC Dossier Outreach Pipeline
# v2_2025-08-27: Dynamic sheet loading and header management.

import streamlit as st
import pandas as pd
import backend2
import config

# --- Rule Persistence Functions ---
def load_rules():
    try:
        with open("llm_rules.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return config.EMAIL_GENERATION_RULES.split('\n') if hasattr(config, 'EMAIL_GENERATION_RULES') and config.EMAIL_GENERATION_RULES else []

def save_rules(rules):
    with open("llm_rules.txt", "w") as f:
        f.write("\n".join(rules))


# --- Validate config at the very beginning ---
if not config.validate_config():
    st.error("Your .env file is missing or has invalid configuration. Please check the console output and your .env file for more details.")
    st.warning("The application cannot start until the configuration is valid.")
    st.stop()

# --- Streamlit App Initialization ---
st.set_page_config(layout="wide")

# --- Sidebar for LLM Rule Editor ---
with st.sidebar:
    st.header("LLM Rule Editor")

    # Initialize rules from file on first run, then manage in session state
    if "llm_rules" not in st.session_state:
        st.session_state.llm_rules = load_rules()

    # Rule display and removal
    if not st.session_state.llm_rules:
        st.info("No rules defined. Add rules below.")
    else:
        st.write("**Current Rules:**")
        for i, rule in enumerate(st.session_state.llm_rules):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(f"{i + 1}. {rule}")
            with col2:
                if st.button("❌", key=f"remove_rule_{i}", help="Remove this rule"):
                    st.session_state.llm_rules.pop(i)
                    save_rules(st.session_state.llm_rules)
                    st.rerun()

    st.write("---")

    # Rule addition
    new_rule = st.text_area("Enter new rule:", key="new_rule_input", placeholder="e.g., 'The email must be shorter than 150 words.'")
    if st.button("Add Rule", type="primary"):
        if new_rule and new_rule.strip():
            st.session_state.llm_rules.append(new_rule.strip())
            save_rules(st.session_state.llm_rules)
            st.toast("Rule added!")
            # Clear the input box by rerunning
            st.rerun()
        else:
            st.warning("Rule cannot be empty.")

st.title("FAST Capital Dossier & Outreach Pipeline")


def _get_scalar_from_series(series, key, row_index_for_warning):
    """
    Safely extracts a scalar value from a pandas Series, handling cases where
    duplicate column names might cause `series.get(key)` to return a Series.
    """
    val = series.get(key)
    if isinstance(val, pd.Series):
        st.warning(
            f"Warning for row {row_index_for_warning}: Duplicate column mapping for '{key}'. "
            f"Using the first value found. Please check your Google Sheet for columns with the same name."
        )
        return val.iloc[0] if not val.empty else None
    return val

# --- Session State Initialization ---
DEFAULTS = {
    "processing_started": False,
    "sheet_loaded": False,
    "mapping_complete": False,
    "gspread_client": None,
    "worksheet": None,
    "user_mapping": {},
    "final_column_map": None,
    "all_leads": pd.DataFrame(),
    "leads_df": pd.DataFrame(),
    "processed_data": [],
    "current_index": 0,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

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
                    st.session_state.gspread_client = backend2.authenticate_gspread()

                    # Open the spreadsheet and get the first worksheet
                    spreadsheet = st.session_state.gspread_client.open(sheet_name)
                    st.session_state.worksheet = spreadsheet.sheet1
                    st.toast(f"Successfully opened sheet: '{sheet_name}'")
                    st.session_state.sheet_loaded = True
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to load or prepare the sheet. Error: {e}")
                    # Reset client on failure to allow re-authentication
                    st.session_state.gspread_client = None

# STATE 2: Column Mapping - After sheet is loaded, before mapping is confirmed
elif st.session_state.sheet_loaded and not st.session_state.mapping_complete:
    st.header("Step 2: Map Your Columns")
    st.info(f"Sheet: **{st.session_state.worksheet.spreadsheet.title}** > **{st.session_state.worksheet.title}**")
    st.write("Match the columns the script needs to the columns in your sheet.")
    st.info("If a required column doesn't exist in your sheet, select the `[Create '...' Column]` option from its dropdown. The column will be added to your Google Sheet automatically when you continue.")

    REQUIRED_COLUMNS_WITH_DESC = {
        'Prospect_Name': 'The full name of the contact person.',
        'Company_Name': 'The name of the company.',
        'Prospect_Email': 'The email address of the prospect.',
        'Prospect_Phone': 'The phone number of the prospect.',
        'Status': 'Tracks the processing status (e.g., "Processed", "Error"). This will be created if it does not exist.',
        'Prospect_Title': 'The inferred job title of the prospect. This will be created if it does not exist.',
        'Halbert_Hook': 'The specific event or trigger for outreach. This will be created if it does not exist.',
        'Capital_Need_Hypothesis': 'The reason the prospect might need capital. This will be created if it does not exist.',
        'Selected_Email_Subject': 'The generated subject line for the email. This will be created if it does not exist.',
        'Selected_Email_Body': 'The generated body for the email. This will be created if it does not exist.',
        'Dossier_JSON': 'The complete research data in JSON format. This will be created if it does not exist.',
        'Sources': 'A list of web sources used for the research. This will be created if it does not exist.'
    }

    try:
        sheet_columns = [h for h in st.session_state.worksheet.row_values(1) if h]
    except Exception as e:
        st.error(f"Could not read columns from the spreadsheet. Error: {e}")
        sheet_columns = []

    available_columns = ["---"] + sheet_columns
    col1, col2 = st.columns(2)
    all_mapped = True

    for i, (req_col, desc) in enumerate(REQUIRED_COLUMNS_WITH_DESC.items()):
        container = col1 if i % 2 == 0 else col2
        with container:
            create_option = f"[Create '{req_col}' Column]"
            options = [create_option] + available_columns
            current_selection = st.session_state.user_mapping.get(req_col)
            if not current_selection:
                normalized_req = req_col.lower().replace("_", "").replace(" ", "")
                for col in sheet_columns:
                    normalized_sheet = col.lower().replace("_", "").replace(" ", "")
                    if normalized_req == normalized_sheet:
                        current_selection = col
                        break
            
            default_index = 0
            if current_selection and current_selection in options:
                default_index = options.index(current_selection)

            user_choice = st.selectbox(label=f"**{req_col}**", options=options, index=default_index, help=desc, key=f"map_{req_col}")
            st.session_state.user_mapping[req_col] = user_choice
            if user_choice == "---":
                all_mapped = False

    st.write("---")
    if st.button("Confirm Mapping and Continue", disabled=not all_mapped, type="primary"):
        with st.spinner("Preparing worksheet and validating mapping..."):
            try:
                final_map = backend2.prepare_worksheet_from_mapping(
                    st.session_state.worksheet,
                    st.session_state.user_mapping,
                    list(REQUIRED_COLUMNS_WITH_DESC.keys())
                )
                st.session_state.final_column_map = final_map
                st.session_state.mapping_complete = True
                st.success("Worksheet is ready! Fetching leads...")
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred while preparing the worksheet: {e}")

# STATE 3: Processing - After mapping is complete, before processing starts
elif st.session_state.mapping_complete and not st.session_state.processing_started:
    st.header("Step 3: Fetch and Process Leads")

    with st.spinner("Fetching new leads based on your mapping..."):
        if st.session_state.all_leads.empty:
            st.session_state.all_leads = backend2.get_new_leads(st.session_state.worksheet, st.session_state.user_mapping)
    
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
                    row_num_for_display = index + 2  # For user-facing messages

                    # Safely extract scalar values, handling potential duplicate columns
                    company_name = _get_scalar_from_series(lead, 'Company_Name', row_num_for_display)
                    prospect_name = _get_scalar_from_series(lead, 'Prospect_Name', row_num_for_display)
                    prospect_email = _get_scalar_from_series(lead, 'Prospect_Email', row_num_for_display)
                    prospect_phone = _get_scalar_from_series(lead, 'Prospect_Phone', row_num_for_display)

                    progress_text = f"Processing lead {i+1}/{total}: {prospect_name or 'N/A'}"
                    progress_bar.progress((i + 1) / total, text=progress_text)

                    dossier = backend2.gather_osint(
                        company_name=company_name,
                        prospect_name=prospect_name,
                        prospect_email=prospect_email,
                        prospect_phone=prospect_phone
                    )
                    rules_string = "\n".join(st.session_state.llm_rules)
                    email_assets = backend2.create_outreach_assets(dossier, prospect_name, rules_string)

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
elif st.session_state.processing_started: # This is now STATE 4
    st.header("Step 4: Review and Approve Emails")

    if st.session_state.current_index < len(st.session_state.processed_data):
        current_item = st.session_state.processed_data[st.session_state.current_index]
        dossier_info = current_item['dossier']
        email_info = current_item['email']
        row_num = current_item['row_index']

        # Safely extract scalar values for display and actions
        lead_prospect_name = _get_scalar_from_series(current_item['lead'], 'Prospect_Name', row_num)
        lead_company_name = _get_scalar_from_series(current_item['lead'], 'Company_Name', row_num)
        lead_prospect_email = _get_scalar_from_series(current_item['lead'], 'Prospect_Email', row_num)


        st.subheader(f"Reviewing Lead {st.session_state.current_index + 1}/{len(st.session_state.processed_data)}: {lead_prospect_name or 'N/A'} at {lead_company_name or 'N/A'}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Generated Dossier")
            st.json(dossier_info, expanded=True)
        with col2:
            st.markdown("#### Generated Email")
            st.text_input("Subject", email_info.get('Selected_Email_Subject', ''), disabled=True, key=f"subject_{row_num}")
            st.text_area("Body", email_info.get('Selected_Email_Body', ''), height=400, disabled=True, key=f"body_{row_num}")

        # Action buttons
        approve_col, skip_col, spacer = st.columns([1, 1, 5])
        with approve_col:
            if st.button("✅ Approve & Send", use_container_width=True, type="primary"):
                with st.spinner("Sending email and updating sheet..."):
                    sent = backend2.send_email(
                        recipient_email=lead_prospect_email,
                        subject=email_info.get('Selected_Email_Subject'),
                        body=email_info.get('Selected_Email_Body')
                    )
                    if sent:
                        st.toast("Email sent successfully!")
                        # Use the worksheet from session state for the update
                        success, msg = backend2.update_google_sheet(st.session_state.worksheet, row_num, "Sent", dossier_info, email_info, st.session_state.final_column_map)
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
                    success, msg = backend2.update_google_sheet(st.session_state.worksheet, row_num, "Skipped", dossier_info, email_info, st.session_state.final_column_map)
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