#!/usr/bin/env python3
"""Fetch NSSCTF challenge metadata and attachments into Amadeus/challenges.

This tool intentionally avoids writeup/solution APIs. It only requests:
- /api/problem/v2/<id>/
- /api/problem/<id>/annex/download/
- the returned attachment URL, if any

Cookie, when needed, is read from NSSCTF_COOKIE and is never written to disk.
ROOT/.env is loaded when present; existing shell environment variables win.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
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

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
}

CATEGORY_NAMES = {
    0: "PWN",
    1: "Web",
    2: "Reverse",
    3: "Crypto",
    4: "Misc",
    5: "Mobile",
}


class FetchError(RuntimeError):
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


def parse_problem_id(value: str) -> str:
    if value.isdigit():
        return value
    parsed = urllib.parse.urlparse(value)
    match = re.search(r"/problem/(\d+)", parsed.path)
    if not match:
        raise FetchError(f"cannot parse NSSCTF problem id from: {value}")
    return match.group(1)


def request_bytes(url: str, cookie: str = "", headers: dict[str, str] | None = None) -> tuple[bytes, dict[str, str], str]:
    req_headers = dict(DEFAULT_HEADERS)
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
            return body, resp_headers, final_url
    except urllib.error.HTTPError as exc:
        body = exc.read()
        raise FetchError(f"HTTP {exc.code} for {url}: {body[:200]!r}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"request failed for {url}: {exc}") from exc


def request_json(url: str, cookie: str = "", headers: dict[str, str] | None = None) -> Any:
    body, _, _ = request_bytes(url, cookie=cookie, headers=headers)
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise FetchError(f"non-JSON response from {url}: {body[:200]!r}") from exc


def safe_title(title: str) -> str:
    title = title.strip()
    title = title.replace("/", "_").replace("\x00", "")
    title = re.sub(r"\s+", " ", title)
    return title or "nssctf_unknown"


def safe_group_path(group: str) -> Path:
    parts = [safe_title(part) for part in re.split(r"[\\/]+", group.strip()) if part.strip()]
    if any(part in {".", ".."} for part in parts):
        raise FetchError("group must not contain '.' or '..' path segments")
    return Path(*parts) if parts else Path()


def tag_names(problem: dict[str, Any]) -> list[str]:
    tags = problem.get("tag") or problem.get("tags") or []
    names: list[str] = []
    for item in tags:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, (list, tuple)) and item:
            names.append(str(item[0]))
        elif isinstance(item, dict):
            name = item.get("name") or item.get("title")
            if name:
                names.append(str(name))
    return names


def category_name(problem: dict[str, Any]) -> str:
    category = problem.get("category")
    if isinstance(category, int):
        return CATEGORY_NAMES.get(category, str(category))
    if category is None:
        return ""
    return str(category)


def normalize_challenge_type(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized or normalized.startswith("-"):
        return ""
    aliases = {
        "pwn": "pwn",
        "web": "web",
        "reverse": "reverse",
        "re": "reverse",
        "rev": "reverse",
        "crypto": "crypto",
        "misc": "misc",
        "mobile": "mobile",
        "forensics": "forensics",
        "forensic": "forensics",
        "osint": "osint",
        "malware": "malware",
    }
    return aliases.get(normalized, "")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_text_if_allowed(path: Path, content: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        return
    path.write_text(content, encoding="utf-8")


def run_init(challenge_dir: Path) -> None:
    subprocess.run([str(INIT_SCRIPT), str(challenge_dir)], cwd=ROOT, check=True)


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


def choose_main_binary(challenge_dir: Path) -> Path | None:
    candidates = []
    for path in challenge_dir.iterdir():
        if not path.is_file() or path.name.startswith("."):
            continue
        if is_probably_elf(path) and not re.search(r"(libc|ld-)", path.name, re.I):
            candidates.append(path)
    return sorted(candidates, key=lambda p: p.name)[0] if candidates else None


def update_pwnrun(challenge_dir: Path, main_binary: Path | None) -> None:
    if not main_binary:
        return
    pwnrun = challenge_dir / ".pwnrun"
    if not pwnrun.exists():
        return
    lines = pwnrun.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("BIN="):
            new_lines.append(f"BIN={sh_quote(main_binary.name)}")
        else:
            new_lines.append(line)
    pwnrun.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def maybe_extract(path: Path, challenge_dir: Path, overwrite: bool) -> list[Path]:
    extracted: list[Path] = []
    if zipfile.is_zipfile(path):
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


def attachment_filename(headers: dict[str, str], fallback: str) -> str:
    cd = headers.get("content-disposition", "")
    match = re.search(r"filename\*=UTF-8''([^;]+)", cd, re.I)
    if match:
        return safe_title(urllib.parse.unquote(match.group(1)))
    match = re.search(r"filename=\"?([^\";]+)\"?", cd, re.I)
    if match:
        return safe_title(urllib.parse.unquote(match.group(1)))
    return fallback


def fetch_attachment(problem_id: str, title: str, cookie: str, challenge_dir: Path, overwrite: bool) -> Path | None:
    annex_api = f"https://www.nssctf.cn/api/problem/{problem_id}/annex/download/"
    referer = f"https://www.nssctf.cn/problem/{problem_id}"
    data = request_json(annex_api, cookie=cookie, headers={"Referer": referer})
    if not isinstance(data, dict) or data.get("code") != 200:
        raise FetchError(f"annex API did not return code 200: {data!r}")

    attachment_url = data.get("data")
    if not isinstance(attachment_url, str) or not attachment_url:
        return None

    body, headers, _ = request_bytes(
        attachment_url,
        headers={
            "Referer": referer,
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
        },
    )
    if not body:
        raise FetchError("attachment download returned empty body")

    name = attachment_filename(headers, safe_title(title))
    out_path = challenge_dir / name
    if out_path.exists() and not overwrite:
        stem = out_path.name
        out_path = challenge_dir / f"{stem}.download"
    out_path.write_bytes(body)
    return out_path


def description_markdown(problem_id: str, problem: dict[str, Any], source_url: str, files: list[Path], attachment_error: str = "") -> str:
    title = str(problem.get("title") or f"NSSCTF {problem_id}")
    desc = str(problem.get("desc") or problem.get("description") or "").strip()
    tags = tag_names(problem)
    category = category_name(problem)
    downloaded = time.strftime("%Y-%m-%d %H:%M:%S %z")

    lines = [
        f"# {title}",
        "",
        f"- Source: {source_url}",
        f"- NSSCTF problem id: {problem_id}",
        f"- Category: {category}" if category else "- Category:",
        f"- Tags: {', '.join(tags)}" if tags else "- Tags:",
        f"- Points: {problem.get('point', '')}",
        f"- Level: {problem.get('level', '')}",
        f"- Docker: {problem.get('docker', '')}",
        f"- Annex: {problem.get('annex', '')}",
        f"- Downloaded at: {downloaded}",
        "",
        "## Description",
        "",
        desc or "(empty)",
        "",
        "## Local Files",
        "",
    ]
    if files:
        for path in files:
            lines.append(f"- `{path.name}`")
    else:
        lines.append("- none")
    if attachment_error:
        lines.extend(["", "## Attachment Error", "", attachment_error])
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Only NSSCTF problem detail and annex download APIs were used.",
            "- Writeup APIs, public writeups, exploit repositories, and solution pages were not accessed.",
        ]
    )
    return "\n".join(lines) + "\n"


def challenge_metadata(problem_id: str, problem: dict[str, Any], source_url: str, files: list[Path]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "title": str(problem.get("title") or f"NSSCTF {problem_id}"),
        "source": source_url,
        "platform": "NSSCTF",
        "problem_id": problem_id,
        "challenge_type": normalize_challenge_type(category_name(problem)),
        "tags": tag_names(problem),
        "points": problem.get("point"),
        "level": problem.get("level", ""),
        "docker": problem.get("docker"),
        "annex": problem.get("annex"),
        "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "description": str(problem.get("desc") or problem.get("description") or "").strip(),
        "local_files": [path.name for path in files],
    }


def facts_markdown(
    problem_id: str,
    problem: dict[str, Any],
    files: list[Path],
    main_binary: Path | None,
    checksec_lines: list[str],
    attachment_error: str = "",
) -> str:
    title = str(problem.get("title") or f"NSSCTF {problem_id}")
    tags = tag_names(problem)
    lines = [
        "# Confirmed Facts",
        "",
        "Only record facts verified from the binary, runtime, debugger, or exploit output.",
        "",
        "## Environment",
        "",
        f"- source: https://www.nssctf.cn/problem/{problem_id}",
        f"- title: {title}",
        f"- category: {category_name(problem)}",
        f"- tags: {', '.join(tags)}" if tags else "- tags:",
        f"- description environment: {str(problem.get('desc') or '').splitlines()[0] if problem.get('desc') else ''}",
        f"- binary: {main_binary.name if main_binary else ''}",
        "- libc:",
        "- ld:",
        "- remote:",
        "",
        "## Files",
        "",
    ]
    if files:
        for path in files:
            lines.append(f"- {path.name}: sha256 {sha256_file(path)}; {sniff_file(path)}")
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
    return "\n".join(
        [
            "# Current Stage",
            "",
            "fetched",
            "",
            "# Target Profile",
            "",
            f"- challenge type: {category_name(problem)}",
            "- protections: see FACTS.md",
            f"- likely bug class: {tags}" if tags else "- likely bug class:",
            "",
            "# Current Primitive",
            "",
            "- none yet",
            "",
            "# Next Step",
            "",
            "- inspect local files and runtime behavior",
            "- configure remote information if provided",
            "",
            "# Checkpoint Plan",
            "",
            "- last stable checkpoint: none yet",
            "- next likely checkpoint: env-ok",
            "- after that: primitive-confirmed",
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
            "- exact remote environment" if main_binary else "- no main binary identified yet",
            f"- attachment download issue: {attachment_error}" if attachment_error else "",
            "",
        ]
    )


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Fetch NSSCTF challenge into Amadeus/challenges")
    parser.add_argument("url_or_id", help="NSSCTF problem URL or numeric id")
    parser.add_argument("--overwrite", action="store_true", help="overwrite generated markdown/config files")
    parser.add_argument("--no-extract", action="store_true", help="do not auto-extract zip attachments")
    parser.add_argument("--group", default="", help="optional challenges subdirectory, e.g. defcon or defcon/quals")
    parser.add_argument("--print-dir", action="store_true", help="print only the resulting challenge directory at the end")
    args = parser.parse_args()

    problem_id = parse_problem_id(args.url_or_id)
    source_url = f"https://www.nssctf.cn/problem/{problem_id}"
    cookie = os.environ.get("NSSCTF_COOKIE", "")

    detail_api = f"https://www.nssctf.cn/api/problem/v2/{problem_id}/"
    detail = request_json(detail_api, cookie=cookie, headers={"Referer": source_url})
    if not isinstance(detail, dict) or detail.get("code") != 200:
        raise FetchError(f"detail API did not return code 200: {detail!r}")
    problem = detail.get("data")
    if not isinstance(problem, dict):
        raise FetchError(f"detail API missing data object: {detail!r}")

    title = safe_title(str(problem.get("title") or f"nssctf_{problem_id}"))
    challenge_dir = CHALLENGES_DIR / safe_group_path(args.group) / title
    challenge_dir.mkdir(parents=True, exist_ok=True)
    run_init(challenge_dir)

    local_files: list[Path] = []
    attachment_error = ""
    if problem.get("annex"):
        try:
            attachment = fetch_attachment(problem_id, title, cookie, challenge_dir, args.overwrite)
            if attachment:
                local_files.append(attachment)
                if not args.no_extract:
                    local_files.extend(maybe_extract(attachment, challenge_dir, args.overwrite))
        except FetchError as exc:
            attachment_error = str(exc)

    main_binary = choose_main_binary(challenge_dir)
    if main_binary:
        main_binary.chmod(main_binary.stat().st_mode | 0o111)
    update_pwnrun(challenge_dir, main_binary)

    if local_files:
        seen = set()
        local_files = [p for p in local_files if not (p in seen or seen.add(p))]

    checksec_lines = checksec(main_binary) if main_binary else []
    write_text_if_allowed(
        challenge_dir / "description.md",
        description_markdown(problem_id, problem, source_url, local_files, attachment_error),
        args.overwrite,
    )
    write_text_if_allowed(
        challenge_dir / "metadata.json",
        json.dumps(challenge_metadata(problem_id, problem, source_url, local_files), indent=2, ensure_ascii=False) + "\n",
        args.overwrite,
    )
    write_text_if_allowed(
        challenge_dir / "FACTS.md",
        facts_markdown(problem_id, problem, local_files, main_binary, checksec_lines, attachment_error),
        args.overwrite,
    )
    write_text_if_allowed(challenge_dir / "STATE.md", state_markdown(problem, main_binary, attachment_error), args.overwrite)

    ctf_files = challenge_dir / ".ctf-files"
    if ctf_files.exists():
        text = ctf_files.read_text(encoding="utf-8")
        additions = [name for name in ("description.md", "metadata.json") if name not in text]
        if additions:
            ctf_files.write_text(text.rstrip() + "\n" + "\n".join(additions) + "\n", encoding="utf-8")

    if args.print_dir:
        print(challenge_dir)
        return 0

    print(f"challenge_dir={challenge_dir}")
    print(f"title={title}")
    for path in local_files:
        print(f"file={path.name} sha256={sha256_file(path)}")
    if main_binary:
        print(f"main_binary={main_binary.name}")
    if attachment_error:
        print(f"attachment_error={attachment_error}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FetchError as exc:
        print(f"fetch_nssctf.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
