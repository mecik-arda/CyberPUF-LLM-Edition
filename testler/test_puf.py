import pytest
import simulated_puf

def test_deterministic_behavior():
    """Aynı donanımda PUF anahtarının deterministik olarak hep aynı çıkması testi."""
    hw1 = simulated_puf.generate_hardware_fingerprint()
    hw2 = simulated_puf.generate_hardware_fingerprint()
    assert hw1 == hw2, "Donanım parmak izi deterministik değil!"
    
    k1 = simulated_puf.extract_puf_key()
    k2 = simulated_puf.extract_puf_key()
    assert k1 == k2, "Üretilen anahtar deterministik değil!"

def test_puf_key_length():
    """Üretilen PUF anahtarının tam olarak 256-bit (32 byte) olmasının testi."""
    key = simulated_puf.extract_puf_key()
    assert len(key) == 32

def test_entropy_simulation(monkeypatch):
    """
    Farklı donanımlarda farklı anahtar üretme testi (Entropi).
    UUID (MAC adresi) donanımı simüle etmek adına sahteleştirilmiştir.
    100 farklı makine için tam olarak 100 farklı 256-bit anahtar çıkmalıdır.
    """
    keys = set()
    for i in range(100):
        # Farklı makineler simülasyonu
        monkeypatch.setattr(simulated_puf.uuid, "getnode", lambda x=i: x)
        key = simulated_puf.extract_puf_key()
        keys.add(key)
    
    assert len(keys) == 100, "PUF Entropisi yetersiz, çakışma (collision) bulundu!"
