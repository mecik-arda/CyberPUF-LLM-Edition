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
});
