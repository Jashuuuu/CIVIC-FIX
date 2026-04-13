import os
import sys
import sqlite3
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Determine if running in serverless environment
IS_SERVERLESS = os.environ.get('VERCEL_ENV') is not None or '/tmp' in os.getcwd()

# Get the directory containing this file for proper path resolution
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Monkey patch sqlite3 for serverless environment (Vercel)
if IS_SERVERLESS:
    _original_connect = sqlite3.connect
    def _patched_connect(path, *args, **kwargs):
        if path == 'database.db' or path.endswith('database.db'):
            return _original_connect('/tmp/database.db', *args, **kwargs)
        return _original_connect(path, *args, **kwargs)
    sqlite3.connect = _patched_connect
    # Create tmp directories for uploads
    os.makedirs('/tmp/uploads', exist_ok=True)
    # Initialize database in /tmp
    if not os.path.exists('/tmp/database.db'):
        schema_path = os.path.join(BASE_DIR, 'schema.sql')
        if os.path.exists(schema_path):
            try:
                conn = sqlite3.connect('/tmp/database.db')
                with open(schema_path, 'r', encoding='utf-8') as f:
                    conn.executescript(f.read())
                conn.commit()
                # Create default admin account
                admin_email = 'civic.managementsrm@gmail.com'
                admin_pass = generate_password_hash('Admin@2026')
                conn.execute('INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)',
                             ('Civic Management', admin_email, admin_pass, 1))
                conn.commit()
                conn.close()
                print("[INIT] Admin account created: civic.managementsrm@gmail.com")
            except Exception as e:
                print(f"[DB INIT ERROR] {e}")

load_dotenv(override=True)  # Load environment variables from .env file, overriding any existing ones

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Flask app configuration with proper paths for serverless
template_dir = os.path.join(BASE_DIR, 'templates')
static_dir = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_civic_key_123')

# Use /tmp for uploads in serverless environment, otherwise use local static/uploads
if IS_SERVERLESS:
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
else:
    app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Flask-Mail Configuration for Gmail SMTP
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

# Get email credentials from environment variables
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

# Validate environment variables
if not MAIL_USERNAME or not MAIL_PASSWORD:
    print("CRITICAL WARNING: MAIL_USERNAME or MAIL_PASSWORD missing in .env")
    print("OTP emails will fail to send!")

app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = ('CivicFix Support', MAIL_USERNAME) if MAIL_USERNAME else None

# Initialize Flask-Mail
mail = Mail(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Ensure static uploads directory exists for local development
if not IS_SERVERLESS:
    static_uploads = os.path.join(BASE_DIR, 'static', 'uploads')
    os.makedirs(static_uploads, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """Get database connection - path is handled by monkey patch in serverless"""
    # In serverless, the path is automatically redirected to /tmp by monkey patch
    db_path = 'database.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.before_request
def require_login():
    allowed_endpoints = ['login', 'register', 'forgot_password', 'verify_otp', 'reset_password', 'static', 'api_send_otp', 'api_verify_otp', 'api_reset_password']
    if request.endpoint not in allowed_endpoints and 'user_id' not in session:
        # Don't flash in JSON APIs
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Unauthorized'}), 401
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))


@app.route('/')
@app.route('/index')
def index():
    conn = get_db_connection()
    # Fetch some recent complaints for the homepage
    complaints = conn.execute('''
        SELECT c.*, u.name as user_name 
        FROM complaints c 
        JOIN users u ON c.user_id = u.id 
        ORDER BY c.date DESC LIMIT 6
    ''').fetchall()
    conn.close()
    return render_template('home.html', complaints=complaints)

