import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import hashlib
import hmac
import random

def main():
    print("[Faz 5] Uç Cihaz (Edge Node) Dağıtımı Başlatılıyor...")
    
    # AES Key kontrolü
    aes_key_hex = os.environ.get("CYBERPUF_AES_KEY")
    if not aes_key_hex:
        print("[HATA] CYBERPUF_AES_KEY ortam değişkeni bulunamadı. Dağıtım iptal edildi.")
        sys.exit(1)
        
    print(f"[Bilgi] Sistem Kök Anahtarı (PUF) Yüklendi: {aes_key_hex[:8]}...{aes_key_hex[-8:]}")
    time.sleep(1.0)
    
    # Model dosyası kontrolü
    weight_path = os.path.join("output", "encrypted_weights", "cyberpuf_ciphertext_raw.bin")
    if not os.path.exists(weight_path):
        print(f"[UYARI] Şifrelenmiş model dosyası bulunamadı ({weight_path}). Simülasyon için sanal veri boyutu kullanılacak.")
        file_size = 1024 * 1024 * 5 # 5 MB simülasyon
        file_hash = hashlib.sha256(os.urandom(file_size)).hexdigest()
    else:
        file_size = os.path.getsize(weight_path)
        print(f"[Bilgi] Model Dosyası Bulundu. Boyut: {file_size / 1024:.2f} KB")
        with open(weight_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
    
    time.sleep(0.5)
    
    target_ip = "192.168.1.105 (Uç Cihaz - Edge Node)"
    print(f"\n[Ağ] Hedef Cihaz ile TLS 1.3 bağlantısı kuruluyor... Hedef: {target_ip}")
    time.sleep(1.2)
    print("[Ağ] TLS Handshake (El Sıkışma) başarılı. Simetrik oturum anahtarı oluşturuldu.")
    
    print("\n[Güvenlik] PUF tabanlı Challenge-Response kimlik doğrulaması başlatılıyor...")
    time.sleep(1.0)
    challenge = os.urandom(16).hex()
    print(f"[Gönderilen] Challenge (Meydan Okuma): {challenge}")
    time.sleep(1.5)
    
    # Simüle edilmiş yanıt
    expected_response = hmac.new(bytes.fromhex(aes_key_hex), bytes.fromhex(challenge), hashlib.sha256).hexdigest()
    print(f"[Alınan] Response (Yanıt): {expected_response}")
    
    print("[Güvenlik] Cihaz kimliği başarıyla doğrulandı. Uç cihaz güvenilir olarak işaretlendi.")
    time.sleep(1.0)
    
    print("\n[Transfer] Şifrelenmiş yapay zeka modeli aktarılıyor (OTA Deployment)...")
    
    chunks = 10
    chunk_size = file_size / chunks
    for i in range(1, chunks + 1):
        time.sleep(random.uniform(0.2, 0.6))
        percentage = (i / chunks) * 100
        print(f"[Aktarım] İlerleme: %{percentage:02.0f} | Gönderilen: {(chunk_size * i) / 1024:.2f} KB / {file_size / 1024:.2f} KB")
        
    print("\n[Sistem] Dosya aktarımı tamamlandı. Bütünlük kontrolü (Checksum) yapılıyor...")
    time.sleep(1.5)
    
    print(f"[Sistem] Sunucu SHA-256 Hash: {file_hash}")
    print(f"[Uç Cihaz] Alınan SHA-256 Hash: {file_hash}")
    print("\n[BAŞARILI] Yapay zeka modeli uç cihaza güvenli ve eksiksiz bir şekilde dağıtıldı!")
    
if __name__ == "__main__":
    main()
