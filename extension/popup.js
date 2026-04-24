// Cross-browser API shim
const api = (typeof browser !== 'undefined') ? browser : chrome;

const SERVER  = 'https://yodelkey.com';
const MAX_FILE = 100 * 1024 * 1024; // 100 MB

// ── DOM refs ──────────────────────────────────────────────────────────────────
const tabs          = document.querySelectorAll('.tab');
const typeInput     = document.getElementById('typeInput');
const sharePanel    = document.getElementById('sharePanel');
const retrievePanel = document.getElementById('retrievePanel');
const contentGrp    = document.getElementById('contentGroup');
const fileGrp       = document.getElementById('fileGroup');
const contentInput  = document.getElementById('contentInput');
const fileInput     = document.getElementById('fileInput');
const shareForm     = document.getElementById('shareForm');
const submitBtn     = document.getElementById('submitBtn');
const resultDiv     = document.getElementById('result');
const fileInfo      = document.getElementById('fileInfo');
const retrieveForm  = document.getElementById('retrieveForm');
const keyInput      = document.getElementById('keyInput');
const retrieveError = document.getElementById('retrieveError');

// ── Init ───────────────────────────────────────────────────────────────────────
(async function init() {
    try {
        const [tab] = await api.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.url && /^https?:\/\//.test(tab.url)) {
            contentInput.value = tab.url;
        }
    } catch (_) {}
})();

// ── Tab switching ──────────────────────────────────────────────────────────────
tabs.forEach(tab => {
    tab.addEventListener('click', function () {
        tabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');

        const type = this.dataset.type;
        typeInput.value = type;

        // Clear results when switching tabs
        resultDiv.style.display = 'none';
        retrieveError.classList.add('hidden');

        if (type === 'retrieve') {
            sharePanel.classList.add('hidden');
            retrievePanel.classList.remove('hidden');
            keyInput.focus();
            return;
        }

        sharePanel.classList.remove('hidden');
        retrievePanel.classList.add('hidden');

        if (type === 'file') {
            contentGrp.classList.add('hidden');
            fileGrp.classList.remove('hidden');
            contentInput.removeAttribute('required');
            fileInput.setAttribute('required', 'required');
        } else {
            contentGrp.classList.remove('hidden');
            fileGrp.classList.add('hidden');
            contentInput.setAttribute('required', 'required');
            fileInput.removeAttribute('required');
            contentInput.placeholder = type === 'url'
                ? 'https://example.com'
                : 'Enter your text here...';
        }
    });
});

// Submit on Enter for URL tab only
contentInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && typeInput.value === 'url') {
        e.preventDefault();
        shareForm.requestSubmit();
    }
});

// File size validation on selection
fileInput.addEventListener('change', function () {
    if (this.files.length > 0) {
        const file = this.files[0];
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        if (file.size > MAX_FILE) {
            fileInfo.textContent = `File too large: ${sizeMB} MB (max 100 MB)`;
            fileInfo.classList.add('file-error');
        } else {
            fileInfo.textContent = `Selected: ${file.name} (${sizeMB} MB)`;
            fileInfo.classList.remove('file-error');
        }
    } else {
        fileInfo.textContent = '';
        fileInfo.classList.remove('file-error');
    }
});

// ── Share form ─────────────────────────────────────────────────────────────────
shareForm.addEventListener('submit', async function (e) {
    e.preventDefault();

    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating…';

    const formData = new FormData();
    formData.append('type', typeInput.value);

    if (typeInput.value === 'file') {
        if (!fileInput.files.length) {
            showShareError('Please select a file.');
            resetSubmit();
            return;
        }
        const file = fileInput.files[0];
        if (file.size > MAX_FILE) {
            showShareError('File size exceeds 100 MB limit.');
            resetSubmit();
            return;
        }
        formData.append('file', file);
    } else {
        formData.append('content', contentInput.value);
    }

    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar    = document.getElementById('progressBar');
    const progressText   = document.getElementById('progressText');

    if (typeInput.value === 'file') {
        uploadProgress.classList.add('active');
    }

    try {
        const key = await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', ev => {
                if (ev.lengthComputable) {
                    const pct = (ev.loaded / ev.total) * 100;
                    progressBar.style.width = pct + '%';
                    progressText.textContent = `Uploading… ${Math.round(pct)}%`;
                }
            });

            xhr.onload = () => {
                const body = xhr.responseText.trim();
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(body);
                } else {
                    reject(new Error(body || `Server error (HTTP ${xhr.status})`));
                }
            };
            xhr.onerror = () => reject(new Error('Network error — check your connection.'));
            xhr.open('POST', `${SERVER}/create`);
            xhr.send(formData);
        });

        if (typeInput.value === 'file') {
            progressBar.style.width = '100%';
            progressText.textContent = 'Upload complete!';
        }

        showShareSuccess(key);

    } catch (err) {
        if (uploadProgress.classList.contains('active')) {
            progressBar.style.width = '0%';
            progressText.textContent = 'Upload failed';
        }
        showShareError(err.message);
    } finally {
        resetSubmit();
    }
});

