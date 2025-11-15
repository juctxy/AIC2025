import numpy as np
import os

npy_dir = r"D:\VSCODE_2025\AIC_2025_MODEL\clip_features"
for file_name in os.listdir(npy_dir):
    if file_name.endswith(".npy"):
        emb = np.load(os.path.join(npy_dir, file_name))
        print(f"{file_name}: shape = {emb.shape}")