"""
PDF Processor - Orquesta la extracción y almacenamiento de reportes
"""
from app.services.document_ai_service import DocumentAIService
from app.services.storage_service import StorageService
from app.services.firestore_service import FirestoreService
from pypdf import PdfReader
from io import BytesIO
from PIL import Image
from datetime import datetime
import json


def json_serializer(obj):
    """Serializador personalizado para objetos no JSON serializables"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

class PDFProcessor:
    def __init__(self):
        self.document_ai = DocumentAIService()
        self.storage = StorageService()
        self.firestore = FirestoreService()
    
    def process_report(self, pdf_content: bytes, filename: str) -> dict:
        """
        Procesa un reporte completo: extrae datos, imágenes y guarda todo
        
        Args:
            pdf_content: Contenido del PDF en bytes
            filename: Nombre del archivo original
            
        Returns:
            Diccionario con el reporte completo y su ID
        """
        print(f"Procesando: {filename}")
        
        # 1. Extraer texto con Document AI
        print("Extrayendo texto con Document AI...")
        document = self.document_ai.process_pdf(pdf_content)
        
        # 2. Parsear la información
        print("Parseando información del reporte...")
        report_data = self._parse_report(document)
        
        # 3. Extraer imágenes del PDF
        print("Extrayendo imágenes...")
        image_urls = self._extract_and_upload_images(pdf_content, filename)
        report_data['images'] = image_urls
        
        # 4. Guardar en Firestore
        print("Guardando en Firestore...")
        report_id = self.firestore.save_report(report_data)
        
        print(f"Reporte procesado: {report_id}")
        
        return {
            "report_id": report_id,
            "data": report_data
        }
    
    def _parse_report(self, document) -> dict:
        """
        Parsea el documento de Document AI y extrae campos estructurados
        """
        # Extraer texto completo
        full_text = self.document_ai.extract_text(document)
        
        # Extraer campos clave-valor
        form_fields = self.document_ai.extract_form_fields(document)
        
        # TODO: Implementar lógica de parseo inteligente
        # Por ahora devolvemos la estructura básica
        
        report = {
            "patient": {
                "name": self._find_field(form_fields, ["Paciente", "Patient"]),
                "species": self._find_field(form_fields, ["Especie", "Species"]),
                "breed": self._find_field(form_fields, ["Raza", "Breed"]),
                "sex": self._find_field(form_fields, ["Sexo", "Sex"]),
                "age": self._find_field(form_fields, ["Edad", "Age"])
            },
            "owner": {
                "name": self._find_field(form_fields, ["Tutor", "Propietario", "Owner"])
            },
            "veterinarian": self._find_field(form_fields, ["Derivante", "Referido por", "Veterinarian"]),
            "diagnosis": self._extract_section(full_text, ["DIAGNÓSTICO", "CONCLUSIÓN"]),
            "recommendations": self._extract_section(full_text, ["Notas", "Recomendaciones"]),
            "raw_text": full_text,
            "extracted_fields": form_fields
        }
        
        return report
    
    def _find_field(self, fields: dict, possible_keys: list) -> str:
        """
        Busca un campo con diferentes posibles nombres
        """
        for key in possible_keys:
            # Buscar coincidencia exacta o parcial (case-insensitive)
            for field_key, field_value in fields.items():
                if key.lower() in field_key.lower():
                    return field_value
        return None
    
    def _extract_section(self, text: str, section_headers: list) -> str:
        """
        Extrae una sección específica del texto
        """
        # TODO: Implementar lógica para extraer secciones
        # Por ahora devolvemos None
        return None
    
    def _extract_and_upload_images(self, pdf_content: bytes, filename: str) -> list:
        """
        Extrae imágenes del PDF y las sube a Cloud Storage
        
        Returns:
            Lista de URLs públicas de las imágenes
        """
        image_urls = []
        
        try:
            # Leer PDF
            pdf_reader = PdfReader(BytesIO(pdf_content))
            image_count = 0
            
            print(f"  PDF tiene {len(pdf_reader.pages)} páginas")
            
            # Recorrer páginas
            for page_num, page in enumerate(pdf_reader.pages):
                print(f"  Procesando página {page_num + 1}...")
                
                try:
                    # Método 1: Usar page.images (pypdf >= 3.0)
                    images_list = list(page.images) if hasattr(page, 'images') else []
                    print(f"    Encontradas {len(images_list)} imágenes en página {page_num + 1}")
                    
                    for img_index, image in enumerate(images_list):
                        try:
                            img_bytes = image.data
                            img_name = getattr(image, 'name', None) or f"image_{img_index}"
                            
                            print(f"    Procesando imagen: {img_name}, size: {len(img_bytes) if img_bytes else 0} bytes")
                            
                            # Verificar que tenga contenido mínimo
                            if img_bytes and len(img_bytes) > 100:
                                # Determinar extensión basada en el contenido
                                ext = 'png'
                                if img_bytes[:2] == b'\xff\xd8':  # JPEG magic bytes
                                    ext = 'jpg'
                                elif img_bytes[:8] == b'\x89PNG\r\n\x1a\n':  # PNG magic bytes
                                    ext = 'png'
                                
                                # Generar nombre único
                                clean_filename = filename.replace('.pdf', '').replace(' ', '_').replace('/', '_')
                                img_filename = f"{clean_filename}_p{page_num + 1}_img{img_index + 1}.{ext}"
                                
                                # Subir a Cloud Storage
                                url = self.storage.upload_image(img_bytes, img_filename)
                                image_urls.append(url)
                                image_count += 1
                                print(f"      ✓ Imagen subida: {img_filename}")
                            else:
                                print(f"      ⚠ Imagen muy pequeña, ignorada")
                                
                        except Exception as e:
                            print(f"      ✗ Error extrayendo imagen {img_index}: {type(e).__name__}: {e}")
                            continue
                            
                except Exception as page_error:
                    print(f"    ✗ Error procesando página {page_num + 1}: {type(page_error).__name__}: {page_error}")
                    continue
            
            print(f"  Total imágenes extraídas y subidas: {image_count}")
                
        except Exception as e:
            print(f"Error general procesando imágenes del PDF: {type(e).__name__}: {e}")
        
        return image_urls


# Función standalone para testing rápido
def test_local_pdf(pdf_path: str):
    """
    Función de prueba para procesar un PDF local
    """
    processor = PDFProcessor()
    
    print(f"Leyendo PDF: {pdf_path}")
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
    
    print(f"PDF leído: {len(pdf_content)} bytes\n")
    
    result = processor.process_report(pdf_content, pdf_path)
    
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=json_serializer))
    
    return result


if __name__ == "__main__":
    # Esto solo se ejecuta cuando corres el archivo directamente
    # python -m app.services.pdf_processor
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "test_pdf.pdf"
    
    test_local_pdf(pdf_path)