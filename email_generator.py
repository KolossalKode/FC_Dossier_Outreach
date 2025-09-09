import random
import os

TEMPLATES_FILE = 'successful_emails.txt'

def load_email_templates(file_path):
    """
    Loads email templates from a file.

    Args:
        file_path (str): The full path to the template file.

    Returns:
        list: A list of template strings. Returns an empty list if the file is not found.
    """
    if not os.path.exists(file_path):
        print(f"Error: Template file not found at {file_path}")
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split templates by the separator '---' and remove any empty strings or extra whitespace.
    templates = [tpl.strip() for tpl in content.split('---') if tpl.strip()]
    print(f"Successfully loaded {len(templates)} email templates.")
    return templates

def generate_personalized_email(lead_data, templates):
    """
    Selects a random template and populates it with data for a specific lead.

    Args:
        lead_data (dict): A dictionary containing lead information. 
                          Keys should match placeholders, e.g., 'business_name'.
        templates (list): A list of email template strings.

    Returns:
        tuple: A (subject, body) tuple for the generated email, or (None, None) on failure.
    """
    if not templates:
        print("Warning: No email templates available to generate an email.")
        return None, None

    template = random.choice(templates)
    
    try:
        subject_line, body_template = template.split('\n', 1)
        subject = subject_line.replace('Subject: ', '').strip()
        body = body_template.strip()
    except ValueError:
        print(f"Warning: Malformed template, could not split subject and body:\n{template}")
        return None, None

    # Replace placeholders with data from the lead_data dictionary
    # Using .get() provides a default value if a key is missing, preventing errors.
    personalized_subject = subject.replace('[Business Name]', lead_data.get('business_name', 'a quick question'))
    
    personalized_body = body.replace('[Business Name]', lead_data.get('business_name', 'your business'))
    personalized_body = personalized_body.replace('[Contact Name]', lead_data.get('contact_name', 'there'))
    personalized_body = personalized_body.replace('[Your Name]', lead_data.get('sender_name', 'Graham'))
    personalized_body = personalized_body.replace('[Your Company]', lead_data.get('sender_company', 'Fast Capital'))

    return personalized_subject, personalized_body

# --- Example of how to use this module ---
if __name__ == "__main__":
    # In your main script, you would integrate the functions like this.
    # This block demonstrates the functionality.
    templates_path = os.path.join(os.path.dirname(__file__), TEMPLATES_FILE)
    email_templates = load_email_templates(templates_path)

    if email_templates:
        sample_lead = {
            'business_name': 'Innovatech Solutions',
            'contact_name': 'Jane Doe',
            'sender_name': 'Graham',
            'sender_company': 'Fast Capital Partners'
        }

        subject, body = generate_personalized_email(sample_lead, email_templates)

        if subject and body:
            print("\n--- Generated Email ---")
            print(f"Subject: {subject}")
            print("\n--- Body ---")
            print(body)
            print("\n-----------------------")