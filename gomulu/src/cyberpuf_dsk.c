#include "cyberpuf_dsk.h"
#include "platform_yapilandirmasi.h"
#include "xil_printf.h"
#include <string.h>

#ifndef XILINX_BAREMETAL_SIM
#include "xaxidma.h"
#include "xil_cache.h"
#endif

#ifndef XILINX_BAREMETAL_SIM
#include "FreeRTOS.h"
#include "task.h"
#include "semphr.h"

extern SemaphoreHandle_t CyberPUF_Mutex;
#endif

#define PACK32(b0, b1, b2, b3) (((uint32_t)(b0) << 24) | ((uint32_t)(b1) << 16) | ((uint32_t)(b2) << 8) | (uint32_t)(b3))

static void CyberPUF_KontrolYaz(CyberPUF_Instance *InstancePtr, uint32_t deger) {
    uint32_t mod_biti = (InstancePtr->AktifMod == CYBERPUF_MODE_DMA) ? KONTROL_MOD_SECIMI_BITI : 0;
    Xil_Out32(InstancePtr->BaseAddress + CYBERPUF_REG_KONTROL, mod_biti | deger);
}

void CyberPUF_Baslat(CyberPUF_Instance *InstancePtr, uint32_t taban_adresi, CyberPUF_TransferMode mod) {
    InstancePtr->BaseAddress = taban_adresi;
    InstancePtr->AktifMod = mod;
    InstancePtr->IsBusy = false;
    InstancePtr->DmaDoneHandler = NULL;
    InstancePtr->CallBackRef = NULL;
    
    CyberPUF_KontrolYaz(InstancePtr, KONTROL_DURUM_TEMIZLE_BITI);
    CyberPUF_KontrolYaz(InstancePtr, 0x00000000);
}

uint32_t CyberPUF_DurumAl(CyberPUF_Instance *InstancePtr) {
    return Xil_In32(InstancePtr->BaseAddress + CYBERPUF_REG_DURUM);
}

bool CyberPUF_AnahtarUret(CyberPUF_Instance *InstancePtr) {
#ifndef XILINX_BAREMETAL_SIM
    if (CyberPUF_Mutex != NULL) {
        xSemaphoreTake(CyberPUF_Mutex, portMAX_DELAY);
    }
#endif
    InstancePtr->IsBusy = true;
    CyberPUF_KontrolYaz(InstancePtr, KONTROL_DURUM_TEMIZLE_BITI);
    CyberPUF_KontrolYaz(InstancePtr, 0x00000000);

    CyberPUF_KontrolYaz(InstancePtr, KONTROL_ANAHTAR_URET_BITI);
    CyberPUF_KontrolYaz(InstancePtr, 0x00000000);

    uint32_t durum = 0;
    uint32_t timeout = 0xFFFFFF;

    while (timeout > 0) {
        durum = Xil_In32(InstancePtr->BaseAddress + CYBERPUF_REG_DURUM);
        if ((durum & DURUM_ANAHTAR_GEN_TAMAM_BITI) != 0) {
            InstancePtr->IsBusy = false;
#ifndef XILINX_BAREMETAL_SIM
            if (CyberPUF_Mutex != NULL) {
                xSemaphoreGive(CyberPUF_Mutex);
            }
#endif
            return true;
        }
#ifndef XILINX_BAREMETAL_SIM
        taskYIELD();
#endif
        timeout--;
    }

    InstancePtr->IsBusy = false;
#ifndef XILINX_BAREMETAL_SIM
    if (CyberPUF_Mutex != NULL) {
        xSemaphoreGive(CyberPUF_Mutex);
    }
#endif
    return false;
}

