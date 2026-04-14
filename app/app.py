import os
import sys
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
import re
from pymongo import MongoClient
from bson import ObjectId

# Determine if running in serverless environment
IS_SERVERLESS = os.environ.get('VERCEL_ENV') is not None or '/tmp' in os.getcwd()

# Get the directory containing this file for proper path resolution
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# MongoDB Connection
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    print("WARNING: MONGO_URI not found in environment variables")
else:
    try:
        client = MongoClient(MONGO_URI)
        db = client["civicfix"]
        users_collection = db["users"]
        reports_collection = db["reports"]
        print("[INIT] MongoDB connected successfully")
        
        # Create default admin account if not exists
        admin_email = 'civic.managementsrm@gmail.com'
        existing_admin = users_collection.find_one({"email": admin_email})
        if not existing_admin:
            admin_pass = generate_password_hash('Admin@2026')
            users_collection.insert_one({
                "name": "Civic Management",
                "email": admin_email,
                "password": admin_pass,
                "is_admin": True
            })
            print("[INIT] Admin account created: civic.managementsrm@gmail.com")
    except Exception as e:
        print(f"[ERROR] MongoDB connection failed: {e}")
        client = None
        db = None
        users_collection = None
        reports_collection = None

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
    if not reports_collection:
        flash('Database not connected.', 'error')
        return render_template('home.html', complaints=[])
    
    # Fetch some recent complaints for the homepage
    complaints = list(reports_collection.find().sort("date", -1).limit(6))
    
    # Add user_name to each complaint
    for complaint in complaints:
        user = users_collection.find_one({"_id": ObjectId(complaint['user_id'])})
        complaint['user_name'] = user['name'] if user else 'Unknown'
    
    return render_template('home.html', complaints=complaints)

