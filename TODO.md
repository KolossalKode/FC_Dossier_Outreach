# Project TODO and Implementation Plan

This document outlines potential improvements and implementation paths for the Fast Capital Pipeline project.

---

## 1. UI-Based Email Rule Customization

**Goal:** Move the `EMAIL_GENERATION_RULES` from `config.py` to the Streamlit UI to allow for real-time customization without code changes.

### Path 1: Simple `st.text_area`
-   **Simplicity:** 9/10
-   **Scalability:** 5/10
-   **Description:** Add a `st.text_area` to the Streamlit sidebar where the user can view and edit the email generation rules. The content of this text area will be passed to the backend functions.
-   **Sample Prompt:**
    > "In `app_2.py`, add a `st.text_area` to the sidebar titled 'Email Generation Rules'. Its default content should be loaded from `config.EMAIL_GENERATION_RULES`. The content of this text area should be passed to the `create_outreach_assets` function in `backend2.py`."

### Path 2: Rule Builder UI
-   **Simplicity:** 6/10
-   **Scalability:** 8/10
-   **Description:** Create a more structured UI in `app_2.py` with `st.text_input` for individual rules and buttons to add/remove rules. This list of rules would be joined into a single string to be passed to the backend.
-   **Sample Prompt:**
    > "Create a dynamic rule editor in the `app_2.py` sidebar. Use `st.text_input` to add new rules to a list stored in `st.session_state`. Add a button to remove rules. Join the list of rules into a string and pass it to the `create_outreach_assets` function in `backend2.py`."

### Path 3: Preset Rule Templates
-   **Simplicity:** 7/10
-   **Scalability:** 7/10
-   **Description:** In `app_2.py`, create a `st.selectbox` with predefined rule templates (e.g., "Aggressive," "Conservative"). The selected template would load a specific set of rules into a `st.text_area` for further editing.
-   **Sample Prompt:**
    > "In `app_2.py`, implement a `st.selectbox` with options for 'Aggressive', 'Conservative', and 'Relationship-focused' email rule templates. When a template is selected, populate a `st.text_area` below it with the corresponding rules. This text area's content will then be used by the backend for email generation."

#### Testing
1.  Run the Streamlit app (`streamlit run app_2.py`).
2.  In the sidebar, modify the text in the 'Email Generation Rules' text area. For example, add a rule like "- All emails must end with 'Best regards'."
3.  Add a new lead to your Google Sheet and click the 'Process New Leads' button.
4.  Go to the 'Review Pending Leads' tab and check the generated email body. It should now include 'Best regards' at the end.

---

## 2. Edit-Before-Sending Functionality

**Goal:** Allow the user to edit the subject and body of a generated email in the UI before sending it.

### Path 1: `st.text_input` and `st.text_area` for Editing
-   **Simplicity:** 9/10
-   **Scalability:** 6/10
-   **Description:** In the review section of `app_2.py`, display the generated subject and body in an `st.text_input` and `st.text_area` respectively. When the "Send" button is clicked, use the current content of these widgets.
-   **Sample Prompt:**
    > "In `app_2.py`, within the lead review loop, display the 'Selected_Email_Subject' in an `st.text_input` and 'Selected_Email_Body' in a `st.text_area`. When the 'Send' button for a lead is clicked, use the current values from these input fields to call the `send_and_update_email` function."

### Path 2: Modal-Based Editor
-   **Simplicity:** 6/10
-   **Scalability:** 7/10
-   **Description:** Add an "Edit" button next to each lead. Clicking it opens a modal or expander containing the text input fields. A "Save Changes" button updates the data in `st.session_state`.
-   **Sample Prompt:**
    > "For each lead in the review list in `app_2.py`, add an 'Edit' button. When clicked, it should set a variable in `st.session_state` to show an editing interface for that lead's email. The interface should have 'Save' and 'Cancel' buttons. The 'Send' button should be disabled until changes are saved."

