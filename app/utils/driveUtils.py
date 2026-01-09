import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# 1. Point to your JSON key (It must be in the ROOT folder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'service_account.json')

# 2. PASTE YOUR FOLDER ID HERE
# (Get this from your Browser URL when inside the shared Drive folder)
PARENT_FOLDER_ID = '18aO52EB8Tyc_dBXEpKI7FWc00Cr-dLJs'

SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate_drive():
    # Primary check: Path constructed from BASE_DIR
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        return build('drive', 'v3', credentials=service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES))
    
    # Fallback check: Current working directory (helpful for some server configs)
    if os.path.exists('service_account.json'):
         return build('drive', 'v3', credentials=service_account.Credentials.from_service_account_file('service_account.json', scopes=SCOPES))
    
    # If both fail, print debug info
    print(f"DEBUG: BASE_DIR is {BASE_DIR}")
    print(f"DEBUG: Expected Key Path: {SERVICE_ACCOUNT_FILE}")
    raise FileNotFoundError(f"Key not found. Please ensure 'service_account.json' is in the root directory.")

def upload_file_to_drive(file_obj, filename, mime_type):
    try:
        service = authenticate_drive()

        file_metadata = {
            'name': filename,
            'parents': [PARENT_FOLDER_ID]
        }

        media = MediaIoBaseUpload(file_obj, mimetype=mime_type, resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webContentLink, webViewLink'
        ).execute()

        # Make Public so frontend can display it
        service.permissions().create(
            fileId=file.get('id'),
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()

        # Return the viewable link
        return file.get('webViewLink')

    except Exception as e:
        print(f"Drive Upload Error: {e}")
        # Return a generic error or re-raise depending on how you want to handle it
        # Re-raising allows the API endpoint to catch it and show the 500 error
        raise e
