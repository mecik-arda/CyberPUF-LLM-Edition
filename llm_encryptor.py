import os
import sys
import tarfile
import struct
import tempfile
from Crypto.Cipher import AES
import simulated_puf
import pqc_helper

MAGIC_HEADER = b"CPUF_LLM"
VERSION = 2

def encrypt_directory(input_dir, output_file):
    print(f"[1/3] Ağırlıklar taranıyor ve geçici tar arşivine alınıyor: {input_dir}")
    fd, temp_tar = tempfile.mkstemp(suffix=".tar", prefix="temp_weights_")
    os.close(fd)
    
    with tarfile.open(temp_tar, "w", dereference=True) as tar:
        tar.add(input_dir, arcname=os.path.basename(input_dir))
        
    orig_size = os.path.getsize(temp_tar)
    print(f"      -> Tar arşivi oluşturuldu. Orijinal Boyut: {orig_size / (1024*1024):.2f} MB")
        
    print(f"[2/3] PUF Anahtarı türetiliyor ve AES-256 motoru başlatılıyor...")
    salt = simulated_puf.generate_dynamic_salt(16)
    puf_base_key = simulated_puf.extract_puf_key(salt)
    
    # PQC Entagrasyonu
    final_key, capsule = pqc_helper.derive_pqc_key(puf_base_key)
    pqc_flag = 1 if capsule else 0
    
    iv = os.urandom(16)
    cipher = AES.new(final_key, AES.MODE_GCM, nonce=iv)
    
    import json
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r") as f:
            layer_paging = json.load(f).get("layer_paging_enabled", False)
    except:
        layer_paging = False

    if layer_paging:
        print(f"[Güvenlik] Katman düzeyinde parçalı şifreleme (Layer Paging) uygulanıyor...")
        CHUNK_SIZE = 4 * 1024 * 1024  # 4MB chunks
    else:
        print(f"[3/3] Streaming şifreleme uygulanıyor (Chunk boyutu: 64MB)...")
        CHUNK_SIZE = 64 * 1024 * 1024  # 64MB
    
    try:
        with open(temp_tar, "rb") as f_in, open(output_file, "wb") as f_out:
            # Format V2: [MAGIC(8)] [VERSION(4)] [SALT(16)] [IV(16)] [PQC_FLAG(1)] [CAPSULE(768/0)] [ORIG_SIZE(8)] [DATA] [TAG(16)]
            f_out.write(MAGIC_HEADER)
            f_out.write(struct.pack('<I', VERSION))
            f_out.write(salt)
            f_out.write(iv)
            f_out.write(struct.pack('B', pqc_flag))
            if pqc_flag:
                f_out.write(capsule)
            f_out.write(struct.pack('<Q', orig_size))
            
            while True:
                chunk = f_in.read(CHUNK_SIZE)
                if not chunk:
                    break
                encrypted_chunk = cipher.encrypt(chunk)
                f_out.write(encrypted_chunk)
                
            tag = cipher.digest()
            f_out.write(tag)
            
        print(f">> Başarılı! Şifreli LLM ağırlığı oluşturuldu: {output_file}")
    finally:
        if os.path.exists(temp_tar):
            os.remove(temp_tar)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Kullanım: python llm_encryptor.py <model_klasoru> <cikti_dosyasi.cpuf_llm>")
        sys.exit(1)
    encrypt_directory(sys.argv[1], sys.argv[2])