### Path 3: Direct Update to Google Sheet
-   **Simplicity:** 5/10
-   **Scalability:** 9/10
-   **Description:** When the user edits the email in the UI, a "Save Draft" button writes the changes directly back to the Google Sheet.
-   **Sample Prompt:**
    > "In `app_2.py`, add a 'Save Draft' button next to the email editing fields. When clicked, this button will trigger a function in `backend2.py` that updates the 'Selected_Email_Subject' and 'Selected_Email_Body' cells for the corresponding row in the Google Sheet."

#### Testing
1.  Run the app and go to the 'Review Pending Leads' tab.
2.  For any lead, modify the text in the subject and body input fields.
3.  Click the 'Send' button for that lead.
4.  Check the 'Sent' folder of your configured sender email account. The email that was sent should contain your exact modifications.

---

## 3. Automated Skipping Rules

**Goal:** Implement rules to automatically skip leads based on certain criteria, reducing the need for manual review.

### Path 1: Keyword-Based Skipping in Backend
-   **Simplicity:** 8/10
-   **Scalability:** 6/10
-   **Description:** In `backend2.py`, after the OSINT step, check the dossier for negative keywords (e.g., "out of business," "non-profit"). If found, automatically update the status to "Skipped - Automated".
-   **Sample Prompt:**
    > "In `backend2.py`, modify the `process_leads_for_review` function. After `gather_osint` is called, check the returned dossier for keywords like 'non-profit', 'out of business', or 'government'. If found, update the Google Sheet row with the status 'Skipped - Automated' and a reason, then continue to the next lead without generating an email."

### Path 2: UI for Defining Skip Rules
-   **Simplicity:** 5/10
-   **Scalability:** 9/10
-   **Description:** In `app_2.py`, create a UI for managing skip rules (e.g., "Skip if 'Company_Name' contains 'Hospital'"). These rules would be applied in the backend.
-   **Sample Prompt:**
    > "Add a 'Skip Rules' configuration section to `app_2.py`. Allow users to define rules based on columns and keywords. In `backend2.py`, before processing a lead, check it against these rules. If a rule matches, skip the lead and log the reason."

### Path 3: AI-Powered Skipping
-   **Simplicity:** 6/10
-   **Scalability:** 8/10
-   **Description:** Create a new function in `backend2.py` that uses a separate, cheaper AI model call to decide if a lead is viable based on initial data, returning a "PROCEED" or "SKIP" decision.
-   **Sample Prompt:**
    > "Create a new function in `backend2.py` called `should_skip_lead`. This function will take the lead's data, call the Gemini API with a prompt asking if the lead is a viable business for funding based on its name and industry, and return True or False. In `process_leads_for_review`, call this function first and skip the lead if it returns True."

#### Testing
1.  In your Google Sheet, add a new lead with a `Company_Name` that is likely to trigger a skip, such as "City of New York Government". Leave the `Status` column blank.
2.  Run the app and click 'Process New Leads'.
3.  Check your Google Sheet. The status for the new lead should be updated to 'Skipped - Automated' (or similar), and no email should have been generated for it in the review tab.

---

## 4. Scheduled Sending

**Goal:** Allow the user to schedule the batch of approved emails to be sent within a specific time window instead of immediately.

### Path 1: External Cron Job / Task Scheduler
-   **Simplicity:** 7/10 (code is simple, setup is external)
-   **Scalability:** 9/10
-   **Description:** Create a separate Python script (`scheduler.py`) that can be run on a schedule (e.g., via a `cron` job). This script finds leads with a "QUEUED" status and sends the emails.
-   **Sample Prompt:**
    > "Create a new script `scheduler.py`. This script will authenticate with Google Sheets, fetch all rows with the status 'QUEUED', send the emails using the `send_email` function from `backend2.py`, and update their status to 'Sent'. In `app_2.py`, change the 'Send' button to a 'Queue' button that updates the lead's status to 'QUEUED'."

### Path 2: Using a Background Task Library (e.g., APScheduler)
-   **Simplicity:** 5/10
-   **Scalability:** 7/10
-   **Description:** Integrate a library like `APScheduler` into the application. The Streamlit app would add jobs to the scheduler.
-   **Sample Prompt:**
    > "Add `APScheduler` to `requirements.txt`. In `app_2.py`, create a scheduler instance. When the user schedules a batch, add a job to the scheduler that calls a function to send the emails. The function will query the Google Sheet for 'QUEUED' leads."

