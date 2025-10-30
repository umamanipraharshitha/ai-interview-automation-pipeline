import os
import io
import time
import json
import requests
import smtplib
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# ---------------------------
# Config: Google / Sheets
# ---------------------------
SERVICE_ACCOUNT_FILE = "service.json"
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Put your spreadsheet ID here (you already shared this one earlier)
SPREADSHEET_ID = "your_spreadsheet_id"
SHEET_NAME = "sheet_name"

# Desired headers in the sheet (final order)
HEADERS = [
    "Filename",
    "Name",
    "Domain",
    "Email",
    "Skills",
    "Education",
    "Projects",
    "Summary",
    "Experience",
    "ATS Score",
]

# Gemini model endpoint
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_UPLOAD_URL = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={GEMINI_API_KEY}"
GEMINI_ANALYZE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

# ---------------------------
# Helpers: Google Services
# ---------------------------
def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

# ---------------------------
# Ensure headers exist in Sheet
# ---------------------------
def ensure_headers():
    sheets = get_sheets_service().spreadsheets()
    header_range = f"{SHEET_NAME}!A1:J1"
    try:
        result = sheets.values().get(spreadsheetId=SPREADSHEET_ID, range=header_range).execute()
        values = result.get("values", [])
        if not values or len(values[0]) < len(HEADERS):
            # Write headers
            sheets.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=header_range,
                valueInputOption="RAW",
                body={"values": [HEADERS]},
            ).execute()
            print("✅ Headers created/updated in Google Sheet.")
        else:
            print("✅ Headers already present.")
    except Exception as e:
        print("❌ Error ensuring headers:", e)
        raise

# ---------------------------
# Get list of filenames already present (to skip duplicates)
# ---------------------------
def get_existing_filenames():
    sheets = get_sheets_service().spreadsheets()
    try:
        result = sheets.values().get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A2:A").execute()
        values = result.get("values", [])
        existing = [row[0] for row in values if len(row) > 0]
        return set(existing)
    except Exception as e:
        print("⚠️ Could not fetch existing filenames, will assume none exist. Error:", e)
        return set()

# ---------------------------
# Append a row to the sheet
# ---------------------------
def append_row_to_sheet(row):
    sheets = get_sheets_service().spreadsheets()
    try:
        sheets.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:J",
            valueInputOption="RAW",
            body={"values": [row]},
        ).execute()
        print(f"📄 Added '{row[0]}' to Google Sheet.")
    except Exception as e:
        print("❌ Failed to append row to Google Sheet:", e)
        raise

# ---------------------------
# Sort sheet by ATS Score (descending)
# ---------------------------
def sort_sheet_by_ats():
    sheets = get_sheets_service()
    # ATS Score is column J (index 9). We will use the batchUpdate sort request.
    try:
        body = {
            "requests": [
                {
                    "sortRange": {
                        "range": {
                            "sheetId": 0,            # Usually Sheet1 has ID 0; if not, you can fetch actual sheetId
                            "startRowIndex": 1,     # skip header row
                        },
                        "sortSpecs": [
                            {
                                "dimensionIndex": 9,  # J column (0-based index)
                                "sortOrder": "DESCENDING"
                            }
                        ]
                    }
                }
            ]
        }
        sheets.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
        print("🔽 Sheet sorted by ATS Score (descending).")
    except Exception as e:
        # If sheetId 0 is wrong for your sheet, fetch actual sheetId then retry:
        try:
            meta = sheets.get(spreadsheetId=SPREADSHEET_ID).execute()
            sheet_id = meta["sheets"][0]["properties"]["sheetId"]
            body["requests"][0]["sortRange"]["range"]["sheetId"] = sheet_id
            sheets.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
            print("🔽 Sheet sorted by ATS Score (descending) using fetched sheetId.")
        except Exception as e2:
            print("❌ Failed to sort sheet:", e2)

