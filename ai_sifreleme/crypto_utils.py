import os
import hashlib
import secrets

def get_puf_key():
    """Returns the PUF key from environment variable."""
    env_key = os.environ.get('CYBERPUF_AES_KEY')
    if env_key:
        try:
            return bytes.fromhex(env_key)
        except ValueError:
            raise ValueError("CYBERPUF_AES_KEY must be a valid hex string.")
            
    raise EnvironmentError("CYBERPUF_AES_KEY environment variable is not set. Fail-fast triggered.")

def derive_key_from_puf_simulation(puf_raw_data, salt=None):
    """
    Derives a 256-bit AES key from the raw PUF response using PBKDF2-HMAC-SHA256.
    
    IMPORTANT: The generated or provided salt MUST be persisted alongside the 
    ciphertext (e.g., in metadata) to ensure the exact same key can be derived 
    during decryption. Without the original salt, decryption will fail.
    """
    if salt is None:
        salt = secrets.token_bytes(16)
    
    # NIST tavsiyesi: Modern sistemler icin 600,000 iterasyon
    key = hashlib.pbkdf2_hmac(
        'sha256',
        puf_raw_data,
        salt,
        600000,
        dklen=32
    )
    return key, salt
