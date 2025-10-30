import pickle
import io
import uuid
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request

# -------------------------------
# 🗝️ Settings
# -------------------------------
TOKEN_PATH = "token.pkl"  # Token for efgh80228@gmail.com
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# ✅ Your new shared folder ID
FOLDER_ID = "your_folder"

# 📄 File to upload (you can change path or file)
TEST_FILE_PATH = r"C:\Users\mprah\Downloads\Resume_2 (1)_compressed.pdf"


# -------------------------------
# 🚀 Authenticate Google Drive
# -------------------------------
def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)
    service = build("drive", "v3", credentials=creds)
    return service


# -------------------------------
# 📤 Upload File
# -------------------------------
def upload_file(file_path, folder_id):
    service = get_drive_service()
    filename = os.path.basename(file_path)
    ext = filename.split(".")[-1].lower()

    mime_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png"
    }
    mime_type = mime_types.get(ext, "application/octet-stream")

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type)

    file_metadata = {
        "name": f"UPLOAD_{uuid.uuid4().hex}_{filename}",
        "parents": [folder_id]
    }

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    print("✅ Upload successful!")
    print("📁 File ID:", uploaded.get("id"))
    print("🔗 File Link:", uploaded.get("webViewLink"))


# -------------------------------
# ▶️ Run
# -------------------------------
if __name__ == "__main__":
    if not os.path.exists(TEST_FILE_PATH):
        print("❌ File not found! Please check TEST_FILE_PATH.")
    else:
        upload_file(TEST_FILE_PATH, FOLDER_ID)
