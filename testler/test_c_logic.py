import os
import struct
import json
import hashlib
import hmac

def sim_CPFE_Header_Oku(tampon):
    offset = 0
    if len(tampon) < 8: return None
    
    magic = tampon[offset:offset+4]
    if magic != b'CPFE': return None
    offset += 4
    
    offset += 2 # version
    mode = tampon[offset]
    offset += 1
    kdf_mode = tampon[offset]
    offset += 1
    
    metadata_boyutu = struct.unpack('<I', tampon[offset:offset+4])[0]
    offset += 4
    
    beklenen_hmac = b""
    metadata_bytes = tampon[offset:offset+metadata_boyutu]
    try:
        # Simulate simple search
        meta_str = metadata_bytes.decode('utf-8')
        idx = meta_str.find('"ciphertext_hmac": "')
        if idx != -1:
            start_idx = idx + 20
            hmac_str = meta_str[start_idx:start_idx+64]
            beklenen_hmac = bytes.fromhex(hmac_str)
    except:
        pass
        
    offset += metadata_boyutu
    
    nonce_len = tampon[offset]
    offset += 1
    nonce = tampon[offset:offset+nonce_len]
    offset += nonce_len
    
    if mode == 0x01: # GCM
        tag_len = tampon[offset]
        offset += 1
        offset += tag_len
    elif mode == 0x02: # CBC
        if beklenen_hmac:
            hmac_len = tampon[offset]
            offset += 1
            offset += hmac_len
            
    ciphertext_len = struct.unpack('<Q', tampon[offset:offset+8])[0]
    offset += 8
    
    return {
        'offset': offset,
        'nonce': nonce,
        'kdf_mode': kdf_mode,
        'beklenen_hmac': beklenen_hmac,
        'metadata_boyutu': metadata_boyutu,
        'ciphertext_len': ciphertext_len
    }

def test_embedded_c_logic():
    print("--- Gömülü C Parse Simülasyon Testi ---")
    
    # Run test from the ai_sifreleme directory context because we need crypto_utils
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ai_sifreleme'))
    from crypto_utils import get_puf_key
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    bin_path = os.path.join("output", "encrypted_weights", "cyberpuf_encrypted_weights.bin")
    if not os.path.exists(bin_path):
        print("Sifreli dosya yok.")
        return
        
    with open(bin_path, 'rb') as f:
        tampon = f.read()
        
    res = sim_CPFE_Header_Oku(tampon)
    if not res:
        print("HATA: Header okunamadi.")
        return
        
    print(f"Header basariyla ayristirildi. Offset: {res['offset']}")
    print(f"KDF Modu: {res['kdf_mode']}")
    print(f"Beklenen HMAC: {res['beklenen_hmac'].hex()}")
    
    if res['kdf_mode'] == 0x02:
        print("HATA: PBKDF2 modu bare-metal'de desteklenmiyor.")
        return
        
    gercek_anahtar_cikarim = get_puf_key()
    
    aad_len = 8
    aad = tampon[0:aad_len]
    
    ciphertext = tampon[res['offset'] : res['offset'] + res['ciphertext_len']]
    
    h = hmac.new(gercek_anahtar_cikarim, digestmod=hashlib.sha256)
    h.update(aad)
    h.update(res['nonce'])
    h.update(ciphertext)
    hesaplanan_mac = h.digest()
    
    print(f"Hesaplanan HMAC: {hesaplanan_mac.hex()}")
    
    if hesaplanan_mac == res['beklenen_hmac']:
        print("BASARILI: Gömülü C Mantığı ile HMAC Birebir Eşleşti!")
    else:
        print("HATA: HMAC Eslesmedi!")
        exit(1)

if __name__ == "__main__":
    test_embedded_c_logic()
