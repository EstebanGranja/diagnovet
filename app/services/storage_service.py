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
        
        # Crear blob y subir
        blob = self.bucket.blob(unique_filename)
        blob.upload_from_string(image_bytes, content_type='image/png')
        
        # Hacer público
        blob.make_public()
        
        return blob.public_url