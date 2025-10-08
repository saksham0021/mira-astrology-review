"""
Vercel Entry Point for Mira Astrology Review System
"""
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set production environment
os.environ['FLASK_ENV'] = 'production'

# Import the main app
from app import app, init_db

# Configure app for production
app.config['DEBUG'] = False
app.config['TESTING'] = False

# Initialize database on startup
try:
    init_db()
    print("Database initialized successfully")
except Exception as e:
    print(f"Database initialization error: {e}")

# This is the WSGI application that Vercel will use
application = app

# For Vercel compatibility - this is the main handler
def handler(environ, start_response):
    return app(environ, start_response)
