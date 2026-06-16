import os
import sys
import time
import hashlib
import subprocess
from flask import Flask, request, jsonify, render_template, Response
import simulated_puf

app = Flask(__name__, static_folder='static', template_folder='static')

# Bellek içi durum takibi
app_status = {
    "start_time": time.time(),
    "ramdisk_path": "/tmp/secure_llm_ram",
    "model_loaded": False,
}

def get_puf_hash():
    # PUF anahtarından ilk 8 karakterlik hex özet
    key = simulated_puf.extract_puf_key()
    return hashlib.sha256(key).hexdigest()[:8]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    uptime = time.time() - app_status["start_time"]
    return jsonify({
        "puf_hash": get_puf_hash(),
        "ramdisk_mounted": os.path.exists(app_status["ramdisk_path"]),
        "ramdisk_path": app_status["ramdisk_path"],
        "model_loaded": app_status["model_loaded"],
        "uptime": int(uptime)
    })

@app.route('/api/encrypt', methods=['POST'])
def encrypt_model():
    data = request.json
    model_path = data.get("model_path")
    output_path = data.get("output_path")
    if not model_path or not output_path:
        return jsonify({"error": "model_path ve output_path gereklidir"}), 400
        
    base_dir = os.path.abspath("/home/ardam/local_ai")
    try:
        abs_model = os.path.abspath(model_path)
        abs_out = os.path.abspath(output_path)
        if not abs_model.startswith(base_dir) or not abs_out.startswith(base_dir):
            return jsonify({"error": "Güvensiz dizin erişimi reddedildi"}), 403
    except Exception:
        return jsonify({"error": "Yol doğrulama hatası"}), 400
        
    def generate():
        import queue
        import threading
        import sys
        from llm_encryptor import encrypt_directory
        
        q = queue.Queue()
        
        def worker():
            class StreamCapture:
                def write(self, s):
                    if s.strip():
                        q.put(s.strip())
                def flush(self):
                    pass
            original_stdout = sys.stdout
            sys.stdout = StreamCapture()
            try:
                encrypt_directory(abs_model, abs_out)
            except Exception as e:
                q.put(f"Hata: {e}")
            finally:
                sys.stdout = original_stdout
                q.put(None)
                
        threading.Thread(target=worker).start()
        
        while True:
            msg = q.get()
            if msg is None:
                break
            yield f"data: {msg}\n\n"
            
        yield "data: [BİTTİ]\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/load', methods=['POST'])
def load_model():
    data = request.json
    cpuf_path = data.get("cpuf_llm_path")
    if not cpuf_path:
        return jsonify({"error": "cpuf_llm_path gereklidir"}), 400
        
    def generate():
        import queue
        import threading
        import sys
        from llm_secure_loader import SecureRAMLoader
        
        q = queue.Queue()
        
        def worker():
            class StreamCapture:
                def write(self, s):
                    if s.strip():
                        q.put(s.strip())
                def flush(self):
                    pass
            original_stdout = sys.stdout
            sys.stdout = StreamCapture()
            try:
                loader = SecureRAMLoader(cpuf_path)
                loader.mount_ramdisk()
                path = loader.decrypt_to_ram()
                q.put(f"Model Yüklendi: {path}")
                app_status["model_loaded"] = True
            except Exception as e:
                q.put(f"Hata: {e}")
            finally:
                sys.stdout = original_stdout
                q.put(None)
                
        threading.Thread(target=worker).start()
        
        while True:
            msg = q.get()
            if msg is None:
                break
            yield f"data: {msg}\n\n"
            
        yield "data: [BİTTİ]\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/zeroize', methods=['POST'])
def zeroize():
    def generate():
        import queue
        import threading
        import sys
        from llm_secure_loader import SecureRAMLoader
        
        q = queue.Queue()
        
        def worker():
            class StreamCapture:
                def write(self, s):
                    if s.strip():
                        q.put(s.strip())
                def flush(self):
                    pass
            original_stdout = sys.stdout
            sys.stdout = StreamCapture()
            try:
                loader = SecureRAMLoader('')
                loader.zeroize_and_unmount()
                app_status["model_loaded"] = False
            except Exception as e:
                q.put(f"Hata: {e}")
            finally:
                sys.stdout = original_stdout
                q.put(None)
                
        threading.Thread(target=worker).start()
        
        while True:
            msg = q.get()
            if msg is None:
                break
            yield f"data: {msg}\n\n"
            
        yield "data: [BİTTİ]\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