# --- Authentication Routes ---
@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        
        if user:
            flash('Email already registered.', 'error')
        else:
            # Check if this is the first user - make them admin
            existing_users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()
            is_first_user = existing_users['count'] == 0
            
            if is_first_user:
                conn.execute('INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)',
                             (name, email, generate_password_hash(password), 1))
                flash('Registration successful! First user registered as admin.', 'success')
            else:
                conn.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                             (name, email, generate_password_hash(password)))
                flash('Registration successful! Please log in.', 'success')
            
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        conn.close()
    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['is_admin'] = user['is_admin']
            flash('Logged in successfully!', 'success')
            if user['is_admin']:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=('GET', 'POST'))
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user:
            # Generate 6-digit OTP
            otp = f"{secrets.randbelow(1000000):06d}"
            expiry_time = (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')  # OTP valid for 15 mins
            
            # Store OTP in database (reusing reset_token column)
            conn = get_db_connection()
            conn.execute('UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?', 
                        (otp, expiry_time, user['id']))
            conn.commit()
            conn.close()
            
            try:
                # Send OTP email
                msg = Message(
                    subject='Your Password Reset OTP - CivicFix',
                    sender=('CivicFix Support', MAIL_USERNAME) if MAIL_USERNAME else None,
                    recipients=[email],
                    html=f"<h3>Hello {user['name']},</h3><p>Your password reset OTP is: <strong>{otp}</strong></p><p>This code will expire in 15 minutes.</p>"
                )
                mail.send(msg)
                flash('An OTP has been sent to your email address.', 'success')
            except Exception as e:
                # Handle error securely, do not expose OTP
                print(f"Error sending OTP email: {str(e)}")
                flash('Failed to send OTP. Please contact support or check mail configuration.', 'error')
            
            # Store email in session to verify OTP
            session['otp_email'] = email
            return redirect(url_for('verify_otp'))
        else:
            # Don't reveal if email exists or not for security
            flash('If that email address exists in our system, an OTP has been sent.', 'info')
            # Store email in session to maintain the same flow and prevent enumeration
            session['otp_email'] = email
            return redirect(url_for('verify_otp'))
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/verify_otp', methods=('GET', 'POST'))
def verify_otp():
    email = session.get('otp_email')
    if not email:
        flash('Please request a new password reset.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        otp = request.form['otp']
        
        conn = get_db_connection()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user = conn.execute('SELECT * FROM users WHERE email = ? AND reset_token = ? AND reset_token_expiry > ?', 
                          (email, otp, current_time)).fetchone()
        conn.close()
        
        if user:
            session['reset_auth'] = True
            flash('OTP verified successfully. You can now reset your password.', 'success')
            return redirect(url_for('reset_password'))
        else:
            flash('Invalid or expired OTP.', 'error')
    
    return render_template('verify_otp.html', email=email)

@app.route('/reset_password', methods=('GET', 'POST'))
def reset_password():
    if not session.get('reset_auth'):
        flash('Unauthorized access. Please verify your OTP first.', 'error')
        return redirect(url_for('login'))

    email = session.get('otp_email')
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('reset_password.html')
        
        # Update password and clear reset token/session
        conn = get_db_connection()
        conn.execute('UPDATE users SET password = ?, reset_token = NULL, reset_token_expiry = NULL WHERE email = ?', 
                    (generate_password_hash(password), email))
        conn.commit()
        conn.close()
        
        session.pop('reset_auth', None)
        session.pop('otp_email', None)
        
        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

# --- User Routes ---
@app.route('/report', methods=('GET', 'POST'))
def report_issue():
    if 'user_id' not in session:
        flash('Please log in to report an issue.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        issue_type = request.form['issue_type']
        description = request.form['description']
        location = request.form['location']
        
        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Make filename unique
                unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                image_path = f"uploads/{unique_filename}"
        
        conn = get_db_connection()
        
        # Smart Feature: Prevent duplicate complaints
        duplicate = conn.execute('''
            SELECT id FROM complaints 
            WHERE location = ? AND issue_type = ? AND status IN ('Pending', 'Accepted')
        ''', (location, issue_type)).fetchone()
        
        if duplicate:
            flash('A similar issue is already reported at this location. You can upvote it!', 'warning')
            conn.close()
            return redirect(url_for('index'))
        
        conn.execute('''
            INSERT INTO complaints (user_id, issue_type, description, location, image_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], issue_type, description, location, image_path))
        conn.commit()
        conn.close()
        
        flash('Issue reported successfully!', 'success')
        return redirect(url_for('my_complaints'))
        
    return render_template('report.html')

@app.route('/my_complaints')
def my_complaints():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    complaints = conn.execute('''
        SELECT * FROM complaints WHERE user_id = ? ORDER BY date DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('my_complaints.html', complaints=complaints)

@app.route('/issue/<int:id>')
def view_issue(id):
    conn = get_db_connection()
    complaint = conn.execute('''
        SELECT c.*, u.name as user_name 
        FROM complaints c 
        JOIN users u ON c.user_id = u.id 
        WHERE c.id = ?
    ''', (id,)).fetchone()
    conn.close()
    
    if not complaint:
        flash('Issue not found.', 'error')
        return redirect(url_for('index'))
        
    return render_template('issue_detail.html', complaint=complaint)

@app.route('/upvote/<int:id>', methods=['POST'])
def upvote(id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    # Simple upvote increment. For a real app, track user upvotes to prevent multiple per user.
    conn.execute('UPDATE complaints SET upvotes = upvotes + 1 WHERE id = ?', (id,))
    conn.commit()
    
    new_upvotes = conn.execute('SELECT upvotes FROM complaints WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    return jsonify({'upvotes': new_upvotes['upvotes']})

# --- Admin Routes ---
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('Unauthorized access.', 'error')
        return redirect(url_for('index'))
        
    status_filter = request.args.get('status', 'All')
    type_filter = request.args.get('type', 'All')
    
    query = 'SELECT c.*, u.name as user_name FROM complaints c JOIN users u ON c.user_id = u.id WHERE 1=1'
    params = []
    
    if status_filter != 'All':
        query += ' AND c.status = ?'
        params.append(status_filter)
    if type_filter != 'All':
        query += ' AND c.issue_type = ?'
        params.append(type_filter)
        
    query += ' ORDER BY c.date DESC'
        
    conn = get_db_connection()
    complaints = conn.execute(query, params).fetchall()
    pending_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Pending'").fetchone()[0]
    accepted_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Accepted'").fetchone()[0]
    conn.close()
    
    return render_template('admin_dashboard.html', complaints=complaints, 
                           current_status=status_filter, current_type=type_filter,
                           pending_count=pending_count, accepted_count=accepted_count)

def analyze_complaint_eta(description, issue_type):
    if not GEMINI_API_KEY:
        return "API Key not configured", None
    
    prompt = f"""
You are an intelligent civic issue management assistant.
Your task is to analyze a user complaint and generate an estimated resolution time.

Instructions:
* Read the complaint carefully.
* Identify the type of issue (e.g., water leakage, road damage, electricity issue, garbage collection, streetlight problem, etc.).
* Based on the severity and type, estimate a realistic resolution time.
* Use practical real-world assumptions (urgent issues = faster resolution, infrastructure issues = longer time).
* Keep the estimate simple and clear (e.g., "4 hours", "1 day", "2–3 days", "1 week").

Output format:
* Issue Type: <detected issue>
* Severity: <Low / Medium / High>
* Estimated Resolution Time: <time>
* Reason: <short explanation why this time is estimated>

Complaint: "{description}"
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text
        
        eta_days = 4
        match = re.search(r'Estimated Resolution Time:\s*(.+)', text, re.IGNORECASE)
        if match:
            time_str = match.group(1).lower()
            if 'hour' in time_str:
                eta_days = 1
            elif 'week' in time_str:
                nums = re.findall(r'\d+', time_str)
                if nums:
                    eta_days = max([int(n) for n in nums]) * 7
                else:
                    eta_days = 7
            elif 'day' in time_str:
                nums = re.findall(r'\d+', time_str)
                if nums:
                    eta_days = max([int(n) for n in nums])
                else:
                    eta_days = 3
        
        return text.strip(), eta_days
    except Exception as e:
        print("Gemini API Error:", e)
        return "Error calling AI.", 4

@app.route('/admin/update/<int:id>', methods=['POST'])
def update_status(id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
        
    new_status = request.form.get('status')
    rejection_reason = request.form.get('rejection_reason')
    
    if new_status in ['Pending', 'Accepted', 'Rejected']:
        conn = get_db_connection()
        
        if new_status == 'Accepted':
            row = conn.execute('SELECT issue_type, description FROM complaints WHERE id = ?', (id,)).fetchone()
            issue_type = row['issue_type']
            description = row['description']
            
            ai_text, eta_days = analyze_complaint_eta(description, issue_type)
            
            if not ai_text or ai_text == "API Key not configured":
                eta_days = {'Garbage': 1, 'Water': 2, 'Streetlight': 3, 'Roads': 5}.get(issue_type, 4)
                ai_text = f"* Issue Type: {issue_type}\\n* Severity: Unknown\\n* Estimated Resolution Time: Default\\n* Reason: AI API Key not configured."
                
            estimated_date = (datetime.now() + timedelta(days=eta_days)).strftime('%Y-%m-%d')
            conn.execute('UPDATE complaints SET status = ?, rejection_reason = ?, estimated_completion_date = ?, ai_analysis = ? WHERE id = ?', 
                         (new_status, rejection_reason, estimated_date, ai_text, id))
        else:
            # Clear ETA if rejected
            conn.execute('UPDATE complaints SET status = ?, rejection_reason = ?, estimated_completion_date = NULL, ai_analysis = NULL WHERE id = ?', 
                         (new_status, rejection_reason, id))
                         
        conn.commit()
        conn.close()
        flash('Status updated successfully.', 'success')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<int:id>', methods=['POST'])
def delete_complaint(id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    conn.execute('DELETE FROM complaints WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Complaint deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/api/send-otp', methods=['POST'])
def api_send_otp():
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    
    email = data['email']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if user:
        otp = f"{secrets.randbelow(1000000):06d}"
        expiry_time = (datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        
        conn = get_db_connection()
        conn.execute('UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?', 
                    (otp, expiry_time, user['id']))
        conn.commit()
        conn.close()
        
        try:
            msg = Message(
                subject='Your Password Reset OTP - CivicFix',
                sender=('CivicFix Support', MAIL_USERNAME) if MAIL_USERNAME else None,
                recipients=[email],
                html=f"<h3>Hello {user['name']},</h3><p>Your password reset OTP is: <strong>{otp}</strong></p><p>This code will expire in 5 minutes.</p>"
            )
            mail.send(msg)
        except Exception as e:
            # Handle securely without returning OTP in API response
            print(f"Error sending API OTP email: {str(e)}")
            return jsonify({'error': 'Failed to send OTP email.'}), 500
            
    return jsonify({'message': 'If that email address exists in our system, an OTP has been sent.'}), 200

@app.route('/api/verify-otp', methods=['POST'])
def api_verify_otp():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    email = data.get('email')
    otp = data.get('otp')
    
    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400
        
    conn = get_db_connection()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user = conn.execute('SELECT * FROM users WHERE email = ? AND reset_token = ? AND reset_token_expiry > ?', 
                      (email, otp, current_time)).fetchone()
    conn.close()
    
    if user:
        # Generate a temporary auth token tied to the DB for resetting pass
        reset_auth_token = secrets.token_hex(32)
        expiry_time = (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db_connection()
        conn.execute('UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?', 
                    (reset_auth_token, expiry_time, user['id']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'OTP verified successfully.', 'reset_auth_token': reset_auth_token}), 200
    
    return jsonify({'error': 'Invalid or expired OTP'}), 401

@app.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
        
    email = data.get('email')
    reset_auth_token = data.get('reset_auth_token')
    new_password = data.get('new_password')
    
    if not all([email, reset_auth_token, new_password]):
        return jsonify({'error': 'email, reset_auth_token, and new_password are required'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long.'}), 400
        
    conn = get_db_connection()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user = conn.execute('SELECT * FROM users WHERE email = ? AND reset_token = ? AND reset_token_expiry > ?', 
                      (email, reset_auth_token, current_time)).fetchone()
                      
    if user:
        conn.execute('UPDATE users SET password = ?, reset_token = NULL, reset_token_expiry = NULL WHERE id = ?', 
                    (generate_password_hash(new_password), user['id']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Password reset successfully.'}), 200
        
    conn.close()
    return jsonify({'error': 'Unauthorized or expired token.'}), 401

@app.route('/api/analytics')
def analytics():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    types_data = conn.execute('SELECT issue_type, COUNT(*) as count FROM complaints GROUP BY issue_type').fetchall()
    status_data = conn.execute('SELECT status, COUNT(*) as count FROM complaints GROUP BY status').fetchall()
    conn.close()
    
    return jsonify({
        'types': {row['issue_type']: row['count'] for row in types_data},
        'status': {row['status']: row['count'] for row in status_data}
    })

# Vercel WSGI handler
class VercelHandler:
    """WSGI-compatible handler for Vercel serverless functions"""
    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        return self.application(environ, start_response)

# Create the handler instance for Vercel
app = VercelHandler(app)
