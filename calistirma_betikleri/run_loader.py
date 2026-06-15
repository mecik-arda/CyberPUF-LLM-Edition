import sys
import time
sys.path.insert(0, '../')
from llm_secure_loader import SecureRAMLoader
loader = SecureRAMLoader('demo_model.cpuf_llm', ram_mount_point='/tmp/demo_ramdisk')
loader.mount_ramdisk()
path = loader.decrypt_to_ram()
print(f"Model Hazır! Yüklendiği Konum: {path}")
time.sleep(1)
print("[5/6] Zeroize işlemi tetikleniyor...")
loader.zeroize_and_unmount()
