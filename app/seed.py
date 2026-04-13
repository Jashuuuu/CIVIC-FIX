import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

def seed_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Clear existing data (if any from previous seeds, though init_db clears it all)
    cursor.execute('DELETE FROM users')
    cursor.execute('DELETE FROM complaints')

    # Add Admin User
    admin_pass = generate_password_hash('admin123')
    cursor.execute('INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)',
                   ('System Admin', 'admin@civicfix.com', admin_pass, 1))
    
    # Add Standard Users
    user_pass = generate_password_hash('user123')
    cursor.execute('INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)',
                   ('John Doe', 'john@example.com', user_pass, 0))
    cursor.execute('INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)',
                   ('Jane Smith', 'jane@example.com', user_pass, 0))
    
    conn.commit()
    
    user_ids = [row[0] for row in cursor.execute('SELECT id FROM users WHERE is_admin = 0').fetchall()]

    # Add sample complaints
    complaints = [
        {
            'issue_type': 'Garbage',
            'description': 'Overflowing dumpster behind the public library. It has been there for days and smells terrible.',
            'location': 'Central Library Alley',
            'status': 'Pending',
            'rejection_reason': None,
            'days_ago': 1,
            'upvotes': 15
        },
        {
            'issue_type': 'Roads',
            'description': 'Massive pothole in the middle lane causing cars to swerve dangerously.',
            'location': 'Highway 99, near exit 4',
            'status': 'Accepted',
            'rejection_reason': None,
            'days_ago': 3,
            'upvotes': 42
        },
        {
            'issue_type': 'Streetlight',
            'description': 'Streetlights are out for the entire block making it unsafe to walk at night.',
            'location': 'Oak Street & 5th Avenue',
            'status': 'Rejected',
            'rejection_reason': 'This block is outside our city jurisdiction.',
            'days_ago': 7,
            'upvotes': 28
        },
        {
            'issue_type': 'Water',
            'description': 'A fire hydrant is slowly leaking water into the street gutter.',
            'location': 'Main St and Lincoln Blvd',
            'status': 'Pending',
            'rejection_reason': None,
            'days_ago': 0,
            'upvotes': 5
        },
        {
            'issue_type': 'Roads',
            'description': 'Faded crosswalk lines at the school intersection.',
            'location': 'West Elementary School',
            'status': 'Accepted',
            'rejection_reason': None,
            'days_ago': 2,
            'upvotes': 19
        }
    ]
    
    for c in complaints:
        date_reported = (datetime.now() - timedelta(days=c['days_ago'])).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO complaints (user_id, issue_type, description, location, status, rejection_reason, date, upvotes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (random.choice(user_ids), c['issue_type'], c['description'], c['location'], c['status'], c['rejection_reason'], date_reported, c['upvotes']))

    conn.commit()
    conn.close()
    
    print("Database seeded completely!")
    print("Admin: admin@civicfix.com / admin123")
    print("User: john@example.com / user123")

if __name__ == '__main__':
    seed_db()
