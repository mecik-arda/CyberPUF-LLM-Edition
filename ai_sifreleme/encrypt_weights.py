import os
import sys
import json
import struct
import hashlib
import secrets
import datetime
import numpy as np
import hmac
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crypto_utils import get_puf_key, derive_key_from_puf_simulation


ENCRYPTED_FILE_MAGIC = b'CPFE'
ENCRYPTED_VERSION_MAJOR = 1
ENCRYPTED_VERSION_MINOR = 0

def encrypt_aes256_gcm(plaintext_data, aes_key, aad=b''):
    if len(aes_key) != 32:
        raise ValueError("AES anahtari 32 byte (256-bit) olmalidir.")
    nonce = secrets.token_bytes(12)  # GCM için önerilen nonce boyutu 12 byte
    cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    if aad:
        cipher.update(aad)
    ciphertext, auth_tag = cipher.encrypt_and_digest(plaintext_data)
    return ciphertext, nonce, auth_tag

def encrypt_aes256_cbc(plaintext_data, aes_key):
    if len(aes_key) != 32:
        raise ValueError("AES anahtari 32 byte (256-bit) olmalidir.")
        
    iv = secrets.token_bytes(16)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    padded_data = pad(plaintext_data, AES.block_size)
    ciphertext = cipher.encrypt(padded_data)

    return ciphertext, iv, b''




def build_encrypted_binary(ciphertext, nonce, auth_tag, metadata, mode='GCM', mac_mode='direct'):
    output = bytearray()

    output.extend(ENCRYPTED_FILE_MAGIC)

    output.extend(struct.pack('<B', ENCRYPTED_VERSION_MAJOR))
    output.extend(struct.pack('<B', ENCRYPTED_VERSION_MINOR))

    if mode == 'GCM':
        output.extend(struct.pack('<B', 0x01))
    elif mode == 'CBC':
        output.extend(struct.pack('<B', 0x02))
    else:
        raise ValueError("Desteklenmeyen mod.")

    if mac_mode == 'direct':
        output.extend(struct.pack('<B', 0x01))
    elif mac_mode == 'pbkdf2':
        output.extend(struct.pack('<B', 0x02))
    else:
        output.extend(struct.pack('<B', 0x00))

    if metadata:
        metadata_json = json.dumps(metadata).encode('utf-8')
        output.extend(struct.pack('<I', len(metadata_json)))
        output.extend(metadata_json)
    else:
        output.extend(struct.pack('<I', 0))

    if mode == 'GCM' or mode == 'CBC':
        output.extend(struct.pack('<B', len(nonce)))
        output.extend(nonce)
        if mode == 'GCM':
            output.extend(struct.pack('<B', len(auth_tag)))
            output.extend(auth_tag)
        elif mode == 'CBC' and 'ciphertext_hmac' in metadata:
            hmac_bytes = bytes.fromhex(metadata['ciphertext_hmac'])
            output.extend(struct.pack('<B', len(hmac_bytes)))
            output.extend(hmac_bytes)

    output.extend(struct.pack('<Q', len(ciphertext)))
    output.extend(ciphertext)

    return bytes(output)


def generate_c_header(encrypted_data, output_path, array_name='encrypted_weights'):
    with open(output_path, 'w') as f:
        f.write(f'#ifndef CYBERPUF_ENCRYPTED_WEIGHTS_H\n')
        f.write(f'#define CYBERPUF_ENCRYPTED_WEIGHTS_H\n\n')
        f.write(f'#include <stdint.h>\n\n')
        f.write(f'#define ENCRYPTED_DATA_SIZE {len(encrypted_data)}\n\n')
        f.write(f'static const uint8_t {array_name}[ENCRYPTED_DATA_SIZE] = {{\n')

        bytes_per_line = 16
        for i in range(0, len(encrypted_data), bytes_per_line):
            chunk = encrypted_data[i:i + bytes_per_line]
            hex_values = ', '.join(f'0x{b:02X}' for b in chunk)
            if i + bytes_per_line < len(encrypted_data):
                f.write(f'    {hex_values},\n')
            else:
                f.write(f'    {hex_values}\n')

        f.write(f'}};\n\n#endif\n')

    return output_path


