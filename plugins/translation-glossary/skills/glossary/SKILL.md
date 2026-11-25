---
name: glossary
description: >-
  Compassion's agreed words in each language. Use when translating or writing
  anything Compassion says, in software or in communications (interface
  strings, .po catalogs, emails, letters, newsletters, web or social copy), in
  German, French, Italian, Swedish, Norwegian, Danish, Finnish or Polish; when
  choosing a word for sponsor, sponsorship, gift or donation; when reviewing a
  translation; or when adding a language.
---

# Compassion translation glossary

Compassion's brand words carry decisions the English does not show. This skill holds those decisions, one reference file per group of languages. The wording is the job here; how a file format or a tool carries the text (Odoo catalogs, POEditor, an email builder) belongs to that project's own rules.

## 1. Open the reference for the language

Read the whole file before writing a word. Its tables are short, and the traps sit at the end.

| Language | Reference file |
|---|---|
| German, Swiss French, Italian (`de`, `fr_CH`, `it`) | `reference/ch.md` |
| Swedish, Norwegian, Danish, Finnish (`sv_SE`, `nb_NO`, `da_DK`, `fi_FI`) | `reference/nordic.md` |
| Polish (`pl_PL`) | `reference/pl.md` |
| any other language | `reference/new-language.md`: derive a glossary first, and stop for a human's approval before translating |

The paths are relative to this file's folder, `${CLAUDE_SKILL_DIR}`.

When translating, also read what already exists in the target language for the same text or product: the other locales of the module, last year's version of the letter, the office's published pages. The English is the source, not the authority. The other languages carry the brand's decisions.

## 2. The rules every language follows

**Sponsorship is a godparent relationship.** No Compassion language uses its own cognate of "sponsor". All use a godparent word (`Pate`, `parrain`, `fadder`, `kummi`, and Polish `patron` from the same family), except Italian, which uses a support word (`sostegno`). Use the term family in the reference file, in every form: the person, the child, the relationship, the verb.

**Sponsorship is never adoption.** Compassion refuses adoption wording for this relationship, for child-protection reasons, even where other charities in that country use it (`adopcja na odległość`, `adozione a distanza`). The same goes for words that claim legal guardianship.

**Gift, donation and contribution are three things.** A *gift* is a present sent to a child, a *donation* is money given to a fund, a *contribution* is the monthly sponsorship payment. Keep them apart wherever the language can. Swedish, Norwegian and Danish cannot: one word covers gift and donation, so read the context.

**Gender-neutral when the gender is unknown.** Software rarely knows the reader's or the child's gender, and a mailing to many supporters never does. Use the form the reference gives: a paired form (`Patin oder Pate`, `parrain ou marraine`), a gender-neutral tense, or a noun phrase.

**The form of address is settled per language.** Each reference states it: `du` in German, `vous` in Swiss French, `tu` in Italian, `Ty` (capitalised) in Polish. Hold it through the whole text.

**Register follows the reader.** Field labels, model names and admin help are impersonal noun phrases. Text a supporter reads (a page, a button, an email, a letter) addresses them in the language's settled form.

**Unchanged in every language:** `Compassion`, `MyCompassion` / `My Compassion` (mirror the form the source uses), `Write&Pray`, `S2B`, payment brands (`Visa`, `Mastercard`). In software, also leave every placeholder (`%s`, `{child_name}`, `#{...}`), every tag and attribute, entities, route paths, and leading and trailing spaces exactly as in the source; translate the visible text and the `title`, `alt` and `aria-label` values.

**Check meanings that look obvious.** Short source strings mislead: in the MyCompassion portal "Code" is the postal code and "Coordinates" means contact details (French *coordonnées*). When a short string is ambiguous, open its context (the template, the form, the surrounding paragraph) before translating it.

## 3. A word the reference does not cover

Name the gap instead of filling it. When a load-bearing word (a programme name, a relationship, a recurring concept) is missing from the reference, say so, propose a term with the reasons for it, and ask before using it throughout. A word coined on the fly becomes the word everyone copies.

## 4. Hand back what the glossary should learn

The maintainers of `compassion-agent-toolkit` improve these references from the communication team's reviews. End the work with a short **Glossary proposals** list when any of these came up, and leave it empty otherwise:

- a term you had to propose because the reference lacked it, and what was decided;
- a correction a reviewer made to your wording, which the reference would have prevented;
- a contradiction between the reference and existing approved material.

Each entry: the language, the English, the term, and one line on why. Leave the installed plugin files unchanged: the maintainers edit the references in the toolkit repository.
