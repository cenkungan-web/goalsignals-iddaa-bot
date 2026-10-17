import uvicorn
import webbrowser
import threading
import time
import sys
import os

def open_browser():
    time.sleep(1.5)
    url = "http://127.0.0.1:8000"
    print(f"\n[+] Goal Signals Iddaa Bot hazir!")
    print(f"[+] Tarayicida aciliyor: {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Tarayici acilamadi: {e}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    sys.path.insert(0, current_dir)

    print("=" * 65)
    print("        GOAL SIGNALS IDDAA BOT")
    print("   Iddaa Oran Eslestirme & Bulten Botu (GoalSignals.com.tr)")
    print("=" * 65)
    print("Adres: http://127.0.0.1:8000")
    print("Durdurmak icin terminalde Ctrl + C tuslarina basin.\n")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False, log_level="info")
