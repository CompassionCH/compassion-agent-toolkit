---
name: rules
description: >-
  Compassion's shared code rules, one file per subject, and the rules review
  before a pull request. Use in a Compassion code repository when writing or
  reviewing tests, fixing a bug or a security hole, adding a guard or changing
  what a state means, handling failures of outside calls or background work,
  writing comments or module docs, or preparing a PR.
---

# Code rules

Open only the subject files that match the change.

| When you | Open |
|---|---|
| write, fix or review tests | [tests.md](tests.md) |
| fix a bug or a hole, add a guard, or change what a state means | [sibling-paths.md](sibling-paths.md) |
| call an outside service, catch errors, run a batch, or add a side task to a flow | [failure-handling.md](failure-handling.md) |
| write or change comments, docstrings, help texts or module docs | [comments-and-docs.md](comments-and-docs.md) |
| prepare a PR, its description, or answers to review | [pr-hygiene.md](pr-hygiene.md) |

In an Odoo repository, `odoo-rules:rules` covers access rights, transactional side effects and translations.

What differs per repository (what it serves, its languages, its dependencies, its checks) is in its `AGENTS.md`. Its decisions are in the ADR folder its `AGENTS.md` names, by default `docs/adr/`. Read the ADR of an area before changing its pattern or deviating from it, and record a new decision with `code-rules:adr`.

**Before opening a PR,** run the rules review: [review.md](review.md). The folder it asks for is this one, `${CLAUDE_SKILL_DIR}`.
