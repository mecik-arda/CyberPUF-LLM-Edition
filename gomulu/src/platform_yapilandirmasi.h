#ifndef PLATFORM_YAPILANDIRMASI_H
#define PLATFORM_YAPILANDIRMASI_H

#define CYBERPUF_TABAN_ADRES 0x43C00000
#define CYBERPUF_DMA_TABAN_ADRES 0x40400000

#define CYBERPUF_DEFAULT_MODE 1 // 1: PIO, 2: DMA

#ifndef XILINX_BAREMETAL_SIM
#define XILINX_BAREMETAL_SIM 0
#endif

// FreeRTOS Iletisim Modlari
#define CYBERPUF_COMM_MODE_QUEUE        1 // Sadece hafif komut kuyrugu
#define CYBERPUF_COMM_MODE_STREAM       2 // Arka planda model akitan Stream Buffer

// Varsayilan calisma modu (Kullanici buradan degistirebilir)
#define ACTIVE_CYBERPUF_COMM_MODE       CYBERPUF_COMM_MODE_QUEUE

#include <stdint.h>

#if XILINX_BAREMETAL_SIM
    #include <stdio.h>
    #include <stdlib.h>
    extern void Sim_RegYaz(uint32_t adres, uint32_t data);
    extern uint32_t Sim_RegOku(uint32_t adres);
    #define Xil_Out32(Addr, Data) Sim_RegYaz((Addr), (Data))
    #define Xil_In32(Addr)        Sim_RegOku((Addr))
#else
    #include "xil_io.h"
#endif

#endif
