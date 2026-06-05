#!/usr/bin/env python3
"""Fetch BUUCTF challenge metadata and attachments into Amadeus/challenges.

This tool intentionally avoids writeup/solution endpoints. It only requests:
- CTFd challenge list/detail APIs needed to identify the target challenge
- file URLs returned by the challenge detail API

Cookie, when needed, is read from BUUCTF_COOKIE or BUUOJ_COOKIE and is never
written to disk.
ROOT/.env is loaded when present; existing shell environment variables win.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHALLENGES_DIR = ROOT / "challenges"
INIT_SCRIPT = ROOT / "bin" / "init_challenge.sh"
sys.path.insert(0, str(ROOT / "bin"))
import state_docs  # noqa: E402
BASE_URL = "https://buuoj.cn"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
    "X-Requested-With": "XMLHttpRequest",
}

LIST_ENDPOINTS = [
    "/api/v1/challenges",
    "/api/v1/challenges/",
]


class FetchError(RuntimeError):
    pass


class AuthNeeded(FetchError):
    pass


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        if key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ[key] = value


def safe_title(title: str) -> str:
    title = title.strip()
    title = title.replace("/", "_").replace("\x00", "")
    title = re.sub(r"\s+", " ", title)
    return title or "buuctf_unknown"


def safe_group_path(group: str) -> Path:
    parts = [safe_title(part) for part in re.split(r"[\\/]+", group.strip()) if part.strip()]
    if any(part in {".", ".."} for part in parts):
        raise FetchError("group must not contain '.' or '..' path segments")
    return Path(*parts) if parts else Path()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def parse_target(value: str) -> tuple[str, str, str]:
    """Return (challenge_id, title_hint, source_url)."""
    if value.isdigit():
        return value, "", f"{BASE_URL}/challenges"

    parsed = urllib.parse.urlparse(value)
    if not parsed.scheme and not parsed.netloc:
        return "", urllib.parse.unquote(value), f"{BASE_URL}/challenges#{urllib.parse.quote(value)}"

    challenge_id = ""
    for pattern in (
        r"/api/v1/challenges/(\d+)",
        r"/challenges/(\d+)",
        r"/challenge/(\d+)",
    ):
        match = re.search(pattern, parsed.path)
        if match:
            challenge_id = match.group(1)
            break

    query = urllib.parse.parse_qs(parsed.query)
    if not challenge_id:
        for key in ("id", "challenge", "challenge_id"):
            if query.get(key) and query[key][0].isdigit():
                challenge_id = query[key][0]
                break

    title_hint = urllib.parse.unquote(parsed.fragment or "")
    if not title_hint:
        for key in ("name", "title"):
            if query.get(key):
                title_hint = urllib.parse.unquote(query[key][0])
                break

    return challenge_id, title_hint, value


def auth_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    token = os.environ.get("BUUCTF_TOKEN") or os.environ.get("BUUOJ_TOKEN")
    if token:
        headers["Authorization"] = f"Token {token}"
    return headers


def is_login_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.path.rstrip("/") == "/login"


def request_bytes(
    url: str,
    cookie: str = "",
    headers: dict[str, str] | None = None,
    expect_json: bool = False,
) -> tuple[bytes, dict[str, str], str]:
    req_headers = dict(DEFAULT_HEADERS)
    req_headers.update(auth_headers())
    if headers:
        req_headers.update(headers)
    if cookie:
        req_headers["Cookie"] = cookie

    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            final_url = resp.geturl()
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        body = exc.read()
        location = exc.headers.get("Location", "")
        if exc.code in (301, 302, 303, 307, 308) and is_login_url(urllib.parse.urljoin(url, location)):
            raise AuthNeeded("BUUCTF login required; set BUUCTF_COOKIE or BUUOJ_COOKIE")
        raise FetchError(f"HTTP {exc.code} for {url}: {body[:200]!r}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"request failed for {url}: {exc}") from exc

    if is_login_url(final_url):
        raise AuthNeeded("BUUCTF login required; set BUUCTF_COOKIE or BUUOJ_COOKIE")
    if expect_json and body.lstrip().startswith(b"<!DOCTYPE"):
        raise AuthNeeded("BUUCTF returned HTML instead of JSON; login cookie is probably missing or expired")
    return body, resp_headers, final_url


def request_json(url: str, cookie: str = "", headers: dict[str, str] | None = None) -> Any:
    body, _, _ = request_bytes(url, cookie=cookie, headers=headers, expect_json=True)
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise FetchError(f"non-JSON response from {url}: {body[:200]!r}") from exc


def unwrap_data(data: Any) -> Any:
    if isinstance(data, dict) and "success" in data and data.get("success") is False:
        raise FetchError(f"BUUCTF API returned success=false: {data!r}")
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


def challenge_items(data: Any) -> list[dict[str, Any]]:
    data = unwrap_data(data)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("challenges", "results", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def fetch_challenge_list(cookie: str) -> list[dict[str, Any]]:
    errors: list[str] = []
    for endpoint in LIST_ENDPOINTS:
        url = urllib.parse.urljoin(BASE_URL, endpoint)
        try:
            items = challenge_items(request_json(url, cookie=cookie, headers={"Referer": f"{BASE_URL}/challenges"}))
            if items:
                return items
            errors.append(f"{endpoint}: empty list")
        except FetchError as exc:
            errors.append(f"{endpoint}: {exc}")
    raise FetchError("could not fetch BUUCTF challenge list; " + "; ".join(errors))


def item_name(item: dict[str, Any]) -> str:
    value = item.get("name") or item.get("title") or item.get("challenge")
    return str(value or "")


def item_id(item: dict[str, Any]) -> str:
    value = item.get("id") or item.get("challenge_id")
    return str(value or "")


def find_challenge_by_title(items: list[dict[str, Any]], title: str) -> dict[str, Any]:
    wanted = normalize_text(title)
    exact = [item for item in items if normalize_text(item_name(item)) == wanted]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        names = ", ".join(f"{item_id(item)}:{item_name(item)}" for item in exact)
        raise FetchError(f"multiple BUUCTF challenges exactly match {title!r}: {names}")

    contains = [item for item in items if wanted and wanted in normalize_text(item_name(item))]
    if len(contains) == 1:
        return contains[0]
    if contains:
        names = ", ".join(f"{item_id(item)}:{item_name(item)}" for item in contains[:10])
        raise FetchError(f"multiple BUUCTF challenges contain {title!r}: {names}")
    raise FetchError(f"BUUCTF challenge not found by title: {title!r}")


def fetch_challenge_detail(challenge_id: str, cookie: str) -> dict[str, Any]:
    errors: list[str] = []
    for endpoint in (f"/api/v1/challenges/{challenge_id}", f"/api/v1/challenges/{challenge_id}/"):
        url = urllib.parse.urljoin(BASE_URL, endpoint)
        try:
            data = unwrap_data(request_json(url, cookie=cookie, headers={"Referer": f"{BASE_URL}/challenges"}))
            if isinstance(data, dict):
                return data
            errors.append(f"{endpoint}: detail was not an object")
        except FetchError as exc:
            errors.append(f"{endpoint}: {exc}")
    raise FetchError("could not fetch BUUCTF challenge detail; " + "; ".join(errors))


def tag_names(problem: dict[str, Any]) -> list[str]:
    tags = problem.get("tags") or problem.get("tag") or []
    names: list[str] = []
    for item in tags:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            name = item.get("value") or item.get("name") or item.get("title")
            if name:
                names.append(str(name))
        elif isinstance(item, (list, tuple)) and item:
            names.append(str(item[0]))
    return names


def category_name(problem: dict[str, Any]) -> str:
    value = problem.get("category") or problem.get("type") or ""
    return str(value or "")


def normalize_challenge_type(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {
        "pwn": "pwn",
        "web": "web",
        "reverse": "reverse",
        "re": "reverse",
        "rev": "reverse",
        "crypto": "crypto",
        "cryptography": "crypto",
        "misc": "misc",
        "mobile": "mobile",
        "forensics": "forensics",
        "forensic": "forensics",
    }
    return aliases.get(normalized, normalized)


def description_text(problem: dict[str, Any]) -> str:
    value = problem.get("description") or problem.get("desc") or ""
    if value is None:
        return ""
    return html.unescape(str(value)).strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_text_if_allowed(path: Path, content: str, overwrite: bool) -> None:
    if path.exists() and not overwrite and not is_stock_template(path):
        return
    path.write_text(content, encoding="utf-8")


def is_stock_template(path: Path) -> bool:
    template = ROOT / "templates" / path.name
    if not template.exists():
        return False
    try:
        return path.read_text(encoding="utf-8") == template.read_text(encoding="utf-8")
    except OSError:
        return False


def run_init(challenge_dir: Path) -> None:
    subprocess.run([str(INIT_SCRIPT), str(challenge_dir)], cwd=ROOT, check=True)


def update_cognition(
    challenge_dir: Path,
    metadata: dict[str, Any],
    facts_text: str,
    state_text: str,
    overwrite: bool,
) -> None:
    if not overwrite:
        return
    data = state_docs.load_cognition(challenge_dir)
    data["metadata"] = metadata
    data["facts"] = state_docs.facts_from_markdown_text(facts_text, challenge_dir.name)
    data["state"] = state_docs.state_from_markdown_text(state_text, challenge_dir.name)
    state_docs.write_json(state_docs.cognition_path(challenge_dir), data)
    state_docs.render_docs(challenge_dir)


def sniff_file(path: Path) -> str:
    try:
        out = subprocess.check_output(["file", str(path)], text=True, stderr=subprocess.DEVNULL)
        return out.strip()
    except Exception:
        return ""


def checksec(path: Path) -> list[str]:
    try:
        out = subprocess.check_output(["checksec", "--file", str(path)], text=True, stderr=subprocess.STDOUT)
        return [line.rstrip() for line in out.splitlines() if line.strip()]
    except Exception:
        return []


def is_probably_elf(path: Path) -> bool:
    try:
        return path.read_bytes()[:4] == b"\x7fELF"
    except OSError:
        return False


def challenge_artifact_paths(challenge_dir: Path) -> list[Path]:
    ignored_dirs = {"__pycache__"}
    paths: list[Path] = []
    for path in challenge_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(challenge_dir)
        if rel.parts and rel.parts[0] in ignored_dirs:
            continue
        if path.name in {
            "amds_state/COGNITION.md",
            "amds_state/cognition.json",
            "description.md",
            "amds_state/run.env",
        }:
            continue
        paths.append(path)
    return sorted(paths, key=lambda p: str(p.relative_to(challenge_dir)))


def choose_main_binary(challenge_dir: Path) -> Path | None:
    candidates = []
    for path in challenge_artifact_paths(challenge_dir):
        if is_probably_elf(path) and not re.search(r"(^|/)(libc|ld-)", str(path.relative_to(challenge_dir)), re.I):
            candidates.append(path)
    return candidates[0] if candidates else None


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def run_config_path(challenge_dir: Path) -> Path:
    for candidate in (
        challenge_dir / "amds_state" / "run.env",
        challenge_dir / "amds_state" / ".pwnrun",
        challenge_dir / ".pwnrun",
    ):
        if candidate.exists():
            return candidate
    return challenge_dir / "amds_state" / "run.env"


def update_run_config(challenge_dir: Path, main_binary: Path | None) -> None:
    if not main_binary:
        return
    run_config = run_config_path(challenge_dir)
    if not run_config.exists():
        return
    main_rel = str(main_binary.relative_to(challenge_dir))
    lines = run_config.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("BIN="):
            new_lines.append(f"BIN={sh_quote(main_rel)}")
        else:
            new_lines.append(line)
    run_config.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def maybe_extract(path: Path, challenge_dir: Path, overwrite: bool) -> list[Path]:
    extracted: list[Path] = []
    if not zipfile.is_zipfile(path):
        return extracted
    with zipfile.ZipFile(path) as zf:
        for member in zf.infolist():
            target = challenge_dir / member.filename
            resolved = target.resolve()
            if not str(resolved).startswith(str(challenge_dir.resolve())):
                raise FetchError(f"refusing zip path traversal entry: {member.filename}")
            if target.exists() and not overwrite:
                continue
            zf.extract(member, challenge_dir)
            if target.exists() and target.is_file():
                extracted.append(target)
    return extracted


def attachment_filename(headers: dict[str, str], fallback_url: str, fallback_name: str) -> str:
    cd = headers.get("content-disposition", "")
    match = re.search(r"filename\*=UTF-8''([^;]+)", cd, re.I)
    if match:
        return safe_title(urllib.parse.unquote(match.group(1)))
    match = re.search(r"filename=\"?([^\";]+)\"?", cd, re.I)
    if match:
        return safe_title(urllib.parse.unquote(match.group(1)))
    path_name = Path(urllib.parse.unquote(urllib.parse.urlparse(fallback_url).path)).name
    return safe_title(path_name or fallback_name)


def file_entries(problem: dict[str, Any]) -> list[tuple[str, str]]:
    raw = problem.get("files") or problem.get("attachments") or problem.get("downloads") or []
    if isinstance(raw, str):
        raw = [raw]
    entries: list[tuple[str, str]] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                entries.append(("", item))
            elif isinstance(item, dict):
                url = item.get("url") or item.get("href") or item.get("download_url") or item.get("location")
                name = item.get("name") or item.get("filename") or item.get("title") or ""
                if url:
                    entries.append((str(name), str(url)))
    return entries


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for index in range(1, 1000):
        candidate = parent / f"{stem}.{index}{suffix}"
        if not candidate.exists():
            return candidate
    return parent / f"{path.name}.download"


def download_files(problem: dict[str, Any], cookie: str, challenge_dir: Path, overwrite: bool) -> list[Path]:
    local_files: list[Path] = []
    for name_hint, raw_url in file_entries(problem):
        url = urllib.parse.urljoin(BASE_URL, raw_url)
        body, headers, final_url = request_bytes(
            url,
            cookie=cookie,
            headers={"Referer": f"{BASE_URL}/challenges", "Accept": "*/*"},
        )
        if not body:
            raise FetchError(f"attachment download returned empty body: {url}")
        filename = attachment_filename(headers, final_url, name_hint or "attachment")
        out_path = challenge_dir / filename
        if out_path.exists() and not overwrite:
            out_path = unique_path(out_path)
        out_path.write_bytes(body)
        local_files.append(out_path)
    return local_files


def rel_name(challenge_dir: Path, path: Path) -> str:
    return str(path.relative_to(challenge_dir))


def description_markdown(
    challenge_id: str,
    problem: dict[str, Any],
    source_url: str,
    files: list[Path],
    challenge_dir: Path,
    attachment_error: str = "",
) -> str:
    title = str(problem.get("name") or problem.get("title") or f"BUUCTF {challenge_id or 'unknown'}")
    tags = tag_names(problem)
    downloaded = time.strftime("%Y-%m-%d %H:%M:%S %z")
    lines = [
        f"# {title}",
        "",
        f"- Source: {source_url}",
        f"- BUUCTF challenge id: {challenge_id}",
        f"- Category: {category_name(problem)}",
        f"- Tags: {', '.join(tags)}" if tags else "- Tags:",
        f"- Points: {problem.get('value', problem.get('points', ''))}",
        f"- Type: {problem.get('type', '')}",
        f"- State: {problem.get('state', '')}",
        f"- Connection info: {problem.get('connection_info', '')}",
        f"- Downloaded at: {downloaded}",
        "",
        "## Description",
        "",
        description_text(problem) or "(empty)",
        "",
        "## Local Files",
        "",
    ]
    if files:
        for path in files:
            lines.append(f"- `{rel_name(challenge_dir, path)}`")
    else:
        lines.append("- none")
    if attachment_error:
        lines.extend(["", "## Attachment Error", "", attachment_error])
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Only BUUCTF challenge metadata and attachment endpoints were used.",
            "- Writeups, public solutions, exploit repositories, and solution pages were not accessed.",
        ]
    )
    return "\n".join(lines) + "\n"


def challenge_metadata(
    challenge_id: str,
    problem: dict[str, Any],
    source_url: str,
    files: list[Path],
    challenge_dir: Path,
    fetch_status: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "title": str(problem.get("name") or problem.get("title") or f"BUUCTF {challenge_id or 'unknown'}"),
        "source": source_url,
        "platform": "BUUCTF",
        "problem_id": challenge_id,
        "challenge_type": normalize_challenge_type(category_name(problem)),
        "tags": tag_names(problem),
        "points": problem.get("value", problem.get("points")),
        "level": "",
        "docker": problem.get("connection_info"),
        "annex": file_entries(problem),
        "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "description": description_text(problem),
        "evidence_dir": "amds_state/evidence",
        "local_files": [rel_name(challenge_dir, path) for path in files],
        "tracked_files": [
            "amds_state/evidence/",
            "description.md",
            "exp.py",
            "exp_template.py",
            "wp.md",
            "amds_state/cognition.json",
            "amds_state/COGNITION.md",
            "amds_state/run.env",
        ],
        "fetch_status": fetch_status,
    }


def facts_markdown(
    challenge_id: str,
    problem: dict[str, Any],
    files: list[Path],
    challenge_dir: Path,
    main_binary: Path | None,
    checksec_lines: list[str],
    attachment_error: str = "",
) -> str:
    title = str(problem.get("name") or problem.get("title") or f"BUUCTF {challenge_id or 'unknown'}")
    tags = tag_names(problem)
    lines = [
        "# Confirmed Facts",
        "",
        "Only record facts verified from the binary, runtime, debugger, or exploit output.",
        "",
        "## Environment",
        "",
        f"- source: {BASE_URL}/challenges",
        f"- title: {title}",
        f"- category: {category_name(problem)}",
        f"- tags: {', '.join(tags)}" if tags else "- tags:",
        f"- connection_info: {problem.get('connection_info', '')}",
        f"- binary: {rel_name(challenge_dir, main_binary) if main_binary else ''}",
        "- libc:",
        "- ld:",
        "- remote:",
        "",
        "## Files",
        "",
    ]
    if files:
        for path in files:
            lines.append(f"- {rel_name(challenge_dir, path)}: sha256 {sha256_file(path)}; {sniff_file(path)}")
    else:
        lines.append("- none")
    if attachment_error:
        lines.extend(["", "## Fetch Issues", "", f"- attachment: {attachment_error}"])
    lines.extend(["", "## Protections", ""])
    if checksec_lines:
        lines.extend(f"- {line}" for line in checksec_lines)
    else:
        lines.append("- none yet")
    lines.extend(
        [
            "",
            "## Bug / Primitive",
            "",
            "- none yet",
            "",
            "## Leaks / Offsets",
            "",
            "- none yet",
            "",
            "## Gadgets / Symbols",
            "",
            "- none yet",
            "",
            "## Constraints",
            "",
            "- fetch-only; no writeups or public solutions were accessed",
        ]
    )
    return "\n".join(lines) + "\n"


def state_markdown(problem: dict[str, Any], main_binary: Path | None, attachment_error: str = "") -> str:
    tags = ", ".join(tag_names(problem))
    open_question = "- exact remote environment" if main_binary else "- no main binary identified yet"
    if attachment_error:
        open_question = f"- attachment download issue: {attachment_error}"
    return "\n".join(
        [
            "# Current Stage",
            "",
            "fetched" if not attachment_error else "fetch-incomplete",
            "",
            "# Target Profile",
            "",
            f"- challenge type: {category_name(problem)}",
            "- protections: see amds_state/cognition.json.facts",
            f"- likely bug class: {tags}" if tags else "- likely bug class:",
            "",
            "# Current Primitive",
            "",
            "- none yet",
            "",
            "# Next Step",
            "",
            "- inspect local files and runtime behavior" if not attachment_error else "- fix fetch issue before solving",
            "- configure remote information if provided",
            "",
            "# Checkpoint Plan",
            "",
            "- last stable checkpoint: none yet",
            "- next likely checkpoint: env-profiled",
            "- after that: entrypoints-mapped",
            "",
            "# Rejected Branches",
            "",
            "- none yet",
            "",
            "# Avoid",
            "",
            "- do not use writeups, public exploit repositories, or solution pages",
            "",
            "# Open Questions",
            "",
            open_question,
            "",
        ]
    )


def write_outputs(
    challenge_id: str,
    problem: dict[str, Any],
    source_url: str,
    challenge_dir: Path,
    files: list[Path],
    main_binary: Path | None,
    attachment_error: str,
    overwrite: bool,
    fetch_status: str,
) -> None:
    checksec_lines = checksec(main_binary) if main_binary else []
    write_text_if_allowed(
        challenge_dir / "description.md",
        description_markdown(challenge_id, problem, source_url, files, challenge_dir, attachment_error),
        overwrite,
    )
    update_cognition(
        challenge_dir,
        challenge_metadata(challenge_id, problem, source_url, files, challenge_dir, fetch_status),
        facts_markdown(challenge_id, problem, files, challenge_dir, main_binary, checksec_lines, attachment_error),
        state_markdown(problem, main_binary, attachment_error),
        overwrite,
    )


def write_partial_failure(title_hint: str, source_url: str, error: str, overwrite: bool, group: str) -> Path:
    title = safe_title(title_hint or "buuctf_fetch_failed")
    challenge_dir = CHALLENGES_DIR / safe_group_path(group) / title
    fresh_cognition = not state_docs.cognition_path(challenge_dir).exists()
    challenge_dir.mkdir(parents=True, exist_ok=True)
    run_init(challenge_dir)
    problem = {
        "name": title,
        "category": "",
        "description": "",
        "connection_info": "",
        "tags": [],
    }
    write_outputs("", problem, source_url, challenge_dir, [], None, error, overwrite or fresh_cognition, "failed")
    return challenge_dir


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Fetch BUUCTF challenge into Amadeus/challenges")
    parser.add_argument("url_or_id_or_title", help="BUUCTF challenge URL, numeric id, or title")
    parser.add_argument("--overwrite", action="store_true", help="overwrite generated markdown/config files")
    parser.add_argument("--no-extract", action="store_true", help="do not auto-extract zip attachments")
    parser.add_argument("--group", default="", help="optional challenges subdirectory, e.g. defcon or defcon/quals")
    parser.add_argument("--print-dir", action="store_true", help="print only the resulting challenge directory at the end")
    args = parser.parse_args()

    challenge_id, title_hint, source_url = parse_target(args.url_or_id_or_title)
    cookie = os.environ.get("BUUCTF_COOKIE") or os.environ.get("BUUOJ_COOKIE") or ""

    try:
        list_item: dict[str, Any] | None = None
        if not challenge_id:
            items = fetch_challenge_list(cookie)
            list_item = find_challenge_by_title(items, title_hint)
            challenge_id = item_id(list_item)
            if not challenge_id:
                raise FetchError(f"matched BUUCTF challenge has no id: {list_item!r}")

        try:
            problem = fetch_challenge_detail(challenge_id, cookie)
        except FetchError:
            if list_item:
                problem = dict(list_item)
            else:
                raise
    except FetchError as exc:
        challenge_dir = write_partial_failure(title_hint, source_url, str(exc), args.overwrite, args.group)
        print(f"challenge_dir={challenge_dir}")
        print(f"fetch_status=failed")
        print(f"fetch_error={exc}")
        return 2

    title = safe_title(str(problem.get("name") or problem.get("title") or title_hint or f"buuctf_{challenge_id}"))
    challenge_dir = CHALLENGES_DIR / safe_group_path(args.group) / title
    fresh_cognition = not state_docs.cognition_path(challenge_dir).exists()
    challenge_dir.mkdir(parents=True, exist_ok=True)
    run_init(challenge_dir)

    local_files: list[Path] = []
    attachment_error = ""
    try:
        local_files.extend(download_files(problem, cookie, challenge_dir, args.overwrite))
        if not args.no_extract:
            extracted: list[Path] = []
            for path in local_files:
                extracted.extend(maybe_extract(path, challenge_dir, args.overwrite))
            local_files.extend(extracted)
    except FetchError as exc:
        attachment_error = str(exc)

    if local_files:
        seen = set()
        local_files = [p for p in local_files if not (p in seen or seen.add(p))]

    main_binary = choose_main_binary(challenge_dir)
    if main_binary:
        main_binary.chmod(main_binary.stat().st_mode | 0o111)
    update_run_config(challenge_dir, main_binary)

    fetch_status = "fetched" if not attachment_error else "partial"
    write_outputs(challenge_id, problem, source_url, challenge_dir, local_files, main_binary, attachment_error, args.overwrite or fresh_cognition, fetch_status)

    if args.print_dir:
        print(challenge_dir)
        return 0 if not attachment_error else 2

    print(f"challenge_dir={challenge_dir}")
    print(f"title={title}")
    print(f"challenge_id={challenge_id}")
    print(f"fetch_status={fetch_status}")
    for path in local_files:
        print(f"file={rel_name(challenge_dir, path)} sha256={sha256_file(path)}")
    if main_binary:
        print(f"main_binary={rel_name(challenge_dir, main_binary)}")
    if attachment_error:
        print(f"attachment_error={attachment_error}")
    return 0 if not attachment_error else 2


if __name__ == "__main__":
    raise SystemExit(main())
