import os
import sys
import shutil
import struct
from Crypto.Cipher import AES

# Üst dizindeki modüle erişim için yolu ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from simulated_puf import extract_puf_key

MAGIC_HEADER = b"CPUF_LLM"
VERSION = 1

def rotate_key(cpuf_file):
    """
    Şifreli .cpuf_llm dosyasının IV değerini ve şifrelemesini yeniler.
    Aynı ciphertext'in uzun süre diskinizde durmasını engelleyerek kriptografik güvenliği (Key Rotation) sağlar.
    """
    print(f"[Rotasyon] {cpuf_file} için şifre ve IV yenileme işlemi başlatılıyor...")
    if not os.path.exists(cpuf_file):
        raise FileNotFoundError(f"{cpuf_file} bulunamadı.")
        
    key = extract_puf_key()
    temp_file = cpuf_file + ".tmp"
    
    CHUNK_SIZE = 64 * 1024 * 1024  # 64MB Streaming
    
    with open(cpuf_file, "rb") as f_in, open(temp_file, "wb") as f_out:
        magic = f_in.read(8)
        version_data = f_in.read(4)
        old_iv = f_in.read(16)
        orig_size_data = f_in.read(8)
        
        # Eski şifreyi çözecek AES motoru
        decrypt_cipher = AES.new(key, AES.MODE_CBC, iv=old_iv)
        
        # Yeni şifreleme için tamamen rastgele, taze bir IV (Initialization Vector)
        new_iv = os.urandom(16)
        encrypt_cipher = AES.new(key, AES.MODE_CBC, iv=new_iv)
        
        # Yeni metadata header'ları yazılıyor
        f_out.write(magic)
        f_out.write(version_data)
        f_out.write(new_iv)
        f_out.write(orig_size_data)
        
        print(f"[Rotasyon] Eski IV: {old_iv.hex()}")
        print(f"[Rotasyon] Yeni IV: {new_iv.hex()}")
        
        # Chunk tabanlı (Streaming) Rotasyon
        while True:
            chunk = f_in.read(CHUNK_SIZE)
            if len(chunk) == 0:
                break
                
            # CBC modunda blok blok deşifre edip, RAM'e tam olarak çıkartmadan anında tekrar şifreliyoruz.
            # padding yapısına dokunulmaz, çünkü decrypt çıktısı zaten pad edilmiş veridir.
            decrypted = decrypt_cipher.decrypt(chunk)
            re_encrypted = encrypt_cipher.encrypt(decrypted)
            
            f_out.write(re_encrypted)
            
    # Eski dosyayı sil ve yeni rotasyona uğramış dosya ile yer değiştir
    shutil.move(temp_file, cpuf_file)
    print(f"[Rotasyon] Başarılı! Dosyanın kriptografik özellikleri güvenle güncellendi.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python key_rotation.py <model.cpuf_llm>")
        sys.exit(1)
    rotate_key(sys.argv[1])
