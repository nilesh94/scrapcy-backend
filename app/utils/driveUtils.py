import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# CONFIG
SCOPES = ['https://www.googleapis.com/auth/drive']
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')
PARENT_FOLDER_ID = '18aO52EB8Tyc_dbXEpKl7FWc00Cr-dLJs' 

def authenticate_drive():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        else:
             raise Exception("Token invalid. Run generate_token.py locally.")

    return build('drive', 'v3', credentials=creds)

def upload_file_to_drive(file_obj, filename, mime_type):
    service = authenticate_drive()
    
    file_metadata = {
        'name': filename,
        'parents': [PARENT_FOLDER_ID]
    }
    
    media = MediaIoBaseUpload(file_obj, mimetype=mime_type, resumable=True)
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    
    file_id = file.get('id')
    
    # Permission
    service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'},
    ).execute()

    # View Link
    direct_link = f"https://drive.google.com/uc?export=view&id={file_id}"
    
    # --- CHANGE: Return Dictionary ---
    return {
        "id": file_id, 
        "url": direct_link
    }

def delete_file_from_drive(file_id):
    """Deletes a file from Google Drive permanently"""
    try:
        service = authenticate_drive()
        service.files().delete(fileId=file_id).execute()
        print(f"Deleted Drive File ID: {file_id}")
        return True
    except Exception as e:
        print(f"Error deleting file {file_id}: {e}")
        return False
