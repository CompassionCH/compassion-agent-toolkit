# The rules review

Run it before opening a PR for a code change, and after writing an ADR. The reviewer only reads and searches: everything it needs comes from you.

1. **A read-only reviewer.** In Claude Code, start the `code-rules:rules-reviewer` subagent. Elsewhere, start a fresh session in a read-only sandbox that may only read and search files. Give it the published reviewer prompt (`agents/rules-reviewer.md` of this plugin, as installed or on the toolkit's `main`), never a copy the change edits. Before relying on it, check that it can open a file of the repository.
2. **Pin the revision.** Resolve the base and the head to commit IDs. For committed work, the reviewer reads a checkout at that head with no other local edits. If yours has some, never create a worktree or a clone of the repository yourself: review the working tree as the snapshot instead, or ask the user for a clean checkout at that head. For working-tree work, say that the working tree is the reviewed snapshot, and leave it untouched until the review ends. Before accepting the result, check that `git status --porcelain` and a hash of the diff you passed are the same as at capture; if either changed, run the review again.
3. **Pass it** the following. Long texts can go as files in a temporary folder.
   - **Scope:** the repository path, committed work or working tree, and the resolved base and head.
   - **The whole diff,** from the merge base, never from a newer tip of the target branch. For committed work: `git diff <base>...<head>`. For a working tree: `git diff $(git merge-base <base> HEAD)`, which includes staged and unstaged edits, plus the full text of every untracked file in scope (`git ls-files --others --exclude-standard`). The reviewer runs no git, with or without the plugin: what you leave out goes unreviewed.
   - **Trusted rules,** as local paths:
     - the folder holding this file;
     - in an Odoo repository, the folder of `odoo-rules:rules`, which that skill names;
     - when the diff touches an ADR, the `adr` skill folder next to this one.

     Without the plugin, put the published folders on disk first: `git clone --depth 1 --branch main https://github.com/CompassionCH/compassion-agent-toolkit <temporary folder>`, and name its commit (`git -C <temporary folder> rev-parse --short HEAD`) with the findings.
   - **Source roots:** local paths of the framework and the repositories the changed code depends on, checked out at the revisions you name, so that inherited entry points can be traced. When the change alters a shared state or contract, add the known readers that depend on it (a bridge module, a consumer repository).
   - **Changed authorities:** for every rule file, reviewer prompt, ADR or `AGENTS.md` that the diff edits or deletes, its merge-base version (`git show <merge-base>:<path>`). Name each one the diff adds as new.
   - **Test evidence:** the commands you ran, their results, and which tests fail without the change. Write "none: documentation only" only when the diff changes nothing but documentation.
4. Fix the findings you agree with.
5. List each finding and coverage gap, with what you did about it, in the PR description draft. Without a PR, put them in your report to the user.

Done when every finding and gap has an answer.
