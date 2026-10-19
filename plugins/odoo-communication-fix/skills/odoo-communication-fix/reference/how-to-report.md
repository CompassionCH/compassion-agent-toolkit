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
| Repos | `compassion-modules`, `compassion-website`, `compassion-switzerland` |
| Templates | `56` B2S New letter, `449` B2S Final Letter, ... | ids given one by one |
| Scratch file | a local scratch file `.html` | the working copy you edit |

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

## 5. Check the texts for other environments

Your database works because every module is installed. The code must also work in a fresh install, in CI and for Nordic, which shares `compassion-modules` but not the Swiss modules.

1. Run the dependency check on the module that ships the templates:
   ```
   python3 $SKILL/scripts/check_dependencies.py --module partner_communication_compassion --xml data/child_letter_emails.xml data/depart_communications.xml
   ```
   It lists the fields and methods used by the templates that are defined only outside the module's dependencies. `UNGUARDED` lines must be handled; the exit code is 1 if there are some.
2. Guard them in the database text (then sync), without adding a dependency: `x.field if 'field' in x._fields else <fallback>`. T3527 needed it for `commercial_name` (sender), `short_signature` (signature), both from `report_compassion`, and `success_sentence` (from `thankyou_letters`).
3. Look for texts written for one object when a job holds several (the first child's reason used for all children, a condition on every sponsorship of a child instead of the letter's own). `reference/rules.md` ("Several objects") shows the fix.

## 6. Sync to the code

1. Write `templates.json` (see `templates/templates.example.json`): template id, module, xmlid, XML file, `i18n` folder.
2. Dry run, then real run:
   ```
   python3 $SKILL/scripts/sync_to_code.py --db <DB> --config templates.json --dry-run
   python3 $SKILL/scripts/sync_to_code.py --db <DB> --config templates.json
   ```
   Add `--create-missing` for a template that has no record in the XML yet (a template imported by hand has the xmlid `__import__.NN`). A second dry run must change nothing.
3. Set `email_from`, `reply_to`, `partner_to` of the XML records to the database values by hand (the script syncs the subject and the body only).
4. Point the matching `partner.communication.config` record at a new xmlid, if you created one.
5. Check: the XML bodies equal the database bodies (ignoring whitespace), `pre-commit run --files <files>` passes in each repo (a new `.po` entry needs `#. module: <module>`).

## 7. Migrations

The data files are `<odoo noupdate="1">`. Odoo skips an existing record of such a file before it reads its fields, so an update changes nothing in existing databases. **Clearing the `noupdate` flag of the records does not help** (the flag is only a second check), and `openupgrade.load_data()` reloads the whole file, including templates you did not correct. Use the models in `templates/`, in each module you changed, and raise the manifest version **above** the database's `latest_version`:

- `post-migration_reload.py` becomes `migrations/<version>/post-migration.py`. Fill `FIXED_TEMPLATES` (data file -> xmlids). It loads only those records from the data file in mode `init`, and first drops their non-English `body_html` and `subject` so that the `.po` files (loaded after the post-migration) fill every language.
- `pre-migration_link.py` becomes `migrations/<version>/pre-migration.py`, only for a template that had no xmlid: it links the existing record to the new xmlid before the data files load, so the update does not create a duplicate.
- In shared code (`compassion-modules`, also used by Nordic) set `REQUIRED_MODULE = "partner_communication_switzerland"`: the reload only runs where that module is installed. The state test is `IN ('installed', 'to upgrade')`.

The reload overwrites every field of the record, so the XML must hold the database values. It also replaces local customisations of these templates in other databases: say so in the PR.

## 8. Verify on a copy

Never on your source database; Claude asks your permission before each run.

1. Force the migration on the copy: set `latest_version` of the modules to the previous version in `ir_module_module`, then `odoo-bin -c odoo.conf -d <TEST_DB> -u <modules> --stop-after-init --no-http`. The log must show `Running upgrade ... post-migration` for each module.
2. Compare with your source database:
   ```
   python3 $SKILL/scripts/compare_databases.py --ref <DB> --test <TEST_DB> --config templates.json
   ```
   French, German and Italian text, subjects and senders must be identical; English must match ignoring the `data-o-mail-quote` attributes that Odoo adds to blockquotes; no duplicate template.
