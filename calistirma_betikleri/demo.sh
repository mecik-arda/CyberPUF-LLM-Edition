#!/bin/bash
set -e

# Sanal ortam python dizini
PYTHON_BIN="../../ai_env/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

echo "=========================================="
echo "CyberPUF-LLM-Edition Uçtan Uca Demo Betiği"
echo "=========================================="

echo "[1/6] 50MB sahte LLM model ağırlığı oluşturuluyor..."
mkdir -p demo_model
dd if=/dev/urandom of=demo_model/model.safetensors bs=1M count=50 status=none

echo "[2/6] llm_encryptor.py ile şifreleme işlemi yapılıyor..."
$PYTHON_BIN ../llm_encryptor.py demo_model demo_model.cpuf_llm

echo "[3/6] Şifreli model RAM diske yükleniyor (Deşifreleme)..."
cat << 'EOF' > run_loader.py
import sys
import time
sys.path.insert(0, '../')
from llm_secure_loader import SecureRAMLoader
loader = SecureRAMLoader('demo_model.cpuf_llm', ram_mount_point='/tmp/demo_ramdisk')
loader.mount_ramdisk()
path = loader.decrypt_to_ram()
print(f"Model Hazır! Yüklendiği Konum: {path}")
time.sleep(1)
print("[5/6] Zeroize işlemi tetikleniyor...")
loader.zeroize_and_unmount()
EOF

echo "[4/6] Model Hazır mesajı bekleniyor..."
$PYTHON_BIN run_loader.py

echo "[6/6] Demo ortamı temizleniyor..."
rm -rf demo_model demo_model.cpuf_llm run_loader.py

echo "=========================================="
echo "Demo Başarıyla Tamamlandı!"
echo "=========================================="
