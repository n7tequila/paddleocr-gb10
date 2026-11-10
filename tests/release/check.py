"""Anonymous metadata-only GHCR and GitHub Release verification."""
import json
import urllib.error
import urllib.parse
import urllib.request

IMAGE = "ghcr.io/n7tequila/paddleocr-gb10:0.2.0"
REPOSITORY = "n7tequila/paddleocr-gb10"
WHEEL = "paddlepaddle_gpu-3.5.0.dev20261109+6c839e963ed-cp312-cp312-linux_aarch64.whl"
SHA256 = "a235ad6edcdf4b499ec3f86829d5302766cee1ee66de7c7786cf44660baf75bb"
ACCEPT = ", ".join(("application/vnd.oci.image.index.v1+json",
                    "application/vnd.docker.distribution.manifest.list.v2+json",
                    "application/vnd.oci.image.manifest.v1+json",
                    "application/vnd.docker.distribution.manifest.v2+json"))


def fetch(url, headers=None, timeout=20):
    request = urllib.request.Request(url, headers={"User-Agent": "paddleocr-gb10-release-check/0.2.1", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        label = "unauthorized" if exc.code in (401, 403) else "not found" if exc.code == 404 else "HTTP error"
        raise RuntimeError(f"{label}: HTTP {exc.code} from {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"network error from {url}: {exc}") from exc


def check_ghcr():
    token_url = "https://ghcr.io/token?" + urllib.parse.urlencode({
        "scope": f"repository:{REPOSITORY}:pull", "service": "ghcr.io"})
    token = json.loads(fetch(token_url)[0])["token"]
    headers = {"Authorization": f"Bearer {token}", "Accept": ACCEPT}
    manifest_url = f"https://ghcr.io/v2/{REPOSITORY}/manifests/0.2.0"
    raw, response_headers = fetch(manifest_url, headers)
    manifest = json.loads(raw)
    digest = response_headers.get("Docker-Content-Digest") or response_headers.get("docker-content-digest")
    assert digest and digest.startswith("sha256:"), "GHCR did not provide a content digest"
    platforms = [entry.get("platform") for entry in manifest.get("manifests", [])]
    if platforms:
        assert any(p.get("os") == "linux" and p.get("architecture") == "arm64" for p in platforms), f"linux/arm64 missing: {platforms}"
    else:
        # A single-platform manifest carries architecture in its config blob.
        config = manifest.get("config", {}).get("digest")
        assert config, "Single-platform manifest has no config digest"
        config_data = json.loads(fetch(f"https://ghcr.io/v2/{REPOSITORY}/blobs/{config}", headers)[0])
        assert config_data.get("os") == "linux" and config_data.get("architecture") == "arm64", config_data
        platforms = [{"os": config_data["os"], "architecture": config_data["architecture"]}]
    return {"image": IMAGE, "digest": digest, "platforms": platforms}


def check_release():
    data = json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/releases/tags/v0.2.0",
                            {"Accept": "application/vnd.github+json"})[0])
    names = {asset["name"] for asset in data.get("assets", [])}
    assert {WHEEL, "SHA256SUMS"} <= names, f"Release assets missing: {names}"
    checksums = fetch(f"https://github.com/{REPOSITORY}/releases/download/v0.2.0/SHA256SUMS")[0].decode()
    entries = dict((name, digest) for digest, name in
                   (line.split(maxsplit=1) for line in checksums.splitlines() if line.strip()))
    assert entries.get(WHEEL) == SHA256, f"Wheel checksum mismatch: {entries.get(WHEEL)}"
    return {"release": data["html_url"], "assets": sorted(names), "wheel_sha256": SHA256}
