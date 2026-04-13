"""
Vercel Serverless Function Entry Point
WSGI-compatible handler for Flask application
"""
import os
import sys

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
APP_DIR = os.path.join(PROJECT_ROOT, 'app')

# Add app directory to Python path
sys.path.insert(0, APP_DIR)
sys.path.insert(0, PROJECT_ROOT)

# Monkey patch sqlite3 before importing app
import sqlite3
_original_connect = sqlite3.connect

def _patched_connect(path, *args, **kwargs):
    """Redirect database to /tmp for serverless environment"""
    if path == 'database.db' or path.endswith('database.db'):
        return _original_connect('/tmp/database.db', *args, **kwargs)
    return _original_connect(path, *args, **kwargs)

sqlite3.connect = _patched_connect

# Create /tmp directories for uploads
os.makedirs('/tmp/uploads', exist_ok=True)

# Initialize database schema
DB_PATH = '/tmp/database.db'
SCHEMA_PATH = os.path.join(APP_DIR, 'schema.sql')

def init_database():
    """Initialize SQLite database in /tmp if not exists"""
    if not os.path.exists(DB_PATH) and os.path.exists(SCHEMA_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()
            print(f"[INIT] Database created at {DB_PATH}")
        except Exception as e:
            print(f"[ERROR] Database init failed: {e}")

init_database()

# Import Flask application
from app import app as flask_app

# Vercel WSGI handler
class VercelHandler:
    """WSGI-compatible handler for Vercel serverless functions"""
    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        return self.application(environ, start_response)

# Create the handler instance
app = VercelHandler(flask_app)