function resetSubmit() {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Create Share Link';
}

function showShareError(msg) {
    resultDiv.className = 'result error';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `<strong>Error:</strong> ${escHtml(msg)}`;
}

function showShareSuccess(key) {
    const fullUrl = `${SERVER}/${key}`;

    resultDiv.className = 'result';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `
        <div class="result-main">
            <div class="result-text">
                <div class="result-content">
                    <span class="result-label">Key:</span>
                    <span class="share-key" id="shareKey">${escHtml(key)}</span>
                </div>
                <div class="result-link">
                    <a href="${escHtml(fullUrl)}" target="_blank">${escHtml(fullUrl)}</a>
                </div>
            </div>
            <div class="result-qr">
                <div id="qrcode"></div>
            </div>
        </div>
    `;

    new QRCode(document.getElementById('qrcode'), {
        text: fullUrl,
        width: 80,
        height: 80,
        colorDark: '#000000',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.H
    });
    addLogoToQR('qrcode', 16);

    document.getElementById('qrcode').addEventListener('click', () => showQRModal(fullUrl));

    document.getElementById('shareKey').addEventListener('click', async function () {
        try {
            await navigator.clipboard.writeText(fullUrl);
            const orig = this.textContent;
            this.textContent = 'Copied!';
            setTimeout(() => { this.textContent = orig; }, 1500);
        } catch (_) {}
    });
}

// ── Retrieve form ──────────────────────────────────────────────────────────────
retrieveForm.addEventListener('submit', e => {
    e.preventDefault();

    const key = keyInput.value.trim().toLowerCase();
    if (!key) {
        retrieveError.className = 'result error';
        retrieveError.style.display = 'block';
        retrieveError.innerHTML = '<strong>Error:</strong> Enter a word key first.';
        return;
    }

    retrieveError.style.display = 'none';
    api.tabs.create({ url: `${SERVER}/${encodeURIComponent(key)}` });
    window.close();
});

// ── QR helpers ─────────────────────────────────────────────────────────────────
function addLogoToQR(containerId, logoSize) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const canvas = container.querySelector('canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.onload = function () {
        const cx = (canvas.width - logoSize) / 2;
        const cy = (canvas.height - logoSize) / 2;
        ctx.fillStyle = 'white';
        ctx.beginPath();
        ctx.arc(canvas.width / 2, canvas.height / 2, logoSize / 2 + 2, 0, 2 * Math.PI);
        ctx.fill();
        ctx.drawImage(img, cx, cy, logoSize, logoSize);
    };
    img.src = 'icons/icon48.png';
}

function showQRModal(url) {
    const modal = document.getElementById('qrModal');
    document.getElementById('qrcodeLarge').innerHTML = '';

    new QRCode(document.getElementById('qrcodeLarge'), {
        text: url,
        width: 300,
        height: 300,
        colorDark: '#000000',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.H
    });
    addLogoToQR('qrcodeLarge', 60);

    requestAnimationFrame(() => modal.classList.add('active'));
}

document.getElementById('qrModal').addEventListener('click', function (e) {
    if (!document.getElementById('qrModalContent').contains(e.target)) {
        this.classList.remove('active');
        setTimeout(() => { document.getElementById('qrcodeLarge').innerHTML = ''; }, 300);
    }
});

// ── Utilities ──────────────────────────────────────────────────────────────────
function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
