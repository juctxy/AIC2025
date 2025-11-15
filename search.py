# search.py (unchanged, keep for OCR if needed later)
import os, json

def search_text_in_json(search_term):
    image_paths = []
    folder_path = r"D:\Data"
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".json"):
                json_path = os.path.join(root, file)
                try:
                    with open(json_path, 'r', encoding='utf-8') as json_file:
                        data = json.load(json_file)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON in file {json_path}: {e}")
                    continue
                if isinstance(data, list):
                    for entry in data:
                        if isinstance(entry, dict) and "text" in entry and "image_path" in entry:
                            if search_term.lower() in entry["text"].lower():
                                image_paths.append(entry["image_path"])
    return image_paths