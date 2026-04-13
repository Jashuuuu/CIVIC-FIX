#!/usr/bin/env python3
"""
Script to update admin credentials
"""

import sqlite3
from werkzeug.security import generate_password_hash

def update_admin():
    """Update admin account with new credentials"""
    
    # New admin credentials
    ADMIN_EMAIL = "civic.managementsrm@gmail.com"
    ADMIN_PASSWORD = "Admin@2026"
    ADMIN_NAME = "Civic Management"
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check if admin exists
    admin = cursor.execute('SELECT * FROM users WHERE is_admin = 1').fetchone()
    
    if admin:
        # Update existing admin
        admin_id = admin[0]
        hashed_password = generate_password_hash(ADMIN_PASSWORD)
        
        cursor.execute('''
            UPDATE users 
            SET name = ?, email = ?, password = ?
            WHERE id = ?
        ''', (ADMIN_NAME, ADMIN_EMAIL, hashed_password, admin_id))
        
        print(f"✅ Admin account updated successfully!")
    else:
        # Create new admin if none exists
        hashed_password = generate_password_hash(ADMIN_PASSWORD)
        
        cursor.execute('''
            INSERT INTO users (name, email, password, is_admin)
            VALUES (?, ?, ?, ?)
        ''', (ADMIN_NAME, ADMIN_EMAIL, hashed_password, 1))
        
        print(f"✅ Admin account created successfully!")
    
    conn.commit()
    conn.close()
    
    print(f"\n🔐 New Admin Credentials:")
    print(f"   Email: {ADMIN_EMAIL}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print(f"\n📝 Note: Keep these credentials secure!")

if __name__ == "__main__":
    update_admin()
