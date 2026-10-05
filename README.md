# compassion-agent-toolkit

Compassion Switzerland's shared setup for AI coding agents on our Odoo work.
Today it targets **Claude Code**.

It has two layers:

1. **Guardrails, enforced for everyone.** A few organization-wide rules in
   Claude Code's managed settings: no reading credentials, no force-push, ask
   before dropping a database or upgrading a module. They cost nothing in the
   agent's context.
2. **A catalog of optional plugins.** The `compassion` plugin marketplace,
   visible to everyone in `/plugin` → **Discover**. Install all of it, some of
   it or none of it; disable or remove a plugin whenever you like.

| Plugin | What it gives you |
|---|---|
| `compassion-starter` | The whole catalog below in one install |
| `find-docs` | Current docs for any library through Context7, and Odoo docs **pinned to your repository's version**, so the agent stops blending Odoo versions |
| `agent-browser` | The agent opens your local Odoo in a real Chrome to check its own work: screenshots, console errors, forms |
| `assisted-by` | Every commit the agent makes ends with `Assisted-by: <model id>, <effort>, <harness>` |

Deliberately not in it: anyone's personal skills, workflows or rules. The
catalog is a common floor, not a copy of one person's setup. Everything else,
each developer grows themselves, one annoyance at a time.

---

## Install

**Prerequisites:** Claude Code, logged in with your organization's account.
`find-docs` and `agent-browser` also need Node.js 18 or newer.

### Everything at once

```
/plugin install compassion-starter@compassion
```

This installs and enables `find-docs`, `agent-browser` and `assisted-by`.
While the starter is installed, its plugins stay on together: to drop one of
them, uninstall `compassion-starter` first (the plugins it brought stay
installed), then disable or uninstall the one you don't want.

### Only what you want

`/plugin` → **Discover** → pick from the `compassion` marketplace, or:

```
/plugin install find-docs@compassion
/plugin install agent-browser@compassion
/plugin install assisted-by@compassion
```

Then `/exit` and start `claude` again. The first time the agent uses
`agent-browser`, it offers to install the CLI and its Chrome, asking before
each step.

### Let your agent do it

Paste this into a new Claude Code session:

> Set me up with the compassion-agent-toolkit, following ONBOARDING.md from
> the CompassionCH/compassion-agent-toolkit repository.

[`ONBOARDING.md`](ONBOARDING.md) walks the agent through the same steps,
asking you before each one.

### On a machine without the organization's settings

The marketplace comes with the managed settings. Without them, add it once:

```
/plugin marketplace add CompassionCH/compassion-agent-toolkit
```

and turn on its updates: `/plugin` → **Marketplaces** → compassion →
**Enable auto-update**.

### For a whole repository

`claude plugin install <plugin>@compassion --scope project` records the plugin
in that repository's `.claude/settings.json`. Commit it, and everyone who
opens the repository in Claude Code is offered the plugin. Each person can
still disable it for themselves.

### Disable or remove

`/plugin` → **Installed** → the plugin → **Disable** or **Uninstall**, or
`claude plugin disable <plugin>@compassion`. After uninstalling the starter,
`claude plugin prune` removes the plugins it brought that nothing else uses.

---

## In an Odoo repository

Nothing to install per repository. Run `/init` once to draft a `CLAUDE.md`,
correct it, and put the Odoo version on line one: `find-docs` reads it to pin
the docs. A repository that already has an `AGENTS.md` can keep it instead,
with the version on line one; without either, `find-docs` falls back to a
module's `__manifest__.py`. Write your local Odoo URL there too
(`http://localhost:8069` or your own port), for `agent-browser`.

---

## Context7, for find-docs

Context7 works without an account, at lower rate limits. For higher ones,
log in once in a terminal:

```bash
npx ctx7@latest login
```

