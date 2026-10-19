# Fixing communication templates with the `odoo-communication-fix` skill

Guide for a developer who takes over a "fix the communications" ticket (same kind of work as T3527). It explains what the skill does, what you must provide, the working loop and how to finish.

## 1. What the work is

The e-mails and SMS of the sponsorship communications are `mail.template` records written in QWeb, in four languages (English source, `fr_CH`, `de_DE`, `it_IT`). After the v14 to v18 migration many of them are wrong: leftover Jinja, variables that do not exist, broken dates, wrong links, texts that differ between languages. The texts live in the **database**; the source XML and the `.po` files are out of date. The skill's job is to:

1. clean each text and propose improvements that **you** accept or refuse,
2. write the accepted text back to the database you work on,
3. copy the database state to the source code (English XML) and to the `.po` files,
4. add migrations so that existing databases receive the corrected texts,
5. commit, push and open draft pull requests.

The database is the source of truth: the developer corrects there, the code follows.

## 2. Before you start: what you provide

The skill asks for these values and never reuses the ones of a previous task.

| Value | Example | Notes |
|---|---|---|
| Ticket number | `T3527` | first in the commit messages and the PR |
| Database | `swiss18` | a copy you can write to, never production |
| Branch | `T3527-fix-communication-rules` | one per repo; feature branch, not `18.0` |
| Repos | `compassion-modules`, `compassion-website`, `compassion-switzerland` | under `~/Dev/18-addons/` |
| Templates | `56` B2S New letter, `449` B2S Final Letter, ... | ids given one by one |
| Scratch file | a PyCharm scratch `.html` | the working copy you edit |

Check first: git is clean on `18.0` in every repo, Odoo 18 and `psql` access to the database work, `pre-commit`, `polib`, `psycopg2`, `lxml` and `gh` (SSH) are installed.

Install the plugin (`/plugin install odoo-communication-fix@compassion`, or the bundler), then start the skill by typing `/odoo-communication-fix` in Claude Code. `$SKILL` below is the skill folder (`scripts/`, `templates/`, `reference/`).

## 3. The loop for one template, one language

1. **Load**: the skill copies the database text of the language into your scratch file and keeps a backup.
2. **Automatic cleanup** (no decision needed): unused variables, inline styles (except buttons), wrapper `div`/`span`, `<p t-out>` shorthand, signature only in digital mode, short language codes in website links, the `urls` list fix. It lists what it changed.
3. **Proposals**: a numbered list of improvements (guards for empty values, several children, wording, links, physical-only sentences, hardcoded numbers...). You answer with the numbers you accept (for example "1,2,4,6"). Nothing is applied that you did not choose. A question in the list is not an action; say what you want.
4. **Review**: the skill checks the XML and shows what was applied and what was left. Read the scratch file, edit it if you want.
5. **Push to the database**: only after your "yes". The skill writes that language with `jsonb_set` and keeps the previous value in a backup file.
6. Repeat for the next language, then the next template. Start with the language you know best; keep the four languages saying the same thing.

Test in Odoo: preview the communication, or use the "Change text" and "Refresh" actions of a communication job. The skill asks your permission before running Odoo or any test.

## 4. The rules to know

All the rules are in `reference/rules.md`. The ones that surprise people:

- The signature is shown **only** when `send_mode == 'digital'` (not in physical letters, not in SMS). The contact lines of an SMS stay.
- German has **no comma** after the salutation.
- Website links use `/fr/`, `/de/`, `/it/`, never `fr_CH` / `de_DE` / `it_IT`.
- `get_date` takes a Babel pattern (`d. MMMM`, `d MMMM`, `MMMM d`); the old keys `date_month` / `date_full` print garbage.
- Exit templates show the poverty paragraph only for `sds_state` `sub` or `sub_waiting`.
- Glossary: *Patenschaft* (de), *sostegno* only (it), *parrainage* (fr).
- Gender and agreement lookups (`child.get('he')`...) are accepted; do not touch or discuss them.

## 5. Sync to the code

1. Write `templates.json` (see `templates/templates.example.json`): template id, module, xmlid, XML file, `i18n` folder.
2. Dry run, then real run:
   ```
   python3 $SKILL/scripts/sync_to_code.py --db <DB> --config templates.json --dry-run
   python3 $SKILL/scripts/sync_to_code.py --db <DB> --config templates.json
   ```
   Add `--create-missing` for a template that has no record in the XML yet (a template imported by hand has the xmlid `__import__.NN`).
3. Point the matching `partner.communication.config` record at the new xmlid.
4. Check: the XML bodies equal the database bodies (ignoring whitespace), the `.po` entries equal the database, `pre-commit run --files <files>` passes in each repo (a new `.po` entry needs `#. module: <module>`).

## 6. Migrations

The data files are `noupdate="1"`: an update does not change existing databases. Add, in each module you changed, `migrations/<version>/pre-migration.py` from `templates/` and raise the manifest version **above** the database's `latest_version`:

- `pre-migration_reload.py` clears the `noupdate` flag of the corrected templates so that the update reloads them;
- `pre-migration_link_and_reload.py` also links a record that only exists in the database to its new xmlid, so the update does not create a duplicate.

The reload overwrites every field of the record, so the XML must hold the database values for `email_from`, `reply_to`, `partner_to`, subject and body. It also replaces any local customisation of these templates in other databases: say so in the PR. Test the migration on a copy of a database before merging.

## 7. Commit, push, pull requests

- One commit per repo: `T3527 FIX <module>: <summary>`, ticket number first, after `pre-commit`.
- Ask before pushing; push the branch to `origin` over SSH.
- Open a **draft** PR against `18.0` in each repo, short description (ticket, what changed, link to the other repo's PR), no tool attribution line. Create the first PR, then the second with the link, then update the first. If `gh pr edit` fails with a "Projects (classic)" error, use `gh api -X PATCH repos/<org>/<repo>/pulls/<n> -f body=...`.

## 8. Things that went wrong on T3527 (check them early)

- A wizard that renders a template body must use the QWeb engine; the default is `inline_template`, which ignores `t-set` and `t-out`.
- A `NameError: urls` came from a list built in a `t-foreach` and read outside its scope.
- A subject cannot use variables defined in the body.
- An IDE reformat of the scratch file adds spaces before punctuation; do not push a reformatted file.
- The forced reload would have overwritten working sender fields with old `${}` text; the XML must be synced first.
- Translations of the `communication.snippet` field were lost because its translation type changed between v14 and v18; check the snippets (`years_uc`...) in each language.
- Other templates still call `get_date` with legacy keys (ids 46, 93, 132 in the T3527 database).

## 9. Checklist before the PR

- [ ] every template of the ticket loaded, cleaned and accepted in the four languages
- [ ] database updated, backups kept
- [ ] XML and `.po` synced, `pre-commit` green
- [ ] migrations added, versions bumped, tested on a copy
- [ ] draft PRs opened, linked to each other, ticket number in the title
