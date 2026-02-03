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
            
            # Recorrer páginas
            for page_num, page in enumerate(pdf_reader.pages):
                # Buscar imágenes en la página
                if '/Resources' in page and '/XObject' in page['/Resources']:
                    x_objects = page['/Resources']['/XObject']
                    
                    for obj_name in x_objects:
                        obj = x_objects[obj_name]
                        
                        # Verificar si es imagen
                        if obj.get('/Subtype') == '/Image':
                            try:
                                # Obtener filtro de compresión
                                img_filter = obj.get('/Filter')
                                
                                # Si es lista, tomar el primero
                                if isinstance(img_filter, list):
                                    img_filter = img_filter[0] if img_filter else None
                                
                                data = obj.get_data()
                                width = int(obj['/Width'])
                                height = int(obj['/Height'])
                                
                                img_bytes = None
                                img_format = 'PNG'
                                
                                # Manejar según el tipo de compresión
                                if img_filter == '/DCTDecode':
                                    # JPEG - usar datos directamente
                                    img_bytes = obj._data  # Datos raw JPEG
                                    img_format = 'JPEG'
                                    
                                elif img_filter == '/FlateDecode':
                                    # PNG/Raw comprimido con zlib
                                    color_space = obj.get('/ColorSpace')
                                    bits_per_component = int(obj.get('/BitsPerComponent', 8))
                                    
                                    # Determinar modo de color
                                    if color_space == '/DeviceRGB':
                                        mode = 'RGB'
                                    elif color_space == '/DeviceGray':
                                        mode = 'L'
                                    elif color_space == '/DeviceCMYK':
                                        mode = 'CMYK'
                                    else:
                                        # Intentar RGB por defecto
                                        mode = 'RGB'
                                    
                                    try:
                                        image = Image.frombytes(mode, (width, height), data)
                                        img_byte_arr = BytesIO()
                                        image.save(img_byte_arr, format='PNG')
                                        img_bytes = img_byte_arr.getvalue()
                                    except Exception:
                                        # Si falla, intentar abrir directamente
                                        try:
                                            image = Image.open(BytesIO(data))
                                            img_byte_arr = BytesIO()
                                            image.save(img_byte_arr, format='PNG')
                                            img_bytes = img_byte_arr.getvalue()
                                        except Exception:
                                            continue
                                            
                                elif img_filter == '/JPXDecode':
                                    # JPEG2000
                                    img_bytes = obj._data
                                    img_format = 'JPEG2000'
                                    
                                else:
                                    # Intentar abrir directamente con PIL
                                    try:
                                        image = Image.open(BytesIO(data))
                                        img_byte_arr = BytesIO()
                                        image.save(img_byte_arr, format='PNG')
                                        img_bytes = img_byte_arr.getvalue()
                                        img_format = 'PNG'
                                    except Exception:
                                        # Último intento: raw bytes
                                        try:
                                            color_space = obj.get('/ColorSpace', '/DeviceRGB')
                                            if color_space == '/DeviceRGB':
                                                mode = 'RGB'
                                            elif color_space == '/DeviceGray':
                                                mode = 'L'
                                            else:
                                                mode = 'RGB'
                                            
                                            image = Image.frombytes(mode, (width, height), data)
                                            img_byte_arr = BytesIO()
                                            image.save(img_byte_arr, format='PNG')
                                            img_bytes = img_byte_arr.getvalue()
                                        except Exception:
                                            continue
                                
                                # Subir a Cloud Storage si se extrajo la imagen
                                if img_bytes and len(img_bytes) > 100:  # Mínimo 100 bytes
                                    ext = 'jpg' if img_format == 'JPEG' else 'png'
                                    img_filename = f"{filename}_page{page_num}_{obj_name}.{ext}"
                                    url = self.storage.upload_image(img_bytes, img_filename)
                                    image_urls.append(url)
                                    print(f"  Imagen extraída: {obj_name}")
                                
                            except Exception as e:
                                print(f"Error extrayendo imagen {obj_name}: {e}")
                                continue
                                
                            except Exception as e:
                                print(f"Error extrayendo imagen {obj_name}: {e}")
                                continue
        
        except Exception as e:
            print(f"Error procesando imágenes: {e}")
        
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