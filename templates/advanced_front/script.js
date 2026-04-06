// --- Config ---
const API_BASE = 'http://127.0.0.1:5000/api'; 

// --- DOM elements ---
const views = {
    home: document.getElementById('view-home'),
    downloads: document.getElementById('view-downloads'),
    history: document.getElementById('view-history') // used for Audio/Video/Completed/Failed
};
const tabs = {
    home: document.getElementById('tab-home'),
    downloads: document.getElementById('tab-downloads'),
    audio: document.getElementById('tab-audio'),
    video: document.getElementById('tab-video'),
    completed: document.getElementById('tab-completed'),
    failed: document.getElementById('tab-failed')
};

const inputElements = {
    url: document.getElementById('urlInput'),
    fetchBtn: document.getElementById('fetchBtn'),
    spinner: document.getElementById('fetchSpinner'),
    error: document.getElementById('fetchError')
};

const previewArea = document.getElementById('previewArea');
const startDownloadBtn = document.getElementById('startDownloadBtn');
const dropZone = document.getElementById('dropZone');
const quickModeToggle = document.getElementById('quickModeToggle');
const successSound = document.getElementById('successSound');

let activePlaylistVideos = []; 
let activeTasksCount = 0;

// --- Analytics Tracking ---
window.addEventListener('load', () => {
    fetch(`${API_BASE}/visit`, { method: 'POST' }).catch(e => console.error("Analytics ping failed"));
});

// --- Navigation & Categories ---
function switchView(viewName, filterType = null) {
    Object.values(views).forEach(v => v.classList.add('hidden'));
    Object.values(tabs).forEach(t => t.classList.remove('active'));
    
    if (tabs[viewName]) tabs[viewName].classList.add('active');

    if (viewName === 'home' || viewName === 'downloads') {
        views[viewName].classList.remove('hidden');
    } else {
        // It's a history category (audio, video, completed, failed)
        views.history.classList.remove('hidden');
        document.getElementById('historyTitle').innerText = capitalize(viewName);
        renderHistory(viewName);
    }
}

function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

Object.keys(tabs).forEach(key => {
    if(tabs[key]) {
        tabs[key].addEventListener('click', (e) => {
            e.preventDefault();
            switchView(key);
        });
    }
});

// --- Drag & Drop Flow ---
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.querySelector('.input-card').classList.add('dragover');
    }, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.querySelector('.input-card').classList.remove('dragover');
    }, false);
});

dropZone.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    let dt = e.dataTransfer;
    let text = dt.getData('text');
    if (text) {
        inputElements.url.value = text.trim();
        triggerFetch();
    }
}

// Auto Paste Detection
inputElements.url.addEventListener('paste', () => {
    setTimeout(triggerFetch, 100);
});

inputElements.fetchBtn.addEventListener('click', triggerFetch);

// Fetch Logic
async function triggerFetch() {
    const url = inputElements.url.value.trim();
    if(!url) return;

    // Reset UI
    previewArea.classList.add('hidden');
    inputElements.error.classList.add('hidden');
    inputElements.spinner.classList.remove('hidden');
    inputElements.fetchBtn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/info`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ url })
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to fetch details');
        
        // Handle Quick Mode: Auto-start Audio download!
        if (quickModeToggle.checked) {
            startInstantDownload(data);
        } else {
            renderPreview(data);
        }
        
    } catch (err) {
        inputElements.error.innerText = err.message;
        inputElements.error.classList.remove('hidden');
    } finally {
        inputElements.spinner.classList.add('hidden');
        inputElements.fetchBtn.disabled = false;
    }
}

function renderPreview(data) {
    document.getElementById('thumbPreview').src = data.thumbnail || 'https://via.placeholder.com/400x225?text=No+Thumbnail';
    document.getElementById('videoTitle').innerText = data.title;
    
    // Duration
    const durTag = document.getElementById('videoDuration');
    if (data.videos.length > 0 && data.videos[0].duration) {
        let mins = Math.floor(data.videos[0].duration / 60);
        let secs = data.videos[0].duration % 60;
        durTag.querySelector('span').innerText = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
        durTag.classList.remove('hidden');
    } else {
        durTag.classList.add('hidden');
    }
    
    const playlistMeta = document.getElementById('playlistMeta');
    const playlistArea = document.getElementById('playlistArea');
    const videoList = document.getElementById('videoList');
    
    activePlaylistVideos = data.videos;
    
    if (data.is_playlist) {
        playlistMeta.innerHTML = `<i class="ri-play-list-2-line"></i> Playlist (${data.videos.length})`;
        playlistMeta.classList.remove('hidden');
        playlistArea.classList.remove('hidden');
        
        videoList.innerHTML = '';
        data.videos.forEach((vid, index) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <label class="checkbox-container">
                    <input type="checkbox" class="vid-checkbox" value="${vid.url}" checked>
                    <span class="checkmark"></span>
                </label>
                <div class="vid-title">${index + 1}. ${vid.title}</div>
            `;
            videoList.appendChild(li);
        });
    } else {
        playlistMeta.classList.add('hidden');
        playlistArea.classList.add('hidden');
    }
    
    previewArea.classList.remove('hidden');
}

