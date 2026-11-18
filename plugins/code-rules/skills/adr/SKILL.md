---
name: adr
description: >-
  Record an architecture decision (ADR) in a Compassion code repository. Use
  when a choice is hard to reverse, surprising without context and the result
  of a real trade-off, when asked to record a decision, or when a change
  replaces one an existing ADR records.
---

# ADR

An ADR records why the code is the way it is, for the reader who would otherwise "fix" it. A rule says what to do; its ADR says why.

## 1. Test

Write one only when all three hold:

1. **Hard to reverse:** changing your mind later costs real work.
2. **Surprising without context:** a reader would ask "why this way?"
3. **A real trade-off:** there were genuine alternatives, and this one won for stated reasons.

If any is missing, stop: a comment or the commit message is enough. When the decision is settled and within the work at hand, draft the ADR. When a real choice is still open, ask the user to make it first.

## 2. Place

1. Find the repository's ADR folder: the one its `AGENTS.md` names, else an existing `docs/adr/`, `docs/decisions/` or `adr/`. Its format, numbering and file names win over [format.md](format.md), except for the status (step 4).
2. No folder yet: create `docs/adr/`.
3. When the repository's `AGENTS.md` does not name the folder yet, add this line, with the folder's path, creating the file if it is missing:
   `Decisions: docs/adr/. Read the ADR of an area before changing its pattern or deviating from it.`
4. Whenever `AGENTS.md` or the folder keeps a list of the ADRs, add the new one to it.
5. Number it after the highest existing one. The default is four digits and a short slug: `0007-carts-stay-on-their-website.md`.

## 3. Write

Use the repository's format, or [format.md](format.md). Then:

- Check every claim about existing code against the base branch and cite the path. When the same change introduces the decision, name the files in the diff that carry it out. Keep what the code does today apart from what is intended.
- Write for a public repository: roles, not people's names, and no customer, donor or other personal data.

## 4. Status

- An ADR on the default branch is accepted; its pull request is the proposal. Write no status line, or `accepted` where the folder's format has a status field. Never `proposed`.
- A merged ADR is never edited, except for one line when a later ADR replaces it: `Superseded by ADR-NNNN`, linked, in the status field where there is one. The new ADR says which one it replaces, and both changes go in the same pull request.
- Leave the files in the working tree. Never commit or push: the maintainer accepts the ADR by merging its pull request.

## 5. Review

Run the rules review described in the `rules` skill's [review.md](../rules/review.md) (`${CLAUDE_PLUGIN_ROOT}/skills/rules/review.md`). Name the new ADR as new, and pass the base version of every file the change edits. Apply what you agree with in one revision, and report the rest to the user.

Done when the ADR, its `AGENTS.md` pointer and any list entry are in the working tree, and the user has the reviewer's remaining findings.
