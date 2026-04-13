# CivicFix - Crowdsourced Civic Issue Reporting System

CivicFix is a modern, full-stack web application designed for citizens to report civic issues (potholes, garbage, broken streetlights) and for authorities to track and manage them via an analytics dashboard.

## Features
- **Citizens**: Register/Login, submit issues with exact location and optional photo evidence, track status, upvote existing issues.
- **Authorities (Admins)**: Advanced dashboard with charts, filterable tables to triage reports, and status management.
- **Smart Features**: Prevent duplicate spam entries on identical locations/types, upvoting system.
- **Premium UI**: Custom CSS with glassmorphism, responsive grids, lightweight icons, and animations.

## Setup Instructions

1. **Prerequisites**: Ensure Python 3.8+ is installed.
2. **Navigate** to the `app` folder:
   ```bash
   cd "c:\python project\civic_report\app"
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Initialize Database**:
   ```bash
   python init_db.py
   ```
5. **Seed the Database with Sample Data**:
   ```bash
   python seed.py
   ```
   *Admin Credentials: `admin@civicfix.com` / `admin123`*  
   *Citizen Credentials: `john@example.com` / `user123`*
   
6. **Run the Server**:
   ```bash
   python app.py
   ```
7. **View Application**: Open your browser and go to `http://127.0.0.1:5000`

## Technologies Used
- **Backend**: Python, Flask, SQLite3, Werkzeug
- **Frontend**: HTML5, custom CSS3 Variables (No framework), BoxIcons, Chart.js for Admin Analytics.
