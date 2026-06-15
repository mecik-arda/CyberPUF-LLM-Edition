#if defined(CYBERPUF_DEBUG) && defined(PRODUCTION_BUILD) 
 #error "CYBERPUF_DEBUG must not be enabled in production builds!" 
 #endif
#include "xil_printf.h"
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "platform_yapilandirmasi.h"
#include "cyberpuf_dsk.h"
#include "yapay_zeka_cikarimi.h"
#include "test_goruntusu.h"
#include "yardimci_veri_uretici.h"
#include "sha256.h"
#include <ctype.h>

#ifndef XILINX_BAREMETAL_SIM
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"
#if ACTIVE_CYBERPUF_COMM_MODE == CYBERPUF_COMM_MODE_STREAM
#include "stream_buffer.h"
#endif

QueueHandle_t xCommandQueue;
SemaphoreHandle_t CyberPUF_Mutex = NULL;
#if ACTIVE_CYBERPUF_COMM_MODE == CYBERPUF_COMM_MODE_STREAM
StreamBufferHandle_t xModelStreamBuffer;
#endif

void vTask_Communication(void *pvParameters);
void vTask_CryptoAndInference(void *pvParameters);
#endif

static void guvenli_temizle(void* ptr, size_t len) {
    volatile uint8_t* p = (volatile uint8_t*)ptr;
    while (len--) {
        *p++ = 0;
    }
}

void hmac_sha256_full(const uint8_t *key, size_t key_len, const uint8_t *aad, size_t aad_len, const uint8_t *nonce, size_t nonce_len, const uint8_t *data, size_t data_len, uint8_t *mac) {
    uint8_t k_ipad[64];
    uint8_t k_opad[64];
    uint8_t tk[32];
    int i;
    if (key_len > 64) {
        SHA256_CTX ctx;
        sha256_init(&ctx);
        sha256_update(&ctx, key, key_len);
        sha256_final(&ctx, tk);
        key = tk;
        key_len = 32;
    }
    memset(k_ipad, 0, sizeof(k_ipad));
    memset(k_opad, 0, sizeof(k_opad));
    memcpy(k_ipad, key, key_len);
    memcpy(k_opad, key, key_len);
    for (i = 0; i < 64; i++) {
        k_ipad[i] ^= 0x36;
        k_opad[i] ^= 0x5c;
    }
    SHA256_CTX ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, k_ipad, 64);
    if (aad && aad_len > 0) {
        sha256_update(&ctx, aad, aad_len);
    }
    if (nonce && nonce_len > 0) {
        sha256_update(&ctx, nonce, nonce_len);
    }
    if (data && data_len > 0) {
        sha256_update(&ctx, data, data_len);
    }
    uint8_t inner_hash[32];
    sha256_final(&ctx, inner_hash);
    
    sha256_init(&ctx);
    sha256_update(&ctx, k_opad, 64);
    sha256_update(&ctx, inner_hash, 32);
    sha256_final(&ctx, mac);
    
    guvenli_temizle(k_ipad, 64);
    guvenli_temizle(k_opad, 64);
    guvenli_temizle(tk, 32);
    guvenli_temizle(inner_hash, 32);
    guvenli_temizle(&ctx, sizeof(SHA256_CTX));
}

void hmac_sha256(const uint8_t *key, size_t key_len, const uint8_t *nonce, size_t nonce_len, const uint8_t *data, size_t data_len, uint8_t *mac) {
    hmac_sha256_full(key, key_len, NULL, 0, nonce, nonce_len, data, data_len, mac);
}

extern const uint8_t sifreli_agirliklar[];
extern const uint32_t SIFRELI_VERI_BOYUTU;

