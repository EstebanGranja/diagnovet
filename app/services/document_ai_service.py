from google.cloud import documentai_v1 as documentai
from app.config import Config

class DocumentAIService:
    def __init__(self):
        self.client = documentai.DocumentProcessorServiceClient()
        self.processor_name = self.client.processor_path(
            Config.PROJECT_ID,
            Config.LOCATION,
            Config.PROCESSOR_ID
        )
    
    def process_pdf(self, pdf_content: bytes) -> documentai.Document:
        """
        Procesa un PDF y extrae texto/estructura
        
        Args:
            pdf_content: Contenido del PDF en bytes
            
        Returns:
            Document object con texto extraído
        """
        # Configurar el request
        raw_document = documentai.RawDocument(
            content=pdf_content,
            mime_type="application/pdf"
        )
        
        # Configurar opciones de procesamiento
        # skip_human_review y process_options para manejar documentos grandes
        process_options = documentai.ProcessOptions(
            ocr_config=documentai.OcrConfig(
                enable_image_quality_scores=False,
            )
        )
        
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document,
            skip_human_review=True,
            process_options=process_options
        )
        
        # Procesar documento
        result = self.client.process_document(request=request)
        
        return result.document
    
    def extract_text(self, document: documentai.Document) -> str:
        """Extraer todo el texto del documento"""
        return document.text
    
    def extract_form_fields(self, document: documentai.Document) -> dict:
        """
        Extraer campos de formulario (clave-valor)
        Útil para extraer: Patient, Owner, Veterinarian, etc.
        """
        fields = {}
        
        for page in document.pages:
            for field in page.form_fields:
                # Nombre del campo
                field_name = self._get_text(field.field_name, document.text)
                # Valor del campo
                field_value = self._get_text(field.field_value, document.text)
                
                if field_name and field_value:
                    fields[field_name.strip()] = field_value.strip()
        
        return fields
    
    def _get_text(self, layout, full_text: str) -> str:
        """Helper para extraer texto de un layout"""
        response = ""
        for segment in layout.text_anchor.text_segments:
            start_index = int(segment.start_index) if segment.start_index else 0
            end_index = int(segment.end_index)
            response += full_text[start_index:end_index]
        return response