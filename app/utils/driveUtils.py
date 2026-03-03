import os
from google.oauth2 import service_account  # NEW IMPORT
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# CONFIG
SCOPES = ['https://www.googleapis.com/auth/drive']

# Helper to find the root folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# PRIORITY 1: Service Account (Best for Server/Render)
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'service_account.json')

# PRIORITY 2: User Token (Best for Local Testing)
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

# YOUR FOLDER ID
PARENT_FOLDER_ID = '18aO52EB8Tyc_dbXEpKl7FWc00Cr-dLJs' 

def authenticate_drive():
    creds = None
    
    # --- METHOD 1: SERVICE ACCOUNT (Recommended) ---
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            # print("Using Service Account for Drive Auth...")
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
            return build('drive', 'v3', credentials=creds, cache_discovery=False)
        except Exception as e:
            print(f"Service Account Error: {e}")
            # If this fails, we fall through to try the Token method
            pass

    # --- METHOD 2: USER TOKEN (Legacy/Local) ---
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Save the refreshed token
                    with open(TOKEN_FILE, 'w') as token:
                        token.write(creds.to_json())
        except Exception as e:
             print(f"Token refresh failed: {e}")
             raise Exception("Token invalid. Please switch to Service Account (service_account.json).")
             
    if not creds or not creds.valid:
        raise Exception("No valid authentication found. Upload 'service_account.json' to server root.")

    return build('drive', 'v3', credentials=creds, cache_discovery=False)

def upload_file_to_drive(file_obj, filename, mime_type):
    try:
        print(f"DEBUG: Starting upload for {filename} ({mime_type})") # LOG 1
        service = authenticate_drive()
        print("DEBUG: Drive authentication successful") # LOG 2
        
        file_metadata = {
            'name': filename,
            'parents': [PARENT_FOLDER_ID]
        }
        
        # Determine the raw stream
        raw_stream = getattr(file_obj, 'file', file_obj)
        print(f"DEBUG: raw_stream type: {type(raw_stream)}") # LOG 3
        
        if hasattr(raw_stream, 'seek'):
            print("DEBUG: Resetting stream pointer via seek(0)") # LOG 4
            raw_stream.seek(0)
            
        media = MediaIoBaseUpload(raw_stream, mimetype=mime_type, resumable=True)
        print("DEBUG: MediaIoBaseUpload object created") # LOG 5
        
        # 1. Upload the file
        print("DEBUG: Initiating service.files().create().execute()") # LOG 6
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        print(f"DEBUG: Upload complete. File ID: {file_id}") # LOG 7
        
        # 2. Make it Public
        try:
            service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'},
            ).execute()
            print("DEBUG: Public permissions set") # LOG 8
        except Exception as p_err:
            print(f"DEBUG WARNING: Could not set permissions: {p_err}")

        # 3. Generate High-Quality Display Link
        direct_link = f"https://drive.google.com/thumbnail?id={file_id}&sz=s4000"
        
        return {
            "id": file_id, 
            "url": direct_link
        }

    except Exception as e:
        print(f"DEBUG ERROR: Drive Upload failed at step. Details: {str(e)}") # LOG 9
        raise e

def delete_file_from_drive(file_id):
    """Deletes a file from Google Drive permanently"""
    try:
        service = authenticate_drive()
        service.files().delete(fileId=file_id).execute()
        # print(f"Deleted Drive File ID: {file_id}")
        return True
    except Exception as e:
        # print(f"Error deleting file {file_id}: {e}")
        return False
