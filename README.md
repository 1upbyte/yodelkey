# [YodelKey](https://yodelkey.com)

share URLs, text, files and more, easily


## How to self-host
1. Clone the repo
2. cd into the `app` directory
3. `uv run app.py`

File retrieval redirects HTTP requests to HTTPS before authentication or download.
Behind a reverse proxy, set `X-Forwarded-Proto` to the original request scheme.
The app trusts one proxy for this header; restrict backend access to that proxy,
which must overwrite any client-supplied value.
Set `YODELKEY_NO_HTTPS` (even to an empty value) to disable this, e.g.
`YODELKEY_NO_HTTPS=1 uv run app.py` for local HTTP development.

> [!NOTE]
> This project was almost entirely vibe-coded in a very short amount of time. I would only run this in a sandboxed environment.

## Credits
Thank you to [yellkey](https://www.yellkey.com) for original inspiration
