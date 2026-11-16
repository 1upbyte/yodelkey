self.onmessage = async ({ data: url }) => {
    try {
        const response = await fetch(url, { cache: 'no-store', redirect: 'error' });
        if (!response.ok) {
            throw new Error(response.status === 403
                ? 'Password incorrect. Open the original link to try again.'
                : 'The file is no longer available.');
        }
        const blob = await response.blob();
        self.postMessage({ blob });
    } catch (error) {
        self.postMessage({ error: error.message || 'Unable to download the file.' });
    }
};
