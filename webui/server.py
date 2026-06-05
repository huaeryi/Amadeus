#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "webui" / "static"
IMGS_DIR = ROOT_DIR / "webui" / "imgs"
CHALLENGES_DIR = ROOT_DIR / "challenges"
CHALLENGE_SCRIPTS_DIR = ROOT_DIR / "scripts" / "challenge"
STATE_SCRIPTS_DIR = ROOT_DIR / "scripts" / "state"
PWN_SCRIPTS_DIR = ROOT_DIR / "scripts" / "pwn"
STATE_DIR_NAME = "amds_state"
CORE_DOCUMENTS = ("cognition.json", "COGNITION.md", "run.env")
GENERATED_DOCUMENTS = {"COGNITION.md"}
CHALLENGE_NAME_RE = re.compile(r"^[^\\\x00]+$")
TEXT_PREVIEW_LIMIT = 256 * 1024
BINARY_PREVIEW_LIMIT = 4096
CHECKPOINT_SUBJECT_RE = re.compile(r"^\[ckpt(?P<number>\d+)\s+(?P<name>.+)\]$")


@dataclass
class ApiError(Exception):
    status: int
    message: str
    details: dict[str, Any] | None = None


def isoformat_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")


def challenge_path(name: str) -> Path:
    if not name or not CHALLENGE_NAME_RE.fullmatch(name):
        raise ApiError(400, "Invalid challenge name. Do not use backslashes or NUL bytes.")
    requested_path = Path(name)
    if requested_path.is_absolute() or any(part in {"", ".", ".."} for part in requested_path.parts):
        raise ApiError(400, "Invalid challenge path. Do not use absolute paths, empty segments, '.', or '..'.")

    path = (CHALLENGES_DIR / requested_path).resolve()
    try:
        path.relative_to(CHALLENGES_DIR.resolve())
    except ValueError as exc:
        raise ApiError(400, "Challenge path escapes the challenges directory.") from exc
    return path


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def state_dir(path: Path) -> Path:
    return path / STATE_DIR_NAME


def document_candidates(path: Path, document_name: str) -> list[Path]:
    if document_name == "cognition.json":
        return [state_dir(path) / "cognition.json", path / "cognition.json"]
    if document_name == "COGNITION.md":
        return [state_dir(path) / "COGNITION.md", path / "COGNITION.md"]
    if document_name in {"run.env", ".pwnrun"}:
        return [state_dir(path) / "run.env", state_dir(path) / ".pwnrun", path / ".pwnrun"]
    return [path / document_name]


def resolve_document_path(path: Path, document_name: str, *, for_write: bool = False) -> Path:
    candidates = document_candidates(path, document_name)
    if for_write and document_name in {"run.env", ".pwnrun"}:
        return candidates[0]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def document_exists(path: Path, document_name: str) -> bool:
    return any(candidate.exists() for candidate in document_candidates(path, document_name))


def read_state_stage(path: Path) -> str:
    cognition_path = resolve_document_path(path, "cognition.json")
    if cognition_path.exists():
        try:
            data = json.loads(cognition_path.read_text(encoding="utf-8"))
            stage = data.get("state", {}).get("current_stage", "")
            if isinstance(stage, str) and stage.strip():
                return stage.strip()
        except json.JSONDecodeError:
            pass

    return "unknown"


def parse_markdown_field(text: str, field_name: str) -> str:
    pattern = re.compile(rf"^- {re.escape(field_name)}:\s*(.*)$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


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
        "x402": "x402",
    }
    return aliases.get(normalized, "")


