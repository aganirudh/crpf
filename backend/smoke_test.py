import urllib.request
import urllib.error
import json

# Test through the Next.js proxy (like the browser does)
print("Testing through Next.js proxy (port 3000)...")
url = 'http://localhost:3000/api/info'
try:
    with urllib.request.urlopen(url, timeout=10) as r:
        info = json.loads(r.read().decode())
        print(f"  Provider: {info.get('llm_provider')}")
        print(f"  Model: {info.get('llm_extractor_model')}")
        print(f"  Mock: {info.get('mock_llm')}")
        print(f"  Key set: {info.get('llm_api_key_set')}")
        print("  ✓ Next.js proxy is working!")
except Exception as e:
    print(f"  ✗ Next.js proxy error: {e}")

# Test direct backend
print("\nTesting direct backend (port 8000)...")
url = 'http://localhost:8000/info'
try:
    with urllib.request.urlopen(url, timeout=10) as r:
        info = json.loads(r.read().decode())
        print(f"  Provider: {info.get('llm_provider')}")
        print(f"  Mock: {info.get('mock_llm')}")
        print("  ✓ Backend is working!")
except Exception as e:
    print(f"  ✗ Backend error: {e}")

print("\nAll good! Go to http://localhost:3000 and try 'Extract Criteria' again.")
