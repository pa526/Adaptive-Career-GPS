import os
from dotenv import load_dotenv

# Load variables from .env file if present
load_dotenv()

class Config:
    """Base configuration settings for Career GPS MVP application."""
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-12345")
    
    # Database configuration
    # Defaulting to a local sqlite database within the project folder
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DEFAULT_DB_PATH = os.path.join(BASE_DIR, "career_gps.db")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # API Integrations
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    @staticmethod
    def init_app(app):
        # Additional app initialization/validation can go here
        if not Config.GEMINI_API_KEY:
            app.logger.warning("WARNING: GEMINI_API_KEY is not set. AI routes ('I'm Stuck') will fail or use mock mode.")
