import sqlite3

def add_overall_status_column():
    conn = sqlite3.connect('mira_analysis.db')
    cursor = conn.cursor()
    
    try:
        # Check if overall_status column exists
        cursor.execute("PRAGMA table_info(reviews)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'overall_status' not in columns:
            cursor.execute('ALTER TABLE reviews ADD COLUMN overall_status TEXT')
            print("Added overall_status column to reviews table")
        else:
            print("overall_status column already exists")
        
        conn.commit()
        print("Database updated successfully")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_overall_status_column()
