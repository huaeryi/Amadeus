#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import state_docs


ROOT = Path(__file__).resolve().parents[1]
COGNITION_TEMPLATE = ROOT / "templates" / "cognition.json"
ALLOWED_STATUS = {"hypothesis", "observed", "verified", "blocked", "target"}
ALLOWED_ENV = {"local", "native", "docker", "patched", "remote"}
STATUS_ORDER = ("verified", "observed", "hypothesis", "target", "blocked")
STATUS_TITLE = {
    "verified": "Verified",
    "observed": "Observed",
    "hypothesis": "Hypothesis",
    "target": "Target",
    "blocked": "Blocked",
}


class CapabilityError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def capability_paths(challenge_dir: Path) -> tuple[Path, Path]:
    return state_docs.cognition_path(challenge_dir), state_docs.cognition_md_path(challenge_dir)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CapabilityError(f"missing {path}") from exc
    except json.JSONDecodeError as exc:
        raise CapabilityError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CapabilityError(f"{path.name} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_cognition(challenge_dir: Path) -> dict[str, Any]:
    json_path, _ = capability_paths(challenge_dir)
    template = load_json(COGNITION_TEMPLATE)
    if json_path.exists():
        data = load_json(json_path)
    else:
        data = template
    if not isinstance(data.get("metadata"), dict):
        data["metadata"] = template["metadata"]
    if not isinstance(data.get("capabilities"), dict):
        data["capabilities"] = template["capabilities"]
    if not data.get("challenge"):
        data["challenge"] = challenge_dir.name
    if not data["capabilities"].get("challenge"):
        data["capabilities"]["challenge"] = challenge_dir.name
    return data


def ensure_document(challenge_dir: Path) -> dict[str, Any]:
    data = load_cognition(challenge_dir)
    write_json(capability_paths(challenge_dir)[0], data)
    return data["capabilities"]


def require_string(value: Any, field: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty string")
        return ""
    return value.strip()


def validate_evidence(evidence: Any, cap_id: str, errors: list[str]) -> None:
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{cap_id}: evidence must be a non-empty list")
        return
    for index, item in enumerate(evidence):
        prefix = f"{cap_id}: evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("type", "summary"):
            require_string(item.get(field), f"{prefix}.{field}", errors)
        if not item.get("artifact") and not item.get("command"):
            errors.append(f"{prefix} must include artifact or command")
        if "artifact" in item and item["artifact"] is not None and not isinstance(item["artifact"], str):
            errors.append(f"{prefix}.artifact must be a string")
        if "command" in item and item["command"] is not None and not isinstance(item["command"], str):
            errors.append(f"{prefix}.command must be a string")
        if "jump" in item and item["jump"] is not None and not isinstance(item["jump"], dict):
            errors.append(f"{prefix}.jump must be an object")


def validate_verification(verification: Any, cap_id: str, status: str, errors: list[str]) -> None:
    if status != "verified":
        if verification is not None and not isinstance(verification, dict):
            errors.append(f"{cap_id}: verification must be null or an object")
        return
    if not isinstance(verification, dict):
        errors.append(f"{cap_id}: verified capability must include verification")
        return
    if verification.get("verified") is not True:
        errors.append(f"{cap_id}: verification.verified must be true")
    for field in ("method", "summary"):
        require_string(verification.get(field), f"{cap_id}: verification.{field}", errors)
    if not verification.get("artifact") and not verification.get("command"):
        errors.append(f"{cap_id}: verification must include artifact or command")


def validate_document(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("version must be 1")
    if not isinstance(data.get("challenge", ""), str):
        errors.append("challenge must be a string")
    active_env = data.get("active_env")
    if active_env not in ALLOWED_ENV:
        errors.append(f"active_env must be one of {', '.join(sorted(ALLOWED_ENV))}")
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list):
        errors.append("capabilities must be a list")
        return errors

    seen_ids: set[str] = set()
    for index, cap in enumerate(capabilities):
        if not isinstance(cap, dict):
            errors.append(f"capabilities[{index}] must be an object")
            continue
        cap_id = require_string(cap.get("id"), f"capabilities[{index}].id", errors) or f"capabilities[{index}]"
        if cap_id in seen_ids:
            errors.append(f"{cap_id}: duplicate id")
        seen_ids.add(cap_id)

        for field in ("name", "category", "summary", "env", "status"):
            require_string(cap.get(field), f"{cap_id}.{field}", errors)
        status = str(cap.get("status", ""))
        env = str(cap.get("env", ""))
        if status and status not in ALLOWED_STATUS:
            errors.append(f"{cap_id}: status must be one of {', '.join(sorted(ALLOWED_STATUS))}")
        if env and env not in ALLOWED_ENV:
            errors.append(f"{cap_id}: env must be one of {', '.join(sorted(ALLOWED_ENV))}")

        confidence = cap.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            errors.append(f"{cap_id}: confidence must be a number between 0 and 1")
        for field in ("depends_on", "enables", "blocked_by", "evidence", "notes"):
            if not isinstance(cap.get(field), list):
                errors.append(f"{cap_id}: {field} must be a list")
        for field in ("created_at", "updated_at"):
            require_string(cap.get(field), f"{cap_id}.{field}", errors)

        validate_evidence(cap.get("evidence"), cap_id, errors)
        validate_verification(cap.get("verification"), cap_id, status, errors)
        if status == "blocked" and not cap.get("blocked_by"):
            errors.append(f"{cap_id}: blocked capability must include blocked_by")
        if status == "blocked" and not str(cap.get("reason") or cap.get("summary") or "").strip():
            errors.append(f"{cap_id}: blocked capability must include reason or summary")

    return errors


def normalize_document(data: dict[str, Any], challenge_dir: Path) -> dict[str, Any]:
    changed = False
    if data.get("version") != 1:
        data["version"] = 1
        changed = True
    if not isinstance(data.get("challenge"), str) or not data.get("challenge"):
        data["challenge"] = challenge_dir.name
        changed = True
    if data.get("active_env") not in ALLOWED_ENV:
        data["active_env"] = "local"
        changed = True
    if not isinstance(data.get("capabilities"), list):
        data["capabilities"] = []
        changed = True

    timestamp = now_iso()
    for cap in data["capabilities"]:
        if not isinstance(cap, dict):
            continue
        if not cap.get("created_at"):
            cap["created_at"] = timestamp
            changed = True
        if not cap.get("updated_at"):
            cap["updated_at"] = cap["created_at"]
            changed = True
        for field in ("depends_on", "enables", "blocked_by", "evidence", "notes"):
            if field not in cap:
                cap[field] = []
                changed = True
        if "verification" not in cap:
            cap["verification"] = None
            changed = True

    data["_changed"] = changed
    return data


def evidence_target(item: dict[str, Any]) -> str:
    artifact = str(item.get("artifact") or "").strip()
    command = str(item.get("command") or "").strip()
    if artifact and command:
        return f"{artifact} (`{command}`)"
    if artifact:
        return artifact
    if command:
        return f"`{command}`"
    return str(item.get("summary") or "").strip()


def render_markdown(data: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Capabilities",
        "",
        f"- challenge: {data.get('challenge', '')}",
        f"- active_env: {data.get('active_env', '')}",
        f"- source: amds_state/cognition.json",
        "",
        "> Generated from `amds_state/cognition.json`. Do not edit this file directly.",
        "",
    ]

    capabilities = [cap for cap in data.get("capabilities", []) if isinstance(cap, dict)]
    by_status = {status: [] for status in STATUS_ORDER}
    for cap in capabilities:
        by_status.setdefault(str(cap.get("status", "")), []).append(cap)

    for status in STATUS_ORDER:
        lines.append(f"## {STATUS_TITLE[status]}")
        lines.append("")
        entries = by_status.get(status, [])
        if not entries:
            lines.append("- none")
            lines.append("")
            continue
        for cap in sorted(entries, key=lambda item: (str(item.get("env", "")), str(item.get("name", "")))):
            name = cap.get("name", "")
            env = cap.get("env", "")
            confidence = cap.get("confidence", "")
            blocked_by = cap.get("blocked_by") or []
            suffix = ""
            if status == "blocked" and blocked_by:
                suffix = f": blocked by {', '.join(str(item) for item in blocked_by)}"
            lines.append(f"- {name} [{env}] confidence={confidence}{suffix}")
            summary = str(cap.get("summary") or "").strip()
            if summary:
                lines.append(f"  Summary: {summary}")
            reason = str(cap.get("reason") or "").strip()
            if reason:
                lines.append(f"  Reason: {reason}")
            evidence = cap.get("evidence") or []
            if evidence:
                rendered = "; ".join(evidence_target(item) for item in evidence if isinstance(item, dict))
                if rendered:
                    lines.append(f"  Evidence: {rendered}")
            verification = cap.get("verification")
            if isinstance(verification, dict):
                target = evidence_target(verification)
                if target:
                    lines.append(f"  Verification: {target}")
            enables = cap.get("enables") or []
            if enables:
                lines.append(f"  Enables: {', '.join(str(item) for item in enables)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def command_init(challenge_dir: Path) -> int:
    challenge_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = capability_paths(challenge_dir)
    cognition = load_cognition(challenge_dir)
    data = normalize_document(cognition["capabilities"], challenge_dir)
    data.pop("_changed", False)
    cognition["capabilities"] = data
    write_json(json_path, cognition)
    state_docs.render_docs(challenge_dir)
    print(f"initialized {json_path}")
    print(f"rendered {md_path}")
    return 0


def command_validate(challenge_dir: Path) -> int:
    json_path, _ = capability_paths(challenge_dir)
    data = load_cognition(challenge_dir)["capabilities"]
    errors = validate_document(data)
    if errors:
        for error in errors:
            print(f"capabilities: {error}", file=sys.stderr)
        return 1
    print(f"valid {json_path}")
    return 0


def command_render(challenge_dir: Path) -> int:
    json_path, md_path = capability_paths(challenge_dir)
    cognition = load_cognition(challenge_dir)
    data = cognition["capabilities"]
    data = normalize_document(data, challenge_dir)
    changed = data.pop("_changed", False)
    errors = validate_document(data)
    if errors:
        for error in errors:
            print(f"capabilities: {error}", file=sys.stderr)
        return 1
    if changed:
        cognition["capabilities"] = data
        write_json(json_path, cognition)
    state_docs.render_docs(challenge_dir)
    print(f"rendered {md_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Amadeus capability JSON and generated Markdown")
    parser.add_argument("command", choices=("init", "validate", "render"))
    parser.add_argument("challenge_dir", nargs="?", default=".")
    args = parser.parse_args()

    challenge_dir = Path(args.challenge_dir).resolve()
    try:
        if args.command == "init":
            return command_init(challenge_dir)
        if args.command == "validate":
            return command_validate(challenge_dir)
        if args.command == "render":
            return command_render(challenge_dir)
    except (CapabilityError, state_docs.StateDocError) as exc:
        print(f"capabilities: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
