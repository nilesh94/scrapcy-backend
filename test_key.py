from google.oauth2 import service_account
import google.auth.transport.requests

# Define Scope
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = 'service_account.json'

print("1. Reading service_account.json...")
try:
    # Attempt to load credentials
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    
    print("2. File read successfully. Attempting to authenticate with Google...")
    
    # Create a request object to force a token refresh
    request = google.auth.transport.requests.Request()
    
    # This triggers the JWT signing and sending to Google
    creds.refresh(request)
    
    print("\nSUCCESS: The key is valid and authentication worked!")
    print(f"Access Token: {creds.token[:10]}...")

except Exception as e:
    print("\nFAILURE: Authentication failed.")
    print(f"Error Details: {e}")
    
    # Check for common formatting issues
    import json
    with open(SERVICE_ACCOUNT_FILE, 'r') as f:
        data = json.load(f)
        key = data.get('private_key', '')
        if "\\n" in key and "\n" not in key:
            print("\nDIAGNOSIS: It looks like your newlines are double-escaped (\\n).")
            print("Try replacing \\n with actual newlines in the file.")
