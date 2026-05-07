import urllib.request
import urllib.error
import json

# First, let's find the latest tender
url = 'http://localhost:8000/tenders'
# Actually let's just test the specific tender the user is having issues with
# Try listing tenders first by checking if the info endpoint works
try:
    with urllib.request.urlopen('http://localhost:8000/info') as r:
        print("Backend /info:", r.read().decode())
except Exception as e:
    print(f"Backend not reachable: {e}")

# Now try the cartograph call for the specific tender
tender_id = 'a2eecd0d-82f7-4e68-821e-554b5eab3678'
url = f'http://localhost:8000/tenders/{tender_id}/cartograph'
print(f"\nPOST {url}")
req = urllib.request.Request(url, method='POST', data=b'')
try:
    with urllib.request.urlopen(req, timeout=180) as response:
        print(f"Status: {response.status}")
        print(f"Body: {response.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    body = e.read().decode('utf-8')
    print(f"Body: {body}")
    try:
        parsed = json.loads(body)
        print(f"Detail: {json.dumps(parsed.get('detail'), indent=2)}")
    except:
        pass
except urllib.error.URLError as e:
    print(f"URLError: {e.reason}")
except Exception as e:
    print(f"Exception: {e}")
