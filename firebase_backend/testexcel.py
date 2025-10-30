from googleapiclient.discovery import build
from google.oauth2 import service_account

# === CONFIG ===
SERVICE_ACCOUNT_FILE = "service.json"  # your service account file path
SPREADSHEET_ID = "sheet_id"  # your sheet ID
RANGE_NAME = "Sheet1!A1:E5"  # first 5 rows

# === AUTH ===
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# === BUILD SERVICE ===
service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()

try:
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get("values", [])

    if not values:
        print("✅ Connected successfully, but no data found in the first 5 rows.")
    else:
        print("✅ Connected successfully! Here’s your sheet data preview:")
        for row in values:
            print(row)

except Exception as e:
    print("❌ Error connecting to Google Sheets:")
    print(e)
