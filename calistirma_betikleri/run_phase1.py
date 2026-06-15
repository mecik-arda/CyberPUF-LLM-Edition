import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
from dotenv import load_dotenv

load_dotenv()


def run_full_pipeline(epoch_sayisi=50, yigin_boyutu=128, ogrenme_orani=0.001, sifreleme_modu='CBC', quant_mode='int8_weight', mac_mode='direct'):
    print("=" * 70)
    print("CyberPUF v4.0.0-Gold - Faz 1: Tam Pipeline Calistirma")
    print("Gelistirici: Arda Mecik")
    print("=" * 70)
    print(f"  Epoch sayisi       : {epoch_sayisi}")
    print(f"  Batch boyutu       : {yigin_boyutu}")
    print(f"  Ogrenme hizi       : {ogrenme_orani}")
    print(f"  Sifreleme modu     : AES-256-{sifreleme_modu}")
    print(f"  Nicemleme (Quant)  : {quant_mode}")
    print(f"  MAC Modu (KDF)     : {mac_mode}")
    print("=" * 70)

    toplam_baslangic = time.time()

    def cleanup_on_error():
        print("\n  [HATA YONETIMI] Ara dosyalar temizleniyor...")
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
        dosyalar = [
            os.path.join(base_dir, 'exported_weights', 'cyberpuf_weights.bin'),
            os.path.join(base_dir, 'encrypted_weights', 'cyberpuf_encrypted_weights.bin'),
            os.path.join(base_dir, 'encrypted_weights', 'cyberpuf_ciphertext_raw.bin'),
            os.path.join(base_dir, 'encrypted_weights', 'cyberpuf_nonce.bin'),
            os.path.join(base_dir, 'encrypted_weights', 'cyberpuf_auth_tag.bin')
        ]
        for dosya in dosyalar:
            if os.path.exists(dosya):
                try:
                    os.remove(dosya)
                    print(f"    - Silindi: {dosya}")
                except OSError:
                    pass

    print("\n\n")
    print("#" * 70)
    print("# ADIM 1/4: CNN MODEL EGITIMI")
    print("#" * 70)

    adim1_baslangic = time.time()
    try:
        from ai_sifreleme.train_model import train_model
        model, gecmis = train_model(
            epochs=epoch_sayisi,
            batch_size=yigin_boyutu,
            learning_rate=ogrenme_orani
        )
    except Exception as e:
        print(f"\n  HATA: Adim 1 (CNN Model Egitimi) basarisiz oldu: {e}")
        cleanup_on_error()
        return False
    adim1_suresi = time.time() - adim1_baslangic
    print(f"\n  Adim 1 suresi: {adim1_suresi:.1f} saniye")

    print("\n\n")
    print("#" * 70)
    print("# ADIM 2/4: AGIRLIK DISA AKTARMA")
    print("#" * 70)

    adim2_baslangic = time.time()
    try:
        from ai_sifreleme.export_weights import export_weights
        ikili_veri, agirlik_manifestosu, sha256_hash_degeri = export_weights(quant_mode=quant_mode)
    except Exception as e:
        print(f"\n  HATA: Adim 2 (Agirlik Disa Aktarma) basarisiz oldu: {e}")
        cleanup_on_error()
        return False
    adim2_suresi = time.time() - adim2_baslangic
    print(f"\n  Adim 2 suresi: {adim2_suresi:.1f} saniye")

    print("\n\n")
    print("#" * 70)
    print("# ADIM 3/4: AES-256 SIFRELEME")
    print("#" * 70)

    adim3_baslangic = time.time()
    try:
        from ai_sifreleme.encrypt_weights import encrypt_weights
        sifreli_ikili_veri, aes_anahtari, nonce_degeri, kimlik_dogrulama_etiketi = encrypt_weights(
            encryption_mode=sifreleme_modu, mac_mode=mac_mode
        )
    except Exception as e:
        print(f"\n  HATA: Adim 3 (AES-256 Sifreleme) basarisiz oldu: {e}")
        cleanup_on_error()
        return False
    adim3_suresi = time.time() - adim3_baslangic
    print(f"\n  Adim 3 suresi: {adim3_suresi:.1f} saniye")

    print("\n\n")
    print("#" * 70)
    print("# ADIM 4/4: UCTAN UCA DOGRULAMA")
    print("#" * 70)

    adim4_baslangic = time.time()
    try:
        from ai_sifreleme.verify_encryption import verify_encryption
        dogrulama_basarili_mi = verify_encryption()
    except Exception as e:
        print(f"\n  HATA: Adim 4 (Uctan Uca Dogrulama) basarisiz oldu: {e}")
        cleanup_on_error()
        return False
    adim4_suresi = time.time() - adim4_baslangic
    print(f"\n  Adim 4 suresi: {adim4_suresi:.1f} saniye")

    toplam_sure = time.time() - toplam_baslangic

    print("\n  Kaynaklarin kapandigi dogrulandi.")

    print("\n\n")
    print("=" * 70)
    print("PIPELINE TAMAMLANDI")
    print("=" * 70)
    print(f"  Adim 1 (Egitim)     : {adim1_suresi:8.1f} saniye")
    print(f"  Adim 2 (Disa Aktar) : {adim2_suresi:8.1f} saniye")
    print(f"  Adim 3 (Sifreleme)  : {adim3_suresi:8.1f} saniye")
    print(f"  Adim 4 (Dogrulama)  : {adim4_suresi:8.1f} saniye")
    print(f"  TOPLAM              : {toplam_sure:8.1f} saniye")
    print(f"  Dogrulama Sonucu    : {'BASARILI' if dogrulama_basarili_mi else 'BASARISIZ'}")
    print("=" * 70)

    return dogrulama_basarili_mi


