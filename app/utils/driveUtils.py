import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# 1. Point to your JSON key (It should be in the root folder)
# We use '..' to go up one level from 'app/utils/' to root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'service_account.json')

# 2. PASTE YOUR FOLDER ID HERE
PARENT_FOLDER_ID = 'PASTE_YOUR_COPIED_FOLDER_ID_HERE' 

SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate_drive():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        # Fallback for some deployment environments if path differs
        if os.path.exists('service_account.json'):
             return build('drive', 'v3', credentials=service_account.Credentials.from_service_account_file('service_account.json', scopes=SCOPES))
        raise FileNotFoundError(f"Key not found at {SERVICE_ACCOUNT_FILE}")

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

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

        # Make Public
        service.permissions().create(
            fileId=file.get('id'),
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()

        return file.get('webViewLink')

    except Exception as e:
        print(f"Drive Upload Error: {e}")
        raise e
