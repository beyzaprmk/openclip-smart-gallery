import sys
from pathlib import Path
import chromadb

# Python Path Güvencesi
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from config import CHROMA_DB_DIR

print("[VECTOR DB] 🔌 ChromaDB Sunucusuna (localhost:8000) bağlanılıyor...")

# 1. KESİN ÇÖZÜM: Artık diske değil, HTTP üzerinden API sunucusuna bağlanıyoruz!
client = chromadb.HttpClient(host="localhost", port=8000)

collection = client.get_or_create_collection(
    name="smart_gallery",
    metadata={"hnsw:space": "cosine"}
)

def save_to_db(image_path: str, embedding: list):
    path_obj = Path(image_path)
    doc_id = str(path_obj.resolve())
    
    metadata = {
        "filename": path_obj.name,
        "extension": path_obj.suffix.lower(),
        "image_path": doc_id  # Silme ve onarma işlemleri için tam yolu da metadata'ya ekliyoruz
    }
    
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        metadatas=[metadata]
    )
    
def delete_from_db(image_path: str):
    path_obj = Path(image_path)
    absolute_path = str(path_obj.resolve())
    
    try:
        results = collection.get(where={"image_path": absolute_path})
        
        if results and len(results['ids']) > 0:
            collection.delete(ids=results['ids'])
            print(f"[VECTOR DB] Başarı: {path_obj.name} vektör veritabanından tamamen SİLİNDİ!")
        else:
            fallback_results = collection.get(where={"filename": path_obj.name})
            if fallback_results and len(fallback_results['ids']) > 0:
                collection.delete(ids=fallback_results['ids'])
                print(f"[VECTOR DB] Başarı (Fallback): {path_obj.name} veritabanından SİLİNDİ!")
            else:
                print(f"[VECTOR DB] Uyarı: {path_obj.name} için silinecek vektör kaydı bulunamadı.")
            
    except Exception as e:
        print(f"[VECTOR DB HATA] Silme işlemi başarısız: {e}")

def search_in_db(query_vector, n_results=6):
    # 2. TEMİZLİK: Artık taze bağlantı kurmaya veya RAM önbelleğini silmeye GEREK YOK!
    # Sunucu zaten tek bir kaynak olarak her zaman en güncel veriyi verecek.
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results
    )
    
    matches = []
    
    if not results["ids"] or not results["ids"][0]:
        return matches
        
    ids = results["ids"][0]             
    distances = results["distances"][0] 
    metadatas = results["metadatas"][0] 
    
    for i in range(len(ids)):
        matches.append({
            "image_path": ids[i],
            "distance": distances[i],
            "filename": metadatas[i]["filename"]
        })
        
    return matches

def clean_ghost_records():
    print("[VECTOR DB] Veritabanı ve disk senkronizasyonu kontrol ediliyor...")
    try:
        all_data = collection.get(include=["metadatas"])
        
        if not all_data or not all_data['ids']:
            print("[VECTOR DB] Veritabanı boş, temizlenecek veri yok.")
            return

        ids_to_delete = []
        
        for db_id, metadata in zip(all_data['ids'], all_data['metadatas']):
            image_path = metadata.get('image_path')
            
            if image_path and not Path(image_path).exists():
                ids_to_delete.append(db_id)
                print(f"[VECTOR DB] Tespit edildi (Hayalet Veri): {Path(image_path).name}")

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            print(f"[VECTOR DB] Başarı: Toplam {len(ids_to_delete)} adet hayalet veri temizlendi.")
        else:
            print("[VECTOR DB] Mükemmel! Veritabanı ve klasör tamamen senkronize.")
            
    except Exception as e:
        print(f"[VECTOR DB HATA] Temizlik işlemi başarısız oldu: {e}")