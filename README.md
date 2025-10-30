
# AI Interview Automation Pipeline
##  Overview

**AI Interview Automation Pipeline** is an intelligent end-to-end system that automates candidate interview analysis using AI. It collects resumes, processes them with **Gemini AI**, and generates structured evaluations and ATS scores. The system integrates seamlessly with Firebase, Google Drive, and Google Sheets for efficient, automated workflows.

---

<p align="center">
  <img src="https://github.com/umamanipraharshitha/ai-interview-automation-pipeline/blob/main/demo.png" alt="AI Interview Pipeline Flow" width="800">
</p>

---



##  Architecture

```
Flutter App (Frontend)
       ↓ Firebase Authentication
FastAPI Backend (Python)
       ↓ Google Drive (File Storage)
Gemini AI (Resume Analysis)
       ↓ Google Sheets (Result Logging)
       ↓ Optional Email Notification
```

---

## Tech Stack

| Component        | Technology        |
| ---------------- | ----------------- |
| Frontend         | Flutter           |
| Authentication   | Firebase          |
| Backend          | FastAPI           |
| File Storage     | Google Drive API  |
| AI Processing    | Gemini API        |
| Data Logging     | Google Sheets API |
| Email Service    | Gmail SMTP        |
| Environment Vars | python-dotenv     |

---

##  Key Features

* Firebase Authentication for secure access
* Resume uploads directly from Flutter app
* Automated backend processing using FastAPI
* Gemini AI analysis of candidate profiles and resumes
* Automatic result logging to Google Sheets
* Email reports and candidate insights

---

## Folder Structure

```
ai-interview-automation-pipeline/
│
├── firebase_backend/
│   ├── main.py                # FastAPI backend
│   ├── automation.py          # Gemini + Sheets automation
│   ├── test.py 
│   ├── serviceAccountKey.json # Firebase Admin key (private)
│   ├── service.json           # Google service key (private)
│   ├── .env                   # Environment variables
│   └── requirements.txt
│
└── flutter_frontend/
    ├── lib/
    │   ├── main.dart
    │   ├── login_screen.dart
    │   ├── signup_screen.dart
    │   └── home_screen.dart
    └── pubspec.yaml
```

---

## Setup Instructions

### 1️ Clone the Repository

```bash
git clone https://github.com/umamanipraharshitha/ai-interview-automation-pipeline.git
cd ai-interview-automation-pipeline
```

### 2️ Backend Setup

```bash
cd firebase_backend
pip install -r requirements.txt
```

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
SENDER_EMAIL=youremail@gmail.com
SENDER_PASSWORD=your_app_password
SPREADSHEET_ID=your_google_sheet_id
FOLDER_ID=your_drive_folder_id
```

Run the backend:

```bash
uvicorn main:app --reload
```

### 3️ Frontend Setup

```bash
cd ../flutter_frontend
flutter pub get
flutter run
```

### 4️ Google APIs Setup

* Go to [Google Cloud Console](https://console.cloud.google.com/)
* Enable **Drive API** and **Sheets API**
* Create a **Service Account**, download the JSON key as `service.json`
* Share the target Drive folder & Sheet with the service account email

---

## Example Output

| Filename   | Name                    | Domain       | Skills              | Education         | ATS Score |
| ---------- | ----------------------- | ------------ | ------------------- | ----------------- | --------- |
| resume.pdf | Uma Mani Praharshitha M | Data Science | Python, FastAPI, ML | B.Tech CSE, JNTUK | 88%       |

---

##  Workflow Summary

1. Candidate logs in via Flutter using Firebase.
2. Uploads resume → FastAPI uploads to Google Drive.
3. Gemini AI processes and extracts key insights.
4. Results saved in Google Sheets automatically with descreasing order of ATS score.


---

## Future Enhancements

* AI-based interview question generator
* Recruiter dashboard with visualization & shortlisting
* Real-time analytics of ATS scores
* Integration with LinkedIn for profile import



