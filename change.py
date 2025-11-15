import os

# base path
base_path = r"D:\Data"

# range of old and new IDs
old_ids = [f"K{i:02d}" for i in range(1, 21)]  # K01 to K20
new_ids = [f"L{i:02d}" for i in range(1, 21)]  # L01 to L20

# process each file in the directory
for filename in os.listdir(base_path):
    if filename.endswith(".json") and any(filename.startswith(old_id + "_V") for old_id in old_ids):
        for old_id, new_id in zip(old_ids, new_ids):
            if filename.startswith(old_id + "_V"):
                old_file = os.path.join(base_path, filename)
                new_file = os.path.join(base_path, filename.replace(old_id, new_id))
                if os.path.exists(old_file):
                    os.rename(old_file, new_file)
                    print(f"Renamed: {old_file} -> {new_file}")
                else:
                    print(f"File not found: {old_file}")