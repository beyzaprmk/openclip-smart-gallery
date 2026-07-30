# ChromaDB bağlantısı, ekleme ve arama (semantic search) fonksiyonları

import chromadb
from pathlib import Path

# config.py'dan veritabanı dizinini çekiyoruz
from config import CHROMA_DB_DIR

print(f"[VECTOR DB] ChromaDB başlatılıyor... Dizin: {CHROMA_DB_DIR}")

# 1. Kalıcı Veritabanı İstemcisi
# Vektörlerin uçup gitmemesi için PersistentClient kullanıyoruz.
client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

# 2. Koleksiyon Oluşturma
collection = client.get_or_create_collection(
    name="smart_gallery",
    metadata={"hnsw:space": "cosine"}
)

def save_to_db(image_path: str, embedding: list):
    """
    Modelden çıkan vektörü dosya yolu ve ekstra bilgilerle birlikte diske kaydeder.
    """
    path_obj = Path(image_path)
    
    # ikinci kez eklemeye kalkarsak hata vermez, veritabanındaki kaydı günceller (Upsert).
    doc_id = str(path_obj.resolve())
    
    metadata = {
        "filename": path_obj.name,
        "extension": path_obj.suffix.lower()
    }
    
    # Vektörü kaydet (Eğer ID varsa günceller, yoksa yeni ekler)
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        metadatas=[metadata]
    )
    
def delete_from_db(image_path: str):
    """
    Silinen fotoğrafı veritabanından metadata (dosya yolu) üzerinden bularak kesin olarak siler.
    """
    path_obj = Path(image_path)
    absolute_path = str(path_obj.resolve())
    
    try:
        # 1. Veritabanında metadata'sı bu dosya yoluna eşit olan kaydı bul
        results = collection.get(
            where={"image_path": absolute_path}
        )
        
        # 2. Eğer kayıt bulunduysa, o ID'yi al ve tamamen sil
        if results and len(results['ids']) > 0:
            collection.delete(ids=results['ids'])
            print(f"[VECTOR DB] Başarı: {path_obj.name} vektör veritabanından tamamen SİLİNDİ!")
        else:
            # Bazen macOS'ta veya farklı işletim sistemlerinde yol stringleri farklılık gösterebilir.
            # Alternatif olarak sadece dosya adına göre (filename) de aratabiliriz:
            fallback_results = collection.get(
                where={"filename": path_obj.name}
            )
            if fallback_results and len(fallback_results['ids']) > 0:
                collection.delete(ids=fallback_results['ids'])
                print(f"[VECTOR DB] Başarı (Fallback): {path_obj.name} veritabanından SİLİNDİ!")
            else:
                print(f"[VECTOR DB] Uyarı: {path_obj.name} için silinecek vektör kaydı bulunamadı.")
            
    except Exception as e:
        print(f"[VECTOR DB HATA] Silme işlemi başarısız: {e}")


def search_in_db(query_embedding: list, n_results: int = 5):
    """
    Kullanıcının girdiği arama metninin vektörünü alır ve 
    kosinüs benzerliğine göre en yakın N adet fotoğrafı döndürür.
    """
    # Veritabanında hızlı bir yakın komşu (Nearest Neighbor) araması yapar
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    matches = []
    
    # Eğer veritabanı boşsa veya sonuç bulunamadıysa listeler boş döner
    if not results["ids"] or not results["ids"][0]:
        return matches
        
    ids = results["ids"][0]             # Eşleşen dosya yolları
    distances = results["distances"][0] # Kosinüs uzaklık skorları
    metadatas = results["metadatas"][0] # Dosya isimleri ve uzantılar
    
    for i in range(len(ids)):
        matches.append({
            "image_path": ids[i],
            "distance": distances[i],
            "filename": metadatas[i]["filename"]
        })
        
    return matches

def clean_ghost_records():
    """
    Uygulama başlarken veritabanındaki tüm kayıtları tarar,
    fiziksel olarak diskte artık var olmayan fotoğrafların vektörlerini temizler.
    """
    print("[VECTOR DB] Veritabanı ve disk senkronizasyonu kontrol ediliyor...")
    try:
        # Veritabanındaki tüm kayıtların metadata'larını (dosya yollarını) ve ID'lerini çek
        all_data = collection.get(include=["metadatas"])
        
        if not all_data or not all_data['ids']:
            print("[VECTOR DB] Veritabanı boş, temizlenecek veri yok.")
            return

        ids_to_delete = []
        
        # Her bir kaydı diskte kontrol et
        for db_id, metadata in zip(all_data['ids'], all_data['metadatas']):
            image_path = metadata.get('image_path')
            
            # Eğer dosya yolu varsa ama diskte fiziksel olarak yoksa, silinecekler listesine ekle
            if image_path and not Path(image_path).exists():
                ids_to_delete.append(db_id)
                print(f"[VECTOR DB] Tespit edildi (Hayalet Veri): {Path(image_path).name}")

        # Eğer silinecek hayalet veri bulunduysa, ChromaDB'den topluca sil
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            print(f"[VECTOR DB] Başarı: Toplam {len(ids_to_delete)} adet hayalet veri temizlendi.")
        else:
            print("[VECTOR DB] Mükemmel! Veritabanı ve klasör tamamen senkronize.")
            
    except Exception as e:
        print(f"[VECTOR DB HATA] Temizlik işlemi başarısız oldu: {e}")