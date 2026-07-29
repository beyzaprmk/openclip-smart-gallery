#Kuyruk yönetimi ve Tüketici

import queue
import threading
import time
from pathlib import Path

from core.encoder import encode_image
from core.vector_db import save_to_db

class ProcessingWorker:
    """
    Kuyruktaki fotoğraf yollarını alıp arka planda yapay zeka 
    modelinden geçirerek veritabanına kaydeden sınıf.
    """
    def __init__(self):
        # İş parçacığı güvenli (thread-safe) kuyruğumuzu başlatıyoruz.
        self.image_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None

    def _process_queue(self):
        """Bu fonksiyon arka planda sürekli çalışarak kuyruğu kontrol eder."""
        print("[WORKER] Arka plan işçisi başlatıldı, kuyruk dinleniyor...")
        
        while self.is_running:
            try:
                # Kuyruktan dosya yolunu al (eğer boşsa 1 saniye bekleyip tekrar dener)
                # timeout sayesinde kuyruk boşken sonsuza kadar kilitlenmez
                image_path = self.image_queue.get(timeout=1.0)
                
                # Eğer 'STOP' sinyali geldiyse döngüyü kır
                if image_path == "STOP":
                    print("[WORKER] Kapanma sinyali alındı, işçi durduruluyor.")
                    self.image_queue.task_done()
                    break

                print(f"[WORKER] İşleniyor: {image_path}")
                
                try:
                    # 1. Fotoğrafı yapay zeka modelinden geçir ve vektörünü al
                    embedding = encode_image(image_path)
                    
                    # 2. Elde edilen vektörü metadata ile birlikte veritabanına kaydet
                    save_to_db(image_path, embedding)
                    
                    print(f"[WORKER] Başarı: {Path(image_path).name} veritabanına eklendi.")
                    
                except Exception as e:
                    print(f"[WORKER] HATA - {image_path} işlenemedi: {e}")
                
                finally:
                    # Başarılı ya da başarısız, bu işin bittiğini kuyruğa bildir
                    self.image_queue.task_done()

            except queue.Empty:
                # Kuyruk boşsa bir şey yapma, beklemeye devam et
                continue

    def start(self):
        """İşçiyi ayrı bir thread olarak arka planda  başlatır."""
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """İşçiyi güvenli bir şekilde durdurur."""
        self.is_running = False
        self.image_queue.put("STOP")
        if self.worker_thread:
            self.worker_thread.join()