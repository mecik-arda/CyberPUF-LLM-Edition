import os
import pytest
from llm_encryptor import encrypt_directory

def test_encryption_roundtrip(temp_workspace):
    """1 MB'lık sahte bir LLM modelini şifreleme ve Magic Header kontrolü."""
    model_dir = "fake_model"
    os.makedirs(model_dir)
    with open(os.path.join(model_dir, "weights.bin"), "wb") as f:
        f.write(os.urandom(1024 * 1024)) # 1MB random veri
        
    out_file = "model.cpuf_llm"
    encrypt_directory(model_dir, out_file)
    
    assert os.path.exists(out_file), "Şifrelenmiş dosya oluşturulamadı."
    assert os.path.getsize(out_file) > 1024 * 1024, "Şifrelenmiş dosya boyutu çok küçük."
    
    with open(out_file, "rb") as f:
        magic = f.read(8)
        assert magic == b"CPUF_LLM", "Dosya başlığı (Magic Header) doğrulanamadı."