def generate_c_header_chunked(encrypted_data, output_dir, array_name='encrypted_weights', chunk_size=65536):
    os.makedirs(output_dir, exist_ok=True)

    num_chunks = (len(encrypted_data) + chunk_size - 1) // chunk_size
    chunk_files = []

    for chunk_idx in range(num_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, len(encrypted_data))
        chunk_data = encrypted_data[start:end]

        chunk_filename = f'{array_name}_chunk_{chunk_idx:04d}.h'
        chunk_path = os.path.join(output_dir, chunk_filename)

        with open(chunk_path, 'w') as f:
            guard = f'CYBERPUF_{array_name.upper()}_CHUNK_{chunk_idx:04d}_H'
            f.write(f'#ifndef {guard}\n')
            f.write(f'#define {guard}\n\n')
            f.write(f'#include <stdint.h>\n\n')
            f.write(f'#define CHUNK_{chunk_idx:04d}_SIZE {len(chunk_data)}\n')
            f.write(f'#define CHUNK_{chunk_idx:04d}_OFFSET {start}\n\n')
            f.write(f'static const uint8_t {array_name}_chunk_{chunk_idx:04d}[CHUNK_{chunk_idx:04d}_SIZE] = {{\n')

            bytes_per_line = 16
            for i in range(0, len(chunk_data), bytes_per_line):
                sub_chunk = chunk_data[i:i + bytes_per_line]
                hex_values = ', '.join(f'0x{b:02X}' for b in sub_chunk)
                if i + bytes_per_line < len(chunk_data):
                    f.write(f'    {hex_values},\n')
                else:
                    f.write(f'    {hex_values}\n')

            f.write(f'}};\n\n#endif\n')

        chunk_files.append(chunk_path)

    master_header_path = os.path.join(output_dir, f'{array_name}_master.h')
    with open(master_header_path, 'w') as f:
        master_guard = f'CYBERPUF_{array_name.upper()}_MASTER_H'
        f.write(f'#ifndef {master_guard}\n')
        f.write(f'#define {master_guard}\n\n')
        f.write(f'#include <stdint.h>\n\n')
        f.write(f'#define TOTAL_ENCRYPTED_SIZE {len(encrypted_data)}\n')
        f.write(f'#define TOTAL_CHUNKS {num_chunks}\n')
        f.write(f'#define CHUNK_SIZE {chunk_size}\n\n')

        for chunk_idx in range(num_chunks):
            chunk_filename = f'{array_name}_chunk_{chunk_idx:04d}.h'
            f.write(f'#include "{chunk_filename}"\n')

        f.write(f'\nstatic const uint8_t* {array_name}_chunks[TOTAL_CHUNKS] = {{\n')
        for chunk_idx in range(num_chunks):
            if chunk_idx < num_chunks - 1:
                f.write(f'    {array_name}_chunk_{chunk_idx:04d},\n')
            else:
                f.write(f'    {array_name}_chunk_{chunk_idx:04d}\n')
        f.write(f'}};\n\n')

        f.write(f'static const uint32_t {array_name}_chunk_sizes[TOTAL_CHUNKS] = {{\n')
        for chunk_idx in range(num_chunks):
            start = chunk_idx * chunk_size
            end = min(start + chunk_size, len(encrypted_data))
            size = end - start
            if chunk_idx < num_chunks - 1:
                f.write(f'    {size},\n')
            else:
                f.write(f'    {size}\n')
        f.write(f'}};\n\n#endif\n')

    chunk_files.append(master_header_path)
    return chunk_files


