import os
import sys
import json
import struct
import hashlib
import hmac
import numpy as np
from Crypto.Cipher import AES

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crypto_utils import get_puf_key, derive_key_from_puf_simulation


def parse_encrypted_binary(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Encrypted file not found: {file_path}")
    
    file_size = os.path.getsize(file_path)
    if file_size < 20:  # Minimum valid file size
        raise ValueError(f"File too small: {file_size} bytes")
    
    if file_size > 1024 * 1024 * 1024:  # 1GB limit
        raise ValueError(f"File too large: {file_size} bytes (max 1GB)")
    
    with open(file_path, 'rb') as f:
        data = f.read()

    offset = 0

    magic = data[offset:offset + 4]
    offset += 4
    if magic != b'CPFE':
        raise ValueError(f"Gecersiz magic number: {magic}, beklenen: CPFE")

    version_major = struct.unpack('<B', data[offset:offset + 1])[0]
    offset += 1
    version_minor = struct.unpack('<B', data[offset:offset + 1])[0]
    offset += 1

    mode_byte = struct.unpack('<B', data[offset:offset + 1])[0]
    offset += 1

    if mode_byte == 0x01:
        encryption_mode = 'GCM'
    elif mode_byte == 0x02:
        encryption_mode = 'CBC'
    else:
        raise ValueError(f"Desteklenmeyen mod: 0x{mode_byte:02X}")

    kdf_mode_byte = struct.unpack('<B', data[offset:offset + 1])[0]
    offset += 1
    
    if kdf_mode_byte == 0x01:
        mac_mode = 'direct'
    elif kdf_mode_byte == 0x02:
        mac_mode = 'pbkdf2'
    else:
        mac_mode = 'unknown'

    metadata_length = struct.unpack('<I', data[offset:offset + 4])[0]
    offset += 4

    if metadata_length > 65536:
        raise ValueError(f"Metadata boyutu cok buyuk: {metadata_length} byte")

    metadata_json = data[offset:offset + metadata_length].decode('utf-8')
    metadata = json.loads(metadata_json)
    offset += metadata_length

    aad_output = bytearray()
    aad_output.extend(magic)
    aad_output.extend(struct.pack('<B', version_major))
    aad_output.extend(struct.pack('<B', version_minor))
    aad_output.extend(struct.pack('<B', mode_byte))
    aad_output.extend(struct.pack('<B', kdf_mode_byte))
    aad_bytes = bytes(aad_output)

    hmac_bytes = b''
    if encryption_mode == 'GCM' or encryption_mode == 'CBC':
        nonce_length = struct.unpack('<B', data[offset:offset + 1])[0]
        offset += 1
        
        if nonce_length < 8 or nonce_length > 32:
            raise ValueError(f"Invalid nonce length: {nonce_length} (expected 8-32)")
        
        nonce = data[offset:offset + nonce_length]
        offset += nonce_length

        if encryption_mode == 'GCM':
            tag_length = struct.unpack('<B', data[offset:offset + 1])[0]
            offset += 1
            
            if tag_length != 16:
                raise ValueError(f"Invalid GCM tag length: {tag_length} (expected 16)")
            
            auth_tag = data[offset:offset + tag_length]
            offset += tag_length
        else:
            if encryption_mode == 'CBC' and 'ciphertext_hmac' in metadata:
                hmac_length = struct.unpack('<B', data[offset:offset + 1])[0]
                offset += 1
                hmac_bytes = data[offset:offset + hmac_length]
                offset += hmac_length
            auth_tag = b''

    ciphertext_length = struct.unpack('<Q', data[offset:offset + 8])[0]
    offset += 8

    ciphertext = data[offset:offset + ciphertext_length]
    offset += ciphertext_length

    parsed = {
        'magic': magic.decode('ascii'),
        'version': f'{version_major}.{version_minor}',
        'encryption_mode': encryption_mode,
        'mac_mode': mac_mode,
        'metadata': metadata,
        'nonce': nonce,
        'auth_tag': auth_tag,
        'file_hmac_bytes': hmac_bytes,
        'ciphertext': ciphertext,
        'aad_bytes': aad_bytes,
        'total_file_size': len(data),
        'header_size': offset - len(ciphertext),
        'ciphertext_size': len(ciphertext)
    }

    return parsed


def decrypt_data(ciphertext, nonce, auth_tag, aes_key, raw_puf_key, mode='GCM', expected_hmac=None, aad=b'', metadata=None):
    if mode == 'GCM':
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        if aad:
            cipher.update(aad)
        plaintext = cipher.decrypt_and_verify(ciphertext, auth_tag)
    elif mode == 'CBC':
        import hmac
        import hashlib
        import json
        if expected_hmac is None:
            raise ValueError("HMAC verification failed! Expected HMAC is missing in CBC mode.")
            
        if metadata.get('mac_mode', 'direct') == 'pbkdf2':
            mac_salt_hex = metadata.get('mac_salt_hex')
            if not mac_salt_hex:
                raise ValueError("HMAC verification failed! mac_salt_hex is missing in metadata.")
            mac_salt = bytes.fromhex(mac_salt_hex)
            mac_key = hashlib.pbkdf2_hmac('sha256', raw_puf_key, mac_salt, 600000, dklen=32)
        else:
            mac_key = raw_puf_key
        
        h = hmac.new(mac_key, digestmod=hashlib.sha256)
        h.update(aad)
        h.update(nonce)
        h.update(ciphertext)
        computed_hmac = h.hexdigest()
        
        if not hmac.compare_digest(computed_hmac, expected_hmac):
            raise ValueError("HMAC verification failed! Ciphertext has been tampered with.")
            
        from Crypto.Util.Padding import unpad
        cipher = AES.new(aes_key, AES.MODE_CBC, nonce)
        decrypted_padded = cipher.decrypt(ciphertext)
        plaintext = unpad(decrypted_padded, AES.block_size)
    else:
        raise ValueError("Desteklenmeyen mod.")

    return plaintext


def parse_weight_binary(plaintext_data):
    offset = 0

    magic = plaintext_data[offset:offset + 4]
    offset += 4
    if magic != b'CPUF':
        raise ValueError(f"Gecersiz agirlik magic number: {magic}, beklenen: CPUF")

    version_major = struct.unpack('<B', plaintext_data[offset:offset + 1])[0]
    offset += 1
    version_minor = struct.unpack('<B', plaintext_data[offset:offset + 1])[0]
    offset += 1

    quant_mode = struct.unpack('<B', plaintext_data[offset:offset + 1])[0]
    offset += 1

    total_arrays = struct.unpack('<I', plaintext_data[offset:offset + 4])[0]
    offset += 4

    if total_arrays > 1000:
        raise ValueError(f"Dizi sayisi cok buyuk: {total_arrays}")

    total_elements = struct.unpack('<Q', plaintext_data[offset:offset + 8])[0]
    offset += 8

    if total_elements > 10**8:
        raise ValueError(f"Toplam eleman sayisi cok buyuk: {total_elements}")

    reserved = plaintext_data[offset:offset + 15]
    offset += 15

    array_shapes = []
    array_sizes = []
    array_scales = []
    array_zps = []
    
    for _ in range(total_arrays):
        ndim = struct.unpack('<B', plaintext_data[offset:offset + 1])[0]
        offset += 1
        shape = []
        for _ in range(ndim):
            dim = struct.unpack('<I', plaintext_data[offset:offset + 4])[0]
            offset += 4
            shape.append(dim)
        array_shapes.append(tuple(shape))

        num_elements = struct.unpack('<I', plaintext_data[offset:offset + 4])[0]
        offset += 4
        size_bytes = struct.unpack('<I', plaintext_data[offset:offset + 4])[0]
        offset += 4
        
        scale = struct.unpack('<f', plaintext_data[offset:offset + 4])[0]
        offset += 4
        
        zp = struct.unpack('<b', plaintext_data[offset:offset + 1])[0]
        offset += 1
        
        padding = plaintext_data[offset:offset + 3]
        offset += 3
        
        array_sizes.append((num_elements, size_bytes))
        array_scales.append(scale)
        array_zps.append(zp)

    weight_arrays = []
    for i in range(total_arrays):
        num_elements = array_sizes[i][0]
        if quant_mode > 0:
            byte_count = num_elements * 1
            int8_data = np.frombuffer(
                plaintext_data,
                dtype=np.int8,
                count=num_elements,
                offset=offset
            )
            weight_array = int8_data.reshape(array_shapes[i])
        else:
            byte_count = num_elements * 4
            float_data = np.frombuffer(
                plaintext_data,
                dtype=np.float32,
                count=num_elements,
                offset=offset
            )
            weight_array = float_data.reshape(array_shapes[i])
            
        weight_arrays.append(weight_array)
        offset += byte_count

    parsed_weights = {
        'magic': magic.decode('ascii'),
        'version': f'{version_major}.{version_minor}',
        'quant_mode': quant_mode,
        'total_arrays': total_arrays,
        'total_elements': total_elements,
        'array_shapes': array_shapes,
        'array_scales': array_scales,
        'array_zps': array_zps,
        'weight_arrays': weight_arrays
    }

    return parsed_weights


def compare_with_original(decrypted_weights, original_weights_path):
    original_data = np.load(original_weights_path)

    original_arrays = [original_data[key] for key in original_data.files]
    decrypted_arrays = decrypted_weights['weight_arrays']
    quant_mode = decrypted_weights['quant_mode']
    array_scales = decrypted_weights.get('array_scales', [])

    if len(original_arrays) != len(decrypted_arrays):
        return False, f"Dizi sayisi uyusmuyor: orijinal={len(original_arrays)}, cozumlenen={len(decrypted_arrays)}"

    for i in range(len(original_arrays)):
        if original_arrays[i].shape != decrypted_arrays[i].shape:
            return False, f"Dizi {i} sekil uyusmuyor: orijinal={original_arrays[i].shape}, cozumlenen={decrypted_arrays[i].shape}"

        comp_array = decrypted_arrays[i]
        if quant_mode > 0:
            scale = array_scales[i]
            comp_array = comp_array.astype(np.float32) * scale
            max_tol = scale * 1.5
        else:
            max_tol = 1e-5

        if not np.allclose(original_arrays[i], comp_array, rtol=1e-3, atol=max_tol):
            max_diff = np.max(np.abs(original_arrays[i] - comp_array))
            return False, f"Dizi {i} deger uyusmuyor: max fark={max_diff} (tol: {max_tol})"

    if quant_mode > 0:
        return True, "Tum diziler basariyla dogrulandi (Nicemleme toleransi dahilinde)."
    return True, "Tum diziler basariyla dogrulandi."


def verify_encryption():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output')
    export_dir = os.path.join(base_dir, 'exported_weights')
    encrypt_dir = os.path.join(base_dir, 'encrypted_weights')

    encrypted_file = os.path.join(encrypt_dir, 'cyberpuf_encrypted_weights.bin')
    original_weights_bin = os.path.join(export_dir, 'cyberpuf_weights.bin')
    original_weights_npz = os.path.join(export_dir, 'numpy_weights', 'all_weights_combined.npz')

    print("=" * 70)
    print("CyberPUF - Faz 1: Uctan Uca Sifreleme Dogrulama")
    print("Gelistirici: Arda Mecik")
    print("=" * 70)

    test_results = []

    print("\n" + "-" * 70)
    print("TEST 1: Sifreli dosya yapisini ayristirma (parsing)")
    print("-" * 70)

    if not os.path.exists(encrypted_file):
        raise FileNotFoundError(f"HATA: Sifreli dosya bulunamadi: {encrypted_file}\nLutfen once encrypt_weights.py betigini calistirin.")

    try:
        parsed = parse_encrypted_binary(encrypted_file)
        print(f"  Magic Number     : {parsed['magic']}")
        print(f"  Versiyon         : {parsed['version']}")
        print(f"  Sifreleme Modu   : {parsed['encryption_mode']} (KDF: {parsed.get('mac_mode', 'unknown')})")
        print(f"  Dosya Boyutu     : {parsed['total_file_size']:,} byte")
        print(f"  Header Boyutu    : {parsed['header_size']:,} byte")
        print(f"  Sifreli Boyut    : {parsed['ciphertext_size']:,} byte")
        print(f"  Nonce Uzunlugu   : {len(parsed['nonce'])} byte")
        if parsed['auth_tag']:
            print(f"  Auth Tag Uzunlugu: {len(parsed['auth_tag'])} byte")
        print(f"  SONUC: BASARILI")
        test_results.append(('Dosya Ayristirma', True, 'Basarili'))
    except Exception as e:
        print(f"  SONUC: BASARISIZ - {str(e)}")
        test_results.append(('Dosya Ayristirma', False, str(e)))
        raise RuntimeError("Dosya ayristirma hatasi") from e

    print("\n" + "-" * 70)
    print("TEST 2: AES-256 Sifre Cozumleme (Decryption)")
    print("-" * 70)

    try:
        raw_puf_key = get_puf_key()
        salt = bytes.fromhex(parsed['metadata']['salt_hex'])
        aes_key, _ = derive_key_from_puf_simulation(raw_puf_key, salt)
        print(f"  Anahtar parmak izi: {hashlib.sha256(aes_key).hexdigest()[:16]}...")

        decrypted_data = decrypt_data(
            parsed['ciphertext'],
            parsed['nonce'],
            parsed['auth_tag'],
            aes_key,
            raw_puf_key,
            mode=parsed['encryption_mode'],
            expected_hmac=parsed['metadata'].get('ciphertext_hmac'),
            aad=parsed.get('aad_bytes', b''),
            metadata=parsed['metadata']
        )
        print(f"  Cozumlenen boyut : {len(decrypted_data):,} byte")
        print(f"  SONUC: BASARILI")
        test_results.append(('AES Sifre Cozme', True, 'Basarili'))
    except Exception as e:
        print(f"  SONUC: BASARISIZ - {str(e)}")
        test_results.append(('AES Sifre Cozme', False, str(e)))
        raise RuntimeError("Sifre cozme hatasi") from e

    print("\n" + "-" * 70)
    print("TEST 3: Orijinal ikili veri ile karsilastirma")
    print("-" * 70)

    original_binary = None
    if os.path.exists(original_weights_bin):
        with open(original_weights_bin, 'rb') as f:
            original_binary = f.read()

        if decrypted_data == original_binary:
            print(f"  Orijinal boyut   : {len(original_binary):,} byte")
            print(f"  Cozumlenen boyut : {len(decrypted_data):,} byte")
            print(f"  Byte-byte eslesme: EVET")
            print(f"  SONUC: BASARILI")
            test_results.append(('Ikili Veri Kiyaslamasi', True, 'Byte-byte eslesme'))
        else:
            print(f"  SONUC: BASARISIZ - Veriler eslesmedi")
            test_results.append(('Ikili Veri Kiyaslamasi', False, 'Veriler eslesmedi'))
    else:
        print(f"  ATLANDI: Orijinal dosya bulunamadi: {original_weights_bin}")
        test_results.append(('Ikili Veri Kiyaslamasi', None, 'Orijinal dosya bulunamadi'))

    print("\n" + "-" * 70)
    print("TEST 4: Agirlik dizilerini ayristirma ve dogrulama")
    print("-" * 70)

    try:
        decrypted_weights = parse_weight_binary(decrypted_data)
        print(f"  Magic Number     : {decrypted_weights['magic']}")
        print(f"  Versiyon         : {decrypted_weights['version']}")
        print(f"  Toplam dizi      : {decrypted_weights['total_arrays']}")
        print(f"  Toplam eleman    : {decrypted_weights['total_elements']:,}")

        for i, (shape, arr) in enumerate(zip(decrypted_weights['array_shapes'], decrypted_weights['weight_arrays'])):
            print(f"  Dizi {i:3d}: Sekil={str(shape):25s} | Min={np.min(arr):+.6f} | Max={np.max(arr):+.6f} | Mean={np.mean(arr):+.6f}")

        print(f"  SONUC: BASARILI")
        test_results.append(('Agirlik Ayristirmasi', True, 'Basarili'))
    except Exception as e:
        print(f"  SONUC: BASARISIZ - {str(e)}")
        test_results.append(('Agirlik Ayristirmasi', False, str(e)))

    print("\n" + "-" * 70)
    print("TEST 5: NumPy orijinal agirliklarla karsilastirma")
    print("-" * 70)

    if os.path.exists(original_weights_npz):
        try:
            match_result, match_message = compare_with_original(
                decrypted_weights, original_weights_npz
            )
            if match_result:
                print(f"  Karsilastirma    : {match_message}")
                print(f"  SONUC: BASARILI")
                test_results.append(('NumPy Kiyaslamasi', True, match_message))
            else:
                print(f"  Karsilastirma    : {match_message}")
                print(f"  SONUC: BASARISIZ")
                test_results.append(('NumPy Kiyaslamasi', False, match_message))
        except Exception as e:
            print(f"  SONUC: BASARISIZ - {str(e)}")
            test_results.append(('NumPy Kiyaslamasi', False, str(e)))
    else:
        print(f"  ATLANDI: NPZ dosyasi bulunamadi: {original_weights_npz}")
        test_results.append(('NumPy Kiyaslamasi', None, 'NPZ dosyasi bulunamadi'))

    print("\n" + "-" * 70)
    print("TEST 6: SHA-256 butunluk kontrolu")
    print("-" * 70)

    decrypted_sha256 = hashlib.sha256(decrypted_data).hexdigest()
    original_sha256 = hashlib.sha256(original_binary).hexdigest() if original_binary is not None else 'N/A'

    print(f"  Cozumlenen SHA-256 : {decrypted_sha256}")
    print(f"  Orijinal SHA-256   : {original_sha256}")

    if decrypted_sha256 == original_sha256:
        print(f"  Hash eslesmesi     : EVET")
        print(f"  SONUC: BASARILI")
        test_results.append(('SHA-256 Butunluk Kontrolu', True, 'Hash eslesti'))
    elif original_sha256 == 'N/A':
        print(f"  ATLANDI: Orijinal dosya yok")
        test_results.append(('SHA-256 Butunluk Kontrolu', None, 'Orijinal dosya yok'))
    else:
        print(f"  Hash eslesmesi     : HAYIR")
        print(f"  SONUC: BASARISIZ")
        test_results.append(('SHA-256 Butunluk Kontrolu', False, 'Hash eslesmedi'))

    print("\n" + "-" * 70)
    print("TEST 7: Yanlis anahtar ile cozumleme testi (negatif test)")
    print("-" * 70)

    wrong_key = bytes([0xFF] * 32)
    wrong_puf_key = bytes([0xAA] * 32)

    try:
        wrong_decrypted = decrypt_data(
            parsed['ciphertext'],
            parsed['nonce'],
            parsed['auth_tag'],
            wrong_key,
            wrong_puf_key,
            mode=parsed['encryption_mode'],
            expected_hmac=parsed['metadata'].get('ciphertext_hmac'),
            aad=parsed.get('aad_bytes', b''),
            metadata=parsed['metadata']
        )
        print(f"  SONUC: BASARISIZ - Yanlis anahtar ile cozumleme basarili olmamali!")
        test_results.append(('Yanlis Anahtar Testi', False, 'Yanlis anahtar kabul edildi'))
    except Exception as e:
        print(f"  Yanlis anahtar ile cozumleme beklendigi gibi basarisiz oldu.")
        print(f"  Hata mesaji: {type(e).__name__}")
        print(f"  SONUC: BASARILI (beklenen davranis)")
        test_results.append(('Yanlis Anahtar Testi', True, 'Yanlis anahtar reddedildi'))

    print("\n" + "-" * 70)
    print("TEST 8: Bozulmus veri ile cozumleme testi (tamper detection)")
    print("-" * 70)

    tampered_ciphertext = bytearray(parsed['ciphertext'])
    tampered_ciphertext[0] ^= 0xFF
    tampered_ciphertext = bytes(tampered_ciphertext)

    try:
        tampered_decrypted = decrypt_data(
            tampered_ciphertext,
            parsed['nonce'],
            parsed['auth_tag'],
            aes_key,
            raw_puf_key,
            mode=parsed['encryption_mode'],
            expected_hmac=parsed['metadata'].get('ciphertext_hmac'),
            aad=parsed.get('aad_bytes', b''),
            metadata=parsed['metadata']
        )
        
        # HMAC varsa zafiyet zaten ustte patlar ve asagiya inmez.
                
        print(f"  SONUC: BASARISIZ - Bozulmus veri tespit edilemedi!")
        test_results.append(('Dis Mudahale Tespiti', False, 'Bozulma fark edilmedi'))
    except Exception as e:
        print(f"  Bozulmus veri beklendigi gibi tespit edildi.")
        print(f"  Hata mesaji: {type(e).__name__}")
        print(f"  SONUC: BASARILI (beklenen davranis)")
        test_results.append(('Dis Mudahale Tespiti', True, 'Bozulma tespit edildi'))

    print("\n" + "=" * 70)
    print("DOGRULAMA SONUC OZETI")
    print("=" * 70)

    passed = 0
    failed = 0
    skipped = 0

    for test_name, result, message in test_results:
        if result is True:
            status = "BASARILI"
            passed += 1
        elif result is False:
            status = "BASARISIZ"
            failed += 1
        else:
            status = "ATLANDI"
            skipped += 1
        print(f"  {test_name:30s} : {status:10s} | {message}")

    print("-" * 70)
    print(f"  Toplam: {len(test_results)} test | Basarili: {passed} | Basarisiz: {failed} | Atlanan: {skipped}")

    if failed == 0:
        print("\n  GENEL SONUC: TUM TESTLER BASARILI")
    else:
        print(f"\n  GENEL SONUC: {failed} TEST BASARISIZ OLDU")

    print("=" * 70)
    print("FAZ 1 TAMAMLANDI: Egitim -> Disa Aktarma -> Sifreleme -> Dogrulama")
    print("Sonraki faz: Faz 2 - FPGA uzerinde RO-PUF ve AES-256 donanim modulleri")
    print("=" * 70)

    verification_report = {
        'project': 'CyberPUF',
        'developer': 'Arda Mecik',
        'phase': 'Faz 1 - End-to-End Verification',
        'tests': [
            {
                'name': name,
                'passed': result,
                'message': msg
            }
            for name, result, msg in test_results
        ],
        'summary': {
            'total': len(test_results),
            'passed': passed,
            'failed': failed,
            'skipped': skipped
        }
    }

    report_path = os.path.join(encrypt_dir, 'verification_report.json')
    with open(report_path, 'w') as f:
        json.dump(verification_report, f, indent=2)
    print(f"\nDogrulama raporu kaydedildi: {report_path}")

    return failed == 0


if __name__ == '__main__':
    success = verify_encryption()
    sys.exit(0 if success else 1)