# ---------------------------
# Upload file to Gemini (returns file_uri)
# ---------------------------
def upload_file_to_gemini(file_name, file_bytes):
    try:
        resp = requests.post(GEMINI_UPLOAD_URL, files={"file": (file_name, file_bytes, "application/pdf")}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if "file" in data and "uri" in data["file"]:
            return data["file"]["uri"]
        else:
            print("⚠️ Unexpected Gemini upload response:", data)
            return None
    except Exception as e:
        print("❌ Gemini upload failed:", e)
        return None

# ---------------------------
# Ask Gemini to analyze; Strong prompt to force JSON
# ---------------------------
def analyze_with_gemini(file_uri, max_retries=3, backoff=3):
    prompt = """
You are a strict JSON-only responder. Analyze the resume PDF given by the file URI provided in the file_data part.
Return ONLY valid JSON (no explanatory text) with EXACT keys:
"name", "domain", "email", "skills", "education", "projects", "summary", "experience", "ats_score"

Requirements:
- "name": string or "N/A"
- "domain": string (e.g., "Data Science", "Software Engineering") or "N/A"
- "email": string or "N/A"
- "skills": JSON array of strings (e.g., ["Python","SQL"])
- "education": string (short)
- "projects": JSON array of objects OR string; if array, each project object with "title" and "description" fields
- "summary": short textual summary string
- "experience": string describing years/roles
- "ats_score": integer between 0 and 100

Do not include any other keys. If you cannot determine a field, set it to "N/A" or an empty array for lists.
Output must be parseable by a JSON parser.
"""

    payload = {
        "contents": [
            {"parts": [{"file_data": {"mime_type": "application/pdf", "file_uri": file_uri}}]},
            {"parts": [{"text": prompt}]}
        ]
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(GEMINI_ANALYZE_URL, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
            # If service overloaded, allow retry with backoff
            if resp.status_code == 503:
                print(f"⚠️ Gemini overloaded (503). Retry {attempt}/{max_retries} after backoff.")
                time.sleep(backoff * attempt)
                continue
            resp.raise_for_status()
            data = resp.json()
            # Expect candidates -> content -> parts -> text
            if "candidates" in data and len(data["candidates"]) > 0:
                part = data["candidates"][0]["content"]["parts"][0]
                text = part.get("text", "")
                return text
            else:
                print("⚠️ Gemini returned unexpected payload:", data)
                return None
        except Exception as e:
            print(f"⚠️ Gemini request failed on attempt {attempt}: {e}")
            time.sleep(backoff * attempt)
    return None

# ---------------------------
# Parse Gemini JSON (with robust fallback)
# ---------------------------
def parse_gemini_output(text):
    if not text:
        return None

    # If text looks like JSON, try parse
    try:
        parsed = json.loads(text)
        return parsed
    except Exception:
        # If model returned text but included a JSON block, try to extract JSON substring
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(text[start:end+1])
                return parsed
            except Exception:
                pass
    # Fallback: return minimal map with summary only
    return {"name": "N/A", "domain": "N/A", "email": "N/A", "skills": [], "education": "N/A", "projects": [], "summary": text, "experience": "N/A", "ats_score": "N/A"}

# ---------------------------
# Analyze one resume file id -> dictionary result
# ---------------------------
def analyze_resume_file(file_id, file_name):
    drive = get_drive_service()
    request = drive.files().get_media(fileId=file_id)
    file_buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(file_buffer, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    file_buffer.seek(0)
    file_bytes = file_buffer.read()

    # Upload to Gemini
    file_uri = upload_file_to_gemini(file_name, file_bytes)
    if not file_uri:
        print("❌ Upload to Gemini failed for", file_name)
        return None

    print("📤 Uploaded to Gemini successfully.")
    gemini_text = analyze_with_gemini(file_uri)
    if not gemini_text:
        print("⚠️ No analysis returned by Gemini.")
        return None

    parsed = parse_gemini_output(gemini_text)
    if not parsed:
        print("⚠️ Could not parse Gemini output at all.")
        return None

    # Normalize fields and types
    # Ensure keys exist
    normalized = {}
    normalized["name"] = parsed.get("name", "N/A")
    normalized["domain"] = parsed.get("domain", "N/A")
    normalized["email"] = parsed.get("email", "N/A")

    skills = parsed.get("skills", [])
    if isinstance(skills, str):
        # split by commas heuristically
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    elif not isinstance(skills, list):
        skills = []

    normalized["skills"] = skills
    normalized["education"] = parsed.get("education", "N/A")
    normalized["projects"] = parsed.get("projects", [])
    normalized["summary"] = parsed.get("summary", "N/A")
    normalized["experience"] = parsed.get("experience", "N/A")

    ats = parsed.get("ats_score", parsed.get("score", "N/A"))
    # try cast to int
    try:
        ats = int(ats)
        if ats < 0: ats = 0
        if ats > 100: ats = 100
    except Exception:
        ats = "N/A"
    normalized["ats_score"] = ats

    return normalized

# ---------------------------
# Build row in correct order for sheet
# ---------------------------
def build_row(file_name, parsed):
    skills_str = ", ".join(parsed.get("skills", [])) if parsed.get("skills") else "N/A"
    # projects: if array of objects, make short representation
    projects = parsed.get("projects", [])
    if isinstance(projects, list):
        proj_summ = []
        for p in projects[:3]:
            if isinstance(p, dict):
                title = p.get("title") or p.get("name") or ""
                desc = p.get("description") or p.get("desc") or ""
                proj_summ.append(f"{title}: {desc}".strip(": "))
            else:
                proj_summ.append(str(p))
        projects_str = " | ".join([s for s in proj_summ if s]) if proj_summ else "N/A"
    else:
        projects_str = str(projects) if projects else "N/A"

    row = [
        file_name,
        parsed.get("name", "N/A"),
        parsed.get("domain", "N/A"),
        parsed.get("email", "N/A"),
        skills_str,
        parsed.get("education", "N/A"),
        projects_str,
        parsed.get("summary", "N/A"),
        parsed.get("experience", "N/A"),
        parsed.get("ats_score", "N/A"),
    ]
    return row

# ---------------------------
# Send Email
# ---------------------------
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"📨 Email sent to {to_email}")
    except Exception as e:
        print("❌ Failed to send email:", e)

# ---------------------------
# Main process
# ---------------------------
def process_resumes_from_drive():
    # ensure headers
    ensure_headers()

    # 👇 Your specific Google Drive folder ID
    FOLDER_ID = "your_folder_id"

    # get Drive files only from that folder
    drive = get_drive_service()
    results = drive.files().list(
        q=f"'{FOLDER_ID}' in parents and mimeType='application/pdf'",
        fields="files(id, name)"
    ).execute()
    files = results.get("files", [])

    if not files:
        print("⚠️ No PDF resumes found in Google Drive folder.")
        return

    existing = get_existing_filenames()
    print(f"📋 {len(existing)} resumes already in sheet. Skipping duplicates.")

    for f in files:
        file_id = f["id"]
        file_name = f["name"]

        if file_name in existing:
            print(f"⏭️ Skipping already processed resume: {file_name}")
            continue

        print(f"\n📄 Processing {file_name}...")
        parsed = analyze_resume_file(file_id, file_name)
        if not parsed:
            print(f"⚠️ Skipping {file_name} due to analysis failure.")
            continue

        row = build_row(file_name, parsed)
        append_row_to_sheet(row)

        # send email summary
        email_body = (
            f"Resume: {file_name}\n\n"
            f"Name: {row[1]}\nDomain: {row[2]}\nEmail: {row[3]}\nATS Score: {row[9]}\n\n"
            f"Skills: {row[4]}\nEducation: {row[5]}\nProjects: {row[6]}\nExperience: {row[8]}\n\nSummary:\n{row[7]}"
        )
        send_email("your_mail", subject=f"AI Resume Summary - {file_name}", body=email_body)

    # After all append, sort sheet by ATS Score
    sort_sheet_by_ats()
    print("\n✅ All resumes processed and sheet updated.")

# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    process_resumes_from_drive()
