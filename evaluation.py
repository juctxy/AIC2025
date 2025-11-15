# OxTn-uzL3vTu7qmet0PIJFtBBqjUlr7A
import requests
import json
# URL list evaluation
eval_list_url = "https://eventretrieval.oj.io.vn/api/v2/client/evaluation/list"

# Params
params = {
    "session": "tQvRuqV9pCDe817yAU_zfAs7Yuw2OfpY"  # Từ bước 1
}

# Gửi GET request
response = requests.get(eval_list_url, params=params)

if response.status_code == 200:
    result = response.json()
    if result:
        evaluation_id = result[0]["id"]  # Lấy ID đầu tiên (thường chỉ có 1)
        print(f"Evaluation ID: {evaluation_id}")
    else:
        print("No evaluations found")
else:
    print(f"Error: {response.status_code} - {response.text}")