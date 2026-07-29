import time
import threading
import subprocess
import sys
from pathlib import Path

# Config ve Orchestration modülleri
from config import WATCH_FOLDER
from orchestration.worker import ProcessingWorker
from orchestration.watcher import start_local_watcher

def main():
    print(f"\n{'='*50}")
    print("AKILLI FOTOĞRAF ALBÜMÜ BAŞLATILIYOR...")
    print(f"{'='*50}\n")

    # 1. Kuyruk ve İşçi (Worker) Başlatma
    # İşçi, kuyruğa düşecek fotoğrafları beklemek üzere arka planda çalışmaya başlar.
    worker = ProcessingWorker()
    worker.start()

    # 2. İzleyiciyi (Watcher) Ayrı Bir İş Parçacığında (Thread) Başlatma
    # start_local_watcher kendi içinde sonsuz bir döngüye sahip olduğu için, 
    # ana akışı bloklamaması adına onu bir Thread (iş parçacığı) içine alıyoruz.
    watcher_thread = threading.Thread(
        target=start_local_watcher, 
        args=(WATCH_FOLDER, worker.image_queue),
        daemon=True
    )
    watcher_thread.start()

    # 3. Streamlit Arayüzünü Subprocess Olarak Başlatma
    print("[SYSTEM] Web arayüzü (Streamlit) ayağa kaldırılıyor...")
    
    # "streamlit run interface/app.py" komutunu terminale yazmışız gibi arka planda çalıştırır
    streamlit_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "interface/app.py"],
        stdout=subprocess.DEVNULL, # Streamlit'in terminali loglarla boğmasını engeller
        stderr=subprocess.DEVNULL
    )

    print("\n Sistem başarıyla başlatıldı!")
    print(" Tarayıcınızda şu adrese gidin: http://localhost:8501")
    print(" Sistemi tamamen kapatmak için terminalde 'CTRL + C' tuşlarına basın.\n")

    try:
        # Ana işlemi canlı tutmak için basit bir bekleme döngüsü
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n Kapatılma sinyali alındı. Tüm sistemler güvenli bir şekilde durduruluyor...")
        
        # 1. Streamlit sunucusunu kapat
        streamlit_process.terminate()
        streamlit_process.wait()
        
        # 2. İşçiyi (Worker) durdur
        worker.stop()
        
        print(" Akıllı Albüm başarıyla kapatıldı. Görüşmek üzere!")

if __name__ == "__main__":
    main()