#include "yapay_zeka_cikarimi.h"
#include <math.h>
#include "xil_printf.h"
#include <string.h>

#include <stdlib.h>

#define MAKS_TAMPON_BOYUTU (32 * 32 * 256)

CPUF_QuantizationMode_t g_aktif_model_modu = CPUF_MODE_FP32;

// These buffers must reside in DDR
static float tampon1[MAKS_TAMPON_BOYUTU];
static float tampon2[MAKS_TAMPON_BOYUTU];

void Conv2D_3x3_Same(const float* giris, float* cikis, const ConvLayerParams* params, int giris_y, int giris_g, int giris_k, int cikis_k) {
    int out_pixels = giris_y * giris_g;
    int kernel_size = 9 * giris_k;
    
    // Allocate im2col buffer
    float* im2col_buf = (float*)malloc(out_pixels * kernel_size * sizeof(float));
    if (!im2col_buf) {
        xil_printf("HATA: im2col_buf icin bellek yetersiz.\n");
        return;
    }
    
    // im2col step
    for (int h = 0; h < giris_y; h++) {
        for (int w = 0; w < giris_g; w++) {
            int row_idx = h * giris_g + w;
            int col_idx = 0;
            for (int cy = -1; cy <= 1; cy++) {
                for (int cx = -1; cx <= 1; cx++) {
                    int r = h + cy;
                    int c = w + cx;
                    if (r >= 0 && r < giris_y && c >= 0 && c < giris_g) {
                        int g_base = (r * giris_g + c) * giris_k;
                        for (int k = 0; k < giris_k; k++) {
                            im2col_buf[row_idx * kernel_size + col_idx++] = giris[g_base + k];
                        }
                    } else {
                        for (int k = 0; k < giris_k; k++) {
                            im2col_buf[row_idx * kernel_size + col_idx++] = 0.0f;
                        }
                    }
                }
            }
        }
    }
    
    // GEMM step: cikis = im2col_buf x weights + biases
    for (int p = 0; p < out_pixels; p++) {
        int out_base = p * cikis_k;
        for (int ck = 0; ck < cikis_k; ck++) {
            float sum = params->b[ck];
            for (int k = 0; k < kernel_size; k++) {
                sum += im2col_buf[p * kernel_size + k] * params->w[k * cikis_k + ck];
            }
            cikis[out_base + ck] = sum;
        }
    }
    
    free(im2col_buf);
}