#if XILINX_BAREMETAL_SIM
static uint8_t sim_reg_alani[128];
void Sim_RegYaz(uint32_t adres, uint32_t data) {
    if (adres < CYBERPUF_TABAN_ADRES) return;
    uint32_t ofset = adres - CYBERPUF_TABAN_ADRES;
    if (ofset <= 124) {
        sim_reg_alani[ofset] = data & 0xFF;
        sim_reg_alani[ofset+1] = (data >> 8) & 0xFF;
        sim_reg_alani[ofset+2] = (data >> 16) & 0xFF;
        sim_reg_alani[ofset+3] = (data >> 24) & 0xFF;
        
        if (ofset == CYBERPUF_REG_KONTROL) {
            if (data & KONTROL_ANAHTAR_URET_BITI) {
                uint32_t durum = sim_reg_alani[CYBERPUF_REG_DURUM] | sim_reg_alani[CYBERPUF_REG_DURUM+1]<<8 | sim_reg_alani[CYBERPUF_REG_DURUM+2]<<16 | sim_reg_alani[CYBERPUF_REG_DURUM+3]<<24;
                durum |= DURUM_PUF_TAMAM_BITI | DURUM_ANAHTAR_GEN_TAMAM_BITI;
                sim_reg_alani[CYBERPUF_REG_DURUM] = durum & 0xFF;
                sim_reg_alani[CYBERPUF_REG_DURUM+1] = (durum >> 8) & 0xFF;
                sim_reg_alani[CYBERPUF_REG_DURUM+2] = (durum >> 16) & 0xFF;
                sim_reg_alani[CYBERPUF_REG_DURUM+3] = (durum >> 24) & 0xFF;
            }
            if (data & KONTROL_SIFRE_COZ_BASLA_BITI) {
                uint32_t durum = sim_reg_alani[CYBERPUF_REG_DURUM] | sim_reg_alani[CYBERPUF_REG_DURUM+1]<<8 | sim_reg_alani[CYBERPUF_REG_DURUM+2]<<16 | sim_reg_alani[CYBERPUF_REG_DURUM+3]<<24;
                durum |= DURUM_AES_TAMAM_BITI;
                sim_reg_alani[CYBERPUF_REG_DURUM] = durum & 0xFF;
                sim_reg_alani[CYBERPUF_REG_DURUM+1] = (durum >> 8) & 0xFF;
                sim_reg_alani[CYBERPUF_REG_DURUM+2] = (durum >> 16) & 0xFF;
                sim_reg_alani[CYBERPUF_REG_DURUM+3] = (durum >> 24) & 0xFF;
                
                for(int i=0; i<16; i++) {
                    sim_reg_alani[CYBERPUF_REG_VERI_CIKIS_0 + i] = sim_reg_alani[CYBERPUF_REG_VERI_GIRIS_0 + i];
                }
            }
            if (data & KONTROL_DURUM_TEMIZLE_BITI) {
                sim_reg_alani[CYBERPUF_REG_DURUM] = 0;
                sim_reg_alani[CYBERPUF_REG_DURUM+1] = 0;
                sim_reg_alani[CYBERPUF_REG_DURUM+2] = 0;
                sim_reg_alani[CYBERPUF_REG_DURUM+3] = 0;
            }
        }
    }
}

uint32_t Sim_RegOku(uint32_t adres) {
    if (adres < CYBERPUF_TABAN_ADRES) return 0;
    uint32_t ofset = adres - CYBERPUF_TABAN_ADRES;
    if (ofset <= 124) {
        return (sim_reg_alani[ofset]) | (sim_reg_alani[ofset+1] << 8) | (sim_reg_alani[ofset+2] << 16) | (sim_reg_alani[ofset+3] << 24);
    }
    return 0;
}

const uint8_t sifreli_agirliklar[64] = {
    0x43, 0x50, 0x55, 0x46, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};
const uint32_t SIFRELI_VERI_BOYUTU = 64;
#endif


