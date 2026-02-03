from google.cloud import firestore
from datetime import datetime
import uuid

class FirestoreService:
    def __init__(self):
        self.db = firestore.Client()
        self.collection = self.db.collection('ultrasound_reports')
    
    def save_report(self, report_data: dict) -> str:
        """
        Guarda un reporte en Firestore
        
        Args:
            report_data: Diccionario con los datos del reporte
            
        Returns:
            ID del documento guardado
        """
        # Generar ID único
        report_id = str(uuid.uuid4())
        
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