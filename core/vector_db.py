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