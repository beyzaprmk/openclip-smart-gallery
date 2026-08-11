import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from config import ALLOWED_EXTENSIONS, WATCH_FOLDER
from graphclip_worker import run_graphclip_scan
from web_state import publish_event, publish_status, reset_live_results


def ask_user_choice() -> str:
    print("\n" + "=" * 50)
    print("AKILLI FOTOĞRAF ALBÜMÜ - MODEL SEÇİMİ")
    print("=" * 50)
    print("1) OpenCLIP kullan")
    print("2) GraphCLIP kullan")
    print("3) İkisini birlikte kullan")
    choice = input("Seçiminiz [1/2/3]: ").strip()
    if choice not in {"1", "2", "3"}:
        print("Geçersiz seçim, 1/2/3 arası değer girin.")
        return ask_user_choice()
    return choice


def list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []

    return sorted(
        [
            path
            for path in folder.rglob("*")
            if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
        ],
        key=lambda path: str(path),
    )


def start_chroma_server() -> subprocess.Popen:
    print("[SYSTEM] ChromaDB API sunucusu arka planda başlatılıyor...")
    return subprocess.Popen(
        ["chroma", "run", "--path", "storage/chroma_data", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_chroma_server(timeout_seconds: int = 20) -> None:
    print("[SYSTEM] ChromaDB sunucusunun hazır olması bekleniyor...")
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", 8000)) == 0:
                print("[SYSTEM] ChromaDB sunucusu hazır.")
                return
        time.sleep(1)

    raise RuntimeError("ChromaDB sunucusu başlatılamadı.")


def run_openclip_scan(images: list[Path], on_result=None) -> list[dict]:
    from core.encoder import encode_image
    from core.vector_db import save_to_db

    results: list[dict] = []
    for image_path in images:
        embedding = encode_image(str(image_path))
        save_to_db(str(image_path), embedding)

        payload = {
            "model": "openclip",
            "image": str(image_path),
            "status": "indexed",
        }
        results.append(payload)

        if on_result is not None:
            on_result(payload)

    return results


def launch_streamlit() -> subprocess.Popen:
    print("[SYSTEM] Web arayüzü (Streamlit) başlatılıyor...")
    return subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "interface/app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    reset_live_results()
    choice = ask_user_choice()
    images = list_images(WATCH_FOLDER)

    if not images:
        print(f"[SYSTEM] {WATCH_FOLDER} içinde işlenecek fotoğraf bulunamadı.")
        return

    print(f"[SYSTEM] {len(images)} fotoğraf taranacak.")

    chroma_process: subprocess.Popen | None = None
    streamlit_process: subprocess.Popen | None = None

    try:
        selected_mode = {"1": "openclip", "2": "graphclip", "3": "both"}[choice]
        publish_status("system", "selected_mode", {"mode": selected_mode})

        if choice in {"1", "3"}:
            chroma_process = start_chroma_server()
            wait_for_chroma_server()

        streamlit_process = launch_streamlit()

        if choice == "1":
            publish_status("openclip", "started", {"image_count": len(images)})
            run_openclip_scan(images, on_result=lambda payload: publish_event(payload))
            publish_status("openclip", "done", {"image_count": len(images)})

        elif choice == "2":
            publish_status("graphclip", "started", {"image_count": len(images)})
            run_graphclip_scan(WATCH_FOLDER, on_result=lambda payload: publish_event(payload))
            publish_status("graphclip", "done", {"image_count": len(images)})

        else:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}

                futures[executor.submit(
                    run_openclip_scan,
                    images,
                    lambda payload: publish_event(payload),
                )] = "openclip"

                futures[executor.submit(
                    run_graphclip_scan,
                    WATCH_FOLDER,
                    "a flower next to a vase",
                    lambda payload: publish_event(payload),
                )] = "graphclip"

                for future in as_completed(futures):
                    model_name = futures[future]
                    try:
                        future.result()
                        publish_status(model_name, "done", {"image_count": len(images)})
                    except Exception as exc:
                        publish_status(model_name, "error", {"error": str(exc)})

        print("\nTarama tamamlandı. Web arayüzünü izleyebilirsiniz: http://localhost:8501")
        print("Sistemi kapatmak için Ctrl+C basın.\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nKapatma sinyali alındı.")
    except Exception as exc:
        print(f"\n[HATA] {exc}")
    finally:
        if streamlit_process is not None:
            streamlit_process.terminate()
            streamlit_process.wait(timeout=5)

        if chroma_process is not None:
            chroma_process.terminate()
            chroma_process.wait(timeout=5)


if __name__ == "__main__":
    main()