if __name__ == '__main__':
    pipeline_epoch_sayisi = 5
    pipeline_yigin_boyutu = 128
    pipeline_ogrenme_orani = 0.001
    pipeline_modu = 'CBC'
    pipeline_quant_mode = 'int8_weight'
    pipeline_mac_mode = 'direct'

    try:
        if len(sys.argv) > 1:
            pipeline_epoch_sayisi = int(sys.argv[1])
            if pipeline_epoch_sayisi <= 0: raise ValueError("Epochs > 0 olmali")
        if len(sys.argv) > 2:
            pipeline_yigin_boyutu = int(sys.argv[2])
            if pipeline_yigin_boyutu <= 0: raise ValueError("Batch size > 0 olmali")
        if len(sys.argv) > 3:
            pipeline_ogrenme_orani = float(sys.argv[3])
            if pipeline_ogrenme_orani <= 0: raise ValueError("Learning rate > 0 olmali")
        if len(sys.argv) > 4:
            pipeline_modu = sys.argv[4].upper()
            if pipeline_modu not in ('CBC', 'GCM'): raise ValueError("Sifreleme modu 'CBC' veya 'GCM' olmali")
        if len(sys.argv) > 5:
            pipeline_quant_mode = sys.argv[5].lower()
            if pipeline_quant_mode not in ('fp32', 'int8_weight', 'int8_full'): raise ValueError("Quant mode 'fp32', 'int8_weight' veya 'int8_full' olmali")
        if len(sys.argv) > 6:
            pipeline_mac_mode = sys.argv[6].lower()
            if pipeline_mac_mode not in ('direct', 'pbkdf2'): raise ValueError("MAC mode 'direct' veya 'pbkdf2' olmali")
    except ValueError as e:
        print(f"HATA: Gecersiz arguman: {e}")
        sys.exit(1)

    basari_durumu = run_full_pipeline(
        epoch_sayisi=pipeline_epoch_sayisi,
        yigin_boyutu=pipeline_yigin_boyutu,
        ogrenme_orani=pipeline_ogrenme_orani,
        sifreleme_modu=pipeline_modu,
        quant_mode=pipeline_quant_mode,
        mac_mode=pipeline_mac_mode
    )

    sys.exit(0 if basari_durumu else 1)
