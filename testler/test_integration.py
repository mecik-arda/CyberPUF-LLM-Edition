import os
import pytest
from llm_encryptor import encrypt_directory
from llm_secure_loader import SecureRAMLoader

def test_full_integration(temp_workspace):
    """
    Uçtan uca test:
    1. Sahte LLM klasörü oluşturulur.
    2. Modül kullanılarak .cpuf_llm formatında şifrelenir.
    3. SecureRAMLoader ile RAM diske deşifre edilir.
    4. Model ağırlığının (veri) bozulmadan aktarıldığı kontrol edilir.
    5. Zeroize tetiklenerek bellekten tamamen silindiği doğrulanır.
    """
    model_dir = "fake_model_int"
    os.makedirs(model_dir)
    with open(os.path.join(model_dir, "test.bin"), "wb") as f:
        f.write(b"cyberpuf-integration-test-data")
        
    cpuf_file = "integration.cpuf_llm"
    
    # Şifrele
    encrypt_directory(model_dir, cpuf_file)
    assert os.path.exists(cpuf_file)
    
    # Deşifre Et (Yükle)
    loader = SecureRAMLoader(cpuf_file, ram_mount_point="int_ramdisk")
    loader.mount_ramdisk()
    loaded_path = loader.decrypt_to_ram()
    
    assert os.path.exists(loaded_path), "Model deşifre edilemedi."
    assert "test.bin" in os.listdir(loaded_path), "Modelin içindeki ağırlık dosyası bulunamadı."
    
    with open(os.path.join(loaded_path, "test.bin"), "rb") as f:
        assert f.read() == b"cyberpuf-integration-test-data", "Deşifre edilen veri aslıyla uyuşmuyor!"
        
    # Zeroize Et (Sıfırlayarak sil)
    loader.zeroize_and_unmount()
    assert not os.path.exists(loaded_path), "Zeroize işlemi başarısız. Klasör hâlâ duruyor!"