### Path 3: In-Memory Scheduler (Not Recommended)
-   **Simplicity:** 3/10 (conceptually simple, but flawed)
-   **Scalability:** 1/10
-   **Description:** Use `st.session_state` to hold a queue. The app would need to remain open, and logic would periodically check the time. This is not a robust solution.
-   **Sample Prompt:**
    > This path is not recommended due to its unreliability.

#### Testing
1.  Run the app and go to the 'Review Pending Leads' tab.
2.  Click the 'Queue' button for one or more leads.
3.  Check the Google Sheet. The status for those leads should now be 'QUEUED'.
4.  From your terminal, run the scheduler script directly: `python scheduler.py`.
5.  Check the Google Sheet again. The queued leads should now be 'Sent'. Verify the emails were received in the recipient's inbox.

---

## 5. Log Skip Reasons

**Goal:** When a user skips a lead, allow them to log a reason, and store this reason in the Google Sheet.

### Path 1: Dropdown with Predefined Reasons
-   **Simplicity:** 8/10
-   **Scalability:** 7/10
-   **Description:** When the "Skip" button is clicked, show a `st.selectbox` with predefined reasons. The selected value is written to a "Skip Reason" column.
-   **Sample Prompt:**
    > "In `app_2.py`, when the 'Skip' button is clicked, use `st.selectbox` to present the user with a list of skip reasons. Create a new function in `backend2.py` called `skip_lead` that takes the row index and the reason, and updates the 'Status' and a new 'Skip Reason' column in the Google Sheet."

### Path 2: Free-Text Input for Reason
-   **Simplicity:** 9/10
-   **Scalability:** 5/10 (harder to analyze)
-   **Description:** Use `st.text_input` to allow the user to type a custom reason for skipping.
-   **Sample Prompt:**
    > "Modify the 'Skip' button functionality in `app_2.py`. When clicked, it should be followed by an `st.text_input` for the user to enter a reason. A 'Confirm Skip' button will then call a backend function to update the 'Status' and 'Skip Reason' columns in the Google Sheet."

### Path 3: Combined Approach
-   **Simplicity:** 7/10
-   **Scalability:** 8/10
-   **Description:** Use a dropdown with predefined reasons, including an "Other" option. If "Other" is selected, a text input box appears for a custom reason.
-   **Sample Prompt:**
    > "In `app_2.py`, create a skip reason dropdown with an 'Other' option. If 'Other' is selected, conditionally display an `st.text_input` for a custom reason. Pass the selected reason or the custom text to a backend function to update the Google Sheet."

#### Testing
1.  Ensure your Google Sheet has a column named 'Skip Reason'.
2.  Run the app and go to the 'Review Pending Leads' tab.
3.  Click the 'Skip' button for a lead. Select a reason from the dropdown that appears.
4.  Check the Google Sheet. The 'Status' for that row should be 'Skipped', and the 'Skip Reason' column should contain the reason you selected.

---

## 6. Multi-Step Campaigns

**Goal:** Instead of a single email, create a pre-defined sequence of emails to be sent to each prospect at a specified cadence.

### Path 1: New "Campaigns" Sheet
-   **Simplicity:** 4/10
-   **Scalability:** 10/10
-   **Description:** Create a new tab in the Google Sheet named "Campaigns" to define the steps of each campaign. A daily scheduled script would advance the campaigns based on a "Campaign_Status" column.
-   **Sample Prompt:**
    > "Design a multi-step campaign system. Create a new 'Campaigns' tab in the Google Sheet to define email sequences. Modify the `scheduler.py` script to not only send emails but also check the 'Campaign_Status' and 'Last_Contact_Date' for each lead. If the cadence has passed, send the next email in the sequence and update the status."