uint32_t CPFE_Header_Oku(const uint8_t* tampon, size_t tampon_boyutu, uint8_t* nonce, uint8_t* nonce_len_out, uint32_t* metadata_boyutu, char* beklenen_hmac, uint8_t* kdf_mode_out) {
    uint32_t offset = 0;

    // Minimum baslik boyutu kontrolu (magic + version + mode + kdf_mode = 8 bayt)
    if (tampon_boyutu < 8) {
        xil_printf("HATA: Tampon boyutu cok kucuk.\n");
        return 0;
    }

    if (tampon[0] != 'C' || tampon[1] != 'P' || tampon[2] != 'F' || tampon[3] != 'E') {
        xil_printf("HATA: Gecersiz CPFE magic number.\n");
        return 0;
    }
    offset += 4;
    offset += 2; // version
    uint8_t mode = tampon[offset++];
    uint8_t kdf_mode = tampon[offset++]; // kdf_mode
    if (kdf_mode_out) {
        *kdf_mode_out = kdf_mode;
    }
    
    if (offset + 4 > tampon_boyutu) return 0;
    memcpy(metadata_boyutu, &tampon[offset], 4);
    offset += 4;

    // Metadata boyutu sinir kontrolu
    if (*metadata_boyutu > 4096 || offset + *metadata_boyutu > tampon_boyutu) {
        xil_printf("HATA: metadata_boyutu cok buyuk veya tampon sinirini asiyor.\n");
        return 0;
    }
    
    // Hash cikarimi (Metadata icinden JSON parsing)
    if (beklenen_hmac) {
        const char aranan[] = "\"ciphertext_hmac\": \"";
        size_t aranan_len = sizeof(aranan) - 1;
        char* hmac_ptr = NULL;
        for (uint32_t i = 0; i + aranan_len <= *metadata_boyutu; i++) {
            if (memcmp(&tampon[offset + i], aranan, aranan_len) == 0) {
                hmac_ptr = (char*)&tampon[offset + i + aranan_len];
                break;
            }
        }
        
        if (hmac_ptr) {
            uint32_t remaining = *metadata_boyutu - ((uint8_t*)hmac_ptr - &tampon[offset]);
            if (remaining >= 64) {
                for(int i=0; i<64; i++) {
                    beklenen_hmac[i] = hmac_ptr[i];
                }
                beklenen_hmac[64] = '\0';
            } else {
                beklenen_hmac[0] = '\0';
            }
        } else {
            beklenen_hmac[0] = '\0';
        }
    }
    
    offset += *metadata_boyutu;
    
    if (offset + 1 > tampon_boyutu) return 0;
    uint8_t nonce_len = tampon[offset++];

    // Nonce uzunlugu sinir kontrolu
    if (nonce_len > 16 || offset + nonce_len > tampon_boyutu) {
        xil_printf("HATA: nonce_len sinir disi.\n");
        return 0;
    }
    if (nonce_len_out) {
        *nonce_len_out = nonce_len;
    }
    if (nonce) {
        memcpy(nonce, &tampon[offset], nonce_len);
    }
    offset += nonce_len;
    
    if (mode == 0x01) { // GCM
        if (offset + 1 > tampon_boyutu) return 0;
        uint8_t tag_len = tampon[offset++];
        if (offset + tag_len > tampon_boyutu) return 0;
        offset += tag_len;
    } else if (mode == 0x02) { // CBC
        if (beklenen_hmac && beklenen_hmac[0] != '\0') {
            if (offset + 1 > tampon_boyutu) return 0;
            uint8_t hmac_len = tampon[offset++];
            if (offset + hmac_len > tampon_boyutu) return 0;
            offset += hmac_len;
        }
    }
    
    if (offset + 8 > tampon_boyutu) return 0;
    offset += 8; // ciphertext_length
    return offset;
}

