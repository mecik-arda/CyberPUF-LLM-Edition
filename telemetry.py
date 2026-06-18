import time
import psutil
import json
import os

CONFIG_FILE = "/home/ardam/underw_framework/CyberPUF_LLM/config.json"

def is_telemetry_enabled():
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            return cfg.get("telemetry_enabled", False)
    except:
        return False

def get_telemetry_data():
    cpu_usage = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    
    # Try to get temperature if available
    temp = "N/A"
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            first_sensor = list(temps.keys())[0]
            temp = f"{temps[first_sensor][0].current}°C"
    except:
        pass
        
    return {
        "cpu_usage": cpu_usage,
        "ram_percent": ram.percent,
        "ram_used_gb": round(ram.used / (1024**3), 2),
        "ram_total_gb": round(ram.total / (1024**3), 2),
        "temperature": temp,
        "timestamp": time.time()
    }

def telemetry_worker(socketio, app):
    while True:
        if is_telemetry_enabled():
            data = get_telemetry_data()
            socketio.emit("telemetry_update", data)
        time.sleep(2)
