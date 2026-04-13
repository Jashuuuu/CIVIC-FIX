import sqlite3

def migrate():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Add role to users
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        print("Added role to users.")
    except sqlite3.OperationalError:
        print("role column already exists.")

    # Convert is_admin to role
    cursor.execute("UPDATE users SET role = 'admin' WHERE is_admin = 1")

    # Add assigned_to and estimated_completion_date to complaints
    try:
        cursor.execute("ALTER TABLE complaints ADD COLUMN assigned_to INTEGER")
        print("Added assigned_to to complaints.")
    except sqlite3.OperationalError:
        print("assigned_to column already exists.")

    try:
        cursor.execute("ALTER TABLE complaints ADD COLUMN estimated_completion_date TIMESTAMP")
        print("Added estimated_completion_date to complaints.")
    except sqlite3.OperationalError:
        print("estimated_completion_date column already exists.")

    conn.commit()
    conn.close()
    print("Migration finished safely.")

if __name__ == '__main__':
    migrate()
