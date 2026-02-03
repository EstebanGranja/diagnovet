from fastapi import FastAPI, UploadFile, File, HTTPException
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
    # Leer el PDF del request
    pdf_content = await file.read()
    
    # Procesar
    processor = PDFProcessor()
    result = processor.process_report(pdf_content, file.filename)
    
    return result



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