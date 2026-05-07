import urllib.request
import urllib.error

url = 'http://localhost:8000/tenders/a2eecd0d-82f7-4e68-821e-554b5eab3678/cartograph'
req = urllib.request.Request(url, method='POST')
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    print(e.read().decode('utf-8'))
except urllib.error.URLError as e:
    print(f"URLError: {e.reason}")
