#!/usr/bin/env python3
"""Chronicle helper to record user-agent decisions and prompt transitions to disk."""

from __future__ import annotations

import argparse
import datetime
import os
from pathlib import Path

LEDGER_PATH = Path("docs/interactions/session-ledger.md")


def append_entry(title: str, prompt: str | None = None, decision: str | None = None,
                 action: str | None = None) -> None:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = [f"\n### [{now}] {title}"]
    if prompt:
        entry.append(f"- **User Prompt**: `{prompt}`")
    if decision:
        entry.append(f"- **Agent Decision**: {decision}")
    if action:
        entry.append(f"- **Action / Output**: {action}")
    entry.append("")

    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write("\n".join(entry))

    print(f"Logged chronicle entry: {title} -> {LEDGER_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a milestone or decision into docs/interactions.")
    parser.add_argument("title", help="Milestone title or decision summary")
    parser.add_argument("--prompt", "-p", help="User prompt that triggered the step")
    parser.add_argument("--decision", "-d", help="Agent architectural decision")
    parser.add_argument("--action", "-a", help="Action taken or commit ref")
    args = parser.parse_args()

    append_entry(args.title, prompt=args.prompt, decision=args.decision, action=args.action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
