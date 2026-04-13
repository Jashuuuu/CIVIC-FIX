import sqlite3

def migrate():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Add ai_analysis to complaints
    try:
        cursor.execute("ALTER TABLE complaints ADD COLUMN ai_analysis TEXT")
        print("Added ai_analysis to complaints.")
    except sqlite3.OperationalError:
        print("ai_analysis column already exists.")
        
    conn.commit()
    conn.close()
    print("AI Migration finished safely.")

if __name__ == '__main__':
    migrate()
