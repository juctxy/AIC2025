from model import create_faiss_index

# Đường dẫn đến thư mục chứa file .npy
npy_dir = r"D:\clip-features-32"

# Gọi hàm để tạo my_index.faiss và my_meta.json
create_faiss_index(
    npy_dir=npy_dir,
    index_path=r"D:\Database\my_index.faiss",
    meta_path=r"D:\Database\my_meta.json",
    batch_size=1000
)