---
name: agent-browser
description: >-
  Drive a real Chrome through the agent-browser CLI to verify, test or debug a
  running web app, especially a local Odoo: load a page, screenshot it, read
  the accessibility tree, fill a form, catch console errors. Use to reproduce
  a UI bug, to read a JS-driven page, and to prove a fix on the page the user
  actually sees.
---

# Browser checks with agent-browser

The `agent-browser` CLI (vercel-labs) controls Chrome over the DevTools Protocol. It renders what a plain fetch cannot: Odoo's web client, portal pages, wizards, OWL components.

Scope: local and dev instances only, with the dev database's test login. Production URLs and real accounts stay outside every session.

## Prerequisite

```bash
agent-browser --version
```

Missing, or Chrome fails to start: offer `/compassion-agent-toolkit:setup`, which installs and checks it.

## Core workflow

**open → snapshot → act → verify → close**

1. Open: `agent-browser open http://localhost:8069/web/login`
2. Snapshot, to get stable element refs (`@e1`, `@e2`, …): `agent-browser snapshot -i --json`
3. Act on those refs: `agent-browser click @e3`, `agent-browser fill @e5 "text"`
4. Verify: `agent-browser get text @e7`, `agent-browser screenshot /tmp/result.png`, `agent-browser console`, `agent-browser errors`
5. Close: `agent-browser close`

Refs come from the snapshot of the page as it is now: take a fresh snapshot after every navigation, and act on its refs rather than on guessed CSS selectors.

The port (`8069` above) is a stand-in: each machine runs Odoo on its own host and port, written in the repo's `CLAUDE.md` or `CLAUDE.local.md`.

Full command reference, straight from the installed CLI: `agent-browser skills get core --full`.

## Batches and sessions

For a multi-step flow, one `batch` saves round-trips. A named `--session` keeps the login cookies between commands:

```bash
agent-browser --session odoo batch \
  "open http://localhost:8069/web/login" \
  "snapshot -i --json"
# read the refs, then:
agent-browser --session odoo batch \
  "fill @e1 <dev login>" \
  "fill @e2 <dev password>" \
  "click @e3" \
  "wait --load load" \
  "open http://localhost:8069/odoo/contacts" \
  "wait --text \"Contacts\"" \
  "screenshot /tmp/contacts.png"
```

Wait on something the page shows (`--text`, `--url`) or on `--load load`. `--load networkidle` waits for a quiet network, so keep it for pages known to go quiet.

## Odoo checks worth knowing

- **Console errors**: after opening a view or running a wizard, read `agent-browser console` and `agent-browser errors`. OWL and wizard errors often never reach the server log; report any non-empty output.
- **Proof of a fix**: open the page the user sees (form, list, portal page) and show the value that was wrong. A screenshot is the evidence.

## Cleanup

Every workflow ends with `close`, by session name when you opened one (`agent-browser --session odoo close`). A forgotten browser holds RAM and a Chrome lock.
