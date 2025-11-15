# model.py - FAISS Index for CLIP features (IVF+PQ + batch insert)
import os
import numpy as np
from haystack.document_stores import FAISSDocumentStore
from haystack.nodes.retriever.multimodal import MultiModalRetriever
from haystack import Pipeline
from haystack import Document
import torch

# Đường dẫn FAISS index
CLIP_DIRS = r"D:\clip-features-32-aic25-b1\clip-features-32"
MAPK_DIRS = r"D:\map-keyframes-aic25-b1\map-keyframes-b2"
META_DIRS = r"D:\media-info-aic25-b1\media-info"
DATA_DIRS = r"D:\Data"

INDEX_PATH = r"D:\Database\my_index.faiss"
CONFIG_PATH = r"D:\Database\my_config.json"


# ======================
# Helpers
# ======================
def get_dirs(video_id_or_prefix):
    """
    Nhận vào video_id (L25_V001, K05_V010) hoặc chỉ prefix ("L" hoặc "K")
    Trả về dict chứa path cho clip, mapk, meta, data
    """
    return {
        "clip": CLIP_DIRS,
        "mapk": MAPK_DIRS,
        "meta": META_DIRS,
        "data": DATA_DIRS,
    }


# ==============================
# Tạo FAISS index với batch insert
# ==============================
def create_faiss_index(
    npy_dir,
    index_path=INDEX_PATH,
    config_path=CONFIG_PATH,
    batch_size=1000
):
    # Nếu có file cũ thì xóa để tránh append
    if os.path.exists(index_path):
        os.remove(index_path)
    if os.path.exists(config_path):
        os.remove(config_path)

    # 🔹 FAISS Flat Index
    document_store = FAISSDocumentStore(
        faiss_index_factory_str="Flat",
        embedding_dim=512,
    )
    
    all_files = [f for f in os.listdir(npy_dir) if f.endswith(".npy")]
    
    batch, counter = [], 0
    for file_name in all_files:
        emb_array = np.load(os.path.join(npy_dir, file_name)).astype(np.float32)

        if emb_array.ndim == 2:
            for i, emb in enumerate(emb_array):
                batch.append(Document(
                    content=f"{file_name}_{i}",
                    embedding=emb,
                    meta={"npy_file": file_name, "frame": i}
                ))
        else:
            batch.append(Document(
                content=file_name,
                embedding=emb_array,
                meta={"npy_file": file_name, "frame": 0}
            ))

        # Ghi batch
        if len(batch) >= batch_size:
            document_store.write_documents(batch)
            counter += len(batch)
            print(f"✅ Đã ghi {counter} vectors vào FAISS...")
            batch = []

    # Ghi batch cuối
    if batch:
        document_store.write_documents(batch)
        counter += len(batch)
        print(f"✅ Đã ghi {counter} vectors vào FAISS...")

    # Lưu index
    document_store.save(index_path=index_path, config_path=config_path)
    print(f"🎉 FAISS Flat index saved at {index_path}, {config_path}")

# Load FAISS index đã build
# ==============================
def load_document_store():
    return FAISSDocumentStore.load(index_path=INDEX_PATH, config_path=CONFIG_PATH)

# ==============================
# Setup retriever + pipeline
# ==============================
def setup_pipeline(document_store):
    retriever = MultiModalRetriever(
        document_store=document_store,
        query_embedding_model="sentence-transformers/clip-ViT-B-32",
        query_type="text",
        document_embedding_models={"image": "sentence-transformers/clip-ViT-B-32"},
    )
    pipeline = Pipeline()
    pipeline.add_node(component=retriever, name="retriever_text_to_image", inputs=["Query"])
    return pipeline

# ==============================
# Hàm search query
# ==============================
def search_query(query, top_k=100):
    document_store = load_document_store()
    pipeline = setup_pipeline(document_store)
    results = pipeline.run(
        query=query,
        params={"retriever_text_to_image": {"top_k": top_k}}
    )
    docs = sorted(results["documents"], key=lambda d: d.score, reverse=True)
    return docs

# ==============================
# Chuyển kết quả về path ảnh
# ==============================
def docs_to_img_paths(docs, data_dir):
    img_paths = []
    for doc in docs:
        npy_id = doc.content  # ví dụ: "L21_V001.npy_15"
        parts = npy_id.split("_")
        video_id = "_".join(parts[:2])  # L21_V001
        frame_id = parts[-1]  # 15 (frame index)
        # Zero-pad frame number
        frame_num_str = f"{int(frame_id)+1:03d}"
        # Extract prefix from video_id (e.g., "L30" from "L30_V025")
        prefix = video_id.split("_")[0]
        image_path = f"{prefix}/keyframes/{video_id}/{frame_num_str}.jpg"
        full_path = os.path.join(data_dir, image_path)
        img_paths.append({
            "image_path": image_path,
            "video_id": video_id,
            "frame_id": frame_id,
            "score": doc.score,
            "exists": os.path.exists(full_path)
        })
    return img_paths