float* CPUF_Ikilisi_Ayristir(uint8_t* cozulmus_veri, uint32_t toplam_boyut, uint32_t* cikan_boyut) {
    uint32_t ofset = 0;
    if (cikan_boyut) *cikan_boyut = 0;
    
    if (toplam_boyut < 16) {
        xil_printf("HATA: Veri boyutu cok kucuk.\n");
        return NULL;
    }
    
    if (cozulmus_veri[0] != 'C' || cozulmus_veri[1] != 'P' || cozulmus_veri[2] != 'U' || cozulmus_veri[3] != 'F') {
        xil_printf("HATA: Gecersiz CPUF sihirli numarasi.\n");
        return NULL;
    }
    ofset += 4;
    
    uint8_t ver_major = cozulmus_veri[ofset++];
    uint8_t ver_minor = cozulmus_veri[ofset++];
    if (ver_major != 1) return NULL;
    
    if (ver_minor >= 2) {
        g_aktif_model_modu = (CPUF_QuantizationMode_t)cozulmus_veri[ofset++];
    } else {
        g_aktif_model_modu = CPUF_MODE_FP32;
    }
    
    uint32_t toplam_diziler;
    memcpy(&toplam_diziler, &cozulmus_veri[ofset], sizeof(uint32_t));
    ofset += 4;
    
    if (toplam_diziler > 100) return NULL;
    
    uint64_t toplam_elemanlar;
    memcpy(&toplam_elemanlar, &cozulmus_veri[ofset], sizeof(uint64_t));
    ofset += 8;
    
    if (toplam_elemanlar > (0xFFFFFFFF / sizeof(float))) {
        xil_printf("HATA: Toplam eleman sayisi tamsayi tasmasina neden olacak.\n");
        return NULL;
    }
    
    uint32_t reserved_size = (ver_minor >= 2) ? 15 : 16;
    if (ofset + reserved_size > toplam_boyut) return NULL;
    ofset += reserved_size;

    float* scales = NULL;
    if (ver_minor >= 2 && g_aktif_model_modu > CPUF_MODE_FP32) {
        scales = (float*)malloc(toplam_diziler * sizeof(float));
        if (!scales) {
            xil_printf("HATA: Bellek yetersiz (scales).\n");
            return NULL;
        }
    }
    
    uint32_t* array_sizes = (uint32_t*)malloc(toplam_diziler * sizeof(uint32_t));
    if (!array_sizes) {
        xil_printf("HATA: Bellek yetersiz (array_sizes).\n");
        if (scales) free(scales);
        return NULL;
    }
    
    for (uint32_t i = 0; i < toplam_diziler; i++) {
        if (ofset >= toplam_boyut) {
            if (scales) free(scales);
            free(array_sizes);
            return NULL;
        }
        uint8_t ndim = cozulmus_veri[ofset++];

        if (ndim > (toplam_boyut - ofset) / 4) {
            if (scales) free(scales);
            free(array_sizes);
            return NULL;
        }
        ofset += ndim * 4;

        if (ofset + 8 > toplam_boyut) {
            if (scales) free(scales);
            free(array_sizes);
            return NULL;
        }
        uint32_t nelem;
        memcpy(&nelem, &cozulmus_veri[ofset], 4);
        array_sizes[i] = nelem;
        ofset += 8; // num_elements, size_bytes
        
        if (ver_minor >= 2) {
            if (ofset + 8 > toplam_boyut) {
                if (scales) free(scales);
                free(array_sizes);
                return NULL;
            }
            if (scales) {
                memcpy(&scales[i], &cozulmus_veri[ofset], 4);
            }
            ofset += 4; // scale
            ofset += 1; // zp
            ofset += 3; // padding
        }
    }
    
    if (ofset >= toplam_boyut) {
        if (scales) free(scales);
        free(array_sizes);
        return NULL;
    }
    
    float* out_weights = NULL;
    
    if (g_aktif_model_modu == CPUF_MODE_INT8_WEIGHT) {
        out_weights = (float*)malloc(toplam_elemanlar * sizeof(float));
        if (!out_weights) {
            xil_printf("HATA: Dequantize tampon bellegi ayrilamadi.\n");
            if (scales) free(scales);
            free(array_sizes);
            return NULL;
        } else {
            uint32_t dst_idx = 0;
            uint32_t src_offset = ofset;
            for (uint32_t i = 0; i < toplam_diziler; i++) {
                float scale = scales[i];
                uint32_t n = array_sizes[i];
                if (src_offset + n > toplam_boyut) {
                    xil_printf("HATA: INT8 Sinir disi bellek erisimi (OOB).\n");
                    free(out_weights);
                    if (scales) free(scales);
                    free(array_sizes);
                    return NULL;
                }
                for (uint32_t j = 0; j < n; j++) {
                    if (dst_idx >= toplam_elemanlar) {
                        xil_printf("HATA: Dequantize bounds error.\n");
                        free(out_weights);
                        if (scales) free(scales);
                        free(array_sizes);
                        return NULL;
                    }
                    int8_t val = (int8_t)cozulmus_veri[src_offset++];
                    out_weights[dst_idx++] = (float)val * scale;
                }
            }
            xil_printf("  -> INT8 agirliklar RAM'e de-quantize edildi.\n");
            if (cikan_boyut) *cikan_boyut = toplam_elemanlar * sizeof(float);
        }
    } 
    else if (g_aktif_model_modu == CPUF_MODE_INT8_FULL) {
        xil_printf("HATA: INT8 Full Integer modu desteklenmiyor.\n");
        if (scales) free(scales);
        free(array_sizes);
        return NULL;
    }
    else {
        // FP32 mode
        // Hizalama guvencesi icin veriyi malloc yapip kopyalamak en dogrusu
        uint64_t req_bytes = toplam_elemanlar * sizeof(float);
        if (ofset + req_bytes > toplam_boyut) {
            xil_printf("HATA: FP32 Sinir disi bellek erisimi (OOB).\n");
            if (scales) free(scales);
            free(array_sizes);
            return NULL;
        }
        out_weights = (float*)malloc(toplam_elemanlar * sizeof(float));
        if (out_weights) {
            memcpy(out_weights, &cozulmus_veri[ofset], toplam_elemanlar * sizeof(float));
            if (cikan_boyut) *cikan_boyut = toplam_elemanlar * sizeof(float);
        } else {
            xil_printf("HATA: FP32 agirliklari kopyalamak icin bellek yetersiz.\n");
            if (scales) free(scales);
            free(array_sizes);
            return NULL;
        }
    }
    
    if (scales) free(scales);
    free(array_sizes);
    
    return out_weights;
}

