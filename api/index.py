import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

# Monkey patch sqlite3 to use /tmp for database in serverless environment
import sqlite3
_original_connect = sqlite3.connect

def _patched_connect(path, *args, **kwargs):
    if path == 'database.db':
        path = '/tmp/database.db'
    return _original_connect(path, *args, **kwargs)

sqlite3.connect = _patched_connect

# Now import the Flask app
from app import app as flask_app

# Initialize database if needed
def init_db():
    db_path = '/tmp/database.db'
    if not os.path.exists(db_path):
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'schema.sql')
        if os.path.exists(schema_path):
            conn = sqlite3.connect(db_path)
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()
            print("Database initialized at /tmp/database.db")

init_db()

# Vercel serverless handler
class Handler:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        return self.app(environ, start_response)

app = Handler(flask_app)
