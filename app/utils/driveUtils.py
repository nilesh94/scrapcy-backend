import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# CONFIGURATION
# This assumes service_account.json is in the ROOT folder (same level as app/)
SERVICE_ACCOUNT_FILE = 'service_account.json' 

# Replace this with the Folder ID you copied from Google Drive
PARENT_FOLDER_ID = 'YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE' 

SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate_drive():
    """Authenticates with Google Drive API using Service Account."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
        
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def upload_file_to_drive(file_obj, filename, mime_type):
    """
    Uploads a file-like object to Google Drive and makes it public.
    Returns the webViewLink (viewable URL).
    """
    try:
        service = authenticate_drive()

        file_metadata = {
            'name': filename,
            'parents': [PARENT_FOLDER_ID]
        }
        
        # Create upload object
        media = MediaIoBaseUpload(file_obj, mimetype=mime_type, resumable=True)
        
        # Execute Upload
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webContentLink, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        
        # Set Permissions to 'Anyone with link can view'
        permission = {
            'type': 'anyone',
            'role': 'reader',
        }
        service.permissions().create(
            fileId=file_id,
            body=permission,
        ).execute()

        # webViewLink is the URL users can click to view the image
        return file.get('webViewLink')

    except Exception as e:
        print(f"Google Drive Upload Error: {e}")
        raise e
