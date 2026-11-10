---
name: aswath-chronicle
description: Use when building features, refactoring, or making non-trivial decisions that require a persistent audit trail of user prompts, agent choices, and git history without wasting LLM tokens.
---

# Aswath Chronicle: Decision & Interaction Audit Trail

A zero-token-overhead skill for recording every milestone, user prompt, agent decision, and failure recovery as granular markdown records and atomic git commits.

## Core Rules

1. **Write to Disk, Never Re-Echo**:
   - Write decisions and narrative records to `docs/` and `docs/interactions/session-ledger.md`.
   - Never re-print full docs into LLM chat context (saves 95%+ tokens).

2. **Atomic Commits Per Step**:
   - Never do a single giant push.
   - Every architectural beat or test suite gets its own commit with a descriptive message:
     - `docs: record problem and options`
     - `feat: implement query builder`
     - `feat: add in-memory execution command`
     - `test: verify edge cases`

3. **Capture Real Prompts & Turns**:
   - Run `python tools/chronicle.py "<Title>" -p "<User Prompt>" -d "<Decision>" -a "<Action>"` on major steps.

4. **Preserve Mistakes & Pivots**:
   - If an approach failed (e.g. OLX server-side `first_owner` query param bug), document the bug and why the design pivoted to in-memory filtering.
