#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
CHALLENGES_DIR = ROOT_DIR / "challenges"
BIN_DIR = ROOT_DIR / "bin"
CORE_DOCUMENTS = ("STATE.md", "FACTS.md", ".ctf-files", ".pwnrun")
CHALLENGE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass
class ApiError(Exception):
    status: int
    message: str
    details: dict[str, Any] | None = None


def isoformat_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")


def challenge_path(name: str) -> Path:
    if not CHALLENGE_NAME_RE.fullmatch(name):
        raise ApiError(400, "Invalid challenge name. Use letters, numbers, dot, dash, or underscore.")

    path = (CHALLENGES_DIR / name).resolve()
    try:
        path.relative_to(CHALLENGES_DIR.resolve())
    except ValueError as exc:
        raise ApiError(400, "Challenge path escapes the challenges directory.") from exc
    return path


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def parse_meta_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    meta: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        meta[key.strip()] = value.strip()
    return meta


def run_script(script_name: str, *args: str) -> dict[str, Any]:
    command = ["bash", str(BIN_DIR / script_name), *args]
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


def collect_artifacts(path: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for entry in sorted(path.iterdir(), key=lambda item: item.name.lower()):
        if entry.name in {"checkpoints", "attempts"}:
            continue

        stat = entry.stat()
        artifacts.append(
            {
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size": stat.st_size,
                "modified_at": isoformat_from_timestamp(stat.st_mtime),
                "is_executable": entry.is_file() and os.access(entry, os.X_OK),
            }
        )
    return artifacts


def collect_attempts(path: Path) -> list[dict[str, Any]]:
    attempts_dir = path / "attempts"
    if not attempts_dir.exists():
        return []

    attempts: list[dict[str, Any]] = []
    for entry in sorted(attempts_dir.iterdir(), key=lambda item: item.name.lower(), reverse=True):
        if not entry.is_file():
            continue
        stat = entry.stat()
        attempts.append(
            {
                "name": entry.name,
                "size": stat.st_size,
                "modified_at": isoformat_from_timestamp(stat.st_mtime),
            }
        )
    return attempts


def collect_checkpoints(path: Path) -> list[dict[str, Any]]:
    checkpoints_dir = path / "checkpoints"
    latest_name = None
    latest_link = checkpoints_dir / "latest"
    if latest_link.is_symlink():
        latest_name = latest_link.resolve().name

    checkpoints: list[dict[str, Any]] = []
    if not checkpoints_dir.exists():
        return checkpoints

    for entry in sorted(checkpoints_dir.iterdir(), key=lambda item: item.name.lower(), reverse=True):
        if not entry.is_dir() or entry.name == "latest":
            continue
        meta = parse_meta_file(entry / "META.txt")
        stat = entry.stat()
        checkpoints.append(
            {
                "id": meta.get("checkpoint_id", entry.name),
                "name": meta.get("name", entry.name),
                "created_at": meta.get("created_at", isoformat_from_timestamp(stat.st_mtime)),
                "target_dir": meta.get("target_dir", "."),
                "is_latest": entry.name == latest_name,
            }
        )
    return checkpoints


def parse_run_info(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["bash", str(BIN_DIR / "run_pwn.sh"), str(path), "info"],
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
    attempts = collect_attempts(path)
    core_files = {name: (path / name).exists() for name in CORE_DOCUMENTS}
    updated_at = isoformat_from_timestamp(path.stat().st_mtime)
    for artifact in artifacts:
        updated_at = max(updated_at, artifact["modified_at"])

    return {
        "name": path.name,
        "path": str(path.relative_to(ROOT_DIR)),
        "initialized": (path / "STATE.md").exists() and (path / "FACTS.md").exists(),
        "core_files": core_files,
        "checkpoint_count": len(checkpoints),
        "attempt_count": len(attempts),
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

    documents = {document: read_text_if_exists(path / document) for document in CORE_DOCUMENTS}
    return {
        "summary": challenge_summary(path),
        "documents": documents,
        "checkpoints": collect_checkpoints(path),
        "attempts": collect_attempts(path),
        "artifacts": collect_artifacts(path),
    }


def list_challenges() -> list[dict[str, Any]]:
    if not CHALLENGES_DIR.exists():
        return []

    challenges = [
        challenge_summary(entry)
        for entry in sorted(CHALLENGES_DIR.iterdir(), key=lambda item: item.name.lower())
        if entry.is_dir() and not entry.name.startswith(".")
    ]
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
                    path = challenge_path(name)
                    if path.exists():
                        raise ApiError(409, f"Challenge already exists: {name}")
                    path.mkdir(parents=False, exist_ok=False)
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

                if len(parts) == 4 and parts[3] == "document":
                    document_name = query.get("name", [""])[0]
                    if document_name not in CORE_DOCUMENTS:
                        raise ApiError(400, "Unsupported document.")
                    path = challenge_path(name)
                    if not path.exists():
                        raise ApiError(404, f"Challenge not found: {name}")
                    document_path = path / document_name

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
                        payload = self.read_json()
                        content = str(payload.get("content", ""))
                        document_path.write_text(content, encoding="utf-8")
                        self.send_json(
                            200,
                            {
                                "message": f"Saved {document_name}",
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
