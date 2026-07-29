#Watchdog Gözlemcisi
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Ayarlar dosyasından geçerli uzantıları alıyoruz 
from config import ALLOWED_EXTENSIONS

class LocalImageHandler(FileSystemEventHandler):
    """
    İşletim sisteminden gelen dosya olaylarını yakalayan ve 
    bunları işlem kuyruğuna  aktaran sınıf.
    """
    def __init__(self, image_queue):
        super().__init__()
        # Ana sistemin bize vereceği Worker'a ait kuyruk
        self.image_queue = image_queue

    def is_valid_image(self, file_path):
        """Dosyanın bir resim formatında olup olmadığını kontrol eder."""
        path = Path(file_path)
        return path.suffix.lower() in ALLOWED_EXTENSIONS

    def on_created(self, event):
        """
        Klasörde YENİ bir dosya oluşturulduğunda tetiklenir.
        macOS'te FSEvents arka plan servisi bu fonksiyonu anında uyarır.
        """
        if not event.is_directory and self.is_valid_image(event.src_path):
            print(f"[WATCHER] Yeni fotoğraf yakalandı: {event.src_path}")
            
            # Yakalanan dosyanın yolunu Worker'ın kuyruğuna atıyoruz
            self.image_queue.put(event.src_path)

def start_local_watcher(folder_path, image_queue):
    """
    Klasör dinleme servisini başlatır. 
    Ana programı bloklayarak uygulamanın kapanmasını engeller.
    """
    event_handler = LocalImageHandler(image_queue)
    observer = Observer()
    
    # recursive=True ile klasörün içindeki alt klasörleri de dinleriz
    observer.schedule(event_handler, str(folder_path), recursive=True)
    observer.start()
    
    print(f"[WATCHER] İzleme başladı. Canlı dinlenen klasör: {folder_path}")
    
    try:
        # İzleyiciyi ayakta tutan sonsuz döngü.
        # Arka planda observer ve worker_thread çalışmaya devam eder.
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[WATCHER] Kapatılma sinyali (Ctrl+C) alındı, izleyici durduruluyor...")
        observer.stop()
        
    observer.join()