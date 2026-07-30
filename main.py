import time
import threading
import subprocess
import sys
from pathlib import Path

# Config ve Orchestration modülleri
from config import WATCH_FOLDER, ALLOWED_EXTENSIONS
from orchestration.worker import ProcessingWorker
from orchestration.watcher import start_local_watcher

# Çift yönlü senkronizasyon için DB araçları
from core.vector_db import clean_ghost_records, collection

def sync_existing_images(folder_path, image_queue):
    """
    Sistem başlarken klasördeki mevcut fotoğrafları diskten okur.
    Veritabanında (ChromaDB) olmayanları tespit edip işçi kuyruğuna (Worker) ekler.
    """
    print("[SYSTEM] Klasördeki mevcut fotoğraflar taranıyor...")
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"[SYSTEM] Uyarı: {folder} bulunamadı.")
        return

    added_count = 0
    # Klasördeki dosyaları tek tek gez
    for file_path in folder.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
            absolute_path = str(file_path.resolve())
            
            # Bu dosya yolu veritabanında zaten kayıtlı mı?
            res = collection.get(where={"image_path": absolute_path})
            
            # Kayıtlı değilse, işlenmesi için kuyruğa fırlat
            if not res or len(res['ids']) == 0:
                image_queue.put(("ADD", absolute_path))
                added_count += 1
                
    if added_count > 0:
        print(f"[SYSTEM] {added_count} adet işlenmemiş fotoğraf bulundu ve kuyruğa eklendi!")
    else:
        print("[SYSTEM] Tüm mevcut fotoğraflar zaten veritabanında güncel.")

def main():
    print(f"\n{'='*50}")
    print(" AKILLI FOTOĞRAF ALBÜMÜ BAŞLATILIYOR...")
    print(f"{'='*50}\n")

    # 1. DB -> Disk Senkronizasyonu (Önceki oturumdan kalan hayalet verileri temizle)
    clean_ghost_records()

    # 2. Çok iş parçacıklı yapıyı (Kuyruk ve İşçi) başlat
    worker = ProcessingWorker()
    worker.start()

    # 3. YENİ EKLENEN: Disk -> DB Senkronizasyonu (Eksik fotoğrafları kuyruğa ekle)
    sync_existing_images(WATCH_FOLDER, worker.image_queue)

    # 4. İzleyiciyi (Watcher) arka planda başlat
    watcher_thread = threading.Thread(
        target=start_local_watcher, 
        args=(WATCH_FOLDER, worker.image_queue),
        daemon=True
    )
    watcher_thread.start()

    # 5. Streamlit Arayüzünü Subprocess Olarak Başlatma
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
        worker.stop()
        print(" Akıllı Albüm başarıyla kapatıldı. Görüşmek üzere!")

if __name__ == "__main__":
    main()