#!/usr/bin/env python
"""
CyberPUF App Launcher - Loads .env and starts Uvicorn
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import subprocess
import webbrowser
import time
from dotenv import load_dotenv

def main():
    print("=" * 60)
    print("CyberPUF Web Dashboard Başlatılıyor...")
    print("=" * 60)
    print()
    
    # Load environment variables from .env
    load_dotenv()
    print("[OK] .env dosyasi yuklendi")
    
    # Verify required variables
    required_vars = ['CYBERPUF_AES_KEY', 'WEBSOCKET_TOKEN', 'APP_HOST', 'APP_PORT']
    missing = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)
        else:
            print(f"[OK] {var} = {os.environ.get(var)[:20]}...")
    
    if missing:
        print()
        print(f"[HATA] Eksik environment variables: {', '.join(missing)}")
        print("[HATA] .env dosyasi bulunamadi! Lutfen .env.example'i kopyalayip .env olusturun.")
        input("Devam etmek için herhangi bir tuşa basın...")
        sys.exit(1)
    
    print()
    host = os.environ.get('APP_HOST', '127.0.0.1')
    port = os.environ.get('APP_PORT', '8000')
    url = f"http://{host}:{port}"
    print(f"[->] Tarayıcı açılışı için sunucu bekleniyor: {url}")
    print()
    
    import threading
    import socket

    def open_browser_when_ready(host_addr, port_num, target_url):
        while True:
            try:
                with socket.create_connection((host_addr, int(port_num)), timeout=1):
                    break
            except (socket.timeout, ConnectionRefusedError, OSError):
                time.sleep(0.5)
        try:
            webbrowser.open(target_url)
        except:
            pass

    threading.Thread(target=open_browser_when_ready, args=(host, port, url), daemon=True).start()
    
    # Start Uvicorn
    print("[OK] python bagimliliklari tam.")
    print("=" * 60)
    print()
    
    cmd = [
        sys.executable, '-m', 'flask',
        '--app', 'main_app',
        'run',
        '--host', host,
        '--port', port
    ]
    
    if sys.platform != 'win32':
        cmd.append('--debug')
        
    subprocess.run(cmd)

if __name__ == '__main__':
    main()
