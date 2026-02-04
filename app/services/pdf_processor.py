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
        print(f"URLs de imágenes guardadas: {len(image_urls)} - {image_urls}")
        
        # 4. Guardar en Firestore
        print("Guardando en Firestore...")
        print(f"Datos a guardar - images: {report_data.get('images')}")
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
    
    def _is_medical_image(self, img_bytes: bytes, width: int, height: int) -> tuple:
        """
        Determina si una imagen es probablemente una radiografía/ecografía médica.
        
        Criterios:
        - Tamaño mínimo: 200x200 pixels (los logos son más pequeños)
        - Tamaño archivo: > 20KB (las radiografías son pesadas)
        - Aspect ratio: entre 0.3 y 3.0 (no muy alargadas como banners/firmas)
        - Preferencia por imágenes en escala de grises
        
        Returns:
            (es_valida: bool, razon: str)
        """
        # Filtro 1: Tamaño mínimo en pixels
        MIN_WIDTH = 200
        MIN_HEIGHT = 200
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            return False, f"muy pequeña ({width}x{height} < {MIN_WIDTH}x{MIN_HEIGHT})"
        
        # Filtro 2: Tamaño mínimo en bytes (20KB)
        MIN_BYTES = 20000
        if len(img_bytes) < MIN_BYTES:
            return False, f"archivo pequeño ({len(img_bytes)//1000}KB < 20KB)"
        
        # Filtro 3: Aspect ratio razonable
        aspect_ratio = width / height
        if aspect_ratio < 0.3 or aspect_ratio > 3.0:
            return False, f"aspect ratio inusual ({aspect_ratio:.2f})"
        
        # Filtro 4: Verificar si es mayoritariamente escala de grises (radiografías lo son)
        try:
            img = Image.open(BytesIO(img_bytes))
            
            # Si es muy pequeña después de decodificar, rechazar
            if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
                return False, f"dimensiones reales pequeñas ({img.width}x{img.height})"
            
            # Convertir a RGB si es necesario para analizar
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Tomar una muestra del centro de la imagen para analizar
            # Esto evita bordes/marcos que podrían ser de otro color
            center_x, center_y = img.width // 2, img.height // 2
            sample_size = min(100, img.width // 4, img.height // 4)
            
            if sample_size > 10:
                # Recortar región central
                left = center_x - sample_size
                top = center_y - sample_size
                right = center_x + sample_size
                bottom = center_y + sample_size
                center_crop = img.crop((left, top, right, bottom))
                
                # Analizar si es escala de grises
                # En escala de grises, R ≈ G ≈ B para cada pixel
                pixels = list(center_crop.getdata())
                if len(pixels) > 0 and len(pixels[0]) >= 3:
                    grayscale_pixels = 0
                    total_pixels = len(pixels)
                    
                    for pixel in pixels[:500]:  # Muestra de 500 pixels
                        r, g, b = pixel[:3]
                        # Tolerancia de 30 para considerar "gris"
                        if abs(r - g) < 30 and abs(g - b) < 30 and abs(r - b) < 30:
                            grayscale_pixels += 1
                    
                    grayscale_ratio = grayscale_pixels / min(500, total_pixels)
                    
                    # Si más del 70% es escala de grises, probablemente es radiografía
                    if grayscale_ratio > 0.7:
                        return True, f"radiografía detectada ({grayscale_ratio:.0%} gris)"
                    
                    # Si es muy colorida, probablemente es logo
                    if grayscale_ratio < 0.3:
                        return False, f"imagen colorida ({grayscale_ratio:.0%} gris) - probable logo"
            
            # Si llegamos aquí, la imagen pasó los filtros básicos
            # pero no pudimos determinar si es escala de grises
            # La aceptamos si es lo suficientemente grande
            if width >= 300 and height >= 300 and len(img_bytes) >= 50000:
                return True, "imagen grande aceptada"
            
            return False, "no cumple criterios de radiografía"
            
        except Exception as e:
            # Si no podemos analizar la imagen, usar solo criterios de tamaño
            # Ser más estrictos: solo aceptar si es muy grande
            if width >= 400 and height >= 400 and len(img_bytes) >= 100000:
                return True, "imagen muy grande (sin análisis)"
            return False, f"error analizando: {e}"
    
    def _extract_and_upload_images(self, pdf_content: bytes, filename: str) -> list:
        """
        Extrae imágenes del PDF usando múltiples métodos y las sube a Cloud Storage.
        
        Returns:
            Lista de URLs públicas de las imágenes
        """
        image_urls = []
        
        # Intentar con PyMuPDF primero (más robusto)
        try:
            import fitz
            image_urls = self._extract_with_pymupdf(pdf_content, filename)
            if image_urls:
                return image_urls
        except ImportError:
            print("  PyMuPDF no disponible, usando método alternativo")
        except Exception as e:
            print(f"  Error con PyMuPDF: {type(e).__name__}: {e}")
        
        # Fallback: pypdf
        try:
            image_urls = self._extract_with_pypdf(pdf_content, filename)
            if image_urls:
                return image_urls
        except Exception as e:
            print(f"  Error con pypdf: {type(e).__name__}: {e}")
        
        # Último recurso: extraer XObjects directamente
        try:
            image_urls = self._extract_xobjects_direct(pdf_content, filename)
        except Exception as e:
            print(f"  Error extrayendo XObjects: {type(e).__name__}: {e}")
        
        return image_urls
    
    def _extract_with_pymupdf(self, pdf_content: bytes, filename: str) -> list:
        """Extrae imágenes usando PyMuPDF (fitz)"""
        import fitz
        image_urls = []
        
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        image_count = 0
        rejected_count = 0
        
        print(f"  [PyMuPDF] PDF tiene {len(pdf_document)} páginas")
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            image_list = page.get_images(full=True)
            print(f"    Página {page_num + 1}: {len(image_list)} imágenes encontradas")
            
            for img_index, img_info in enumerate(image_list):
                try:
                    xref = img_info[0]
                    base_image = pdf_document.extract_image(xref)
                    
                    if base_image:
                        img_bytes = base_image["image"]
                        img_ext = base_image.get("ext", "png")
                        width = base_image.get("width", 0)
                        height = base_image.get("height", 0)
                        
                        # Aplicar filtro inteligente para detectar radiografías
                        is_valid, reason = self._is_medical_image(img_bytes, width, height)
                        
                        if is_valid:
                            clean_filename = filename.replace('.pdf', '').replace(' ', '_').replace('/', '_')
                            img_filename = f"{clean_filename}_p{page_num + 1}_img{img_index + 1}.{img_ext}"
                            
                            url = self.storage.upload_image(img_bytes, img_filename)
                            image_urls.append(url)
                            image_count += 1
                            print(f"      ✓ {img_filename} ({width}x{height}) - {reason}")
                        else:
                            rejected_count += 1
                            print(f"      ⊘ Ignorada ({width}x{height}): {reason}")
                            
                except Exception as e:
                    print(f"      ✗ Error imagen {img_index}: {e}")
                    continue
        
        pdf_document.close()
        print(f"  [PyMuPDF] Total: {image_count} radiografías guardadas, {rejected_count} imágenes filtradas")
        return image_urls
    
    def _extract_with_pypdf(self, pdf_content: bytes, filename: str) -> list:
        """Extrae imágenes usando pypdf"""
        image_urls = []
        
        pdf_reader = PdfReader(BytesIO(pdf_content))
        image_count = 0
        rejected_count = 0
        
        print(f"  [pypdf] PDF tiene {len(pdf_reader.pages)} páginas")
        
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                if hasattr(page, 'images'):
                    images_list = list(page.images)
                    print(f"    Página {page_num + 1}: {len(images_list)} imágenes encontradas")
                    
                    for img_index, image in enumerate(images_list):
                        try:
                            img_bytes = image.data
                            
                            if img_bytes and len(img_bytes) > 1000:
                                # Detectar formato y dimensiones
                                try:
                                    img = Image.open(BytesIO(img_bytes))
                                    width, height = img.width, img.height
                                except:
                                    width, height = 0, 0
                                
                                # Aplicar filtro inteligente
                                is_valid, reason = self._is_medical_image(img_bytes, width, height)
                                
                                if is_valid:
                                    ext = 'png'
                                    if img_bytes[:2] == b'\xff\xd8':
                                        ext = 'jpg'
                                    
                                    clean_filename = filename.replace('.pdf', '').replace(' ', '_').replace('/', '_')
                                    img_filename = f"{clean_filename}_p{page_num + 1}_img{img_index + 1}.{ext}"
                                    
                                    url = self.storage.upload_image(img_bytes, img_filename)
                                    image_urls.append(url)
                                    image_count += 1
                                    print(f"      ✓ {img_filename} ({width}x{height}) - {reason}")
                                else:
                                    rejected_count += 1
                                    print(f"      ⊘ Ignorada: {reason}")
                                    
                        except Exception as e:
                            print(f"      ✗ Error imagen {img_index}: {e}")
                            continue
            except Exception as e:
                print(f"    ✗ Error página {page_num + 1}: {e}")
                continue
        
        print(f"  [pypdf] Total: {image_count} radiografías guardadas, {rejected_count} filtradas")
        return image_urls
    
    def _extract_xobjects_direct(self, pdf_content: bytes, filename: str) -> list:
        """Extrae imágenes directamente de XObjects del PDF"""
        image_urls = []
        
        pdf_reader = PdfReader(BytesIO(pdf_content))
        image_count = 0
        rejected_count = 0
        
        print(f"  [XObjects] PDF tiene {len(pdf_reader.pages)} páginas")
        
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                if '/Resources' not in page:
                    continue
                    
                resources = page['/Resources']
                if '/XObject' not in resources:
                    continue
                
                x_objects = resources['/XObject'].get_object()
                print(f"    Página {page_num + 1}: {len(x_objects)} XObjects encontrados")
                
                for obj_name, obj_ref in x_objects.items():
                    try:
                        obj = obj_ref.get_object()
                        
                        # Verificar que sea imagen
                        if obj.get('/Subtype') != '/Image':
                            continue
                        
                        width = int(obj.get('/Width', 0))
                        height = int(obj.get('/Height', 0))
                        
                        # Obtener datos de la imagen
                        img_filter = obj.get('/Filter')
                        if isinstance(img_filter, list):
                            img_filter = img_filter[0] if img_filter else None
                        
                        # Intentar obtener datos
                        try:
                            data = obj.get_data()
                        except Exception:
                            data = obj._data if hasattr(obj, '_data') else None
                        
                        if not data or len(data) < 1000:
                            continue
                        
                        img_bytes = None
                        ext = 'png'
                        
                        # JPEG (DCTDecode)
                        if img_filter == '/DCTDecode':
                            img_bytes = data
                            ext = 'jpg'
                        
                        # JPEG 2000 (JPXDecode)
                        elif img_filter == '/JPXDecode':
                            img_bytes = data
                            ext = 'jp2'
                        
                        # FlateDecode - necesita reconstruir imagen
                        elif img_filter == '/FlateDecode':
                            try:
                                color_space = obj.get('/ColorSpace')
                                bits = int(obj.get('/BitsPerComponent', 8))
                                
                                if color_space == '/DeviceRGB':
                                    mode = 'RGB'
                                elif color_space == '/DeviceGray':
                                    mode = 'L'
                                elif color_space == '/DeviceCMYK':
                                    mode = 'CMYK'
                                else:
                                    mode = 'RGB'
                                
                                image = Image.frombytes(mode, (width, height), data)
                                img_buffer = BytesIO()
                                image.save(img_buffer, format='PNG')
                                img_bytes = img_buffer.getvalue()
                                ext = 'png'
                            except Exception as img_err:
                                print(f"        Error reconstruyendo imagen: {img_err}")
                                continue
                        
                        # Sin filtro - raw data
                        elif img_filter is None:
                            try:
                                color_space = obj.get('/ColorSpace', '/DeviceRGB')
                                if color_space == '/DeviceRGB':
                                    mode = 'RGB'
                                elif color_space == '/DeviceGray':
                                    mode = 'L'
                                else:
                                    mode = 'RGB'
                                
                                image = Image.frombytes(mode, (width, height), data)
                                img_buffer = BytesIO()
                                image.save(img_buffer, format='PNG')
                                img_bytes = img_buffer.getvalue()
                                ext = 'png'
                            except Exception:
                                continue
                        
                        if img_bytes:
                            # Aplicar filtro inteligente
                            is_valid, reason = self._is_medical_image(img_bytes, width, height)
                            
                            if is_valid:
                                clean_filename = filename.replace('.pdf', '').replace(' ', '_').replace('/', '_')
                                clean_obj_name = str(obj_name).replace('/', '_')
                                img_filename = f"{clean_filename}_p{page_num + 1}_{clean_obj_name}.{ext}"
                                
                                url = self.storage.upload_image(img_bytes, img_filename)
                                image_urls.append(url)
                                image_count += 1
                                print(f"      ✓ {img_filename} ({width}x{height}) - {reason}")
                            else:
                                rejected_count += 1
                                print(f"      ⊘ Ignorada ({width}x{height}): {reason}")
                            
                    except Exception as e:
                        print(f"      ✗ Error XObject {obj_name}: {e}")
                        continue
                        
            except Exception as e:
                print(f"    ✗ Error página {page_num + 1}: {e}")
                continue
        
        print(f"  [XObjects] Total: {image_count} radiografías guardadas, {rejected_count} filtradas")
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