# --- Authentication Routes ---
@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '')
            email = request.form.get('email', '').lower().strip()
            password = request.form.get('password', '')
            
            if not name or not email or not password:
                flash('Please fill in all fields.', 'error')
                return render_template('register.html')
            
            if not users_collection:
                flash('Database not connected.', 'error')
                return render_template('register.html')
            
            user = users_collection.find_one({"email": email})
            
            if user:
                flash('Email already registered.', 'error')
            else:
                # Check if this is the first user - make them admin
                user_count = users_collection.count_documents({})
                is_first_user = user_count == 0
                
                hashed_password = generate_password_hash(password)
                print(f"[REGISTER] Creating user: {email}, is_admin: {is_first_user}")
                
                if is_first_user:
                    users_collection.insert_one({
                        "name": name,
                        "email": email,
                        "password": hashed_password,
                        "is_admin": True
                    })
                    flash('Registration successful! First user registered as admin.', 'success')
                else:
                    users_collection.insert_one({
                        "name": name,
                        "email": email,
                        "password": hashed_password,
                        "is_admin": False
                    })
                    flash('Registration successful! Please log in.', 'success')
                
                return redirect(url_for('login'))
        except Exception as e:
            print(f"[ERROR] Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').lower().strip()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash('Please fill in all fields.', 'error')
                return render_template('login.html')
            
            if not users_collection:
                flash('Database not connected.', 'error')
                return render_template('login.html')
            
            print(f"[LOGIN] Attempting login for: {email}")
            
            user = users_collection.find_one({"email": email})
            
            if not user:
                print(f"[LOGIN] User not found: {email}")
                flash('User not found. Please register first.', 'error')
                return render_template('login.html')
            
            if check_password_hash(user['password'], password):
                session['user_id'] = str(user['_id'])
                session['user_name'] = user['name']
                session['is_admin'] = user.get('is_admin', False)
                print(f"[LOGIN] Success: {email}, is_admin: {user.get('is_admin', False)}")
                flash('Logged in successfully!', 'success')
                if user.get('is_admin', False):
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('index'))
            else:
                print(f"[LOGIN] Wrong password for: {email}")
                flash('Invalid email or password.', 'error')
        except Exception as e:
            print(f"[ERROR] Login error: {e}")
            flash('Login failed. Please try again.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=('GET', 'POST'))
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        
        if not users_collection:
            flash('Database not connected.', 'error')
            return render_template('forgot_password.html')
        
        user = users_collection.find_one({"email": email})
        
        if user:
            # Generate 6-digit OTP
            otp = f"{secrets.randbelow(1000000):06d}"
            expiry_time = datetime.now() + timedelta(minutes=15)
            
            # Store OTP in database
            users_collection.update_one(
                {"_id": user['_id']},
                {"$set": {"reset_token": otp, "reset_token_expiry": expiry_time}}
            )
            
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
        otp = request.form.get('otp', '')
        
        if not users_collection:
            flash('Database not connected.', 'error')
            return render_template('verify_otp.html', email=email)
        
        current_time = datetime.now()
        user = users_collection.find_one({
            "email": email,
            "reset_token": otp,
            "reset_token_expiry": {"$gt": current_time}
        })
        
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
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('reset_password.html')
        
        if not users_collection:
            flash('Database not connected.', 'error')
            return render_template('reset_password.html')
        
        # Update password and clear reset token/session
        users_collection.update_one(
            {"email": email},
            {"$set": {"password": generate_password_hash(password), "reset_token": None, "reset_token_expiry": None}}
        )
        
        session.pop('reset_auth', None)
        session.pop('otp_email', None)
        
        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

# --- User Routes ---
@app.route('/report', methods=('GET', 'POST'))
def report_issue():
    try:
        if 'user_id' not in session:
            flash('Please log in to report an issue.', 'error')
            return redirect(url_for('login'))

        if request.method == 'POST':
            try:
                issue_type = request.form.get('issue_type', '')
                description = request.form.get('description', '')
                location = request.form.get('location', '')
                
                if not issue_type or not description or not location:
                    flash('Please fill in all required fields.', 'error')
                    return render_template('report.html')
                
            except Exception as e:
                print(f"[ERROR] Form parsing error: {e}")
                flash('Invalid form data.', 'error')
                return render_template('report.html')
            
            # Handle file upload
            image_path = None
            try:
                if 'image' in request.files:
                    file = request.files['image']
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        # Make filename unique
                        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(save_path)
                        image_path = f"uploads/{unique_filename}"
                        print(f"[INFO] Image saved: {save_path}")
            except Exception as e:
                print(f"[ERROR] File upload error: {e}")
                flash('Failed to upload image. Continuing without image.', 'warning')
            
            try:
                if not reports_collection:
                    flash('Database not connected.', 'error')
                    return render_template('report.html')
                
                # Smart Feature: Prevent duplicate complaints
                duplicate = reports_collection.find_one({
                    "location": location,
                    "issue_type": issue_type,
                    "status": {"$in": ["Pending", "Accepted"]}
                })
                
                if duplicate:
                    flash('A similar issue is already reported at this location. You can upvote it!', 'warning')
                    return redirect(url_for('index'))
                
                reports_collection.insert_one({
                    "user_id": session['user_id'],
                    "issue_type": issue_type,
                    "description": description,
                    "location": location,
                    "image_path": image_path,
                    "status": "Pending",
                    "date": datetime.now(),
                    "upvotes": 0,
                    "rejection_reason": None,
                    "estimated_completion_date": None,
                    "ai_analysis": None
                })
                
                flash('Issue reported successfully!', 'success')
                return redirect(url_for('my_complaints'))
            except Exception as e:
                print(f"[ERROR] Database error: {e}")
                flash('Failed to save issue. Please try again.', 'error')
                return render_template('report.html')
                
        return render_template('report.html')
    except Exception as e:
        print(f"[ERROR] Unexpected error in /report: {e}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return render_template('report.html')

@app.route('/my_complaints')
def my_complaints():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if not reports_collection:
        flash('Database not connected.', 'error')
        return render_template('my_complaints.html', complaints=[])
        
    complaints = list(reports_collection.find({"user_id": session['user_id']}).sort("date", -1))
    
    return render_template('my_complaints.html', complaints=complaints)

@app.route('/issue/<id>')
def view_issue(id):
    if not reports_collection or not users_collection:
        flash('Database not connected.', 'error')
        return redirect(url_for('index'))
    
    try:
        complaint = reports_collection.find_one({"_id": ObjectId(id)})
    except:
        flash('Invalid issue ID.', 'error')
        return redirect(url_for('index'))
    
    if not complaint:
        flash('Issue not found.', 'error')
        return redirect(url_for('index'))
    
    # Get user name
    user = users_collection.find_one({"_id": ObjectId(complaint['user_id'])})
    complaint['user_name'] = user['name'] if user else 'Unknown'
    
    return render_template('issue_detail.html', complaint=complaint)

@app.route('/upvote/<id>', methods=['POST'])
def upvote(id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not reports_collection:
        return jsonify({'error': 'Database not connected'}), 500
    
    try:
        reports_collection.update_one(
            {"_id": ObjectId(id)},
            {"$inc": {"upvotes": 1}}
        )
        complaint = reports_collection.find_one({"_id": ObjectId(id)})
        return jsonify({'upvotes': complaint['upvotes']})
    except:
        return jsonify({'error': 'Invalid issue ID'}), 400

# --- Admin Routes ---
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('Unauthorized access.', 'error')
        return redirect(url_for('index'))
    
    if not reports_collection or not users_collection:
        flash('Database not connected.', 'error')
        return render_template('admin_dashboard.html', complaints=[],
                               current_status='All', current_type='All',
                               pending_count=0, accepted_count=0)
        
    status_filter = request.args.get('status', 'All')
    type_filter = request.args.get('type', 'All')
    
    # Build query
    query = {}
    if status_filter != 'All':
        query['status'] = status_filter
    if type_filter != 'All':
        query['issue_type'] = type_filter
        
    complaints = list(reports_collection.find(query).sort("date", -1))
    
    # Add user_name to each complaint
    for complaint in complaints:
        user = users_collection.find_one({"_id": ObjectId(complaint['user_id'])})
        complaint['user_name'] = user['name'] if user else 'Unknown'
    
    pending_count = reports_collection.count_documents({"status": "Pending"})
    accepted_count = reports_collection.count_documents({"status": "Accepted"})
    
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

@app.route('/admin/update/<id>', methods=['POST'])
def update_status(id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    if not reports_collection:
        flash('Database not connected.', 'error')
        return redirect(url_for('admin_dashboard'))
        
    new_status = request.form.get('status')
    rejection_reason = request.form.get('rejection_reason')
    
    if new_status in ['Pending', 'Accepted', 'Rejected']:
        try:
            if new_status == 'Accepted':
                complaint = reports_collection.find_one({"_id": ObjectId(id)})
                if complaint:
                    issue_type = complaint['issue_type']
                    description = complaint['description']
                    
                    ai_text, eta_days = analyze_complaint_eta(description, issue_type)
                    
                    if not ai_text or ai_text == "API Key not configured":
                        eta_days = {'Garbage': 1, 'Water': 2, 'Streetlight': 3, 'Roads': 5}.get(issue_type, 4)
                        ai_text = f"* Issue Type: {issue_type}\\n* Severity: Unknown\\n* Estimated Resolution Time: Default\\n* Reason: AI API Key not configured."
                    
                    estimated_date = datetime.now() + timedelta(days=eta_days)
                    reports_collection.update_one(
                        {"_id": ObjectId(id)},
                        {"$set": {
                            "status": new_status,
                            "rejection_reason": rejection_reason,
                            "estimated_completion_date": estimated_date,
                            "ai_analysis": ai_text
                        }}
                    )
            else:
                # Clear ETA if rejected or pending
                reports_collection.update_one(
                    {"_id": ObjectId(id)},
                    {"$set": {
                        "status": new_status,
                        "rejection_reason": rejection_reason,
                        "estimated_completion_date": None,
                        "ai_analysis": None
                    }}
                )
            
            flash('Status updated successfully.', 'success')
        except:
            flash('Invalid complaint ID.', 'error')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<id>', methods=['POST'])
def delete_complaint(id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    if not reports_collection:
        flash('Database not connected.', 'error')
        return redirect(url_for('admin_dashboard'))
        
    try:
        reports_collection.delete_one({"_id": ObjectId(id)})
        flash('Complaint deleted.', 'success')
    except:
        flash('Invalid complaint ID.', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/api/send-otp', methods=['POST'])
def api_send_otp():
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    
    email = data['email'].lower().strip()
    
    if not users_collection:
        return jsonify({'error': 'Database not connected'}), 500
    
    user = users_collection.find_one({"email": email})
    
    if user:
        otp = f"{secrets.randbelow(1000000):06d}"
        expiry_time = datetime.now() + timedelta(minutes=5)
        
        users_collection.update_one(
            {"_id": user['_id']},
            {"$set": {"reset_token": otp, "reset_token_expiry": expiry_time}}
        )
        
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
    
    email = data.get('email', '').lower().strip()
    otp = data.get('otp')
    
    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400
    
    if not users_collection:
        return jsonify({'error': 'Database not connected'}), 500
        
    current_time = datetime.now()
    user = users_collection.find_one({
        "email": email,
        "reset_token": otp,
        "reset_token_expiry": {"$gt": current_time}
    })
    
    if user:
        # Generate a temporary auth token tied to the DB for resetting pass
        reset_auth_token = secrets.token_hex(32)
        expiry_time = datetime.now() + timedelta(minutes=15)
        users_collection.update_one(
            {"_id": user['_id']},
            {"$set": {"reset_token": reset_auth_token, "reset_token_expiry": expiry_time}}
        )
        return jsonify({'message': 'OTP verified successfully.', 'reset_auth_token': reset_auth_token}), 200
    
    return jsonify({'error': 'Invalid or expired OTP'}), 401

@app.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
        
    email = data.get('email', '').lower().strip()
    reset_auth_token = data.get('reset_auth_token')
    new_password = data.get('new_password')
    
    if not all([email, reset_auth_token, new_password]):
        return jsonify({'error': 'email, reset_auth_token, and new_password are required'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long.'}), 400
    
    if not users_collection:
        return jsonify({'error': 'Database not connected'}), 500
        
    current_time = datetime.now()
    user = users_collection.find_one({
        "email": email,
        "reset_token": reset_auth_token,
        "reset_token_expiry": {"$gt": current_time}
    })
                      
    if user:
        users_collection.update_one(
            {"_id": user['_id']},
            {"$set": {"password": generate_password_hash(new_password), "reset_token": None, "reset_token_expiry": None}}
        )
        return jsonify({'message': 'Password reset successfully.'}), 200
        
    return jsonify({'error': 'Unauthorized or expired token.'}), 401

@app.route('/api/analytics')
def analytics():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not reports_collection:
        return jsonify({'error': 'Database not connected'}), 500
        
    types_data = list(reports_collection.aggregate([
        {"$group": {"_id": "$issue_type", "count": {"$sum": 1}}}
    ]))
    status_data = list(reports_collection.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]))
    
    return jsonify({
        'types': {item['_id']: item['count'] for item in types_data},
        'status': {item['_id']: item['count'] for item in status_data}
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
