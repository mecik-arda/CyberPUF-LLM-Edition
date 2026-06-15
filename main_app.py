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
        
    def generate():
        cmd = [sys.executable, "llm_encryptor.py", model_path, output_path]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line.strip()}\n\n"
        process.stdout.close()
        process.wait()
        yield "data: [BİTTİ]\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/load', methods=['POST'])
def load_model():
    data = request.json
    cpuf_path = data.get("cpuf_llm_path")
    if not cpuf_path:
        return jsonify({"error": "cpuf_llm_path gereklidir"}), 400
        
    def generate():
        inline_script = f"""
import sys
from llm_secure_loader import SecureRAMLoader
try:
    loader = SecureRAMLoader('{cpuf_path}')
    loader.mount_ramdisk()
    path = loader.decrypt_to_ram()
    print(f"Model Yüklendi: {{path}}")
except Exception as e:
    print(f"Hata: {{e}}")
"""
        cmd = [sys.executable, "-c", inline_script]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line.strip()}\n\n"
        process.stdout.close()
        process.wait()
        if process.returncode == 0:
            app_status["model_loaded"] = True
        yield "data: [BİTTİ]\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/zeroize', methods=['POST'])
def zeroize():
    def generate():
        inline_script = f"""
from llm_secure_loader import SecureRAMLoader
try:
    loader = SecureRAMLoader('')
    loader.zeroize_and_unmount()
except Exception as e:
    print(f"Hata: {{e}}")
"""
        cmd = [sys.executable, "-c", inline_script]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line.strip()}\n\n"
        process.stdout.close()
        process.wait()
        app_status["model_loaded"] = False
        yield "data: [BİTTİ]\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
