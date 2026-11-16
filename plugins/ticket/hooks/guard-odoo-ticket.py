#!/usr/bin/env python3
"""PreToolUse guard for the Odoo ticket tool (odoo_ticket.py).

A guardrail against honest mistakes, not a security boundary: it reads the
command as text, so a differently spelled command gets past it. The hard
guarantees are elsewhere: the CLIs refuse unmasked output outside a terminal,
and the bot account's Odoo rights keep it read-only.

- Write commands are for humans only: blocked outright for Claude. The shipped
  CLI has none, but older local copies may.
- The config folder holds the API key: Claude never reads it.
- Commands that print personal data unmasked or half-masked (`--raw`,
  `--regex-only`, `sanitizer.py --dry-run`) are blocked: the CLIs only run them
  in the user's own terminal.
"""
import json
import re
import sys

WRITE_CMDS = r"comment|create|set-stage|assign|set-pr|set-description|send-template"

data = json.load(sys.stdin)
cmd = (data.get("tool_input") or {}).get("command", "")

# The subcommand where argparse expects it, so `search "payment create"` passes.
if re.search(rf"""odoo_ticket\.py["']?(?:\s+--env(?:=|\s+)\S+|\s+--\S+)*\s+({WRITE_CMDS})\b""",
             cmd):
    print("Blocked: Odoo ticket writes are done by the user, not Claude. "
          "Hand them the command or text to run themselves.", file=sys.stderr)
    sys.exit(2)

if re.search(r"\.config/compassion-odoo|compassion-odoo/config", cmd):
    print("Blocked: this file holds the Odoo API key. To change it, the user runs "
          "`odoo_ticket.py setup` in their own terminal.", file=sys.stderr)
    sys.exit(2)

if (re.search(r"odoo_ticket\.py\b.*--(raw|regex-only)\b", cmd)
        or re.search(r"sanitizer\.py\b.*--(dry-run|regex-only)\b", cmd)):
    print("Blocked: unmasked or half-masked output only runs in the user's own "
          "terminal. Give them the command to run there.", file=sys.stderr)
    sys.exit(2)
