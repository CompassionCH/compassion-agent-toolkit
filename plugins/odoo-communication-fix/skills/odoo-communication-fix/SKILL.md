---
name: odoo-communication-fix
description: Fix and align the Compassion communication e-mail templates (mail.template used by partner.communication.job) in four languages. A developer corrects them in a database, the skill cleans each text, proposes improvements, writes the result back to the database, then syncs the English source XML and the fr_CH, de_DE, it_IT .po files, adds the migrations, verifies them on a copy, exports the texts to the comm-rules repository and opens draft PRs. Use for "fix communication rules", "correct the B2S / exit / birthday / SUB templates", or any ticket that asks to fix communication texts in v18.
---

# Fixing Compassion communications

Method used for T3527 (B2S letters, planned and unplanned exit, birthday reminder, SUB dossier). Everything that changes from one task to the next is a **parameter you must collect first**; never reuse a value from a previous task.

`$SKILL` below means the folder this file is in (it holds `scripts/`, `templates/` and `reference/`). The scripts need `python3` with `psycopg2`, `polib` and `lxml`.

## 0. Collect the parameters (ask, do not guess)

| Parameter | How to get it | Used for |
|---|---|---|
| `TICKET` | Ask (CLAUDE.md: ticket number first). Example `T3527`. If there is none, say so and continue without prefix | branch, commit messages, PR |
| `DB` | Ask for the database that holds the corrected texts, test with `psql -l` | source of truth |
| `TEST_DB` | A **copy** (older or fresh) used to test the migrations. Never `DB` | section 7 |
| `BRANCH` | `<TICKET>-fix-communication-rules` unless the user says otherwise. Also ask the CLAUDE.md question "current branch or feature branch?" | all repos |
| `REPOS` | From `~/Dev/CLAUDE.md` layout: `compassion-modules` and `compassion-website` (under `NN-addons/nordic-sh/addons-compassion-base/`), `compassion-switzerland` (under `NN-addons/addons-switzerland/`). `NN` = Odoo version from the folder prefix | code |
| `SHARED` | Is the module shared with another organisation (Nordic) that has its own texts? `compassion-modules` is; `compassion-switzerland` is not. If yes, the reload runs only where a Swiss-only module is installed (`REQUIRED_MODULE`, section 6) | migrations |
| `TEMPLATES` | The ids/names of the mail.template records to fix, given by the user, one at a time | scope |
| `SCRATCH` | The scratch file the user works in (PyCharm scratches folder). Ask which file | working copy |
| `LANGS` | `en_US`, `fr_CH`, `de_DE`, `it_IT`. The user chooses the order (usually the one he is fixing first) | loop |
| `PROGRESS_TABLE` | The Claude Docs table that lists every template of an active config and its status (`reference/progress-table.md`). Read it to see what is `Todo`, and update it at the end of each template | scope, tracking |
| `COMM_RULES_REPO` | Optional: the repository with one HTML file per config and language (`~/Dev/comm-rules`) | section 8 |

Create the branch in each repo (`git checkout -b <BRANCH>` from a clean `18.0`). Never touch the `odoo.conf` Connect settings (stage stays active) and do not read `odoo.conf` (it holds credentials): pass `-c odoo.conf` to Odoo without opening it.

Ask permission **each time** you run Odoo or a test. Reading with `psql` is fine; writing to the database only when the user asked for it for that template.

## 1. Map each template to its source

First read the progress table (`reference/progress-table.md`): it lists every template of an active config with `Todo` / `Done`. Propose the `Todo` templates to the user, or take the ones he gives, and skip the `Done` ones unless he asks to redo them.

```sql
select t.id, t.name->>'en_US', d.module||'.'||d.name
from mail_template t left join ir_model_data d on d.model='mail.template' and d.res_id=t.id
where t.id in (...);
select c.id, c.email_template_id, s.name from partner_communication_config c
join utm_source s on s.id=c.source_id;   -- the config name is the name of its utm.source
```
- A template with an xmlid lives in `<module>/data/*.xml` (grep `id="<xmlid>"`). Typical modules: `partner_communication_compassion`, `partner_communication_switzerland`.
- A template with `__import__.NN` has **no source** (it only exists in the database, e.g. the B2S Final Letter): create an xmlid and a record in the XML, point the config at it, and link the existing record with a pre-migration (section 6).

## 2. Per template and per language: the loop