def read_challenge_metadata(path: Path) -> dict[str, Any]:
    description_text = read_text_if_exists(path / "description.md")
    cognition: dict[str, Any] = {}
    cognition_path = resolve_document_path(path, "cognition.json")
    if cognition_path.exists():
        try:
            parsed = json.loads(cognition_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                cognition = parsed
        except json.JSONDecodeError:
            cognition = {}
    metadata = cognition.get("metadata", {}) if isinstance(cognition.get("metadata"), dict) else {}

    title = str(metadata.get("title") or "").strip()
    if not title:
        first_heading = re.search(r"^#\s+(.+)$", description_text, re.MULTILINE)
        title = first_heading.group(1).strip() if first_heading else path.name

    challenge_type = str(metadata.get("challenge_type") or metadata.get("category") or "").strip()
    if not challenge_type:
        challenge_type = parse_markdown_field(description_text, "Category")
    if not challenge_type:
        facts = cognition.get("facts", {}) if isinstance(cognition.get("facts"), dict) else {}
        for section in facts.get("sections", []) if isinstance(facts.get("sections"), list) else []:
            items = section.get("items", []) if isinstance(section, dict) else []
            for item in items:
                text = str(item)
                if text.lower().startswith("category:"):
                    challenge_type = text.split(":", 1)[1].strip()
                    break
            if challenge_type:
                break
    if not challenge_type:
        state = cognition.get("state", {}) if isinstance(cognition.get("state"), dict) else {}
        profile = state.get("target_profile", {}) if isinstance(state.get("target_profile"), dict) else {}
        challenge_type = str(profile.get("challenge_type") or "").strip()
    challenge_type = normalize_challenge_type(challenge_type)

    tags = metadata.get("tags", [])
    if not isinstance(tags, list):
        tags = [str(tags)]
    if not tags:
        raw_tags = parse_markdown_field(description_text, "Tags")
        tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]

    return {
        **metadata,
        "title": title,
        "challenge_type": challenge_type,
        "tags": tags,
    }


def derive_solve_status(stage: str) -> str:
    normalized = stage.strip().lower()
    if normalized in {"solved", "completed"}:
        return "solved"
    return "unsolved"


