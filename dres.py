import requests
import json

# Function to fetch evaluation_id dynamically
def get_evaluation_id(session_id):
    eval_list_url = "https://eventretrieval.oj.io.vn/api/v2/client/evaluation/list"
    params = {"session": session_id}
    response = requests.get(eval_list_url, params=params)
    if response.status_code == 200:
        result = response.json()
        if result:
            evaluation_id = result[0]["id"]
            status = result[0]["status"]
            if status == "ACTIVE":
                return evaluation_id
            else:
                print("Evaluation is not active. Cannot submit.")
                return None
        else:
            print("No evaluations found.")
            return None
    else:
        print(f"Error fetching evaluation list: {response.status_code} - {response.text}")
        return None

# Hardcoded session_id (replace if needed, or fetch via login)
session_id = "eTWKX8KXrOSIuiXEmjnyNpO7V9JrddgG"

# Fetch evaluation_id
evaluation_id = get_evaluation_id(session_id)
if evaluation_id is None:
    exit()  # Stop if cannot get active evaluation

# Submit URL
submit_url = f"https://eventretrieval.oj.io.vn/api/v2/submit/{evaluation_id}"

# Params for submit
params = {
    "session": session_id
}

# Simulate UI inputs (in a real UI, these would come from JavaScript/form values)
# For testing, use console inputs; replace with variables from JS in production
video_id = input("Video_ID: ").strip()
start = input("Start: ").strip()
end = input("End: ").strip()
qa_answer = input("QA_Answer: ").strip()
frame_id = input("Frame_ID: ").strip()

# Determine submission type based on rules
if video_id and start and end:
    # KIS: Video_ID + Start + End filled
    body = {
        "answerSets": [{
            "answers": [{
                "mediaItemName": video_id,
                "start": start,
                "end": end
            }]
        }]
    }
elif video_id and start and not end and qa_answer:
    # QA: Video_ID + Start filled, End empty, QA_Answer filled
    text = f"QA-{qa_answer}-{video_id}-{start}"
    body = {
        "answerSets": [{
            "answers": [{
                "text": text
            }]
        }]
    }
elif video_id and frame_id:
    # TRAKE: Video_ID + Frame_ID filled (frame_id can be comma-separated)
    text = f"TR-{video_id}-{frame_id}"
    body = {
        "answerSets": [{
            "answers": [{
                "text": text
            }]
        }]
    }
else:
    print("Invalid input based on submission rules.")
    exit()

# Submit
response = requests.post(submit_url, params=params, json=body)

if response.status_code == 200:
    print("Submit successful!")
else:
    print(f"Error: {response.status_code} - {response.text}")