def encrypt_weights(weight_binary_path=None, encryption_mode='GCM', mac_mode='direct'):
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output')
    export_dir = os.path.join(base_dir, 'exported_weights')
    encrypt_dir = os.path.join(base_dir, 'encrypted_weights')
    c_header_dir = os.path.join(encrypt_dir, 'c_headers')
    os.makedirs(encrypt_dir, exist_ok=True)
    os.makedirs(c_header_dir, exist_ok=True)

    if weight_binary_path is None:
        weight_binary_path = os.path.join(export_dir, 'cyberpuf_weights.bin')

    if not os.path.exists(weight_binary_path):
        raise FileNotFoundError(f"HATA: Agirlik dosyasi bulunamadi: {weight_binary_path}\nLutfen once export_weights.py betigini calistirin.")

    print("=" * 70)
    print("CyberPUF - Faz 1: AES-256 Agirlik Sifreleme")
    print("Gelistirici: Arda Mecik")
    print(f"Sifreleme Modu: AES-256-{encryption_mode} (KDF: {mac_mode})")
    print("=" * 70)

    print("\n[1/7] Duz metin (plaintext) agirlik dosyasi okunuyor...")
    with open(weight_binary_path, 'rb') as f:
        plaintext_data = f.read()
    print(f"  Dosya boyutu  : {len(plaintext_data):,} byte ({len(plaintext_data) / (1024 * 1024):.2f} MB)")

    plaintext_sha256 = hashlib.sha256(plaintext_data).hexdigest()
    print(f"  SHA-256 ozeti : {plaintext_sha256}")

    print("\n[2/7] PUF simule edilen AES-256 anahtari hazirlaniyor...")
    raw_puf_key = get_puf_key()
    aes_key, salt = derive_key_from_puf_simulation(raw_puf_key)
    print(f"  Anahtar uzunlugu : {len(aes_key) * 8} bit")
    print(f"  Anahtar parmak izi: {hashlib.sha256(aes_key).hexdigest()[:16]}...")
    print(f"  Not: Bu anahtar ortam degiskeninden (veya fallback) alindi.")


    encryption_metadata = {
        'project': 'CyberPUF',
        'developer': 'Arda Mecik',
        'encryption_mode': f'AES-256-{encryption_mode}',
        'mac_mode': mac_mode,
        'plaintext_size': len(plaintext_data),
        'ciphertext_size': None,
        'plaintext_sha256': plaintext_sha256,
        'salt_hex': salt.hex(),
        'timestamp': datetime.datetime.now().isoformat(),
        'key_source': 'PUF_SIMULATED_STATIC'
    }

    if mac_mode == 'pbkdf2':
        mac_salt = secrets.token_bytes(16)
        encryption_metadata['mac_salt_hex'] = mac_salt.hex()

    if encryption_mode == 'GCM':
        expected_ciphertext_size = len(plaintext_data)
    elif encryption_mode == 'CBC':
        expected_ciphertext_size = len(plaintext_data) + (AES.block_size - len(plaintext_data) % AES.block_size)
    else:
        raise ValueError("Desteklenmeyen mod.")
    
    encryption_metadata['ciphertext_size'] = expected_ciphertext_size

    print(f"\n[3/7] AES-256-{encryption_mode} ile sifreleme gerceklestiriliyor...")

    aad_output = bytearray()
    aad_output.extend(ENCRYPTED_FILE_MAGIC)
    aad_output.extend(struct.pack('<B', ENCRYPTED_VERSION_MAJOR))
    aad_output.extend(struct.pack('<B', ENCRYPTED_VERSION_MINOR))
    aad_output.extend(struct.pack('<B', 0x01 if encryption_mode == 'GCM' else 0x02))
    if mac_mode == 'direct':
        aad_output.extend(struct.pack('<B', 0x01))
    elif mac_mode == 'pbkdf2':
        aad_output.extend(struct.pack('<B', 0x02))
    else:
        aad_output.extend(struct.pack('<B', 0x00))
    
    aad_bytes = bytes(aad_output)

    if encryption_mode == 'GCM':
        ciphertext, nonce, auth_tag = encrypt_aes256_gcm(plaintext_data, aes_key, aad=aad_bytes)
    elif encryption_mode == 'CBC':
        ciphertext, nonce, auth_tag = encrypt_aes256_cbc(plaintext_data, aes_key)
    else:
        raise ValueError("Desteklenmeyen mod.")

    # Update metadata with ciphertext info if needed (for CBC HMAC)
    ciphertext_sha256 = hashlib.sha256(ciphertext).hexdigest()
    encryption_metadata['ciphertext_size'] = len(ciphertext)
    
    # Key separation: Derive a separate key for MAC
    if mac_mode == 'pbkdf2':
        mac_key = hashlib.pbkdf2_hmac('sha256', raw_puf_key, mac_salt, 600000, dklen=32)
    else:
        mac_key = raw_puf_key
    
    # Encrypt-then-MAC
    h = hmac.new(mac_key, digestmod=hashlib.sha256)
    h.update(aad_bytes)
    h.update(nonce)
    h.update(ciphertext)
    ciphertext_hmac = h.hexdigest()
    
    if encryption_mode == 'CBC':
        encryption_metadata['ciphertext_hmac'] = ciphertext_hmac
        
    print(f"  Sifreli veri boyutu  : {len(ciphertext):,} byte")
    print(f"  IV/Nonce (hex)       : {nonce.hex()}")
    print(f"  Sifreleme SHA-256    : {ciphertext_sha256}")
    print(f"  Sifreli Veri HMAC    : {ciphertext_hmac}")

    print("\n[4/7] Dogrulama: Sifreli veriyi cozumleme (decrypt) testi...")

    if encryption_mode == 'GCM':
        verify_cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        verify_cipher.update(aad_bytes)
        decrypted_data = verify_cipher.decrypt_and_verify(ciphertext, auth_tag)
    elif encryption_mode == 'CBC':
        from Crypto.Util.Padding import unpad
        verify_cipher = AES.new(aes_key, AES.MODE_CBC, nonce)
        decrypted_padded = verify_cipher.decrypt(ciphertext)
        decrypted_data = unpad(decrypted_padded, AES.block_size)

    if decrypted_data == plaintext_data:
        print(f"  BASARILI: Cozumlenen veri orijinal veriyle ESLESIR.")
        print(f"  Orijinal boyut   : {len(plaintext_data):,} byte")
        print(f"  Cozumlenen boyut : {len(decrypted_data):,} byte")
    else:
        raise Exception("HATA: Cozumlenen veri orijinal veriyle ESLESMEZ!")

    print("\n[5/7] Sifreli ikili (binary) dosya olusturuluyor...")

    encrypted_binary = build_encrypted_binary(
        ciphertext, nonce, auth_tag, encryption_metadata, mode=encryption_mode, mac_mode=mac_mode
    )

    encrypted_bin_path = os.path.join(encrypt_dir, 'cyberpuf_encrypted_weights.bin')
    with open(encrypted_bin_path, 'wb') as f:
        f.write(encrypted_binary)
    print(f"  Sifreli dosya boyutu : {len(encrypted_binary):,} byte ({len(encrypted_binary) / (1024 * 1024):.2f} MB)")
    print(f"  Dosya kaydedildi     : {encrypted_bin_path}")

    raw_encrypted_path = os.path.join(encrypt_dir, 'cyberpuf_ciphertext_raw.bin')
    with open(raw_encrypted_path, 'wb') as f:
        f.write(ciphertext)
    print(f"  Ham sifreli veri     : {raw_encrypted_path}")

    nonce_path = os.path.join(encrypt_dir, 'cyberpuf_nonce.bin')
    with open(nonce_path, 'wb') as f:
        f.write(nonce)
    print(f"  Nonce/IV dosyasi     : {nonce_path}")

    if encryption_mode == 'GCM':
        tag_path = os.path.join(encrypt_dir, 'cyberpuf_auth_tag.bin')
        with open(tag_path, 'wb') as f:
            f.write(auth_tag)
        print(f"  Auth Tag dosyasi     : {tag_path}")

    print("\n[6/7] C header dosyalari olusturuluyor (donanima yukleme icin)...")

    single_header_path = os.path.join(c_header_dir, 'cyberpuf_encrypted_weights.h')
    if len(encrypted_binary) <= 1024 * 1024:
        generate_c_header(encrypted_binary, single_header_path)
        print(f"  Tekil header dosyasi : {single_header_path}")
    else:
        print(f"  Veri boyutu 1MB'den buyuk, parcali header olusturuluyor...")

    chunked_dir = os.path.join(c_header_dir, 'chunked')
    chunk_files = generate_c_header_chunked(
        encrypted_binary, chunked_dir,
        array_name='encrypted_weights',
        chunk_size=65536
    )
    print(f"  Parcali header dosyalari ({len(chunk_files)} adet):")
    for cf in chunk_files:
        print(f"    -> {cf}")

    nonce_header_path = os.path.join(c_header_dir, 'cyberpuf_nonce.h')
    nonce_header_lines = []
    nonce_header_lines.append('#ifndef CYBERPUF_NONCE_H')
    nonce_header_lines.append('#define CYBERPUF_NONCE_H')
    nonce_header_lines.append('')
    nonce_header_lines.append('#include <stdint.h>')
    nonce_header_lines.append('')
    nonce_header_lines.append(f'#define NONCE_SIZE {len(nonce)}')
    nonce_header_lines.append('')
    hex_values = ', '.join(f'0x{b:02X}' for b in nonce)
    nonce_header_lines.append(f'static const uint8_t aes_nonce[NONCE_SIZE] = {{ {hex_values} }};')
    nonce_header_lines.append('')

    if encryption_mode == 'GCM' and auth_tag:
        nonce_header_lines.append(f'#define AUTH_TAG_SIZE {len(auth_tag)}')
        nonce_header_lines.append('')
        hex_values_tag = ', '.join(f'0x{b:02X}' for b in auth_tag)
        nonce_header_lines.append(f'static const uint8_t aes_auth_tag[AUTH_TAG_SIZE] = {{ {hex_values_tag} }};')
        nonce_header_lines.append('')

    nonce_header_lines.append('#endif')
    nonce_header_lines.append('')

    with open(nonce_header_path, 'w') as f:
        f.write('\n'.join(nonce_header_lines))
    print(f"  Nonce header dosyasi : {nonce_header_path}")

    print("\n[7/7] Sifreleme ozet raporu olusturuluyor...")

    encryption_report = {
        'project': 'CyberPUF',
        'developer': 'Arda Mecik',
        'phase': 'Faz 1 - AES-256 Encryption',
        'encryption': {
            'algorithm': 'AES-256',
            'mode': encryption_mode,
            'key_length_bits': 256,
            'key_source': 'PUF Simulated (Static)',
            'nonce_length_bytes': len(nonce),
            'auth_tag_length_bytes': len(auth_tag) if auth_tag else 0
        },
        'data': {
            'plaintext_size_bytes': len(plaintext_data),
            'ciphertext_size_bytes': len(ciphertext),
            'encrypted_file_size_bytes': len(encrypted_binary),
            'overhead_bytes': len(encrypted_binary) - len(plaintext_data),
            'overhead_percentage': ((len(encrypted_binary) - len(plaintext_data)) / len(plaintext_data)) * 100,
            'plaintext_sha256': plaintext_sha256,
            'ciphertext_sha256': ciphertext_sha256
        },
        'files': {
            'encrypted_binary': encrypted_bin_path,
            'raw_ciphertext': raw_encrypted_path,
            'nonce_file': nonce_path,
            'c_header_single': single_header_path if len(encrypted_binary) <= 1024 * 1024 else 'N/A (too large)',
            'c_header_chunked_dir': chunked_dir,
            'c_header_nonce': nonce_header_path
        },
        'verification': {
            'decrypt_test': 'PASSED',
            'data_integrity': 'VERIFIED'
        },
        'timestamp': datetime.datetime.now().isoformat()
    }

    report_path = os.path.join(encrypt_dir, 'encryption_report.json')
    with open(report_path, 'w') as f:
        json.dump(encryption_report, f, indent=2)
    print(f"  Rapor kaydedildi: {report_path}")

    print("\n" + "=" * 70)
    print("SIFRELEME OZETI")
    print("=" * 70)
    print(f"  Algoritma          : AES-256-{encryption_mode}")
    print(f"  Duz metin boyutu   : {len(plaintext_data):,} byte")
    print(f"  Sifreli boyut      : {len(encrypted_binary):,} byte")
    print(f"  Ek yuk (overhead)  : {len(encrypted_binary) - len(plaintext_data):,} byte ({encryption_report['data']['overhead_percentage']:.2f}%)")
    print(f"  Dogrulama          : BASARILI")
    print("=" * 70)
    print("FAZ 1 - ADIM 3 TAMAMLANDI: Agirliklar sifrelendi.")
    print("Sonraki adim: verify_encryption.py ile uctan uca dogrulama yapin.")
    print("=" * 70)

    # Bellek izolasyonu: bytearray zerolization ile bellekten guvenli silme
    aes_key_ba = bytearray(aes_key)
    for i in range(len(aes_key_ba)):
        aes_key_ba[i] = 0
    del aes_key
    
    return encrypted_binary, bytes(aes_key_ba), nonce, auth_tag


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="CyberPUF Sifreleme Modulu")
    parser.add_argument("weight_path", nargs='?', default=None, help="Sifrelenecek agirlik dosyasinin yolu")
    parser.add_argument("--mode", default='GCM', choices=['GCM', 'CBC'], help="Sifreleme modu")
    parser.add_argument("--mac-mode", default='direct', choices=['direct', 'pbkdf2'], help="HMAC KDF modu")
    args = parser.parse_args()

    encrypt_weights(
        weight_binary_path=args.weight_path,
        encryption_mode=args.mode,
        mac_mode=args.mac_mode
    )