### Path 2: Hardcoded Campaign Logic
-   **Simplicity:** 7/10
-   **Scalability:** 3/10
-   **Description:** In `backend2.py`, define campaign sequences directly in the code. The lead's status in the sheet would track their progress.
-   **Sample Prompt:**
    > "In `backend2.py`, define a dictionary representing a 3-step email campaign. Modify the daily script to check the status of each lead. If a lead is on a campaign step, and enough time has passed, send the next email in the sequence as defined in the dictionary and update the status in the sheet."

### Path 3: AI-Generated Follow-ups
-   **Simplicity:** 6/10
-   **Scalability:** 7/10
-   **Description:** Instead of pre-defining campaigns, make a new AI call to generate a context-aware follow-up message, using the original dossier and the previously sent email as context.
-   **Sample Prompt:**
    > "Create a function `generate_follow_up_email` in `backend2.py`. It should take the original dossier and the text of the last email sent. It will then call the Gemini API with a prompt to generate a polite and relevant follow-up email. The daily script will call this function for leads that are due for a follow-up."

#### Testing
1.  Create a 'Campaigns' tab in your Google Sheet and define a 2-step campaign.
2.  In your main leads sheet, assign a lead to this campaign by setting its 'Campaign_Status' to 'CampaignName - Step 1'.
3.  Run the `scheduler.py` script. Verify the first email is sent and the status is updated to 'CampaignName - Step 1 Sent'.
4.  Manually edit the 'Last_Contact_Date' in the sheet to a past date that meets the cadence for the next step.
5.  Run `scheduler.py` again. Verify the second email is sent and the status is updated to 'CampaignName - Step 2 Sent'.

---

## 7. Human-Readable Dossier Display

**Goal:** Display the JSON dossier in a more human-readable format (Markdown) in the Streamlit UI.

### Path 1: Simple JSON to Markdown Conversion
-   **Simplicity:** 8/10
-   **Scalability:** 7/10
-   **Description:** Create a function that takes the dossier JSON and formats it as a simple Markdown string. This Markdown is then displayed using `st.markdown`.
-   **Sample Prompt:**
    > "In `app_2.py`, create a function `dossier_to_markdown(dossier_json)`. This function will parse the JSON string and convert it into a Markdown formatted string. In the lead review section, instead of displaying the raw JSON, call this function and display the result using `st.markdown(dossier_as_markdown, unsafe_allow_html=True)`."

### Path 2: AI-Powered Summarization
-   **Simplicity:** 7/10
-   **Scalability:** 6/10
-   **Description:** Create a new AI call that takes the raw JSON dossier and prompts the model to summarize it into a clean, narrative-style report for a human reviewer.
-   **Sample Prompt:**
    > "Create a new function in `backend2.py` called `summarize_dossier(dossier_json)`. This function will call the Gemini API with a prompt that says: 'Summarize the following JSON data into a clean, easy-to-read Markdown report for a sales executive.' In `app_2.py`, call this function and display the summarized report using `st.markdown`."

### Path 3: Tabbed Dossier View
-   **Simplicity:** 6/10
-   **Scalability:** 8/10
-   **Description:** In `app_2.py`, use `st.tabs` to break the dossier into logical sections (e.g., "Company Info," "Financials"). Each tab would display the relevant portion of the JSON.
-   **Sample Prompt:**
    > "In the lead review section of `app_2.py`, parse the `Dossier_JSON`. Use `st.tabs` to create separate tabs for key sections of the dossier like 'Company Overview', 'Recent News', and 'Financial Highlights'. Display the relevant data within each tab."

#### Testing
1.  Run the app and process a new lead.
2.  Go to the 'Review Pending Leads' tab.
3.  Find the lead and view its details.
4.  Instead of a raw block of JSON text, the dossier should be displayed with clear headings and formatted text, making it easy to read.

---

## 8. Model Selector

**Goal:** Allow the user to select the model for research and email writing in the UI.

### Path 1: Simple Model Selection
- **Simplicity:** 9/10
- **Scalability:** 7/10
- **Description:** Add two `st.selectbox` widgets to the sidebar in `app_2.py`, one for the research model and one for the email writing model. The selected models will be passed to the backend functions.
- **Sample Prompt:**
    > "In `app_2.py`, add two `st.selectbox` widgets to the sidebar. The first, labeled 'Research Model', should allow selecting from a list of models (e.g., 'gemini-1.5-pro', 'gemini-1.5-flash'). The second, labeled 'Email Writing Model', should have the same options. The selected values should be passed to the `gather_osint` and `create_outreach_assets` functions in `backend2.py` respectively."