It shows a link and a short code to open in any browser, and keeps the login
on the machine. A `CONTEXT7_API_KEY` in your environment works too (free key
at <https://context7.com/dashboard>). Never paste a key into the chat: a key
that reached a conversation is burned; revoke it and make a new one.

`ctx7 setup` installs Context7's own generic `find-docs` skill. You don't need
both: that one has no Odoo pinning, this one does.

---

## The commit trailer

With `assisted-by` installed, every `git commit` the agent runs gets one
trailer, for example:

```
Assisted-by: claude-opus-5-5, high, claude-code
```

It says AI helped while a human stays the author, in line with the OCA's AI
policy. A hook adds it, so it does not depend on the agent remembering, and
the values come from Claude Code rather than from the model's memory: the
model of the exact message that made the commit (a subagent's own model
included), and the effort level in effect, even after `/model` or `/effort`
mid-session. A commit that already carries an `Assisted-by:` trailer is left
as it is. Claude Code's own `Co-Authored-By` line is switched off with
`"attribution": {"commit": ""}`, which the managed settings set; without
them, add it to your own `~/.claude/settings.json`.

The format is fixed for analytics: `<model id>, <effort>, <harness>`, with
the raw API model id (`claude-opus-5-5`, `claude-haiku-4-5-20251001`) and
`unknown` for a value Claude Code did not record. To count them:

```bash
git log --since=2026-01-01 --format='%(trailers:key=Assisted-by,valueonly,separator=)' \
  | grep . | sort | uniq -c | sort -rn
```

Cost: nothing in context; the hook starts only for a command containing
`git commit` (Claude Code 2.1.85+; older versions start it for every command
and it exits at once), and it never blocks a commit. It covers commits the
agent makes, not ones a person types. Don't want it? Disable or uninstall
`assisted-by`.

---

## For the workspace owner

Server-managed settings need the **Owner** role: claude.ai →
**Admin settings → Claude Code → Managed settings**. Paste
[`admin/managed-settings.json`](admin/managed-settings.json). It:

- registers the `compassion` marketplace for everyone, with auto-update on,
  and installs **no** plugin: each developer chooses;
- blocks the retired all-in-one plugin `compassion-agent-toolkit` (toolkit
  0.3 and earlier), so it stops loading on machines that still have it;
- **denies** reading credentials on every machine: `odoo.conf`, `.odoorc`,
  `~/.pgpass`, `.env`, `.env.*`, and private keys (`~/.ssh/id_*` without
  `.pub`, `*.pem`, `*.key`). `~/.ssh/config` and public keys stay readable;
  a key with a custom name needs its own rule;
- **denies** force-pushes (`--force`, `-f`, `+branch`): they can overwrite
  teammates' work on the remote. Plain pushes are allowed;
- **asks first** before dropping a database or a table (`dropdb`, `DROP`),
  upgrading or installing an Odoo module (`odoo-bin -u` / `-i`), and any
  `psql`;
- switches off Claude Code's `Co-Authored-By` commit line, so only the
  `Assisted-by:` trailer remains for those who use it.

Everything else stays each developer's choice, bypass-permissions mode
included (for a disposable VM or container).

Rules match the command as the agent writes it: they are guardrails, not a
vault. The real boundary stays the environment: no production credentials on
development machines, and anonymized databases (Odoo's neutralize is not
anonymization). Server-managed settings are also a client-side control: on an
unmanaged laptop a user can bypass them.

---

## Coming from toolkit 0.3

Toolkit 0.3 was one plugin, `compassion-agent-toolkit`, installed for
everyone. It is retired and blocked by the managed settings. To get the same
tools back, install `compassion-starter`, or the plugins you want, as above.
The Context7 key you entered in that plugin's **Configure options** is no
longer used: run `npx ctx7@latest login` instead.

---

## Feedback to Anthropic

Feedback is welcome, and it has a cost worth knowing: `/feedback` in Claude
Code, and thumbs up or down on claude.ai, send **the whole conversation** to
Anthropic, kept for up to 5 years. Before sending, make sure the session holds
no personal data, credentials or confidential code.

---

## Updates

With auto-update on, Claude Code checks this marketplace when a session starts
and downloads newer plugin versions in the background. The open session keeps
the version it loaded and shows `Plugin updated · Run /reload-plugins to
apply`; the next session loads it on its own. To update now:
`claude plugin update <plugin>@compassion`.

## Maintaining the catalog

```bash
claude plugin validate .                     # the marketplace
for p in plugins/*/; do claude plugin validate "$p"; done
claude --plugin-dir ./plugins                # try every plugin locally
```

**Releasing a change = bump that plugin's `version` and push.** Claude Code
keeps every install on the `version` in the plugin's
`.claude-plugin/plugin.json` until it changes: a push without a new version
reaches no one. Each plugin has its own version. Changes to
`admin/managed-settings.json` reach people only once the workspace owner
pastes the new version. Before announcing a change, try it locally with
`--plugin-dir` as above.

**Adding a plugin to the catalog:**

1. `plugins/<name>/.claude-plugin/plugin.json`, with `name`, `version` and a
   one-line `description`, plus its skills, hooks or agents beside it.
2. An entry in `.claude-plugin/marketplace.json`, `source: "./plugins/<name>"`.
3. Add `<name>` to `compassion-starter`'s `dependencies` and bump the
   starter's version, when everyone benefits from it.
4. A row in the table at the top of this README.

One job per plugin, and each one useful on its own: that is what lets people
pick.

## License

MIT, see [LICENSE](LICENSE).
