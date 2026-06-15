import os
import tarfile
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import simulated_puf

def encrypt_directory(input_dir, output_file):
    print(f"[1/3] Ağırlıklar taranıyor ve paketleniyor: {input_dir}")
    temp_tar = "temp_weights.tar"
    with tarfile.open(temp_tar, "w") as tar:
        tar.add(input_dir, arcname=os.path.basename(input_dir))
        
    print(f"[2/3] PUF Anahtarı alınıyor ve AES-256 motoru başlatılıyor...")
    key = simulated_puf.extract_puf_key()
    cipher = AES.new(key, AES.MODE_CBC)
    iv = cipher.iv
    
    with open(temp_tar, "rb") as f:
        data = f.read()
    
    print(f"[3/3] Şifreleme işlemi uygulanıyor...")
    padded_data = pad(data, AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    
    with open(output_file, "wb") as f:
        f.write(iv)
        f.write(encrypted_data)
        
    os.remove(temp_tar)
    print(f">> Başarılı! Şifreli LLM ağırlığı oluşturuldu: {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Kullanım: python llm_encryptor.py <model_klasoru> <cikti_dosyasi.cpuf_llm>")
        sys.exit(1)
    encrypt_directory(sys.argv[1], sys.argv[2])
