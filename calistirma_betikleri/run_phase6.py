import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import random

def main():
    print("[Faz 6] Ağ Trafiği Gözetimi (Network Monitor) Başlatılıyor...")
    time.sleep(1.0)
    
    print("\n[Ağ] Paket Sniffer aktif edildi (Arayüz: eth0, Port: 8883/443)")
    print("[Ağ] Derin Paket İnceleme (DPI) motoru yükleniyor...")
    time.sleep(1.5)
    
    # Normal trafik simülasyonu
    print("\n--- CANLI AĞ TRAFİĞİ ---")
    for _ in range(4):
        time.sleep(random.uniform(0.3, 0.8))
        src = f"192.168.1.{random.randint(10, 50)}"
        dst = "192.168.1.105"
        size = random.randint(120, 1500)
        print(f"[Trafik] {src} -> {dst} | Protokol: TLS 1.3 | Boyut: {size} Bytes")
        
    # Atak simülasyonu
    time.sleep(1.5)
    print("\n[!] DİKKAT: ANOMALİ TESPİT EDİLDİ [!]")
    print("[Güvenlik] Ağda beklenmeyen bir ARP yansıması (Spoofing) saptandı.")
    
    time.sleep(1.0)
    print("[Saldırı] Kaynak: 192.168.1.150 (Tanımsız Cihaz)")
    print("[Saldırı] Tür: Ortadaki Adam (Man-in-the-Middle / MiTM)")
    print("[Saldırı] Eylem: Şifreli model dağıtım paketleri kopyalanmaya çalışılıyor...")
    
    time.sleep(2.0)
    print("\n[Savunma] CyberPUF Koruma Mekanizması Devrede:")
    print("  - Veri AES-256 (Kök: PUF Anahtarı) ile şifrelendiği için paketler çözülemez.")
    print("  - HMAC kimlik doğrulaması sayesinde paket içeriği değiştirilemez.")
    
    time.sleep(1.5)
    print("\n[Ağ] Kötü niyetli IP adresi bloklanıyor: 192.168.1.150")
    print("[Sistem] TLS bağlantısı güvenli kanaldan devam ettiriliyor.")
    
    for _ in range(3):
        time.sleep(random.uniform(0.3, 0.8))
        src = "192.168.1.10" # Dashboard IP
        dst = "192.168.1.105"
        size = random.randint(1024, 4096)
        print(f"[Trafik] {src} -> {dst} | Protokol: TLS 1.3 | Boyut: {size} Bytes [GÜVENLİ]")
        
    print("\n[BAŞARILI] Ağ trafik denetimi tamamlandı. İhlal girişimleri başarıyla bertaraf edildi.")

if __name__ == "__main__":
    main()
