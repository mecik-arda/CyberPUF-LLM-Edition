import time
from collections import defaultdict

class AnomalyDetector:
    def __init__(self, threshold=3, time_window=300):
        # Varsayılan: 300 saniye (5 dakika) içinde 3 yükleme denemesi
        self.threshold = threshold
        self.time_window = time_window
        self.access_logs = defaultdict(list)
        
    def log_access(self, file_path):
        current_time = time.time()
        
        # Sadece belirlenen zaman penceresi (time_window) içerisindeki logları tut
        self.access_logs[file_path] = [
            t for t in self.access_logs[file_path] 
            if current_time - t <= self.time_window
        ]
        
        self.access_logs[file_path].append(current_time)
        
        if len(self.access_logs[file_path]) >= self.threshold:
            self._trigger_alarm(file_path)
            return True # Alarm durumu tetiklendi
        return False
        
    def _trigger_alarm(self, file_path):
        print(f"[ALARM] Anormal bellek erişimi (RAM) tespit edildi! Dosya: {file_path}")
        print(f"[UYARI] {self.time_window} saniye içinde {self.threshold} kez deşifre denemesi yapıldı. Sistem geçici olarak kilitleniyor...")
        # NOT: Gerçek prodüksiyon senaryosunda bu aşamada webhook tetiklenir, E-posta atılır 
        # ve RAM disk'te aktif bir model varsa derhal `zeroize` komutu çağrılarak imha edilir.
