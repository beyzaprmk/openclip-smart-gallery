import time
from config import WATCH_FOLDER
from orchestration.worker import ProcessingWorker
from orchestration.watcher import start_local_watcher

def main():
    print(f"\n{'='*50}")
    print("🚀 Akıllı Fotoğraf Albümü Başlatılıyor...")
    print(f"📂 İzlenen Klasör: {WATCH_FOLDER}")
    print("💡 Test etmek için bu klasöre birkaç .jpg veya .png dosyası kopyalayın.")
    print(f"{'='*50}\n")

    # 1. Arka plan işçisini (Worker) başlat
    worker = ProcessingWorker()
    worker.start()

    try:
        # 2. Gözlemciyi (Watcher) başlat
        # Bu fonksiyon terminali bloklar ve sonsuz bir döngüde klasörü dinler.
        # Yakaladığı fotoğrafları doğrudan 'worker.image_queue' içine fırlatır.
        start_local_watcher(WATCH_FOLDER, worker.image_queue)
        
    except KeyboardInterrupt:
        # Terminalde Ctrl+C basıldığında sistemi temiz bir şekilde kapatır
        print("\n[MAIN] Sistem kapatılıyor...")
        
    finally:
        worker.stop()
        print("[MAIN] İşçi durduruldu. Sistem güvenle kapatıldı.")

if __name__ == "__main__":
    main()