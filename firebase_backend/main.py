from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials as fb_credentials, firestore, auth, initialize_app
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
import io, uuid, pickle, os

# -----------------------------
# 🔥 Firebase Initialization
# -----------------------------
fb_cred = fb_credentials.Certificate("serviceAccountKey.json")
initialize_app(fb_cred)
db = firestore.client()

# -----------------------------
# 🔑 Google Drive (token.pkl-based)
# -----------------------------
TOKEN_PATH = "token.pkl"  # from your working upload script
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_ID = "your_folder"  # your working Drive folder

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
# -----------------------------
# 🚀 FastAPI App
# -----------------------------
app = FastAPI(title="AI Interview System Backend (Google Drive Integrated)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# 🧍 Signup
# -----------------------------
@app.post("/auth/signup")
async def signup_user(uid: str = Form(...), name: str = Form(...), email: str = Form(...)):
    try:
        db.collection("users").document(uid).set({
            "uid": uid,
            "name": name,
            "email": email,
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        return {"message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------
# 🧍 Login
# -----------------------------
@app.post("/auth/login")
async def login_user(email: str = Form(...), password: str = Form(...)):
    if email and password:
        return {"message": "Login successful", "email": email}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# -----------------------------
# 🔐 Verify Firebase ID Token
# -----------------------------
@app.get("/auth/verify")
async def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    try:
        token = authorization.split(" ")[1]
        decoded = auth.verify_id_token(token)
        return {"uid": decoded["uid"], "email": decoded.get("email")}
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Invalid token: {e}")

# -----------------------------
# 📤 Upload Resume → Google Drive
# -----------------------------
@app.post("/upload/resume")
async def upload_resume(file: UploadFile = File(...), user_id: str = Form(...)):
    try:
        # ✅ Read uploaded file
        file_bytes = await file.read()

        # ✅ Detect MIME type
        ext = file.filename.split(".")[-1].lower()
        mime_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
        }
        mime_type = mime_types.get(ext, "application/octet-stream")

        # ✅ Build file metadata
        filename = f"{user_id}_{uuid.uuid4().hex}_{file.filename}"
        file_metadata = {"name": filename, "parents": [FOLDER_ID]}

        # ✅ Prepare upload
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type)
        drive_service = get_drive_service()

        # ✅ Upload to Drive
        uploaded = (
            drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )

        file_link = uploaded.get("webViewLink")

        return {"message": "✅ Upload successful", "file_url": file_link}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
# -----------------------------
# 🌐 Root Endpoint
# -----------------------------
@app.get("/")
def root():
    return {"message": "AI Interview System Backend (Google Drive Integrated) 🚀"}