1. Back up the DB value: `select body_html->>'<lang>' from mail_template where id=<id>` into a file named `b<id>_<lang>_original.html`, and copy it to `SCRATCH`.
2. Run the automatic cleanup: `python3 $SKILL/scripts/clean_template.py $SCRATCH --lang <lang>` (see `reference/rules.md`, "Automatic rules"). Report what it removed.
3. Read the whole template, then **propose** improvements as a numbered list (categories and never-propose list in `reference/rules.md`). Apply **only** the numbers the user chooses; if he picks an item that is a question, say how you interpreted it.
4. Check the XML (`xml.dom.minidom`), run `clean_template.py --check` again, and show the user a summary (what was applied, what was left).
5. When the user confirms, write to the database with `jsonb_set` for that language only (psycopg2, `to_jsonb(%s::text)`), keep the backup, then report the new length.
6. If the user edits the scratch by hand, diff it against your saved version before pushing. If it lost your edits or an IDE reformat added line breaks around `<t>` elements (it puts a space before punctuation), say so and ask.
7. Subjects are inline templates (`{{ }}`): they do not see the `t-set` variables of the body. A variable from the body in a subject gives `NameError`.

Report in English whatever the language of the template.

## 3. Review the texts for other environments (before syncing)

The database works because every module is installed. The code must also work where they are not (Nordic, CI, a fresh install).

