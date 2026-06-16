document.addEventListener("DOMContentLoaded", () => {
    const terminal = document.getElementById("terminal-output");
    
    function logToTerminal(msg) {
        const div = document.createElement("div");
        div.className = "log-line";
        div.textContent = `> ${msg}`;
        terminal.appendChild(div);
        terminal.scrollTop = terminal.scrollHeight;
    }

    async function fetchStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            
            document.getElementById("puf-hash").textContent = data.puf_hash;
            document.getElementById("ramdisk-status").textContent = data.ramdisk_mounted ? "Aktif (Bağlandı)" : "Pasif";
            document.getElementById("ramdisk-status").style.color = data.ramdisk_mounted ? "var(--success)" : "var(--danger)";
            
            document.getElementById("ramdisk-path").textContent = data.ramdisk_path;
            
            document.getElementById("model-status").textContent = data.model_loaded ? "Yüklü ve Hazır" : "Bekliyor";
            document.getElementById("model-status").style.color = data.model_loaded ? "var(--success)" : "var(--text-secondary)";
            
            document.getElementById("uptime").textContent = `${data.uptime} saniye`;
        } catch (e) {
            console.error("Status fetch error", e);
        }
    }

    setInterval(fetchStatus, 2000);
    fetchStatus();

    function triggerSSECommand(endpoint, payload) {
        logToTerminal(`[SİSTEM] ${endpoint} komutu gönderiliyor...`);
        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(async response => {
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                lines.forEach(line => {
                    if (line.startsWith('data: ')) {
                        const msg = line.substring(6);
                        if (msg === "[BİTTİ]") {
                            logToTerminal("[SİSTEM] İşlem başarıyla tamamlandı.");
                            fetchStatus();
                        } else {
                            logToTerminal(msg);
                        }
                    }
                });
            }
        }).catch(err => {
            logToTerminal(`[HATA] ${err.message}`);
        });
    }

    document.getElementById("btn-encrypt").addEventListener("click", () => {
        const inPath = document.getElementById("model-input-path").value;
        const outPath = document.getElementById("model-output-path").value;
        triggerSSECommand("/api/encrypt", { model_path: inPath, output_path: outPath });
    });

    document.getElementById("btn-load").addEventListener("click", () => {
        const cpufPath = document.getElementById("cpuf-load-path").value;
        triggerSSECommand("/api/load", { cpuf_llm_path: cpufPath });
    });

    document.getElementById("btn-zeroize").addEventListener("click", () => {
        triggerSSECommand("/api/zeroize", {});
    });

    // Config Management
    async function fetchConfig() {
        try {
            const res = await fetch("/api/config");
            const config = await res.json();
            document.getElementById("toggle-attestation").checked = config.hardware_attestation_enabled || false;
            document.getElementById("toggle-pqc").checked = config.pqc_enabled || false;
            document.getElementById("toggle-antidebug").checked = config.anti_debug_enabled || false;
            document.getElementById("toggle-telemetry").checked = config.telemetry_enabled || false;
            document.getElementById("toggle-layerpaging").checked = config.layer_paging_enabled || false;
        } catch (e) {
            console.error("Config fetch error", e);
        }
    }
    fetchConfig();

    document.getElementById("btn-save-settings").addEventListener("click", async () => {
        const payload = {
            hardware_attestation_enabled: document.getElementById("toggle-attestation").checked,
            pqc_enabled: document.getElementById("toggle-pqc").checked,
            anti_debug_enabled: document.getElementById("toggle-antidebug").checked,
            telemetry_enabled: document.getElementById("toggle-telemetry").checked,
            layer_paging_enabled: document.getElementById("toggle-layerpaging").checked
        };
        try {
            const res = await fetch("/api/config", {
                method: "POST",
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                logToTerminal("[SİSTEM] Güvenlik ayarları kaydedildi.");
            }
        } catch (e) {
            logToTerminal(`[HATA] Ayarlar kaydedilemedi: ${e}`);
        }
    });

    // Socket.IO Telemetry Listener
    const socket = io();
    socket.on("telemetry_update", (data) => {
        document.getElementById("tel-cpu").textContent = data.cpu_usage + "%";
        document.getElementById("tel-ram").textContent = `${data.ram_percent}% (${data.ram_used_gb}GB / ${data.ram_total_gb}GB)`;
        document.getElementById("tel-temp").textContent = data.temperature;
    });
});
