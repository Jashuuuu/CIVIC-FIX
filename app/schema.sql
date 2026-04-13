DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS complaints;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    reset_token TEXT,
    reset_token_expiry TIMESTAMP,
    role TEXT DEFAULT 'user'
);

CREATE TABLE complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    issue_type TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    image_path TEXT,
    status TEXT DEFAULT 'Pending',
    rejection_reason TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    upvotes INTEGER DEFAULT 0,
    assigned_to INTEGER,
    estimated_completion_date TIMESTAMP,
    ai_analysis TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
