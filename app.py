from flask import Flask, render_template, request, jsonify, send_file, make_response
import pandas as pd
import sqlite3
import json
import os
import time
from datetime import datetime
from google_sheets_integration import GoogleSheetsSync
from kundli_chart_generator import generate_kundli_image, kundli_to_bytes, generate_kundli_from_parsed_data

# Google Sheets integration (optional) - Now enabled for real-time sync
try:
    from google_sheets_integration import GoogleSheetsSync
    GOOGLE_SHEETS_ENABLED = True
    print("INFO: Google Sheets integration enabled for real-time data sync.")
except ImportError:
    print("WARNING: Google Sheets integration not available. Install gspread and google-auth to enable.")
    GOOGLE_SHEETS_ENABLED = False

app = Flask(__name__)

# Configure Flask app
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Cache for Google Sheets data to improve performance
sheets_cache = {
    'data': None,
    'last_updated': 0,
    'cache_duration': 300  # 5 minutes cache
}

def get_cached_sheets_data():
    """Get Google Sheets data with caching to improve performance"""
    current_time = time.time()
    
    # Check if cache is valid
    if (sheets_cache['data'] is not None and 
        current_time - sheets_cache['last_updated'] < sheets_cache['cache_duration']):
        print("DEBUG: Using cached Google Sheets data")
        return sheets_cache['data']
    
    # Cache is expired or empty, fetch new data
    if google_sync:
        try:
            print("DEBUG: Fetching fresh Google Sheets data")
            data = google_sync.get_all_data()
            sheets_cache['data'] = data
            sheets_cache['last_updated'] = current_time
            print(f"DEBUG: Cached {len(data)} records from Google Sheets")
            return data
        except Exception as e:
            print(f"ERROR: Failed to fetch Google Sheets data: {e}")
            # Return cached data if available, even if expired
            return sheets_cache['data'] if sheets_cache['data'] else []
    
    return []

# Google Sheets configuration
app.config['GOOGLE_SHEETS_URL'] = 'https://docs.google.com/spreadsheets/d/1fd3YNixXYHcvyDgq2TcOHG6PGlzryt5T4nT2ObXUScM/edit?usp=sharing'
app.config['GOOGLE_CREDENTIALS_FILE'] = 'credentials.json/credentials.json'

# Initialize Google Sheets sync if available
google_sync = None
if GOOGLE_SHEETS_ENABLED and os.path.exists(app.config['GOOGLE_CREDENTIALS_FILE']):
    try:
        google_sync = GoogleSheetsSync(
            credentials_file=app.config['GOOGLE_CREDENTIALS_FILE'],
            spreadsheet_url=app.config['GOOGLE_SHEETS_URL']
        )
        if google_sync.connect():
            print("SUCCESS: Google Sheets integration enabled")
        else:
            google_sync = None
    except Exception as e:
        print(f"WARNING: Could not initialize Google Sheets: {e}")
        google_sync = None

# Create necessary directories
os.makedirs('exports', exist_ok=True)