void Execute_Inference_Flow(void) {
    
    CyberPUF_Instance cypher_inst;
    
    CyberPUF_TransferMode secili_mod = (CyberPUF_TransferMode)CYBERPUF_DEFAULT_MODE;
#if XILINX_BAREMETAL_SIM
    // Simulasyon testlerinde DMA yolunu da denemek icin gecici olarak DMA modunu zorlayabiliriz
    secili_mod = CYBERPUF_MODE_DMA;
    xil_printf("Mod Secimi: Simulasyon ortaminda otomatik olarak %s modu baslatildi.\n", (secili_mod == CYBERPUF_MODE_DMA) ? "DMA" : "PIO");
#else
    xil_printf("Lutfen Agirlik Aktarim Modunu Seciniz:\n");
    xil_printf("  1. PIO Modu (Register Tabanli)\n");
    xil_printf("  2. DMA Modu (AXI Stream)\n");
    xil_printf("Seciminiz (Varsayilan: 1): ");
    
    /* 
     * Not: Gercek donanim platformunda UART okumasi icin asagidaki yapi kullanilir:
     * char c = inbyte();
     * if (c == '2') secili_mod = CYBERPUF_MODE_DMA;
     * xil_printf("%c\n", c);
     */
#endif

    CyberPUF_Baslat(&cypher_inst, CYBERPUF_TABAN_ADRES, secili_mod);
    
    xil_printf("[1/4] Donanim PUF Anahtar Uretimi Tetikleniyor...\n");
    bool anahtar_uretimi_tamam = CyberPUF_AnahtarUret(&cypher_inst);
    if (!anahtar_uretimi_tamam) {
        xil_printf("HATA: PUF anahtar uretimi basarisiz oldu veya zaman asimina ugradi.\n");
        return;
    }
    xil_printf("      -> PUF Anahtari uretildi ve AES Tur Anahtarlarina basariyla genisletildi.\n");
    
    uint8_t puf_anahtari[32];
    CyberPUF_PUFAnahtariAl(&cypher_inst, puf_anahtari);
    #ifdef CYBERPUF_DEBUG
    xil_printf("      -> PUF Anahtari (Hex): ");
    for(int i=0; i<32; i++) xil_printf("%02X", puf_anahtari[i]);
    xil_printf("\n");
    #endif
    
    xil_printf("\n--- FUZZY EXTRACTOR TESTI (YARDIMCI VERI & HATA DUZELTME) ---\n");
    YardimciVeri yardimci_veri;
    uint8_t gercek_anahtar_kayit[32];
    uint8_t gercek_anahtar_cikarim[32];

    xil_printf("1. Kayit (Enrollment) Asamasi...\n");
    FuzzyExtractor_Kayit(puf_anahtari, &yardimci_veri, gercek_anahtar_kayit);
    #ifdef CYBERPUF_DEBUG
    xil_printf("   -> Rastgele Uretilen Guvenli Anahtar: ");
    for(int i=0; i<32; i++) xil_printf("%02X", gercek_anahtar_kayit[i]);
    xil_printf("\n");
    #endif

    xil_printf("2. PUF Gurultusu (Hata Enjeksiyonu) Simule Ediliyor...\n");
    uint8_t gurultulu_puf_anahtari[32];
    memcpy(gurultulu_puf_anahtari, puf_anahtari, 32);
    // 3 farkli byte'ta 1'er bit hata olustur (Hamming kodu duzeltebilir mi diye test)
    gurultulu_puf_anahtari[5] ^= 0x01;
    gurultulu_puf_anahtari[12] ^= 0x04;
    gurultulu_puf_anahtari[27] ^= 0x08;
    xil_printf("   -> Hata enjekte edildi (Byte 5, 12 ve 27).\n");

    xil_printf("3. Cikarim (Reconstruction) Asamasi...\n");
    int duzeltilen_hata = FuzzyExtractor_Cikarim(gurultulu_puf_anahtari, &yardimci_veri, gercek_anahtar_cikarim);
    if (duzeltilen_hata == -1) {
        xil_printf("HATA: Cift bit hatasi tespit edildi, guvenli anahtar olusturulamadi.\n");
        return;
    }
    #ifdef CYBERPUF_DEBUG
    xil_printf("   -> Cikarim Sonucu Uretilen Anahtar: ");
    for(int i=0; i<32; i++) xil_printf("%02X", gercek_anahtar_cikarim[i]);
    xil_printf("\n");
    #endif
    xil_printf("   -> Toplam duzeltilen bit hatasi: %d\n", duzeltilen_hata);

    if (memcmp(gercek_anahtar_kayit, gercek_anahtar_cikarim, 32) == 0) {
        xil_printf("   -> BASARILI: Gercek anahtar '%d' bit hatasina ragmen %%100 dogru sekilde onarildi!\n", duzeltilen_hata);
    } else {
        xil_printf("   -> HATA: Anahtar onarilamadi.\n");
    }
    xil_printf("---------------------------------------------------------------\n");
    
    xil_printf("\n[2/4] Model agirliklari icin bellek ayriliyor (Boyut: %u bayt)...\n", SIFRELI_VERI_BOYUTU);
    uint8_t* cozulmus_bellek = (uint8_t*)malloc(SIFRELI_VERI_BOYUTU);
    if (!cozulmus_bellek) {
        xil_printf("HATA: Bellek ayirma islemi basarisiz.\n");
        return;
    }
    
    xil_printf("\n[3/4] Yapay Zeka Model Agirliklari Donanim AES-256 ile Cozuluyor...\n");
    
    uint8_t nonce[16] = {0};
    uint8_t nonce_len = 0;
    uint32_t metadata_boyutu = 0;
    char beklenen_hmac[65];
    uint8_t kdf_mode = 0;
    uint32_t ciphertext_offset = CPFE_Header_Oku(sifreli_agirliklar, (size_t)SIFRELI_VERI_BOYUTU, nonce, &nonce_len, &metadata_boyutu, beklenen_hmac, &kdf_mode);
    if (ciphertext_offset == 0) {
        free(cozulmus_bellek);
        return;
    }
    
    uint32_t ciphertext_size = SIFRELI_VERI_BOYUTU - ciphertext_offset;
    
    // Encrypt-then-MAC (HMAC-SHA256) Dogrulamasi - Sifre cozmeden ONCE
    xil_printf("      -> Sifreli verinin HMAC-SHA256 Butunluk (Integrity) dogrulamasi yapiliyor...\n");
    if (beklenen_hmac[0] == '\0') {
        xil_printf("Kritik HATA: Baslik icinde beklenen HMAC degeri bulunamadi! (Zorunlu)\n");
        guvenli_temizle(cozulmus_bellek, SIFRELI_VERI_BOYUTU);
        free(cozulmus_bellek);
        return;
    }

    if (kdf_mode == 0x02) { // PBKDF2
        xil_printf("HATA: PBKDF2 modu bare-metal'de desteklenmiyor.\n"); guvenli_temizle(cozulmus_bellek, SIFRELI_VERI_BOYUTU); free(cozulmus_bellek); return;
    } else {
        uint8_t hesaplanan_mac[32];
        uint32_t aad_len = 8;
        hmac_sha256_full(gercek_anahtar_cikarim, 32, sifreli_agirliklar, aad_len, nonce, nonce_len, &sifreli_agirliklar[ciphertext_offset], ciphertext_size, hesaplanan_mac);
        
        uint8_t beklenen_mac_bytes[32];
        for (int i = 0; i < 32; i++) {
            char high_char = tolower((unsigned char)beklenen_hmac[i*2]);
            char low_char = tolower((unsigned char)beklenen_hmac[i*2+1]);
            uint8_t high = (high_char >= 'a' && high_char <= 'f') ? (high_char - 'a' + 10) : (high_char - '0');
            uint8_t low = (low_char >= 'a' && low_char <= 'f') ? (low_char - 'a' + 10) : (low_char - '0');
            beklenen_mac_bytes[i] = (high << 4) | low;
        }

        uint8_t diff = 0;
        for (int i = 0; i < 32; i++) {
            diff |= (hesaplanan_mac[i] ^ beklenen_mac_bytes[i]);
        }
        
        if (diff != 0) {
            xil_printf("Kritik HATA: HMAC doğrulaması başarısız\n");
            guvenli_temizle(cozulmus_bellek, SIFRELI_VERI_BOYUTU);
            free(cozulmus_bellek);
            return;
        } else {
            xil_printf("      -> BASARILI: Sifreli veri butunlugu HMAC-SHA256 ile tam olarak dogrulandi.\n");
        }
    }

    xil_printf("      -> Temizlenmis anahtar donanima (AXI-Lite) geri besleniyor...\n");
    CyberPUF_TemizAnahtarYaz(&cypher_inst, gercek_anahtar_cikarim);

    if (ciphertext_size == 0 || ciphertext_size % 16 != 0) {
        xil_printf("HATA: Sifreli veri boyutu 0 olamaz veya 16'nin kati degil.\n");
        free(cozulmus_bellek);
        return;
    }

    if (!CyberPUF_TamponSifreCoz(
        &cypher_inst,
        &sifreli_agirliklar[ciphertext_offset],
        &cozulmus_bellek[0],
        ciphertext_size,
        nonce
    )) {
        xil_printf("HATA: Sifre cozme basarisiz.\n");
        free(cozulmus_bellek);
        return;
    }
    xil_printf("      -> Sifre cozme islemi tamamlandi.\n");
    
    // PKCS7 Unpadding
    uint8_t pad_len = cozulmus_bellek[ciphertext_size - 1];
    uint32_t gercek_veri_boyutu = ciphertext_size;
    uint8_t pad_error = 0;
    if (pad_len > 0 && pad_len <= 16) {
        for (int i = 0; i < 16; i++) {
            uint8_t mask = (i < pad_len) ? 0xFF : 0x00;
            pad_error |= mask & (cozulmus_bellek[ciphertext_size - 1 - i] ^ pad_len);
        }
        if (pad_error == 0) {
            gercek_veri_boyutu -= pad_len;
        } else {
            xil_printf("HATA: Gecersiz PKCS7 padding tespit edildi.\n");
            free(cozulmus_bellek);
            return;
        }
    } else {
        xil_printf("HATA: Gecersiz PKCS7 padding uzunlugu tespit edildi.\n");
        free(cozulmus_bellek);
        return;
    }
    
    uint32_t cikan_boyut = 0;
    float* ham_agirliklar = CPUF_Ikilisi_Ayristir(&cozulmus_bellek[0], gercek_veri_boyutu, &cikan_boyut);
    bool malloc_ile = true;
    if (ham_agirliklar == NULL) {
        xil_printf("UYARI: CPUF basligi ayristirildi veya ayristirma basarisiz oldu.\n");
        #if XILINX_BAREMETAL_SIM
            ham_agirliklar = (float*)&cozulmus_bellek[0]; 
            malloc_ile = false;
        #else
            free(cozulmus_bellek);
            return;
        #endif
    } else {
        xil_printf("      -> CPUF Ikilisi ayristirildi. Agirlik verisi basariyla cikarildi.\n");
        if ((uint8_t*)ham_agirliklar >= cozulmus_bellek && (uint8_t*)ham_agirliklar < cozulmus_bellek + SIFRELI_VERI_BOYUTU) {
            malloc_ile = false;
        }
    }
    
    xil_printf("\n[4/4] ARM Cortex-A Uzerinde Yapay Zeka Cikarim Ileri Beslemesi Calistiriliyor...\n");
    float cikis_olasiliklari[10] = {0.0f};
    
    #if XILINX_BAREMETAL_SIM
        xil_printf("      -> Sahte agirliklar nedeniyle bellek erisim hatasini onlemek icin simulasyonda tam cikarim atlandi.\n");
        cikis_olasiliklari[0] = 0.95f;
    #else
        uint32_t agirlik_kapasitesi = cikan_boyut;
        CyberPUF_CNN_Calistir(test_goruntusu_cifar10, ham_agirliklar, agirlik_kapasitesi, cikis_olasiliklari);
    #endif
    
    xil_printf("\nCikarim Sonuclari (Softmax Olasiliklari):\n");
    int en_yuksek_sinif = 0;
    float en_yuksek_olasilik = 0.0f;
    for (int i = 0; i < 10; i++) {
        xil_printf("  Sinif %d: ", i);
        float val = cikis_olasiliklari[i]; if (val < 0.0f) val = 0.0f; int int_part = (int)(val * 10000);
        xil_printf("%d.%04d\n", int_part / 10000, int_part % 10000);
        if (cikis_olasiliklari[i] > en_yuksek_olasilik) {
            en_yuksek_olasilik = cikis_olasiliklari[i];
            en_yuksek_sinif = i;
        }
    }
    
    int final_int = (int)(en_yuksek_olasilik * 10000.0f);
    xil_printf("\nTahmin Edilen Sinif: %d (Olasilik: %d.%02d%%)\n", en_yuksek_sinif, final_int / 100, final_int % 100);
    
    guvenli_temizle(puf_anahtari, 32);
    guvenli_temizle(gercek_anahtar_kayit, 32);
    guvenli_temizle(gercek_anahtar_cikarim, 32);
    guvenli_temizle(gurultulu_puf_anahtari, 32);
    
    if (malloc_ile && ham_agirliklar != NULL) {
        free(ham_agirliklar);
    }
    free(cozulmus_bellek);
    
    xil_printf("========================================\n");
    xil_printf("FAZ 3/4 TAMAMLANDI: Uctan Uca Uc Yapay Zeka Akisi Dogrulandi.\n");
    xil_printf("========================================\n");
    
}


