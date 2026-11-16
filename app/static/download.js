const link = document.getElementById('download');
const status = document.getElementById('status');
const downloadUrl = new URL(window.location.href);
downloadUrl.searchParams.set('download', '1');
link.href = downloadUrl.href;

let worker;
let blobUrl;

function showError(message) {
    status.textContent = message;
    worker?.terminate();
}

try {
    worker = new Worker(link.dataset.worker);
    worker.onmessage = ({ data }) => {
        if (data.error) {
            showError(data.error);
            return;
        }
        blobUrl = URL.createObjectURL(data.blob);
        link.href = blobUrl;
        link.download = link.dataset.filename;
        link.textContent = 'Save file';
        link.click();
        status.textContent = 'Your file is ready. If the download did not start, click Save file.';
        worker.terminate();
    };
    worker.onerror = () => showError('Unable to start the download. Try the direct download link.');
    worker.postMessage(downloadUrl.href);
} catch {
    showError('Background downloads are unavailable. Try the direct download link.');
}

window.addEventListener('pagehide', (event) => {
    if (!event.persisted) {
        worker?.terminate();
        if (blobUrl) URL.revokeObjectURL(blobUrl);
    }
});