1. Run `python3 $SKILL/scripts/check_dependencies.py --module <module> --xml data/<file>.xml ...`. It lists the fields and methods the templates use that are defined only **outside** the dependency closure of the module (for example `commercial_name` and `short_signature` from `report_compassion`, `success_sentence` from `thankyou_letters`). `UNGUARDED` entries must be handled.
2. Handle them with a guard, not a new dependency and not a data move: `x.field if 'field' in x._fields else <fallback>` (works in the inline and QWeb engines, tested; `getattr`/`hasattr` are not available in the sandbox). Fallbacks: company name for the sender, user name for the signature, empty string for an optional sentence. Apply it in the database first, then sync.
3. Texts built for **one** object while a job can hold several (`child[:1]`, one `lifecycle` record for all children, `has_sub` computed on every sponsorship of a child instead of the letter's own sponsorship): check them and propose a fix per object (see `reference/rules.md`, "Several objects").

## 4. Sync to the code

1. Write a `templates.json` (format in `scripts/sync_to_code.py`, example in `templates/templates.example.json`): id, module, xmlid, xml_file, i18n_dir.
2. Dry run: `python3 $SKILL/scripts/sync_to_code.py --db <DB> --config templates.json --dry-run`.
3. Real run (add `--create-missing` for a template without a record in the XML). It updates the English subject and body of the XML record, and the `name`, `subject`, `body_html` entries of `fr_CH.po`, `de_DE.po`, `it_IT.po` from the database (msgid = English, msgstr = translation). A second dry run must say "would change 0 file(s)".
4. New xmlid: change the config record that must use it (`email_template_id ref=...`).
5. In the XML records, also set `email_from`, `reply_to`, `partner_to` to the database values (the script does not sync them), otherwise the reload (section 6) overwrites the working values with the old `${}` Mako text.
6. Verify: the XML bodies match the database bodies ignoring whitespace; `pre-commit run --files <changed files>` in each repo (new `.po` entries need `#. module: <module>`).
7. Update the progress table: `Done` and the ticket on every row with that template id (`reference/progress-table.md`). Do it once the template is in the database and synced, not before.

## 5. Code fixes that came with it (check them first on a new task)

The change text wizard and the quick refresh of `partner.communication.job`, and `snippet_text`, were fixed in T3527. Check `partner_communication/wizards/change_text_wizard.py` and `generate_communication_wizard.py` (render with `engine="qweb", options={"post_process": True}`), `quick_refresh` (context `skip_pdf_count=True`, works without `lang_preview`) and the `communication.snippet` translations before assuming they behave. `refresh_text` is slow for physical jobs (two PDF renders): see `reference/rules.md`, Pitfalls.

## 6. Migrations (so the existing databases get the fixed texts)

The data files are `<odoo noupdate="1">`. **Odoo skips an existing record of such a file before it reads its fields**; the `noupdate` flag in `ir_model_data` is only a second check. So clearing the flag (`openupgrade.set_xml_ids_noupdate_value(..., False)`) reloads **nothing** for these files, and `openupgrade.load_data()` on the file would reset every template of that file, including the ones not corrected. What works: load only the corrected records in mode `init` from a **post**-migration.

In each module touched, raise the manifest version **above the `latest_version` of the database** (`select latest_version from ir_module_module where name=...`) and add, from `templates/`:
- `post-migration_reload.py` -> `migrations/<version>/post-migration.py`: fill `MODULE`, `FIXED_TEMPLATES` (data file -> xmlids) and `REQUIRED_MODULE`. It loads only those records from the data file, after dropping their non-English `body_html`/`subject` values so the `.po` files (loaded after the post-migration) fill all languages. Without that, the old translations stay when the English structure changed.
- `pre-migration_link.py` -> `migrations/<version>/pre-migration.py`, only for a template that had no xmlid: it links the existing record to the new xmlid **before** the data files load, otherwise the update creates a duplicate.
- Shared code (`SHARED`): set `REQUIRED_MODULE` to a module that only that organisation installs. Test it with `state IN ('installed', 'to upgrade')`: dependents of the updated module are `to upgrade` while the migration runs, `= 'installed'` skips the migration.
- A forced reload overwrites **every field** of the record, so the XML must hold the database values (section 4 step 5).
- Never run a migration without the user's permission.

## 7. Verify the migration on `TEST_DB`

Ask permission, then on the **copy** only:
1. Force the migration: `update ir_module_module set latest_version='<previous version>' where name in (...)`, then `odoo-bin -c odoo.conf -d <TEST_DB> -u <modules> --stop-after-init --no-http`. Check the log for `Running upgrade ... post-migration`. Tracebacks about a missing filestore file are not migration errors.
2. `python3 $SKILL/scripts/compare_databases.py --ref <DB> --test <TEST_DB> --config templates.json`: fr/de/it bodies, subjects and senders must be identical, English identical ignoring the `data-o-mail-quote` attributes Odoo adds to `<blockquote>`, and no duplicate template.
3. Render the texts: `templates/render_test_shell.py` (rolled back): single object, **several objects**, the optional-field guards. Use `same_job_search=[('id','=',0)]` when creating test jobs, otherwise the job is merged into an existing one and you test the wrong data.
4. A duplicate record (two templates with the same name) in the test database means the link step did not run (its xmlid already existed): remove the stray record and its xmlid (with the user's permission) and run again.

## 8. Export to the comm-rules repository (optional)

`python3 $SKILL/scripts/export_to_repo.py --db <DB> --repo <COMM_RULES_REPO> --ids <template ids> [--dry-run]` writes `<config name>_<EN|FR|DE|IT>.html` byte for byte from the database (the config name is the config's `utm.source` name). Existing files are replaced, missing ones created. Commit there as `<TICKET> UPD comm rules: ...`.

## 9. Commit, push, PR

- Commit message `<TICKET> FIX <module>: <summary>`; the ticket number first. Do not commit until the user asked; open the PyCharm diff view for review when the CLAUDE.md rule says so. The user may commit and amend himself: re-read `git status`/`git log` before assuming your changes are still uncommitted, and never `git stash` on a tree you did not check.
- **Ask before pushing** and say where it goes (`origin`, over SSH). Do not push `18.0` unless the user says so.
- Draft PR against `18.0` with `gh pr create --draft`, short description (ticket, what, other repo PR), **no "Generated with Claude Code" line**. Open it in the browser. Create the first PR, then the second one linking to it, then update the first body. If `gh pr edit` fails on a "Projects (classic)" GraphQL error, update with `gh api -X PATCH repos/<org>/<repo>/pulls/<n> -f body=...`.
- An automated reviewer (Greptile) comments on the PRs. Read the comments (`gh api repos/<org>/<repo>/pulls/<n>/comments`), **check each against the Odoo source before agreeing** (it was right on the `noupdate` reload and the `to upgrade` state, wrong that a field has no definition), and ask the user which ones to apply.

## Files

- `scripts/clean_template.py`: automatic cleanup of one body.
- `scripts/check_dependencies.py`: fields used by the templates that live outside the module's dependencies.
- `scripts/sync_to_code.py`: database to XML and `.po`.
- `scripts/compare_databases.py`: reference database against the migrated test database.
- `scripts/export_to_repo.py`: database to the comm-rules HTML files.
- `templates/`: example `templates.json`, migration models, rendering test model.
- `reference/progress-table.md`: the progress table (where it is, how to read and update it).
- `reference/rules.md`: automatic rules, proposal categories, language and wording rules, pitfalls.
- `reference/how-to-report.md`: step by step guide for another developer.
