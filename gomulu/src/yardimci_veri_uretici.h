#ifndef YARDIMCI_VERI_URETICI_H
#define YARDIMCI_VERI_URETICI_H

#include <stdint.h>

#define PUF_ANAHTAR_BOYUTU 32 // 256 bit

// Helper Data (Yardimci Veri) yapisi
// 32 byte XOR Maskesi (Code Offset) ve 32 byte Hamming(7,4) Parite verisi icerir.
typedef struct {
    uint8_t xor_maskesi[PUF_ANAHTAR_BOYUTU];
    uint8_t parite_verisi[PUF_ANAHTAR_BOYUTU]; 
} YardimciVeri;

/**
 * @brief PUF kayit asamasinda calisir. Rastgele bir anahtar uretir ve Yardimci Veri (Helper Data) olusturur.
 * 
 * @param puf_ham_anahtar PUF'tan okunan ilk ham 256-bit anahtar.
 * @param yardimci_veri   Uretilecek olan Helper Data (Disariya kaydedilir).
 * @param guvenli_anahtar Uretilen ve sistemde kullanilacak gercek AES anahtari.
 */
void FuzzyExtractor_Kayit(const uint8_t* puf_ham_anahtar, YardimciVeri* yardimci_veri, uint8_t* guvenli_anahtar);

/**
 * @brief Cihaz acildiginda gurultulu PUF verisini Yardımcı Veri ile onararak %100 dogru anahtari uretir.
 * 
 * @param puf_yeni_anahtar PUF'tan o an okunan, muhtemelen bazi bitleri degismis (gurultulu) anahtar.
 * @param yardimci_veri    Kayit asamasinda uretilip saklanan Helper Data.
 * @param guvenli_anahtar  Hata ayiklamadan sonra kurtarilan gercek AES anahtari.
 * @return int             Deltanin/Hatanin kac bit oldugu (0 ise hatasiz). -1 ise kurtarilamayacak kadar hata var.
 */
int FuzzyExtractor_Cikarim(const uint8_t* puf_yeni_anahtar, const YardimciVeri* yardimci_veri, uint8_t* guvenli_anahtar);

#endif // YARDIMCI_VERI_URETICI_H
