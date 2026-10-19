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

**Never propose** the gender / agreement lookups (`child.get('he')`, `his`, `him`, `accord_s`, `boy` from `child.get('lui')`...). They are an accepted pattern.

## Language rules (Compassion glossary)

- German: sponsorship is always *Patenschaft* / *Patenschaften*; "Hold" stays "Hold". Informal du/ihr according to `plural`.
- Italian: sponsorship is only *sostegno* / *sostegni* (never sponsorizzazione); sponsored: *sostenuto*, to sponsor: *sostenere*.
- French: sponsorship is *parrainage*.
- v14 is the reference for wording, but the v14 syntax (`${}`, `% set`) is not v18 QWeb: do not copy v14 translations of code-bearing templates.

## Pitfalls

- **Rendering engine**: `_render_template` defaults to `inline_template` in v18, which ignores `t-set` / `t-out`. Wizards that render a template body must pass `engine="qweb"` and `options={"post_process": True}`. Subjects are inline templates.
- **IDE reformat** of the scratch file puts line breaks around `<t>` elements and renders a space before punctuation. Do not push a reformatted file.
- **`noupdate`**: the data files are `noupdate="1"`; the existing databases keep their old text until a migration clears the flag. A forced reload overwrites **every field of the record**, so the XML must carry the database values for `email_from`, `reply_to`, `partner_to`, subject and body.
- **Duplicates**: a record that only exists in the database (`__import__.NN`) must be linked to the new xmlid in a **pre**-migration, before the data files load.
- **Version bump**: the migration folder and manifest version must be above `ir_module_module.latest_version` of the target database.
- **`.po` files**: edit with `polib` (`wrapwidth=78`, the round trip is lossless). A new entry needs `#. module: <module>` or the OCA hook `po-requires-module` fails. The msgid is the database body (`<html><body>`, `&#x27;`), so a fresh install built from the XML may not match it byte for byte.
- **Templates 56/449 and others `t-if` on `<p>`** (`<p t-if="...">`) work; the revision tool only handles the old Mako syntax.
- **`gh pr edit`** can fail on the "Projects (classic)" error: use `gh api -X PATCH`.
- A push can be refused by the sandbox classifier: ask the user for a permission rule rather than working around it.
