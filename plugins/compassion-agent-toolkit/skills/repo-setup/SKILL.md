---
name: repo-setup
description: For a repository maintainer — add the team's CLAUDE.md starter and safety baseline to the current Odoo repository, and offer the kit to everyone who clones it.
disable-model-invocation: true
---

# Repository setup

Run once per Odoo repository by whoever maintains it. The result is a reviewed working tree the maintainer commits: after that, teammates who open the repo and trust the folder are offered the kit, and the safety rules apply to everyone who works in it.

## 1. Identify the repository

Confirm it holds Odoo addons (folders with a `__manifest__.py`) and read its Odoo version from a manifest `version` (`18.0.1.0.0` → 18.0) or the branch name.

Done when you can name the version and the addon folders.

## 2. Safety baseline: `.claude/settings.json`

Merge `${CLAUDE_PLUGIN_ROOT}/templates/settings.json` into the repository's `.claude/settings.json`, creating it if absent. Merging keeps every existing key and rule and adds what is missing: the `attribution` setting, the `permissions.deny` and `permissions.ask` rules, the `extraKnownMarketplaces` entry and the `enabledPlugins` entry.

Show the resulting file as a diff and wait for the maintainer's yes before writing it. Walk them through each rule in one line, so the team's choices are deliberate: `git push` is denied in the baseline because pushes stay human; they may drop that line. `attribution.commit: false` removes Claude Code's `Co-Authored-By` line: the toolkit's hook adds the `Assisted-by:` trailer instead.

## 3. Instructions: `CLAUDE.md`

- **No `CLAUDE.md` yet**: draft one from `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md`. Fill each `{{…}}` from what the repository shows (version, addon folders, test command); where only a human knows the answer, write `TODO:` and list those lines for the maintainer.
- **A `CLAUDE.md` exists**: propose only the sections it lacks, as a diff. Line one carrying the Odoo version is the one addition always worth making.

Machine-specific details (paths, ports, database names, how Odoo starts on one laptop) belong in `CLAUDE.local.md`, which stays out of git: make sure `.gitignore` lists it.

## 4. Hand-off

List the changed files and suggest a commit message in the repository's style, for example `[IMP] repo: Claude Code team settings and CLAUDE.md`. The maintainer reviews and commits.
