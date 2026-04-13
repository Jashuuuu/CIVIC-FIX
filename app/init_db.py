import sqlite3
import os

def init_db():
    db_path = 'database.db'
    
    if os.path.exists(db_path):
        os.remove(db_path)
        
    connection = sqlite3.connect(db_path)
    
    with open('schema.sql') as f:
        connection.executescript(f.read())
        
    connection.commit()
    connection.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