void BatchNorm_ReLU(float* data, const ConvLayerParams* params, int h, int w, int c) {
    float epsilon = 1e-3f;
    float scale[256];
    for (int ch = 0; ch < c && ch < 256; ch++) {
        scale[ch] = params->gamma[ch] / sqrtf(fabsf(params->var[ch]) + epsilon);
    }
    for (int i = 0; i < h * w; i++) {
        for (int ch = 0; ch < c && ch < 256; ch++) {
            float deger = data[i * c + ch];
            deger = scale[ch] * (deger - params->mean[ch]) + params->beta[ch];
            if (deger < 0.0f) {
                deger = 0.0f;
            }
            data[i * c + ch] = deger;
        }
    }
}

void MaxPool_2x2(const float* giris, float* cikis, int giris_y, int giris_g, int c) {
    int out_h = giris_y / 2;
    int out_w = giris_g / 2;
    
    for (int h = 0; h < out_h; h++) {
        for (int w = 0; w < out_w; w++) {
            for (int cy = 0; cy < 2; cy++) {
                for (int cg = 0; cg < 2; cg++) {
                    int r = h * 2 + cy;
                    int cl = w * 2 + cg;
                    for (int ch = 0; ch < c; ch++) {
                        float deger = giris[(r * giris_g + cl) * c + ch];
                        if (cy == 0 && cg == 0) {
                            cikis[(h * out_w + w) * c + ch] = deger;
                        } else {
                            if (deger > cikis[(h * out_w + w) * c + ch]) {
                                cikis[(h * out_w + w) * c + ch] = deger;
                            }
                        }
                    }
                }
            }
        }
    }
}

void Dense_Layer(const float* giris, float* cikis, const DenseLayerParams* params, int giris_ozellikleri, int cikis_ozellikleri) {
    for (int o = 0; o < cikis_ozellikleri; o++) {
        float toplam = params->b[o];
        for (int i = 0; i < giris_ozellikleri; i++) {
            toplam += giris[i] * params->w[i * cikis_ozellikleri + o];
        }
        cikis[o] = toplam;
    }
}

void BatchNorm_ReLU_Dense(float* data, const DenseLayerParams* params, int ozellikler) {
    float epsilon = 1e-3f;
    for (int i = 0; i < ozellikler; i++) {
        float m = params->mean[i];
        float v = params->var[i];
        float gamma = params->gamma[i];
        float beta = params->beta[i];
        
        float scale = gamma / sqrtf(fabsf(v) + epsilon);
        float deger = scale * (data[i] - m) + beta;
        
        if (deger < 0.0f) {
            deger = 0.0f;
        }
        data[i] = deger;
    }
}

void Dense_Final_Softmax(const float* giris, float* cikis, const DenseFinalParams* params, int giris_ozellikleri, int sinif_sayisi) {
    float maks_deger = -1e6f;
    for (int o = 0; o < sinif_sayisi; o++) {
        float toplam = params->b[o];
        for (int i = 0; i < giris_ozellikleri; i++) {
            toplam += giris[i] * params->w[i * sinif_sayisi + o];
        }
        cikis[o] = toplam;
        if (toplam > maks_deger) {
            maks_deger = toplam;
        }
    }
    
    float toplam_ustel = 0.0f;
    for (int o = 0; o < sinif_sayisi; o++) {
        cikis[o] = expf(cikis[o] - maks_deger);
        toplam_ustel += cikis[o];
    }
    
    for (int o = 0; o < sinif_sayisi; o++) {
        cikis[o] /= toplam_ustel;
    }
}

static float* ConvParametreleriniCikar(float* ptr, ConvLayerParams* p, int giris_k, int cikis_k, uint32_t* kapasite) {
    uint64_t gereken = ((uint64_t)3 * 3 * giris_k * cikis_k) + 5 * cikis_k;
    uint64_t gereken_bayt = gereken * sizeof(float);
    if (*kapasite < gereken_bayt) return NULL;
    // gereken_bayt truncation is safe due to the guard above
    *kapasite -= (uint32_t)gereken_bayt;
    p->w = ptr; ptr += (3 * 3 * giris_k * cikis_k);
    p->b = ptr; ptr += cikis_k;
    p->gamma = ptr; ptr += cikis_k;
    p->beta = ptr; ptr += cikis_k;
    p->mean = ptr; ptr += cikis_k;
    p->var = ptr; ptr += cikis_k;
    return ptr;
}

