import pytest
import os
import shutil

@pytest.fixture
def temp_workspace(tmp_path):
    """Testler sırasında izole bir geçici çalışma dizini sağlar."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield str(tmp_path)
    os.chdir(original_cwd)
