# Odoo translations

## Choose the catalogs

Keep English in the source strings. The repositories reject `en.po` in pre-commit. Ship translations of every new or changed user-facing string in the same PR.

- If the module has catalogs, update **every existing locale**, including for a country-specific module. Keep the filenames. Odoo loads the base language before its regional variant.
- For a module's first catalogs, use the locales in the repo's `AGENTS.md` for each country that installs **that module**; for a country-specific module, its country's locales. Also add the locales of an office that a deployment hosts when the module meets the condition the repo's `AGENTS.md` gives for it.

## Work from a fresh export

1. Export a fresh POT from a development database with the changed module installed and up to date. In the project's Odoo launcher, use `-d DB --i18n-export=TEMP_DIR/MODULE.pot --modules=MODULE --stop-after-init`.
2. Match the source diff to the export, including existing `msgid`s that gained, lost or moved an occurrence. Check that every changed user-facing string was extracted. For a first catalog, use the full export.
3. Translate against the locale's established vocabulary. Use its existing glossary when available. Otherwise derive one from that locale's translations in the module and across the repository. When adding a language, establish the glossary before translating the first entries.
4. With a PO parser, refresh each affected entry's Odoo references from the full module export in every target locale. If a second view reuses a translated string, keep its `msgstr` and include both view XML IDs. Preserve unrelated entries and remove a key only when it has disappeared from the full export.
5. Reparse each PO. For each affected key still in the export, verify its current references and a complete, nonempty translation with the source placeholders and inline markup intact. PO strings can span several quoted lines.

## Put the translation where the label is rendered

If the browser maps a result to a label, send a stable key and map it to literal `_t()` strings in JavaScript. Translate a server-rendered label in Python or QWeb. In Python, pass a literal format string and its values as separate arguments to `_()` so Odoo translates before formatting.

For browser strings, check that the module is included by `ir.http._get_translation_frontend_modules_name()`. Installed modules whose names start with `website` are included automatically. Extend the list for other modules if their strings are missing.
