# Rules learned on T3527

## Automatic rules (applied without asking, `scripts/clean_template.py` does most of them)

1. **Unused `t-set` removed**, iteratively. A name counts as used only inside a `t-*` expression (outside string literals); words in the text or in quoted strings do not count. A `t-set` used for a side effect (`urls.append(...)`) is never removed.
2. **Inline `style` attributes removed**, except the ones that draw a button (the `<a>` with `background-color` / `border-radius` and the centring `<div>` around it).
3. **Wrappers removed**: the outer `<div class="communication-text" t-att-style=...>`, any `<div>`/`<span>` that only wraps the `t-set` lines, and a bare `<div>` around the whole text. The `t-set` lines sit directly under `<body>`.
4. **Paragraph shorthand**: `<p><t t-out="x"></t></p>` becomes `<p t-out="x"/>`. A paragraph with text next to the variable (a comma after the salutation) stays as it is.
5. **Signature**: only for `object.send_mode == 'digital'` (never `!= 'physical'`: it must not appear in physical letters nor SMS), the regular `object.user_id.signature` (not `short_signature`), written `<p t-out="object.user_id.signature"/>`. The contact lines of an SMS branch (Sarah / phone / WhatsApp or chat link) stay.
6. **Footnote** (the text that starts with `*`): `<blockquote><small>*...</small></blockquote>`, placed before the closing greeting and the signature, and shown only when an asterisk is displayed (for example `t-if="does_write or can_gift"`).
7. **Website links** use the short code: `/fr/...`, `/de/...`, `/it/...` (never `fr_CH`, `de_DE`, `it_IT`). English has no language path (use the root URL). Check plain-text URLs and URL variables.
8. **Dates**: in v18 `get_date(field, pattern)` takes a Babel pattern. The legacy keys `date_month`, `date_full`, `date_short` are no longer looked up and print garbage (`15AMt6_21ont10`). Use the pattern of the old key: German `d. MMMM`, `d. MMMM yyyy`, `d.M.yyyy`; French and Italian `d MMMM`, `d MMMM yyyy`, `d.M.yyyy`; English `MMMM d`. Also check every other template that calls `get_date` (ids 46, 93, 132 in swiss18 still use legacy keys; 96 uses `%B %Y`).
9. **Link list**: the `urls` list built with `t-foreach` + `urls.append` gives `NameError` out of its scope. Use `<t t-set="urls" t-value="list(dict.fromkeys(letter.filtered('read_url').mapped('read_url')))"/>`.
10. **`t-set` inside `t-if` / `t-else`** is replaced by one-line conditional expressions (`'a' if cond else 'b'`).
11. **German**: no comma after `partner.salutation`. French, Italian, English keep it as in the existing text.
12. **Exit templates** (Planned and Unplanned exit): the poverty / new sponsorship paragraph only when `sponsorships[:1].sds_state in ("sub", "sub_waiting")`. The B2S Final Letter uses `not has_sub`.

## Proposals (numbered list, the user picks the numbers, never apply unasked)

- **Guards**: `[0]` on an empty recordset (`payment_mode_id.name`, `sponsorships[0]`) becomes `[:1]` or `(... or [''])[0]`; `child.age` / `child.gender` on several children become `child[:1]...`; a missing field office; an empty previous child name.
- **Several children**: plural forms driven by `one_child = len(child) == 1`.
- **Several objects** and **optional fields**: see the two sections below (`check_dependencies.py` finds the second).
- **`.title()` tricks** replaced by first-letter capitalisation (`x[:1].upper() + x[1:]`).
- **Words built from pieces** ("salutar" + `lo`/`la`) replaced by whole-word variables.
- **Text matches** on names or translated reasons (`'LSV' in payment_term`, `"ferngeblieben" in reason`): fragile, report them.
- **`<br/><br/>`** replaced by separate `<p>`.
- **Physical-only wording**: "enclosed / im Anhang / en annexe / in allegato" and "the attached payment slip" only when `send_mode == 'physical'`.
- **Footnote** with no asterisk in the text, or an asterisk with no footnote.
- **Hardcoded values**: category/title ids (29, 23), field office ids (1, 19), phone numbers, figures (use the snippets `number_unacceptable_conditions`, `number_deaths_under_5`, `age_deaths_under_5`).
- **Links**: no link to MyCompassion (`https://mycompassion.ch/<code>/my/letter`) where the text invites to write; static URLs written with `t-attf-href` (use `href`); one variable per URL.
- **Dead code**: HTML comments with old blocks, unused snippets variables.
- **Closing line** and signature field consistent with the other templates ("..., " with a comma before the signature).
- **Thousands**: `'{:,}'.format(x).replace(',', '.')` (never tested in the QWeb sandbox, say so).
- **Content alignment**: the four languages of one template should say the same thing. Ask before replacing a whole text and keep the old one in the backup.

## Several objects

A job can hold several objects of one partner (children, sponsorships, letters). A text written for one object must not silently use the first:
- `lifecycle = child.mapped('lifecycle_ids')[:1]` and one `reason` for all children: use a list "<child>: <reason>" when `not one_child`, skip children without a reason, and set `good_reason` / `hopes` only when `one_child`.
- A condition about the **letter** (`has_sub`) must read the letter's own records: `letter.mapped('sponsorship_id.sub_sponsorship_id.state')`, not every sponsorship of the child.
- Figures built from the first object (`sponsorships[:1].contract_duration`, `child[:1].field_office_id`, `child[:1].age`: hours at the centre, meals, medical check-ups, "able to go to school"): show them only when `one_child` (`<p t-if="one_child">`) and give grouped letters a shorter generic paragraph (`<p t-else="">`). Avoid a preposition before `name` in the generic text: its fallback ("your children", "i tuoi figlioli") breaks Italian "di i tuoi"; use an accusative construction ("ha accompagnato <name>").
- `field.country_id` (the country of the first child) in a sentence about all children: leave the country out of the grouped branch.
Add the list branch for each language with the existing vocabulary (*parrainages*, *Patenschaften*, *sostegni*) and ask the user to read the three translations.

