# CyberPUF LLM Edition (Proof of Concept)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-Proof%20of%20Concept-orange)

**CyberPUF LLM Edition** is an advanced Hardware Security and Edge-AI project designed to secure the Intellectual Property (IP) of Large Language Models (LLMs) deployed on edge devices and local hardware. 

This project is an evolution of the original [CyberPUF](https://github.com/mecik-arda/CyberPUF) architecture, adapted to handle the massive weight architectures of modern LLMs (like Qwen, Llama, Phi) without introducing severe latency or memory bottlenecks.

## The Core Problem
When multi-billion parameter AI models are deployed on edge devices, their weights (often stored as `.safetensors` or `.bin`) reside in the local storage. Hackers can easily copy these files, effectively stealing millions of dollars worth of AI research and proprietary fine-tuning.

Traditional full-disk encryption requires the key to be stored somewhere on the device, which can be extracted.

## The CyberPUF Solution
CyberPUF LLM Edition introduces a **Secure RAM-Disk Wrapper** architecture relying on Physical Unclonable Functions (PUF):

1. **AES-256 Encryption:** The LLM directory is compressed and encrypted into a single `.cpuf_llm` payload.
2. **PUF Derived Keys:** The encryption/decryption key is never stored on disk. It is generated dynamically at runtime using hardware fingerprints (simulating an SRAM/RO-PUF).
3. **Volatile RAM-Disk (tmpfs) Decryption:** At runtime, the model is **never** decrypted back to the physical SSD. Instead, Linux `tmpfs` is used to create a secure memory-mapped disk. The weights are decrypted directly into RAM.
4. **Zeroization:** The moment the inference engine (e.g., OpenVINO, Llama.cpp, Transformers) loads the weights into active memory/VRAM, the decrypted RAM-disk is permanently wiped and unmounted.

## Architecture Modules

- `simulated_puf.py`: Simulates the hardware PUF by generating a 256-bit entropy key derived from device fingerprints.
- `llm_encryptor.py`: Takes a standard HuggingFace/OpenVINO model directory and outputs an AES-256 CBC encrypted `.cpuf_llm` package.
- `llm_secure_loader.py`: The secure wrapper that mounts the `tmpfs` RAM disk, decrypts the payload on-the-fly, and securely zeroizes the data post-load.

## Usage (Proof of Concept)

### 1. Encrypting a Model
```bash
python llm_encryptor.py /path/to/huggingface_model /path/to/output.cpuf_llm
```

### 2. Securely Loading the Model
```python
from llm_secure_loader import SecureRAMLoader

# Initialize the loader
loader = SecureRAMLoader("output.cpuf_llm")

# Mount a secure tmpfs RAM disk
loader.mount_ramdisk()

# Decrypt weights directly into RAM
secure_model_path = loader.decrypt_to_ram()

# -> (Load your model using transformers/OpenVINO from secure_model_path here) <-

# Destroy the RAM disk permanently
loader.zeroize_and_unmount()
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
**Developer:** Arda Meçik
