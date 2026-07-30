import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import ALLOWED_EXTENSIONS

class LocalImageHandler(FileSystemEventHandler):
    def __init__(self, image_queue):
        super().__init__()
        self.image_queue = image_queue

    def is_valid_image(self, file_path):
        path = Path(file_path)
        # Gizli/geçici dosyaları yoksay
        if path.name.startswith('.'):
            return False
        return path.suffix.lower() in ALLOWED_EXTENSIONS

    def on_created(self, event):
        if not event.is_directory and self.is_valid_image(event.src_path):
            print(f"[WATCHER] Yeni fotoğraf yakalandı (Oluşturma): {event.src_path}")
            self.image_queue.put(("ADD", event.src_path))

    def on_deleted(self, event):
        if not event.is_directory and self.is_valid_image(event.src_path):
            print(f"[WATCHER] Fotoğraf silinmesi yakalandı: {event.src_path}")
            self.image_queue.put(("DELETE", event.src_path))

    def on_moved(self, event):
        if not event.is_directory and self.is_valid_image(event.dest_path):
            print(f"[WATCHER] Yeni fotoğraf yakalandı (Yeniden Adlandırma/Taşıma): {event.dest_path}")
            # Hedef yolu (dest_path) kullanarak veritabanına ekle
            self.image_queue.put(("ADD", event.dest_path))

def start_local_watcher(folder_path, image_queue):
    event_handler = LocalImageHandler(image_queue)
    observer = Observer()
    observer.schedule(event_handler, str(folder_path), recursive=True)
    observer.start()
    print(f"[WATCHER] İzleme başladı. Canlı dinlenen klasör: {folder_path}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[WATCHER] Kapatılma sinyali alındı, durduruluyor...")
        observer.stop()
        
    observer.join()