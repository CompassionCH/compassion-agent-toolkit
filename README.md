# compassion-agent-toolkit

Compassion Switzerland's shared toolkit for AI coding agents on our Odoo work.
Today it targets **Claude Code**, packaged as a Claude Code plugin marketplace.

It is minimal on purpose: two tools every developer benefits from, a guided
setup, an honest commit trailer, and a few organization-wide guardrails.
Everything else, each developer grows themselves, one annoyance at a time.

| In the toolkit | What it gives you |
|---|---|
| `find-docs` | Current docs for any library through Context7, and Odoo docs **pinned to your repository's version**, so the agent stops blending Odoo versions |
| `agent-browser` | The agent opens your local Odoo in a real Chrome to check its own work: screenshots, console errors, forms |
| `setup` | Installs and checks the two CLIs and your Context7 key, asking before each step |
| Commit trailer | Every commit the agent makes ends with `Assisted-by: <model id>, <effort>, <harness>` |

Deliberately not in it: anyone's personal skills, workflows or rules. The
toolkit is the common floor, not a copy of one person's setup.

---

## Install

**Prerequisites:** Claude Code, logged in with your organization's account;
Node.js 18 or newer; a free Context7 API key of your own from
<https://context7.com/dashboard> (optional, for higher rate limits).

### A. Automatic, once the workspace owner has enabled it (preferred)

The workspace owner adds the toolkit to the organization's managed settings
(see [For the workspace owner](#for-the-workspace-owner)). Your next Claude
Code session installs it by itself. Then:

1. `/plugin` → **Installed** → compassion-agent-toolkit → **Configure options**
   → paste your Context7 key (masked, stored in your OS keychain).
2. `/exit`, start `claude` again, and run `/compassion-agent-toolkit:setup`.

### B. By hand

In a Claude Code session:

```
/plugin marketplace add CompassionCH/compassion-agent-toolkit
/plugin install compassion-agent-toolkit@compassion
```

The install asks for your Context7 key. Then `/exit`, `claude`, and
`/compassion-agent-toolkit:setup`.

### C. Let your agent do it

Paste this into a new Claude Code session:

> Set me up with the compassion-agent-toolkit, following ONBOARDING.md from
> the CompassionCH/compassion-agent-toolkit repository.

[`ONBOARDING.md`](ONBOARDING.md) walks the agent through the same steps,
asking you before each one.

**Your key goes only in the Configure options dialog**, never in the chat. A
key pasted into a conversation is burned: revoke it on the dashboard and make
a new one.

---

## In an Odoo repository

Nothing to install per repository. Run `/init` once to draft a `CLAUDE.md`,
correct it, and put the Odoo version on line one: find-docs reads it to pin
the docs (it falls back to a module's `__manifest__.py`).

---

## The commit trailer

Every `git commit` the agent runs gets one trailer, for example:

```
Assisted-by: claude-opus-5-5, high, claude-code
```

It says AI helped while a human stays the author, in line with the OCA's AI
policy. A hook adds it, so it does not depend on the agent remembering, and
the values come from Claude Code rather than from the model's memory: the
model of the exact message that made the commit (a subagent's own model
included), and the effort level in effect, even after `/model` or `/effort`
mid-session. Claude Code's own `Co-Authored-By` line is switched off with
`"attribution": {"commit": ""}`, which the managed settings set (a plugin
cannot); without them, add it to your own `~/.claude/settings.json`.

The format is fixed for analytics: `<model id>, <effort>, <harness>`, with
the raw API model id (`claude-opus-5-5`, `claude-haiku-4-5-20251001`) and
`unknown` for a value Claude Code did not record. To count them:

```bash
git log --since=2026-01-01 --format='%(trailers:key=Assisted-by,valueonly,separator=)' \
  | grep . | sort | uniq -c | sort -rn
```

Cost: nothing in context; the hook starts only for a
command containing `git commit` (Claude Code 2.1.85+; older versions start it
for every command and it exits at once), and it never blocks a commit. It
covers commits the agent makes, not ones a person types.

---

## For the workspace owner

Server-managed settings need the **Owner** role: claude.ai →
**Admin settings → Claude Code → Managed settings**. Paste
[`admin/managed-settings.json`](admin/managed-settings.json). It:

- registers this marketplace and installs `compassion-agent-toolkit` for
  everyone, kept up to date;
- **denies** reading credentials on every machine: `odoo.conf`, `.odoorc`,
  `~/.pgpass`, `.env`, `.env.*`;
- **denies** force-pushes (`--force`, `-f`, `+branch`): they can overwrite
  teammates' work on the remote. Plain pushes are allowed;
- **asks first** before dropping a database or a table (`dropdb`, `DROP`),
  upgrading or installing an Odoo module (`odoo-bin -u` / `-i`), and any
  `psql`;
- switches off Claude Code's `Co-Authored-By` commit line, so only the
  toolkit's `Assisted-by:` remains.

Everything else stays each developer's choice, bypass-permissions mode
included (for a disposable VM or container).

Rules match the command as the agent writes it: they are guardrails, not a
vault. The real boundary stays the environment: no production credentials on
development machines, and anonymized databases (Odoo's neutralize is not
anonymization). Server-managed settings are also a client-side control: on an
unmanaged laptop a user can bypass them.

---

## Feedback to Anthropic

Feedback is welcome, and it has a cost worth knowing: `/feedback` in Claude
Code, and thumbs up or down on claude.ai, send **the whole conversation** to
Anthropic, kept for up to 5 years. Before sending, make sure the session holds
no personal data, credentials or confidential code.

---

## Update and remove

- **Update**: with auto-update on, Claude Code checks this marketplace when a
  session starts and downloads a newer version in the background. The open
  session keeps the version it loaded and shows `Plugin updated · Run
  /reload-plugins to apply`; the next session loads it on its own. Auto-update
  is off by default for marketplaces outside Anthropic's own: the managed
  settings turn it on (`autoUpdate: true`). A
  developer who installed by hand turns it on in `/plugin` → **Marketplaces**
  → compassion → **Enable auto-update**, or updates now with
  `claude plugin update compassion-agent-toolkit@compassion`.
- **Remove**: `/plugin` → **Installed** → compassion-agent-toolkit →
  **Uninstall** (a managed install can only be removed by the owner).

## Maintaining the toolkit

```bash
claude plugin validate .                                   # the marketplace
claude plugin validate ./plugins/compassion-agent-toolkit  # the plugin
```

**Releasing a change = bump `version` and push.** Claude Code keeps every
install on the `version` in `plugins/compassion-agent-toolkit/.claude-plugin/plugin.json`
until it changes: a push without a new version reaches no one. Changes to
`admin/managed-settings.json` reach people only once the workspace owner
pastes the new version. Before announcing a change, install it on one machine
with
`claude --plugin-dir ./plugins/compassion-agent-toolkit` and run
`/compassion-agent-toolkit:setup`.

## License

MIT, see [LICENSE](LICENSE).
