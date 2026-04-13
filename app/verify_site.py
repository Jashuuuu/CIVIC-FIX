import urllib.request
import urllib.parse
from http.cookiejar import CookieJar

cj = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
urllib.request.install_opener(opener)

base_url = 'http://127.0.0.1:5000'

def check_url(url, method='GET', data=None):
    if data:
        data = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=data, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')

print("Testing Site...")

# 1. Home
status, content = check_url(base_url + '/')
print("Home:", status)

# 2. Login
login_data = {'email': 'civic.managementsrm@gmail.com', 'password': 'Admin@2026'}
status, content = check_url(base_url + '/login', method='POST', data=login_data)
# Login redirects on success
print("Login Status (Expect 200/Redirect):", status)

# 3. Admin
status, content = check_url(base_url + '/admin')
print("Admin Dashboard:", status)

if status == 200 and "Civic Management" in content:
    print("Logged in successfully as admin!")
    
    # parse the first complaint id from the html
    import re
    ids = re.findall(r'/admin/update/(\d+)', content)
    if ids:
        first_id = ids[0]
        # 4. Update
        update_data = {'status': 'Accepted', 'rejection_reason': ''}
        status, content = check_url(base_url + f'/admin/update/{first_id}', method='POST', data=update_data)
        print(f"Update Complaint {first_id}:", status)
        if status in [200, 302]:
            print("Update endpoint returned success/redirect. No 500 error!")
        else:
            print("Error on update!")
    else:
        print("No complaints found to update.")

    status, content = check_url(base_url + '/analytics')
    print("Analytics (Should redirect or 200 if API):", status)

else:
    print("Failed to load admin dashboard or verify admin session.")
