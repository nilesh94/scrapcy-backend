import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# CONFIG
SCOPES = ['https://www.googleapis.com/auth/drive']
# Helper to find the root folder (where token.json lives)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

# YOUR FOLDER ID
PARENT_FOLDER_ID = '18aO52EB8Tyc_dbXEpKl7FWc00Cr-dLJs' 

def authenticate_drive():
    creds = None
    # 1. Load existing token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # 2. Refresh if expired
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save the refreshed token
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"Token refresh failed: {e}")
                raise Exception("Token invalid and refresh failed. Please regenerate token.json locally.")
        else:
             raise Exception("Token invalid or missing. Run generate_token.py locally and upload token.json to Render.")

    return build('drive', 'v3', credentials=creds)

def upload_file_to_drive(file_obj, filename, mime_type):
    try:
        service = authenticate_drive()
        
        file_metadata = {
            'name': filename,
            'parents': [PARENT_FOLDER_ID]
        }
        
        media = MediaIoBaseUpload(file_obj, mimetype=mime_type, resumable=True)
        
        # 1. Upload the file
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        
        # 2. Make it Public (Anyone with link can view)
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()

        # 3. Generate High-Quality Display Link
        # 'sz=s4000' allows up to 4000px on the longest side (High Quality)
        # We use the 'thumbnail' endpoint because it works reliably in <img> tags
        direct_link = f"https://drive.google.com/thumbnail?id={file_id}&sz=s4000"
        
        return {
            "id": file_id, 
            "url": direct_link
        }

    except Exception as e:
        print(f"Drive Upload Error: {e}")
        raise e

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
