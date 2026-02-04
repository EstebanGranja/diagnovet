from google.cloud import storage
from app.config import Config
import uuid

class StorageService:
    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(Config.BUCKET_NAME)
    
    def upload_image(self, image_bytes: bytes, filename: str) -> str:
        """
        Sube una imagen a Cloud Storage
        
        Args:
            image_bytes: Contenido de la imagen en bytes
            filename: Nombre del archivo
            
        Returns:
            URL pública de la imagen
        """
        # Generar nombre único
        unique_filename = f"images/{uuid.uuid4()}_{filename}"
        
        # Detectar content type basado en los primeros bytes
        content_type = 'image/png'
        if image_bytes[:2] == b'\xff\xd8':
            content_type = 'image/jpeg'
        elif image_bytes[:4] == b'\x89PNG':
            content_type = 'image/png'
        
        # Crear blob y subir
        blob = self.bucket.blob(unique_filename)
        blob.upload_from_string(image_bytes, content_type=content_type)
        
        # Con uniform bucket-level access, los objetos son públicos 
        # automáticamente si el bucket tiene el permiso allUsers
        # No necesitamos make_public()
        
        return blob.public_url