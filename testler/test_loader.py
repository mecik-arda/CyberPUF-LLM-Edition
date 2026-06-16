import os
import pytest
import subprocess
from unittest.mock import patch
from llm_secure_loader import SecureRAMLoader

@patch('subprocess.run')
def test_loader_mount_fails_securely(mock_run, temp_workspace):
    """Sudo izni olmadığında sistemin fail-closed prensibiyle Exception fırlattığını test eder."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="mount", timeout=5)
    loader = SecureRAMLoader("dummy.cpuf", ram_mount_point="mock_ramdisk")
    with pytest.raises(RuntimeError, match=r"\[Kritik\] RAM Disk \(tmpfs\) oluşturulamadı"):
        loader.mount_ramdisk()
