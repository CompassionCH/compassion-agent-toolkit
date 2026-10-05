---
name: find-docs
description: >-
  Current documentation and code examples for any library, framework, SDK, CLI
  or cloud service, through the Context7 CLI. Use for API syntax,
  configuration, version migration and library-specific debugging, and for
  Odoo framework questions, pinned to the repository's Odoo version. Training
  data is stale: look it up even when the answer seems known.
---

# Documentation lookup

## Command form

Resolve once per session:

```bash
command -v ctx7 >/dev/null && echo "use: ctx7" || echo "use: npx ctx7@latest"
```

Examples below use `ctx7`; write `npx ctx7@latest` instead when it is not on PATH. When neither runs, the machine is not set up yet: offer `/compassion-agent-toolkit:setup`.

## Workflow

1. Resolve the library to an ID: `ctx7 library <name> "<question>"`
2. Query it: `ctx7 docs <libraryId> "<question>"`

Step 1 is skippable only when the user hands you an ID (`/org/project` or `/org/project/version`). Budget: three commands per question, then answer from the best result and say it was the best available.

### Picking a library

Weigh name match, description, code-snippet count, source reputation (High / Medium first) and benchmark score (100 is best). When the user names a version, use the matching entry from the result's **Versions** list, as `/org/project/<version>`. Two good matches: say so and take the more relevant. No good match: say so and suggest a better query.

### Writing the query

The query ranks the results, so write it in the user's own words, one concept per query: `"React useEffect cleanup with async operations"`, not `"hooks"`. Several concepts means several `docs` calls, unless the question is how they interact. Queries leave the machine: keep them free of secrets, credentials, personal data and proprietary code.

## Odoo

Odoo's API moves between versions and the model's memory blends them, so every Odoo lookup is **pinned** to the repository's version. Read the version from line one of the repo's `CLAUDE.md` (team convention) or from a `__manifest__.py` `version` (`18.0.1.0.0` → 18.0), then:

| Repository | Where to look |
|---|---|
| 18.0 | `ctx7 docs /odoo/documentation/__branch__18.0 "<question>"`; framework source: `/odoo/odoo/__branch__18.0` |
| 19.0 | framework source: `/odoo/odoo/__branch__19.0` |
| 14.0 – 17.0 | Context7 indexes nothing for these: read the local Odoo source of that version (`odoo/fields.py`, `odoo/models.py`, the addon's own code) |

An unpinned Odoo ID serves the newest branch, which is why the pin is part of every Odoo query.

## Authentication

The toolkit supplies the developer's own key: Claude Code keeps the plugin option `context7_api_key` in the OS keychain, and the toolkit's SessionStart hook exports it as `CONTEXT7_API_KEY` for the session. Check its state without printing it:

```bash
[ -n "$CONTEXT7_API_KEY" ] && echo "key: set" || echo "key: unset"
```

Unset still works, at lower rate limits. To add a key: a free one at https://context7.com/dashboard, entered in `/plugin` → **Installed** → compassion-agent-toolkit → **Configure options**, then a new session. That dialog is the only place for the key; a key pasted into the chat is burned, so ask the user to revoke it on the dashboard and make a new one.

## Errors

A quota error ("Monthly quota reached", "quota exceeded"): tell the user, then check the key state (above) and `ctx7 whoami`. No key and no login → point them to **Configure options**; either present → that account's quota is spent. If they can't authenticate, answer from training knowledge, labelled as possibly outdated. Whenever Context7 was not used, say why.

`ctx7 setup` replaces this skill with Context7's generic one; leave running it to the user.

## Common mistakes

- IDs start with `/`: `/facebook/react`, not `facebook/react`
- `ctx7 docs react "hooks"` fails: resolve the ID with `ctx7 library` first
