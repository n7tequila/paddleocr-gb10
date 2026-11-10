# Publish to GitHub from macOS / 从 macOS 发布

> Historical v0.1.0 bootstrap instructions below. The repository is no longer empty. Do not rerun this script against the populated repository for v0.2.0.

## Current v0.2.0 publication status

The [v0.2.0 GitHub Release](https://github.com/n7tequila/paddleocr-gb10/releases/tag/v0.2.0) has the GPU Wheel and matching `SHA256SUMS` attachment. Anonymous requests for `ghcr.io/n7tequila/paddleocr-gb10:0.2.0` now return HTTP 200 for the token and OCI index; the index includes `linux/arm64`. A full image pull and remote GPU retest remain outstanding. If the GitHub Package page is still hidden, connect the package to this repository and confirm Public visibility in the GitHub UI. See [release details](docs/releases.md).

Destination (already created): https://github.com/n7tequila/paddleocr-gb10

The supplied ZIP and standalone script are for **macOS**. They do not execute any OCR models or need access to the Spark machine.

1. Download `paddleocr-gb10-v0.1.0.zip` and `publish-paddleocr-gb10-macos.sh` into the same Mac folder (e.g. `~/Downloads`).
2. Ensure git works (`git --version`), set `git config --global user.name` and `git config --global user.email` if needed, and authenticate with GitHub over HTTPS. You can use `gh auth login` followed by `gh auth setup-git` if you have GitHub CLI.
3. Open Terminal and run:

```bash
cd ~/Downloads
chmod +x publish-paddleocr-gb10-macos.sh
./publish-paddleocr-gb10-macos.sh paddleocr-gb10-v0.1.0.zip
```

The script clones the existing repository, checks for an empty remote, commits the files and pushes to `main`. It never uses `--force`. It refuses to overwrite any repository that already contains tracked files.

Optionally, **only if you want a tagged GitHub Release and have `gh` installed/authenticated**, use:

```bash
./publish-paddleocr-gb10-macos.sh paddleocr-gb10-v0.1.0.zip --release
```

This uploads the source ZIP as a release asset, not the GB10 Wheel. GitHub Release is optional; the regular publish is sufficient to populate the repository.

如果 HTTPS 推送认证失败，请先运行 `gh auth login` 和 `gh auth setup-git`，再重试脚本。脚本会重新克隆仓库；如果前一次已经推送成功，重试会因远端非空而安全退出。
