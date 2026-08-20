from flask import Flask, jsonify, request, render_template, send_from_directory
import os
import glob
import requests
import csv
import warnings
import json
from model import load_document_store, setup_pipeline, get_dirs
from deep_translator import GoogleTranslator  # thêm translate
from langdetect import detect  # detect ngôn ngữ

# Ẩn tất cả FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning)

# Load FAISS index + pipeline khi server start
document_store = load_document_store()
pipeline = setup_pipeline(document_store)

# Initialize Google Translator (once, globally for efficiency)
translator = GoogleTranslator(source='vi', target='en')

app = Flask(__name__)

# ======================
# Helpers
# ======================
def get_frame_idx(video_id, frame_n):
    """Tìm frame_idx từ CSV mapk dựa trên video_id và frame_n"""
    dirs = get_dirs(video_id)
    csv_path = os.path.join(dirs["mapk"], f"{video_id}.csv")
    if not os.path.exists(csv_path):
        print(f"⚠️ CSV not found: {csv_path}")
        return None
    with open(csv_path, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row["n"]) == frame_n:
                return int(row["frame_idx"])
    return None


def get_csv_data(video_id):
    """Đọc CSV và trả về list các dict với n, pts_time, frame_idx, fps (nếu có)"""
    dirs = get_dirs(video_id)
    csv_path = os.path.join(dirs["mapk"], f"{video_id}.csv")
    rows = []
    if not os.path.exists(csv_path):
        return rows
    with open(csv_path, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rows.append({
                    "n": int(row.get("n", 0)),
                    "pts_time": float(row.get("pts_time", 0.0)) if row.get("pts_time", "") != "" else None,
                    "frame_idx": int(row.get("frame_idx", 0)),
                    # fps may be present in CSV; try to parse as float, otherwise None
                    "fps": float(row["fps"]) if "fps" in row and row["fps"] != "" else None
                })
            except Exception:
                continue
    return rows


def get_metadata(video_id):
    """Đọc file metadata JSON cho video_id"""
    dirs = get_dirs(video_id)
    meta_path = os.path.join(dirs["meta"], f"{video_id}.json")
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error reading metadata for {video_id}: {e}")
        return None


def has_vietnamese_diacritics(text):
    """Check if text contains Vietnamese diacritic characters."""
    vietnamese_chars = set('àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ')
    return any(char in vietnamese_chars for char in text.lower())


# ======================
# Routes
# ======================
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_images')
def get_images():
    folder_path = request.args.get('folder', '')
    if not folder_path or not os.path.exists(folder_path):
        return jsonify({"error": "Folder not found"}), 404
    image_paths = glob.glob(os.path.join(folder_path, "*.jpg"))
    image_paths.sort(key=lambda x: int(os.path.basename(x).split('.')[0]))
    return jsonify([os.path.basename(img) for img in image_paths])


@app.route('/search_clip')
def search_clip():
    query = request.args.get('query', '').lower()
    topk = int(request.args.get('topk', 50))
    print(f"🔎 Received query: {query}, topk={topk}")
    
    # Detect language (Vietnamese -> translate sang English)
    try:
        lang = detect(query)
        print(f"Detected language: {lang}")
        if lang == 'vi' or has_vietnamese_diacritics(query):
            translated = translator.translate(query)
            query = translated.lower()
            print(f"✅ Translated to EN: {query}")
        else:
            print("✅ Query assumed English, no translation")
    except Exception as e:
        print(f"⚠️ Language detection/translation error: {e}")
        if has_vietnamese_diacritics(query):
            translated = translator.translate(query)
            query = translated.lower()
            print(f"✅ Fallback translated to EN: {query}")
        else:
            print("✅ Proceeding with original query (assumed English)")

    # Chạy pipeline để tìm kiếm
    results = pipeline.run(query=query, params={"retriever_text_to_image": {"top_k": topk}})
    print(f"✅ Pipeline finished, got {len(results['documents'])} docs")
    
    docs = sorted(results["documents"], key=lambda d: d.score, reverse=True)
    response = []
    
    for i, doc in enumerate(docs):
        npy_file = doc.content  # ví dụ: "L25_V063.npy"
        score = doc.score
        base_name = os.path.splitext(os.path.basename(npy_file))[0]  # "L25_V063"
        video_id = base_name
        frame_index = doc.meta.get("frame", 0)
        frame_n = frame_index + 1
        print(f"🔍 Calculated frame_index {frame_index} to frame_n {frame_n} for {video_id}")

        dirs = get_dirs(video_id)
        # Extract prefix from video_id (e.g., "L30" from "L30_V025")
        prefix = video_id.split("_")[0]
        image_path = f"{prefix}/keyframes/{video_id}/{frame_n:03d}.jpg"
        full_path = os.path.join(dirs["data"], image_path)
        print(f"🔍 Full path: {full_path}")
        if not os.path.exists(full_path):
            print(f"⚠️ Missing file: {full_path}")
            continue

        frame_idx_value = get_frame_idx(video_id, frame_n)
        csv_data = get_csv_data(video_id)

        # --- xử lý YouTube link ---
        yt_link = None
        meta = get_metadata(video_id)
        if meta and "youtube_url" in meta:
            yt_link = meta["youtube_url"]
        elif frame_idx_value is not None:
            yt_link = f"https://www.youtube.com/watch?v={video_id}&t={frame_idx_value}s"

        fixed_path = image_path.replace("\\", "/")
        response.append({
            "image_path": f"/images/{fixed_path}",
            "video_id": video_id,
            "frame_id": frame_n,
            "frame_idx": frame_idx_value,
            "score": score,
            "yt_link": yt_link,
            "csv_data": csv_data
        })

        if i < 5:
            print(f"➡️ {video_id} frame {frame_n} frame_idx={frame_idx_value} score={score:.4f} link={yt_link}")
    
    print(f"🎯 Returning {len(response)} results")
    return jsonify({"results": response})


@app.route('/images/<path:filename>')
def serve_image(filename):
    # Remove prefix logic, just serve from the data folder
    dirs = get_dirs("L01_V001")  # or any valid video_id, just to get the data folder
    return send_from_directory(dirs["data"], filename)

# Function to fetch evaluation_id dynamically (copied from dres.py)
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

@app.route('/submit_to_dres', methods=['POST'])
def submit_to_dres():
    data = request.json
    print(f"Received data: {data}")  # Debug
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Extract fields (strip whitespace)
    video_id = data.get('video_id', '').strip()
    start_raw = data.get('start', '').strip()
    end_raw = data.get('end', '').strip()
    qa_answer = data.get('qa_answer', '').strip()
    frame_id = data.get('frame_id', '').strip()

    # Login to get fresh session_id (as in your code)
    login_url = "https://eventretrieval.oj.io.vn/api/v2/login"
    login_data = {
        "username": "team058",
        "password": "Wyy5uCHcbF"
    }
    login_response = requests.post(login_url, json=login_data)
    if login_response.status_code != 200:
        print(f"Login error: {login_response.status_code} - {login_response.text}")
        return jsonify({"error": "Login failed"}), 500
    session_id = login_response.json()["sessionId"]

    # Fetch evaluation_id
    evaluation_id = get_evaluation_id(session_id)
    if evaluation_id is None:
        return jsonify({"error": "Cannot get active evaluation ID"}), 500

   # helper: try to convert a provided value to an integer frame index
    def parse_frame_idx(value):
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except Exception:
            return None

    # helper: compute ms start from frame_idx using CSV fps
    def frameidx_to_ms(vid, frame_idx):
        csv_rows = get_csv_data(vid)
        if not csv_rows:
            return None, "CSV not found or empty for video_id"
        # find row where frame_idx matches
        for r in csv_rows:
            if r.get("frame_idx") == frame_idx:
                fps = r.get("fps")
                # fallback: try metadata if fps missing
                if not fps:
                    meta = get_metadata(vid)
                    if meta and "fps" in meta:
                        try:
                            fps = float(meta["fps"])
                        except Exception:
                            fps = None
                if not fps or fps == 0:
                    return None, "FPS not found in CSV or metadata"
                # compute milliseconds
                start_ms = (frame_idx / float(fps)) * 1000.0
                return int(round(start_ms)), None
        return None, "No matching frame_idx found in CSV"

    # helper: if a value is numeric string treat as integer milliseconds
    def parse_numeric_ms(value):
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except Exception:
            return None


    # Determine submission type and build body (mutually exclusive: QA -> TRAKE -> KIS)
    body = None

    # QA (if qa_answer present) — take precedence
    if qa_answer:
        start_frame = parse_frame_idx(start_raw)
        if start_frame is not None:
            start_ms, err = frameidx_to_ms(video_id, start_frame)
            if err:
                return jsonify({"error": f"Cannot compute start time for QA: {err}"}), 400
            text = f"QA-{qa_answer}-{video_id}-{start_ms}"
        else:
            # keep raw start if not a frame index (could be ms or other)
            text = f"QA-{qa_answer}-{video_id}-{start_raw}"
        body = {
            "answerSets": [{
                "answers": [{
                    "text": text
                }]
            }]
        }

    # TRAKE (frame submission)
    elif frame_id:
        text = f"TR-{video_id}-{frame_id}"
        body = {
            "answerSets": [{
                "answers": [{
                    "text": text
                }]
            }]
        }

    # KIS (mediaItemName with numeric start/end)
    elif video_id and start_raw:
        # KIS logic (with conversion if frame)
        start_frame = parse_frame_idx(start_raw)

        if start_frame is not None:
            start_ms, err = frameidx_to_ms(video_id, start_frame)
            if err:
                return jsonify({"error": f"Cannot compute start time: {err}"}), 400
            start_value = str(start_ms + 3) 
            
            end_value = str(start_ms + 32)
        body = {
            "answerSets": [{
                "answers": [{
                    "mediaItemName": video_id,
                    "start": start_value,
                    "end": end_value
                }]
            }]
        }

    else:
        return jsonify({"error": "Invalid input based on submission rules"}), 400


    # Submit to DRES
    try:
        submit_url = f"https://eventretrieval.oj.io.vn/api/v2/submit/{evaluation_id}"
        params = {"session": session_id}
        print(f"Sending to DRES: {body}")  # Debug
        dres_response = requests.post(submit_url, params=params, json=body)
        print(f"DRES raw response: {dres_response.status_code} - {dres_response.text}")  # Debug

        # Forward DRES response to frontend
        if dres_response.status_code == 200:
            try:
                dres_json = dres_response.json()  # Parse JSON from DRES
                return jsonify(dres_json), 200  # Pass through {"status": "CORRECT", "description": ...}
            except ValueError:
                # If not JSON, fallback to text
                return jsonify({"status": "ERROR", "description": dres_response.text}), 200
        else:
            # Non-200: Return error with DRES text
            return jsonify({"status": "ERROR", "description": dres_response.text}), dres_response.status_code
    except Exception as e:
        print(f"Submission error: {str(e)}")
        return jsonify({"status": "ERROR", "description": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)