bool CyberPUF_BlokSifreCoz(CyberPUF_Instance *InstancePtr, const uint8_t* sifreli_metin_16b, uint8_t* duz_metin_16b) {
    uint32_t w3 = PACK32(sifreli_metin_16b[0], sifreli_metin_16b[1], sifreli_metin_16b[2], sifreli_metin_16b[3]);
    uint32_t w2 = PACK32(sifreli_metin_16b[4], sifreli_metin_16b[5], sifreli_metin_16b[6], sifreli_metin_16b[7]);
    uint32_t w1 = PACK32(sifreli_metin_16b[8], sifreli_metin_16b[9], sifreli_metin_16b[10], sifreli_metin_16b[11]);
    uint32_t w0 = PACK32(sifreli_metin_16b[12], sifreli_metin_16b[13], sifreli_metin_16b[14], sifreli_metin_16b[15]);

    Xil_Out32(InstancePtr->BaseAddress + CYBERPUF_REG_VERI_GIRIS_0, w0);
    Xil_Out32(InstancePtr->BaseAddress + CYBERPUF_REG_VERI_GIRIS_1, w1);
    Xil_Out32(InstancePtr->BaseAddress + CYBERPUF_REG_VERI_GIRIS_2, w2);
    Xil_Out32(InstancePtr->BaseAddress + CYBERPUF_REG_VERI_GIRIS_3, w3);

    CyberPUF_KontrolYaz(InstancePtr, KONTROL_DURUM_TEMIZLE_BITI);
    CyberPUF_KontrolYaz(InstancePtr, 0x00000000);

    CyberPUF_KontrolYaz(InstancePtr, KONTROL_SIFRE_COZ_BASLA_BITI);
    CyberPUF_KontrolYaz(InstancePtr, 0x00000000);

    uint32_t durum = 0;
    uint32_t timeout = 0xFFFFFF;

    while (timeout > 0) {
        durum = Xil_In32(InstancePtr->BaseAddress + CYBERPUF_REG_DURUM);
        if ((durum & DURUM_AES_TAMAM_BITI) != 0) {
            break;
        }
#ifndef XILINX_BAREMETAL_SIM
        taskYIELD();
#endif
        timeout--;
    }

    if (timeout == 0) {
        return false;
    }

    uint32_t r0 = Xil_In32(InstancePtr->BaseAddress + CYBERPUF_REG_VERI_CIKIS_0);
    uint32_t r1 = Xil_In32(InstancePtr->BaseAddress + CYBERPUF_REG_VERI_CIKIS_1);
    uint32_t r2 = Xil_In32(InstancePtr->BaseAddress + CYBERPUF_REG_VERI_CIKIS_2);
    uint32_t r3 = Xil_In32(InstancePtr->BaseAddress + CYBERPUF_REG_VERI_CIKIS_3);

    duz_metin_16b[0] = (uint8_t)((r3 >> 24) & 0xFF);
    duz_metin_16b[1] = (uint8_t)((r3 >> 16) & 0xFF);
    duz_metin_16b[2] = (uint8_t)((r3 >> 8) & 0xFF);
    duz_metin_16b[3] = (uint8_t)(r3 & 0xFF);

    duz_metin_16b[4] = (uint8_t)((r2 >> 24) & 0xFF);
    duz_metin_16b[5] = (uint8_t)((r2 >> 16) & 0xFF);
    duz_metin_16b[6] = (uint8_t)((r2 >> 8) & 0xFF);
    duz_metin_16b[7] = (uint8_t)(r2 & 0xFF);

    duz_metin_16b[8] = (uint8_t)((r1 >> 24) & 0xFF);
    duz_metin_16b[9] = (uint8_t)((r1 >> 16) & 0xFF);
    duz_metin_16b[10] = (uint8_t)((r1 >> 8) & 0xFF);
    duz_metin_16b[11] = (uint8_t)(r1 & 0xFF);

    duz_metin_16b[12] = (uint8_t)((r0 >> 24) & 0xFF);
    duz_metin_16b[13] = (uint8_t)((r0 >> 16) & 0xFF);
    duz_metin_16b[14] = (uint8_t)((r0 >> 8) & 0xFF);
    duz_metin_16b[15] = (uint8_t)(r0 & 0xFF);

    return true;
}

