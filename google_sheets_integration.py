"""
Google Sheets Integration for Mira Astrology Review System
Syncs data between local database and Google Sheets
"""

import gspread
from google.oauth2.service_account import Credentials
import sqlite3
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

class GoogleSheetsSync:
    def __init__(self, credentials_file: str, spreadsheet_url: str):
        """
        Initialize Google Sheets connection
        
        Args:
            credentials_file: Path to Google service account credentials JSON
            spreadsheet_url: URL of the Google Sheet
        """
        self.spreadsheet_url = spreadsheet_url
        self.credentials_file = credentials_file
        self.client = None
        self.sheet = None
        
    def connect(self):
        """Establish connection to Google Sheets"""
        try:
            # Define the scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Authenticate
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=scope
            )
            
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_url(self.spreadsheet_url).sheet1
            
            print(f"SUCCESS: Connected to Google Sheet: {self.sheet.title}")
            return True
            
        except Exception as e:
            print(f"ERROR: Error connecting to Google Sheets: {e}")
            return False
    
    def get_all_data(self) -> List[Dict[str, Any]]:
        """
        Fetch all data from Google Sheet
        
        Returns:
            List of dictionaries with session data
        """
        try:
            # Get all records as list of dictionaries
            records = self.sheet.get_all_records()
            print(f"SUCCESS: Fetched {len(records)} records from Google Sheet")
            return records
            
        except Exception as e:
            print(f"ERROR: Error fetching data: {e}")
            return []
    
    def sync_to_database(self, db_path: str = 'mira_analysis.db'):
        """
        Sync Google Sheet data to local SQLite database
        
        Args:
            db_path: Path to SQLite database
        """
        records = self.get_all_data()
        if not records:
            print("No records to sync")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        synced_count = 0
        updated_count = 0
        
        for record in records:
            session_id = record.get('session_id') or record.get('Session ID')
            
            if not session_id:
                print(f"WARNING: Skipping record because session_id is missing: {record}")
                continue
            
            # Check if session exists
            cursor.execute('SELECT id FROM sessions WHERE session_id = ?', (session_id,))
            existing = cursor.fetchone()
            
            # Prepare data
            data = {
                'session_id': session_id,
                'user_id': record.get('user_id') or record.get('User ID'),
                'age': record.get('age') or record.get('Age'),
                'gender': record.get('gender') or record.get('Gender'),
                'rating': record.get('rating') or record.get('Rating'),
                'summary': record.get('summary') or record.get('Summary'),
                'kundli': record.get('kundli') or record.get('Kundli'),
                'major_dasha': record.get('major_dasha') or record.get('Major Dasha'),
                'minor_dasha': record.get('minor_dasha') or record.get('Minor Dasha'),
                'sub_minor_dasha': record.get('sub_minor_dasha') or record.get('Sub Minor Dasha'),
                'manglik_dosha': record.get('manglik_dosha') or record.get('Manglik Dosha'),
                'pitra_dosha': record.get('pitra_dosha') or record.get('Pitra Dosha'),
                'chat': record.get('chat') or record.get('Chat'),
                'saurabh_analysis': record.get('saurabh_analysis') or record.get('Saurabh Analysis'),
                'original_marking': record.get('original_marking') or record.get('Original Marking'),
            }
            
            if existing:
                # Update existing record
                cursor.execute('''
                    UPDATE sessions SET
                        user_id = ?, age = ?, gender = ?, rating = ?,
                        summary = ?, kundli = ?, major_dasha = ?, minor_dasha = ?,
                        sub_minor_dasha = ?, manglik_dosha = ?, pitra_dosha = ?,
                        chat = ?, saurabh_analysis = ?, original_marking = ?
                    WHERE session_id = ?
                ''', (
                    data['user_id'], data['age'], data['gender'], data['rating'],
                    data['summary'], data['kundli'], data['major_dasha'], data['minor_dasha'],
                    data['sub_minor_dasha'], data['manglik_dosha'], data['pitra_dosha'],
                    data['chat'], data['saurabh_analysis'], data['original_marking'],
                    session_id
                ))
                updated_count += 1
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO sessions (
                        session_id, user_id, age, gender, rating, summary, kundli,
                        major_dasha, minor_dasha, sub_minor_dasha, manglik_dosha,
                        pitra_dosha, chat, saurabh_analysis, original_marking
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['session_id'], data['user_id'], data['age'], data['gender'],
                    data['rating'], data['summary'], data['kundli'], data['major_dasha'],
                    data['minor_dasha'], data['sub_minor_dasha'], data['manglik_dosha'],
                    data['pitra_dosha'], data['chat'], data['saurabh_analysis'],
                    data['original_marking']
                ))
                synced_count += 1
        
        # Get all session IDs from the sheet
        sheet_session_ids = set()
        for record in records:
            session_id = record.get('session_id') or record.get('Session ID')
            if session_id:
                sheet_session_ids.add(str(session_id))
        
        # Delete sessions that are no longer in the sheet
        cursor.execute('SELECT session_id FROM sessions')
        db_session_ids = [row[0] for row in cursor.fetchall()]
        
        deleted_count = 0
        for db_session_id in db_session_ids:
            if str(db_session_id) not in sheet_session_ids:
                # Delete from reviews first (foreign key constraint)
                cursor.execute('DELETE FROM reviews WHERE session_id = ?', (db_session_id,))
                # Delete from sessions
                cursor.execute('DELETE FROM sessions WHERE session_id = ?', (db_session_id,))
                deleted_count += 1
                print(f"INFO: Deleted session {db_session_id} (no longer in sheet)")
        
        # Sync review deletions - remove reviews that are no longer marked in Google Sheets
        sheet_reviewed_sessions = set()
        for record in records:
            session_id = record.get('session_id') or record.get('Session ID')
            # Check if this session has review data in the sheet
            review_status = record.get('Review Status') or record.get('review_status')
            overall_status = record.get('Overall Status') or record.get('overall_status')
            comments = record.get('Comments') or record.get('comments')
            reviewed_by = record.get('Reviewed By') or record.get('reviewed_by')
            
            # If any review field has meaningful data, consider it reviewed
            has_review_data = False
            debug_info = []
            
            if review_status and review_status.strip() and review_status.strip().lower() not in ['', 'not_started']:
                has_review_data = True
                debug_info.append(f"review_status='{review_status}'")
            
            if overall_status and overall_status.strip() and overall_status.strip().lower() not in ['', 'none']:
                has_review_data = True
                debug_info.append(f"overall_status='{overall_status}'")
            
            if comments and comments.strip():
                has_review_data = True
                debug_info.append(f"comments='{comments[:50]}...'")
            
            if reviewed_by and reviewed_by.strip() and reviewed_by.strip().lower() not in ['', 'none', 'system reviewer']:
                has_review_data = True
                debug_info.append(f"reviewed_by='{reviewed_by}'")
            
            if has_review_data and session_id:
                sheet_reviewed_sessions.add(str(session_id))
                print(f"DEBUG: Found review data for session {session_id}: {', '.join(debug_info)}")
        
        # Get all reviewed sessions from local database
        cursor.execute('SELECT session_id FROM reviews')
        db_reviewed_sessions = [str(row[0]) for row in cursor.fetchall()]
        
        # Delete reviews that are no longer marked in the sheet
        review_deleted_count = 0
        for db_session_id in db_reviewed_sessions:
            if db_session_id not in sheet_reviewed_sessions:
                cursor.execute('DELETE FROM reviews WHERE session_id = ?', (db_session_id,))
                review_deleted_count += 1
                print(f"INFO: Deleted review for session {db_session_id} (no longer marked in sheet)")
        
        conn.commit()
        conn.close()
        
        print(f"SUCCESS: Sync complete: {synced_count} new, {updated_count} updated, {deleted_count} deleted, {review_deleted_count} reviews removed")
    
    def update_review_in_sheet(self, session_id: str, review_data: Dict[str, Any]):
        """
        Update review data back to Google Sheet
        
        Args:
            session_id: Session ID to update
            review_data: Dictionary with review information
        """
        try:
            # Find the row with this session_id
            cell = self.sheet.find(session_id)
            
            if not cell:
                print(f"ERROR: Session {session_id} not found in sheet")
                return False
            
            row_num = cell.row
            
            # Get header row to find column indices
            headers = self.sheet.row_values(1)
            
            # Map review data to columns
            updates = []
            
            # Add review columns if they don't exist
            review_columns = {
                'Review Status': review_data.get('status', ''),
                'Overall Status': review_data.get('overall_status', ''),
                'Comments': review_data.get('comments', ''),
                'Reviewed By': review_data.get('astrologer_name', 'System Reviewer'),
                'Review Date': review_data.get('updated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            }
            
            for col_name, value in review_columns.items():
                if col_name in headers:
                    col_idx = headers.index(col_name) + 1
                    updates.append({
                        'range': f'{gspread.utils.rowcol_to_a1(row_num, col_idx)}',
                        'values': [[value]]
                    })
                else:
                    # Add new column
                    new_col_idx = len(headers) + 1
                    self.sheet.update_cell(1, new_col_idx, col_name)
                    self.sheet.update_cell(row_num, new_col_idx, value)
                    headers.append(col_name)
            
            # Batch update
            if updates:
                self.sheet.batch_update(updates)
            
            print(f"SUCCESS: Updated review for session {session_id} in Google Sheet")
            return True
            
        except Exception as e:
            print(f"ERROR: Error updating sheet: {e}")
            return False
    
    def sync_all_reviews_to_sheet(self, db_path: str = 'mira_analysis.db'):
        """
        Sync all reviews from database to Google Sheet
        
        Args:
            db_path: Path to SQLite database
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all reviews
        cursor.execute('''
            SELECT session_id, astrologer_name, overall_status, comments, status, updated_at
            FROM reviews
        ''')
        
        reviews = cursor.fetchall()
        conn.close()
        
        synced_count = 0
        
        for review in reviews:
            session_id, astrologer_name, overall_status, comments, status, updated_at = review
            
            review_data = {
                'astrologer_name': astrologer_name,
                'overall_status': overall_status,
                'comments': comments,
                'status': status,
                'updated_at': updated_at
            }
            
            if self.update_review_in_sheet(session_id, review_data):
                synced_count += 1
        
        print(f"SUCCESS: Synced {synced_count} reviews to Google Sheet")
    
    def sync_sessions_to_sheet(self, db_path: str = 'mira_analysis.db'):
        """
        Sync all session data from database to Google Sheet
        
        Args:
            db_path: Path to SQLite database
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all sessions with their review status
        cursor.execute('''
            SELECT s.session_id, s.user_id, s.age, s.gender, s.rating, s.summary,
                   s.kundli, s.major_dasha, s.minor_dasha, s.sub_minor_dasha,
                   s.manglik_dosha, s.pitra_dosha, s.chat, s.saurabh_analysis,
                   s.original_marking,
                   r.astrologer_name, r.overall_status, r.comments, r.status as review_status,
                   r.updated_at as review_date
            FROM sessions s
            LEFT JOIN reviews r ON s.session_id = r.session_id
            ORDER BY s.id
        ''')
        
        sessions = cursor.fetchall()
        conn.close()
        
        if not sessions:
            print("No sessions to sync")
            return
        
        try:
            # Get current headers
            headers = self.sheet.row_values(1)
            
            # Define expected headers
            expected_headers = [
                'Session ID', 'User ID', 'Age', 'Gender', 'Rating', 'Summary',
                'Kundli', 'Major Dasha', 'Minor Dasha', 'Sub Minor Dasha',
                'Manglik Dosha', 'Pitra Dosha', 'Chat', 'Saurabh Analysis',
                'Original Marking', 'Reviewed By', 'Overall Status', 'Comments',
                'Review Status', 'Review Date'
            ]
            
            # Check if headers need to be updated
            if headers != expected_headers:
                self.sheet.update('A1', [expected_headers])

            # Prepare all data for batch update
            all_data = []
            for session in sessions:
                row_data = [str(item) if item is not None else '' for item in session]
                all_data.append(row_data)
            
            # Update all data starting from the second row
            if all_data:
                self.sheet.update('A2', all_data)
            
            print(f"SUCCESS: Synced {len(sessions)} sessions to Google Sheet")
            
        except Exception as e:
            print(f"ERROR: Error syncing sessions to sheet: {e}")
    
    def sync_single_session_to_sheet(self, session_id: str, db_path: str = 'mira_analysis.db'):
        """
        Sync a single session with its review data to Google Sheets
        More efficient for real-time updates - ALWAYS updates existing entry, never creates duplicates
        
        Args:
            session_id: Session ID to sync
            db_path: Path to SQLite database
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get session with review data
        cursor.execute('''
            SELECT s.session_id, s.user_id, s.age, s.gender, s.rating, s.summary,
                   s.kundli, s.major_dasha, s.minor_dasha, s.sub_minor_dasha,
                   s.manglik_dosha, s.pitra_dosha, s.chat, s.saurabh_analysis,
                   s.original_marking,
                   r.astrologer_name, r.overall_status, r.comments, r.status as review_status,
                   r.updated_at as review_date
            FROM sessions s
            LEFT JOIN reviews r ON s.session_id = r.session_id
            WHERE s.session_id = ?
        ''', (session_id,))
        
        session = cursor.fetchone()
        conn.close()
        
        if not session:
            print(f"ERROR: Session {session_id} not found in database")
            return False
        
        try:
            print(f"DEBUG: Looking for session {session_id} in Google Sheet...")
            
            # Get all data from the sheet to find the exact row
            all_records = self.sheet.get_all_records()
            row_num = None
            
            # Search through all records to find matching session_id
            for idx, record in enumerate(all_records):
                # Check multiple possible column names for session_id
                record_session_id = (record.get('Session ID') or 
                                   record.get('session_id') or 
                                   record.get('SessionID') or 
                                   record.get('session id'))
                
                if str(record_session_id) == str(session_id):
                    row_num = idx + 2  # +2 because: +1 for 1-indexing, +1 for header row
                    print(f"DEBUG: Found session {session_id} at row {row_num}")
                    break
            
            if row_num:
                # Update existing row - NEVER create duplicate
                row_data = [str(item) if item is not None else '' for item in session]
                
                # Get the number of columns to determine the range
                headers = self.sheet.row_values(1)
                num_cols = len(headers)
                
                # Ensure we have enough data for all columns
                while len(row_data) < num_cols:
                    row_data.append('')
                
                # Update the entire row with proper range
                end_col = chr(ord('A') + num_cols - 1)  # Convert to column letter
                range_name = f'A{row_num}:{end_col}{row_num}'
                
                print(f"DEBUG: Updating range {range_name} with {len(row_data)} values")
                
                self.sheet.update(range_name, [row_data[:num_cols]])
                print(f"SUCCESS: Updated existing session {session_id} at row {row_num} in Google Sheet")
                
            else:
                # Session not found in sheet - this should not happen for reviews
                # But if it does, we need to add it
                print(f"WARNING: Session {session_id} not found in Google Sheet - this should not happen for existing sessions")
                
                # Get headers to ensure proper column alignment
                headers = self.sheet.row_values(1)
                expected_headers = [
                    'Session ID', 'User ID', 'Age', 'Gender', 'Rating', 'Summary',
                    'Kundli', 'Major Dasha', 'Minor Dasha', 'Sub Minor Dasha',
                    'Manglik Dosha', 'Pitra Dosha', 'Chat', 'Saurabh Analysis',
                    'Original Marking', 'Reviewed By', 'Overall Status', 'Comments',
                    'Review Status', 'Review Date'
                ]
                
                # Update headers if needed
                if headers != expected_headers:
                    self.sheet.update('A1', [expected_headers])
                
                # Add the session as new row
                row_data = [str(item) if item is not None else '' for item in session]
                self.sheet.append_row(row_data)
                print(f"WARNING: Added session {session_id} as new row (should have existed)")
            
            return True
                
        except Exception as e:
            print(f"ERROR: Error syncing single session to sheet: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_review_columns_only(self, session_id: str, review_data: Dict[str, Any]):
        """
        Update ONLY the review columns for a session - more efficient for real-time review updates
        This prevents creating duplicate entries by only updating review-specific columns
        
        Args:
            session_id: Session ID to update
            review_data: Dictionary with review information
        """
        try:
            print(f"DEBUG: Updating review columns for session {session_id}...")
            
            # Get all data from the sheet to find the exact row
            all_records = self.sheet.get_all_records()
            row_num = None
            
            # Search through all records to find matching session_id
            for idx, record in enumerate(all_records):
                # Check multiple possible column names for session_id
                record_session_id = (record.get('Session ID') or 
                                   record.get('session_id') or 
                                   record.get('SessionID') or 
                                   record.get('session id'))
                
                if str(record_session_id) == str(session_id):
                    row_num = idx + 2  # +2 because: +1 for 1-indexing, +1 for header row
                    print(f"DEBUG: Found session {session_id} at row {row_num}")
                    break
            
            if not row_num:
                print(f"ERROR: Session {session_id} not found in Google Sheet")
                return False
            
            # Get headers to find review column positions
            headers = self.sheet.row_values(1)
            
            # Map review data to specific columns
            review_columns = {
                'Reviewed By': review_data.get('astrologer_name', 'System Reviewer'),
                'Overall Status': review_data.get('overall_status', ''),
                'Comments': review_data.get('comments', ''),
                'Review Status': review_data.get('status', 'completed'),
                'Review Date': review_data.get('updated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            }
            
            # Update only the review columns
            updates = []
            for col_name, value in review_columns.items():
                if col_name in headers:
                    col_idx = headers.index(col_name) + 1  # 1-indexed
                    col_letter = chr(ord('A') + col_idx - 1)
                    cell_range = f'{col_letter}{row_num}'
                    updates.append({
                        'range': cell_range,
                        'values': [[str(value) if value is not None else '']]
                    })
                    print(f"DEBUG: Will update {col_name} at {cell_range} with '{value}'")
                else:
                    print(f"WARNING: Column '{col_name}' not found in headers")
            
            # Batch update all review columns
            if updates:
                self.sheet.batch_update(updates)
                print(f"SUCCESS: Updated {len(updates)} review columns for session {session_id}")
                return True
            else:
                print(f"WARNING: No review columns to update for session {session_id}")
                return False
                
        except Exception as e:
            print(f"ERROR: Error updating review columns: {e}")
            import traceback
            traceback.print_exc()
            return False


def setup_google_sheets_integration():
    """
    Setup instructions for Google Sheets integration
    """
    print("""
    ╔════════════════════════════════════════════════════════════════════════╗
    ║         Google Sheets Integration Setup Instructions                   ║
    ╚════════════════════════════════════════════════════════════════════════╝
    
    📋 STEP 1: Create Google Service Account
    ─────────────────────────────────────────────────────────────────────────
    1. Go to: https://console.cloud.google.com/
    2. Create a new project or select existing
    3. Enable Google Sheets API and Google Drive API
    4. Create Service Account:
       - IAM & Admin → Service Accounts → Create Service Account
       - Name: "Mira Astrology Sync"
       - Grant role: "Editor"
    5. Create Key:
       - Click on service account → Keys → Add Key → JSON
       - Download the JSON file
       - Save as: credentials.json in project folder
    
    📊 STEP 2: Share Google Sheet
    ─────────────────────────────────────────────────────────────────────────
    1. Open your Google Sheet
    2. Click "Share" button
    3. Add the service account email (from credentials.json)
       Example: mira-astrology-sync@project-id.iam.gserviceaccount.com
    4. Give "Editor" permissions
    
    📦 STEP 3: Install Required Packages
    ─────────────────────────────────────────────────────────────────────────
    pip install gspread google-auth google-auth-oauthlib google-auth-httplib2
    
    🔄 STEP 4: Usage
    ─────────────────────────────────────────────────────────────────────────
    # Initialize sync
    sync = GoogleSheetsSync(
        credentials_file='credentials.json',
        spreadsheet_url='YOUR_SHEET_URL'
    )
    
    # Connect
    sync.connect()
    
    # Sync from Google Sheet to Database
    sync.sync_to_database()
    
    # Update review back to Google Sheet
    sync.update_review_in_sheet(session_id, review_data)
    
    # Sync all reviews to Google Sheet
    sync.sync_all_reviews_to_sheet()
    
    ╚════════════════════════════════════════════════════════════════════════╝
    """)


if __name__ == '__main__':
    setup_google_sheets_integration()
