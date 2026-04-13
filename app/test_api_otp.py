import json
import time
from app import app, get_db_connection

def test_api_otp_flow():
    app.config['TESTING'] = True
    client = app.test_client()

    with app.app_context():
        # Clean db and insert test user
        conn = get_db_connection()
        conn.execute('DELETE FROM users WHERE email = ?', ('api_test@example.com',))
        from werkzeug.security import generate_password_hash
        conn.execute("INSERT INTO users (name, email, password) VALUES ('API Test', 'api_test@example.com', ?)",
                     (generate_password_hash('hashed_pass'),))
        conn.commit()
        conn.close()

    # Step 1: Request OTP
    response = client.post('/api/send-otp', json={'email': 'api_test@example.com'})
    assert response.status_code == 200, "Expected 200 OK"
    assert b'OTP has been sent' in response.data, "Expected OTP sent message"

    # Dig out the OTP from the database
    with app.app_context():
        conn = get_db_connection()
        user = conn.execute('SELECT reset_token FROM users WHERE email = ?', ('api_test@example.com',)).fetchone()
        otp = user['reset_token']
        conn.close()

    assert otp is not None, "OTP not generated"

    # Step 2: Verify OTP
    response = client.post('/api/verify-otp', json={'email': 'api_test@example.com', 'otp': otp})
    assert response.status_code == 200, "Failed to verify OTP"
    data = json.loads(response.data)
    reset_auth_token = data.get('reset_auth_token')
    assert reset_auth_token is not None, "Reset auth token not returned"

    # Step 3: Reset password
    response = client.post('/api/reset-password', json={
        'email': 'api_test@example.com',
        'reset_auth_token': reset_auth_token,
        'new_password': 'api_newpassword123'
    })
    assert response.status_code == 200, "Password reset failed"
    assert b'Password reset successfully' in response.data, "Password reset response lacking"

    print("All API tests passed!")

if __name__ == '__main__':
    test_api_otp_flow()
