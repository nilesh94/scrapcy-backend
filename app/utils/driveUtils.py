import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# 1. SCOPES
SCOPES = ['https://www.googleapis.com/auth/drive']

# 2. FILE PATHS
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

# 3. YOUR FOLDER ID
PARENT_FOLDER_ID = '18aO52EB8Tyc_dbXEpKl7FWc00Cr-dLJs'

def authenticate_drive():
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None

    if creds and creds.valid:
        return build('drive', 'v3', credentials=creds)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            return build('drive', 'v3', credentials=creds)
        except Exception:
            pass

    raise Exception(f"Authentication Failed! Token file at {TOKEN_FILE} is invalid or missing.")

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
            fields='id'  # <--- WE ONLY NEED THE ID NOW
        ).execute()

        file_id = file.get('id')

        # Make Public
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()

        # --- CRITICAL FIX ---
        # Construct a DIRECT IMAGE LINK using the lh3 domain (Google's Image CDN).
        # webViewLink is a HTML page, which breaks <img> tags.
        # This link points directly to the image binary.
        direct_link = f"https://lh3.googleusercontent.com/d/{file_id}"
        
        return direct_link

    except Exception as e:
        print(f"Drive Upload Error: {e}")
        raise e
