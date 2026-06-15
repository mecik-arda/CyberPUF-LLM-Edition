import os
import pytest
from llm_secure_loader import SecureRAMLoader

def test_loader_mount_fallback(temp_workspace):
    """Sudo izni olmadan (veya test ortamında) tmpfs mount işleminin başarılı şekilde fallback yapıp yapmadığını test eder."""
    loader = SecureRAMLoader("dummy.cpuf", ram_mount_point="mock_ramdisk")
    loader.mount_ramdisk()
    assert os.path.exists("mock_ramdisk"), "Fallback RAM Disk simülasyon klasörü oluşturulamadı."
