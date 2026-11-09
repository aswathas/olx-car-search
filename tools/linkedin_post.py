"""Gate and render a LinkedIn post spec.

    python tools/linkedin_post.py --spec docs/linkedin/specs/<slug>.json --check
    python tools/linkedin_post.py --spec docs/linkedin/specs/<slug>.json \
        --out docs/linkedin/<date>-<slug>.md

A spec that fails a gate writes nothing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BANNED = ["excited to announce", "delighted", "game-changer", "game changer",
          "revolutionary", "unlock", "leverage", "seamless", "delve",
          "i am excited", "thrilled to"]
PLAIN_WORD = re.compile(r"^[a-z0-9]+$")
HAS_SOURCE = re.compile(r"(https?://|\.py\b|\.json\b|/|::)")


def render(spec: dict) -> str:
    parts = [spec["hook"].strip(), ""]
    parts.extend(paragraph.strip() for paragraph in spec["body"])
    parts.append("")
    parts.append(spec["cta"].strip())
    parts.append("")
    parts.append(" ".join("#" + tag for tag in spec["hashtags"]))
    text = "\n\n".join(parts)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def check(spec: dict, spec_dir: Path) -> list[str]:
    failures: list[str] = []
    hook = (spec.get("hook") or "").strip()
    if not hook:
        failures.append("hook is missing")
    elif len(hook) > 200:
        failures.append(f"hook is {len(hook)} characters, max 200")

    body = spec.get("body") or []
    if not body:
        failures.append("body is missing")
    for index, paragraph in enumerate(body):
        if len(paragraph) > 600:
            failures.append(f"body[{index}] is {len(paragraph)} characters, max 600")

    links = spec.get("links") or []
    if not any(link.get("url", "").startswith("https://") for link in links):
        failures.append("no https link")

    hashtags = spec.get("hashtags") or []
    if not 3 <= len(hashtags) <= 5:
        failures.append(f"{len(hashtags)} hashtags, need 3-5")
    for tag in hashtags:
        if not PLAIN_WORD.match(tag):
            failures.append(f"hashtag {tag!r} is not a plain word")

    for image in spec.get("images") or []:
        if not image.get("alt"):
            failures.append(f"image {image.get('path')} has no alt text")
        path = spec_dir / image.get("path", "")
        if not path.exists():
            path = spec_dir.parent / image.get("path", "")
        if not path.exists():
            failures.append(f"image {image.get('path')} does not exist")
        elif path.stat().st_size > 12 * 1024 * 1024:
            failures.append(f"image {image.get('path')} is over 12MB")

    evidence = spec.get("evidence") or []
    if not any(HAS_SOURCE.search(line) for line in evidence):
        failures.append("no evidence line names a source")

    if not (spec.get("cta") or "").strip():
        failures.append("cta is missing")

    rendered = render(spec).lower()
    for word in BANNED:
        if word in rendered:
            failures.append(f"banned word: {word}")

    if len(render(spec)) > 3000:
        failures.append(f"post is {len(render(spec))} characters, max 3000")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    failures = check(spec, args.spec.parent)
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    if args.check:
        print(f"OK {args.spec} - {len(render(spec))} characters")
        return 0
    if not args.out:
        print("OK - pass --out to write the post")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(spec) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
