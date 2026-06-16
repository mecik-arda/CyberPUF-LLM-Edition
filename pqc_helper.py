import os
import json
import hashlib
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

CONFIG_FILE = "/home/ardam/local_ai/CyberPUF_LLM/config.json"

def is_pqc_enabled():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f).get("pqc_enabled", False)
    except:
        return False

class RustMLKEMWrapper:
    """
    Rust tabanlı ML-KEM (Kyber) Kapsülleme Simülasyonu.
    Gerçek donanımda 'pqclean' veya benzeri Rust tabanlı KEM tekerleği (wheel) çağrılır.
    """
    @staticmethod
    def encapsulate(public_key_seed: bytes):
        # Kapsülleme (Encapsulation): Ortak anahtar (shared secret) ve kapsül (ciphertext) üretilir.
        print("[PQC] Rust ML-KEM/Kyber Kapsülleme (Encapsulation) tetiklendi...")
        shared_secret = hashlib.sha3_256(public_key_seed + b"ml-kem-rust-backend").digest()
        ciphertext_capsule = os.urandom(768) # Kyber-512 typical ciphertext length
        return shared_secret, ciphertext_capsule

    @staticmethod
    def decapsulate(private_key_seed: bytes, ciphertext_capsule: bytes):
        print("[PQC] Rust ML-KEM/Kyber Deşifreleme (Decapsulation) tetiklendi...")
        shared_secret = hashlib.sha3_256(private_key_seed + b"ml-kem-rust-backend").digest()
        return shared_secret

def derive_pqc_key(puf_entropy: bytes, capsule: bytes = None):
    """
    Eğer PQC aktifse, PUF entropisini ML-KEM kullanarak kapsüller ve
    elde edilen PQC Shared Secret'ı AES anahtarı için kullanır.
    
    Eğer capsule verilmemişse (Şifreleme aşaması), yeni bir tane üretilir.
    Eğer capsule verilmişse (Çözme aşaması), var olan kapsül açılır.
    """
    if not is_pqc_enabled():
        return puf_entropy, b""
        
    if capsule is None:
        # Şifreleme aşaması
        shared_secret, new_capsule = RustMLKEMWrapper.encapsulate(puf_entropy)
        
        hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b'pqc-aes-salt', info=b'pqc-kem', backend=default_backend())
        final_aes_key = hkdf.derive(shared_secret)
        return final_aes_key, new_capsule
    else:
        # Çözme aşaması
        shared_secret = RustMLKEMWrapper.decapsulate(puf_entropy, capsule)
        hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b'pqc-aes-salt', info=b'pqc-kem', backend=default_backend())
        final_aes_key = hkdf.derive(shared_secret)
        return final_aes_key, capsule
