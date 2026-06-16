# CyberPUF LLM Edition (Proof of Concept)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-Proof%20of%20Concept-orange)

[🇹🇷 Türkçe](#türkçe) | [🇬🇧 English](#english)

---

## 🇹🇷 Türkçe

**CyberPUF LLM Edition**, sınır cihazlarda (edge devices) ve yerel donanımlarda çalışan Büyük Dil Modellerinin (LLM) fikri mülkiyetini (IP) güvence altına almak için tasarlanmış gelişmiş bir Donanım Güvenliği ve Edge-AI projesidir.

Bu proje, orijinal [CyberPUF](https://github.com/mecik-arda/CyberPUF) mimarisinin bir evrimi olup, modern LLM'lerin (Qwen, Llama, Phi vb.) devasa ağırlık mimarilerini ciddi gecikmeler (latency) veya bellek darboğazları yaratmadan şifreleyebilecek şekilde uyarlanmıştır.

### Temel Problem
Milyarlarca parametreli yapay zeka modelleri sınır cihazlara yüklendiğinde, ağırlık dosyaları (`.safetensors` veya `.bin`) yerel diskte saklanır. Kötü niyetli kişiler bu dosyaları kolayca kopyalayarak milyonlarca dolarlık yapay zeka araştırmalarını ve özel ince ayarları (fine-tuning) çalabilir. Geleneksel tam disk şifreleme yöntemleri, cihazın bir yerinde saklanan ve ele geçirilebilecek bir anahtar gerektirir.

### CyberPUF Çözümü
CyberPUF LLM Edition, Fiziksel Klonlanamaz Fonksiyonlara (PUF) dayanan bir **Güvenli RAM-Disk Wrapper** mimarisi sunar:

1. **AES-256 Şifreleme:** LLM dizini sıkıştırılır ve tek bir `.cpuf_llm` dosyasına (Streaming ile chunklar halinde) şifrelenir.
2. **PUF Tabanlı Anahtarlar:** Şifreleme/deşifreleme anahtarı diskte asla saklanmaz. Donanım parmak izi (SRAM/RO-PUF simülasyonu) kullanılarak çalışma zamanında dinamik olarak (HKDF ile) üretilir.
3. **RAM-Disk (tmpfs) Deşifreleme:** Çalışma zamanında model **asla** fiziksel diske (SSD) geri deşifre edilmez. Linux `tmpfs` kullanılarak RAM üzerinde güvenli bir disk oluşturulur ve doğrudan oraya açılır.
4. **Zeroization:** Çıkarım motoru (örn. OpenVINO, Llama.cpp, Transformers) ağırlıkları aktif belleğe/VRAM'e yüklediği an, deşifre edilen RAM-disk kalıcı olarak sıfırlarla ezilerek (`memset`) imha edilir ve sistemden sökülür.

### Mimari Diyagram

```text
+-------------------+       +-----------------------+       +-------------------+
| Edge Device HW    |       |   CyberPUF LLM Core   |       | Volatile RAM Disk |
| (MAC, CPU, Disk)  |       |                       |       | (tmpfs mount)     |
+---------+---------+       +-----------+-----------+       +---------+---------+
          |                             |                             |
          | 1. Extract HW Fingerprint   |                             |
          v                             v                             |
+---------+---------+       +-----------+-----------+                 |
|                   |       |                       |                 |
|   Simulated PUF   +------>+  HKDF Key Derivation  |                 |
|                   |       |                       |                 |
+-------------------+       +-----------+-----------+                 |
                                        |                             |
                                        | 2. Generate 256-bit Key     |
                                        v                             |
                            +-----------+-----------+                 |
                            | AES-256-CBC Decryptor |                 |
                            | (Streaming Mode)      |                 |
                            +-----------+-----------+                 |
                                        ^                             |
                                        |                             |
                            +-----------+-----------+                 |
                            | Encrypted LLM Payload |                 |
                            | (.cpuf_llm tarball)   |                 |
                            +-----------------------+                 |
                                                                      |
                            3. Decrypt chunks & Write to RAM Disk     |
                            =========================================>|
                                                                      v
                                                            +---------+---------+
                                                            |  Decrypted LLM    |
                                                            |  Model Weights    |
                                                            +---------+---------+
                                                                      |
                                                            4. Load to VRAM     |
                                                            ===================>|
                                                                      |
                            5. Zeroize & Unmount RAM Disk             |
                            <=========================================+
```

### Mimari Modüller
- `simulated_puf.py`: Cihaz parmak izlerinden 256-bit entropi anahtarı türeterek donanım PUF simülasyonu yapar.
- `llm_encryptor.py`: Standart LLM model klasörünü alır ve AES-256 CBC Streaming şifreli bir `.cpuf_llm` paketi çıkarır.
- `llm_secure_loader.py`: `tmpfs` RAM diskini bağlayan, çalışma zamanında deşifre eden ve kullanım sonrası RAM'den güvenli zeroize ile silen sarıcı.
- `main_app.py`: Süreçleri takip edebileceğiniz Flask tabanlı karanlık temalı SSE web paneli.

---

## 🇬🇧 English

**CyberPUF LLM Edition** is an advanced Hardware Security and Edge-AI project designed to secure the Intellectual Property (IP) of Large Language Models (LLMs) deployed on edge devices and local hardware. 

This project is an evolution of the original [CyberPUF](https://github.com/mecik-arda/CyberPUF) architecture, adapted to handle the massive weight architectures of modern LLMs (like Qwen, Llama, Phi) without introducing severe latency or memory bottlenecks through streaming encryption.

### The Core Problem
When multi-billion parameter AI models are deployed on edge devices, their weights (often stored as `.safetensors` or `.bin`) reside in the local storage. Hackers can easily copy these files, effectively stealing millions of dollars worth of AI research and proprietary fine-tuning. Traditional full-disk encryption requires the key to be stored somewhere on the device, which can be extracted.

### The CyberPUF Solution
CyberPUF LLM Edition introduces a **Secure RAM-Disk Wrapper** architecture relying on Physical Unclonable Functions (PUF):

1. **AES-256 Encryption:** The LLM directory is compressed and encrypted into a single `.cpuf_llm` payload using streaming.
2. **PUF Derived Keys:** The encryption/decryption key is never stored on disk. It is generated dynamically at runtime using hardware fingerprints and HKDF.
3. **Volatile RAM-Disk (tmpfs) Decryption:** At runtime, the model is **never** decrypted back to the physical SSD. Instead, Linux `tmpfs` is used to create a secure memory-mapped disk. The weights are decrypted directly into RAM.
4. **Zeroization:** The moment the inference engine loads the weights into active memory/VRAM, the decrypted RAM-disk is permanently wiped via memory overwriting (`memset`) and unmounted.

*(See the ASCII Architecture Diagram in the Turkish section above for details).*

### Architecture Modules
- `simulated_puf.py`: Simulates the hardware PUF by generating a 256-bit entropy key derived from device fingerprints.
- `llm_encryptor.py`: Takes a standard LLM model directory and outputs an AES-256 CBC encrypted `.cpuf_llm` package via chunks.
- `llm_secure_loader.py`: The secure wrapper that mounts the `tmpfs` RAM disk, decrypts the payload on-the-fly, and securely zeroizes the data post-load.
- `main_app.py`: Flask-based modern dark UI to manage encryption/decryption workflows.

---

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Developer:** Arda Meçik
