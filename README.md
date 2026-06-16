# CyberPUF LLM Edition (Proof of Concept)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-Proof%20of%20Concept-orange)

[Türkçe](#türkçe) | [English](#english)

---

## Türkçe

**CyberPUF LLM Edition**, sınır cihazlarda (edge devices) ve yerel donanımlarda çalışan Büyük Dil Modellerinin (LLM) fikri mülkiyetini (IP) güvence altına almak için tasarlanmış gelişmiş bir Donanım Güvenliği ve Edge-AI projesidir.

Bu proje, orijinal [CyberPUF](https://github.com/mecik-arda/CyberPUF) mimarisinin bir evrimi olup, modern LLM'lerin (Qwen, Llama, Phi vb.) devasa ağırlık mimarilerini ciddi gecikmeler (latency) veya bellek darboğazları yaratmadan şifreleyebilecek şekilde uyarlanmıştır.

### Temel Problem
Milyarlarca parametreli yapay zeka modelleri sınır cihazlara yüklendiğinde, ağırlık dosyaları (`.safetensors` veya `.bin`) yerel diskte saklanır. Kötü niyetli kişiler bu dosyaları kolayca kopyalayarak milyonlarca dolarlık yapay zeka araştırmalarını ve özel ince ayarları (fine-tuning) çalabilir. Geleneksel tam disk şifreleme yöntemleri, cihazın bir yerinde saklanan ve ele geçirilebilecek bir anahtar gerektirir.

### CyberPUF Çözümü
CyberPUF LLM Edition, Fiziksel Klonlanamaz Fonksiyonlara (PUF) dayanan bir **Güvenli RAM-Disk / FUSE Wrapper** mimarisi sunar:

1. **Hugging Face Streaming & AES-256 Şifreleme:** LLM dizini sıkıştırılır ve tek bir `.cpuf_llm` dosyasına (Streaming ile chunklar halinde) şifrelenir. Ayrıca `/hf-indir` komutuyla modeller diske kaydedilmeden anında (on-the-fly) şifrelenebilir.
2. **Gelişmiş PUF Entropisi:** Şifreleme anahtarı diskte asla saklanmaz. OS Kernel, UUID, MAC ve dinamik `salt` değerlerinden beslenen donanım parmak izi (SRAM/RO-PUF simülasyonu) kullanılarak dinamik üretilir.
3. **RAM-Disk & FUSE (On-The-Fly) Deşifreleme:** Çalışma zamanında model **asla** fiziksel diske (SSD) deşifre edilmez. Kullanıcının `config.json` seçimine bağlı olarak ya Linux `tmpfs` üzerinden RAM-Disk'e ya da `fusepy` ile tamamen sanal (VFS) olarak diske açılır.
4. **Akıllı Zeroization & TEE:** Çıkarım motoru ana süreci sonlandırdığında PID takibi (Smart Zeroize) tetiklenir. Tüm şifresiz veriler kalıcı olarak sıfırlarla ezilir (`memset`) ve RAM-disk sökülür. Proje ayrıca Intel SGX / AMD SEV tabanlı TEE (Trusted Execution Environment) Docker altyapısına da tam uyumludur.

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

### Kurulum

#### 1. Ön Gereksinimler
- **Linux/WSL:** Linux `tmpfs` RAM disk özelliği kullanıldığı için bu proje Linux veya Windows Subsystem for Linux (WSL) üzerinde çalışacak şekilde tasarlanmıştır.
- **Python:** Python 3.10+ sürümü gereklidir.
- **Sudo Yetkisi:** RAM disk oluşturup bağlama (`mount/umount`) işlemleri için kullanıcının sudo yetkisine sahip olması veya `/etc/sudoers` dosyasında `mount` ve `umount` komutlarının şifresiz (`NOPASSWD`) yapılandırılmış olması gerekir.

#### 2. Deponun İndirilmesi
```bash
git clone --recursive https://github.com/mecik-arda/CyberPUF-LLM-Edition.git
cd CyberPUF-LLM-Edition
```

#### 3. Sanal Ortam Oluşturma ve Bağımlılıklar
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 4. Yapılandırma (.env)
`.env.example` dosyasını `.env` olarak kopyalayın ve gerekli değerleri doldurun:
```bash
cp .env.example .env
```
- `CYBERPUF_AES_KEY`: 64 karakterli güvenli bir hex anahtarı üretip buraya yazın. (Örn: `openssl rand -hex 32` komutu ile üretebilirsiniz).
- `WEBSOCKET_TOKEN`: Gerçek zamanlı arayüz iletişimi için kullanılacak güçlü bir rastgele anahtar yazın.
- `APP_HOST`: `127.0.0.1` veya sunucu IP adresi.
- `APP_PORT`: Sunucunun çalışacağı port (Varsayılan: `8000`).

---

### Kullanım

#### A. CLI Komutları ile Modeli Şifreleme ve Yükleme
Uygulamayı doğrudan komut satırı araçları ile çalıştırabilirsiniz:

1. **Model Şifreleme (Encryption):**
   ```bash
   python3 llm_encryptor.py /yol/to/model_klasoru /yol/to/cikti_dosyasi.cpuf_llm
   ```
   *Bu komut, belirtilen klasördeki tüm ağırlıkları sıkıştırıp cihaz donanımından türetilen PUF anahtarıyla şifreler.*

2. **Model Yükleme (Decryption & RAM-Disk Mount):**
   ```bash
   python3 llm_secure_loader.py /yol/to/cikti_dosyasi.cpuf_llm
   ```
   *Bu komut, geçici bir RAM disk bağlar, şifreli modeli RAM diske çözer ve bellekten silmek (Zeroize) için ENTER tuşuna basmanızı bekler.*

#### B. Web Dashboard (Arayüz) ile Çalıştırma
Tüm işlemleri görselleştirmek ve gerçek zamanlı takip etmek için modern web arayüzünü şu yöntemlerden biriyle başlatabilirsiniz:

1. **Hazır Çalıştırma Betikleri ile (Önerilen):**
   - **Linux / WSL:**
     ```bash
     chmod +x run_linux.sh
     ./run_linux.sh
     ```
   - **Windows:**
     Doğrudan `run_win.bat` dosyasına çift tıklayarak ya da terminalde çalıştırarak başlatabilirsiniz.

2. **`underw` CLI Aracı ile:**
   Eğer sisteminizde `underw` CLI aracı tanımlıysa:
   ```bash
   underw start
   ```

3. **Manuel Olarak:**
   ```bash
   python3 calistirma_betikleri/start_app.py
   ```
Sunucu ayağa kalktığında tarayıcınızda otomatik olarak `http://127.0.0.1:8000` adresi açılacaktır. Arayüzden model yükleme ve şifreleme adımlarını canlı olarak izleyebilirsiniz.

#### C. Testleri Çalıştırma (Pytest)
Projedeki tüm güvenlik, entegrasyon ve şifreleme modüllerini test etmek için pytest komutunu kullanabilirsiniz:
```bash
PYTHONPATH=. pytest
```

---

## English

**CyberPUF LLM Edition** is an advanced Hardware Security and Edge-AI project designed to secure the Intellectual Property (IP) of Large Language Models (LLMs) deployed on edge devices and local hardware. 

This project is an evolution of the original [CyberPUF](https://github.com/mecik-arda/CyberPUF) architecture, adapted to handle the massive weight architectures of modern LLMs (like Qwen, Llama, Phi) without introducing severe latency or memory bottlenecks through streaming encryption.

### The Core Problem
When multi-billion parameter AI models are deployed on edge devices, their weights (often stored as `.safetensors` or `.bin`) reside in the local storage. Hackers can easily copy these files, effectively stealing millions of dollars worth of AI research and proprietary fine-tuning. Traditional full-disk encryption requires the key to be stored somewhere on the device, which can be extracted.

### The CyberPUF Solution
CyberPUF LLM Edition introduces a **Secure RAM-Disk / FUSE Wrapper** architecture relying on Physical Unclonable Functions (PUF):

1. **Hugging Face Streaming & AES-256 Encryption:** The LLM directory is compressed and encrypted into a single `.cpuf_llm` payload. You can also download and encrypt HF models on-the-fly without saving to disk in plaintext.
2. **Enhanced PUF Derived Keys:** The encryption/decryption key is never stored on disk. It is generated dynamically at runtime using hardware fingerprints (OS Kernel, UUID, MAC, and dynamic salt) and HKDF.
3. **Volatile RAM-Disk & FUSE Decryption:** At runtime, the model is **never** decrypted back to the physical SSD. Based on `config.json` choices, it either uses Linux `tmpfs` RAM disk or `fusepy` for a completely virtual filesystem.
4. **Smart Zeroization & TEE:** A PID tracker automatically triggers zeroization when the inference engine terminates. The decrypted RAM-disk is permanently wiped via memory overwriting (`memset`) and unmounted. The project also ships with a mock TEE (Intel SGX/AMD SEV) Docker infrastructure.

*(See the ASCII Architecture Diagram in the Turkish section above for details).*

### Architecture Modules
- `simulated_puf.py`: Simulates the hardware PUF by generating a 256-bit entropy key derived from device fingerprints.
- `llm_encryptor.py`: Takes a standard LLM model directory and outputs an AES-256 CBC encrypted `.cpuf_llm` package via chunks.
- `llm_secure_loader.py`: The secure wrapper that mounts the `tmpfs` RAM disk, decrypts the payload on-the-fly, and securely zeroizes the data post-load.
- `main_app.py`: Flask-based modern dark UI to manage encryption/decryption workflows.

---

### Installation

#### 1. Prerequisites
- **Linux/WSL:** Linux `tmpfs` RAM disk features are required. This project is meant to run under Linux or WSL environment.
- **Python:** Python 3.10+ is required.
- **Sudo Privileges:** The process requires `sudo` privileges to run `mount` and `umount` commands. Alternatively, configure your `/etc/sudoers` to allow passwordless mounting for your user.

#### 2. Clone the Repository
```bash
git clone --recursive https://github.com/mecik-arda/CyberPUF-LLM-Edition.git
cd CyberPUF-LLM-Edition
```

#### 3. Setup Virtual Environment & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 4. Configure Environment (.env)
Copy the `.env.example` file to `.env` and configure the settings:
```bash
cp .env.example .env
```
- `CYBERPUF_AES_KEY`: Generate a secure 64-character hex key (e.g. using `openssl rand -hex 32`).
- `WEBSOCKET_TOKEN`: A strong random string for secure real-time communications.
- `APP_HOST`: `127.0.0.1` or your server's IP address.
- `APP_PORT`: Server port (Default: `8000`).

---

### Usage

#### A. CLI Commands for Model Encryption & Mounting
Run the tools directly from your CLI terminal:

1. **Encrypt a Model:**
   ```bash
   python3 llm_encryptor.py /path/to/model_folder /path/to/output_file.cpuf_llm
   ```
   *This command archives the directory and encrypts the binary payload using the hardware-derived key.*

2. **Mount & Decrypt a Model (Secure RAM-Loader):**
   ```bash
   python3 llm_secure_loader.py /path/to/output_file.cpuf_llm
   ```
   *This command spins up a temporary secure RAM disk, decrypts the payload into memory, and waits for a keypress to securely Zeroize the RAM disk.*

#### B. Launching the Web Dashboard
Use the interactive web panel to trigger encryption and loading pipelines. You can launch it using one of the following methods:

1. **Using Run Scripts (Recommended):**
   - **Linux / WSL:**
     ```bash
     chmod +x run_linux.sh
     ./run_linux.sh
     ```
   - **Windows:**
     Simply double-click on `run_win.bat` or run it from the Windows Command Prompt/PowerShell.

2. **Using the `underw` CLI tool:**
   If you have the `underw` CLI tool configured:
   ```bash
   underw start
   ```

3. **Manually:**
   ```bash
   python3 calistirma_betikleri/start_app.py
   ```
Open your browser and navigate to `http://127.0.0.1:8000`.

#### C. Running Unit and Integration Tests (Pytest)
Run the test suite using pytest to verify encryption, mounting, and decryption logic:
```bash
PYTHONPATH=. pytest
```

---

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Developer:** Arda Meçik
