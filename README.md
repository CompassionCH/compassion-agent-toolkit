# compassion-agent-toolkit

Compassion Switzerland's shared setup for AI coding agents on our Odoo work,
for **Claude Code**. Two layers:

1. **Guardrails, enforced for everyone** through managed settings: no reading
   credentials, no force-push, ask before dropping a database or upgrading a
   module.
2. **Optional plugins** in the `compassion` marketplace, visible in `/plugin` →
   **Discover**. Install all, some or none; remove any whenever you like.

| Plugin | What it gives you |
|---|---|
| `compassion-bundler` | All the Compassion plugins in one install |
| `find-docs` | Current docs for any library through Context7, and Odoo docs **pinned to your repository's version** |
| `agent-browser` | The agent checks its work in your local Odoo through a real Chrome: screenshots, console errors, forms |
| `assisted-by` | Every commit the agent makes ends with `Assisted-by: <model id>, <effort>, <harness>` |

The catalog is a common floor, not anyone's personal setup.

## Install

You need Claude Code logged in with the organization's account, and Node.js
18+ for `find-docs` and `agent-browser`.

- **Everything:** `/plugin install compassion-bundler@compassion`
- **Only what you want:** pick in `/plugin` → **Discover**, or
  `/plugin install <plugin>@compassion`
- **Let your agent do it:** in a new session, say *"Set me up with the
  compassion-agent-toolkit, following ONBOARDING.md from the
  CompassionCH/compassion-agent-toolkit repository."*

Then restart `claude`. The first time the agent uses `agent-browser`, it
offers to install the CLI and its Chrome.

No `compassion` marketplace in `/plugin` (a machine without the
organization's settings)? Add it with
`/plugin marketplace add CompassionCH/compassion-agent-toolkit` and turn on
**Enable auto-update** for it under `/plugin` → **Marketplaces**.

## Updates and changes

- **Updates are automatic.** Claude Code fetches new versions when a session
  starts, and the next session loads them (or run `/reload-plugins`).
- **With the bundler, new plugins arrive on their own.** When a plugin joins
  the catalog, the bundler's update installs it; nothing to do. If you picked
  plugins one by one, install new ones from **Discover** when you want them.
- **Remove or pause a plugin:** `/plugin` → **Installed** → **Uninstall** or
  **Disable**. The bundler's plugins stay on together: to drop one, uninstall
  the bundler first (its plugins stay installed), then the one you don't
  want.
- **For a whole repository:** `claude plugin install <plugin>@compassion
  --scope project`, then commit `.claude/settings.json`. Everyone opening the
  repository is offered the plugin.

## In an Odoo repository

Put the Odoo version on line one of the repository's `CLAUDE.md` (draft one
with `/init`) or `AGENTS.md`, plus your local Odoo URL. `find-docs` pins the
docs to that version, and `agent-browser` uses that URL.

## find-docs and Context7

Context7 works without an account, at lower rate limits. For higher ones, run
`npx ctx7@latest login` once in a terminal, or set `CONTEXT7_API_KEY`. Never
paste a key into the chat; if you do, revoke it and make a new one.
`ctx7 setup` would install Context7's generic `find-docs` too: keep one,
ideally this one, which pins Odoo versions.

## The commit trailer

With `assisted-by`, every commit the agent makes ends with, for example:

```
Assisted-by: claude-opus-5-5, high, claude-code
```

It says AI helped while a human stays the author, in line with the OCA's AI
policy. A hook adds it from what Claude Code records, so it never depends on
the agent remembering, and skips commits that already have one. It costs
nothing in context and never blocks a commit. Unknown values read `unknown`.
To count them:

```bash
git log --format='%(trailers:key=Assisted-by,valueonly,separator=)' | grep . | sort | uniq -c
```

## For the workspace owner

Paste [`admin/managed-settings.json`](admin/managed-settings.json) in claude.ai
→ **Admin settings → Claude Code → Managed settings** (Owner role). It:

- registers the `compassion` marketplace with auto-update, installing no
  plugin;
- blocks the retired all-in-one `compassion-agent-toolkit` plugin (0.3 and
  earlier);
- **denies** reading credentials: `odoo.conf`, `.odoorc`, `~/.pgpass`, `.env*`,
  private SSH keys, `*.pem`, `*.key`;
- **denies** force-pushes; plain pushes stay allowed;
- **asks first** before `dropdb`, `DROP DATABASE/TABLE`, `odoo-bin -u/-i` and
  `psql`;
- switches off Claude Code's `Co-Authored-By` line.

These rules are guardrails, not a vault: keep production credentials off
development machines and use anonymized databases (Odoo's neutralize is not
anonymization).

## Coming from toolkit 0.3

The single `compassion-agent-toolkit` plugin is retired. Install
`compassion-bundler` to get the same tools back, and run
`npx ctx7@latest login`: the Context7 key from the old plugin's options is no
longer used.

## Feedback to Anthropic

`/feedback`, and thumbs up or down on claude.ai, send **the whole
conversation** to Anthropic, kept up to 5 years. Check it holds no personal
data, credentials or confidential code first.

## Maintaining the catalog

```bash
claude plugin validate .                                  # the marketplace
for p in plugins/*/; do claude plugin validate "$p"; done # each plugin
claude --plugin-dir ./plugins                             # try them locally
```

**Releasing = bump that plugin's `version` and push.** Without a new version,
nobody receives the change. Changes to `admin/managed-settings.json` apply
once the workspace owner pastes them.

**Adding a plugin:**

1. Create `plugins/<name>/.claude-plugin/plugin.json` (`name`, `version`, a
   one-line `description`), with its skills or hooks beside it.
2. Add it to `.claude-plugin/marketplace.json`: `source: "./plugins/<name>"`.
3. Add it to `compassion-bundler`'s `dependencies` **and bump the bundler's
   version**, or bundler users never receive it.
4. Add a row to the table above.

One job per plugin, each useful on its own.

## License

MIT, see [LICENSE](LICENSE).
