#!/usr/bin/env python3
"""
Final verification of new entry sync
"""

import requests
import sqlite3
from google_sheets_integration import GoogleSheetsSync

def final_verification():
    """Complete verification of the sync"""
    print("FINAL VERIFICATION: New Entry Sync Test")
    print("=" * 60)
    
    # Step 1: Check database
    print("\n1. Checking Database...")
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM sessions")
    total_db = cursor.fetchone()[0]
    print(f"   Total sessions in database: {total_db}")
    
    cursor.execute("SELECT session_id, user_id, age, gender FROM sessions WHERE session_id LIKE 'TEST_%'")
    test_sessions = cursor.fetchall()
    print(f"   Test sessions in database: {len(test_sessions)}")
    if test_sessions:
        for ts in test_sessions:
            print(f"     - Session ID: {ts[0]}, User ID: {ts[1]}, Age: {ts[2]}, Gender: {ts[3]}")
    
    conn.close()
    
    # Step 2: Check Google Sheets
    print("\n2. Checking Google Sheets...")
    try:
        sync = GoogleSheetsSync(
            credentials_file='credentials.json/credentials.json',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/1fd3YNixXYHcvyDgq2TcOHG6PGlzryt5T4nT2ObXUScM/edit?usp=sharing'
        )
        
        if sync.connect():
            data = sync.get_all_data()
            print(f"   Total records in Google Sheets: {len(data)}")
            
            test_entries = [d for d in data if 'TEST_' in str(d.get('Session ID', ''))]
            print(f"   Test entries in Google Sheets: {len(test_entries)}")
            if test_entries:
                for te in test_entries:
                    print(f"     - Session ID: {te.get('Session ID')}, User ID: {te.get('User ID')}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Step 3: Check Website API
    print("\n3. Checking Website API...")
    try:
        response = requests.get("http://localhost:8081/sessions")
        if response.status_code == 200:
            sessions = response.json()
            print(f"   Total sessions from API: {len(sessions)}")
            
            test_api_sessions = [s for s in sessions if 'TEST_' in s.get('session_id', '')]
            print(f"   Test sessions from API: {len(test_api_sessions)}")
            if test_api_sessions:
                for tas in test_api_sessions:
                    print(f"     - Session ID: {tas.get('session_id')}, User ID: {tas.get('user_id')}")
            else:
                print("     WARNING: Test session not found in API response")
                print(f"     First 3 session IDs from API: {[s['session_id'] for s in sessions[:3]]}")
                print(f"     Last 3 session IDs from API: {[s['session_id'] for s in sessions[-3:]]}")
        else:
            print(f"   ERROR: API returned status {response.status_code}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Step 4: Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Database has: {total_db} sessions")
    print(f"Google Sheets has: {len(data) if 'data' in locals() else 'Unknown'} records")
    print(f"Website API returns: {len(sessions) if 'sessions' in locals() else 'Unknown'} sessions")
    
    if total_db != len(sessions):
        print("\nDISCREPANCY DETECTED!")
        print(f"Database has {total_db} sessions but API returns {len(sessions)}")
        print("This suggests a caching issue or the API is not fetching all records.")
        print("\nSOLUTION: Clear browser cache and hard refresh (Ctrl+Shift+R)")
    
    if test_sessions and not test_api_sessions:
        print("\nTest session is in database but NOT in API response")
        print("The sync FROM Google Sheets TO database worked!")
        print("But the website API needs to be refreshed.")
        print("\nPlease:")
        print("1. Clear your browser cache")
        print("2. Hard refresh the page (Ctrl+Shift+R)")
        print("3. Or close and reopen the browser")

if __name__ == '__main__':
    final_verification()
