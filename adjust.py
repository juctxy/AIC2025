import os
import json

FOLDER_PATH = r"D:\media-info-aic25-b1\media-info"

def adjust_image_paths(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        original = item["image_path"]
        item["image_path"] = original.replace(
            "/content/drive/MyDrive/",
            "D:\Data"
        )
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    for filename in os.listdir(FOLDER_PATH):
        if filename.endswith(".json"):
            adjust_image_paths(os.path.join(FOLDER_PATH, filename))
    print("✅ All image paths updated.")