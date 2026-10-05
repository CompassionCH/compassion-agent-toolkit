---
name: setup
description: >-
  Install, check or repair the compassion-agent-toolkit on this machine: Node.js,
  the ctx7 CLI, the agent-browser CLI and its Chrome, and the developer's
  Context7 key. Use when the user asks to set up the toolkit, when the toolkit's
  session note reports something missing, or when find-docs or agent-browser
  fail on a missing tool.
---

# Toolkit setup

The bar for done: every row of the status table reads ✔, or reads ✘ with the reason the user chose to leave it. Show each install command and wait for a yes before running it; installs go through the user's own permission prompts, and system-level changes (sudo, the OS package manager) are run by the user.

## 1. Take stock

```bash
node --version; npm --version
command -v ctx7 >/dev/null && ctx7 --version || echo "ctx7: not on PATH"
agent-browser --version
[ -n "$CONTEXT7_API_KEY" ] && echo "key: set" || echo "key: unset"
```

Report a table: Node.js ≥ 18 · ctx7 · agent-browser · Chrome for agent-browser (proven in step 6) · Context7 key. The key row shows *set* or *unset*, never the value.

## 2. Node.js 18 or newer

Missing or older: the user installs it the way this machine manages software (distribution package, nvm, Homebrew on macOS). Machines differ, so lay out the options and let them choose. Resume at step 1 once `node --version` shows 18 or newer.

## 3. ctx7

Propose `npm install -g ctx7`. If npm answers `EACCES`, skip the global install: `npx ctx7@latest` runs it without installing, and find-docs already falls back to it.

Done when `ctx7 --version` or `npx ctx7@latest --version` prints a version.

## 4. agent-browser

Propose, in order:

```bash
npm install -g agent-browser
agent-browser install          # downloads Chrome for Testing
```

On Linux, when Chrome later fails to start over missing system libraries, the fix is `agent-browser install --with-deps`. It calls the system package manager and may need sudo, so the user runs it by typing `! agent-browser install --with-deps` in the prompt.

Done when the browser half of the smoke test (step 6) passes.

## 5. Context7 key

Unset: the user creates a free key at https://context7.com/dashboard and enters it in `/plugin` → **Installed** → compassion-agent-toolkit → **Configure options**, masked, stored in the OS keychain. A new session (`/exit`, then `claude`) exports it; the kit's SessionStart hook does that on every start.

That dialog is the only place for the key. A key pasted into the chat is burned: ask the user to revoke it on the dashboard and create a new one.

The key is optional: without one, Context7 answers at lower rate limits. Record the user's choice in the table.

## 6. Smoke test

```bash
ctx7 library odoo "stored computed fields"      # the results list /odoo/documentation
agent-browser open https://example.com && agent-browser get title && agent-browser close   # prints "Example Domain"
```

(`npx ctx7@latest` in place of `ctx7` when step 3 fell back to it.) A failure sends you back to the step that owns it.

## 7. Report

The final status table, then two lines on use:

- **find-docs**: ask any library or Odoo question; Claude looks it up, pinned to the repository's Odoo version.
- **agent-browser**: "open my local Odoo at `<url>` and check `<page>`"; Claude drives the browser and shows a screenshot.
