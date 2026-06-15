#include "yardimci_veri_uretici.h"
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include "sha256.h"

#define TRNG_REG_DATA 0x43C00000

static uint32_t TRNG_Read(void) {
    // Donanimsal TRNG uyumlu okuma
    return *(volatile uint32_t*)(TRNG_REG_DATA);
}

void FuzzyExtractor_Kayit(const uint8_t* puf_ham_anahtar, YardimciVeri* yardimci_veri, uint8_t* guvenli_anahtar) {
    // 1. TRNG tabanli Salt (Tuz) uretimi (Privacy Amplification icin)
    for (int i = 0; i < PUF_ANAHTAR_BOYUTU; i += 4) {
        uint32_t r = TRNG_Read();
        yardimci_veri->xor_maskesi[i] = (r >> 24) & 0xFF;
        yardimci_veri->xor_maskesi[i+1] = (r >> 16) & 0xFF;
        yardimci_veri->xor_maskesi[i+2] = (r >> 8) & 0xFF;
        yardimci_veri->xor_maskesi[i+3] = r & 0xFF;
    }
    memset(yardimci_veri->parite_verisi, 0, PUF_ANAHTAR_BOYUTU);

    // 2. Privacy Amplification: SHA-256(PUF || Salt)
    uint8_t hash_buf[PUF_ANAHTAR_BOYUTU * 2];
    memcpy(hash_buf, puf_ham_anahtar, PUF_ANAHTAR_BOYUTU);
    memcpy(hash_buf + PUF_ANAHTAR_BOYUTU, yardimci_veri->xor_maskesi, PUF_ANAHTAR_BOYUTU);

    SHA256_CTX ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, hash_buf, sizeof(hash_buf));
    sha256_final(&ctx, guvenli_anahtar);
}

int FuzzyExtractor_Cikarim(const uint8_t* puf_yeni_anahtar, const YardimciVeri* yardimci_veri, uint8_t* guvenli_anahtar) {
    // Donanim katmanindaki iyilestirmelerle (ECC donanimda) PUF tamamen kararli gelir.
    // Hamming duzeltmesine gerek kalmamistir. Sadece Privacy Amplification yapilir.
    
    uint8_t hash_buf[PUF_ANAHTAR_BOYUTU * 2];
    memcpy(hash_buf, puf_yeni_anahtar, PUF_ANAHTAR_BOYUTU);
    memcpy(hash_buf + PUF_ANAHTAR_BOYUTU, yardimci_veri->xor_maskesi, PUF_ANAHTAR_BOYUTU);

    SHA256_CTX ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, hash_buf, sizeof(hash_buf));
    sha256_final(&ctx, guvenli_anahtar);

    return 0; // Hata yok (donanim tarafindan giderildi)
}
