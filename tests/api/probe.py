"""Official PaddleX HTTP contract helpers; standard library only."""
import base64
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, ProxyHandler, build_opener

OPENER = build_opener(ProxyHandler({}))  # Never send loopback requests to a proxy.


def base_url(value):
    value = value.rstrip("/")
    if value.endswith("/layout-parsing"):
        value = value.removesuffix("/layout-parsing")
    if not value.startswith(("http://", "https://")):
        raise ValueError("PADDLEOCR_API_URL must be an HTTP(S) base URL")
    return value


def request_json(url, payload=None, timeout=10):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, method="GET" if data is None else "POST",
                      headers={"Content-Type": "application/json"})
    start = time.monotonic()
    try:
        response = OPENER.open(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
    with response:
        status = response.status
        raw = response.read()
    elapsed = time.monotonic() - start
    try:
        body = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise AssertionError(f"HTTP {status}: response is not JSON: {raw[:200]!r}") from exc
    return status, body, elapsed


def health(url, timeout=10):
    status, body, elapsed = request_json(base_url(url) + "/health", timeout=timeout)
    assert status == 200, f"GET /health returned HTTP {status}: {body}"
    assert isinstance(body, dict) and body.get("errorCode") == 0, body
    return {"http_status": status, "elapsed_s": round(elapsed, 3), "response": body}


def image_payload(image_path):
    return {"file": base64.b64encode(Path(image_path).read_bytes()).decode("ascii"),
            "fileType": 1, "visualize": False}


def infer(url, image_path, timeout=300, expected_pages=1, on_response=None):
    status, body, elapsed = request_json(base_url(url) + "/layout-parsing",
                                         image_payload(image_path), timeout=timeout)
    if on_response:
        on_response(status, body, elapsed)
    assert status == 200, f"POST /layout-parsing returned HTTP {status}: {str(body)[:500]}"
    assert isinstance(body, dict) and body.get("errorCode") == 0, body
    pages = body.get("result", {}).get("layoutParsingResults")
    assert isinstance(pages, list) and len(pages) == expected_pages, f"Expected {expected_pages} page(s), got {pages!r}"
    for index, page in enumerate(pages):
        assert isinstance(page, dict) and "prunedResult" in page and "markdown" in page, f"Page {index} missing fields"
        markdown = page["markdown"]
        assert isinstance(markdown, dict) and isinstance(markdown.get("text"), str) and markdown["text"].strip(), f"Page {index} has empty Markdown"
    assert elapsed <= timeout, f"Inference exceeded {timeout}s: {elapsed:.2f}s"
    return {"http_status": status, "elapsed_s": round(elapsed, 3),
            "pages": len(pages), "markdown_chars": sum(len(p["markdown"]["text"]) for p in pages),
            "response": body}


def invalid_request(url, payload, timeout=30):
    status, body, elapsed = request_json(base_url(url) + "/layout-parsing", payload, timeout=timeout)
    assert status >= 400 or (isinstance(body, dict) and body.get("errorCode", 0) != 0), (
        f"Invalid request was accepted: HTTP {status}, {str(body)[:300]}")
    return {"http_status": status, "elapsed_s": round(elapsed, 3), "response": body}