// Select All
document.getElementById('selectAll')?.addEventListener('change', (e) => {
    const checkboxes = document.querySelectorAll('.vid-checkbox');
    checkboxes.forEach(cb => cb.checked = e.target.checked);
});

// Format changes quality options
document.getElementById('formatSelect').addEventListener('change', (e) => {
    const qGroup = document.getElementById('qualityGroup');
    const qSelect = document.getElementById('qualitySelect');
    
    if (e.target.value === 'Audio') {
        qSelect.innerHTML = `
            <option value="high">320kbps (High)</option>
            <option value="normal" selected>192kbps (Normal)</option>
            <option value="low">128kbps (Low)</option>
        `;
    } else if (e.target.value === 'Video') {
        qSelect.innerHTML = `
            <option value="1080p">1080p (Best)</option>
            <option value="720p" selected>720p (Good)</option>
            <option value="360p">360p (Data Saver)</option>
        `;
    } else {
        qSelect.innerHTML = `<option value="best">Best Available</option>`;
    }
});


// --- Start Main Download ---
startDownloadBtn.addEventListener('click', async () => {
    const format = document.getElementById('formatSelect').value;
    const quality = document.getElementById('qualitySelect').value;
    
    // Get Selected Videos
    let selectedUrls = [];
    const checkboxes = document.querySelectorAll('.vid-checkbox');
    
    if(checkboxes.length > 0) {
        checkboxes.forEach(cb => { if(cb.checked) selectedUrls.push(cb.value); });
    } else {
        if(activePlaylistVideos.length > 0) selectedUrls.push(activePlaylistVideos[0].url);
    }

    if (selectedUrls.length === 0) {
        alert("Please select at least one video to download.");
        return;
    }

    startDownloadBtn.disabled = true;
    startDownloadBtn.innerHTML = `<i class="ri-loader-4-line ri-spin"></i> Starting...`;

    await executeDownloadRequest(selectedUrls, format, quality, document.getElementById('videoTitle').innerText);

    startDownloadBtn.disabled = false;
    startDownloadBtn.innerHTML = `<i class="ri-download-2-line"></i> Start Download`;
});

// Quick Mode trigger
async function startInstantDownload(apiData) {
    if(apiData.videos.length === 0) return;
    
    let urls = apiData.is_playlist ? apiData.videos.map(v => v.url) : [apiData.videos[0].url];
    // Quick Mode defaults: Audio + High Quality
    await executeDownloadRequest(urls, "Audio", "high", apiData.title);
}

// Execute Request
async function executeDownloadRequest(videos, format, quality, title) {
    try {
        const res = await fetch(`${API_BASE}/download`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ videos, format, quality, title })
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        switchView('downloads');
        createTaskCard(data.task_id, titleName);
        startPolling(data.task_id, format);
        updateBadge(1);
        
        previewArea.classList.add('hidden');
        inputElements.url.value = '';
    } catch (err) {
        alert("Failed to start download: " + err.message);
    }
}

