import requests
import json

# URL login
login_url = "https://eventretrieval.oj.io.vn/api/v2/login"

# Body request
login_data = {
    "username": "team058",
    "password": "Wyy5uCHcbF"
}

# Gửi POST request
response = requests.post(login_url, json=login_data)

if response.status_code == 200:
    result = response.json()
    session_id = result["sessionId"]
    print(f"Session ID: {session_id}")
else:
    print(f"Error: {response.status_code} - {response.text}")