import os
import sys
import asyncio
import shutil
import re
import hmac
import json
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Set
import base64
import io
import numpy as np
from PIL import Image
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, status

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title="CyberPUF Dashboard")

# Load environment variables from .env file
load_dotenv()

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # CSRF Check
    if request.url.path.startswith("/api/") and request.method in ["POST", "PUT", "DELETE"]:
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JSONResponse(status_code=403, content={"detail": "CSRF verification failed"})
            
    response = await call_next(request)
    
    # Security Headers
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' ws: wss:; img-src 'self' data:"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# CORS configuration from environment
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
allow_creds = True
if "*" in allowed_origins:
    allowed_origins = ["*"]
    allow_creds = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_creds,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        if not self.active_connections:
            return
            
        async def send_to_conn(conn):
            try:
                await conn.send_text(message)
                return None
            except Exception:
                return conn
                
        results = await asyncio.gather(*(send_to_conn(conn) for conn in list(self.active_connections)))
        
        for failed_conn in filter(None, results):
            self.disconnect(failed_conn)

manager = ConnectionManager()
running_tasks = {}
_background_tasks = set()

os.makedirs(os.path.join("static", "test_images"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join("static")), name="static")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    ws_token = os.environ.get("WEBSOCKET_TOKEN")
    if not ws_token:
        await websocket.close(code=1008, reason="Token not configured")
        return
    await manager.connect(websocket)
    
    try:
        import json
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
        auth_data = json.loads(auth_msg)
        if auth_data.get("type") != "auth" or not hmac.compare_digest(auth_data.get("token", ""), ws_token):
            raise Exception("Invalid auth")
    except Exception:
        manager.disconnect(websocket)
        await websocket.close(code=1008, reason="Invalid token")
        return

    # Token Bucket Flooding protection
    bucket_capacity = 50
    tokens = bucket_capacity
    last_msg_time = asyncio.get_running_loop().time()
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Payload size limit (e.g., 4096 bytes)
            if len(data) > 4096:
                await websocket.close(code=1009, reason="Message too large")
                break
                
            current_time = asyncio.get_running_loop().time()
            elapsed = current_time - last_msg_time
            last_msg_time = current_time
            
            # Refill tokens (10 per second)
            tokens = min(bucket_capacity, tokens + elapsed * 10)
            
            if tokens < 1:
                # Rate limit exceeded, warn and throttle instead of disconnecting immediately
                try:
                    await websocket.send_text(json.dumps({"type": "log", "task_id": "system", "task_name": "Sistem", "message": "[UYARI] Ağ trafiği kısıtlaması: Rate-limit aşıldı, lütfen yavaşlayın."}))
                except Exception:
                    pass
                await asyncio.sleep(0.5)
                continue
                
            tokens -= 1
            
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

async def run_subprocess_and_broadcast(cmd: list, cwd: str, task_name: str, task_id: str, max_timeout: int = None, extra_env: dict = None):
    if task_id in running_tasks:
        await manager.broadcast(json.dumps({"type": "log", "task_id": task_id, "task_name": task_name, "message": f"[{task_name}] Zaten calisiyor!"}))
        return
    running_tasks[task_id] = True
    
    cmd_log = [c if "python" not in c.lower() else "python" for c in cmd]
    await manager.broadcast(json.dumps({"type": "log", "task_id": task_id, "task_name": task_name, "message": f"[{task_name}] Baslatiliyor: {' '.join(cmd_log)}"}))
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    if extra_env:
        env.update(extra_env)
    
    aes_key = os.environ.get("CYBERPUF_AES_KEY")
    if not aes_key:
        await manager.broadcast(json.dumps({"type": "log", "task_id": task_id, "task_name": task_name, "message": f"[{task_name}] HATA: CYBERPUF_AES_KEY ortam degiskeni bulunamadi! (Fail-safe)"}))
        del running_tasks[task_id]
        return
    env["CYBERPUF_AES_KEY"] = aes_key

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env
        )

        async def read_stdout():
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                try:
                    await manager.broadcast(json.dumps({
                        "type": "log", 
                        "task_id": task_id, 
                        "task_name": task_name, 
                        "message": line.decode('utf-8', errors='replace').rstrip()
                    }))
                except Exception:
                    pass

        read_task = asyncio.create_task(read_stdout())
        _background_tasks.add(read_task)
        read_task.add_done_callback(_background_tasks.discard)
        try:
            try:
                env_timeout = int(os.environ.get("SUBPROCESS_TIMEOUT", "600"))
            except ValueError:
                env_timeout = 600
            timeout = max_timeout or env_timeout
            await asyncio.wait_for(process.wait(), timeout=timeout)
            await manager.broadcast(json.dumps({"type": "log", "task_id": task_id, "task_name": task_name, "message": f"[{task_name}] Tamamlandi. Cikis Kodu: {process.returncode}"}))
        except asyncio.TimeoutError:
            process.kill()
            await manager.broadcast(json.dumps({"type": "log", "task_id": task_id, "task_name": task_name, "message": f"[{task_name}] HATA: Zaman asimi ({timeout}s). Islem sonlandirildi."}))
            await process.wait()
    finally:
        if task_id in running_tasks:
            del running_tasks[task_id]

