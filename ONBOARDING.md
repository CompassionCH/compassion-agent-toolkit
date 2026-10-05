# Onboarding: Claude Code at Compassion Switzerland IT

You are setting up Claude Code for a developer on Compassion Switzerland's IT
team, who works on Odoo. Take the steps in order. After each one, tell them in
one line what happened. Ask before installing anything or changing a settings
file, and leave slash commands to them: those they type themselves.

Done when both tries in step 5 work, or the developer has chosen to stop.

## 1. Check the basics

- `claude --version` runs, and the session is logged in with the Compassion
  Team account (the developer can check with `/status`; `/login` switches
  account).
- `node --version` shows 18 or newer. Older or missing: the developer
  installs Node.js the way their machine manages software; offer the usual
  options (distribution package, nvm, Homebrew on macOS) and let them choose.

## 2. Add the toolkit

If `/plugin` already lists **compassion-agent-toolkit** (the workspace owner can
install it for everyone), skip to the key. Otherwise the developer types:

```
/plugin marketplace add CompassionCH/compassion-agent-toolkit
/plugin install compassion-agent-toolkit@compassion
```

**The Context7 key.** The developer creates a free key at
<https://context7.com/dashboard> and enters it in the plugin's dialog, or later
in `/plugin` → **Installed** → compassion-agent-toolkit → **Configure options**. The key
is masked and kept in their OS keychain. That dialog is its only place: if a
key shows up in this chat, ask them to revoke it and create a new one.

Then they restart: `/exit`, then `claude`.

## 3. Run the toolkit's setup

The developer runs `/compassion-agent-toolkit:setup`. It installs and checks `ctx7` and
`agent-browser`, confirms the key reached the session, and runs a smoke test.

## 4. Their Odoo repository

In the repository they work on, with Claude Code started there:

- no `CLAUDE.md` yet → `/init`, then correct the draft together. **The Odoo
  version goes on line one**: find-docs reads it to pin the docs.
- `.claude/settings.json` without the team rules → point them to the
  repository's maintainer, who runs `/compassion-agent-toolkit:repo-setup` once for
  everyone.

## 5. Try it

- "What does a stored computed field need in `@api.depends`, in Odoo
  `<their version>`?" → find-docs answers from the pinned docs.
- "Open `<their local Odoo URL>`/web/login and take a screenshot." →
  agent-browser shows the page.

Close with the three habits: read every diff as if a colleague wrote it; give
Claude a way to check itself (a test, the browser, the Odoo log); one task per
session, `/clear` between tickets.
