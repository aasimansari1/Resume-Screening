import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-resume-screener-secret-2024')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'resumes')
    EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), 'exports')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}
    RESULTS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'results.json')

    # Admin credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

    # Mail settings (optional)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', '')

    # Scoring weights
    WEIGHT_TFIDF = 0.35
    WEIGHT_SKILLS = 0.35
    WEIGHT_EXPERIENCE = 0.20
    WEIGHT_EDUCATION = 0.10
