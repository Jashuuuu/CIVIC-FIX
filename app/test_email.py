#!/usr/bin/env python3
"""
Test script to verify Flask-Mail configuration
"""

import os
from flask import Flask
from flask_mail import Mail, Message

def test_email_config():
    """Test email configuration and send a test email"""
    
    # Create a minimal Flask app for testing
    app = Flask(__name__)
    
    # Get environment variables
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    print("=== Flask-Mail Configuration Test ===")
    print(f"MAIL_USERNAME: {MAIL_USERNAME}")
    print(f"MAIL_PASSWORD: {'SET' if MAIL_PASSWORD else 'NOT SET'}")
    print()
    
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("❌ ERROR: Environment variables not set!")
        print("Please set:")
        print("  MAIL_USERNAME=your-email@gmail.com")
        print("  MAIL_PASSWORD=your-16-character-app-password")
        return False
    
    # Configure Flask-Mail
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
    app.config['MAIL_DEFAULT_SENDER'] = ('CivicFix Support', MAIL_USERNAME)
    
    # Initialize Flask-Mail
    mail = Mail(app)
    
    with app.app_context():
        try:
            # Create test message
            msg = Message(
                subject='🧪 CivicFix Email Test',
                sender=('CivicFix Support', MAIL_USERNAME),
                recipients=[MAIL_USERNAME],  # Send to self for testing
                html='''
                <h2>✅ Email Configuration Test Successful!</h2>
                <p>This is a test email from CivicFix to verify that your Flask-Mail configuration is working correctly.</p>
                <p><strong>Configuration Details:</strong></p>
                <ul>
                    <li>SMTP Server: smtp.gmail.com:587</li>
                    <li>TLS Enabled: Yes</li>
                    <li>Default Sender: CivicFix Support</li>
                </ul>
                <p>If you receive this email, your password reset feature should work!</p>
                <hr>
                <p><em>This is an automated test message from CivicFix.</em></p>
                '''
            )
            
            print("📧 Sending test email...")
            mail.send(msg)
            print(f"✅ Test email sent successfully to {MAIL_USERNAME}")
            print("📬 Check your inbox (and spam folder) for the test email.")
            return True
            
        except Exception as e:
            print(f"❌ Email sending failed: {str(e)}")
            print("\n🔧 Troubleshooting tips:")
            print("1. Ensure you're using a Gmail App Password (not your regular password)")
            print("2. Check that 2-factor authentication is enabled on your Gmail account")
            print("3. Verify the App Password was generated correctly")
            print("4. Check your internet connection and firewall settings")
            return False

def check_gmail_setup():
    """Display Gmail setup instructions"""
    print("\n=== Gmail App Password Setup ===")
    print("1. Enable 2-Factor Authentication:")
    print("   - Go to https://myaccount.google.com/security")
    print("   - Enable '2-Step Verification'")
    print()
    print("2. Generate App Password:")
    print("   - Go to https://myaccount.google.com/apppasswords")
    print("   - Select: Mail → Other (Custom name) → 'CivicFix'")
    print("   - Copy the 16-character password")
    print()
    print("3. Set Environment Variables:")
    print("   PowerShell: $env:MAIL_USERNAME='your-email@gmail.com'")
    print("   PowerShell: $env:MAIL_PASSWORD='your-16-character-app-password'")
    print()

if __name__ == "__main__":
    check_gmail_setup()
    test_email_config()
