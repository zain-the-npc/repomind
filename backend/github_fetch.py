"""
Pulls all relevant files from a public GitHub repo using the REST API.
No git clone needed - uses the git trees API + raw content fetch.
"""

import re
import requests
from config import GITHUB_TOKEN, CODE_EXTENSIONS, DOC_EXTENSIONS, SKIP_DIRS, SKIP_FILES, MAX_FILE_SIZE_BYTES


def parse_github_url(url: str) -> tuple[str, str]:
    """
    'https://github.com/owner/repo' -> ('owner', 'repo')
    Also handles trailing slash, .git suffix, branch paths.
    """
    match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
    if not match:
        raise ValueError(f"Not a valid GitHub repo URL: {url}")
    owner, repo = match.group(1), match.group(2)
    repo = repo.removesuffix(".git")
    return owner, repo


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _get_default_branch(owner: str, repo: str) -> str:
    resp = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=_headers())
    resp.raise_for_status()
    return resp.json()["default_branch"]


def _should_skip(path: str, size: int) -> bool:
    if size > MAX_FILE_SIZE_BYTES:
        return True
    parts = path.split("/")
    if any(p in SKIP_DIRS for p in parts):
        return True
    filename = parts[-1]
    if filename in SKIP_FILES:
        return True
    ext = "." + filename.split(".")[-1] if "." in filename else ""
    if ext not in CODE_EXTENSIONS and ext not in DOC_EXTENSIONS:
        return True
    return False


def _classify(path: str) -> str:
    ext = "." + path.split(".")[-1] if "." in path else ""
    return "code" if ext in CODE_EXTENSIONS else "doc"


def get_files(repo_url: str) -> list[dict]:
    """
    Returns list of dicts: {path, content, language_or_type}
    Skips binaries, lockfiles, huge files, and SKIP_DIRS.
    """
    owner, repo = parse_github_url(repo_url)
    branch = _get_default_branch(owner, repo)

    tree_resp = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
        headers=_headers(),
    )
    tree_resp.raise_for_status()
    tree = tree_resp.json()["tree"]

    files = []
    for entry in tree:
        if entry["type"] != "blob":
            continue
        path = entry["path"]
        size = entry.get("size", 0)
        if _should_skip(path, size):
            continue

        # Uses raw.githubusercontent.com instead of the blob API — much higher
        # rate limit (blob API burns 1 API request per file, hits 60/hr unauthenticated
        # limit fast on real repos).
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        raw_resp = requests.get(raw_url)
        if raw_resp.status_code != 200:
            continue  # skip files that fail to fetch

        try:
            content = raw_resp.content.decode("utf-8")
        except UnicodeDecodeError:
            continue  # binary file slipped through, skip

        files.append({
            "path": path,
            "content": content,
            "type": _classify(path),
        })

    return files


if __name__ == "__main__":
    # quick manual test
    test_url = "https://github.com/psf/requests"
    result = get_files(test_url)
    print(f"Fetched {len(result)} files")
    for f in result[:5]:
        print(f["type"], f["path"], len(f["content"]), "chars")