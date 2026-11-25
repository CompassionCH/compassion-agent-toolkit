# Deriving a glossary for a new language

Use this when the language has no reference file yet. It is the method that produced `pl.md`; read that file alongside as the worked example.

The languages Compassion already writes in have made decisions about its words. Read them, work out what they agreed each concept *is*, then say that in the new language.

Done when a human has approved the draft glossary. Translate nothing before that.

## 1. Gather the corpus

Collect every existing rendering of the same material:

- the other reference files in this folder;
- for software: the same module's catalogs in every shipped language (in Odoo, `<module>/i18n/*.po`), read side by side;
- for communications: the same campaign, letter or page as the other offices published it, and anything the office for the new language has already published.

Read all of it rather than a sample: the decisive word choices hide in strings that look boring.

Note where each text comes from, because it sets the register. In an Odoo catalog the `#:` reference tells you:

| reference starts with | what it is | register |
|---|---|---|
| `model_terms:ir.ui.view` | a page the user sees | the product voice |
| `model:ir.model.fields` | a field label | impersonal noun phrase |
| `model:ir.model,` | a model name | impersonal noun phrase |
| `code:` | a message from Python | usually user-facing, sometimes admin |

## 2. Find the load-bearing terms

Lay the languages side by side for the terms that recur tens of times: they cascade into every other string. For each, ask whether the languages agree. Where they reach for the same metaphor, that is the brand's real meaning, and the new language must carry it. Where one differs, find out why: it is often a connotation problem in that language, the kind you are about to meet.

## 3. Test each candidate term

A candidate passes all four:

- **Connotation.** Check a dictionary, not only intuition. Polish `sponsoring` is neutral for institutions and seedy for people.
- **Brand rules.** Adoption wording is out, whatever the sector uses (see `SKILL.md`).
- **Legal claim.** It must not promise a status that does not exist, such as legal guardianship.
- **Countability and inflection.** Walk real strings: "My sponsorships", "Ended sponsorships", "Number of sponsorships". A word with no natural plural is out, however good it sounds in the singular.

Look for a precedent before coining: a well-known charity in that country using a term for this same relationship is worth more than a better-sounding invention.

## 4. Decide the form of address

Where the language has a formal/informal choice, decide it explicitly, from these sources:

- **Donor-facing copy** of charities in that country: what supporters already read.
- **For software, Odoo's own translation** for that language, in its `portal`, `website` and `auth_signup` modules: what users of any Odoo product already see. It reversed a wrong first guess for Polish.
- **Published style guides** for the language (Microsoft and Google publish one per language).

Then check the grammatical cost: a formal register may force gender agreement the text cannot resolve.

## 5. List the language's own traps

Gendered verb forms where the subject's gender is unknown; more plural forms than English; cases, when a name or number is inserted; nouns whose grammatical gender differs from the person's; false friends.

## 6. Write the draft and stop

Write the draft in the conversation or in the working project, never in this folder, in the shape of `pl.md`:

1. the core term family, and where each form is used;
2. **rejected alternatives, each with its reason**: the most valuable part, because it stops the next person reopening a settled question;
3. the form of address and the evidence for it;
4. the other settled vocabulary;
5. the traps;
6. writing conventions: capitalisation, quotation marks, buttons, example names.

Show it to the user and **stop for approval**. Name the calls you are least sure of and what would change if they are wrong. In the Polish pass, evidence overturned two of the first three calls before a single string was written.

Once approved, add it to the toolkit by pull request: `improving.md`.

## 7. After translating

Have someone who did not translate read the result against the glossary. On the Polish pass that review found 69 corrections, among them "Coordinates", which survived the whole first pass.
