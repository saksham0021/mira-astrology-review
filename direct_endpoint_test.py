#!/usr/bin/env python3
"""
Direct test of the sessions endpoint with detailed logging
"""

import requests
import time

def test_endpoint_directly():
    """Test the endpoint and check logs"""
    print("TESTING SESSIONS ENDPOINT DIRECTLY")
    print("=" * 50)
    
    print("\n1. Making request to /sessions endpoint...")
    
    try:
        # Make request with explicit headers
        headers = {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        response = requests.get("http://localhost:8081/sessions", headers=headers)
        
        print(f"   Response status: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            sessions = response.json()
            print(f"   Sessions received: {len(sessions)}")
            
            # Check for test session
            test_sessions = [s for s in sessions if 'TEST_' in s.get('session_id', '')]
            print(f"   Test sessions: {len(test_sessions)}")
            
            # Check for duplicates
            session_ids = [s['session_id'] for s in sessions]
            unique_ids = set(session_ids)
            print(f"   Unique session IDs: {len(unique_ids)}")
            
            if len(session_ids) != len(unique_ids):
                from collections import Counter
                duplicates = [item for item, count in Counter(session_ids).items() if count > 1]
                print(f"   Duplicate session IDs: {duplicates}")
            
            # Show first and last few sessions
            print(f"   First 3 sessions: {[s['session_id'] for s in sessions[:3]]}")
            print(f"   Last 3 sessions: {[s['session_id'] for s in sessions[-3:]]}")
            
        else:
            print(f"   Error response: {response.text}")
            
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print("\n2. Summary:")
    print("   The endpoint is returning 447 sessions but we expect more")
    print("   The debug logs should show what's happening in Flask")
    print("   Check the Flask terminal for debug output")

if __name__ == '__main__':
    test_endpoint_directly()