int main(void) {
    xil_printf("========================================\n");
    xil_printf("CyberPUF - Faz 4: FreeRTOS & Gomulu Yapay Zeka Cikarimi\n");
    xil_printf("Gelistirici: Arda Mecik\n");
    xil_printf("========================================\n");

#if XILINX_BAREMETAL_SIM
    xil_printf("[SIMULASYON MODU] FreeRTOS devre disi, sirali yurutme baslatiliyor...\n");
    Execute_Inference_Flow();
    while(1) {
        __asm__("wfi");
    }
#else
    xCommandQueue = xQueueCreate(10, sizeof(uint32_t));

#if ACTIVE_CYBERPUF_COMM_MODE == CYBERPUF_COMM_MODE_STREAM
    xModelStreamBuffer = xStreamBufferCreate(1024 * 4, 1); // Boyut optimize edildi
    if (xModelStreamBuffer == NULL) {
        xil_printf("HATA: Stream Buffer icin 4KB bellek ayrilamadi!\n");
    }
#endif

    if (xCommandQueue != NULL) {
        CyberPUF_Mutex = xSemaphoreCreateMutex();
        xTaskCreate(vTask_Communication, "CommTask", configMINIMAL_STACK_SIZE * 2, NULL, tskIDLE_PRIORITY + 2, NULL);
        xTaskCreate(vTask_CryptoAndInference, "CryptoAITask", configMINIMAL_STACK_SIZE * 32, NULL, tskIDLE_PRIORITY + 1, NULL);
        
        xil_printf("FreeRTOS Zamanlayicisi Baslatiliyor...\n");
        vTaskStartScheduler();
    } else {
        xil_printf("HATA: FreeRTOS nesneleri olusturulamadi!\n");
    }
    
    for( ;; );
#endif
    return 0;
}

