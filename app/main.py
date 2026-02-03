from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from pypdf import PdfReader
from app.services.pdf_processor import PDFProcessor

# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="DiagnoVET API",
    description="PDF processing API for veterinary ultrasound reports",
    version="1.0.0"
)

# API Key para autenticación
API_KEY = os.getenv("API_KEY")

def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """
    Verifies the API Key in the header.
    If API_KEY is not set, allows free access (development).
    """
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(
            status_code=401, 
            detail="Invalid or missing API Key. Include 'X-API-Key' header."
        )
    return x_api_key

@app.get("/")
def root():
    """Health check endpoint - público"""
    return {
        "message": "DiagnoVET API is running",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/reports")
def list_reports(limit: int = 10, _: str = Depends(verify_api_key)):
    """
    List all processed reports (requires API Key)
    
    Args:
        limit: Maximum number of reports to return (default 10)
        
    Returns:
        List of reports with basic info
    """
    from app.services.firestore_service import FirestoreService
    
    firestore = FirestoreService()
    docs = firestore.collection.order_by('created_at', direction='DESCENDING').limit(limit).stream()
    
    reports = []
    for doc in docs:
        data = doc.to_dict()
        # Convertir datetime
        created_at = data.get('created_at')
        if hasattr(created_at, 'isoformat'):
            created_at = created_at.isoformat()
        
        reports.append({
            "report_id": doc.id,
            "patient_name": data.get('patient', {}).get('name'),
            "species": data.get('patient', {}).get('species'),
            "owner": data.get('owner', {}).get('name'),
            "images_count": len(data.get('images', [])),
            "created_at": created_at
        })
    
    return {
        "total": len(reports),
        "reports": reports
    }



@app.post("/upload-report")
async def upload_report(file: UploadFile = File(...), _: str = Depends(verify_api_key)):
    """
    Upload and process a veterinary PDF report (requires API Key)
    """
    # Leer el PDF del request
    pdf_content = await file.read()
    
    # Procesar
    processor = PDFProcessor()
    result = processor.process_report(pdf_content, file.filename)
    
    return result



@app.get("/reports/{report_id}")
def get_report(report_id: str, _: str = Depends(verify_api_key)):
    """
    Retrieve a processed report by ID (requires API Key)
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON with report data and image URLs
    """
    from app.services.firestore_service import FirestoreService
    
    firestore = FirestoreService()
    report = firestore.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Convertir datetime a string si existe
    if 'created_at' in report:
        created_at = report['created_at']
        if hasattr(created_at, 'isoformat'):
            report['created_at'] = created_at.isoformat()
        else:
            report['created_at'] = str(created_at)
    
    return {
        "report_id": report_id,
        "data": report
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)