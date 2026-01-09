import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# 1. SCOPES: We need full Drive access
SCOPES = ['https://www.googleapis.com/auth/drive']

# 2. FILE PATHS
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

# 3. YOUR FOLDER ID (From your link)
PARENT_FOLDER_ID = '18aO52EB8Tyc_dbXEpKl7FWc00Cr-dLJs'

def authenticate_drive():
    creds = None
    # A. Load existing token if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # B. If no valid token, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # If refresh fails, delete token and re-login
                os.remove(TOKEN_FILE)
                return authenticate_drive()
        else:
            # This flow opens a browser window for you to login
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError("Missing 'credentials.json'. Download it from Google Cloud Console (OAuth Client ID).")
                
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # C. Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

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
