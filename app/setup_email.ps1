# PowerShell script to set up email environment variables for CivicFix
# Run this script in PowerShell to configure email settings

Write-Host "=== CivicFix Email Setup ===" -ForegroundColor Green
Write-Host ""

# Prompt for Gmail address
$gmail = Read-Host "Enter your Gmail address"
if (-not $gmail) {
    Write-Host "❌ Gmail address is required!" -ForegroundColor Red
    exit 1
}

# Validate Gmail format
if ($gmail -notmatch "@gmail\.com$") {
    Write-Host "❌ Please enter a valid Gmail address!" -ForegroundColor Red
    exit 1
}

# Prompt for App Password
Write-Host ""
Write-Host "Enter your 16-character Gmail App Password:" -ForegroundColor Yellow
Write-Host "(Get one from: https://myaccount.google.com/apppasswords)" -ForegroundColor Gray
$appPassword = Read-Host "App Password" -AsSecureString

# Convert secure string to plain text
$appPasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($appPassword))

if (-not $appPasswordPlain) {
    Write-Host "❌ App Password is required!" -ForegroundColor Red
    exit 1
}

# Set environment variables for current session
$env:MAIL_USERNAME = $gmail
$env:MAIL_PASSWORD = $appPasswordPlain

Write-Host ""
Write-Host "✅ Environment variables set for current session!" -ForegroundColor Green
Write-Host ""
Write-Host "To make these permanent, run these commands:" -ForegroundColor Yellow
Write-Host "setx MAIL_USERNAME `"$gmail`"" -ForegroundColor Cyan
Write-Host "setx MAIL_PASSWORD `"$appPasswordPlain`"" -ForegroundColor Cyan
Write-Host ""

# Test the configuration
Write-Host "📧 Testing email configuration..." -ForegroundColor Blue
python test_email.py

Write-Host ""
Write-Host "🚀 You can now test the password reset feature!" -ForegroundColor Green