def run_script(script_name: str, *args: str) -> dict[str, Any]:
    command = ["bash", str(CHALLENGE_SCRIPTS_DIR / script_name), *args]
    result = subprocess.run(
        command,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    payload = {
        "command": command,
        "code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if result.returncode != 0:
        raise ApiError(400, f"{script_name} failed", payload)
    return payload


def render_state_docs(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["python3", str(STATE_SCRIPTS_DIR / "state_docs.py"), "render", str(path)],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    payload = {
        "command": ["python3", str(STATE_SCRIPTS_DIR / "state_docs.py"), "render", str(path)],
        "code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if result.returncode != 0:
        raise ApiError(400, "cognition render failed", payload)
    return payload


def run_git(path: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise ApiError(
            400,
            "git command failed",
            {
                "command": ["git", "-C", str(path), *args],
                "code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
    return result


def resolve_path_in_challenge(challenge_name: str, relative_path: str) -> tuple[Path, Path]:
    challenge_dir = challenge_path(challenge_name)
    if not challenge_dir.exists():
        raise ApiError(404, f"Challenge not found: {challenge_name}")
    if not relative_path or relative_path == ".":
        return challenge_dir, challenge_dir

    requested_path = Path(relative_path)
    if requested_path.is_absolute():
        raise ApiError(400, "Absolute paths are not allowed.")

    resolved_path = (challenge_dir / requested_path).resolve()
    try:
        resolved_path.relative_to(challenge_dir.resolve())
    except ValueError as exc:
        raise ApiError(400, "File path escapes the challenge directory.") from exc

    return challenge_dir, resolved_path


def hexdump_preview(data: bytes) -> str:
    lines: list[str] = []
    for offset in range(0, len(data), 16):
        chunk = data[offset : offset + 16]
        hex_part = " ".join(f"{byte:02x}" for byte in chunk)
        ascii_part = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
        lines.append(f"{offset:08x}  {hex_part:<47}  {ascii_part}")
    return "\n".join(lines)


def build_directory_entries(challenge_dir: Path, resolved_dir: Path) -> list[dict[str, Any]]:
    relative_dir = str(resolved_dir.relative_to(challenge_dir))
    entries: list[dict[str, Any]] = []

    for entry in sorted(
        resolved_dir.iterdir(),
        key=lambda item: (not item.is_dir(), item.name.lower()),
    ):
        try:
            stat = entry.stat()
        except OSError:
            continue
        entry_relative = str(entry.relative_to(challenge_dir))
        entries.append(
            {
                "name": entry.name,
                "path": entry_relative,
                "type": "directory" if entry.is_dir() else "file",
                "size": stat.st_size,
                "modified_at": isoformat_from_timestamp(stat.st_mtime),
                "is_executable": entry.is_file() and os.access(entry, os.X_OK),
                "previewable": entry.is_file(),
            }
        )

    return entries


def preview_file(challenge_name: str, relative_path: str) -> dict[str, Any]:
    challenge_dir, resolved_path = resolve_path_in_challenge(challenge_name, relative_path)
    if not resolved_path.exists():
        raise ApiError(404, f"File not found: {relative_path}")

    relative_name = str(resolved_path.relative_to(challenge_dir))
    stat = resolved_path.stat()

    if resolved_path.is_dir():
        parent_path: str | None = None
        if resolved_path != challenge_dir:
            parent_path = str(resolved_path.parent.relative_to(challenge_dir))
        return {
            "path": relative_name or ".",
            "name": resolved_path.name,
            "type": "directory",
            "size": stat.st_size,
            "modified_at": isoformat_from_timestamp(stat.st_mtime),
            "is_root": resolved_path == challenge_dir,
            "parent_path": parent_path or ".",
            "entries": build_directory_entries(challenge_dir, resolved_path),
        }

    with resolved_path.open("rb") as file_handle:
        raw = file_handle.read(TEXT_PREVIEW_LIMIT + 1)

    is_binary = b"\x00" in raw
    if not is_binary:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            is_binary = True

    if is_binary:
        preview_bytes = raw[:BINARY_PREVIEW_LIMIT]
        content = hexdump_preview(preview_bytes)
        truncated = stat.st_size > BINARY_PREVIEW_LIMIT
        preview_kind = "binary"
        limit = BINARY_PREVIEW_LIMIT
    else:
        preview_bytes = raw[:TEXT_PREVIEW_LIMIT]
        content = preview_bytes.decode("utf-8", errors="replace")
        truncated = stat.st_size > TEXT_PREVIEW_LIMIT
        preview_kind = "text"
        limit = TEXT_PREVIEW_LIMIT

    return {
        "path": relative_name,
        "name": resolved_path.name,
        "type": "file",
        "preview_kind": preview_kind,
        "size": stat.st_size,
        "modified_at": isoformat_from_timestamp(stat.st_mtime),
        "truncated": truncated,
        "preview_limit": limit,
        "content": content,
    }


def collect_artifacts(path: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for entry in sorted(path.iterdir(), key=lambda item: item.name.lower()):
        try:
            stat = entry.stat()
        except OSError:
            continue
        artifacts.append(
            {
                "name": entry.name,
                "path": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size": stat.st_size,
                "modified_at": isoformat_from_timestamp(stat.st_mtime),
                "is_executable": entry.is_file() and os.access(entry, os.X_OK),
                "previewable": entry.is_file(),
            }
        )
    return artifacts


def collect_checkpoints(path: Path) -> list[dict[str, Any]]:
    checkpoints: list[dict[str, Any]] = []
    if not (path / ".git").exists():
        return checkpoints

    head_result = run_git(path, "rev-parse", "--verify", "HEAD")
    if head_result.returncode != 0:
        return checkpoints
    head_hash = head_result.stdout.strip()

    log_result = run_git(path, "log", "--date=unix", "--format=%H%x1f%h%x1f%P%x1f%ct%x1f%s")
    if log_result.returncode != 0:
        return checkpoints

    for line in log_result.stdout.splitlines():
        parts = line.split("\x1f", 4)
        if len(parts) != 5:
            continue
        full_hash, short_hash, parent_hashes, created_timestamp, subject = parts
        match = CHECKPOINT_SUBJECT_RE.match(subject)
        if not match:
            continue
        checkpoints.append(
            {
                "id": full_hash,
                "short_id": short_hash,
                "name": match.group("name"),
                "number": int(match.group("number")),
                "subject": subject,
                "created_at": isoformat_from_timestamp(float(created_timestamp)),
                "target_dir": str(path.relative_to(ROOT_DIR)),
                "parent_id": parent_hashes.split()[0] if parent_hashes.strip() else None,
                "is_latest": False,
                "is_head": full_hash == head_hash,
            }
        )

    if checkpoints:
        checkpoints[0]["is_latest"] = True

    checkpoint_ids = {checkpoint["id"] for checkpoint in checkpoints}
    previous_id: str | None = None
    for checkpoint in reversed(checkpoints):
        if checkpoint["parent_id"] not in checkpoint_ids:
            checkpoint["parent_id"] = previous_id
        previous_id = checkpoint["id"]

    return checkpoints


def build_checkpoint_graph(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "nodes": [
            {
                "id": checkpoint["id"],
                "name": checkpoint["name"],
                "created_at": checkpoint["created_at"],
                "target_dir": checkpoint.get("target_dir", "."),
                "parent_id": checkpoint.get("parent_id"),
                "short_id": checkpoint.get("short_id"),
            }
            for checkpoint in checkpoints
        ],
        "edges": [
            {"parent": checkpoint["parent_id"], "child": checkpoint["id"]}
            for checkpoint in checkpoints
            if checkpoint.get("parent_id")
        ],
    }


def parse_run_info(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["bash", str(PWN_SCRIPTS_DIR / "run_pwn.sh"), str(path), "info"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )

    info: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        info[key.strip()] = value.strip()

    return {
        "ok": result.returncode == 0,
        "code": result.returncode,
        "info": info,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def challenge_summary(path: Path) -> dict[str, Any]:
    artifacts = collect_artifacts(path)
    checkpoints = collect_checkpoints(path)
    state_stage = read_state_stage(path)
    solve_status = derive_solve_status(state_stage)
    metadata = read_challenge_metadata(path)
    core_files = {name: document_exists(path, name) for name in CORE_DOCUMENTS}
    updated_at = isoformat_from_timestamp(path.stat().st_mtime)
    for artifact in artifacts:
        updated_at = max(updated_at, artifact["modified_at"])

    challenge_name = str(path.relative_to(CHALLENGES_DIR))
    group = str(path.parent.relative_to(CHALLENGES_DIR)) if path.parent != CHALLENGES_DIR else ""
    event = challenge_name.split("/", 1)[0]
    return {
        "name": challenge_name,
        "group": "" if group == "." else group,
        "event": event,
        "title": metadata.get("title") or path.name,
        "path": str(path.relative_to(ROOT_DIR)),
        "metadata": metadata,
        "challenge_type": metadata.get("challenge_type", ""),
        "tags": metadata.get("tags", []),
        "initialized": document_exists(path, "cognition.json") and document_exists(path, "COGNITION.md"),
        "state_stage": state_stage,
        "solve_status": solve_status,
        "core_files": core_files,
        "checkpoint_count": len(checkpoints),
        "artifact_count": len(artifacts),
        "updated_at": updated_at,
        "has_exp": (path / "exp.py").exists(),
        "has_writeup": (path / "wp.md").exists(),
    }


def challenge_detail(name: str) -> dict[str, Any]:
    path = challenge_path(name)
    if not path.exists():
        raise ApiError(404, f"Challenge not found: {name}")
    if not path.is_dir():
        raise ApiError(400, f"Challenge path is not a directory: {name}")

    documents = {document: read_text_if_exists(resolve_document_path(path, document)) for document in CORE_DOCUMENTS}
    checkpoints = collect_checkpoints(path)
    return {
        "summary": challenge_summary(path),
        "documents": documents,
        "checkpoints": checkpoints,
        "checkpoint_graph": build_checkpoint_graph(checkpoints),
        "artifacts": collect_artifacts(path),
    }


def list_challenges() -> list[dict[str, Any]]:
    if not CHALLENGES_DIR.exists():
        return []

    def is_challenge_dir(path: Path) -> bool:
        return path.is_dir() and not path.name.startswith(".") and any(document_exists(path, name) for name in CORE_DOCUMENTS)

    def is_supported_challenge_path(path: Path) -> bool:
        parts = path.relative_to(CHALLENGES_DIR).parts
        if any(part.startswith(".") for part in parts):
            return False
        if len(parts) == 2:
            return True
        if len(parts) == 3:
            return parts[1].lower() in {"reverse", "pwn", "web", "misc", "crypto"}
        return False

    challenges: list[dict[str, Any]] = []
    for entry in sorted(CHALLENGES_DIR.rglob("*"), key=lambda item: str(item.relative_to(CHALLENGES_DIR)).lower()):
        if not entry.is_dir() or not is_supported_challenge_path(entry):
            continue
        if is_challenge_dir(entry):
            challenges.append(challenge_summary(entry))
    return challenges


class AmadeusHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[webui] {self.address_string()} - {format % args}")

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_asset(self, root: Path, relative_path: str) -> None:
        requested_path = Path(unquote(relative_path))
        if requested_path.is_absolute() or any(part in {"", ".", ".."} for part in requested_path.parts):
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid asset path")
            return

        path = (root / requested_path).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid asset path")
            return
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Asset not found")
            return

        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ApiError(400, "Request body must be valid JSON.") from exc

    def handle_api(self, method: str) -> None:
        parsed = urlparse(self.path)
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        query = parse_qs(parsed.query)

        try:
            if parts == ["api", "challenges"]:
                if method == "GET":
                    self.send_json(200, {"challenges": list_challenges()})
                    return
                if method == "POST":
                    payload = self.read_json()
                    name = str(payload.get("name", "")).strip()
                    initialize = bool(payload.get("initialize", True))
                    if not name:
                        raise ApiError(400, "Challenge name is required.")
                    if len(Path(name).parts) != 2:
                        raise ApiError(400, "Challenge name must use <competition>/<challenge>, for example defcon/baby_heap.")
                    path = challenge_path(name)
                    if path.exists():
                        raise ApiError(409, f"Challenge already exists: {name}")
                    path.mkdir(parents=True, exist_ok=False)
                    result: dict[str, Any] | None = None
                    if initialize:
                        result = run_script("init_challenge.sh", str(path))
                    self.send_json(
                        201,
                        {
                            "message": f"Created challenge {name}",
                            "script_result": result,
                            "challenge": challenge_detail(name),
                        },
                    )
                    return

            if len(parts) >= 3 and parts[:2] == ["api", "challenges"]:
                name = parts[2]

                if len(parts) == 3 and method == "GET":
                    self.send_json(200, {"challenge": challenge_detail(name)})
                    return

                if len(parts) == 4 and parts[3] == "init" and method == "POST":
                    path = challenge_path(name)
                    if not path.exists():
                        raise ApiError(404, f"Challenge not found: {name}")
                    result = run_script("init_challenge.sh", str(path))
                    self.send_json(
                        200,
                        {
                            "message": f"Initialized challenge {name}",
                            "script_result": result,
                            "challenge": challenge_detail(name),
                        },
                    )
                    return

                if len(parts) == 4 and parts[3] == "run-info" and method == "GET":
                    path = challenge_path(name)
                    if not path.exists():
                        raise ApiError(404, f"Challenge not found: {name}")
                    self.send_json(200, {"run_info": parse_run_info(path)})
                    return

                if len(parts) == 4 and parts[3] == "file" and method == "GET":
                    requested_path = query.get("path", [""])[0]
                    self.send_json(200, {"file": preview_file(name, requested_path)})
                    return

                if len(parts) == 4 and parts[3] == "document":
                    document_name = query.get("name", [""])[0]
                    if document_name == ".pwnrun":
                        document_name = "run.env"
                    if document_name not in CORE_DOCUMENTS:
                        raise ApiError(400, "Unsupported document.")
                    path = challenge_path(name)
                    if not path.exists():
                        raise ApiError(404, f"Challenge not found: {name}")
                    document_path = resolve_document_path(path, document_name, for_write=method == "PUT")

                    if method == "GET":
                        self.send_json(
                            200,
                            {
                                "name": document_name,
                                "content": read_text_if_exists(document_path),
                            },
                        )
                        return

                    if method == "PUT":
                        if document_name in GENERATED_DOCUMENTS:
                            raise ApiError(400, f"{document_name} is generated from JSON; edit the corresponding JSON file instead.")
                        payload = self.read_json()
                        content = str(payload.get("content", ""))
                        old_content = read_text_if_exists(document_path)
                        document_path.write_text(content, encoding="utf-8")
                        render_result = None
                        if document_name == "cognition.json":
                            try:
                                render_result = render_state_docs(path)
                            except ApiError:
                                document_path.write_text(old_content, encoding="utf-8")
                                if old_content:
                                    render_state_docs(path)
                                raise
                        self.send_json(
                            200,
                            {
                                "message": f"Saved {document_name}",
                                "render_result": render_result,
                                "challenge": challenge_detail(name),
                            },
                        )
                        return

                if len(parts) == 4 and parts[3] == "checkpoints" and method == "POST":
                    payload = self.read_json()
                    checkpoint_name = str(payload.get("name", "")).strip()
                    if not checkpoint_name:
                        raise ApiError(400, "Checkpoint name is required.")
                    path = challenge_path(name)
                    if not path.exists():
                        raise ApiError(404, f"Challenge not found: {name}")
                    result = run_script("checkpoint.sh", checkpoint_name, str(path))
                    self.send_json(
                        200,
                        {
                            "message": f"Created checkpoint {checkpoint_name}",
                            "script_result": result,
                            "challenge": challenge_detail(name),
                        },
                    )
                    return

                if len(parts) == 4 and parts[3] == "restore" and method == "POST":
                    payload = self.read_json()
                    checkpoint_id = str(payload.get("checkpoint", "")).strip()
                    if not checkpoint_id:
                        raise ApiError(400, "Checkpoint id is required.")
                    path = challenge_path(name)
                    if not path.exists():
                        raise ApiError(404, f"Challenge not found: {name}")
                    result = run_script("restore.sh", checkpoint_id, str(path))
                    self.send_json(
                        200,
                        {
                            "message": f"Restored checkpoint {checkpoint_id}",
                            "script_result": result,
                            "challenge": challenge_detail(name),
                        },
                    )
                    return

            raise ApiError(404, "API route not found.")
        except ApiError as exc:
            self.send_json(exc.status, {"error": exc.message, "details": exc.details or {}})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api("GET")
            return
        if parsed.path == "/favicon.ico":
            self.send_asset(IMGS_DIR, "amds-favicon.png")
            return
        if parsed.path.startswith("/imgs/"):
            self.send_asset(IMGS_DIR, parsed.path.removeprefix("/imgs/"))
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        self.handle_api("POST")

    def do_PUT(self) -> None:
        self.handle_api("PUT")


def main() -> None:
    parser = argparse.ArgumentParser(description="Amadeus challenge management web UI")
    parser.add_argument("--host", default=os.environ.get("AMADEUS_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("AMADEUS_PORT", "9999")))
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), AmadeusHandler)
    print(f"Amadeus web UI listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
