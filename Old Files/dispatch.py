# dispatch.py
# Module 4: Sends the finalized email to the prospect.
# v1_2025-08-18: Using Python's smtplib for direct, high-impact SMTP dispatch.

import os
import smtplib
import ssl
from email.message import EmailMessage

# --- Configuration ---
# Load sensitive credentials from environment variables for security.
# IMPORTANT: For Gmail/Google Workspace, you must generate an "App Password".
# Your regular password will NOT work due to security policies.
#
# How to generate an App Password:
# 1. Go to your Google Account settings: myaccount.google.com
# 2. Navigate to "Security".
# 3. Under "How you sign in to Google", enable 2-Step Verification if not already active.
# 4. After enabling it, an "App passwords" option will appear in the same section.
# 5. Click it, select "Mail" for the app and "Windows Computer" (or other) for the device.
# 6. Google will generate a 16-character password. Use this for SENDER_APP_PASSWORD.

SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
SENDER_APP_PASSWORD = os.environ.get('SENDER_APP_PASSWORD')
SMTP_SERVER = "smtp.gmail.com" # For Google Workspace/Gmail
SMTP_PORT = 465 # For SSL connection

# NEW: Load personal/business information from environment variables
SENDER_NAME = os.environ.get('SENDER_NAME', 'Graham Gordon')
SENDER_COMPANY = os.environ.get('SENDER_COMPANY', 'FastCapitalNYC.com')
SENDER_PHONE = os.environ.get('SENDER_PHONE', '(917) 745-3378')
SENDER_INFO_EMAIL = os.environ.get('SENDER_INFO_EMAIL', 'info@fastcapitalnyc.com')

# --- Core Dispatch Function ---

def send_email(recipient_email: str, subject: str, body: str):
    """
    Connects to a Google SMTP server and sends a personalized email.

    Args:
        recipient_email (str): The prospect's email address.
        subject (str): The email subject line.
        body (str): The email content.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    # --- Input Validation ---
    if not all([SENDER_EMAIL, SENDER_APP_PASSWORD]):
        print("  [DISPATCH] Error: SENDER_EMAIL or SENDER_APP_PASSWORD env variables not set.")
        return False
        
    if not all([recipient_email, subject, body]):
        print("  [DISPATCH] Error: Missing recipient, subject, or body. Cannot send email.")
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    
    # UPDATED: Use environment variables for signature instead of hardcoded values
    signature = f"""
--
Sincerely,

{SENDER_NAME}
{SENDER_COMPANY}
Growth Funding Architect
(o){SENDER_PHONE}
{SENDER_INFO_EMAIL}
Apply for Funding

"It always seems impossible until it's done." - Nelson Mandela
"""
    full_body = body + "\n\n" + signature
    msg.set_content(full_body)

    print(f"  [DISPATCH] Preparing to send email to '{recipient_email}' via Google SMTP...")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.send_message(msg)
            print("    -> Email sent successfully.")
            return True
            
    except smtplib.SMTPAuthenticationError:
        print("    [ERROR] SMTP Authentication Failed. Verify your SENDER_EMAIL and ensure you are using a valid 16-digit App Password, not your regular password.")
        return False
    except Exception as e:
        print(f"    [ERROR] An unexpected error occurred while sending email: {e}")
        return False

if __name__ == '__main__':
    print("--- Running Dispatch Module Standalone Test ---")
    
    test_recipient = os.environ.get('TEST_RECIPIENT_EMAIL')
    if test_recipient:
        test_subject = "Dispatch Module Test (SMTP)"
        test_body = "This is a test email from the dispatch.py module using direct SMTP. If you received this, it's working."
        
        success = send_email(test_recipient, test_subject, test_body)
        
        if success:
            print("\n--- Test Complete: Check the recipient's inbox. ---")
        else:
            print("\n--- Test Failed. Check the error messages above. ---")
    else:
        print("No TEST_RECIPIENT_EMAIL environment variable set. Cannot run test.")