bool CyberPUF_TamponSifreCoz(CyberPUF_Instance *InstancePtr, const uint8_t* sifreli_metin, uint8_t* duz_metin, uint32_t boyut_bayt, const uint8_t* iv) {
    bool ret_val = false;
#ifndef XILINX_BAREMETAL_SIM
    if (CyberPUF_Mutex != NULL) {
        xSemaphoreTake(CyberPUF_Mutex, portMAX_DELAY);
    }
#endif
    if (InstancePtr->IsBusy) {
        goto end_unlock;
    }
    InstancePtr->IsBusy = true;
    
    uint32_t remainder = boyut_bayt % 16;
    if (remainder != 0) {
        xil_printf("HATA: Sifreli metin boyutu (%u) 16'nin kati degil. CBC modunda PKCS7 dolgusu beklenir.\n", boyut_bayt);
        InstancePtr->IsBusy = false;
        goto end_unlock;
    }
    
    uint32_t blocks = boyut_bayt / 16;
    uint8_t prev_block[16];
    
    if (iv != NULL) {
        memcpy(prev_block, iv, 16);
    } else {
        memset(prev_block, 0, 16);
    }
    
    if (InstancePtr->AktifMod == CYBERPUF_MODE_DMA) {
#ifndef XILINX_BAREMETAL_SIM
        extern XAxiDma AxiDma;
        
        Xil_DCacheFlushRange((INTPTR)sifreli_metin, boyut_bayt);
        Xil_DCacheInvalidateRange((INTPTR)duz_metin, boyut_bayt);

        int status_rx = XAxiDma_SimpleTransfer(&AxiDma, (UINTPTR)duz_metin, boyut_bayt, XAXIDMA_DEVICE_TO_DMA);
        int status_tx = XAxiDma_SimpleTransfer(&AxiDma, (UINTPTR)sifreli_metin, boyut_bayt, XAXIDMA_DMA_TO_DEVICE);

        if (status_tx != 0 || status_rx != 0) {
            xil_printf("HATA: DMA transferi baslatilamadi.\n");
            InstancePtr->IsBusy = false;
            goto end_unlock;
        }

        // Asenkron interrupt mimarisinde DMA bitisi callback'te islenir. 
        // Burada basitce polling yapiyoruz (bloklayici):
        while (XAxiDma_Busy(&AxiDma, XAXIDMA_DMA_TO_DEVICE) || 
               XAxiDma_Busy(&AxiDma, XAXIDMA_DEVICE_TO_DMA)) {
            taskYIELD();
        }
#endif
        if (InstancePtr->DmaDoneHandler != NULL) {
            InstancePtr->DmaDoneHandler(InstancePtr->CallBackRef);
        }
        
    } else {
        // PIO Modu (Mevcut Register uzerinden Dongu)
        for (uint32_t i = 0; i < blocks; i++) {
            uint8_t current_cipher[16];
            memcpy(current_cipher, &sifreli_metin[i * 16], 16);
            
            uint8_t dec_out[16];
            if (!CyberPUF_BlokSifreCoz(InstancePtr, current_cipher, dec_out)) {
                xil_printf("HATA: Blok sifre cozme basarisiz. (Blok %u)\n", i);
                InstancePtr->IsBusy = false;
                goto end_unlock;
            }
            
            // CBC Zincirleme (XOR) islemi
            for (int j = 0; j < 16; j++) {
                duz_metin[i * 16 + j] = dec_out[j] ^ prev_block[j];
            }
            
            memcpy(prev_block, current_cipher, 16);
        }
    }
    
    InstancePtr->IsBusy = false;
    ret_val = true;

end_unlock:
#ifndef XILINX_BAREMETAL_SIM
    if (CyberPUF_Mutex != NULL) {
        xSemaphoreGive(CyberPUF_Mutex);
    }
#endif
    return ret_val;
}

void CyberPUF_PUFAnahtariAl(CyberPUF_Instance *InstancePtr, uint8_t* anahtar_tamponu_32b) {
    for (int i = 0; i < 8; i++) {
        uint32_t word = Xil_In32(InstancePtr->BaseAddress + CYBERPUF_REG_PUF_ANAHTAR_0 + (i * 4));
        anahtar_tamponu_32b[i * 4 + 0] = (uint8_t)(word & 0xFF);
        anahtar_tamponu_32b[i * 4 + 1] = (uint8_t)((word >> 8) & 0xFF);
        anahtar_tamponu_32b[i * 4 + 2] = (uint8_t)((word >> 16) & 0xFF);
        anahtar_tamponu_32b[i * 4 + 3] = (uint8_t)((word >> 24) & 0xFF);
    }
}

void CyberPUF_TemizAnahtarYaz(CyberPUF_Instance *InstancePtr, const uint8_t* temiz_anahtar_32b) {
    for (int i = 0; i < 8; i++) {
        uint32_t word = ((uint32_t)temiz_anahtar_32b[i * 4 + 0]) |
                        (((uint32_t)temiz_anahtar_32b[i * 4 + 1]) << 8) |
                        (((uint32_t)temiz_anahtar_32b[i * 4 + 2]) << 16) |
                        (((uint32_t)temiz_anahtar_32b[i * 4 + 3]) << 24);
        Xil_Out32(InstancePtr->BaseAddress + CYBERPUF_REG_PUF_ANAHTAR_YAZ_0 + (i * 4), word);
    }
}

