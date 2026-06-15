import pytest
import os
import secrets
from ai_sifreleme.crypto_utils import derive_key_from_puf_simulation

def sahte_puf_anahtari_uret():
    """
    Kriptografik olarak güvenli 256-bit (32 byte) sahte bir PUF anahtarı üretir.
    Bu, Halka Osilatör (Ring Oscillator) PUF donanım modülünden gelen ham yanıtı simüle eder.
    """
    return secrets.token_bytes(32)

def byte_dizisine_gurultu_ekle(veri: bytes, bit_cevirme_sayisi: int = 1) -> bytes:
    """
    Byte dizisindeki rastgele bitleri çevirerek PUF donanımındaki fiziksel 
    çevresel gürültüyü (sıcaklık, voltaj değişimleri) simüle eder.
    
    Argümanlar:
        veri: Orijinal byte dizisi (Ham PUF Anahtarı)
        bit_cevirme_sayisi: Çevrilecek rastgele bit sayısı (Gürültü Seviyesi)
    
    Döndürür:
        Belirtilen gürültünün uygulandığı yeni byte dizisi.
    """
    degistirilebilir_veri = bytearray(veri)
    for _ in range(bit_cevirme_sayisi):
        byte_indeksi = secrets.randbelow(len(degistirilebilir_veri))
        bit_indeksi = secrets.randbelow(8)
        degistirilebilir_veri[byte_indeksi] ^= (1 << bit_indeksi)
    return bytes(degistirilebilir_veri)

@pytest.mark.parametrize("bit_cevirme_sayisi", [1, 2, 5, 10, 128])
def test_puf_gurultusu_anahtar_uyusmazligi_yaratir(bit_cevirme_sayisi):
    """
    PUF anahtarındaki HERHANGİ BİR seviyedeki gürültünün (tek bir bit değişimi bile olsa),
    çığ etkisi (avalanche effect) nedeniyle PBKDF2 (veya herhangi bir kriptografik türetme fonksiyonu) 
    tarafından tamamen farklı bir AES anahtarı üretilmesine neden olduğunu test eder.
    
    Bu test, Gömülü C donanım katmanının anahtarı AES veya PBKDF2 motorlarına beslemeden önce 
    PUF hatalarını düzeltmek için neden bir Fuzzy Extractor'a (Hata Düzelticiye) 
    MUTLAKA sahip olması gerektiğini ampirik olarak kanıtlar.
    """
    orijinal_puf_anahtari = sahte_puf_anahtari_uret()
    
    # 1. Temiz PUF anahtarını kullanarak temel AES anahtarını türet
    temiz_aes_anahtari, salt = derive_key_from_puf_simulation(orijinal_puf_anahtari)
    
    # 2. PUF anahtarına çevresel gürültü (bit değişimleri) enjekte et
    gurultulu_puf_anahtari = byte_dizisine_gurultu_ekle(orijinal_puf_anahtari, bit_cevirme_sayisi=bit_cevirme_sayisi)
    
    # Gürültünün gerçekten enjekte edildiğini doğrula
    assert orijinal_puf_anahtari != gurultulu_puf_anahtari, "Gürültülü anahtar orijinaliyle eşleşmemeli"
    
    # 3. Gürültülü PUF anahtarını ve birebir AYNI salt (tuz) değerini kullanarak anahtarı yeniden türetmeyi dene
    gurultulu_aes_anahtari, _ = derive_key_from_puf_simulation(gurultulu_puf_anahtari, salt=salt)
    
    # 4. Türetilen AES anahtarları tamamen farklı olmalıdır.
    assert temiz_aes_anahtari != gurultulu_aes_anahtari, (
        f"{bit_cevirme_sayisi} bitlik PUF gürültüsüne rağmen türetilen anahtarlar eşleşti! "
        "Bu, türetme fonksiyonunda ciddi bir kriptografik güvenlik açığına işaret eder."
    )
    
def test_gurultusuz_puf_tutarliligi():
    """
    Temel kriptografik tutarlılığı test eder:
    Donanımdaki Fuzzy Extractor tüm çevresel gürültüyü başarıyla temizler ve 
    orijinal PUF anahtarını tam olarak yeniden oluşturursa, PBKDF2 türetme fonksiyonu 
    şifre çözmeye izin verecek şekilde tutarlı olarak birebir aynı AES anahtarını üretmelidir.
    """
    orijinal_puf_anahtari = sahte_puf_anahtari_uret()
    
    # İlk aşama: Şifreleme
    aes_anahtari_sifreleme, salt = derive_key_from_puf_simulation(orijinal_puf_anahtari)
    
    # İkinci aşama: Şifre Çözme (meta verilerden alınan aynı salt değeri kullanılarak)
    aes_anahtari_cozumleme, _ = derive_key_from_puf_simulation(orijinal_puf_anahtari, salt=salt)
    
    assert aes_anahtari_sifreleme == aes_anahtari_cozumleme, (
        "Tutarlı PUF anahtarları, aynı salt kullanıldığında aynı AES anahtarlarını üretmelidir."
    )
