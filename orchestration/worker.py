import queue
import threading
from pathlib import Path

from core.encoder import encode_image
# delete_from_db fonksiyonunu da import etmeyi unutmadık:
from core.vector_db import save_to_db, delete_from_db

class ProcessingWorker:
    def __init__(self):
        self.image_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None

    def _process_queue(self):
        print("[WORKER] Arka plan işçisi başlatıldı, kuyruk dinleniyor...")
        
        while self.is_running:
            try:
                task = self.image_queue.get(timeout=1.0)
                
                if task == "STOP":
                    print("[WORKER] Kapanma sinyali alındı, işçi durduruluyor.")
                    self.image_queue.task_done()
                    break

                # Kuyruktan gelen paketi açıyoruz (unpacking)
                action, image_path = task
                
                try:
                    if action == "ADD":
                        print(f"[WORKER] Vektörleştiriliyor: {image_path}")
                        embedding = encode_image(image_path)
                        save_to_db(image_path, embedding)
                        print(f"[WORKER] Başarı: {Path(image_path).name} veritabanına eklendi.")
                        
                    elif action == "DELETE":
                        print(f"[WORKER] Veritabanından siliniyor: {image_path}")
                        # Vektörleştirmeye gerek yok, sadece DB'den siliyoruz
                        delete_from_db(image_path)
                        
                except Exception as e:
                    print(f"[WORKER] HATA - İşlem başarısız ({action}): {e}")
                
                finally:
                    self.image_queue.task_done()

            except queue.Empty:
                continue

    def start(self):
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()

    def stop(self):
        self.is_running = False
        self.image_queue.put("STOP")
        if self.worker_thread:
            self.worker_thread.join()