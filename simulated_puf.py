import hashlib
import uuid
import platform
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

def generate_hardware_fingerprint():
    """Simüle edilmiş deterministik bir donanım parmak izi."""
    try:
        node = platform.node()
        mac = str(uuid.getnode())
        processor = platform.processor()
        
        # Disk partitions removed for determinism
        fingerprint_raw = f"{node}-{mac}-{processor}"
        return fingerprint_raw.encode('utf-8')
    except Exception as e:
        # Fallback is dangerous, raise exception instead
        raise RuntimeError("Donanım parmak izi okunamadı. Sistem güvenliği için PUF işlemi durduruluyor.") from e

def extract_puf_key(salt=b'cyberpuf-llm-edition-static-salt-v1'):
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
        salt=salt,
        info=b'puf-key-expansion',
        backend=default_backend()
    )
    puf_key = hkdf.derive(hw_id_bytes)
    return puf_key

if __name__ == "__main__":
    key = extract_puf_key()
    print(f"Sistem Parmak Izi : {generate_hardware_fingerprint()}")
    print(f"Simulated PUF Key (Hex): {key.hex()}")
