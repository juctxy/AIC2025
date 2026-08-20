# model.py - FAISS Index for CLIP features (direct faiss, no Haystack)
#
# Drop-in replacement for the old Haystack-based version. Keeps the same
# public functions/signatures (load_document_store, setup_pipeline,
# pipeline.run(query=..., params=...), doc.content/.score/.meta) so app.py
# does not need to change.
import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Đường dẫn dữ liệu
CLIP_DIRS = r"D:\clip-features-32"
MAPK_DIRS = r"D:\map-keyframes"
META_DIRS = r"D:\media-info"
DATA_DIRS = r"D:\Data"

INDEX_PATH = r"D:\Database\my_index.faiss"
# Replaces the old Haystack my_config.json: stores one metadata dict per
# vector, in the same order they were added to the FAISS index.
META_PATH = r"D:\Database\my_meta.json"

EMBEDDING_DIM = 512
CLIP_MODEL_NAME = "clip-ViT-B-32"

_clip_model = None


def get_clip_model():
    """Lazily load the CLIP text/image encoder (loaded once, reused)."""
    global _clip_model
    if _clip_model is None:
        _clip_model = SentenceTransformer(CLIP_MODEL_NAME)
    return _clip_model


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


class Document:
    """Lightweight stand-in for haystack.Document so app.py keeps working
    unchanged (it reads .content, .score, .meta)."""

    __slots__ = ("content", "meta", "score")

    def __init__(self, content, meta=None, score=None):
        self.content = content
        self.meta = meta or {}
        self.score = score


# ==============================
# Tạo FAISS index với batch insert
# ==============================
def create_faiss_index(
    npy_dir,
    index_path=INDEX_PATH,
    meta_path=META_PATH,
    batch_size=1000,
):
    # Nếu có file cũ thì xóa để tránh append
    if os.path.exists(index_path):
        os.remove(index_path)
    if os.path.exists(meta_path):
        os.remove(meta_path)

    # Flat index + inner product on L2-normalized vectors == cosine similarity
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    metadata = []

    all_files = [f for f in os.listdir(npy_dir) if f.endswith(".npy")]

    batch_vecs = []
    counter = 0

    def flush():
        nonlocal batch_vecs, counter
        if not batch_vecs:
            return
        mat = np.vstack(batch_vecs).astype(np.float32)
        faiss.normalize_L2(mat)
        index.add(mat)
        counter += len(batch_vecs)
        print(f"✅ Đã ghi {counter} vectors vào FAISS...")
        batch_vecs = []

    for file_name in all_files:
        emb_array = np.load(os.path.join(npy_dir, file_name)).astype(np.float32)

        if emb_array.ndim == 2:
            for i, emb in enumerate(emb_array):
                batch_vecs.append(emb)
                metadata.append({
                    "npy_file": file_name,
                    "frame": i,
                    "content": f"{file_name}_{i}",
                })
        else:
            batch_vecs.append(emb_array)
            metadata.append({
                "npy_file": file_name,
                "frame": 0,
                "content": file_name,
            })

        if len(batch_vecs) >= batch_size:
            flush()

    flush()  # ghi batch cuối

    faiss.write_index(index, index_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f)

    print(f"🎉 FAISS Flat index saved at {index_path}, {meta_path}")


# ==============================
# Load FAISS index đã build
# ==============================
class DocumentStore:
    """Holds the faiss index + parallel metadata list."""

    def __init__(self, index, metadata):
        self.index = index
        self.metadata = metadata


def load_document_store(index_path=INDEX_PATH, meta_path=META_PATH):
    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    return DocumentStore(index, metadata)


# ==============================
# Setup retriever + pipeline
# ==============================
class Pipeline:
    """Minimal stand-in for the old Haystack Pipeline: exposes
    .run(query=..., params={"retriever_text_to_image": {"top_k": N}})
    and returns {"documents": [Document, ...]}, matching app.py's usage."""

    def __init__(self, document_store):
        self.store = document_store
        self.model = get_clip_model()

    def run(self, query, params=None):
        top_k = 50
        if params and "retriever_text_to_image" in params:
            top_k = params["retriever_text_to_image"].get("top_k", top_k)

        query_emb = self.model.encode([query], convert_to_numpy=True).astype(np.float32)
        faiss.normalize_L2(query_emb)

        scores, ids = self.store.index.search(query_emb, top_k)

        docs = []
        for score, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue
            meta = self.store.metadata[idx]
            docs.append(Document(
                content=meta["content"],
                meta={"npy_file": meta["npy_file"], "frame": meta["frame"]},
                score=float(score),
            ))
        return {"documents": docs}


def setup_pipeline(document_store):
    return Pipeline(document_store)


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
        frame_num_str = f"{int(frame_id)+1:03d}"
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