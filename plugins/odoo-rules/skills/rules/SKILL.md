---
name: rules
description: >-
  Use in Compassion Odoo repositories when changing or reviewing ACLs, record
  rules, public routes or RPC methods, transactional side effects, payment
  provider outcomes, integration settings on neutralized database copies, or
  translatable strings and catalogs.
---

# Odoo rules

Open the subject that matches the change. The local rule directory for the reviewer is `${CLAUDE_SKILL_DIR}`, the directory containing this file.

- [Security](security.md) for client-supplied values, privileged writes, RPC exposure, ACLs and record rules.
- [Side effects](side-effects.md) for savepoints, pending provider transactions, staff follow-up and neutralizing integrations on database copies.
- [Translations](translations.md) for new or changed strings, first catalogs and browser translations.

Use `code-rules:rules` for the shared coding and pre-PR rules.
