import sqlite3

def add_reset_token_columns():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        # Add reset_token column
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
        print("Added reset_token column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("reset_token column already exists")
        else:
            print(f"Error adding reset_token column: {e}")
    
    try:
        # Add reset_token_expiry column
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token_expiry TIMESTAMP")
        print("Added reset_token_expiry column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("reset_token_expiry column already exists")
        else:
            print(f"Error adding reset_token_expiry column: {e}")
    
    conn.commit()
    conn.close()
    print("Migration completed!")

if __name__ == "__main__":
    add_reset_token_columns()
