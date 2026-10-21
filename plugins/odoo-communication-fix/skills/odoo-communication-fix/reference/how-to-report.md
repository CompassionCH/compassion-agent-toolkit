# Fixing communication templates with the `odoo-communication-fix` skill

Guide for a developer who takes over a "fix the communications" ticket (same kind of work as T3527). It explains what the skill does, what you must provide, the working loop and how to finish.

## 1. What the work is

The e-mails and SMS of the sponsorship communications are `mail.template` records written in QWeb, in four languages (English source, `fr_CH`, `de_DE`, `it_IT`). After the v14 to v18 migration many of them are wrong: leftover Jinja, variables that do not exist, broken dates, wrong links, texts that differ between languages. The texts live in the **database**. Since the production migration, the XML records of the modules are `noupdate` generic default examples: the corrected texts are **not** written in the XML or in the `.po` files, and there are no migration scripts. The skill's job is to:

1. clean each text and propose improvements that **you** accept or refuse,
2. write the accepted text to your **local** database (restored from the production backup, so the template ids are the same as in production),
3. export the texts to the **comm-rules** repository,
4. only if you agree, every time, push the English text and the translations of those `mail.template` records to production over SSH,
5. update the progress table and commit.

The local database is the working copy: you correct there, the repository keeps the result.

## 2. Before you start: what you provide

The skill asks for these values and never reuses the ones of a previous task.

| Value | Example | Notes |
|---|---|---|
| Ticket number | `T3527` | first in the commit messages |
| Local database | `swiss18` | restored from the production backup, you can write to it |
| Templates | `56` B2S New letter, `449` B2S Final Letter, ... | from the progress table, most used first |
| Scratch file | a local scratch file `.html` | the working copy you edit |
| comm-rules repository | `~/Dev/comm-rules` | one HTML file per config and language |
| Production (only to push) | SSH target, database name, psql command | asked at the moment you choose to push, never stored |

Check first: `psql` access to the local database works, the comm-rules repository is clean, `psycopg2` and `lxml` are installed.

Install the plugin (`/plugin install odoo-communication-fix@compassion`, or the bundler), then start the skill by typing `/odoo-communication-fix` in Claude Code. `$SKILL` in the commands below is the skill folder (`scripts/`, `templates/`, `reference/`).

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

## 5. Test the texts locally

Render them on real jobs without saving anything: `templates/render_test_shell.py`, run through `odoo-bin shell` (everything is rolled back, Claude asks your permission first). Test one object, **several objects**, and each language. A text written for one object can silently use the first one when a job holds several: the first child's reason or figures used for all children, a condition on every sponsorship of a child instead of the letter's own (`reference/rules.md`, "Several objects"). When you create test jobs, pass `same_job_search=[('id', '=', 0)]`, otherwise the job is merged into an existing one and you test the wrong data.

## 6. Update the comm-rules repository

```
python3 $SKILL/scripts/export_to_repo.py --db <DB> --repo ~/Dev/comm-rules --ids 56 449 59 --dry-run
```
It writes `<config name>_<EN|FR|DE|IT>.html` from your local database, byte for byte. The config name is the name of the `utm.source` of the communication config that uses the template; a missing file is created. Remove `--dry-run`, review the diff, commit in that repository (`<TICKET> UPD comm rules: ...`). Claude asks before pushing the repository.

## 7. Push to production (optional)

This writes to the production database, so it is a separate decision each time, with your explicit yes. Claude asks for the SSH target (`user@host`), the production database name and how to run psql on the server, and never stores them.

```
python3 $SKILL/scripts/push_to_production.py --db <DB> --ids 56 449 --ssh user@host --prod-db <prod db> --dry-run
```
- The dry run lists the templates (id and English name), the fields (`body_html`, `subject`), the languages and the exact SSH command. Nothing is sent.
- `--rollback` runs the whole transaction on production and rolls it back: it tests the connection and the guards without writing.
- The real push uses `--yes`. It is one transaction, all or nothing.

What it does: it reads only your **local** database. On production it only sends `UPDATE mail_template SET body_html = body_html || {...}, subject = subject || {...} WHERE id = <id> AND name->>'en_US' = '<English name>'`: the English text and the translations are merged into the jsonb values (other languages are kept). The id is the local one; the English name is a guard, and if either differs the transaction fails and nothing is written.

What it never does: read anything from production (no previous value, no other field, no other record), touch `email_from`, `reply_to`, `partner_to` or any other table. Because it reads nothing, the previous production text is not saved: rely on your own database backup, or on the previous comm-rules commit if the template was exported before.

## 8. Progress table

The last section of this guide lists every template of an active communication config with its usage (communication jobs created in the last 12 months, most used first) and its status (`Todo` / `Done`) and ticket. Start at the top. When a template is accepted, in your local database and exported to the comm-rules repository, mark it `Done` with your ticket. The skill does it for you when it can reach the document (`reference/progress-table.md`); otherwise edit the table by hand. A template shared by several configs has one row per config: mark all of them. `Done` does not mean pushed to production.

## 9. Commit and push

- One commit in the comm-rules repository: `T3527 UPD comm rules: <summary>`, ticket number first.
- You may commit and amend yourself: Claude re-reads `git status` and `git log` before assuming its changes are uncommitted.
- Ask before pushing; Claude says where it goes (`origin`, over SSH).

## 10. Things that went wrong on T3527 (check them early)

- A wizard that renders a template body must use the QWeb engine; the default is `inline_template`, which ignores `t-set` and `t-out`.
- A `NameError: urls` came from a list built in a `t-foreach` and read outside its scope.
- A subject cannot use variables defined in the body.
- An IDE reformat of the scratch file adds spaces before punctuation; do not push a reformatted file.
- Translations of the `communication.snippet` field were lost because its translation type changed between v14 and v18; check the snippets (`years_uc`...) in each language.
- The unplanned exit used the first child's reason, and both exit letters the first child's figures, for all children.
- `refresh_text` on a physical job took about 66 s (two PDF renders); see `reference/rules.md`, Pitfalls.
- Other templates still call `get_date` with legacy keys; check the progress table rows you take.
- The first approach wrote the English in the XML records and reloaded them with migrations. The records are `noupdate`, and Odoo skips such records before reading their fields, so clearing the flag reloaded nothing. After the production migration the whole approach was dropped.

## 11. Checklist

- [ ] every template of the ticket loaded, cleaned and accepted in the four languages
- [ ] local database updated, backups kept
- [ ] texts rendered locally, several-object cases handled
- [ ] comm-rules repository updated and committed
- [ ] production push done, if you chose to (dry run shown, explicit yes)
- [ ] progress table updated (`Done` and the ticket on every row of the templates)
