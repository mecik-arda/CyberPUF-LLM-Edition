import os
import struct
import pytest
import numpy as np
from ai_sifreleme.crypto_utils import get_puf_key, derive_key_from_puf_simulation
from ai_sifreleme.encrypt_weights import build_encrypted_binary, encrypt_aes256_cbc, encrypt_aes256_gcm
from ai_sifreleme.verify_encryption import parse_encrypted_binary, decrypt_data, parse_weight_binary

# Test amaçlı sahte bir PUF anahtarı belirliyoruz
import secrets
os.environ['CYBERPUF_AES_KEY'] = secrets.token_hex(32)

def sahte_agirlik_ikilisi_uret():
    """CPUF formatıyla eşleşen çok basit bir sahte ağırlık ikilisi (binary) oluşturur."""
    cikis = bytearray()
    
    # Sihirli numara (Magic Number) ve versiyon
    cikis.extend(b'CPUF')
    cikis.extend(struct.pack('<B', 1))
    cikis.extend(struct.pack('<B', 0))
    cikis.extend(struct.pack('<B', 0)) # nicemleme_modu (quant_mode)
    
    toplam_dizi_sayisi = 1
    toplam_eleman_sayisi = 4
    cikis.extend(struct.pack('<I', toplam_dizi_sayisi))
    cikis.extend(struct.pack('<Q', toplam_eleman_sayisi))
    
    # 15 rezerve edilmiş byte
    cikis.extend(b'\x00' * 15)
    
    # Dizi 1 Başlığı
    cikis.extend(struct.pack('<B', 1)) # boyut sayısı (ndim)
    cikis.extend(struct.pack('<I', 4)) # sekil[0]
    cikis.extend(struct.pack('<I', 4)) # eleman_sayisi
    cikis.extend(struct.pack('<I', 16)) # byte_boyutu (float32 için 4 * 4)
    cikis.extend(struct.pack('<f', 1.0)) # olcekleme (scale)
    cikis.extend(struct.pack('<b', 0)) # sifir_noktasi (zp)
    cikis.extend(b'\x00' * 3) # dolgu (padding)
    
    # Dizi 1 Verisi (float32 değerleri: 1.0, 2.0, 3.0, 4.0)
    veri = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    cikis.extend(veri.tobytes())
    
    return bytes(cikis)

@pytest.mark.parametrize("mod,mac_modu", [
    ('GCM', 'direct'),
    ('CBC', 'direct'),
])
def test_uctan_uca_tam_akis(tmp_path, mod, mac_modu):
    """
    Uçtan Uca (E2E) Testi: 
    1. Sahte bir düz ağırlık ikili dosyası (binary) oluşturur.
    2. Belirtilen şifreleme modunu ve mac_modunu kullanarak dosyayı şifreler.
    3. Diske kaydeder.
    4. Şifrelenmiş dosyayı ayrıştırır (parse).
    5. Dosyayı tekrar düz ağırlıklara deşifre eder (decrypt).
    6. Düz ağırlık formatını ayrıştırır.
    7. Ayrıştırılan ağırlıkların orijinal sahte veriyle eşleştiğini doğrular (assert).
    """
    # 1. Düz Veri (Plain data)
    duz_metin = sahte_agirlik_ikilisi_uret()
    ham_puf_anahtari = get_puf_key()
    aes_anahtari, salt = derive_key_from_puf_simulation(ham_puf_anahtari)
    
    # 2. Şifreleme (Encrypt)
    if mod == 'GCM':
        aad_ciktisi = bytearray()
        aad_ciktisi.extend(b'CPFE\x01\x00\x01')
        aad_ciktisi.extend(struct.pack('<B', 0x01 if mac_modu == 'direct' else 0x02))
        aad_byte_dizisi = bytes(aad_ciktisi)
        
        sifreli_metin, nonce, auth_tag = encrypt_aes256_gcm(duz_metin, aes_anahtari, aad=aad_byte_dizisi)
        meta_veri = {'plaintext_size': len(duz_metin), 'salt_hex': salt.hex()}
    else:
        sifreli_metin, nonce, auth_tag = encrypt_aes256_cbc(duz_metin, aes_anahtari)
        meta_veri = {'plaintext_size': len(duz_metin), 'salt_hex': salt.hex()}
        
        aad_ciktisi = bytearray()
        aad_ciktisi.extend(b'CPFE\x01\x00\x02')
        aad_ciktisi.extend(struct.pack('<B', 0x01 if mac_modu == 'direct' else 0x02))
        aad_byte_dizisi = bytes(aad_ciktisi)
        
        import hmac, hashlib
        h = hmac.new(ham_puf_anahtari, digestmod=hashlib.sha256)
        h.update(aad_byte_dizisi)
        h.update(nonce)
        h.update(sifreli_metin)
        meta_veri['ciphertext_hmac'] = h.hexdigest()

    ikili_veri = build_encrypted_binary(
        sifreli_metin, nonce, auth_tag, meta_veri, mode=mod, mac_mode=mac_modu
    )
    
    # 3. Diske Kaydet
    dosya_yolu = tmp_path / f"test_e2e_{mod}.bin"
    dosya_yolu.write_bytes(ikili_veri)
    
    # 4. Ayrıştır (Parse)
    ayristirilmis = parse_encrypted_binary(str(dosya_yolu))
    
    # 5. Şifreyi Çöz (Decrypt)
    cozumlenen_duz_metin = decrypt_data(
        ayristirilmis['ciphertext'],
        ayristirilmis['nonce'],
        ayristirilmis['auth_tag'],
        aes_anahtari,
        ham_puf_anahtari,
        mode=ayristirilmis['encryption_mode'],
        expected_hmac=ayristirilmis['metadata'].get('ciphertext_hmac'),
        aad=ayristirilmis.get('aad_bytes', b''),
        metadata=ayristirilmis['metadata']
    )
    
    assert cozumlenen_duz_metin == duz_metin, "Çözümlenen metin orijinal düz metinle eşleşmiyor!"
    
    # 6. Düz Ağırlıkları Ayrıştır
    ayristirilmis_agirliklar = parse_weight_binary(cozumlenen_duz_metin)
    
    # 7. Doğrulamalar (Assertions)
    assert ayristirilmis_agirliklar['magic'] == 'CPUF'
    assert ayristirilmis_agirliklar['total_elements'] == 4
    np.testing.assert_array_equal(
        ayristirilmis_agirliklar['weight_arrays'][0],
        np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    )
