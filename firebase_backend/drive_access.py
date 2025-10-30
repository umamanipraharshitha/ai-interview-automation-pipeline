from google.oauth2 import service_account
from googleapiclient.discovery import build

# Path to your service account file
SERVICE_ACCOUNT_FILE = "service.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Authenticate
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# Build Drive service
drive_service = build("drive", "v3", credentials=creds)

# Example: List files in Google Drive
results = drive_service.files().list(
    pageSize=10, fields="files(id, name)"
).execute()
items = results.get("files", [])

if not items:
    print("No files found.")
else:
    print("Files:")
    for item in items:
        print(f"{item['name']} ({item['id']})")
