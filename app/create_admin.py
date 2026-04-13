import sqlite3
from werkzeug.security import generate_password_hash
import getpass
import sys

def create_admin():
    print("=== Create CivicFix Admin Account ===")
    
    # Prompt for admin details
    name = input("Enter admin name: ").strip()
    email = input("Enter admin email: ").strip()
    
    if not name or not email:
        print("Error: Name and email are required.")
        sys.exit(1)
        
    password = getpass.getpass("Enter admin password: ")
    confirm_password = getpass.getpass("Confirm password: ")
    
    if password != confirm_password:
        print("Error: Passwords do not match.")
        sys.exit(1)
        
    if len(password) < 6:
        print("Error: Password must be at least 6 characters long.")
        sys.exit(1)
        
    # Open DB and insert admin
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Check if email exists
        user = cursor.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user:
            print("Error: This email is already registered.")
            sys.exit(1)
            
        hashed_password = generate_password_hash(password)
        
        cursor.execute('INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)',
                       (name, email, hashed_password, 1))
        
        conn.commit()
        conn.close()
        
        print(f"\nSuccess! Admin account created for {email}.")
        print("You can now log in at http://127.0.0.1:5000/login")
        
    except Exception as e:
        print(f"Database error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    create_admin()