class EncryptionMode(str, Enum):
    CBC = "CBC"
    GCM = "GCM"

class QuantMode(str, Enum):
    int8_weight = "int8_weight"
    fp32 = "fp32"

class TrainParams(BaseModel):
    epochs: int = Field(gt=0, le=1000)
    batch_size: int = Field(gt=0, le=2048)
    learning_rate: float = Field(gt=0.0)
    encryption_mode: EncryptionMode
    quant_mode: QuantMode

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    expected_token = os.environ.get("WEBSOCKET_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=500, detail="Token config missing")
    if not hmac.compare_digest(credentials.credentials, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return credentials.credentials



@app.post("/api/train")
async def start_training(params: TrainParams, token: str = Depends(verify_token)):
    if "phase1" in running_tasks:
        return {"error": "Zaten calisiyor"}
    cmd = [
        sys.executable, "calistirma_betikleri/run_phase1.py",
        str(params.epochs),
        str(params.batch_size),
        str(params.learning_rate),
        params.encryption_mode.value,
        params.quant_mode.value
    ]
    task = asyncio.create_task(run_subprocess_and_broadcast(cmd, ".", "AI Pipeline (Phase 1)", "phase1"))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"message": "Egitim baslatildi"}

@app.post("/api/simulate_hw")
async def start_hw_simulation(token: str = Depends(verify_token)):
    if "phase2" in running_tasks:
        return {"error": "Zaten calisiyor"}
    async def build_and_run_hw():
        import hashlib
        expected_hash = os.environ.get("COMPILE_PS1_HASH", "65EBA0F259DAF1FE76FB3C34B3B35D8644EBF8B2C4001A9C4709C174BCCB62FC").lower()
        with open(os.path.join("donanim", "compile.ps1"), "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest().lower()
        if actual_hash != expected_hash:
            await manager.broadcast("\n[Donanım] HATA: Script butunluk kontrolu basarisiz!\n")
            return
            
        await manager.broadcast("\n[Donanım] VHDL kodları derleniyor ve testbench'ler calistiriliyor...\n")
        cmd = ["powershell.exe", "-ExecutionPolicy", "RemoteSigned", "-File", "compile.ps1"]
        await run_subprocess_and_broadcast(cmd, "donanim", "Donanım Simülasyonu (Faz 2)", "phase2_inner")

    running_tasks["phase2"] = True
    def cleanup(task):
        running_tasks.pop("phase2", None)
        if not task.cancelled() and task.exception():
            print(f"[HATA] Arka plan görevi çöktü: {task.exception()}")
    task = asyncio.create_task(build_and_run_hw())
    _background_tasks.add(task)
    task.add_done_callback(cleanup)
    task.add_done_callback(_background_tasks.discard)
    return {"message": "Donanim simulasyonu baslatildi"}

@app.post("/api/simulate")
async def start_simulation(token: str = Depends(verify_token)):
    if "phase3" in running_tasks:
        return {"error": "Zaten calisiyor"}
        
    gcc_path = shutil.which("gcc")
    if not gcc_path:
        return {"error": "gcc bulunamadi. Lutfen PATH'e ekleyin."}

    build_cmd = [
        gcc_path, "-DXILINX_BAREMETAL_SIM=1", "src/main.c", "src/cyberpuf_dsk.c", 
        "src/yapay_zeka_cikarimi.c", "src/yardimci_veri_uretici.c", "src/sha256.c", 
        "src/test_goruntusu.c", "-lm", "-o", "cyberpuf_sim.exe"
    ]
    
    async def build_and_run():
        await manager.broadcast("\n[Simulasyon] Gömülü sistem derleniyor...\n")
        try:
            proc = await asyncio.create_subprocess_exec(
                *build_cmd,
                cwd="gomulu",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                try:
                    await manager.broadcast(line.decode('utf-8', errors='replace').rstrip())
                except Exception:
                    pass
                    
            try:
                await asyncio.wait_for(proc.wait(), timeout=120)
            except asyncio.TimeoutError:
                proc.kill()
                await manager.broadcast("\n[Simulasyon] Derleme zaman asimina ugradi!\n")
                return
                
            if proc.returncode != 0:
                await manager.broadcast("\n[Simulasyon] Derleme hatasi!\n")
                return
                
            await manager.broadcast("\n[Simulasyon] Derleme basarili. Calistiriliyor...\n")
            
            run_cmd = ["cyberpuf_sim.exe"]
            await run_subprocess_and_broadcast(run_cmd, "gomulu", "Gömülü Simülasyon (Phase 3)", "phase3_inner")
        except Exception as e:
            import logging
            logging.exception("Simulation error")
            await manager.broadcast("\n[Simulasyon] Beklenmeyen hata olustu. Lutfen loglari kontrol edin.\n")

    running_tasks["phase3"] = True
    def cleanup(task):
        running_tasks.pop("phase3", None)
        if not task.cancelled() and task.exception():
            print(f"[HATA] Arka plan görevi çöktü: {task.exception()}")
    task = asyncio.create_task(build_and_run())
    _background_tasks.add(task)
    task.add_done_callback(cleanup)
    task.add_done_callback(_background_tasks.discard)
    return {"message": "Simulasyon baslatildi"}

@app.post("/api/run_security_tests")
async def run_security_tests(token: str = Depends(verify_token)):
    if "security_tests" in running_tasks:
        return {"error": "Zaten calisiyor"}
        
    async def execute_tests():
        task_name = "Güvenlik & Sızma Testleri"
        task_id = "security_tests"
        
        try:
            # 1. Sinematik Yükleme Mesajları
            await manager.broadcast(json.dumps({"type": "log", "task_id": task_id, "task_name": task_name, "message": f"[{task_name}] [Sistem] Güvenlik duvarı analiz ediliyor..."}))
            await asyncio.sleep(1.0)
            await manager.broadcast(json.dumps({"type": "log", "task_id": task_id, "task_name": task_name, "message": f"[{task_name}] [Sistem] Kriptografik bütünlük saldırıları başlatılıyor..."}))
            await asyncio.sleep(1.0)
            await manager.broadcast(json.dumps({"type": "log", "task_id": task_id, "task_name": task_name, "message": f"[{task_name}] [Sistem] PUF Çevresel gürültü tolerans testleri yükleniyor...\n"}))
            await asyncio.sleep(0.5)

            # 2. Pytest Komutunun Çalıştırılması
            cmd = [
                sys.executable, "-m", "pytest",
                "testler/test_manipulasyon_dayanikliligi.py",
                "testler/test_puf_gurultu_simulasyonu.py",
                "testler/test_uctan_uca_akis.py",
                "-v", "--color=yes"
            ]
            
            # extra_env kullanarak thread-safe sekilde çevre degiskeni veriyoruz
            await run_subprocess_and_broadcast(cmd, ".", task_name, f"{task_id}_inner", extra_env={"FORCE_COLOR": "1"})
        except Exception as e:
            await manager.broadcast(json.dumps({"type": "log", "task_id": task_id, "task_name": task_name, "message": f"[{task_name}] [HATA] Testler başlatılırken kritik bir hata oluştu: {str(e)}"}))
            import traceback
            traceback.print_exc()

    running_tasks["security_tests"] = True
    def cleanup(task):
        running_tasks.pop("security_tests", None)
        if not task.cancelled() and task.exception():
            print(f"[HATA] Arka plan görevi çöktü: {task.exception()}")
            
    task = asyncio.create_task(execute_tests())
    _background_tasks.add(task)
    task.add_done_callback(cleanup)
    task.add_done_callback(_background_tasks.discard)
    return {"message": "Guvenlik testleri baslatildi"}

@app.post("/api/deploy_ota")
async def deploy_ota(token: str = Depends(verify_token)):
    if "ota_deployment" in running_tasks:
        return {"error": "Zaten calisiyor"}
    cmd = [sys.executable, "calistirma_betikleri/run_phase5.py"]
    task = asyncio.create_task(run_subprocess_and_broadcast(cmd, ".", "Uç Cihaz Dağıtımı", "ota_deployment"))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"message": "Dağıtım başlatıldı"}

@app.post("/api/monitor_network")
async def monitor_network(token: str = Depends(verify_token)):
    if "network_monitor" in running_tasks:
        return {"error": "Zaten calisiyor"}
    cmd = [sys.executable, "calistirma_betikleri/run_phase6.py"]
    task = asyncio.create_task(run_subprocess_and_broadcast(cmd, ".", "Ağ Trafiği Gözetimi", "network_monitor"))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"message": "Ağ gözetimi başlatıldı"}

@app.post("/api/tee_attestation")
async def tee_attestation(token: str = Depends(verify_token)):
    if "tee_attestation" in running_tasks:
        return {"error": "Zaten calisiyor"}
    cmd = [sys.executable, "calistirma_betikleri/run_phase7.py"]
    task = asyncio.create_task(run_subprocess_and_broadcast(cmd, ".", "TEE Attestation", "tee_attestation"))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"message": "Attestation başlatıldı"}

