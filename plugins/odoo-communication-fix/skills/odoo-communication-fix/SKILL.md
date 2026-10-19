---
name: odoo-communication-fix
description: Fix and align the Compassion communication e-mail templates (mail.template used by partner.communication.job) in four languages. A developer corrects them in a database, the skill cleans each text, proposes improvements, writes the result back to the database, then syncs the English source XML and the fr_CH, de_DE, it_IT .po files, adds the migrations and opens draft PRs. Use for "fix communication rules", "correct the B2S / exit / birthday / SUB templates", or any ticket that asks to fix communication texts in v18.
---

# Fixing Compassion communications

`$SKILL` below means the folder this file is in (it holds `scripts/`, `templates/` and `reference/`). The scripts need `python3` with `psycopg2`, `polib` and `lxml`.

Method used for T3527 (B2S letters, planned and unplanned exit, birthday reminder, SUB dossier). Everything that changes from one task to the next is a **parameter you must collect first**; never reuse a value from a previous task.

## 0. Collect the parameters (ask, do not guess)

| Parameter | How to get it | Used for |
|---|---|---|
| `TICKET` | Ask (CLAUDE.md: ticket number first). Example `T3527` | branch, commit messages, PR |
| `DB` | Ask for the database that holds the corrected texts, test with `psql -l` | source of truth |
| `BRANCH` | `<TICKET>-fix-communication-rules` unless the user says otherwise. Also ask the CLAUDE.md question "current branch or feature branch?" | all repos |
| `REPOS` | From `~/Dev/CLAUDE.md` layout: `compassion-modules` and `compassion-website` (under `NN-addons/nordic-sh/addons-compassion-base/`), `compassion-switzerland` (under `NN-addons/addons-switzerland/`). `NN` = Odoo version from the folder prefix | code |
| `TEMPLATES` | The ids/names of the mail.template records to fix, given by the user, one at a time | scope |
| `SCRATCH` | The scratch file the user works in (PyCharm scratches folder). Ask which file | working copy |
| `LANGS` | `en_US`, `fr_CH`, `de_DE`, `it_IT`. The user chooses the order (usually the one he is fixing first) | loop |

Create the branch in each repo (`git checkout -b <BRANCH>` from a clean `18.0`). Never touch the `odoo.conf` Connect settings (stage stays active).

Ask permission **each time** you run Odoo or a test. Reading with `psql` is fine; writing to the database only when the user asked for it for that template.

## 1. Map each template to its source

```sql
select t.id, t.name->>'en_US', d.module||'.'||d.name
from mail_template t left join ir_model_data d on d.model='mail.template' and d.res_id=t.id
where t.id in (...);
select c.id, c.email_template_id, d.module||'.'||d.name from partner_communication_config c
left join ir_model_data d on d.model='partner.communication.config' and d.res_id=c.id;
```
- A template with an xmlid lives in `<module>/data/*.xml` (grep `id="<xmlid>"`). Typical modules: `partner_communication_compassion`, `partner_communication_switzerland`.
- A template with `__import__.NN` has **no source** (it only exists in the database, e.g. the B2S Final Letter): create an xmlid and a record in the XML, point the config at it, and link the existing record with a pre-migration (section 5).

## 2. Per template and per language: the loop

1. Back up the DB value: `select body_html->>'<lang>' from mail_template where id=<id>` into a file named `b<id>_<lang>_original.html`, and copy it to `SCRATCH`.
2. Run the automatic cleanup: `python3 $SKILL/scripts/clean_template.py $SCRATCH --lang <lang>` (see `reference/rules.md`, "Automatic rules"). Report what it removed.
3. Read the whole template, then **propose** improvements as a numbered list (categories and never-propose list in `reference/rules.md`). Apply **only** the numbers the user chooses; if he picks an item that is a question, say how you interpreted it.
4. Check the XML (`xml.dom.minidom`), run `clean_template.py --check` again, and show the user a summary (what was applied, what was left).
5. When the user confirms, write to the database with `jsonb_set` for that language only (psycopg2, `to_jsonb(%s::text)`), keep the backup, then report the new length.
6. If the user edits the scratch by hand, diff it against your saved version before pushing. If it lost your edits or an IDE reformat added line breaks around `<t>` elements (it puts a space before punctuation), say so and ask.
7. Subjects are inline templates (`{{ }}`): they do not see the `t-set` variables of the body. A variable from the body in a subject gives `NameError`.

Report in English whatever the language of the template.

## 3. Sync to the code

1. Write a `templates.json` (format in `scripts/sync_to_code.py`, example in `templates/templates.example.json`): id, module, xmlid, xml_file, i18n_dir.
2. Dry run: `python3 $SKILL/scripts/sync_to_code.py --db <DB> --config templates.json --dry-run`.
3. Real run (add `--create-missing` for a template without a record in the XML). It updates the English subject and body of the XML record, and the `name`, `subject`, `body_html` entries of `fr_CH.po`, `de_DE.po`, `it_IT.po` from the database (msgid = English, msgstr = translation).
4. New xmlid: change the config record that must use it (`email_template_id ref=...`).
5. In the XML records, also set `email_from`, `reply_to`, `partner_to` to the database values, otherwise the forced reload (section 5) overwrites the working values with the old `${}` Mako text.
6. Verify: the XML bodies match the database bodies ignoring whitespace; every `.po` body and subject equals the database (the T3527 run checked 36/36); `pre-commit run --files <changed files>` in each repo (new `.po` entries need `#. module: <module>`).

## 4. Code fixes that came with it (check them first on a new task)

The change text wizard and the quick refresh of `partner.communication.job`, and `snippet_text`, were fixed in T3527. Check `partner_communication/wizards/change_text_wizard.py` and `generate_communication_wizard.py` (render with `engine="qweb", options={"post_process": True}`), `quick_refresh` (context `skip_pdf_count=True`) and the `communication.snippet` translations before assuming they behave.

## 5. Migrations (so the existing databases get the fixed texts)

Templates are in `noupdate="1"` files, so an update does not touch them. In each module touched, add `migrations/<next version>/pre-migration.py` and raise the manifest version **above the `latest_version` of the database** (`select latest_version from ir_module_module where name=...`). Models in `templates/`:
- `pre-migration_link_and_reload.py`: link an existing record to a new xmlid (avoids a duplicate) and flag the fixed templates as updatable (`openupgrade.set_xml_ids_noupdate_value(..., False)`).
- `pre-migration_reload.py`: only the reload, for templates that already have an xmlid.
Do not run the migrations without the user's permission.

## 6. Commit, push, PR

- Commit message `<TICKET> FIX <module>: <summary>`; the ticket number first. Do not commit until the user asked; open the PyCharm diff view for review when the CLAUDE.md rule says so.
- **Ask before pushing** and say where it goes (`origin`, over SSH). Do not push `18.0` unless the user says so.
- Draft PR against `18.0` with `gh pr create --draft`, short description (ticket, what, other repo PR), **no "Generated with Claude Code" line**. Open it in the browser. Create the first PR, then the second one linking to it, then update the first body. If `gh pr edit` fails on a "Projects (classic)" GraphQL error, update with `gh api -X PATCH repos/<org>/<repo>/pulls/<n> -f body=...`.

## Files

- `scripts/clean_template.py`: automatic cleanup of one body.
- `scripts/sync_to_code.py`: database to XML and `.po`.
- `templates/`: example `templates.json`, migration models.
- `reference/rules.md`: automatic rules, proposal categories, language and wording rules, pitfalls.
- `reference/how-to-report.md`: step by step guide for another developer.
