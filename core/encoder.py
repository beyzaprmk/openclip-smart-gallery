# OpenCLIP model yükleme ve vektör (embedding) çıkarma

import torch
import open_clip
from PIL import Image

# config.py'dan önceden tanımladığımız donanım ve model ayarlarını çekiyoruz
from config import CLIP_MODEL_NAME, CLIP_PRETRAINED, DEVICE

print("[ENCODER] OpenCLIP modeli Metal (mps) üzerine yükleniyor. Bu işlem sadece bir kez yapılacaktır...")

# Modeli ve veri ön işleme (preprocess) fonksiyonunu belleğe al
model, _, preprocess = open_clip.create_model_and_transforms(
    model_name=CLIP_MODEL_NAME, 
    pretrained=CLIP_PRETRAINED
)

# Modeli belirtilen cihaza (macOS için 'mps') gönder ve çıkarım (eval) moduna al
model = model.to(DEVICE)
model.eval()

def encode_image(image_path):
    """
    Verilen fotoğrafı okur, OpenCLIP modelinden geçirir 
    ve 512 boyutlu normalize edilmiş bir vektör (embedding) döndürür.
    """
    try:
        # 1. Fotoğrafı Aç ve RGB'ye Çevir
        image = Image.open(image_path).convert("RGB")
        
        # 2. Ön İşleme (Preprocess)
        # Görüntüyü 224x224 boyutuna getirir ve PyTorch tensörüne çevirir.
        image_tensor = preprocess(image).unsqueeze(0).to(DEVICE)
        
        # 3. Çıkarım (Inference)
        # torch.no_grad() ile gradyan hesaplamasını kapatma.
        # Bu, bellek tüketimini yarı yarıya düşürür ve işlemi hızlandırır.
        with torch.no_grad():
            image_features = model.encode_image(image_tensor)
            
            # 4. L2 Optimizasyonu (Kosinüs Benzerliği İçin)
            # Vektörleri normalize etmek, daha sonra ChromaDB'de yapılacak olan
            image_features /= image_features.norm(dim=-1, keepdim=True)
            
        # 5. ChromaDB'ye Uygun Formata Çevirme
        return image_features.squeeze(0).cpu().tolist()
        
    except Exception as e:
        print(f"[ENCODER HATA] {image_path} vektörleştirilemedi: {e}")
        # Hatanın Worker tarafından yakalanması için fırlatıyoruz
        raise e