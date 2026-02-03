import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PROJECT_ID = os.getenv("PROJECT_ID")
    LOCATION = os.getenv("LOCATION", "us")
    PROCESSOR_ID = os.getenv("PROCESSOR_ID")
    BUCKET_NAME = os.getenv("BUCKET_NAME")
    
    @classmethod
    def validate(cls):
        """Validar que todas las variables estén configuradas"""
        missing = []
        if not cls.PROJECT_ID:
            missing.append("PROJECT_ID")
        if not cls.PROCESSOR_ID:
            missing.append("PROCESSOR_ID")
        if not cls.BUCKET_NAME:
            missing.append("BUCKET_NAME")
        
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")
        
        return True

# Validar al importar
Config.validate()