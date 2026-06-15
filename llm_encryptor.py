import os
import sys
import tarfile
import struct
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import simulated_puf

MAGIC_HEADER = b"CPUF_LLM"
VERSION = 1

def encrypt_directory(input_dir, output_file):
    print(f"[1/3] Ağırlıklar taranıyor ve geçici tar arşivine alınıyor: {input_dir}")
    temp_tar = "temp_weights.tar"
    
    with tarfile.open(temp_tar, "w") as tar:
        tar.add(input_dir, arcname=os.path.basename(input_dir))
        
    orig_size = os.path.getsize(temp_tar)
    print(f"      -> Tar arşivi oluşturuldu. Orijinal Boyut: {orig_size / (1024*1024):.2f} MB")
        
    print(f"[2/3] PUF Anahtarı türetiliyor ve AES-256 motoru başlatılıyor...")
    key = simulated_puf.extract_puf_key()
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    print(f"[3/3] Streaming şifreleme uygulanıyor (Chunk boyutu: 64MB)...")
    CHUNK_SIZE = 64 * 1024 * 1024  # 64MB (16'nın katı)
    
    with open(temp_tar, "rb") as f_in, open(output_file, "wb") as f_out:
        # Format: [MAGIC(8)] [VERSION(4)] [IV(16)] [ORIG_SIZE(8)] [DATA]
        f_out.write(MAGIC_HEADER)
        f_out.write(struct.pack('<I', VERSION))
        f_out.write(iv)
        f_out.write(struct.pack('<Q', orig_size))
        
        while True:
            chunk = f_in.read(CHUNK_SIZE)
            if len(chunk) < CHUNK_SIZE:
                # Son veri parçasına her halükarda PKCS7 padding eklenmelidir
                padded_chunk = pad(chunk, AES.block_size)
                encrypted_chunk = cipher.encrypt(padded_chunk)
                f_out.write(encrypted_chunk)
                break
            else:
                encrypted_chunk = cipher.encrypt(chunk)
                f_out.write(encrypted_chunk)
                
    os.remove(temp_tar)
    print(f">> Başarılı! Şifreli LLM ağırlığı oluşturuldu: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Kullanım: python llm_encryptor.py <model_klasoru> <cikti_dosyasi.cpuf_llm>")
        sys.exit(1)
    encrypt_directory(sys.argv[1], sys.argv[2])
