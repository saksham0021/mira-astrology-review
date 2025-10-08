#!/usr/bin/env python3
"""
Direct database test to simulate the exact sessions endpoint logic
"""

import sqlite3
import json

def simulate_sessions_endpoint():
    """Simulate the exact logic from the sessions endpoint"""
    print("SIMULATING SESSIONS ENDPOINT LOGIC")
    print("=" * 50)
    
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    # Check total sessions
    cursor.execute("SELECT COUNT(*) FROM sessions")
    total_sessions = cursor.fetchone()[0]
    print(f"Total sessions in database: {total_sessions}")
    
    # Execute the exact same query as the endpoint
    cursor.execute('''
        SELECT s.session_id, s.user_id, s.age, s.gender, s.rating,
               s.manglik_dosha, s.pitra_dosha, s.original_marking,
               CASE WHEN r.id IS NOT NULL THEN 1 ELSE 0 END as reviewed,
               r.status as review_status, r.astrologer_name, r.overall_status, r.comments
        FROM sessions s
        LEFT JOIN reviews r ON s.session_id = r.session_id
        ORDER BY 
            CASE 
                WHEN r.status = 'completed' THEN 2
                WHEN r.status = 'in_progress' THEN 1
                ELSE 0
            END ASC, s.id ASC
    ''')
    
    rows = cursor.fetchall()
    print(f"SQL query returned: {len(rows)} rows")
    
    # Simulate the processing loop
    sessions = []
    processed_count = 0
    error_count = 0
    
    for row in rows:
        try:
            processed_count += 1
            
            # Check for None values that might cause issues
            if row[0] is None:  # session_id
                print(f"WARNING: Row {processed_count} has NULL session_id")
                continue
            
            # Determine marking status
            marking = str(row[7]).lower() if row[7] else ''
            if marking in ['marked', 'correct', 'good', 'yes', '1']:
                marking_status = 'marked'
            elif marking in ['not marked', 'incorrect', 'wrong', 'bad', 'no', '0']:
                marking_status = 'not_marked'
            elif marking in ['cant judge', "can't judge", 'unclear', 'unknown', 'maybe']:
                marking_status = 'cant_judge'
            else:
                marking_status = 'cant_judge'
            
            # Create existing_review object
            existing_review = None
            if row[8]:  # If reviewed
                existing_review = {
                    'overall_status': row[11],
                    'comments': row[12],
                    'astrologer_name': row[10]
                }
            
            session_data = {
                'session_id': row[0],
                'user_id': row[1],
                'age': row[2],
                'gender': row[3],
                'rating': row[4],
                'manglik_dosha': row[5],
                'pitra_dosha': row[6],
                'original_marking': row[7],
                'marking_status': marking_status,
                'reviewed': bool(row[8]),
                'review_status': row[9] or 'not_started',
                'astrologer_name': row[10],
                'existing_review': existing_review
            }
            
            sessions.append(session_data)
            
        except Exception as e:
            error_count += 1
            print(f"ERROR processing row {processed_count}: {e}")
            print(f"Row data: {row}")
    
    conn.close()
    
    print(f"Processed {processed_count} rows")
    print(f"Errors: {error_count}")
    print(f"Successfully created {len(sessions)} session objects")
    
    # Check for duplicates
    session_ids = [s['session_id'] for s in sessions]
    unique_ids = set(session_ids)
    print(f"Unique session IDs: {len(unique_ids)}")
    
    if len(session_ids) != len(unique_ids):
        from collections import Counter
        duplicates = [item for item, count in Counter(session_ids).items() if count > 1]
        print(f"Duplicate session IDs: {duplicates[:10]}")
    
    # Show some sample data
    print(f"First 3 session IDs: {session_ids[:3]}")
    print(f"Last 3 session IDs: {session_ids[-3:]}")
    
    return sessions

if __name__ == '__main__':
    sessions = simulate_sessions_endpoint()
    print(f"\nFINAL RESULT: {len(sessions)} sessions would be returned by the endpoint")