## Optional fields

Templates of a shared module must not read fields defined in modules that are not among its dependencies. `scripts/check_dependencies.py` finds them. Guard with `'field' in record._fields` (tested in `inline_template` and `qweb`; `getattr` and `hasattr` are not in the sandbox):
- sender: `company.with_context(lang=...).commercial_name if 'commercial_name' in company._fields else company.name`
- signature: `user.short_signature if 'short_signature' in user._fields else user.name`
- optional sentence: `object.success_sentence if 'success_sentence' in object._fields else ''`
Adding the dependency is not possible when the module lives in another repository (`report_compassion` is in compassion-switzerland, `compassion-modules` cannot depend on it). Moving the Swiss-specific templates to the Swiss module is the clean fix, done during a refactor, not in a fix ticket.

**Never propose** the gender / agreement lookups (`child.get('he')`, `his`, `him`, `accord_s`, `boy` from `child.get('lui')`...). They are an accepted pattern.

## Language rules (Compassion glossary)

- German: sponsorship is always *Patenschaft* / *Patenschaften*; "Hold" stays "Hold". Informal du/ihr according to `plural`.
- Italian: sponsorship is only *sostegno* / *sostegni* (never sponsorizzazione); sponsored: *sostenuto*, to sponsor: *sostenere*.
- French: sponsorship is *parrainage*.
- v14 is the reference for wording, but the v14 syntax (`${}`, `% set`) is not v18 QWeb: do not copy v14 translations of code-bearing templates.

## Pitfalls

- **Rendering engine**: `_render_template` defaults to `inline_template` in v18, which ignores `t-set` / `t-out`. Wizards that render a template body must pass `engine="qweb"` and `options={"post_process": True}`. Subjects are inline templates.
- **IDE reformat** of the scratch file puts line breaks around `<t>` elements and renders a space before punctuation. Do not push a reformatted file.
- **`noupdate`**: the data files are `<odoo noupdate="1">`. In update mode Odoo skips an existing record of such a file **before reading its fields** (`odoo/tools/convert.py`, `_tag_record`); the `noupdate` flag of `ir_model_data` is only a second check, so clearing it (`openupgrade.set_xml_ids_noupdate_value`) reloads nothing. `openupgrade.load_data()` has no record filter and would reset the templates of the file that were not corrected. Use `templates/post-migration_reload.py`: it loads only the listed records in mode `init`. A reload overwrites **every field of the record**, so the XML must carry the database values for `email_from`, `reply_to`, `partner_to`, subject and body.
- **Translations after a reload**: if the structure of the English text changed, Odoo keeps the old translated values and the `.po` (loaded after the post-migration, without overwrite) does not replace them. The reload helper drops the non-English `body_html` and `subject` of the reloaded records first.
- **`data-o-mail-quote`**: loading HTML through the ORM adds `data-o-mail-quote="1" data-o-mail-quote-node="1"` to every `<blockquote>` (the footnotes). The text is the same; `compare_databases.py` ignores them. In Odoo's chatter such a footnote can be folded as quoted text.
- **Shared code**: `compassion-modules` is also used by Nordic, which has other texts. A migration that reloads templates there must be guarded (`REQUIRED_MODULE`), and the module state to test is `IN ('installed', 'to upgrade')`: a dependent of the updated module is `to upgrade` while the migration runs.
- **Rolled-back tests**: creating a test job with the same partner and config as a pending job **merges** into it (`same_job_search`), so you render the wrong data. Pass `same_job_search=[('id', '=', 0)]`. Nothing is saved if you `env.cr.rollback()` at the end of the `odoo-bin shell` script.
- **Slow refresh (physical jobs)**: `refresh_text` regenerated the attachments (`get_correspondence_attachments`, a PDF) and counted the PDF pages again at the write of `body_html`, about 30 s each in T3527. `quick_refresh` does not (`skip_pdf_count`). `attachments_object_ids` now skips the regeneration when the objects did not change and the page count is queued (PR #2181). Measure with a timer script before optimising.
- **Greptile review comments** are often right (it found the `noupdate` reload and the `to upgrade` state) but not always (it said a field had no definition). Check each against the Odoo source and the repositories, then ask the user which to apply.
- **Duplicates**: a record that only exists in the database (`__import__.NN`) must be linked to the new xmlid in a **pre**-migration, before the data files load.
- **Version bump**: the migration folder and manifest version must be above `ir_module_module.latest_version` of the target database.
- **`.po` files**: edit with `polib` (`wrapwidth=78`, the round trip is lossless). A new entry needs `#. module: <module>` or the OCA hook `po-requires-module` fails. The msgid is the database body (`<html><body>`, `&#x27;`), so a fresh install built from the XML may not match it byte for byte.
- **Templates 56/449 and others `t-if` on `<p>`** (`<p t-if="...">`) work; the revision tool only handles the old Mako syntax.
- **`gh pr edit`** can fail on the "Projects (classic)" error: use `gh api -X PATCH`.
- A push can be refused by the sandbox classifier: ask the user for a permission rule rather than working around it.
