#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FACTS_TEMPLATE = ROOT / "templates" / "facts.json"
STATE_TEMPLATE = ROOT / "templates" / "state.json"


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
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def state_from_markdown(path: Path, challenge: str) -> dict[str, Any]:
    sections = state_markdown_sections(path.read_text(encoding="utf-8"))
    known_sections = {
        "Current Stage",
        "Target Profile",
        "Current Primitive",
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


def facts_from_markdown(path: Path, challenge: str) -> dict[str, Any]:
    title, sections = markdown_sections(path.read_text(encoding="utf-8"))
    intro = "Only record facts verified from the binary, runtime, debugger, or exploit output."
    data_sections = [{"title": key, "items": value or ["none yet"]} for key, value in sections.items()]
    return {"version": 1, "challenge": challenge, "intro": intro, "sections": data_sections}


def init_docs(challenge_dir: Path) -> None:
    challenge_dir.mkdir(parents=True, exist_ok=True)
    for template, output in (
        (FACTS_TEMPLATE, challenge_dir / "facts.json"),
        (STATE_TEMPLATE, challenge_dir / "state.json"),
    ):
        if not output.exists():
            data = load_json(template)
        else:
            data = load_json(output)
        changed = False
        if not data.get("challenge"):
            data["challenge"] = challenge_dir.name
            changed = True
        if output.name == "state.json" and "your_turn" not in data:
            data["your_turn"] = []
            changed = True
        if output.name == "state.json" and "extra_sections" not in data:
            data["extra_sections"] = []
            changed = True
        if changed or not output.exists():
            write_json(output, data)
    render_docs(challenge_dir)


def validate_facts(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("facts.json: version must be 1")
    if not isinstance(data.get("challenge"), str):
        errors.append("facts.json: challenge must be a string")
    sections = data.get("sections")
    if not isinstance(sections, list):
        errors.append("facts.json: sections must be a list")
        return errors
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            errors.append(f"facts.json: sections[{index}] must be an object")
            continue
        if not isinstance(section.get("title"), str) or not section.get("title").strip():
            errors.append(f"facts.json: sections[{index}].title must be a non-empty string")
        if not isinstance(section.get("items"), list):
            errors.append(f"facts.json: sections[{index}].items must be a list")
    return errors


def validate_state(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("state.json: version must be 1")
    for field in ("challenge", "current_stage", "current_primitive"):
        if not isinstance(data.get(field), str):
            errors.append(f"state.json: {field} must be a string")
    if not isinstance(data.get("target_profile"), dict):
        errors.append("state.json: target_profile must be an object")
    if not isinstance(data.get("checkpoint_plan"), dict):
        errors.append("state.json: checkpoint_plan must be an object")
    for field in ("next_steps", "rejected_branches", "avoid", "open_questions"):
        if not isinstance(data.get(field), list):
            errors.append(f"state.json: {field} must be a list")
    if "your_turn" in data and not isinstance(data.get("your_turn"), list):
        errors.append("state.json: your_turn must be a list")
    if "extra_sections" in data:
        extra_sections = data.get("extra_sections")
        if not isinstance(extra_sections, list):
            errors.append("state.json: extra_sections must be a list")
        else:
            for index, section in enumerate(extra_sections):
                if not isinstance(section, dict):
                    errors.append(f"state.json: extra_sections[{index}] must be an object")
                    continue
                if not isinstance(section.get("title"), str) or not section.get("title").strip():
                    errors.append(f"state.json: extra_sections[{index}].title must be a non-empty string")
                if not isinstance(section.get("items"), list):
                    errors.append(f"state.json: extra_sections[{index}].items must be a list")
    return errors


def validate_docs(challenge_dir: Path) -> list[str]:
    return validate_facts(load_json(challenge_dir / "facts.json")) + validate_state(load_json(challenge_dir / "state.json"))


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
    ]
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


def render_docs(challenge_dir: Path) -> None:
    facts = load_json(challenge_dir / "facts.json")
    state = load_json(challenge_dir / "state.json")
    errors = validate_facts(facts) + validate_state(state)
    if errors:
        raise StateDocError("; ".join(errors))
    (challenge_dir / "FACTS.md").write_text(render_facts(facts), encoding="utf-8")
    (challenge_dir / "STATE.md").write_text(render_state(state), encoding="utf-8")


def import_markdown(challenge_dir: Path) -> None:
    if (challenge_dir / "FACTS.md").exists():
        write_json(challenge_dir / "facts.json", facts_from_markdown(challenge_dir / "FACTS.md", challenge_dir.name))
    if (challenge_dir / "STATE.md").exists():
        write_json(challenge_dir / "state.json", state_from_markdown(challenge_dir / "STATE.md", challenge_dir.name))
    render_docs(challenge_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Amadeus facts/state JSON and generated Markdown")
    parser.add_argument("command", choices=("init", "validate", "render", "import-md"))
    parser.add_argument("challenge_dir", nargs="?", default=".")
    args = parser.parse_args()
    challenge_dir = Path(args.challenge_dir).resolve()
    try:
        if args.command == "init":
            init_docs(challenge_dir)
            print(f"initialized {challenge_dir}/facts.json")
            print(f"initialized {challenge_dir}/state.json")
            print(f"rendered {challenge_dir}/FACTS.md")
            print(f"rendered {challenge_dir}/STATE.md")
        elif args.command == "validate":
            errors = validate_docs(challenge_dir)
            if errors:
                for error in errors:
                    print(f"state-docs: {error}", file=sys.stderr)
                return 1
            print(f"valid {challenge_dir}/facts.json")
            print(f"valid {challenge_dir}/state.json")
        elif args.command == "render":
            render_docs(challenge_dir)
            print(f"rendered {challenge_dir}/FACTS.md")
            print(f"rendered {challenge_dir}/STATE.md")
        elif args.command == "import-md":
            import_markdown(challenge_dir)
            print(f"imported markdown into {challenge_dir}/facts.json")
            print(f"imported markdown into {challenge_dir}/state.json")
    except StateDocError as exc:
        print(f"state-docs: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
