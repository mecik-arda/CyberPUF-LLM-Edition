import os
import sys
import struct
import pytest
from ai_sifreleme.crypto_utils import get_puf_key, derive_key_from_puf_simulation
from ai_sifreleme.encrypt_weights import build_encrypted_binary, encrypt_aes256_cbc
from ai_sifreleme.verify_encryption import parse_encrypted_binary, decrypt_data
import hashlib
import hmac

# Testlerin get_puf_key() fonksiyonunda hata vermemesi için sahte bir PUF anahtarı belirliyoruz
import secrets
os.environ['CYBERPUF_AES_KEY'] = secrets.token_hex(32)

def gecerli_sahte_cbc_paketi_uret():
    duz_metin = b"Sahte agirlik verisi 12345678"
    ham_puf_anahtari = get_puf_key()
    aes_anahtari, salt = derive_key_from_puf_simulation(ham_puf_anahtari)
    
    sifreli_metin, nonce, auth_tag = encrypt_aes256_cbc(duz_metin, aes_anahtari)
    
    meta_veri = {
        'plaintext_size': len(duz_metin),
        'salt_hex': salt.hex(),
        'encryption_mode': 'AES-256-CBC'
    }
    
    # Encrypt-then-MAC (AAD) oluşturma sürecini simüle ediyoruz
    aad_ciktisi = bytearray()
    aad_ciktisi.extend(b'CPFE')
    aad_ciktisi.extend(struct.pack('<B', 1))
    aad_ciktisi.extend(struct.pack('<B', 0))
    aad_ciktisi.extend(struct.pack('<B', 0x02)) # CBC Modu
    aad_ciktisi.extend(struct.pack('<B', 0x01)) # Direct Mod
    aad_byte_dizisi = bytes(aad_ciktisi)
    
    h = hmac.new(ham_puf_anahtari, digestmod=hashlib.sha256)
    h.update(aad_byte_dizisi)
    h.update(nonce)
    h.update(sifreli_metin)
    meta_veri['ciphertext_hmac'] = h.hexdigest()
    
    ikili_veri = build_encrypted_binary(
        sifreli_metin, nonce, auth_tag, meta_veri, mode='CBC', mac_mode='direct'
    )
    return ikili_veri, ham_puf_anahtari, aes_anahtari

def test_hmac_manipulasyonu(tmp_path):
    """İkili dosyadaki HMAC değerinin değiştirilmesinin başarıyla bir hatayı tetikleyip tetiklemediğini test eder."""
    ikili_veri, ham_puf_anahtari, aes_anahtari = gecerli_sahte_cbc_paketi_uret()
    
    dosya_yolu = tmp_path / "sahte_manipule_edilmis_hmac.bin"
    dosya_yolu.write_bytes(ikili_veri)
    
    ayristirilmis = parse_encrypted_binary(str(dosya_yolu))
    
    # Saldırganın meta verilerdeki beklenen HMAC değerini değiştirdiğini simüle ediyoruz
    manipule_edilmis_beklenen_hmac = ayristirilmis['metadata']['ciphertext_hmac']
    manipule_edilmis_beklenen_hmac = "ff" + manipule_edilmis_beklenen_hmac[2:] # İlk byte'ı tersine çevir
    
    with pytest.raises(ValueError, match="HMAC verification failed"):
        decrypt_data(
            ayristirilmis['ciphertext'],
            ayristirilmis['nonce'],
            ayristirilmis['auth_tag'],
            aes_anahtari,
            ham_puf_anahtari,
            mode=ayristirilmis['encryption_mode'],
            expected_hmac=manipule_edilmis_beklenen_hmac,
            aad=ayristirilmis.get('aad_bytes', b''),
            metadata=ayristirilmis['metadata']
        )

def test_sifreli_metin_manipulasyonu(tmp_path):
    """Şifreli metnin değiştirilmesinin başarıyla bir MAC doğrulama hatasını tetikleyip tetiklemediğini test eder."""
    ikili_veri, ham_puf_anahtari, aes_anahtari = gecerli_sahte_cbc_paketi_uret()
    dosya_yolu = tmp_path / "sahte_manipule_edilmis_sifreli_metin.bin"
    
    # Dosyanın sonuna doğru (şifreli metnin içinde olan) bir bit'i tersine çevir
    manipule_edilmis_ikili = bytearray(ikili_veri)
    manipule_edilmis_ikili[-1] ^= 0xFF
    
    dosya_yolu.write_bytes(manipule_edilmis_ikili)
    ayristirilmis = parse_encrypted_binary(str(dosya_yolu))
    
    with pytest.raises(ValueError, match="HMAC verification failed"):
        decrypt_data(
            ayristirilmis['ciphertext'],
            ayristirilmis['nonce'],
            ayristirilmis['auth_tag'],
            aes_anahtari,
            ham_puf_anahtari,
            mode=ayristirilmis['encryption_mode'],
            expected_hmac=ayristirilmis['metadata']['ciphertext_hmac'],
            aad=ayristirilmis.get('aad_bytes', b''),
            metadata=ayristirilmis['metadata']
        )

def test_yarim_kesilmis_paket(tmp_path):
    """Yarım kesilmiş bir paketin güvenli bir şekilde çöküp çökmediğini (hata verip vermediğini) test eder."""
    ikili_veri, ham_puf_anahtari, aes_anahtari = gecerli_sahte_cbc_paketi_uret()
    dosya_yolu = tmp_path / "sahte_yarim_kesilmis.bin"
    
    # Son 10 byte'ı kes (Truncate)
    yarim_kesilmis_ikili = ikili_veri[:-10]
    dosya_yolu.write_bytes(yarim_kesilmis_ikili)
    
    ayristirilmis = parse_encrypted_binary(str(dosya_yolu))
    
    # Şifreli metin kesildiği için şifre çözme işlemi başarısız olmalıdır,
    # bu nedenle HMAC eşleşmeyecek veya dolgu (padding) yanlış olacaktır.
    with pytest.raises(Exception):
        decrypt_data(
            ayristirilmis['ciphertext'],
            ayristirilmis['nonce'],
            ayristirilmis['auth_tag'],
            aes_anahtari,
            ham_puf_anahtari,
            mode=ayristirilmis['encryption_mode'],
            expected_hmac=ayristirilmis['metadata']['ciphertext_hmac'],
            aad=ayristirilmis.get('aad_bytes', b''),
            metadata=ayristirilmis['metadata']
        )
