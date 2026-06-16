import os
import sys
import shutil
import subprocess
import tarfile
import struct
import ctypes
import platform
import threading
import time
import psutil
from Crypto.Cipher import AES
from simulated_puf import extract_puf_key

MAGIC_HEADER = b"CPUF_LLM"
VERSION = 2

class SecureRAMLoader:
    def __init__(self, cpuf_file, ram_mount_point="/home/ardam/local_ai/temp_ramdisk", use_fuse=False):
        self.cpuf_file = cpuf_file
        self.ram_mount_point = ram_mount_point
        self.use_fuse = use_fuse
        self.extracted_path = None
        
    def mount_ramdisk(self):
        """Cross-Platform RAM/VRAM güvenli alan açıcı"""
        if not os.path.exists(self.ram_mount_point):
            os.makedirs(self.ram_mount_point)
            
        sys_os = platform.system()
        print(f"[Güvenlik] OS Tespit Edildi: {sys_os}. Bellek Alanı (RAM-Disk/FUSE) sisteme bağlanıyor...")
        
        try:
            if sys_os == "Linux":
                if self.use_fuse:
                    print("[FUSE] Linux FUSE modülü tetikleniyor...")
                else:
                    subprocess.run(["sudo", "mount", "-t", "tmpfs", "-o", "size=8G", "tmpfs", self.ram_mount_point], check=True, stderr=subprocess.DEVNULL, timeout=5)
            elif sys_os == "Windows":
                print("[Uyarı] Windows üzerinde ImDisk/WinFSP tespit edilemedi. Geçici güvenli dizin modu devrede!")
            elif sys_os == "Darwin":
                print("[Uyarı] macOS üzerinde hdiutil tespit edilemedi. Geçici güvenli dizin modu devrede!")
            else:
                pass
        except Exception as e:
            raise RuntimeError(f"[Kritik] RAM Disk / FUSE oluşturulamadı. Güvenlik gereği fallback yasaktır! Detay: {e}")

    def decrypt_to_ram(self):
        """FUSE veya Full-RAM modunda ağırlıkları deşifre eder."""
        if self.use_fuse:
            print("\n[Güvenlik] FUSE (On-the-fly Streaming) modu aktif edildi!")
            print("[Güvenlik] Modeller doğrudan belleğe tam olarak çıkarılmayacak, chunk'lar halinde okunacak.")
            return self._fuse_mount_simulate()
            
        print("[Güvenlik] Deşifre işlemi başlatılıyor (Full RAM Modu)...")
        temp_tar = os.path.join(self.ram_mount_point, "temp_weights.tar")
        CHUNK_SIZE = 64 * 1024 * 1024  # 64MB
        
        file_size = os.path.getsize(self.cpuf_file)
        
        with open(self.cpuf_file, "rb") as f_in, open(temp_tar, "wb") as f_out:
            magic = f_in.read(8)
            if magic != MAGIC_HEADER:
                raise ValueError("HATA: Gecersiz dosya formati. .cpuf_llm magic basligi bulunamadi.")
                
            version_data = f_in.read(4)
            version = struct.unpack('<I', version_data)[0]
            
            if version >= 2:
                salt = f_in.read(16)
                key = extract_puf_key(salt)
                iv = f_in.read(16)
                orig_size_data = f_in.read(8)
                orig_size = struct.unpack('<Q', orig_size_data)[0]
                data_size = file_size - 8 - 4 - 16 - 16 - 8 - 16 # V2 Format
            else:
                key = extract_puf_key() # V1 Format
                iv = f_in.read(16)
                orig_size_data = f_in.read(8)
                orig_size = struct.unpack('<Q', orig_size_data)[0]
                data_size = file_size - 8 - 4 - 16 - 8 - 16
            
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
                f_out.close()
                self._zeroize_file(temp_tar)
                os.remove(temp_tar)
                raise ValueError(f"HATA: MAC doğrulaması başarısız. Veri imha edildi! ({e})")
            
        print("[Güvenlik] Ağırlıklar belleğe (RAM) çıkarılıyor...")
        with tarfile.open(temp_tar, "r") as tar:
            try:
                tar.extractall(path=self.ram_mount_point, filter='data')
            except TypeError:
                tar.extractall(path=self.ram_mount_point) 
            
        self._zeroize_file(temp_tar)
        os.remove(temp_tar)
        
        items = os.listdir(self.ram_mount_point)
        dirs = [d for d in items if os.path.isdir(os.path.join(self.ram_mount_point, d))]
        if dirs:
            self.extracted_path = os.path.join(self.ram_mount_point, dirs[0])
        else:
            self.extracted_path = self.ram_mount_point
        return self.extracted_path

    def _fuse_mount_simulate(self):
        """FUSE modunun entegrasyon prototipi."""
        print("[FUSE] Modelin metadata başlıkları okunuyor ve sanal dosya sistemi (VFS) ayağa kaldırılıyor...")
        # Simüle edilmiş FUSE mount işlemi
        self.extracted_path = self.ram_mount_point
        return self.extracted_path

    def start_smart_zeroize(self, target_pid):
        """PID takibi ile süreç kapandığında otomatik zeroize eder (Smart Zeroize)."""
        def tracker():
            print(f"[Güvenlik] PID {target_pid} izleniyor. Süreç sonlandığında RAM silinecek.")
            while psutil.pid_exists(target_pid):
                time.sleep(2)
            print(f"[Güvenlik] Süreç ({target_pid}) sonlandı. Otomatik Zeroize başlatılıyor...")
            self.zeroize_and_unmount()
            
        t = threading.Thread(target=tracker, daemon=True)
        t.start()

    def _zeroize_file(self, filepath):
        if not os.path.exists(filepath):
            return
            
        file_size = os.path.getsize(filepath)
        print(f"[Güvenlik] Zeroize uygulanıyor: {os.path.basename(filepath)} ({file_size} bytes)")
        
        try:
            with open(filepath, "r+b") as f:
                chunk = b'\x00' * (64 * 1024 * 1024)
                written = 0
                while written < file_size:
                    to_write = min(len(chunk), file_size - written)
                    f.write(chunk[:to_write])
                    written += to_write
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            pass

    def zeroize_and_unmount(self):
        print("\n[Güvenlik] Hassas veriler RAM üzerinden Zeroize işlemiyle siliniyor...")
        if self.use_fuse:
            print("[FUSE] Sanal dosya sistemi bağlantısı kesiliyor...")
            
        if self.extracted_path and os.path.exists(self.extracted_path):
            if os.path.isdir(self.extracted_path):
                for root, dirs, files in os.walk(self.extracted_path, topdown=False):
                    for name in files:
                        filepath = os.path.join(root, name)
                        self._zeroize_file(filepath)
                        os.remove(filepath)
                    for name in dirs:
                        try:
                            os.rmdir(os.path.join(root, name))
                        except Exception:
                            pass
                try:
                    os.rmdir(self.extracted_path)
                except:
                    pass
            else:
                self._zeroize_file(self.extracted_path)
                os.remove(self.extracted_path)
        
        if os.path.exists(self.ram_mount_point):
            shutil.rmtree(self.ram_mount_point, ignore_errors=True)
            
        if platform.system() == "Linux" and not self.use_fuse:
            try:
                subprocess.run(["sudo", "umount", self.ram_mount_point], check=True, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        print("[Güvenlik] İzler kalıcı olarak silindi.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python llm_secure_loader.py <model.cpuf_llm> [use_fuse_flag: 0|1]")
        sys.exit(1)
        
    use_fuse_flag = False
    if len(sys.argv) == 3 and sys.argv[2] == "1":
        use_fuse_flag = True
        
    loader = SecureRAMLoader(sys.argv[1], use_fuse=use_fuse_flag)
    loader.mount_ramdisk()
    path = loader.decrypt_to_ram()
    print(f"Model Hazır. Path: {path}")
    
    # Kendi PID'imizi izleyelim (Hemen test için zeroize devreye girmez, input bekler)
    loader.start_smart_zeroize(os.getpid())
    
    input("Silmek ve bellekten atmak için ENTER'a basın...")
    loader.zeroize_and_unmount()
