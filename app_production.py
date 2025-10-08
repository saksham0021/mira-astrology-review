"""
Production-Ready Mira Astrology Review System
Security-hardened version for public deployment
"""
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import sqlite3
import os
import json
import logging
import secrets
from datetime import datetime
from werkzeug.utils import secure_filename
from logging.handlers import RotatingFileHandler

# Import custom modules
from astro_parser import AstroDataParser, parse_session_astrological_data
from kundli_chart_generator import generate_kundli_image, kundli_to_bytes, generate_kundli_from_parsed_data
from production_config import config

# Google Sheets integration (optional)
GOOGLE_SHEETS_ENABLED = False
try:
    from google_sheets_integration import GoogleSheetsSync
    GOOGLE_SHEETS_ENABLED = True
    print("INFO: Google Sheets integration available")
except ImportError:
    print("INFO: Google Sheets integration not available. Install gspread and google-auth to enable.")

def create_app(config_name='production'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Security headers
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if app.config.get('PREFERRED_URL_SCHEME') == 'https':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    # Logging configuration
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            app.config.get('LOG_FILE', 'logs/mira_app.log'),
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.info('Mira Astrology Review System startup')
    
    # Create necessary directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('exports', exist_ok=True)
    
    # Initialize Google Sheets if available
    google_sync = None
    if GOOGLE_SHEETS_ENABLED and app.config.get('GOOGLE_SHEETS_URL'):
        try:
            google_sync = GoogleSheetsSync(
                credentials_file=app.config['GOOGLE_CREDENTIALS_FILE'],
                spreadsheet_url=app.config['GOOGLE_SHEETS_URL']
            )
            if google_sync.connect():
                app.logger.info("Google Sheets integration enabled")
            else:
                google_sync = None
        except Exception as e:
            app.logger.warning(f"Could not initialize Google Sheets: {e}")
            google_sync = None
    
    def allowed_file(filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    def init_db():
        """Initialize database with proper schema"""
        conn = sqlite3.connect('mira_analysis.db')
        cursor = conn.cursor()
        
        # Create sessions table with all required columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                user_id TEXT,
                age TEXT,
                gender TEXT,
                rating INTEGER,
                summary TEXT,
                kundli TEXT,
                kundli_json TEXT,
                major_dasha TEXT,
                minor_dasha TEXT,
                sub_minor_dasha TEXT,
                dasha_json TEXT,
                manglik_dosha TEXT,
                pitra_dosha TEXT,
                dosha_json TEXT,
                chat TEXT,
                marking TEXT,
                saurabh_analysis TEXT,
                parsed_astro TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create reviews table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                astrologer_name TEXT NOT NULL,
                overall_status TEXT,
                comments TEXT,
                review_status TEXT DEFAULT 'not_started',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        app.logger.info("Database initialized successfully")
    
    # Routes
    @app.route('/')
    def index():
        """Main page with cache control"""
        response = render_template('index.html')
        from flask import make_response
        resp = make_response(response)
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp
    
    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring"""
        try:
            # Test database connection
            conn = sqlite3.connect('mira_analysis.db')
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            conn.close()
            
            return jsonify({
                'status': 'healthy',
                'version': 'v13.0',
                'timestamp': datetime.now().isoformat(),
                'database': 'connected'
            }), 200
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/upload', methods=['POST'])
    def upload_file():
        """Upload and process Excel file with enhanced security"""
        try:
            if 'file' not in request.files:
                app.logger.warning("Upload attempt without file")
                return jsonify({'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not allowed_file(file.filename):
                app.logger.warning(f"Invalid file type attempted: {file.filename}")
                return jsonify({'error': 'Invalid file type. Only Excel files (.xlsx, .xls) are allowed.'}), 400
            
            # Secure filename
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process Excel file
            df = pd.read_excel(filepath)
            app.logger.info(f"Processing file with {len(df)} rows")
            
            # Database operations
            conn = sqlite3.connect('mira_analysis.db')
            cursor = conn.cursor()
            
            processed_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Insert session data
                    cursor.execute('''
                        INSERT OR REPLACE INTO sessions 
                        (session_id, user_id, age, gender, rating, summary, kundli, kundli_json,
                         major_dasha, minor_dasha, sub_minor_dasha, dasha_json,
                         manglik_dosha, pitra_dosha, dosha_json, chat, marking, saurabh_analysis,
                         parsed_astro, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        str(row.get('session_id', '')),
                        str(row.get('user_id', '')),
                        str(row.get('age', '')),
                        str(row.get('gender', '')),
                        int(row.get('rating', 0)) if pd.notna(row.get('rating')) else None,
                        str(row.get('summary', '')),
                        str(row.get('Kundli', '')),
                        str(row.get('kundli_json', '')),
                        str(row.get('major_dasha', '')),
                        str(row.get('minor_dasha', '')),
                        str(row.get('sub_minor_dasha', '')),
                        str(row.get('dasha_json', '')),
                        str(row.get('manglik_dosha', '')),
                        str(row.get('pitra_dosha', '')),
                        str(row.get('dosha_json', '')),
                        str(row.get('Chat', '')),
                        str(row.get('Marking', '')),
                        str(row.get('Saurabh Analysis', '')),
                        json.dumps(parse_session_astrological_data(row))
                    ))
                    processed_count += 1
                except Exception as e:
                    app.logger.error(f"Error processing row {index}: {e}")
                    error_count += 1
            
            conn.commit()
            conn.close()
            
            # Clean up uploaded file
            os.remove(filepath)
            
            app.logger.info(f"Upload completed: {processed_count} processed, {error_count} errors")
            
            return jsonify({
                'success': True,
                'message': f'Successfully processed {processed_count} sessions',
                'processed': processed_count,
                'errors': error_count
            })
            
        except Exception as e:
            app.logger.error(f"Upload error: {e}")
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    # Add all other routes from original app.py here...
    # (For brevity, including just the critical ones above)
    
    # Initialize database
    with app.app_context():
        init_db()
    
    return app

# Create application instance
app = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    host = os.environ.get('HOST', '127.0.0.1')  # Secure default
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.logger.info(f"Starting Mira Astrology Review System on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
