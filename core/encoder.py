import torch
import open_clip
from PIL import Image, ImageOps

from config import CLIP_MODEL_NAME, CLIP_PRETRAINED, DEVICE

print("[ENCODER] OpenCLIP modeli Metal (mps) üzerine yükleniyor...")

model, _, preprocess = open_clip.create_model_and_transforms(
    model_name=CLIP_MODEL_NAME, 
    pretrained=CLIP_PRETRAINED
)

model = model.to(DEVICE)
model.eval()

tokenizer = open_clip.get_tokenizer(CLIP_MODEL_NAME)

# YENİ EKLENEN KISIM: Fotoğrafı veri kaybı yaşamadan kareye dönüştüren fonksiyon
def pad_to_square(image):
    """
    Fotoğrafın orijinal en-boy oranını bozmadan, eksik kalan kısımları 
    siyah (0,0,0) ile doldurarak kusursuz bir kare (Letterbox) oluşturur.
    """
    width, height = image.size
    
    # Eğer fotoğraf zaten kareyse işlem yapma
    if width == height:
        return image
        
    max_dim = max(width, height)
    
    # Siyah arka planlı boş bir kare kanvas oluştur
    squared_image = Image.new("RGB", (max_dim, max_dim), (0, 0, 0))
    
    # Orijinal fotoğrafı bu siyah kanvasın tam merkezine yapıştır
    paste_x = (max_dim - width) // 2
    paste_y = (max_dim - height) // 2
    squared_image.paste(image, (paste_x, paste_y))
    
    return squared_image

def encode_image(image_path):
    """Fotoğrafı önce kareye tamamlar, sonra vektöre çevirir."""
    try:
        # 1. Fotoğrafı Aç ve RGB'ye Çevir
        raw_image = Image.open(image_path).convert("RGB")
        
        # 2. Kırpılmayı engellemek için Padding (Dolgu) uygula
        padded_image = pad_to_square(raw_image)
        
        # 3. Modele gönder (Artık hiçbir piksel kaybolmayacak!)
        image_tensor = preprocess(padded_image).unsqueeze(0).to(DEVICE)
        
        with torch.no_grad():
            image_features = model.encode_image(image_tensor)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            
        return image_features.squeeze(0).cpu().tolist()
        
    except Exception as e:
        print(f"[ENCODER HATA] {image_path} vektörleştirilemedi: {e}")
        raise e

def encode_text(search_query: str):
    """Kullanıcının metnini vektöre çevirir."""
    try:
        text_tokens = tokenizer([search_query]).to(DEVICE)
        with torch.no_grad():
            text_features = model.encode_text(text_tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)
        return text_features.squeeze(0).cpu().tolist()
    except Exception as e:
        print(f"[ENCODER HATA] Metin vektörleştirilemedi: {e}")
        raise e