static float* DenseParametreleriniCikar(float* ptr, DenseLayerParams* p, int in_f, int out_f, uint32_t* kapasite) {
    uint64_t gereken = ((uint64_t)in_f * out_f) + 5 * out_f;
    uint64_t gereken_bayt = gereken * sizeof(float);
    if (*kapasite < gereken_bayt) return NULL;
    // gereken_bayt truncation is safe due to the guard above
    *kapasite -= (uint32_t)gereken_bayt;
    p->w = ptr; ptr += (in_f * out_f);
    p->b = ptr; ptr += out_f;
    p->gamma = ptr; ptr += out_f;
    p->beta = ptr; ptr += out_f;
    p->mean = ptr; ptr += out_f;
    p->var = ptr; ptr += out_f;
    return ptr;
}

void CyberPUF_CNN_Calistir(const float* giris_goruntusu, float* ham_agirliklar, uint32_t agirlik_kapasitesi, float* cikis_olasiliklari) {
    float* w_ptr = ham_agirliklar;
    ConvLayerParams conv1_1, conv1_2, conv2_1, conv2_2, conv3_1, conv3_2;
    DenseLayerParams dense1, dense2;
    DenseFinalParams final_dense;

    uint32_t kalan_kapasite = agirlik_kapasitesi;

    w_ptr = ConvParametreleriniCikar(w_ptr, &conv1_1, 3, 64, &kalan_kapasite);
    if (!w_ptr) goto coker;
    w_ptr = ConvParametreleriniCikar(w_ptr, &conv1_2, 64, 64, &kalan_kapasite);
    if (!w_ptr) goto coker;
    w_ptr = ConvParametreleriniCikar(w_ptr, &conv2_1, 64, 128, &kalan_kapasite);
    if (!w_ptr) goto coker;
    w_ptr = ConvParametreleriniCikar(w_ptr, &conv2_2, 128, 128, &kalan_kapasite);
    if (!w_ptr) goto coker;
    w_ptr = ConvParametreleriniCikar(w_ptr, &conv3_1, 128, 256, &kalan_kapasite);
    if (!w_ptr) goto coker;
    w_ptr = ConvParametreleriniCikar(w_ptr, &conv3_2, 256, 256, &kalan_kapasite);
    if (!w_ptr) goto coker;

    w_ptr = DenseParametreleriniCikar(w_ptr, &dense1, 4096, 512, &kalan_kapasite);
    if (!w_ptr) goto coker;
    w_ptr = DenseParametreleriniCikar(w_ptr, &dense2, 512, 256, &kalan_kapasite);
    if (!w_ptr) goto coker;

    if (kalan_kapasite < ((256 * 10) + 10) * sizeof(float)) goto coker;
    final_dense.w = w_ptr; w_ptr += (256 * 10);
    final_dense.b = w_ptr; w_ptr += 10;

    Conv2D_3x3_Same(giris_goruntusu, tampon1, &conv1_1, 32, 32, 3, 64);
    BatchNorm_ReLU(tampon1, &conv1_1, 32, 32, 64);

    Conv2D_3x3_Same(tampon1, tampon2, &conv1_2, 32, 32, 64, 64);
    BatchNorm_ReLU(tampon2, &conv1_2, 32, 32, 64);

    MaxPool_2x2(tampon2, tampon1, 32, 32, 64);

    Conv2D_3x3_Same(tampon1, tampon2, &conv2_1, 16, 16, 64, 128);
    BatchNorm_ReLU(tampon2, &conv2_1, 16, 16, 128);

    Conv2D_3x3_Same(tampon2, tampon1, &conv2_2, 16, 16, 128, 128);
    BatchNorm_ReLU(tampon1, &conv2_2, 16, 16, 128);

    MaxPool_2x2(tampon1, tampon2, 16, 16, 128);

    Conv2D_3x3_Same(tampon2, tampon1, &conv3_1, 8, 8, 128, 256);
    BatchNorm_ReLU(tampon1, &conv3_1, 8, 8, 256);

    Conv2D_3x3_Same(tampon1, tampon2, &conv3_2, 8, 8, 256, 256);
    BatchNorm_ReLU(tampon2, &conv3_2, 8, 8, 256);

    MaxPool_2x2(tampon2, tampon1, 8, 8, 256);

    Dense_Layer(tampon1, tampon2, &dense1, 4096, 512);
    BatchNorm_ReLU_Dense(tampon2, &dense1, 512);

    Dense_Layer(tampon2, tampon1, &dense2, 512, 256);
    BatchNorm_ReLU_Dense(tampon1, &dense2, 256);

    Dense_Final_Softmax(tampon1, cikis_olasiliklari, &final_dense, 256, 10);
    
    return;

coker:
    xil_printf("HATA: Agirlik bellegi sinir disi (OOB read) engellendi.\n");
    if (cikis_olasiliklari != NULL) {
        memset(cikis_olasiliklari, 0, 10 * sizeof(float));
    }
}
