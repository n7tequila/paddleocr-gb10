#!/usr/bin/env bash
# Publish a prepared paddleocr-gb10 ZIP to the EXISTING GitHub repository.
# macOS system Bash 3.2 compatible. No force push / no remote history rewrite.
set -euo pipefail

REPO_URL="https://github.com/n7tequila/paddleocr-gb10.git"
REPO_SLUG="n7tequila/paddleocr-gb10"
ZIP_DEFAULT="paddleocr-gb10-v0.1.0.zip"
ZIP_PATH="${1:-$ZIP_DEFAULT}"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command -v git >/dev/null 2>&1 || fail 'git is not installed (install Xcode Command Line Tools: xcode-select --install)'
command -v unzip >/dev/null 2>&1 || fail 'unzip is not available'
[[ -f "$ZIP_PATH" ]] || fail "ZIP missing: $ZIP_PATH (pass the downloaded zip path as first argument)"
ZIP_PATH="$(cd "$(dirname "$ZIP_PATH")" && pwd)/$(basename "$ZIP_PATH")"

# Auth via existing Git credential helper, or GitHub CLI if installed.
if command -v gh >/dev/null 2>&1; then
  if ! gh auth status >/dev/null 2>&1; then
    printf 'GitHub CLI is installed but not authenticated. Run: gh auth login\n'
    printf 'If HTTPS Git credentials are already set up, the push may still work.\n'
  fi
fi

TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/paddleocr-gb10-publish.XXXXXX")"
trap 'rm -rf "$TEMP_DIR"' EXIT HUP INT TERM
printf 'Extracting ZIP...\n'
unzip -q "$ZIP_PATH" -d "$TEMP_DIR/extract"
SOURCE="$TEMP_DIR/extract/paddleocr-gb10"
[[ -f "$SOURCE/README.md" && -f "$SOURCE/README.zh-CN.md" ]] || fail 'Unexpected ZIP structure (expected paddleocr-gb10/README.md)'
[[ -f "$SOURCE/LICENSE" ]] || fail 'LICENSE missing'

printf 'Cloning existing GitHub repository...\n'
git clone "$REPO_URL" "$TEMP_DIR/remote"
cd "$TEMP_DIR/remote"
# Work on the server default branch, or initialize main if the repository is still empty.
if git show-ref --verify --quiet refs/heads/main; then
  git checkout main
elif git ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
  git fetch origin main
  git checkout -b main --track origin/main
elif git rev-parse HEAD >/dev/null 2>&1; then
  fail 'Remote has commits but no main branch. Review its default branch first; script refuses to overwrite it.'
else
  git checkout -B main
fi

# Only populate a truly empty repo; otherwise do not silently overwrite user work.
if [[ -n "$(git ls-files)" ]]; then
  fail 'Remote repository is no longer empty. Script will not replace existing files. Review manually.'
fi

# Clean directory exclusion is intentional: only project files, not archive or credentials.
cp -R "$SOURCE/." "$TEMP_DIR/remote/"
find . -name '.DS_Store' -type f -delete

git add -A
git diff --cached --check
printf '\nStaged changes:\n'
git diff --cached --stat
[[ -n "$(git diff --cached --name-only)" ]] || fail 'Nothing to publish'

if [[ -z "$(git config user.name || true)" || -z "$(git config user.email || true)" ]]; then
  fail 'Set your Git identity first: git config --global user.name "Your Name" && git config --global user.email "you@example.com"'
fi

git commit -m 'Initial release: PaddleOCR on NVIDIA GB10 (v0.1.0)'
printf '\nPushing to GitHub (no force push)...\n'
git push -u origin main

printf '\nSUCCESS: https://github.com/%s\n' "$REPO_SLUG"
printf 'Source ZIP remains at: %s\n' "$ZIP_PATH"
printf 'NOTE: No PaddlePaddle Wheel or model weights were uploaded.\n'

if [[ "${2:-}" == '--release' ]]; then
  command -v gh >/dev/null 2>&1 || fail 'To create a GitHub release, install GitHub CLI: brew install gh'
  gh auth status >/dev/null 2>&1 || fail 'Run gh auth login before creating the GitHub Release'
  git tag v0.1.0
  git push origin v0.1.0
  gh release create v0.1.0 "$ZIP_PATH" --repo "$REPO_SLUG" --title 'v0.1.0 — GB10 foundation' --notes-file "$SOURCE/docs/releases.md"
  printf 'Release: https://github.com/%s/releases/tag/v0.1.0\n' "$REPO_SLUG"
fi
