import sys
from llm_secure_loader import SecureRAMLoader
try:
    loader = SecureRAMLoader('/home/ardam/local_ai/encrypted_models/Phi-3-mini.cpuf_llm')
    loader.mount_ramdisk()
    path = loader.decrypt_to_ram()
    print('GCM MAC Verify Success! Path:', path)
    loader.zeroize_and_unmount()
except Exception as e:
    print('Hata:', e)