def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE,
            user_id TEXT,
            age INTEGER,
            gender TEXT,
            rating REAL,
            summary TEXT,
            kundli TEXT,
            kundli_json TEXT,
            major_dasha TEXT,
            minor_dasha TEXT,
            sub_minor_dasha TEXT,
            manglik_dosha TEXT,
            pitra_dosha TEXT,
            dasha_json TEXT,
            chat TEXT,
            saurabh_analysis TEXT,
            original_marking TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create reviews table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            astrologer_name TEXT,
            overall_status TEXT,
            comments TEXT,
            status TEXT DEFAULT 'not_started',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
    ''')
    
    # Add indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions (session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_id ON sessions (id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reviews_session_id ON reviews (session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews (status)')
    print("DEBUG: Database indexes created for better performance")
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Main page"""
    response = render_template('index.html')
    # Force no-cache headers
    from flask import make_response
    resp = make_response(response)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/diagnostic')
def diagnostic():
    """Diagnostic page for mobile testing"""
    from flask import make_response
    response = render_template('diagnostic.html')
    resp = make_response(response)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/test-layout')
def test_layout():
    """Test page for user info layout"""
    from flask import make_response
    response = render_template('test_layout.html')
    resp = make_response(response)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/test-cache')
def test_cache():
    """Test page for cache fix"""
    with open('test_cache_fix.html', 'r', encoding='utf-8') as f:
        content = f.read()
    resp = make_response(content)
    resp.headers['Content-Type'] = 'text/html'
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@app.route('/sessions')
def get_sessions():
    """Get all sessions with review status - no pagination"""
    print("DEBUG: /sessions endpoint called")
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    # First check total sessions in database
    cursor.execute("SELECT COUNT(*) FROM sessions")
    total_sessions = cursor.fetchone()[0]
    print(f"DEBUG: Total sessions in database: {total_sessions}")
    
    # Get ALL sessions - no pagination
    cursor.execute('''
        SELECT s.session_id, s.user_id, s.age, s.gender, s.rating,
               s.manglik_dosha, s.pitra_dosha, s.original_marking
        FROM sessions s
        ORDER BY s.id ASC
    ''')
    
    rows = cursor.fetchall()
    print(f"DEBUG: SQL query returned {len(rows)} rows")
    
    # Get review data from Google Sheets (cached for performance)
    google_reviews = {}
    records = get_cached_sheets_data()
    if records:
        try:
            for record in records:
                session_id = record.get('session_id') or record.get('Session ID')
                if session_id:
                    review_status = record.get('Review Status') or record.get('review_status')
                    overall_status = record.get('Overall Status') or record.get('overall_status')
                    comments = record.get('Comments') or record.get('comments')
                    reviewed_by = record.get('Reviewed By') or record.get('reviewed_by')
                    
                    # Check if this session has review data
                    has_review = (review_status and review_status.strip() and review_status.strip().lower() not in ['', 'not_started', 'none'])
                    
                    if has_review:
                        google_reviews[str(session_id)] = {
                            'review_status': review_status or 'completed',
                            'overall_status': overall_status,
                            'comments': comments,
                            'astrologer_name': reviewed_by or 'System Reviewer'
                        }
        except Exception as e:
            print(f"ERROR: Could not process cached Google Sheets data: {e}")
    
    sessions = []
    processed_count = 0
    error_count = 0
    
    # Process in smaller chunks to avoid memory/timeout issues
    chunk_size = 100
    total_chunks = (len(rows) + chunk_size - 1) // chunk_size
    print(f"DEBUG: Processing {len(rows)} rows in {total_chunks} chunks of {chunk_size}")
    
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        chunk_num = i // chunk_size + 1
        print(f"DEBUG: Processing chunk {chunk_num}/{total_chunks} (rows {i+1} to {min(i+chunk_size, len(rows))})")
        
        for row in chunk:
            try:
                processed_count += 1
                
                # Skip rows with NULL session_id
                if not row[0]:
                    print(f"DEBUG: Skipping row {processed_count} - NULL session_id")
                    continue
                
                # Determine marking status based on original_marking field
                marking = str(row[7]).lower() if row[7] else ''
                if marking in ['marked', 'correct', 'good', 'yes', '1']:
                    marking_status = 'marked'
                elif marking in ['not marked', 'incorrect', 'wrong', 'bad', 'no', '0']:
                    marking_status = 'not_marked'
                elif marking in ['cant judge', "can't judge", 'unclear', 'unknown', 'maybe']:
                    marking_status = 'cant_judge'
                else:
                    marking_status = 'cant_judge'  # Default for unclear cases
                    
                # Get review data from Google Sheets AND local database
                session_id = str(row[0])
                google_review = google_reviews.get(session_id)
                existing_review = None
                reviewed = False
                review_status = 'not_started'
                astrologer_name = None
                
                # First check local database for immediate updates
                cursor.execute('SELECT astrologer_name, overall_status, comments, status FROM reviews WHERE session_id = ?', (session_id,))
                local_review = cursor.fetchone()
                
                if local_review:
                    # Use local database data (most up-to-date)
                    reviewed = True
                    review_status = local_review[3] or 'completed'  # status
                    astrologer_name = local_review[0]  # astrologer_name
                    existing_review = {
                        'overall_status': local_review[1],  # overall_status
                        'comments': local_review[2],  # comments
                        'astrologer_name': local_review[0]  # astrologer_name
                    }
                elif google_review:
                    # Fallback to Google Sheets data
                    reviewed = True
                    review_status = google_review['review_status']
                    astrologer_name = google_review['astrologer_name']
                    existing_review = {
                        'overall_status': google_review['overall_status'],
                        'comments': google_review['comments'],
                        'astrologer_name': google_review['astrologer_name']
                    }
                
                sessions.append({
                    'session_id': row[0],
                    'user_id': row[1],
                    'age': row[2],
                    'gender': row[3],
                    'rating': row[4],
                    'manglik_dosha': row[5],
                    'pitra_dosha': row[6],
                    'original_marking': row[7],
                    'marking_status': marking_status,
                    'reviewed': reviewed,
                    'review_status': review_status,
                    'astrologer_name': astrologer_name,
                    'existing_review': existing_review
                })
                
            except Exception as e:
                error_count += 1
                print(f"DEBUG: Error processing row {processed_count}: {e}")
                print(f"DEBUG: Row data: {row}")
    
    print(f"DEBUG: Processed {processed_count} rows, {error_count} errors, {len(sessions)} sessions created")
    
    # Check for duplicates
    session_ids = [s['session_id'] for s in sessions]
    unique_ids = set(session_ids)
    print(f"DEBUG: Unique session IDs: {len(unique_ids)}")
    
    if len(session_ids) != len(unique_ids):
        from collections import Counter
        duplicates = [item for item, count in Counter(session_ids).items() if count > 1]
        print(f"DEBUG: Duplicate session IDs found: {duplicates[:5]}")
    
    conn.close()
    
    # Count sessions by review status for statistics
    unmarked_count = len([s for s in sessions if not s['reviewed']])
    marked_count = len([s for s in sessions if s['reviewed']])
    
    print(f"DEBUG: Found {unmarked_count} unmarked, {marked_count} marked sessions")
    
    # Simple sort by session_id for consistency
    sessions.sort(key=lambda x: x['session_id'])
    print(f"DEBUG: Sorted sessions by session_id")
    
    # Return all sessions - no pagination needed
    print(f"DEBUG: Returning all {len(sessions)} sessions")
    
    print(f"DEBUG: Processed {len(sessions)} sessions, returning with no-cache headers")
    
    # Create response with no-cache headers
    print(f"DEBUG: Returning {len(sessions)} sessions with no-cache headers")
    response_data = {
        'sessions': sessions,
        'total_sessions': total_sessions
    }
    response = make_response(jsonify(response_data))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    print(f"DEBUG: Headers set - Cache-Control: {response.headers.get('Cache-Control')}")
    return response

@app.route('/session/<session_id>')
def get_session(session_id):
    """Get detailed session data with parsed astrological information"""
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error': 'Session not found'}), 404
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    session_data = dict(zip(columns, row))
    
    # Parse astrological data using JSON parser
    try:
        parsed_astro_data = parse_session_astrological_data(session_data)
        session_data['parsed_astro'] = parsed_astro_data
            
    except Exception as e:
        app.logger.error(f"Error parsing astrological data for session {session_id}: {e}")
        session_data['parsed_astro'] = {}
    
    # Check if already reviewed
    cursor.execute('SELECT * FROM reviews WHERE session_id = ?', (session_id,))
    review_row = cursor.fetchone()
    
    if review_row:
        review_columns = [description[0] for description in cursor.description]
        session_data['existing_review'] = dict(zip(review_columns, review_row))
    
    conn.close()
    return jsonify(session_data)

@app.route('/parse-astro-data', methods=['POST'])
def parse_astro_data():
    """Parse astrological JSON data"""
    data = request.json
    parser = AstroDataParser()
    
    result = {}
    
    if 'kundli' in data:
        result['kundli'] = parser.parse_kundli_data(data['kundli'])
    
    if 'doshas' in data:
        result['doshas'] = parser.parse_dosha_data(data['doshas'])
    
    if 'dasha' in data:
        result['dasha'] = parser.parse_dasha_data(data['dasha'])
    
    return jsonify(result)

@app.route('/review', methods=['POST'])
def submit_review():
    """Submit astrologer's review with new button-based system"""
    data = request.json
    
    required_fields = ['session_id']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    try:
        # Check if review already exists
        cursor.execute('SELECT id FROM reviews WHERE session_id = ?', (data['session_id'],))
        existing_review = cursor.fetchone()
        
        if existing_review:
            # Update existing review
            cursor.execute('''
                UPDATE reviews SET
                astrologer_name = ?, overall_status = ?, 
                comments = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            ''', (
                data.get('astrologer_name', 'System Reviewer'),
                data.get('overall_status'),
                data.get('comments', ''),
                data.get('status', 'in_progress'),
                data['session_id']
            ))
        else:
            # Insert new review
            cursor.execute('''
                INSERT INTO reviews 
                (session_id, astrologer_name, overall_status, comments, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data['session_id'],
                data.get('astrologer_name', 'System Reviewer'),
                data.get('overall_status'),
                data.get('comments', ''),
                data.get('status', 'in_progress')
            ))
        
        conn.commit()
        
        # Invalidate cache to ensure immediate updates in session list
        sheets_cache['last_updated'] = 0
        print(f"DEBUG: Invalidated cache after review submission for session {data['session_id']}")
        
        # Sync to Google Sheets if enabled (real-time sync)
        if google_sync:
            try:
                # Use the more efficient review-only update to prevent duplicates
                review_data = {
                    'astrologer_name': data.get('astrologer_name', 'System Reviewer'),
                    'overall_status': data.get('overall_status'),
                    'comments': data.get('comments', ''),
                    'status': data.get('status', 'completed'),
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Try the review-only update first (more efficient and prevents duplicates)
                if google_sync.update_review_columns_only(data['session_id'], review_data):
                    print(f"SUCCESS: Real-time updated review columns for session {data['session_id']} in Google Sheets")
                else:
                    # Fallback to full session sync if review-only update fails
                    print(f"INFO: Review-only update failed, trying full session sync for {data['session_id']}")
                    google_sync.sync_single_session_to_sheet(data['session_id'])
                    print(f"SUCCESS: Real-time synced full session {data['session_id']} to Google Sheets")
                    
            except Exception as e:
                print(f"WARNING: Could not sync to Google Sheets: {e}")
                import traceback
                traceback.print_exc()
        
        conn.close()
        
        status_message = 'Analysis completed successfully' if data.get('status') == 'completed' else 'Changes saved successfully'
        return jsonify({'success': True, 'message': status_message})
    
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Error submitting review: {str(e)}'}), 500

@app.route('/kundli-chart/<session_id>')
def get_kundli_chart(session_id):
    """Generate and return kundli chart image for a session"""
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT kundli_json, kundli FROM sessions WHERE session_id = ?', (session_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'Session not found'}), 404
    
    kundli_json, kundli_text = row
    
    try:
        # Try JSON data first, then fallback to text
        kundli_data = kundli_json if kundli_json and kundli_json.strip() else kundli_text
        
        if not kundli_data or kundli_data.strip() == '':
            return jsonify({'error': 'No kundli data available'}), 404
        
        # Generate chart image
        img_bytes = kundli_to_bytes(kundli_data)
        
        return send_file(
            img_bytes,
            mimetype='image/png',
            as_attachment=False,
            download_name=f'kundli_chart_{session_id}.png'
        )
        
    except Exception as e:
        return jsonify({'error': f'Error generating chart: {str(e)}'}), 500

@app.route('/kundli-chart-from-parsed/<session_id>')
def get_kundli_chart_from_parsed(session_id):
    """Generate kundli chart from parsed session data"""
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error': 'Session not found'}), 404
    
    # Get column names and create session data dict
    columns = [description[0] for description in cursor.description]
    session_data = dict(zip(columns, row))
    conn.close()
    
    try:
        # Parse astrological data
        parsed_astro_data = parse_session_astrological_data(session_data)
        kundli_data = parsed_astro_data.get('kundli', {})
        
        if not kundli_data:
            return jsonify({'error': 'No kundli data available for parsing'}), 404
        
        # Generate chart from parsed data
        img = generate_kundli_from_parsed_data(kundli_data)
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return send_file(
            img_bytes,
            mimetype='image/png',
            as_attachment=False,
            download_name=f'kundli_chart_parsed_{session_id}.png'
        )
        
    except Exception as e:
        return jsonify({'error': f'Error generating chart from parsed data: {str(e)}'}), 500

@app.route('/export')
def export_data():
    """Export reviewed data to Excel"""
    conn = sqlite3.connect('mira_analysis.db')
    
    query = '''
        SELECT 
            s.session_id, s.user_id, s.age, s.gender, s.rating, s.summary,
            s.kundli, s.major_dasha, s.minor_dasha, s.sub_minor_dasha,
            s.manglik_dosha, s.pitra_dosha, s.chat, s.saurabh_analysis,
            s.original_marking,
            r.astrologer_name, r.accuracy_rating, r.kundli_correct,
            r.dasha_correct, r.dosha_correct, r.analysis_correct, r.comments,
            r.reviewed_at
        FROM sessions s
        LEFT JOIN reviews r ON s.session_id = r.session_id
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'mira_reviewed_data_{timestamp}.xlsx'
    filepath = os.path.join('exports', filename)
    
    df.to_excel(filepath, index=False)
    
    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/stats')
def get_stats():
    """Get review statistics - count reviews from Google Sheets"""
    # Check if Google Sheets is configured
    google_sheets_connected = google_sync is not None
    
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM sessions')
    total_sessions = cursor.fetchone()[0]
    
    # Force fresh data if requested
    if request.args.get('force_fresh'):
        print("DEBUG: Forcing fresh Google Sheets data for stats")
        sheets_cache['last_updated'] = 0  # Invalidate cache
    
    # Count reviewed sessions from Google Sheets data (cached for performance)
    reviewed_sessions = 0
    records = get_cached_sheets_data()
    if records:
        try:
            # Count sessions with review status data - ONLY based on 'Review Status' column
            for record in records:
                review_status = record.get('Review Status') or record.get('review_status')
                
                # Count as reviewed ONLY if Review Status column has meaningful data
                if (review_status and review_status.strip() and 
                    review_status.strip().lower() not in ['', 'not_started', 'none']):
                    reviewed_sessions += 1
                    
        except Exception as e:
            print(f"ERROR: Could not get review count from Google Sheets: {e}")
            # Fallback to local database count
            cursor.execute('SELECT COUNT(DISTINCT session_id) FROM reviews')
            reviewed_sessions = cursor.fetchone()[0]
    else:
        # Fallback to local database count if Google Sheets not available
        cursor.execute('SELECT COUNT(DISTINCT session_id) FROM reviews')
        reviewed_sessions = cursor.fetchone()[0]
    
    cursor.execute('SELECT AVG(accuracy_rating) FROM reviews')
    avg_rating = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN kundli_correct = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as kundli_accuracy,
            SUM(CASE WHEN dasha_correct = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as dasha_accuracy,
            SUM(CASE WHEN dosha_correct = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as dosha_accuracy,
            SUM(CASE WHEN analysis_correct = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as analysis_accuracy
        FROM reviews
    ''')
    
    accuracies = cursor.fetchone()
    
    conn.close()
    
    # Create response with no-cache headers
    response = make_response(jsonify({
        'total_sessions': total_sessions,
        'reviewed_sessions': reviewed_sessions,
        'pending_sessions': total_sessions - reviewed_sessions,
        'avg_rating': round(avg_rating, 2),
        'kundli_accuracy': round(accuracies[0] or 0, 2),
        'dasha_accuracy': round(accuracies[1] or 0, 2),
        'dosha_accuracy': round(accuracies[2] or 0, 2),
        'analysis_accuracy': round(accuracies[3] or 0, 2),
        'google_sheets_connected': google_sheets_connected,
        'google_sheets_url': app.config['GOOGLE_SHEETS_URL'] if google_sheets_connected else None
    }))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/api/sheets-status', methods=['GET'])
