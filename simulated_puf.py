import hashlib
import uuid
import platform
import psutil
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

def generate_hardware_fingerprint():
    """Simüle edilmiş deterministik bir donanım parmak izi."""
    try:
        node = platform.node()
        mac = str(uuid.getnode())
        processor = platform.processor()
        
        # Disk partitions stringification
        partitions = psutil.disk_partitions(all=False)
        disk_info = "".join([f"{p.device}{p.mountpoint}{p.fstype}" for p in partitions])
        
        fingerprint_raw = f"{node}-{mac}-{processor}-{disk_info}"
        return fingerprint_raw.encode('utf-8')
    except Exception as e:
        # Fallback in case of failure
        return b"fallback-simulated-hardware-uid"

def extract_puf_key():
    """
    Donanımsal PUF'tan elde edilen entropiyi simüle eder.
    Gerçek dünyada fuzzy extractor üzerinden gelen ham anahtardır.
    HKDF kullanılarak cryptographically secure 256-bit anahtar türetilir.
    """
    hw_id_bytes = generate_hardware_fingerprint()
    
    # 256-bit AES anahtarı için HKDF kullanımı
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'cyberpuf-llm-edition-static-salt-v1', # Gerçek projelerde rastgele salt metadata ile saklanır
        info=b'puf-key-expansion',
        backend=default_backend()
    )
    puf_key = hkdf.derive(hw_id_bytes)
    return puf_key

if __name__ == "__main__":
    key = extract_puf_key()
    print(f"Sistem Parmak Izi : {generate_hardware_fingerprint()}")
    print(f"Simulated PUF Key (Hex): {key.hex()}")
