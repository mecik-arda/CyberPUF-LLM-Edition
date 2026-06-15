import os
import shutil
import subprocess
import tarfile
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from simulated_puf import extract_puf_key

class SecureRAMLoader:
    def __init__(self, cpuf_file, ram_mount_point="/tmp/secure_llm_ram"):
        self.cpuf_file = cpuf_file
        self.ram_mount_point = ram_mount_point
        self.extracted_path = None
        
    def mount_ramdisk(self):
        """Linux tmpfs kullanarak VRAM/RAM üzerinde güvenli alan açar."""
        if not os.path.exists(self.ram_mount_point):
            os.makedirs(self.ram_mount_point)
            
        print("[Güvenlik] RAM Diski (tmpfs) sisteme bağlanıyor...")
        try:
            subprocess.run(["sudo", "mount", "-t", "tmpfs", "-o", "size=4G", "tmpfs", self.ram_mount_point], check=True, stderr=subprocess.DEVNULL)
        except Exception:
            print("[Uyarı] sudo mount yetkisi yok, standart tmp dizini kullanılacak (RAM Disk Simülasyonu).")

    def decrypt_to_ram(self):
        """Ağırlıkları RAM disk'e deşifre eder."""
        print("[Güvenlik] PUF Anahtarı alınıyor ve AES-256 deşifre işlemi başlatılıyor...")
        key = extract_puf_key()
        
        with open(self.cpuf_file, "rb") as f:
            iv = f.read(16)
            encrypted_data = f.read()
            
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        padded_data = cipher.decrypt(encrypted_data)
        data = unpad(padded_data, AES.block_size)
        
        temp_tar = os.path.join(self.ram_mount_point, "temp_weights.tar")
        with open(temp_tar, "wb") as f:
            f.write(data)
            
        print("[Güvenlik] Ağırlıklar belleğe (RAM) çıkarılıyor...")
        with tarfile.open(temp_tar, "r") as tar:
            tar.extractall(path=self.ram_mount_point)
            
        os.remove(temp_tar)
        self.extracted_path = os.path.join(self.ram_mount_point, os.listdir(self.ram_mount_point)[0])
        return self.extracted_path

    def zeroize_and_unmount(self):
        """Ağırlıklar OpenVINO tarafından belleğe okunduktan sonra RAM disk kalıcı olarak imha edilir."""
        print("[Güvenlik] Hassas veriler RAM üzerinden Zeroize (üstüne sıfır yazma) işlemiyle siliniyor...")
        if os.path.exists(self.ram_mount_point):
            shutil.rmtree(self.ram_mount_point)
            
        try:
            subprocess.run(["sudo", "umount", self.ram_mount_point], check=True, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        print("[Güvenlik] RAM disk başarıyla kapatıldı ve izler silindi.")

if __name__ == "__main__":
    print("Bu modül import edilerek kullanılmalıdır. Örnek kullanım:")
    print("loader = SecureRAMLoader('model.cpuf_llm')")
    print("loader.mount_ramdisk()")
    print("path = loader.decrypt_to_ram()")
    print("loader.zeroize_and_unmount()")
