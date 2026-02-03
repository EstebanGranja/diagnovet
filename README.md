# DiagnoVET - Backend Challenge

Cloud-native REST API for processing veterinary medical report PDFs. Extracts structured data using AI and stores images in the cloud.


## Tech Stack

| Service | Purpose |
|---------|---------|
| **FastAPI** | REST API framework |
| **Google Cloud Document AI** | PDF text extraction & form parsing |
| **Google Cloud Storage** | Image storage with public URLs |
| **Google Firestore** | NoSQL database for report metadata |
| **Cloud Run** | Serverless container hosting |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/upload-report` | Upload and process a PDF report |
| `GET` | `/reports` | List all reports (patient, owner, veterinarian, diagnosis, recommendations) |
| `GET` | `/reports/{report_id}` | Retrieve a specific report with metadata and images |
| `GET` | `/reports/{report_id}/images` | Retrieve only the images from a report |

## Live API

**Production URL:** `https://diagnovet-api-1069231448075.us-central1.run.app`

**Swagger Docs:** https://diagnovet-api-1069231448075.us-central1.run.app/docs

### Testing with Postman

1. **Health Check (GET `/`)**
   - URL: `https://diagnovet-api-1069231448075.us-central1.run.app/`

2. **Upload Report (POST `/upload-report`)**
   - URL: `https://diagnovet-api-1069231448075.us-central1.run.app/upload-report`
   - Header: `X-API-Key: your-api-key`
   - Body: Select "form-data", add a field `file` (type "File") with your PDF

3. **List Reports (GET `/reports`)**
   - URL: `https://diagnovet-api-1069231448075.us-central1.run.app/reports`
   - Header: `X-API-Key: your-api-key`
   - Response includes: `patient`, `owner`, `veterinarian`, `diagnosis`, `recommendations`

4. **Get Specific Report (GET `/reports/{report_id}`)**
   - URL: `https://diagnovet-api-1069231448075.us-central1.run.app/reports/{report_id}`
   - Header: `X-API-Key: your-api-key`
   - Response includes structured metadata and image URLs

5. **Get Report Images (GET `/reports/{report_id}/images`)**
   - URL: `https://diagnovet-api-1069231448075.us-central1.run.app/reports/{report_id}/images`
   - Header: `X-API-Key: your-api-key`
   - Response includes list of public image URLs from Cloud Storage

## Local Development

### Prerequisites
- Python 3.11+
- Google Cloud SDK configured
- GCP Project with enabled APIs:
  - Document AI
  - Cloud Storage
  - Firestore

### Setup

```bash
# Clone repository
git clone https://github.com/EstebanGranja/diagnovet.git
cd diagnovet

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your GCP credentials
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PROJECT_ID` | Google Cloud Project ID |
| `LOCATION` | Document AI location (e.g., `us`) |
| `PROCESSOR_ID` | Document AI Processor ID |
| `BUCKET_NAME` | Cloud Storage bucket name |

### Run Locally

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`

Swagger documentation at `http://localhost:8000/docs`

## Docker

```bash
# Build image
docker build -t diagnovet-api .

# Run container
docker run -p 8080:8080 -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json diagnovet-api
```

## Deploy to Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/diagnovet-api

# Deploy to Cloud Run
gcloud run deploy diagnovet-api \
  --image gcr.io/PROJECT_ID/diagnovet-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## Project Structure

```
diagnovet/
├── app/
│   ├── __init__.py
│   ├── config.py              # Environment configuration
│   ├── main.py                # FastAPI application & routes
│   └── services/
│       ├── document_ai_service.py  # Document AI integration
│       ├── firestore_service.py    # Firestore operations
│       ├── pdf_processor.py        # PDF processing orchestrator
│       └── storage_service.py      # Cloud Storage operations
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```


