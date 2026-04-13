# Gmail SMTP Setup for Password Reset

## 📧 Gmail App Password Setup

### Step 1: Enable 2-Factor Authentication (2FA)
1. Go to your Google Account: https://myaccount.google.com/
2. Click on "Security" in the left menu
3. Under "Signing in to Google", enable "2-Step Verification"
4. Follow the setup process

### Step 2: Generate App Password
1. After enabling 2FA, go back to Security settings
2. Click on "App passwords" (you may need to search for it)
3. Select:
   - App: "Mail"
   - Device: "Other (Custom name)" → Enter "CivicFix"
4. Click "Generate"
5. Copy the 16-character password (this is your App Password)

### Step 3: Set Environment Variables
Set these environment variables before running the app:

**Windows (Command Prompt):**
```cmd
set MAIL_USERNAME=your-email@gmail.com
set MAIL_PASSWORD=your-16-character-app-password
```

**Windows (PowerShell):**
```powershell
$env:MAIL_USERNAME="your-email@gmail.com"
$env:MAIL_PASSWORD="your-16-character-app-password"
```

**Or add to your system environment variables permanently:**
1. Right-click "This PC" → Properties → Advanced system settings
2. Click "Environment Variables"
3. Add new variables:
   - Name: `MAIL_USERNAME` → Value: `your-email@gmail.com`
   - Name: `MAIL_PASSWORD` → Value: `your-16-character-app-password`

### Step 4: Test the Configuration
Restart your Flask app and test the forgot password feature.

## 🔧 Troubleshooting

### Common Issues:
1. **"Less secure apps" error**: Use App Password, not your regular password
2. **SMTP authentication failed**: Double-check the App Password
3. **Connection timeout**: Check firewall/antivirus settings
4. **Email not received**: Check spam/junk folder

### Test Email Sending:
```python
# Quick test in Python shell
from app import mail, Message
msg = Message('Test', recipients=['your-email@gmail.com'])
msg.body = 'Test email'
mail.send(msg)
```

## 🚀 Production Deployment
For production, consider:
- Using environment-specific configuration
- Setting up a dedicated email service (SendGrid, AWS SES)
- Configuring proper domain authentication (SPF, DKIM)
