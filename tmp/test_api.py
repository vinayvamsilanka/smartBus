import urllib.request
import json
from urllib.error import HTTPError

url = "http://127.0.0.1:8000/api/optimizer/predict"
data = json.dumps({"origin": "Eluru", "dest": "Hyderabad", "date": "2026-03-31"}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.getcode()}")
        print(f"Body: {response.read().decode('utf-8')}")
except HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Body: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
