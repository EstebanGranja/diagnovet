from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from pypdf import PdfReader

# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="DiagnoVET API",
    description="PDF processing API for veterinary ultrasound reports",
    version="1.0.0"
)

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "message": "DiagnoVET API is running",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.post("/upload-report")
async def upload_report(file: UploadFile = File(...)):
    """
    Upload a PDF ultrasound report for processing
    
    Args:
        file: PDF file to process
        
    Returns:
        JSON with extracted data and image URLs
    """
    
    # Validar que sea PDF
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # TODO: Implementar lógica de procesamiento
    # 1. Leer el PDF
    # 2. Extraer texto con Document AI
    # 3. Extraer imágenes
    # 4. Subir imágenes a Cloud Storage
    # 5. Guardar metadata en Firestore
    
    return {
        "status": "received",
        "filename": file.filename,
        "message": "Processing not implemented yet"
    }

@app.get("/reports/{report_id}")
def get_report(report_id: str):
    """
    Retrieve a processed report by ID
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON with report data and image URLs
    """
    
    # TODO: Implementar lógica de recuperación desde Firestore
    
    return {
        "report_id": report_id,
        "message": "Retrieval not implemented yet"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)