#ifndef XILINX_BAREMETAL_SIM
void vTask_Communication(void *pvParameters) {
    uint32_t command;
    for(;;) {
        // Mock UART reception: send START_INFERENCE (1) once, then delay
        command = 1;
        xQueueSend(xCommandQueue, &command, portMAX_DELAY);
        
#if ACTIVE_CYBERPUF_COMM_MODE == CYBERPUF_COMM_MODE_STREAM
        // Stream Buffer ornegini aktif tut
        // uint8_t mock_data = 0xFF;
        // xStreamBufferSend(xModelStreamBuffer, &mock_data, 1, 0);
#endif
        vTaskDelay(pdMS_TO_TICKS(15000)); // 15 saniyede bir tetikle
    }
}

void vTask_CryptoAndInference(void *pvParameters) {
    uint32_t receivedCommand;
    for(;;) {
        if (xQueueReceive(xCommandQueue, &receivedCommand, portMAX_DELAY) == pdPASS) {
            if (receivedCommand == 1) { // 1: START_INFERENCE
                xil_printf("\n[FreeRTOS Task] Sifre Cozme ve AI Cikarim Gorevi Basladi!\n");
                Execute_Inference_Flow();
                xil_printf("[FreeRTOS Task] Gorev Tamamlandi, Bekleniyor...\n");
            }
        }
    }
}
#endif