3. Render the texts without saving (`templates/render_test_shell.py`, run with `odoo-bin shell`, rolled back): one object, several objects, and the guards. When you create test jobs pass `same_job_search=[('id', '=', 0)]`, otherwise the job is merged into an existing one.
4. Two templates with the same name in the copy mean the link step did not run because the xmlid already existed. Delete the stray record and its xmlid and run again.

## 9. Export to the comm-rules repository (optional)

```
python3 $SKILL/scripts/export_to_repo.py --db <DB> --repo ~/Dev/comm-rules --ids 56 449 59 --dry-run
```
It writes `<config name>_<EN|FR|DE|IT>.html` from the database, byte for byte. The config name is the name of the `utm.source` of the communication config that uses the template; a missing file is created. Remove `--dry-run`, then commit in that repository (`<TICKET> UPD comm rules: ...`).

## 10. Commit, push, pull requests

- One commit per repo: `T3527 FIX <module>: <summary>`, ticket number first, after `pre-commit`.
- You may commit and amend yourself: Claude re-reads `git status` and `git log` before assuming its changes are uncommitted.
- Ask before pushing; push the branch to `origin` over SSH.
- Open a **draft** PR against `18.0` in each repo, short description (ticket, what changed, link to the other repo's PR), no tool attribution line. Create the first PR, then the second with the link, then update the first. If `gh pr edit` fails with a "Projects (classic)" error, use `gh api -X PATCH repos/<org>/<repo>/pulls/<n> -f body=...`.
- Greptile reviews the PRs. Read its comments and **check each against the Odoo source** before applying it: on T3527 it was right about the `noupdate` reload, the `to upgrade` state, the optional fields and the several-children case, and wrong that `commercial_name` is not defined anywhere (it is, in a module the shared code does not depend on). Tell it when a point does not apply in your context.

## 11. Things that went wrong on T3527 (check them early)

- A wizard that renders a template body must use the QWeb engine; the default is `inline_template`, which ignores `t-set` and `t-out`.
- A `NameError: urls` came from a list built in a `t-foreach` and read outside its scope.
- A subject cannot use variables defined in the body.
- An IDE reformat of the scratch file adds spaces before punctuation; do not push a reformatted file.
- The first migration cleared the `noupdate` flag and reloaded nothing; the filtered post-migration replaced it.
- The `to upgrade` state: the first guard only accepted `installed` and skipped the migration during a real upgrade.
- Old French, German and Italian text survived the reload of the B2S Final Letter until the translations were dropped before loading.
- A record imported by hand (`__import__.NN`) and a stray copy created by an earlier test produced two "B2S Final Letter" templates.
- Translations of the `communication.snippet` field were lost because its translation type changed between v14 and v18; check the snippets (`years_uc`...) in each language.
- The templates used fields of modules outside the dependencies of the shared module (see section 5).
- The unplanned exit used the first child's reason for all children.
- `refresh_text` on a physical job took about 66 s (two PDF renders); see `reference/rules.md`, Pitfalls.
- Other templates still call `get_date` with legacy keys (ids 46, 93, 96, 127, 132 in the T3527 database).

## 12. Progress table

The last section of this guide lists every template of an active communication config with its status (`Todo` / `Done`) and the ticket. Pick the next templates there, and mark each one `Done` with your ticket once it is in the database and synced to the code. The skill does it for you when it can reach the document (`reference/progress-table.md`); otherwise edit the table by hand. A template shared by several configs has one row per config: mark all of them.

## 13. Checklist before the PR

- [ ] every template of the ticket loaded, cleaned and accepted in the four languages
- [ ] database updated, backups kept
- [ ] dependency check clean (guards in place), several-object cases handled
- [ ] XML and `.po` synced, second dry run empty, `pre-commit` green
- [ ] migrations added (post-migration reload, pre-migration link if needed), versions bumped
- [ ] migration run on a copy, `compare_databases.py` clean, texts rendered
- [ ] comm-rules repository updated (if used)
- [ ] progress table updated (`Done` and the ticket on every row of the templates)
- [ ] draft PRs opened, linked to each other, ticket number in the title, review comments answered
