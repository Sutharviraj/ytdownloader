const API_BASE_URL = "https://tube-grabber.onrender.com";

document.addEventListener('DOMContentLoaded', () => {
    // --- Server Wake-up Timer Logic ---
    const wakeupBanner = document.getElementById('wakeupBanner');
    const wakeupTimer = document.getElementById('wakeupTimer');
    let isServerReady = false;

    // Initial ping to check if server is awake
    fetch(`${API_BASE_URL}/api/ping`, { method: 'GET' })
        .then(res => res.json())
        .then(data => {
            if (data.status === "awake") {
                isServerReady = true;
                if (wakeupBanner) wakeupBanner.classList.add('hidden');
            }
        })
        .catch(err => console.log("Ping failed:", err));

    // Show timer if server is sleeping (doesn't respond in 1.5 seconds)
    setTimeout(() => {
        if (!isServerReady && wakeupBanner) {
            wakeupBanner.classList.remove('hidden');
            let timeLeft = 50; // Render free tier takes ~50s to wake up
            wakeupTimer.innerText = timeLeft;
            
            const countInt = setInterval(() => {
                if (isServerReady) {
                    clearInterval(countInt);
                    wakeupBanner.classList.add('hidden');
                    return;
                }
                timeLeft--;
                if (timeLeft > 0) {
                    wakeupTimer.innerText = timeLeft;
                } else {
                    wakeupTimer.innerText = "Starting momentarily...";
                    clearInterval(countInt);
                }
            }, 1000);
            
            // Continuous ping until awake
            const pingInt = setInterval(() => {
                if(isServerReady) { clearInterval(pingInt); return; }
                fetch(`${API_BASE_URL}/api/ping`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === "awake") {
                            isServerReady = true;
                            wakeupBanner.classList.add('hidden');
                            clearInterval(pingInt);
                        }
                    }).catch(e => {});
            }, 3000);
        }
    }, 1500);

    // --- Selectors ---
    const navLinks = document.querySelectorAll('.nav-link');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    const urlInput = document.getElementById('urlInput');
    const pasteBtn = document.getElementById('pasteBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    
    const statusContainer = document.getElementById('statusContainer');
    const statusText = document.getElementById('statusText');
    const progressFill = document.getElementById('progressFill');
    const speedText = document.getElementById('speedText');
    const etaText = document.getElementById('etaText');
    
    const previewContainer = document.getElementById('previewContainer');
    const videoThumb = document.getElementById('videoThumb');
    const videoTitle = document.getElementById('videoTitle');
    const videoUploader = document.getElementById('videoUploader');
    const qualitySelection = document.getElementById('qualitySelection');
    const formatBtns = document.querySelectorAll('.f-btn');
    const confirmDownloadBtn = document.getElementById('confirmDownloadBtn');

    const successContainer = document.getElementById('successContainer');
    const successFileTitle = document.getElementById('successFileTitle');
    const finalDownloadLink = document.getElementById('finalDownloadLink');
    const restartBtn = document.getElementById('restartBtn');
    
    const authOverlay = document.getElementById('authOverlay');
    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const closeAuth = document.getElementById('closeAuth');
    const googleLoginBtn = document.getElementById('googleLoginBtn');
    const guestLoginBtn = document.getElementById('guestLoginBtn');
    const emailLoginForm = document.getElementById('emailLoginForm');
    const authError = document.getElementById('authError');
    const userInfo = document.getElementById('userInfo');
    const userEmail = document.getElementById('userEmail');

    let currentFormat = 'Video';
    let selectedFormatId = null;
    let activeTaskId = null;

    // --- Tab Navigation ---
    navLinks.forEach(link => {
        link.onclick = () => {
            const tabId = link.dataset.tab;
            navLinks.forEach(l => l.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            link.classList.add('active');
            document.getElementById(`${tabId}-tab`).classList.add('active');
            if (tabId === 'downloads') loadHistory();
        };
    });

    // --- Clipboard Paste ---
    pasteBtn.onclick = async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text;
                pasteBtn.innerText = "COPIED";
                setTimeout(() => pasteBtn.innerText = "Paste", 1000);
            }
        } catch (e) { alert("Please paste manually."); }
    };

    // --- Analyze Media ---
    downloadBtn.onclick = async () => {
        const url = urlInput.value.trim();
        if (!url) return alert("Please paste a URL first.");
        
        // Reset UI
        previewContainer.classList.add('hidden');
        successContainer.classList.add('hidden');
        statusContainer.classList.remove('hidden');
        statusText.style.color = "white"; 
        
        if (!isServerReady) {
            statusText.innerText = "Waiting for server to wake up...";
        } else {
            statusText.innerText = "Analyzing media links...";
        }
        progressFill.style.width = "5%";

        try {
            const res = await fetch(`${API_BASE_URL}/api/get_info`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            renderPreview(data);
            statusContainer.classList.add('hidden');
            previewContainer.classList.remove('hidden');
        } catch (err) {
            let msg = err.message;
            if (msg.includes("confirm you're not a bot") || msg.includes("Failed to fetch")) {
                if (msg.includes("Failed to fetch")) {
                    msg = "⚠️ Server connection failed. Make sure URL is updated.";
                } else {
                    msg = "⚠️ Server verification required. (Owner: Provide cookies to fix this).";
                }
            }
            statusText.innerText = msg;
            statusText.style.color = "#fb7185";
        }
    };

    function renderPreview(data) {
        videoThumb.src = data.thumbnail || "https://placehold.co/600x400/000/fff?text=Preview";
        videoTitle.innerText = data.title;
        videoUploader.innerText = data.uploader || "Unknown Uploader";
        qualitySelection.innerHTML = "";
        
        const qualities = data.formats || [];
        qualities.forEach((fmt, idx) => {
            const btn = document.createElement('button');
            btn.className = "q-btn";
            btn.innerText = fmt.label || fmt.format_note || "Best Quality";
            if (idx === 0) { btn.classList.add('active'); selectedFormatId = fmt.format_id; }
            btn.onclick = () => {
                document.querySelectorAll('.q-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedFormatId = fmt.format_id;
            };
            qualitySelection.appendChild(btn);
        });
    }

    // Format Toggle
    formatBtns.forEach(btn => {
        btn.onclick = () => {
            formatBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFormat = btn.dataset.fmt;
        };
    });

    // --- Final Download ---
    confirmDownloadBtn.onclick = async () => {
        const url = urlInput.value.trim();
        previewContainer.classList.add('hidden');
        statusContainer.classList.remove('hidden');
        statusText.innerText = "Connecting to high-speed server...";
        progressFill.style.width = "10%";

        try {
            const res = await fetch(`${API_BASE_URL}/api/download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url, format: currentFormat, format_id: selectedFormatId, title: videoTitle.innerText
                })
            });
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            activeTaskId = data.task_id;
            startPolling();
        } catch (e) { statusText.innerText = e.message; statusText.style.color = "#fb7185"; }
    };

    function startPolling() {
        const poll = setInterval(async () => {
            if (!activeTaskId) { clearInterval(poll); return; }
            try {
                const res = await fetch(`${API_BASE_URL}/api/status/${activeTaskId}`);
                const data = await res.json();
                
                progressFill.style.width = `${data.progress}%`;
                speedText.innerText = data.speed || "Queueing...";
                etaText.innerText = data.eta || "00:00";
                
                if (data.error) throw new Error(data.error);
                
                if (data.finished) {
                    clearInterval(poll);
                    showSuccess(data);
                } else {
                    statusText.innerText = data.status_msg;
                }
            } catch (e) { 
                clearInterval(poll); 
                let msg = e.message;
                if (msg.includes("confirm you're not a bot")) {
                    msg = "⚠️ YouTube blocked this request. (Owner Action Required).";
                }
                statusText.innerText = msg; 
                statusText.style.color = "#fb7185";
            }
        }, 800);
    }

    function showSuccess(data) {
        statusContainer.classList.add('hidden');
        successContainer.classList.remove('hidden');
        successFileTitle.innerText = data.filename || "Your file is ready.";
        finalDownloadLink.href = `${API_BASE_URL}/api/get_file/${activeTaskId}`;
    }

    restartBtn.onclick = () => {
        successContainer.classList.add('hidden');
        urlInput.value = "";
        progressFill.style.width = "0%";
    };

    // --- Auth Sync ---
    const syncAuth = setInterval(() => {
        if (window.firebaseAuth) {
            clearInterval(syncAuth);
            window.firebaseAuth.onAuthStateChanged(user => {
                if (user) {
                    authOverlay.classList.add('hidden');
                    userInfo.classList.remove('hidden');
                    loginBtn.classList.add('hidden');
                    userEmail.innerText = user.isAnonymous ? "Guest Mode" : (user.email || "Active User");
                } else {
                    userInfo.classList.add('hidden');
                    loginBtn.classList.remove('hidden');
                }
            });
        }
    }, 200);

    loginBtn.onclick = () => authOverlay.classList.remove('hidden');
    closeAuth.onclick = () => authOverlay.classList.add('hidden');
    logoutBtn.onclick = () => window.firebaseLogout(window.firebaseAuth);
    googleLoginBtn.onclick = () => window.signInWithPopup(window.firebaseAuth, window.googleProvider);
    guestLoginBtn.onclick = () => window.signInAnonymously(window.firebaseAuth);
    
    emailLoginForm.onsubmit = async (e) => {
        e.preventDefault();
        const email = e.target[0].value;
        const pass = e.target[1].value;
        try { await window.firebaseLogin(window.firebaseAuth, email, pass); }
        catch (err) { authError.innerText = err.message; authError.classList.remove('hidden'); }
    };

    function loadHistory() {
        const tbody = document.querySelector('#historyTable tbody');
        fetch(`${API_BASE_URL}/api/history`).then(r => r.json()).then(data => {
            if (!data || data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:3rem;opacity:0.3">No recent activity found.</td></tr>';
                return;
            }
            tbody.innerHTML = [...data].reverse().map(item => `
                <tr>
                    <td style="font-weight:700">${item.title}</td>
                    <td style="opacity:0.6">${new Date(item.timestamp).toLocaleDateString()}</td>
                    <td><span class="badge success">Finished</span></td>
                </tr>
            `).join('');
        }).catch(e => {
             tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:3rem;color:#fb7185">Cannot load history. Server may be sleeping or URL is incorrect.</td></tr>';
        });
    }
});
