# Onboarding: Claude Code at Compassion Switzerland IT

You are setting up Claude Code for a developer on Compassion Switzerland's IT
team, who works on Odoo. Take the steps in order. After each one, tell them in
one line what happened. Ask before installing anything or changing a settings
file. Commands that need their own terminal or a browser, they run themselves:
they can type `! <command>` in the prompt to run one in this session.

Done when every try in step 7 that matches what they installed works, or the
developer has chosen to stop.

## 1. Check the basics

- `claude --version` runs, and the session is logged in with the Compassion
  Team account (the developer can check with `/status`; `/login` switches
  account).
- `node --version` shows 18 or newer; `find-docs` and `agent-browser` need it.
  Older or missing: the developer installs Node.js the way their machine
  manages software; offer the usual options (distribution package, nvm,
  Homebrew on macOS) and let them choose.

## 2. The marketplace

```bash
claude plugin marketplace list
```

`compassion` listed: the organization's settings brought it; go on. Not
listed: the developer adds it with
`/plugin marketplace add CompassionCH/compassion-agent-toolkit`, then turns on
its updates in `/plugin` → **Marketplaces** → compassion → **Enable
auto-update**.

## 3. Choose the plugins

Show them the catalog and ask which they want:

- **compassion-bundler**: all the Compassion plugins, in one install
- **find-docs**: current library docs through Context7, Odoo docs pinned to
  the repository's version
- **agent-browser**: the agent checks their local Odoo in a real Chrome
- **assisted-by**: an `Assisted-by:` trailer on every commit the agent makes

Tell them the one trade-off of the bundler: while it is installed, its
plugins stay on together; picking plugins one by one keeps each removable on
its own. With their yes, install their choice, for example:

```bash
claude plugin install compassion-bundler@compassion
```

If they ran `ctx7 setup` before, they already have Context7's generic
`find-docs` skill: `find-docs` from the catalog adds Odoo pinning, and one of
the two is enough. Let them choose.

Then they restart: `/exit`, then `claude`.

## 4. Context7 login (with find-docs, optional)

Context7 works without an account, at lower rate limits. For higher ones, the
developer runs `! npx ctx7@latest login` and opens the link it shows. A key
must never be pasted into this chat: if one shows up, ask them to revoke it at
<https://context7.com/dashboard> and make a new one.

## 5. The agent-browser CLI (with agent-browser)

With their yes:

```bash
npm install -g agent-browser
agent-browser install          # downloads Chrome for Testing
```

When npm answers `EACCES`, they fix their npm prefix or Node install the way
their machine manages software; no sudo. On Linux, when Chrome fails to start
over missing system libraries, they run
`! agent-browser install --with-deps` themselves (it may need sudo).

## 6. Their Odoo repository

In the repository they work on, with Claude Code started there:

- no `CLAUDE.md` (or `AGENTS.md`) yet → `/init`, then correct the draft
  together. **The Odoo version goes on line one**: find-docs reads it to pin
  the docs. Add their local Odoo URL, for agent-browser.

## 7. Try it

- find-docs: "What does a stored computed field need in `@api.depends`, in
  Odoo `<their version>`?" → answered from the pinned docs.
- agent-browser: "Open `<their local Odoo URL>`/web/login and take a
  screenshot." → the page shows.
- assisted-by: in a scratch repository, ask for a commit, then
  `git log -1 --format=%B` ends with `Assisted-by: …`.

Close with the three habits: read every diff as if a colleague wrote it; give
Claude a way to check itself (a test, the browser, the Odoo log); one task per
session, `/clear` between tickets.

One thing to tell them about feedback: `/feedback`, and thumbs up or down on
claude.ai, send the whole conversation to Anthropic, kept for up to 5 years.
Feedback is welcome; check the session holds no personal data or secrets
first.
