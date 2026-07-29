import os
import torch
from pathlib import Path

# Projenin çalıştığı ana klasörün yolunu dinamik olarak buluyoruz
BASE_DIR = Path(__file__).resolve().parent

# Sistemin canlı olarak izleyeceği klasör. 
# NOT: Çalıştırmadan önce bilgisayarında bu klasörü oluşturmayı unutma!
WATCH_FOLDER = Path.home() / "Pictures" / "SmartGallery"

# ChromaDB'nin veritabanı dosyalarını kalıcı olarak yazacağı yer
CHROMA_DB_DIR = BASE_DIR / "storage" / "chroma_data"

# İlgili klasörler yoksa otomatik olarak oluşturulmasını sağlıyoruz
WATCH_FOLDER.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)



# OpenCLIP modeli. Hız ve başarı oranı dengesi açısından
CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED = "laion2b_s34b_b79k"


# İşletim sisteminin donanımına göre yapay zekanın nerede çalışacağını belirliyoruz.
# Mac kullandığın için sistem otomatik olarak 'mps' (Metal Performance Shaders) seçecektir.
# Bu, vektör çıkarma işlemini CPU'ya göre katbekat hızlandırır.
if torch.backends.mps.is_available():
    DEVICE = "mps"
elif torch.cuda.is_available():
    DEVICE = "cuda"
else:
    DEVICE = "cpu"


# Gözlemcinin sadece bu uzantılara sahip fotoğrafları dikkate almasını sağlıyoruz.
# Böylece klasöre yanlışlıkla atılan bir .pdf veya .txt dosyası sistemi çökertmez.
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}