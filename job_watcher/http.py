"""Small HTTP helpers with a browser-like user agent and simple retries."""
import html
import re
import time

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})


def _request(method, url, retries=2, **kwargs):
    kwargs.setdefault("timeout", 30)
    for attempt in range(retries + 1):
        try:
            response = _session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(2 * (attempt + 1))


def get_json(url, **kwargs):
    return _request("GET", url, **kwargs).json()


def get_text(url, **kwargs):
    return _request("GET", url, **kwargs).text


def post_json(url, payload, **kwargs):
    return _request("POST", url, json=payload, **kwargs).json()


def strip_html(text: str) -> str:
    """HTML (possibly entity-escaped) to plain, single-spaced text."""
    text = html.unescape(html.unescape(text or ""))
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()