@app.get("/api/test_images")
async def get_test_images(token: str = Depends(verify_token)):
    test_images_dir = os.path.join("static", "test_images")
    if not os.path.exists(test_images_dir):
        return {"images": []}
    
    files = os.listdir(test_images_dir)
    valid_files = [f for f in files if f.endswith(".png") and re.match(r"^[a-zA-Z0-9_.-]+\.png$", f)]
    return {"images": valid_files}

_weight_viz_cache = {
    "mtime": 0,
    "data": None
}

@app.get("/api/weight_visuals")
async def get_weight_visuals(token: str = Depends(verify_token)):
    plaintext_path = os.path.join("output", "exported_weights", "cyberpuf_weights.bin")
    ciphertext_path = os.path.join("output", "encrypted_weights", "cyberpuf_ciphertext_raw.bin")

    if not os.path.exists(plaintext_path) or not os.path.exists(ciphertext_path):
        return {"error": "Ağırlık dosyaları henüz oluşturulmadı. Lütfen Faz 1 eğitimini başlatın."}

    current_mtime = max(os.path.getmtime(plaintext_path), os.path.getmtime(ciphertext_path))
    if _weight_viz_cache["data"] and _weight_viz_cache["mtime"] >= current_mtime:
        return _weight_viz_cache["data"]

    def read_and_convert(filepath):
        with open(filepath, "rb") as f:
            data = f.read(4096)
        
        if len(data) < 4096:
            data = data + b'\x00' * (4096 - len(data))
        else:
            data = data[:4096]
            
        arr = np.frombuffer(data, dtype=np.uint8).reshape((64, 64))
        img = Image.fromarray(arr, 'L')
        img = img.resize((256, 256), Image.NEAREST)
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_str}"

    plain_b64 = await asyncio.to_thread(read_and_convert, plaintext_path)
    cipher_b64 = await asyncio.to_thread(read_and_convert, ciphertext_path)

    response_data = {
        "plaintext_img": plain_b64,
        "encrypted_img": cipher_b64
    }
    
    _weight_viz_cache["mtime"] = current_mtime
    _weight_viz_cache["data"] = response_data

    return response_data

app.mount("/", StaticFiles(directory=os.path.join("static"), html=True), name="root")

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("APP_HOST", "127.0.0.1")
    port = int(os.environ.get("APP_PORT", "8000"))
    debug = os.environ.get("APP_DEBUG", "False").lower() == "true"
    
    # Sistem tespit ve Uvicorn reload uyumluluk ayarı
    import platform
    os_name = platform.system()
    
    if os_name == "Windows":
        if debug:
            print(f"[BİLGİ] Sistem tespit edildi: {os_name}")
            print("[UYARI] Windows üzerinde asyncio alt süreç (subprocess) uyumluluğunu sağlamak için Uvicorn reload devre dışı bırakıldı.")
            debug = False
    elif os_name in ["Linux", "Darwin"]:
        if debug:
            print(f"[BİLGİ] Sistem tespit edildi: {os_name}")
            print("[BİLGİ] İşletim sisteminiz alt süreçleri tam destekliyor, Uvicorn Hot-Reload aktif edildi.")
            
    uvicorn.run("main_app:app", host=host, port=port, reload=debug)