def sheets_status():
    """Check Google Sheets integration status"""
    print("DEBUG: sheets-status endpoint called")
    return jsonify({
        'enabled': google_sync is not None,
        'sheet_url': app.config['GOOGLE_SHEETS_URL'] if google_sync else None
    })

@app.route('/api/sync-from-sheets', methods=['POST'])
def sync_from_sheets():
    """Sync data FROM Google Sheets TO local database"""
    if not google_sync:
        return jsonify({'error': 'Google Sheets integration not available'}), 503
    
    try:
        # Sync from Google Sheets to database
        google_sync.sync_to_database()
        return jsonify({
            'success': True, 
            'message': 'Successfully synced data from Google Sheets to database'
        })
    except Exception as e:
        return jsonify({'error': f'Error syncing from Google Sheets: {str(e)}'}), 500

@app.route('/api/sync-to-sheets', methods=['POST'])
def sync_to_sheets():
    """Sync data FROM local database TO Google Sheets"""
    if not google_sync:
        return jsonify({'error': 'Google Sheets integration not available'}), 503
    
    try:
        # Sync sessions and reviews to Google Sheets
        google_sync.sync_sessions_to_sheet()
        return jsonify({
            'success': True, 
            'message': 'Successfully synced data from database to Google Sheets'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/force-sync', methods=['POST'])
def force_sync():
    """Force a complete bidirectional sync"""
    if not google_sync:
        return jsonify({'success': False, 'error': 'Google Sheets integration not available'})
    
    try:
        # Sync from Google Sheets to database
        google_sync.sync_to_database()
        
        # Sync from database to Google Sheets
        google_sync.sync_sessions_to_sheet()
        
        return jsonify({'success': True, 'message': 'Forced sync completed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clear-reviews-and-sync', methods=['POST'])
def clear_reviews_and_sync():
    """Clear all reviews and re-sync from Google Sheets"""
    if not google_sync:
        return jsonify({'success': False, 'error': 'Google Sheets integration not available'})
    
    try:
        # Clear all reviews from local database
        conn = sqlite3.connect('mira_analysis.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reviews')
        conn.commit()
        conn.close()
        print("INFO: Cleared all reviews from local database")
        
        # Invalidate cache to force fresh data fetch
        sheets_cache['last_updated'] = 0
        print("INFO: Invalidated Google Sheets cache")
        
        # Re-sync from Google Sheets to rebuild reviews
        google_sync.sync_to_database()
        
        return jsonify({'success': True, 'message': 'Reviews cleared and re-synced from Google Sheets'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/full-sync', methods=['POST'])
def full_sync():
    """Perform full bidirectional sync"""
    if not google_sync:
        return jsonify({'success': False, 'error': 'Google Sheets integration not available'})
    
    try:
        # First sync FROM Google Sheets TO database (get latest session data)
        google_sync.sync_to_database()
        
        # Then sync FROM database TO Google Sheets (update with reviews)
        google_sync.sync_sessions_to_sheet()
        
        return jsonify({
            'success': True, 
            'message': 'Successfully completed full bidirectional sync'
        })
    except Exception as e:
        return jsonify({'error': f'Error during full sync: {str(e)}'}), 500

@app.route('/debug/session/<session_id>')
def debug_session_status(session_id):
    """Debug endpoint to check session review status immediately"""
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    # Check local database
    cursor.execute('SELECT astrologer_name, overall_status, comments, status, updated_at FROM reviews WHERE session_id = ?', (session_id,))
    local_review = cursor.fetchone()
    
    # Check Google Sheets cache
    records = get_cached_sheets_data()
    google_review = None
    for record in records:
        record_session_id = record.get('session_id') or record.get('Session ID')
        if str(record_session_id) == str(session_id):
            google_review = {
                'review_status': record.get('Review Status'),
                'overall_status': record.get('Overall Status'),
                'comments': record.get('Comments'),
                'astrologer_name': record.get('Reviewed By')
            }
            break
    
    conn.close()
    
    return jsonify({
        'session_id': session_id,
        'local_review': {
            'astrologer_name': local_review[0] if local_review else None,
            'overall_status': local_review[1] if local_review else None,
            'comments': local_review[2] if local_review else None,
            'status': local_review[3] if local_review else None,
            'updated_at': local_review[4] if local_review else None,
        } if local_review else None,
        'google_review': google_review,
        'cache_age': time.time() - sheets_cache['last_updated'] if sheets_cache['last_updated'] else 'Never updated'
    })

@app.route('/debug/sessions-count')
def debug_sessions_count():
    """Quick debug endpoint to check session counts"""
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM sessions')
    total_sessions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM reviews')
    total_reviews = cursor.fetchone()[0]
    
    # Get a few sample sessions
    cursor.execute('SELECT session_id, user_id, age, gender FROM sessions LIMIT 5')
    sample_sessions = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'total_sessions': total_sessions,
        'total_reviews': total_reviews,
        'sample_sessions': [
            {
                'session_id': row[0],
                'user_id': row[1], 
                'age': row[2],
                'gender': row[3]
            } for row in sample_sessions
        ],
        'cache_status': {
            'last_updated': sheets_cache['last_updated'],
            'cache_age': time.time() - sheets_cache['last_updated'] if sheets_cache['last_updated'] else 'Never updated'
        }
    })

@app.route('/debug/sheets-data')
def debug_sheets_data():
    """Debug endpoint to see raw Google Sheets data"""
    records = get_cached_sheets_data()
    
    # Get first few records with review data
    review_records = []
    for record in records[:10]:  # First 10 records
        review_status = record.get('Review Status') or record.get('review_status')
        overall_status = record.get('Overall Status') or record.get('overall_status')
        comments = record.get('Comments') or record.get('comments')
        reviewed_by = record.get('Reviewed By') or record.get('reviewed_by')
        session_id = record.get('session_id') or record.get('Session ID')
        
        if any([review_status, overall_status, comments, reviewed_by]):
            review_records.append({
                'session_id': session_id,
                'review_status': review_status,
                'overall_status': overall_status,
                'comments': comments,
                'reviewed_by': reviewed_by,
                'all_keys': list(record.keys())
            })
    
    # Count reviewed sessions using same logic as stats
    reviewed_count = 0
    for record in records:
        review_status = record.get('Review Status') or record.get('review_status')
        if (review_status and review_status.strip() and 
            review_status.strip().lower() not in ['', 'not_started', 'none']):
            reviewed_count += 1
    
    return jsonify({
        'total_records': len(records),
        'reviewed_count': reviewed_count,
        'sample_review_records': review_records,
        'first_record_keys': list(records[0].keys()) if records else [],
        'cache_age': time.time() - sheets_cache['last_updated'] if sheets_cache['last_updated'] else 'Never updated'
    })

@app.route('/debug/quick-status')
def debug_quick_status():
    """Quick status check for debugging"""
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM sessions')
    total_sessions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM reviews')
    local_reviews = cursor.fetchone()[0]
    
    conn.close()
    
    # Get Google Sheets review count
    records = get_cached_sheets_data()
    sheets_reviews = 0
    if records:
        for record in records:
            review_status = record.get('Review Status') or record.get('review_status')
            if (review_status and review_status.strip() and 
                review_status.strip().lower() not in ['', 'not_started', 'none']):
                sheets_reviews += 1
    
    return jsonify({
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_sessions': total_sessions,
        'local_reviews': local_reviews,
        'sheets_reviews': sheets_reviews,
        'cache_age_seconds': time.time() - sheets_cache['last_updated'] if sheets_cache['last_updated'] else 'Never',
        'google_sync_enabled': google_sync is not None
    })

# Import required modules for parsing
import io
import re
import json as json_module

class AstroDataParser:
    """Parser for astrological data from session records"""
    
    def parse_kundli_data(self, kundli_text):
        """Parse kundli text data"""
        if not kundli_text:
            return {}
        
        # Try to parse as JSON first
        try:
            if isinstance(kundli_text, str) and (kundli_text.strip().startswith('{') or kundli_text.strip().startswith('[')):
                return json_module.loads(kundli_text)
        except:
            pass
        
        # Parse text format
        kundli_data = {}
        lines = str(kundli_text).split('\n')
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                kundli_data[key.strip()] = value.strip()
        
        return kundli_data
    
    def parse_dosha_data(self, dosha_text):
        """Parse dosha information"""
        if not dosha_text:
            return {}
        
        dosha_data = {}
        if 'manglik' in str(dosha_text).lower():
            dosha_data['manglik'] = True
        if 'pitra' in str(dosha_text).lower():
            dosha_data['pitra'] = True
        
        return dosha_data
    
    def parse_dasha_data(self, dasha_text):
        """Parse dasha information"""
        if not dasha_text:
            return {}
        
        try:
            if isinstance(dasha_text, str) and dasha_text.strip().startswith('{'):
                return json_module.loads(dasha_text)
        except:
            pass
        
        return {'raw_text': str(dasha_text)}

def parse_session_astrological_data(session_data):
    """Parse all astrological data from a session"""
    parser = AstroDataParser()
    
    result = {
        'kundli': {},
        'doshas': {},
        'dasha': {}
    }
    
    # Parse kundli data
    if session_data.get('kundli_json'):
        try:
            result['kundli'] = json_module.loads(session_data['kundli_json'])
        except:
            result['kundli'] = parser.parse_kundli_data(session_data.get('kundli'))
    elif session_data.get('kundli'):
        result['kundli'] = parser.parse_kundli_data(session_data['kundli'])
    
    # Parse dosha data
    dosha_info = {}
    if session_data.get('manglik_dosha'):
        dosha_info['manglik'] = session_data['manglik_dosha']
    if session_data.get('pitra_dosha'):
        dosha_info['pitra'] = session_data['pitra_dosha']
    result['doshas'] = dosha_info
    
    # Parse dasha data - handle JSON strings
    dasha_data = {}
    
    # Parse major dasha
    if session_data.get('major_dasha'):
        try:
            dasha_data['major'] = json.loads(session_data['major_dasha'])
        except:
            dasha_data['major'] = session_data['major_dasha']
    
    # Parse minor dasha
    if session_data.get('minor_dasha'):
        try:
            dasha_data['minor'] = json.loads(session_data['minor_dasha'])
        except:
            dasha_data['minor'] = session_data['minor_dasha']
    
    # Parse sub minor dasha
    if session_data.get('sub_minor_dasha'):
        try:
            dasha_data['sub_minor'] = json.loads(session_data['sub_minor_dasha'])
        except:
            dasha_data['sub_minor'] = session_data['sub_minor_dasha']
    
    result['dasha'] = dasha_data
    
    return result

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
