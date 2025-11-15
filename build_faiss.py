from model import create_faiss_index

# Đường dẫn đến thư mục chứa file .npy
npy_dir = r"D:\clip-features-32-aic25-b1\clip-features-32"

# Gọi hàm để tạo my_index.faiss và my_config.json
create_faiss_index(
    npy_dir=npy_dir,
    index_path=r"D:\Database\my_index.faiss",
    config_path=r"D:\Database\my_config.json",
    batch_size=1000
)