// --- Active Tasks & Polling ---
function updateBadge(change) {
    activeTasksCount += change;
    const badge = document.getElementById('activeBadge');
    if(activeTasksCount > 0) {
        badge.innerText = activeTasksCount;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

function createTaskCard(taskId, title) {
    const list = document.getElementById('activeList');
    const empty = document.getElementById('activeEmpty');
    if(empty) empty.classList.add('hidden');

    const card = document.createElement('div');
    card.className = 'task-card fade-in';
    card.id = `task-${taskId}`;
    
    card.innerHTML = `
        <div class="task-header">
            <div class="task-title"><i class="ri-film-line"></i> ${title}</div>
            <div class="task-status" id="status-${taskId}">Starting...</div>
        </div>
        <div class="progress-container">
            <div class="progress-bar" id="progress-${taskId}"></div>
        </div>
        <div class="task-stats">
            <span id="speed-${taskId}">0 MB/s</span>
            <span id="eta-${taskId}">00:00 ETA</span>
            <span id="count-${taskId}"></span>
        </div>
    `;
    list.prepend(card);
}

function startPolling(taskId, format) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/status/${taskId}`);
            const data = await res.json();
            
            if (data.error) {
                clearInterval(interval);
                return;
            }

            // Update UI
            document.getElementById(`progress-${taskId}`).style.width = `${data.progress}%`;
            document.getElementById(`speed-${taskId}`).innerText = data.speed;
            document.getElementById(`eta-${taskId}`).innerText = `${data.eta} ETA`;
            
            if(data.total_videos > 1) {
                document.getElementById(`count-${taskId}`).innerText = `Video ${data.current_video}/${data.total_videos}`;
            }

            const statusEl = document.getElementById(`status-${taskId}`);
            
            if (data.finished) {
                clearInterval(interval);
                updateBadge(-1);
                
                if (data.error) {
                    statusEl.innerHTML = `<i class="ri-error-warning-line"></i> Failed`;
                    statusEl.classList.add('error');
                    saveToHistory(taskId, document.querySelector(`#task-${taskId} .task-title`).innerText, format, 'failed');
                } else {
                    statusEl.innerHTML = `<i class="ri-check-line"></i> Complete`;
                    statusEl.classList.add('success');
                    
                    // Sound & Popup
                    successSound.play();
                    
                    saveToHistory(taskId, document.querySelector(`#task-${taskId} .task-title`).innerText, format, 'completed');
                    
                    // Move to history visually after 3 seconds
                    setTimeout(() => {
                        const taskEl = document.getElementById(`task-${taskId}`);
                        if(taskEl) taskEl.remove();
                        if(document.getElementById('activeList').children.length === 1) { // Only empty state left
                            document.getElementById('activeEmpty').classList.remove('hidden');
                        }
                    }, 4000);
                }
            } else {
                statusEl.innerText = `${data.progress}% - ${data.status_msg}`;
            }

        } catch(err) {
            console.error("Polling error", err);
        }
    }, 1000);
}

// --- History System ---
function saveToHistory(id, title, format, status) {
    let history = JSON.parse(localStorage.getItem('tb_history') || '[]');
    // title contains HTML string from icon, replace it
    title = title.replace(/<[^>]*>?/gm, '').trim(); 
    history.unshift({ id, title, format, status, date: new Date().toLocaleString() });
    
    // Keep max 100
    if(history.length > 100) history.pop();
    
    localStorage.setItem('tb_history', JSON.stringify(history));
}

function renderHistory(filterType) {
    const list = document.getElementById('historyList');
    const empty = document.getElementById('historyEmpty');
    let history = JSON.parse(localStorage.getItem('tb_history') || '[]');
    
    // Filter
    if (filterType === 'audio') history = history.filter(h => h.format === 'Audio');
    if (filterType === 'video') history = history.filter(h => h.format === 'Video');
    if (filterType === 'completed') history = history.filter(h => h.status === 'completed');
    if (filterType === 'failed') history = history.filter(h => h.status === 'failed');
    
    list.innerHTML = '';
    list.appendChild(empty); // keep empty state element in dom

    if(history.length === 0) {
        empty.classList.remove('hidden');
        return;
    }
    
    empty.classList.add('hidden');
    
    history.forEach(item => {
        const div = document.createElement('div');
        div.className = 'task-card';
        const icon = item.format === 'Audio' ? 'ri-music-2-line' : 'ri-film-line';
        const statIcon = item.status === 'completed' ? '<i class="ri-check-line" style="color:var(--success)"></i>' : '<i class="ri-error-warning-line" style="color:var(--danger)"></i>';
        
        div.innerHTML = `
            <div class="task-header" style="margin-bottom:0; align-items:center;">
                <div class="task-title" style="flex:1;"><i class="${icon}"></i> ${item.title}</div>
                <div style="font-weight: 600; font-size: 1.1rem; margin-right: 16px;">${statIcon}</div>
                <div style="color:var(--text-muted); font-size: 0.85rem">${item.date}</div>
            </div>
        `;
        list.appendChild(div);
    });
}

document.getElementById('clearHistoryBtn').addEventListener('click', () => {
    localStorage.removeItem('tb_history');
    renderHistory('history');
});

// Init
renderHistory('history');
