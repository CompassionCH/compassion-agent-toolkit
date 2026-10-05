Odoo {{VERSION}}. {{One line: what this repository holds and who uses it.}}

## Layout
- Addons: {{addon folders}}. Odoo core and third-party addons live elsewhere: read them, change them only through our own modules.
- Any addon can `_inherit` a model, so before changing a model, search every addon path for its other overrides.

## Run
- Tests: `odoo-bin -d <db> --test-tags /<module> --stop-after-init`
- Upgrading a module (`-u`) asks first: the team's settings make it an ask rule.
- How Odoo starts on your machine (paths, port, database name) goes in `CLAUDE.local.md`, which stays out of git.

## Conventions
- {{Views: `<list>`, not `<tree>`; `invisible="…"` expressions, not `attrs`. (Odoo 17+; adapt for older versions.)}}
- Commit messages: `[FIX] module: what changed` (OCA style). Claude may commit on a branch; a hook adds the `Assisted-by:` trailer, so add none yourself. Push the branch when asked; never force-push.
- Framework and library questions go through find-docs, pinned to Odoo {{VERSION}}.

## Data
- Work on an anonymized dev database: Odoo's neutralize switches off mail and crons but keeps every name. Production databases and servers are out of scope for every session.
- Credentials (`odoo.conf`, `.odoorc`, `~/.pgpass`, `.env`) stay unread: the team's deny rules enforce it.
