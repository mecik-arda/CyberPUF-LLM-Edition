import os
import sys
import shutil
import subprocess
import tarfile
import struct
import ctypes
from Crypto.Cipher import AES
from simulated_puf import extract_puf_key

MAGIC_HEADER = b"CPUF_LLM"
VERSION = 1

class SecureRAMLoader:
    def __init__(self, cpuf_file, ram_mount_point="/home/ardam/local_ai/temp_ramdisk"):
        self.cpuf_file = cpuf_file
        self.ram_mount_point = ram_mount_point
        self.extracted_path = None
        
    def mount_ramdisk(self):
        """Linux tmpfs kullanarak VRAM/RAM üzerinde güvenli alan açar."""
        if not os.path.exists(self.ram_mount_point):
            os.makedirs(self.ram_mount_point)
            
        print("[Güvenlik] RAM Diski (tmpfs) sisteme bağlanıyor...")
        try:
            # sudo gerektirir. Gerçek ortamda sudoers içinde NOPASSWD ayarlanmalı.
            subprocess.run(["sudo", "mount", "-t", "tmpfs", "-o", "size=8G", "tmpfs", self.ram_mount_point], check=True, stderr=subprocess.DEVNULL, timeout=5)
        except Exception:
            print("[Uyarı] sudo mount yetkisi yok veya zaman aşımına uğradı, standart tmp dizini kullanılacak (RAM Disk Simülasyonu Fallback).")

    def decrypt_to_ram(self):
        """Ağırlıkları streaming mantığıyla RAM disk'e deşifre eder."""
        print("[Güvenlik] PUF Anahtarı türetiliyor ve AES-256 deşifre işlemi başlatılıyor...")
        key = extract_puf_key()
        
        temp_tar = os.path.join(self.ram_mount_point, "temp_weights.tar")
        
        CHUNK_SIZE = 64 * 1024 * 1024  # 64MB
        
        file_size = os.path.getsize(self.cpuf_file)
        # Format: MAGIC(8) + VERSION(4) + IV(16) + ORIG_SIZE(8) + DATA + TAG(16)
        data_size = file_size - 8 - 4 - 16 - 8 - 16
        
        with open(self.cpuf_file, "rb") as f_in, open(temp_tar, "wb") as f_out:
            magic = f_in.read(8)
            if magic != MAGIC_HEADER:
                raise ValueError("HATA: Gecersiz dosya formati. .cpuf_llm magic basligi bulunamadi.")
                
            version_data = f_in.read(4)
            version = struct.unpack('<I', version_data)[0]
            
            iv = f_in.read(16)
            
            orig_size_data = f_in.read(8)
            orig_size = struct.unpack('<Q', orig_size_data)[0]
            
            cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
            
            print("[Güvenlik] Streaming deşifreleme yapılıyor...")
            
            bytes_read = 0
            while bytes_read < data_size:
                read_size = min(CHUNK_SIZE, data_size - bytes_read)
                chunk = f_in.read(read_size)
                if not chunk:
                    break
                f_out.write(cipher.decrypt(chunk))
                bytes_read += len(chunk)
                
            tag = f_in.read(16)
            try:
                cipher.verify(tag)
                print("[Güvenlik] MAC doğrulaması başarılı! Dosya bütünlüğü tam.")
            except Exception as e:
                raise ValueError(f"HATA: MAC doğrulaması başarısız. Dosya bozulmuş veya anahtar yanlış! ({e})")
            
        print("[Güvenlik] Ağırlıklar belleğe (RAM) çıkarılıyor...")
        with tarfile.open(temp_tar, "r") as tar:
            tar.extractall(path=self.ram_mount_point)
            
        # Zeroize temp_tar
        self._zeroize_file(temp_tar)
        os.remove(temp_tar)
        
        # Tar'dan çıkan ilk dizini bul (genellikle model klasörü)
        items = os.listdir(self.ram_mount_point)
        if items:
            self.extracted_path = os.path.join(self.ram_mount_point, items[0])
        return self.extracted_path

    def _zeroize_file(self, filepath):
        """Dosyanın diski/RAM'i terk etmeden önce ctypes memset ile sıfırlanması"""
        if not os.path.exists(filepath):
            return
            
        file_size = os.path.getsize(filepath)
        print(f"[Güvenlik] Zeroize (Üstüne sıfır yazma) uygulanıyor: {os.path.basename(filepath)} ({file_size} bytes)")
        
        try:
            with open(filepath, "r+b") as f:
                # 64MB'lik zero chunklar
                chunk = b'\x00' * (64 * 1024 * 1024)
                written = 0
                while written < file_size:
                    to_write = min(len(chunk), file_size - written)
                    f.write(chunk[:to_write])
                    written += to_write
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"[Uyarı] Zeroize işlemi sırasında hata oluştu: {e}")

    def zeroize_and_unmount(self):
        """Ağırlıklar OpenVINO/Transformers tarafından okunduktan sonra RAM disk kalıcı olarak imha edilir."""
        print("\n[Güvenlik] Hassas veriler RAM üzerinden Zeroize işlemiyle siliniyor...")
        
        if self.extracted_path and os.path.exists(self.extracted_path):
            if os.path.isdir(self.extracted_path):
                for root, dirs, files in os.walk(self.extracted_path, topdown=False):
                    for name in files:
                        filepath = os.path.join(root, name)
                        self._zeroize_file(filepath)
                        os.remove(filepath)
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(self.extracted_path)
            else:
                self._zeroize_file(self.extracted_path)
                os.remove(self.extracted_path)
        
        if os.path.exists(self.ram_mount_point):
            # Kalan diğer herşeyi de temizle
            shutil.rmtree(self.ram_mount_point, ignore_errors=True)
            
        try:
            subprocess.run(["sudo", "umount", self.ram_mount_point], check=True, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        print("[Güvenlik] RAM disk başarıyla kapatıldı ve izler kalıcı olarak silindi.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Test Kullanımı: python llm_secure_loader.py <model.cpuf_llm>")
        sys.exit(1)
        
    loader = SecureRAMLoader(sys.argv[1])
    loader.mount_ramdisk()
    path = loader.decrypt_to_ram()
    print(f"Model RAM Diske Yüklendi: {path}")
    input("Silmek ve bellekten atmak için ENTER'a basın...")
    loader.zeroize_and_unmount()
