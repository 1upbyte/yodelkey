const api = (typeof browser !== 'undefined') ? browser : chrome;
const DEFAULT_SERVER = 'http://localhost:5000';

const form       = document.getElementById('optionsForm');
const serverInput= document.getElementById('serverUrl');
const statusMsg  = document.getElementById('statusMsg');

// Load saved value on open
api.storage.sync.get({ serverUrl: DEFAULT_SERVER }).then(stored => {
    serverInput.value = stored.serverUrl || DEFAULT_SERVER;
});

form.addEventListener('submit', async e => {
    e.preventDefault();

    let url = serverInput.value.trim().replace(/\/$/, '');

    // Basic validation
    if (!url) {
        url = DEFAULT_SERVER;
        serverInput.value = url;
    }
    if (!/^https?:\/\//i.test(url)) {
        showStatus('URL must start with http:// or https://', 'err');
        return;
    }

    try {
        await api.storage.sync.set({ serverUrl: url });
        showStatus('Settings saved!', 'ok');
    } catch (err) {
        showStatus(`Failed to save: ${err.message}`, 'err');
    }
});

function showStatus(msg, type) {
    statusMsg.textContent = msg;
    statusMsg.className = `status-msg ${type}`;
    // Re-trigger animation by briefly removing/re-adding class
    void statusMsg.offsetWidth;
    clearTimeout(statusMsg._timer);
    statusMsg._timer = setTimeout(() => {
        statusMsg.className = 'status-msg hidden';
    }, 3000);
}
