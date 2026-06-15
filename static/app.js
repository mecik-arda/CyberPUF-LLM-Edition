document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const wsStatusDot = document.getElementById('ws-status-dot');
    const wsStatusText = document.getElementById('ws-status-text');
    const terminalsWrapper = document.getElementById('terminals-wrapper');
    // Fallback if browser cached the old index.html
    const systemTerminalBody = document.getElementById('terminal-body-system') || document.getElementById('terminal-body');
    const clearTermBtn = document.getElementById('clear-term-btn');
    
    const trainForm = document.getElementById('train-form');
    const trainBtn = document.getElementById('train-btn');
    const trainSpinner = document.getElementById('train-spinner');
    
    const simBtn = document.getElementById('sim-btn');
    const simSpinner = document.getElementById('sim-spinner');
    
    const hwSimBtn = document.getElementById('hw-sim-btn');
    const hwSimSpinner = document.getElementById('hw-sim-spinner');
    
    const imageSelect = document.getElementById('test-image-select');
    const imagePreview = document.getElementById('test-image-preview');
    const imagePlaceholder = document.getElementById('image-placeholder');

    const predClass = document.getElementById('pred-class');
    const predConf = document.getElementById('pred-conf');
    const pufStatus = document.getElementById('puf-status');

    // Modal Elements
    const helpBtn = document.getElementById('help-btn');
    const helpModal = document.getElementById('help-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const authModal = document.getElementById('auth-modal');
    const authTokenInput = document.getElementById('auth-token-input');
    const authSubmitBtn = document.getElementById('auth-submit-btn');

    // Button references
    const btnPhase5 = document.getElementById('btn-phase5');
    const btnPhase6 = document.getElementById('btn-phase6');
    const btnPhase7 = document.getElementById('btn-phase7');

    // Terminal Logging
    const MAX_TERMINAL_LINES = 1000;

    function getOrCreateTerminal(taskId, taskName) {
        if (!taskId || taskId === 'system') return systemTerminalBody;
        
        // Fallback: If browser cached the old index.html without terminalsWrapper
        if (!terminalsWrapper) return systemTerminalBody;

        let termBody = document.getElementById(`terminal-body-${taskId}`);
        if (!termBody) {
            const win = document.createElement('div');
            win.className = 'terminal-window';
            win.id = `term-${taskId}`;
            
            const header = document.createElement('div');
            header.className = 'terminal-window-header';
            const titleSpan = document.createElement('span');
            titleSpan.textContent = taskName + ' Konsolu';
            const closeSpan = document.createElement('span');
            closeSpan.className = 'close-term-btn';
            closeSpan.textContent = '×';
            closeSpan.onclick = () => document.getElementById(`term-${taskId}`).remove();
            header.appendChild(titleSpan);
            header.appendChild(closeSpan);
            
            termBody = document.createElement('div');
            termBody.className = 'terminal-body';
            termBody.id = `terminal-body-${taskId}`;
            
            win.appendChild(header);
            win.appendChild(termBody);
            terminalsWrapper.appendChild(win);
        }
        return termBody;
    }

    function logToTerminal(message, type = 'normal', taskId = 'system', taskName = 'Sistem') {
        const targetBody = getOrCreateTerminal(taskId, taskName);
        const isAtBottom = targetBody.scrollHeight - targetBody.scrollTop <= targetBody.clientHeight + 50;

        const line = document.createElement('div');
        line.className = `term-line ${type}`;
        
        // Zaman damgasi (Timestamp) ekleme
        const now = new Date();
        const timeStr = now.toTimeString().split(' ')[0]; // HH:MM:SS
        
        // Sayet mesaj zaten bir tag [Sistem] iceriyorsa, basina saat ekle
        if (message.startsWith('[')) {
            line.textContent = `[${timeStr}] ${message}`;
        } else if (message.startsWith('>')) {
            line.textContent = `> [${timeStr}] ${message.substring(1).trim()}`;
        } else {
            line.textContent = `[${timeStr}] [INFO] ${message}`;
        }
        
        targetBody.appendChild(line);
        
        // Prevent DOM Bloat / Memory Leak
        while (targetBody.childElementCount > MAX_TERMINAL_LINES) {
            targetBody.removeChild(targetBody.firstElementChild);
        }

        // Auto-scroll to ensure latest logs are visible
        if (isAtBottom) {
            targetBody.scrollTop = targetBody.scrollHeight;
        }

        // Parse logs to update UI state if simulation is running
        parseSimulationLogs(message);
    }

    clearTermBtn.addEventListener('click', () => {
        systemTerminalBody.innerHTML = '<div class="term-line welcome">CyberPUF OS v4.0.0-Gold Terminal\'ine Hoş Geldiniz.</div>';
        const dynamicWindows = document.querySelectorAll('.terminal-window:not(#term-system)');
        dynamicWindows.forEach(w => w.remove());
    });

    let wsReconnectDelay = 1000;
    const MAX_RECONNECT_DELAY = 30000;
    let cachedWsToken = null;
    let authPromiseResolvers = [];

    async function getWebSocketToken() {
        if (cachedWsToken) {
            return cachedWsToken;
        }
        
        authModal.classList.remove('hidden');
        
        return new Promise((resolve) => {
            authPromiseResolvers.push(resolve);
        });
    }

    authSubmitBtn.addEventListener('click', () => {
        const token = authTokenInput.value.trim();
        if (token) {
            cachedWsToken = token;
            authModal.classList.add('hidden');
            if (authPromiseResolvers.length > 0) {
                authPromiseResolvers.forEach(resolve => resolve(token));
                authPromiseResolvers = [];
            }
        }
    });

    async function fetchAPI(endpoint, options = {}) {
        const token = await getWebSocketToken();
        const headers = {
            'Authorization': `Bearer ${token}`,
            'X-Requested-With': 'XMLHttpRequest',
            ...(options.headers || {})
        };
        const config = {
            ...options,
            headers
        };
        const res = await fetch(endpoint, config);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res;
    }

    async function connectWebSocket() {
        try {
            // Fetch WebSocket token from server
            const wsToken = await getWebSocketToken();

            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            ws.send(JSON.stringify({ type: 'auth', token: wsToken }));
            wsReconnectDelay = 1000;
            wsStatusDot.className = 'dot connected';
            wsStatusText.textContent = 'Canlı Bağlantı Aktif';
            logToTerminal('[Sistem] Sunucuya WebSocket üzerinden bağlanıldı.', 'info');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'log') {
                    logToTerminal(data.message, 'normal', data.task_id, data.task_name);
                }
            } catch (e) {
                logToTerminal(event.data);
            }
        };

        ws.onclose = (event) => {
            if (event.code === 1008) {
                cachedWsToken = null;
            }
            wsStatusDot.className = 'dot disconnected';
            wsStatusText.textContent = 'Bağlantı Koptu - Yeniden Deneniyor...';
            setTimeout(connectWebSocket, wsReconnectDelay);
            wsReconnectDelay = Math.min(wsReconnectDelay * 2, MAX_RECONNECT_DELAY);
        };

        ws.onerror = (error) => {
            console.error('WebSocket Hatası:', error);
            logToTerminal('[HATA] WebSocket bağlantısı başarısız. Token doğrulanıyor...', 'error');
        };
        } catch (err) {
            console.error('Config fetch error:', err);
            logToTerminal(`[HATA] WebSocket token alınamadı: ${err.message}`, 'error');
            // Retry after delay
            setTimeout(connectWebSocket, wsReconnectDelay);
            wsReconnectDelay = Math.min(wsReconnectDelay * 2, MAX_RECONNECT_DELAY);
        }
    }

    connectWebSocket();

    // Fetch Test Images
    async function loadTestImages() {
        try {
            const res = await fetchAPI('/api/test_images');
            const data = await res.json();
            imageSelect.innerHTML = '<option value="">-- Bir Görsel Seçin --</option>';
            data.images.forEach(img => {
                const opt = document.createElement('option');
                opt.value = img;
                opt.textContent = img;
                imageSelect.appendChild(opt);
            });
        } catch (e) {
            console.error('Görseller yüklenemedi:', e);
            imageSelect.innerHTML = '<option value="">Yüklenemedi</option>';
        }
    }
    loadTestImages();

    imageSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        if (val) {
            // Image SRC validasyonu (defence-in-depth)
            if (/^[a-zA-Z0-9_.-]+\.(png|jpg|jpeg)$/.test(val)) {
                imagePreview.src = `/static/test_images/${val}`;
                imagePreview.classList.remove('hidden');
                imagePlaceholder.classList.add('hidden');
            } else {
                console.error("Geçersiz görsel dosya adı formatı.");
            }
        } else {
            imagePreview.src = '';
            imagePreview.classList.add('hidden');
            imagePlaceholder.classList.remove('hidden');
        }
    });

    // API Calls
    trainForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            epochs: parseInt(document.getElementById('epochs').value),
            batch_size: parseInt(document.getElementById('batch_size').value),
            learning_rate: parseFloat(document.getElementById('learning_rate').value),
            encryption_mode: document.getElementById('encryption_mode').value,
            quant_mode: document.getElementById('quant_mode').value
        };

        trainBtn.disabled = true;
        trainSpinner.classList.remove('hidden');

        try {
            await fetchAPI('/api/train', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            logToTerminal('[Sistem] Eğitim komutu sunucuya iletildi.', 'info');
        } catch(err) {
            logToTerminal(`[Hata] Eğitim başlatılamadı: ${err.message}`, 'error');
        } finally {
            trainBtn.disabled = false;
            trainSpinner.classList.add('hidden');
        }
    });

    simBtn.addEventListener('click', async () => {
        simBtn.disabled = true;
        simSpinner.classList.remove('hidden');
        
        // Reset playground UI
        predClass.textContent = 'Hesaplanıyor...';
        predConf.textContent = '---';
        pufStatus.textContent = 'Bekleniyor...';
        pufStatus.style.color = '';

        try {
            await fetchAPI('/api/simulate', { method: 'POST' });
            logToTerminal('[Sistem] Simülasyon komutu sunucuya iletildi.', 'info');
        } catch(err) {
            logToTerminal(`[Hata] Simülasyon başlatılamadı: ${err.message}`, 'error');
            predClass.textContent = 'Hata';
        } finally {
            simBtn.disabled = false;
            simSpinner.classList.add('hidden');
        }
    });

    if (hwSimBtn) {
        hwSimBtn.addEventListener('click', async () => {
            hwSimBtn.disabled = true;
            hwSimSpinner.classList.remove('hidden');
            
            try {
                await fetchAPI('/api/simulate_hw', { method: 'POST' });
                logToTerminal('[Sistem] Donanım simülasyon komutu sunucuya iletildi.', 'info');
            } catch(err) {
                logToTerminal(`[Hata] Donanım simülasyonu başlatılamadı: ${err.message}`, 'error');
            } finally {
                hwSimBtn.disabled = false;
                hwSimSpinner.classList.add('hidden');
            }
        });
    }

    // Security Tests (Phase 4)
    const btnSecurityTest = document.getElementById('btn-security-test');
    const secSpinner = document.getElementById('sec-spinner');

    if (btnSecurityTest) {
        btnSecurityTest.addEventListener('click', async () => {
            btnSecurityTest.disabled = true;
            secSpinner.classList.remove('hidden');
            
            // Create console manually if it doesn't exist
            getOrCreateTerminal('security_tests', 'Güvenlik & Sızma Testleri');

            try {
                await fetchAPI('/api/run_security_tests', { method: 'POST' });
                logToTerminal('[Sistem] Güvenlik testleri komutu sunucuya iletildi.', 'info', 'security_tests', 'Güvenlik & Sızma Testleri');
            } catch(err) {
                logToTerminal(`[Hata] Güvenlik testleri başlatılamadı: ${err.message}`, 'error', 'security_tests', 'Güvenlik & Sızma Testleri');
            } finally {
                btnSecurityTest.disabled = false;
                secSpinner.classList.add('hidden');
            }
        });
    }

    // Phase 5 (OTA Deployment)
    const phase5Spinner = document.getElementById('phase5-spinner');
    if (btnPhase5) {
        btnPhase5.addEventListener('click', async () => {
            btnPhase5.disabled = true;
            if(phase5Spinner) phase5Spinner.classList.remove('hidden');
            getOrCreateTerminal('ota_deployment', 'Uç Cihaz Dağıtımı (OTA)');

            try {
                await fetchAPI('/api/deploy_ota', { method: 'POST' });
                logToTerminal('[Sistem] OTA Dağıtım komutu sunucuya iletildi.', 'info', 'ota_deployment', 'Uç Cihaz Dağıtımı');
            } catch(err) {
                logToTerminal(`[Hata] Dağıtım başlatılamadı: ${err.message}`, 'error', 'ota_deployment', 'Uç Cihaz Dağıtımı');
            } finally {
                btnPhase5.disabled = false;
                if(phase5Spinner) phase5Spinner.classList.add('hidden');
            }
        });
    }

    // Phase 6 (Network Monitor)
    const phase6Spinner = document.getElementById('phase6-spinner');
    if (btnPhase6) {
        btnPhase6.addEventListener('click', async () => {
            btnPhase6.disabled = true;
            if(phase6Spinner) phase6Spinner.classList.remove('hidden');
            getOrCreateTerminal('network_monitor', 'Ağ Trafiği Gözetimi');

            try {
                await fetchAPI('/api/monitor_network', { method: 'POST' });
                logToTerminal('[Sistem] Ağ gözetim komutu sunucuya iletildi.', 'info', 'network_monitor', 'Ağ Trafiği Gözetimi');
            } catch(err) {
                logToTerminal(`[Hata] Ağ gözetimi başlatılamadı: ${err.message}`, 'error', 'network_monitor', 'Ağ Trafiği Gözetimi');
            } finally {
                btnPhase6.disabled = false;
                if(phase6Spinner) phase6Spinner.classList.add('hidden');
            }
        });
    }

    // Phase 7 (TEE Attestation)
    const phase7Spinner = document.getElementById('phase7-spinner');
    if (btnPhase7) {
        btnPhase7.addEventListener('click', async () => {
            btnPhase7.disabled = true;
            if(phase7Spinner) phase7Spinner.classList.remove('hidden');
            getOrCreateTerminal('tee_attestation', 'TEE Attestation');

            try {
                await fetchAPI('/api/tee_attestation', { method: 'POST' });
                logToTerminal('[Sistem] TEE Attestation komutu sunucuya iletildi.', 'info', 'tee_attestation', 'TEE Attestation');
            } catch(err) {
                logToTerminal(`[Hata] Attestation başlatılamadı: ${err.message}`, 'error', 'tee_attestation', 'TEE Attestation');
            } finally {
                btnPhase7.disabled = false;
                if(phase7Spinner) phase7Spinner.classList.add('hidden');
            }
        });
    }


    // Simple Log Parser to update Playground UI based on C Simulation Output
    function parseSimulationLogs(msg) {
        // PUF Doğrulama parse
        if (msg.includes("SHA-256 HASH DOGRULAMASI BASARILI")) {
            pufStatus.textContent = "✅ BAŞARILI (Kırılmaz Anahtar)";
            pufStatus.style.color = "var(--accent)";
        } else if (msg.includes("DOGRULAMA BASARISIZ")) {
            pufStatus.textContent = "❌ BAŞARISIZ (Güvenlik İhlali)";
            pufStatus.style.color = "var(--danger)";
        }

        // Tahmin Sınıfı parse. Example output from C: "Tahmin Edilen Sinif: 3"
        const classMatch = msg.match(/Tahmin Edilen Sinif:\s*(\d+)/);
        if (classMatch) {
            const classIdx = parseInt(classMatch[1]);
            const cifarClasses = ["Uçak", "Otomobil", "Kuş", "Kedi", "Geyik", "Köpek", "Kurbağa", "At", "Gemi", "Kamyon"];
            predClass.textContent = cifarClasses[classIdx] || `Sınıf ${classIdx}`;
        }

        // Tahmin Güveni parse. Example: "Güven: 98.45%"
        // C kodunda bu log mevcut değilse şimdilik statik bir değer kalabilir veya eklenebilir.
        // Ama biz modelin ne kadar güvenli çözüldüğünü vs. parse edebiliriz.
    }

    // Weight Visualization Logic
    const loadVizBtn = document.getElementById('load-viz-btn');
    const vizSpinner = document.getElementById('viz-spinner');
    const vizPlain = document.getElementById('viz-plain');
    const vizPlainPlaceholder = document.getElementById('viz-plain-placeholder');
    const vizCipher = document.getElementById('viz-cipher');
    const vizCipherPlaceholder = document.getElementById('viz-cipher-placeholder');
    const vizError = document.getElementById('viz-error');

    loadVizBtn.addEventListener('click', async () => {
        loadVizBtn.disabled = true;
        vizSpinner.classList.remove('hidden');
        vizError.classList.add('hidden');
        
        try {
            const res = await fetchAPI('/api/weight_visuals');
            const data = await res.json();
            
            if (data.error) {
                vizError.textContent = data.error;
                vizError.classList.remove('hidden');
            } else {
                vizPlain.src = data.plaintext_img;
                vizPlain.classList.remove('hidden');
                vizPlainPlaceholder.classList.add('hidden');

                vizCipher.src = data.encrypted_img;
                vizCipher.classList.remove('hidden');
                vizCipherPlaceholder.classList.add('hidden');
                
                logToTerminal('[Sistem] Ağırlık görselleştirme verileri başarıyla yüklendi.', 'info');
            }
        } catch (err) {
            vizError.textContent = `Görseller yüklenirken hata oluştu: ${err.message}`;
            vizError.classList.remove('hidden');
        } finally {
            loadVizBtn.disabled = false;
            vizSpinner.classList.add('hidden');
        }
    });

    // Modal Event Listeners
    helpBtn.addEventListener('click', () => {
        helpModal.classList.remove('hidden');
    });

    closeModalBtn.addEventListener('click', () => {
        helpModal.classList.add('hidden');
    });

    // Close modal when clicking outside of it
    window.addEventListener('click', (e) => {
        if (e.target === helpModal) {
            helpModal.classList.add('hidden');
        }
    });
});
