# DiagnoVET - Backend Challenge

PDF processing API for veterinary ultrasound reports using Google Cloud Platform.

## Tech Stack
- FastAPI
- Google Cloud Document AI
- Google Cloud Storage
- Google Firestore
- Cloud Run

## Local Development

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  
# Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload
```

## API Endpoints

- `GET /` - Health check
- `POST /upload-report` - Upload PDF report
- `GET /reports/{report_id}` - Retrieve processed report

## Deployment

(To be completed)