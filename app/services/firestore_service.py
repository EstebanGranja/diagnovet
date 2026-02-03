from google.cloud import firestore
from datetime import datetime
import uuid
import re

class FirestoreService:
    def __init__(self):
        self.db = firestore.Client()
        self.collection = self.db.collection('ultrasound_reports')
    
    def _generate_report_id(self, report_data: dict) -> str:
        """
        Genera un ID legible basado en el nombre del dueño y timestamp.
        Formato: owner_YYYYMMDD_HHMMSS o uuid si no hay nombre
        """
        # Intentar obtener nombre del dueño
        owner_name = None
        if 'owner' in report_data and report_data['owner']:
            owner_name = report_data['owner'].get('name')
        
        # Timestamp actual
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        if owner_name:
            # Limpiar nombre: solo letras y números, lowercase
            clean_name = re.sub(r'[^a-zA-Z0-9]', '', owner_name).lower()
            # Limitar a 20 caracteres
            clean_name = clean_name[:20] if clean_name else None
        else:
            clean_name = None
        
        if clean_name:
            return f"{clean_name}_{timestamp}"
        else:
            # Fallback a UUID corto si no hay nombre
            return f"report_{timestamp}_{str(uuid.uuid4())[:8]}"
    
    def save_report(self, report_data: dict) -> str:
        """
        Guarda un reporte en Firestore
        
        Args:
            report_data: Diccionario con los datos del reporte
            
        Returns:
            ID del documento guardado
        """
        # Generar ID legible
        report_id = self._generate_report_id(report_data)
        
        # Agregar metadata
        report_data['id'] = report_id
        report_data['created_at'] = datetime.utcnow()
        
        # Guardar en Firestore
        self.collection.document(report_id).set(report_data)
        
        return report_id
    
    def get_report(self, report_id: str) -> dict:
        """
        Recupera un reporte por ID
        
        Args:
            report_id: ID del reporte
            
        Returns:
            Diccionario con los datos del reporte o None
        """
        doc = self.collection.document(report_id).get()
        
        if doc.exists:
            return doc.to_dict()
        return None