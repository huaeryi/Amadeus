#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
COGNITION_TEMPLATE = ROOT / "templates" / "cognition.json"
AMDS_STATE_DIR = "amds_state"


class StateDocError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StateDocError(f"missing {path}") from exc
    except json.JSONDecodeError as exc:
        raise StateDocError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise StateDocError(f"{path.name} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def state_dir(challenge_dir: Path) -> Path:
    return challenge_dir / AMDS_STATE_DIR


def cognition_path(challenge_dir: Path) -> Path:
    new_path = state_dir(challenge_dir) / "cognition.json"
    old_path = challenge_dir / "cognition.json"
    if new_path.exists() or not old_path.exists():
        return new_path
    return old_path


def cognition_md_path(challenge_dir: Path) -> Path:
    new_path = state_dir(challenge_dir) / "COGNITION.md"
    old_path = challenge_dir / "COGNITION.md"
    if cognition_path(challenge_dir).parent == state_dir(challenge_dir):
        return new_path
    return old_path


def sync_challenge_names(data: dict[str, Any], challenge: str) -> bool:
    changed = False
    if not data.get("challenge"):
        data["challenge"] = challenge
        changed = True
    for key in ("metadata", "facts", "state", "capabilities"):
        section = data.get(key)
        if isinstance(section, dict) and not section.get("challenge"):
            section["challenge"] = challenge
            changed = True
    return changed


def load_cognition(challenge_dir: Path) -> dict[str, Any]:
    path = cognition_path(challenge_dir)
    template = load_json(COGNITION_TEMPLATE)
    if path.exists():
        data = load_json(path)
    else:
        data = template
    for key in ("facts", "state", "capabilities"):
        if key not in data:
            data[key] = template[key]
    if not isinstance(data.get("facts"), dict):
        raise StateDocError("cognition.json: facts must be an object")
    if not isinstance(data.get("metadata"), dict):
        raise StateDocError("cognition.json: metadata must be an object")
    if not isinstance(data.get("state"), dict):
        raise StateDocError("cognition.json: state must be an object")
    if not isinstance(data.get("capabilities"), dict):
        raise StateDocError("cognition.json: capabilities must be an object")
    return data


def markdown_sections(text: str) -> tuple[str, dict[str, list[str]]]:
    current = ""
    title = ""
    sections: dict[str, list[str]] = {}
    preface: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            title = line[2:].strip()
            current = ""
            continue
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if not line:
            continue
        if current:
            item = line[2:].strip() if line.startswith("- ") else line.strip()
            sections[current].append(item)
        elif title:
            preface.append(line.strip())
    return title, {key: value or ["none yet"] for key, value in sections.items()}


def state_markdown_sections(text: str) -> dict[str, list[str]]:
    current = ""
    sections: dict[str, list[str]] = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            current = line[2:].strip()
            sections.setdefault(current, [])
            continue
        if not line or not current:
            continue
        item = line[2:].strip() if line.startswith("- ") else line.strip()
        sections[current].append(item)
    return sections


def state_from_markdown_text(text: str, challenge: str) -> dict[str, Any]:
    sections = state_markdown_sections(text)
    known_sections = {
        "Current Stage",
        "Target Profile",
        "Current Primitive",
        "Debug",
        "Next Step",
        "Checkpoint Plan",
        "Rejected Branches",
        "Avoid",
        "Open Questions",
        "Your Turn",
    }
    stage_items = sections.get("Current Stage", ["not started"])
    profile_items = sections.get("Target Profile", [])
    profile = {"challenge_type": "", "protections": "", "likely_bug_class": ""}
    for item in profile_items:
        key, _, value = item.partition(":")
        normalized = key.strip().replace(" ", "_").replace("-", "_").lower()
        if normalized in profile:
            profile[normalized] = value.strip()
    plan_items = sections.get("Checkpoint Plan", [])
    plan = {"last_stable_checkpoint": "", "next_likely_checkpoint": "", "after_that": ""}
    for item in plan_items:
        key, _, value = item.partition(":")
        normalized = key.strip().replace(" ", "_").replace("-", "_").lower()
        if normalized in plan:
            plan[normalized] = value.strip()
    return {
        "version": 1,
        "challenge": challenge,
        "current_stage": stage_items[0] if stage_items else "not started",
        "target_profile": profile,
        "current_primitive": (sections.get("Current Primitive") or ["none yet"])[0],
        "debug": debug_from_items(sections.get("Debug") or []),
        "next_steps": sections.get("Next Step") or ["none yet"],
        "checkpoint_plan": plan,
        "rejected_branches": sections.get("Rejected Branches") or ["none yet"],
        "avoid": sections.get("Avoid") or ["none yet"],
        "open_questions": sections.get("Open Questions") or ["none yet"],
        "your_turn": sections.get("Your Turn") or [],
        "extra_sections": [
            {"title": key, "items": value}
            for key, value in sections.items()
            if key not in known_sections
        ],
    }


def state_from_markdown(path: Path, challenge: str) -> dict[str, Any]:
    return state_from_markdown_text(path.read_text(encoding="utf-8"), challenge)


def facts_from_markdown_text(text: str, challenge: str) -> dict[str, Any]:
    title, sections = markdown_sections(text)
    intro = "Only record facts verified from the binary, runtime, debugger, or exploit output."
    data_sections = [{"title": key, "items": value or ["none yet"]} for key, value in sections.items()]
    return {"version": 1, "challenge": challenge, "intro": intro, "sections": data_sections}


def facts_from_markdown(path: Path, challenge: str) -> dict[str, Any]:
    return facts_from_markdown_text(path.read_text(encoding="utf-8"), challenge)


def debug_from_items(items: list[str]) -> dict[str, Any]:
    debug = {"pwndbg_mcp": "127.0.0.1:8780", "session_scope": "single challenge", "notes": []}
    notes: list[str] = []
    for item in items:
        key, _, value = item.partition(":")
        normalized = key.strip().replace(" ", "_").replace("-", "_").lower()
        if normalized in {"pwndbg_mcp", "session_scope"}:
            debug[normalized] = value.strip()
        elif item.strip() and item.strip() != "none yet":
            notes.append(item.strip())
    debug["notes"] = notes
    return debug


def normalize_cognition(data: dict[str, Any], challenge_dir: Path) -> bool:
    template = load_json(COGNITION_TEMPLATE)
    changed = False
    if data.get("version") != 1:
        data["version"] = 1
        changed = True
    for key in ("metadata", "facts", "state", "capabilities"):
        if not isinstance(data.get(key), dict):
            data[key] = template[key]
            changed = True
    changed = sync_challenge_names(data, challenge_dir.name) or changed
    metadata = data["metadata"]
    if metadata.get("schema_version") != 1:
        metadata["schema_version"] = 1
        changed = True
    if not metadata.get("title"):
        metadata["title"] = challenge_dir.name
        changed = True

    state = data["state"]
    for field, default in (
        ("your_turn", []),
        ("extra_sections", []),
        ("debug", {"pwndbg_mcp": "127.0.0.1:8780", "session_scope": "single challenge", "notes": []}),
    ):
        if field not in state:
            state[field] = default
            changed = True

    capabilities = data["capabilities"]
    if capabilities.get("active_env") is None:
        capabilities["active_env"] = "local"
        changed = True
    if not isinstance(capabilities.get("capabilities"), list):
        capabilities["capabilities"] = []
        changed = True
    return changed


def init_docs(challenge_dir: Path) -> None:
    challenge_dir.mkdir(parents=True, exist_ok=True)
    state_dir(challenge_dir).mkdir(parents=True, exist_ok=True)
    data = load_cognition(challenge_dir)
    changed = normalize_cognition(data, challenge_dir)
    if changed or not cognition_path(challenge_dir).exists():
        write_json(cognition_path(challenge_dir), data)
    render_docs(challenge_dir)


def validate_facts(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("cognition.json.facts: version must be 1")
    if not isinstance(data.get("challenge"), str):
        errors.append("cognition.json.facts: challenge must be a string")
    sections = data.get("sections")
    if not isinstance(sections, list):
        errors.append("cognition.json.facts: sections must be a list")
        return errors
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            errors.append(f"cognition.json.facts: sections[{index}] must be an object")
            continue
        if not isinstance(section.get("title"), str) or not section.get("title").strip():
            errors.append(f"cognition.json.facts: sections[{index}].title must be a non-empty string")
        if not isinstance(section.get("items"), list):
            errors.append(f"cognition.json.facts: sections[{index}].items must be a list")
    return errors


def validate_state(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("cognition.json.state: version must be 1")
    for field in ("challenge", "current_stage", "current_primitive"):
        if not isinstance(data.get(field), str):
            errors.append(f"cognition.json.state: {field} must be a string")
    if not isinstance(data.get("target_profile"), dict):
        errors.append("cognition.json.state: target_profile must be an object")
    if not isinstance(data.get("checkpoint_plan"), dict):
        errors.append("cognition.json.state: checkpoint_plan must be an object")
    if "debug" in data:
        debug = data.get("debug")
        if not isinstance(debug, dict):
            errors.append("cognition.json.state: debug must be an object")
        else:
            for field in ("pwndbg_mcp", "session_scope"):
                if field in debug and not isinstance(debug.get(field), str):
                    errors.append(f"cognition.json.state: debug.{field} must be a string")
            if "notes" in debug and not isinstance(debug.get("notes"), list):
                errors.append("cognition.json.state: debug.notes must be a list")
    for field in ("next_steps", "rejected_branches", "avoid", "open_questions"):
        if not isinstance(data.get(field), list):
            errors.append(f"cognition.json.state: {field} must be a list")
    if "your_turn" in data and not isinstance(data.get("your_turn"), list):
        errors.append("cognition.json.state: your_turn must be a list")
    if "extra_sections" in data:
        extra_sections = data.get("extra_sections")
        if not isinstance(extra_sections, list):
            errors.append("cognition.json.state: extra_sections must be a list")
        else:
            for index, section in enumerate(extra_sections):
                if not isinstance(section, dict):
                    errors.append(f"cognition.json.state: extra_sections[{index}] must be an object")
                    continue
                if not isinstance(section.get("title"), str) or not section.get("title").strip():
                    errors.append(f"cognition.json.state: extra_sections[{index}].title must be a non-empty string")
                if not isinstance(section.get("items"), list):
                    errors.append(f"cognition.json.state: extra_sections[{index}].items must be a list")
    return errors


def validate_capabilities(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("cognition.json.capabilities: version must be 1")
    if not isinstance(data.get("challenge"), str):
        errors.append("cognition.json.capabilities: challenge must be a string")
    if not isinstance(data.get("active_env"), str):
        errors.append("cognition.json.capabilities: active_env must be a string")
    if not isinstance(data.get("capabilities"), list):
        errors.append("cognition.json.capabilities: capabilities must be a list")
    return errors


def validate_metadata(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("cognition.json.metadata: schema_version must be 1")
    for field in ("title", "source", "platform", "problem_id", "challenge_type", "level", "downloaded_at", "description", "evidence_dir"):
        if field in data and data[field] is not None and not isinstance(data[field], str):
            errors.append(f"cognition.json.metadata: {field} must be a string")
    for field in ("tags", "local_files", "tracked_files"):
        if field in data and not isinstance(data[field], list):
            errors.append(f"cognition.json.metadata: {field} must be a list")
    return errors


def validate_docs(challenge_dir: Path) -> list[str]:
    data = load_cognition(challenge_dir)
    return (
        validate_metadata(data["metadata"])
        + validate_facts(data["facts"])
        + validate_state(data["state"])
        + validate_capabilities(data["capabilities"])
    )


def render_facts(data: dict[str, Any]) -> str:
    lines = ["# Confirmed Facts", ""]
    intro = str(data.get("intro") or "").strip()
    if intro:
        lines.extend([intro, ""])
    for section in data.get("sections", []):
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "").strip()
        if not title:
            continue
        lines.extend([f"## {title}", ""])
        items = section.get("items") if isinstance(section.get("items"), list) else []
        if not items:
            items = ["none yet"]
        lines.extend(f"- {item}" for item in items)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_state(data: dict[str, Any]) -> str:
    profile = data.get("target_profile") if isinstance(data.get("target_profile"), dict) else {}
    plan = data.get("checkpoint_plan") if isinstance(data.get("checkpoint_plan"), dict) else {}
    debug = data.get("debug") if isinstance(data.get("debug"), dict) else {}
    def field_line(label: str, value: Any) -> str:
        text = str(value or "").strip()
        return f"- {label}: {text}" if text else f"- {label}:"

    lines = [
        "# Current Stage",
        "",
        str(data.get("current_stage") or "not started"),
        "",
        "# Target Profile",
        "",
        field_line("challenge type", profile.get("challenge_type", "")),
        field_line("protections", profile.get("protections", "")),
        field_line("likely bug class", profile.get("likely_bug_class", "")),
        "",
        "# Current Primitive",
        "",
        f"- {data.get('current_primitive') or 'none yet'}",
        "",
        "# Debug",
        "",
        field_line("pwndbg_mcp", debug.get("pwndbg_mcp", "127.0.0.1:8780")),
        field_line("session_scope", debug.get("session_scope", "single challenge")),
        "",
    ]
    debug_notes = debug.get("notes") if isinstance(debug.get("notes"), list) else []
    if debug_notes:
        lines.extend(["# Debug Notes", ""])
        lines.extend(f"- {item}" for item in debug_notes if str(item).strip())
        lines.append("")
    list_sections = (
        ("Next Step", data.get("next_steps")),
        ("Checkpoint Plan", [
            f"last stable checkpoint: {plan.get('last_stable_checkpoint', '')}",
            f"next likely checkpoint: {plan.get('next_likely_checkpoint', '')}",
            f"after that: {plan.get('after_that', '')}",
        ]),
        ("Rejected Branches", data.get("rejected_branches")),
        ("Avoid", data.get("avoid")),
        ("Open Questions", data.get("open_questions")),
        ("Your Turn", data.get("your_turn")),
    )
    for title, items in list_sections:
        lines.extend([f"# {title}", ""])
        if not isinstance(items, list) or not items:
            items = ["none yet"]
        lines.extend(f"- {item}" for item in items if str(item).strip())
        lines.append("")
    for section in data.get("extra_sections", []):
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "").strip()
        if not title:
            continue
        lines.extend([f"# {title}", ""])
        items = section.get("items") if isinstance(section.get("items"), list) else []
        lines.extend(f"- {item}" for item in items if str(item).strip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


STATUS_ORDER = ("verified", "observed", "hypothesis", "target", "blocked")
STATUS_TITLE = {
    "verified": "Verified",
    "observed": "Observed",
    "hypothesis": "Hypothesis",
    "target": "Target",
    "blocked": "Blocked",
}


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


def render_capabilities(data: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Capabilities",
        "",
        f"- active_env: {data.get('active_env', '')}",
        "",
    ]
    capabilities = [cap for cap in data.get("capabilities", []) if isinstance(cap, dict)]
    by_status = {status: [] for status in STATUS_ORDER}
    for cap in capabilities:
        by_status.setdefault(str(cap.get("status", "")), []).append(cap)

    for status in STATUS_ORDER:
        lines.extend([f"## {STATUS_TITLE[status]}", ""])
        entries = by_status.get(status, [])
        if not entries:
            lines.extend(["- none", ""])
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


def demote_markdown(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.rstrip().splitlines():
        if line.startswith("## "):
            lines.append("#### " + line[3:])
        elif line.startswith("# "):
            lines.append("### " + line[2:])
        else:
            lines.append(line)
    return lines


def render_metadata(data: dict[str, Any]) -> str:
    fields = (
        ("title", data.get("title")),
        ("platform", data.get("platform")),
        ("source", data.get("source")),
        ("problem_id", data.get("problem_id")),
        ("challenge_type", data.get("challenge_type")),
        ("tags", ", ".join(str(item) for item in data.get("tags", []) if str(item).strip()) if isinstance(data.get("tags"), list) else data.get("tags")),
        ("points", data.get("points")),
        ("level", data.get("level")),
        ("docker", data.get("docker")),
        ("annex", data.get("annex")),
        ("downloaded_at", data.get("downloaded_at")),
        ("evidence_dir", data.get("evidence_dir")),
    )
    lines = ["# Metadata", ""]
    for label, value in fields:
        if value is None or value == "" or value == []:
            continue
        lines.append(f"- {label}: {value}")
    description = str(data.get("description") or "").strip()
    if description:
        lines.extend(["", "## Description", "", description])
    local_files = data.get("local_files")
    if isinstance(local_files, list) and local_files:
        lines.extend(["", "## Local Files", ""])
        lines.extend(f"- {item}" for item in local_files)
    tracked_files = data.get("tracked_files")
    if isinstance(tracked_files, list) and tracked_files:
        lines.extend(["", "## Tracked Files", ""])
        lines.extend(f"- {item}" for item in tracked_files)
    return "\n".join(lines).rstrip() + "\n"


def render_cognition(data: dict[str, Any]) -> str:
    lines = [
        "# Cognition",
        "",
        f"- challenge: {data.get('challenge', '')}",
        "- source: amds_state/cognition.json",
        "",
        "> Generated from `amds_state/cognition.json`. Do not edit this file directly.",
        "",
        "## Metadata",
        "",
    ]
    lines.extend(demote_markdown(render_metadata(data["metadata"])))
    lines.extend([
        "",
        "## State",
        "",
    ])
    lines.extend(demote_markdown(render_state(data["state"])))
    lines.extend(["", "## Facts", ""])
    lines.extend(demote_markdown(render_facts(data["facts"])))
    lines.extend(["", "## Capabilities", ""])
    lines.extend(demote_markdown(render_capabilities(data["capabilities"])))
    return "\n".join(lines).rstrip() + "\n"


def render_docs(challenge_dir: Path) -> None:
    data = load_cognition(challenge_dir)
    changed = normalize_cognition(data, challenge_dir)
    errors = validate_docs(challenge_dir)
    if errors:
        raise StateDocError("; ".join(errors))
    if changed:
        write_json(cognition_path(challenge_dir), data)
    md_path = cognition_md_path(challenge_dir)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_cognition(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Amadeus cognition JSON and generated Markdown")
    parser.add_argument("command", choices=("init", "validate", "render"))
    parser.add_argument("challenge_dir", nargs="?", default=".")
    args = parser.parse_args()
    challenge_dir = Path(args.challenge_dir).resolve()
    try:
        if args.command == "init":
            init_docs(challenge_dir)
            print(f"initialized {cognition_path(challenge_dir)}")
            print(f"rendered {cognition_md_path(challenge_dir)}")
        elif args.command == "validate":
            errors = validate_docs(challenge_dir)
            if errors:
                for error in errors:
                    print(f"state-docs: {error}", file=sys.stderr)
                return 1
            print(f"valid {cognition_path(challenge_dir)}")
        elif args.command == "render":
            render_docs(challenge_dir)
            print(f"rendered {cognition_md_path(challenge_dir)}")
    except StateDocError as exc:
        print(f"state-docs: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
