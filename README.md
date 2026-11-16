# [YodelKey](https://yodelkey.com)

share URLs, text, files and more, easily


## How to self-host
1. Clone the repo
2. cd into the `app` directory
3. `uv run app.py`

Browser file links open a download page that fetches the file in a background
Web Worker and saves it through a blob URL, working around
[Chromium's HTTP/HSTS download warning](https://issues.chromium.org/issues/584973367).
Clients such as curl receive the file directly. Use `?download=1` for a direct
download in a browser without JavaScript. Passwords are still required, and
burn-after-read files are consumed when the file is fetched, not when the page opens.

> [!NOTE]
> This project was almost entirely vibe-coded in a very short amount of time. I would only run this in a sandboxed environment.

## Credits
Thank you to [yellkey](https://www.yellkey.com) for original inspiration
