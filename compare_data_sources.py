#!/usr/bin/env python3
"""
Compare data between Google Sheets, Database, and API
"""

import sqlite3
import requests
from google_sheets_integration import GoogleSheetsSync

def compare_data_sources():
    """Compare all data sources"""
    print("COMPARING DATA SOURCES")
    print("=" * 60)
    
    # 1. Check Google Sheets
    print("\n1. GOOGLE SHEETS:")
    try:
        sync = GoogleSheetsSync(
            credentials_file='credentials.json/credentials.json',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/1fd3YNixXYHcvyDgq2TcOHG6PGlzryt5T4nT2ObXUScM/edit?usp=sharing'
        )
        
        if sync.connect():
            sheets_data = sync.get_all_data()
            print(f"   Total records: {len(sheets_data)}")
            
            # Check for test entries
            test_entries = [d for d in sheets_data if 'TEST_' in str(d.get('Session ID', ''))]
            print(f"   Test entries: {len(test_entries)}")
            
            if test_entries:
                te = test_entries[0]
                print(f"   Test entry: {te.get('Session ID')} - {te.get('User ID')}")
            
            # Check last few entries
            print(f"   Last 3 session IDs: {[d.get('Session ID') for d in sheets_data[-3:]]}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 2. Check Database
    print("\n2. DATABASE:")
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM sessions")
    db_total = cursor.fetchone()[0]
    print(f"   Total sessions: {db_total}")
    
    cursor.execute("SELECT session_id FROM sessions WHERE session_id LIKE 'TEST_%'")
    db_test = cursor.fetchall()
    print(f"   Test sessions: {len(db_test)}")
    if db_test:
        print(f"   Test session ID: {db_test[0][0]}")
    
    cursor.execute("SELECT session_id FROM sessions ORDER BY id DESC LIMIT 3")
    db_recent = cursor.fetchall()
    print(f"   Last 3 session IDs: {[r[0] for r in db_recent]}")
    
    conn.close()
    
    # 3. Check API
    print("\n3. WEBSITE API:")
    try:
        response = requests.get("http://localhost:8081/sessions")
        if response.status_code == 200:
            api_sessions = response.json()
            print(f"   Total sessions: {len(api_sessions)}")
            
            api_test = [s for s in api_sessions if 'TEST_' in s.get('session_id', '')]
            print(f"   Test sessions: {len(api_test)}")
            
            print(f"   Last 3 session IDs: {[s['session_id'] for s in api_sessions[-3:]]}")
        else:
            print(f"   ERROR: Status {response.status_code}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 4. Analysis
    print("\n4. ANALYSIS:")
    print(f"   Google Sheets: {len(sheets_data) if 'sheets_data' in locals() else 'Unknown'} records")
    print(f"   Database: {db_total} sessions")
    print(f"   API: {len(api_sessions) if 'api_sessions' in locals() else 'Unknown'} sessions")
    
    if 'sheets_data' in locals() and len(sheets_data) != db_total:
        print(f"   MISMATCH: Google Sheets has {len(sheets_data)} but database has {db_total}")
        print("   This explains why the sync shows different numbers")
    
    if db_test and not api_test:
        print("   ISSUE: Test session in database but not in API")
        print("   The database sync worked, but API filtering is removing it")

if __name__ == '__main__':
    compare_data_sources()
