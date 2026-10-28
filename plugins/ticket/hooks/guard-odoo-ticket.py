#!/usr/bin/env python3
"""PreToolUse guard for the Odoo ticket tool (odoo_ticket.py).

- Write commands are for humans only: blocked outright for Claude. The shipped
  CLI has none, but older local copies may.
- The config holds the API key: Claude never reads it.
- Commands that print personal data unmasked or half-masked (`--raw`,
  `--regex-only`, `sanitizer.py --dry-run`) always ask the user, even in auto
  mode.
"""
import json
import re
import sys

WRITE_CMDS = r"comment|create|set-stage|assign|set-pr|set-description|send-template"

data = json.load(sys.stdin)
cmd = (data.get("tool_input") or {}).get("command", "")

if re.search(rf"odoo_ticket\.py\b[^|;&]*\s({WRITE_CMDS})\b", cmd):
    print("Blocked: Odoo ticket writes are done by the user, not Claude. "
          "Hand them the command or text to run themselves.", file=sys.stderr)
    sys.exit(2)

if re.search(r"compassion-odoo/config\.ini", cmd):
    print("Blocked: this file holds the Odoo API key. To change it, the user runs "
          "`odoo_ticket.py setup` in their own terminal.", file=sys.stderr)
    sys.exit(2)

if (re.search(r"odoo_ticket\.py\b.*--(raw|regex-only)\b", cmd)
        or re.search(r"sanitizer\.py\b.*--(dry-run|regex-only)\b", cmd)):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": "This can show UNSANITIZED personal data "
                                    "(real names, emails, phones) to Claude.",
    }}))
