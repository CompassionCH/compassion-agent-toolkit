---
name: odoo-communication-fix
description: Fix and align the Compassion communication e-mail templates (mail.template used by partner.communication.job) in four languages. A developer corrects them in a local database restored from the production backup; the skill cleans each text, proposes improvements, writes the result to the local database, exports the texts to the comm-rules repository and, only if the user agrees each time, pushes the English text and the translations of those mail.template records to production over SSH. Use for "fix communication rules", "correct the B2S / exit / birthday / SUB templates", or any ticket that asks to fix communication texts in v18.
---

# Fixing Compassion communications

Method used for T3527 (B2S letters, planned and unplanned exit, birthday reminder, SUB dossier), adapted after the production migration. The texts live in the **database** (`mail.template`, jsonb with English and the translations). The XML records of the modules are `noupdate` generic default examples: **do not write the corrected English in them, do not touch the `.po` files, no migration scripts**. The corrected texts are kept in the **comm-rules repository** and, optionally, pushed to production.

Everything that changes from one task to the next is a **parameter you must collect first**; never reuse a value from a previous task.

`$SKILL` below means the folder this file is in (it holds `scripts/`, `templates/` and `reference/`). The scripts need `python3` with `psycopg2` and `lxml`.

## 0. Collect the parameters (ask, do not guess)

| Parameter | How to get it | Used for |
|---|---|---|
| `TICKET` | Ask (CLAUDE.md: ticket number first). Example `T3527`. If there is none, say so and continue without prefix | commit messages |
| `DB` | The **local** database restored from the production backup that holds the corrected texts (`psql -l`). Template ids are the same as in production | source of truth |
| `TEMPLATES` | The templates to fix, from the progress table (`reference/progress-table.md`, most used first) or given by the user, one at a time | scope |
| `SCRATCH` | The scratch file the user works in (PyCharm scratches folder). Ask which file | working copy |
| `LANGS` | `en_US`, `fr_CH`, `de_DE`, `it_IT`. The user chooses the order | loop |
| `COMM_RULES_REPO` | The repository with one HTML file per config and language (`~/Dev/comm-rules`). Ask the CLAUDE.md question "current branch or feature branch?" before changing it | section 4 |
| `PROD` | **Only when the user wants to push to production** (section 5): the SSH target (`user@host`), the production database name, and the psql command on the server. Ask them at that moment, do not store them | section 5 |

Never touch the `odoo.conf` Connect settings (stage stays active) and do not read `odoo.conf` (it holds credentials): pass `-c odoo.conf` to Odoo without opening it. Ask permission **each time** you run Odoo or a test. Reading the local database with `psql` is fine; write to it only when the user asked for it for that template.

## 1. Map each template

```sql
select c.id, s.name, t.id, t.name->>'en_US' from partner_communication_config c
join utm_source s on s.id = c.source_id join mail_template t on t.id = c.email_template_id
where c.active order by lower(s.name);   -- the config name is the name of its utm.source
```
First read the progress table (`reference/progress-table.md`): it lists every template of an active config with its usage and `Todo` / `Done`. Propose the `Todo` templates from the top (most used), or take the ones the user gives, and skip the `Done` ones unless he asks to redo them. A template shared by several configs has one row per config.

## 2. Per template and per language: the loop

1. Back up the DB value: `select body_html->>'<lang>' from mail_template where id=<id>` into a file named `b<id>_<lang>_original.html`, and copy it to `SCRATCH`.
2. Run the automatic cleanup: `python3 $SKILL/scripts/clean_template.py $SCRATCH --lang <lang>` (see `reference/rules.md`, "Automatic rules"). Report what it removed.
3. Read the whole template, then **propose** improvements as a numbered list (categories and never-propose list in `reference/rules.md`, including "Several objects"). Apply **only** the numbers the user chooses; if he picks an item that is a question, say how you interpreted it.
4. Check the XML (`xml.dom.minidom`), run `clean_template.py --check` again, and show the user a summary (what was applied, what was left).
5. When the user confirms, write to the local database with `jsonb_set` for that language only (psycopg2, `to_jsonb(%s::text)`), keep the backup, then report the new length.
6. If the user edits the scratch by hand, diff it against your saved version before pushing. If it lost your edits or an IDE reformat added line breaks around `<t>` elements (it puts a space before punctuation), say so and ask.
7. Subjects are inline templates (`{{ }}`): they do not see the `t-set` variables of the body. A variable from the body in a subject gives `NameError`.

