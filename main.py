import time
import threading
import subprocess
import sys
import socket
from pathlib import Path

from config import WATCH_FOLDER, ALLOWED_EXTENSIONS

def main():
    print(f"\n{'='*50}")
    print("🚀 AKILLI FOTOĞRAF ALBÜMÜ BAŞLATILIYOR (CLIENT-SERVER MİMARİSİ)...")
    print(f"{'='*50}\n")

    # 1. LOG GÜRÜLTÜSÜNÜ KESME: stdout ve stderr tamamen susturuldu
    print("[SYSTEM]  ChromaDB API Sunucusu arka planda ayağa kaldırılıyor...")
    chroma_process = subprocess.Popen(
        ["chroma", "run", "--path", "storage/chroma_data", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    print("[SYSTEM] Sunucunun uyanması bekleniyor...")
    
    server_ready = False
    for _ in range(20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex(('127.0.0.1', 8000)) == 0:
                server_ready = True
                break
        time.sleep(1)
            
    if not server_ready:
        print("\n[HATA] ChromaDB sunucusu başlatılamadı veya ulaşılamadı!")
        chroma_process.terminate()
        sys.exit(1)

    print("[SYSTEM]  ChromaDB Sunucusu hazır ve dinliyor (Port: 8000)")

    # Sunucu uyandıktan sonra modülleri yüklüyoruz
    from orchestration.worker import ProcessingWorker
    from orchestration.watcher import start_local_watcher
    from core.vector_db import clean_ghost_records, collection
    
    # 2. HIZLI VE AKILLI SENKRONİZASYON (O(1) Karmaşıklığı)
    def sync_existing_images(folder_path, image_queue):
        print("[SYSTEM] Klasördeki mevcut fotoğraflar ve DB karşılaştırılıyor (Hızlı Senkronizasyon)...")
        folder = Path(folder_path)
        if not folder.exists(): return
        
        # Sadece tek bir HTTP isteği ile veritabanındaki TÜM dosya yollarını (ID'leri) çekiyoruz
        existing_data = collection.get(include=[])
        db_paths = set(existing_data['ids']) if existing_data and existing_data['ids'] else set()
        
        added_count = 0
        for file_path in folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
                abs_path = str(file_path.resolve())
                
                # Sadece veritabanı kümesinde (set) OLMAYAN yepyeni görseller hesaplanacak
                if abs_path not in db_paths:
                    image_queue.put(("ADD", abs_path))
                    added_count += 1
                    
        if added_count > 0:
            print(f"[SYSTEM] {added_count} adet yeni/işlenmemiş fotoğraf bulundu ve sıraya alındı!")
        else:
            print("[SYSTEM] Mükemmel! Tüm fotoğraflar zaten vektörleşmiş durumda. Yeniden hesaplama yapılmayacak.")

    clean_ghost_records()

    worker = ProcessingWorker()
    worker.start()

    sync_existing_images(WATCH_FOLDER, worker.image_queue)

    watcher_thread = threading.Thread(
        target=start_local_watcher, 
        args=(WATCH_FOLDER, worker.image_queue),
        daemon=True
    )
    watcher_thread.start()

    print("[SYSTEM]  Web arayüzü (Streamlit) ayağa kaldırılıyor...")
    streamlit_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "interface/app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("\n Sistem başarıyla başlatıldı!")
    print(" Tarayıcınızda şu adrese gidin: http://localhost:8501")
    print(" Sistemi tamamen kapatmak için terminalde 'CTRL + C' tuşlarına basın.\n")

    try:
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n Kapatılma sinyali alındı. Tüm sistemler güvenli bir şekilde durduruluyor...")
        streamlit_process.terminate()
        streamlit_process.wait()
        
        chroma_process.terminate()
        chroma_process.wait()
        
        worker.stop()
        print(" Akıllı Albüm başarıyla kapatıldı")

if __name__ == "__main__":
    main()