### Path 2: Model Configuration File
- **Simplicity:** 7/10
- **Scalability:** 9/10
- **Description:** Create a `models.json` file that defines the available models and their properties (e.g., name, api_name, cost). The UI would read this file to populate the model selection widgets. This makes it easier to add or remove models without changing the code.
- **Sample Prompt:**
    > "Create a `models.json` file with a list of models, each with a 'name' and 'api_name' field. In `app_2.py`, read this file and use it to populate the model selection `st.selectbox` widgets. Pass the selected model's 'api_name' to the backend functions."

### Path 3: A/B Testing Framework
- **Simplicity:** 4/10
- **Scalability:** 10/10
- **Description:** Implement a simple A/B testing framework. The user can select multiple models to test. For each new lead, the application would randomly assign one of the selected models for research and one for email writing. The model used would be logged in the Google Sheet. This would allow for data-driven decisions on which models perform best.
- **Sample Prompt:**
    > "In `app_2.py`, allow the user to select multiple models for A/B testing using `st.multiselect`. In `backend2.py`, when processing a lead, randomly select one of the chosen models for the `gather_osint` call and one for the `create_outreach_assets` call. Add two new columns to the Google Sheet, 'Research Model Used' and 'Email Model Used', and log the randomly selected model names for each lead."

#### Testing
1. Run the app.
2. In the sidebar, select a different model for research and email writing.
3. Process a new lead.
4. Check the generated dossier and email to see if the output quality differs.
5. If A/B testing is implemented, check the Google Sheet to see if the model names are logged correctly.

---

## 9. OAuth Integration

**Goal:** Allow users to authenticate with their own Google account to access Google Sheets and send emails, instead of using a shared service account.

### Path 1: Basic Streamlit OAuth for Google
- **Simplicity:** 8/10
- **Scalability:** 6/10
- **Description:** Use a library like `streamlit-oauth` to handle the Google OAuth flow. The application would use the user's token to access Google Sheets and send emails via the Gmail API. This approach is simpler but may require each user to configure their own Google Cloud project.
- **Sample Prompt:**
    > "Integrate the `streamlit-oauth` library into `app_2.py`. Configure it for Google authentication. Once the user is authenticated, use their access token to initialize the `gspread` client and to send emails via the Gmail API instead of SMTP."

### Path 2: Centralized OAuth with User Management
- **Simplicity:** 5/10
- **Scalability:** 9/10
- **Description:** Set up an OAuth 2.0 application in the Google Cloud Console. The application will have a single client ID and secret. The backend will handle the token exchange and securely store refresh tokens for users to enable long-running jobs.
- **Sample Prompt:**
    > "Create a new module `auth.py` to handle the Google OAuth 2.0 flow. In the Google Cloud Console, create OAuth 2.0 credentials. In `app_2.py`, add a 'Login with Google' button that redirects the user to the Google consent screen. The backend should handle the callback, exchange the authorization code for an access token and refresh token, and store the tokens securely."

### Path 3: Third-Party Authentication Service
- **Simplicity:** 7/10
- **Scalability:** 10/10
- **Description:** Integrate a service like Auth0 or Firebase Authentication. These services manage the entire user authentication lifecycle. The application would receive a JWT from the authentication service, which can then be used to make authenticated requests to Google APIs.
- **Sample Prompt:**
    > "Integrate Firebase Authentication into the application. Use the Firebase Web SDK in the Streamlit frontend to handle the Google sign-in flow. On the backend, verify the Firebase ID token and use it to make authenticated requests to Google APIs on behalf of the user."

#### Testing
1. Run the app.
2. You should be prompted to log in with your Google account.
3. After logging in, you should be able to access your own Google Sheets.
4. When you send an email, it should be sent from your own email address.
5. Check the "Sent" folder of your Gmail account to verify that the email was sent.