Report in English whatever the language of the template.

## 3. Test the texts locally (recommended)

Render them on real jobs without saving anything: `templates/render_test_shell.py` (run through `odoo-bin shell`, rolled back, ask permission): one object, **several objects**, each language. Use `same_job_search=[('id','=',0)]` when creating test jobs, otherwise the job is merged into an existing one and you test the wrong data.

## 4. Update the comm-rules repository

`python3 $SKILL/scripts/export_to_repo.py --db <DB> --repo <COMM_RULES_REPO> --ids <template ids> [--dry-run]` writes `<config name>_<EN|FR|DE|IT>.html` byte for byte from the local database (the config name is the config's `utm.source` name). Existing files are replaced, missing ones created. Show the user what changed, commit there as `<TICKET> UPD comm rules: <summary>` (open the PyCharm diff view first, per CLAUDE.md), then update the progress table (section 6). **Ask before pushing** the repository and say where it goes.

## 5. Push to production (optional, needs the user's permission every time)

This writes to the **production** database over SSH. It is not the local test database: treat it as a separate, explicit decision, even if the user pushed before.

1. Ask the user whether he wants to push these templates to production. If not, stop here.
2. Ask for the SSH target, the production database name and how to run psql on the server (for example `sudo -u postgres psql`). Never reuse values from a previous task or store them.
3. Show the dry run and wait for an explicit yes: `python3 $SKILL/scripts/push_to_production.py --db <DB> --ids <ids> --ssh <user@host> --prod-db <prod db> [--psql "<cmd>"] --dry-run`. It prints the templates (id, English name), the fields (`body_html`, `subject`), the languages and the exact SSH command, with no connection.
4. Optional test: add `--rollback`. It runs the whole transaction on production and rolls it back (connection and guards checked, nothing written).
5. Real push, only after the yes: the same command with `--yes` instead of `--dry-run`. One transaction, all or nothing.
6. What it does and never does: it reads only the **local** database. On production it only sends `UPDATE mail_template SET body_html = body_html || {...}, subject = subject || {...} WHERE id = <id> AND name->>'en_US' = '<English name>'`, merging the English text and the translations (other languages of production are kept). The id is the local one (same as production); the English name is a guard, and if either differs the transaction fails and rolls back. It **never reads anything from production** (no previous value, no other field, no other record) and never touches `email_from`, `reply_to`, `partner_to` or other tables. Because it reads nothing, the previous production text is not saved: tell the user he can rely on his own database backup, or on the previous comm-rules commit if the template was exported before.
7. Report the result as printed (`ok <id>`, committed or rolled back). If it fails, nothing was written.

## 6. Progress table

When a template is accepted, in the local database and exported to the comm-rules repository, mark it `Done` with the ticket on every row of its id (`reference/progress-table.md`). Done does not mean pushed to production.

## 7. Commit, push

- Commit message `<TICKET> UPD comm rules: <summary>`; the ticket number first. Do not commit until the user asked. The user may commit and amend himself: re-read `git status` / `git log` before assuming your changes are still uncommitted, and never `git stash` on a tree you did not check.
- **Ask before pushing** and say where it goes (`origin`, over SSH). Do not push `18.0` unless the user says so.
- If a PR is needed: `gh pr create --draft`, short description (ticket, what), **no "Generated with Claude Code" line**, open it in the browser. If `gh pr edit` fails on a "Projects (classic)" GraphQL error, use `gh api -X PATCH repos/<org>/<repo>/pulls/<n> -f body=...`.

## Files

- `scripts/clean_template.py`: automatic cleanup of one body.
- `scripts/export_to_repo.py`: local database to the comm-rules HTML files.
- `scripts/push_to_production.py`: optional push of the English text and translations to production over SSH (write only).
- `templates/render_test_shell.py`: render the texts on real jobs, rolled back.
- `reference/rules.md`: automatic rules, proposal categories, language and wording rules, pitfalls.
- `reference/progress-table.md`: the progress table (where it is, how to read and update it).
- `reference/how-to-report.md`: step by step guide for another developer.
