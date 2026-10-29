---
name: odoo-release
description: Release Odoo addons to stage or production, with release notes and live progress.
disable-model-invocation: true
---

# Release Odoo addons to production or stage

This skill connects to servers and restarts a production Odoo: it is started **only by the user** (`/odoo-release`, or resumed with it), never by Claude on its own initiative.

`$ENV` is the chosen environment block of the configuration (section 0), `$CFG` the whole configuration. `$WORK` is `<workdir_root>/<YYYY-MM-DD>-<environment>/` for this release (JSON and HTML files). Never write HTML to `/tmp` or the scratchpad: the user's browser may not be able to read it, so `workdir_root` must be a folder the browser can open. The scripts are in `${CLAUDE_SKILL_DIR}/scripts/`, the supporting documents in `${CLAUDE_SKILL_DIR}/reference/`: [server-setup.md](reference/server-setup.md) (polkit rule, log file, filestore rights, upload folder) and [slack.md](reference/slack.md) (message templates). Read them when they are needed, not before.

**Hard rules**

- Phases 1 to 5 are **read-only on the server** (only `git fetch`, and read-only probes). Nothing is pulled, stopped or updated before the operator approves in phase 6.
- Ask permission before each write to a remote server (release note upload, pull, service stop, module update, restart), and say what it does and on which server.
- Never push the technical notes anywhere. Only the user release notes go to the release-notes server, and only when `$ENV.upload_release_notes` is true.
- Do not read `odoo.conf` or `etc/*.conf` (credentials). Pass them to Odoo without opening them.
- Follow the project's own instructions (CLAUDE.md) first: if they ask for a ticket number before starting, ask it. A release has no single ticket; if there is none, say so and continue.
- Git over SSH only. Never push local repositories without asking where it goes. If something is unpushed, **tell the user and stop**; they push themselves.
- The environment must be named in every approval question and in the technical notes, so nobody approves a production deployment believing it is stage. Production is the sensitive choice: never assume it.
- Report in the language the user writes to you; the release notes use `release_notes.language`.

## 0. Environment and configuration

**First ask which server to deploy to**, with AskUserQuestion, one option per key of `environments` (for example `production`, `stage`). Never guess from earlier answers: ask at every release.

Everything specific to a person, server or organisation lives in `~/.config/odoo-release/config.json`. The skill folder holds only `config.example.json`, with placeholder values and the expected keys.

1. Read `~/.config/odoo-release/config.json`. If it does not exist, or the chosen environment or keys of `config.example.json` are missing, **ask the user for each missing value** (propose detected defaults when possible: submodules from `.gitmodules`, services from `ssh <host> systemctl list-units 'odoo*'`, git folders under the addons path, `ls` for the virtualenv and conf file, the branch checked out on the server). Create the folder and write the file; do not ask again for values already stored. A new environment is added as a new key under `environments`.
2. At the start of each release show the stored values of the chosen environment in a short table and ask whether anything changed. Update the file when it did.
3. Never write secrets in it (no passwords, no database credentials, no contents of Odoo config files).

Top-level keys:

| Key | Meaning |
|---|---|
| `repos[]` | The master repositories: `name`, `local_path` (git root on this machine), `latest_submodules` (relative paths of submodules to bring to the latest `submodule_branch` before releasing) |
| `release_notes.ssh`, `release_notes.remote_dir` | Web server and folder where the user release notes are uploaded |
| `release_notes.url_base` | Optional. Public URL of that folder (e.g. `https://notes.example.org/release-notes/`), to give the user the link once published and to check that it answers |
| `release_notes.organisation`, `audience`, `language`, `contact` | Used to write the user notes: who the readers are, the language, who to contact |
| `slack.mention` | Optional. What the Slack message starts with to alert people (e.g. `<!channel>`, `<!here>`, or empty). Default: none |
| `workdir_root` | Where release folders are created |
| `ticket_regex` | Regular expression of a ticket reference in commit messages |
| `open_command` | Command that opens a file in the user's browser (`xdg-open`, `open`...) |

Keys of an environment (`$ENV`):

| Key | Meaning |
|---|---|
| `ssh` | SSH host (alias or `user@host`) of the Odoo server |
| `branch` | Branch the master repositories are released from, locally and on the server (`18.0`, `stage`...) |
| `base_branch` | Optional. Branch that must already be contained in `branch` before releasing (stage: the production branch, `18.0`). `null` for production. See phase 1, step 0 |
| `submodule_branch` | Branch the `latest_submodules` are brought to in phase 1. `null`: do not move submodules, only check that the pointers are committed and exist on their remote. With a `base_branch` (stage), the `latest_submodules` are still brought up to their `base_branch` in phase 1, step 0 |
| `repo_paths` | Per repository name, its git root **on the server** (it may be named differently there) |
| `python` | Python of the Odoo virtualenv on the server. **Always** use it on the server, never the system Python |
| `odoo_dir`, `odoo_bin`, `update_conf` | Folder from which Odoo is started, the `odoo-bin` path and the config file used for updates, both relative to `odoo_dir` |
| `services` | Odoo systemd services, in the order to **stop**; they are started in the reverse order |
| `use_sudo` | Whether `systemctl` needs `sudo` |
| `update_log_dir` | Where the update log is written on the server |
| `upload_release_notes` | Whether the user release notes are written and uploaded for this environment (usually production only) |
| `presence` | `true`: before the approval, show how many people are checked in (HR attendance), see phase 6. Usually production only |
| `deferral` | Object, usually production only. `enabled`: offer to defer the deployment; `timezone` (e.g. `Europe/Zurich`); `slots`: list of `{"label", "time"}` (`time` is `HH:MM`, 24 h, in that timezone); `minutes_per_module`: estimated downtime per module to update (default 1). Absent or `enabled: false` (stage): the release is always immediate |

**Asked at every release, never stored:** the environment, the database name (phase 3), the deployment time (phase 6, when `deferral` applies) and the approvals. Offer the previous database name of the same environment as the first option when you know it from this conversation, but let the user confirm it.

In the rest of this file `repo.local_path`, `$ENV.ssh` and so on refer to these keys.

## 1. Check the local repositories (blocking)

For each repository of `repos[]`, and for each of its `latest_submodules`:

**Fetch first, always, before any count, comparison or merge.** In each master run `git fetch --prune && git submodule foreach --recursive 'git fetch --prune'`. A plain `git fetch` in a master only fetches the submodules whose pointer moved, so the other submodule remotes stay stale and a comparison with `origin/<branch>` silently misses commits (stage release 2026-10-29: 4 commits of `compassion-switzerland` were missed that way). Compare and merge only fetched `origin/...` refs, never local branches, which may be behind; fast-forward the local branches you use afterwards (step 1).

0. **Only when `$ENV.base_branch` is set (stage): is `branch` behind the base branch?** Count `git rev-list --count origin/<branch>..origin/<base_branch>` in each master **and, for each `latest_submodules` entry, the commits of the submodule's `origin/<base_branch>` that are not in the pointer recorded by the master's `origin/<branch>`** (`git -C <sub> rev-list --count $(git rev-parse origin/<branch>:<sub>)..origin/<base_branch>`). The master's base branch may itself point to an older submodule commit than the submodule's base branch tip, so a master count of 0 does not mean stage is up to date. A non-zero count means changes already on the production branch are missing from stage. Show the number of commits per repository and per submodule (`git log --oneline origin/<branch>..origin/<base_branch>`) and **ask the user** (AskUserQuestion, naming repo, branches and remote) whether to update `<branch>` from `<base_branch>`, **including pushing `origin/<branch>`** (the server pulls from there). If **no**, continue without it and flag in the technical notes that stage lacks those production changes. If **yes**, per master repository, with a clean working tree:
   - **Before merging, check what stage would lose.** List the commits only on `<branch>` (`git log origin/<base_branch>..origin/<branch>`) and the removals or reverts on `<base_branch>` since the merge base (`git log --grep='^Revert\|^REM' <merge-base>..origin/<base_branch>`), in the masters and in their `latest_submodules`. Stage often carries work that production does not (a feature under test, possibly reverted on the base branch): a merge would silently undo it. If there are such commits, show them, say what the merge would remove, and offer: merge anyway, cherry-pick the base commits instead, or skip the update. Also check the project's memory notes about work kept on `<branch>`.
   - If a submodule pointer diverged (neither commit is the ancestor of the other) and the submodule has its own `<branch>` on its remote, the merge must happen **in the submodule first** (same questions, same rules, push the submodule, then bump the pointer in the master). Otherwise stop and ask.
   - **Latest submodules.** For each `latest_submodules` entry with a gap (see the count above), merge the submodule's `origin/<base_branch>` into its `<branch>` (create the tracking branch if it is absent locally; if the submodule has no `<branch>` on its remote, bump the pointer to `origin/<base_branch>` instead), push the submodule, then commit the new pointer in the master, even when the master's merge itself is a no-op. Submodules **not** in `latest_submodules` (OCA, third party) stay at their recorded pointer, even when their upstream is far ahead: do not report them as gaps.
   - `git checkout <branch> && git pull --ff-only`, then `git merge --no-ff origin/<base_branch> -m "<ticket + > UPD merge <base_branch> into <branch>"` (commit message style of the project, ticket first if there is one; fast-forward when possible).
   - Submodule pointers: if both sides moved a pointer, keep the base branch's pointer when the stage one is its ancestor (`git merge-base --is-ancestor`); otherwise see the submodule rule above. Any other conflict: `git merge --abort`, report and stop. Never resolve code conflicts on your own.
   - Run the project's checks if the project asks for them, show `git diff --stat origin/<branch>..<branch>`, then push `origin <branch>` (the approval above covers the merge and this push, for these repositories only; say where it went).
   - Then continue with the checks below on the updated branch. Go back to the branch the checkout was on before if the user did not ask to stay.
1. `git fetch`. Masters: check that the checkout is on `$ENV.branch`, the working tree is clean, and `git status -sb` shows no ahead/behind. Submodules: same, on `$ENV.submodule_branch` (skip the branch check when it is `null`). If behind its remote branch, fast-forward (`git pull --ff-only`) after asking; this is the "latest changes" step. Never switch branches with uncommitted changes: stop and report.
2. For each master repository: the submodule pointers are committed (`git status` shows no `modified: <submodule> (new commits)`) and the commit is pushed (`git rev-list origin/<branch>..<branch>` is empty). Check that each pointer's commit exists on the submodule's remote (`git -C <sub> branch -r --contains <sha>` is not empty).
3. Print a table repo / branch / clean / pushed. Any failure stops the release: say which repo and what to do. The local checkout may be on another branch (a feature branch, or `18.0` while releasing stage): do not switch away from uncommitted work, and ask before switching a clean checkout to `$ENV.branch`.

## 2. Fetch the server (do not pull)

Check that every `$ENV.repo_paths` entry exists and is the right repository (`ssh <ssh> 'cd <path> && git remote get-url origin'`, compare with the local `origin`). If a path is wrong, list the folder, ask the user and fix the configuration. Then, for each repository:

```bash
ssh <ssh> "cd <path> && git fetch --recurse-submodules=on-demand && git status -sb | head -3 && git rev-parse HEAD @{u} && git submodule status --recursive"
```
`git fetch` only downloads objects (including the new commits of the submodules whose pointer moved); it changes neither the working tree nor the checked-out commits. Do not run `git pull`, `git submodule update` or `git checkout` in this phase. Warn if the server has local modifications (`git status --porcelain` not empty), is not on `$ENV.branch`, or if `@{u}` differs from the local `$ENV.branch` commit (not pushed, or someone pushed elsewhere). A submodule on the server that is not at the pointer recorded by the current HEAD (`+` in `git submodule status`) is **drift**: the pull resets it. Phase 3 analyses what that reset changes; the release does not go on until the user has seen it.

### Preflight: can the services be controlled without a password?

Check it here, read-only, so a missing permission is known before the release and not at the stop step (a manual `sudo` stop and start adds minutes of downtime):

```bash
ssh <ssh> 'for u in <services>; do
  if [ "$(systemctl is-active $u)" = active ]; then
    pid=$(systemctl show $u -p MainPID --value)
    systemctl --no-ask-password start $u >/dev/null 2>&1 && echo "$u: allowed (pid $pid untouched: $([ "$pid" = "$(systemctl show $u -p MainPID --value)" ] && echo yes || echo NO))" || echo "$u: NOT allowed"
  else echo "$u: not active, not tested (a start would change its state)"; fi
done
for c in ssh.service sshd.service; do [ "$(systemctl is-active $c)" = active ] && break; done
[ "$(systemctl is-active $c)" = active ] && { systemctl --no-ask-password start $c >/dev/null 2>&1 && echo "control $c: allowed (rule TOO BROAD)" || echo "control $c: refused (good)"; } || echo "control: no active ssh unit found, not tested"
sudo -n true 2>/dev/null && echo "sudo without password: yes" || echo "sudo without password: no"'
```
This uses the real authorization path. `systemctl start` on a unit that is already running is a no-op (same pid), and polkit decides before systemd looks at the state, so it proves the rule matches the user and the unit; the rule grants `start`, `stop` and `restart` together, so stop is covered too. Every probe is guarded by `is-active`, so it never starts anything that was stopped: the SSH unit is the control because it is always running while you are connected (a too broad rule would "start" it, a no-op). Only a unit that stops between the check and the probe (a few milliseconds) could be started by it. Never loop over other units.
- All `allowed`, control refused: stop and start run by the skill, with no manual step.
- `NOT allowed` (and no passwordless sudo): tell the user now, point to [reference/server-setup.md](reference/server-setup.md) for the polkit rule, and say that the stop and start will have to be run by them in their own terminal, which adds to the downtime. Offer to continue anyway. Never try to work around it (no password in a command, no `sudo -S`, no edit of sudoers or polkit by yourself).

## 3. What will the pull bring

The diff is computed **on the server**, between what is currently checked out there (`HEAD` and each submodule's current commit) and what `git pull && git submodule update` would give (`@{u}` and the submodule commits its tree points to). Run the script over SSH from stdin; it is read-only and nothing is copied to the server:

```bash
ssh <ssh> "$(printf '%q ' <python> - --ticket-regex '<ticket_regex>' <server path of each repo>)" < "${CLAUDE_SKILL_DIR}/scripts/release_diff.py" > "$WORK/diff.json"
```
`printf '%q'` protects the regular expression from the remote shell (ssh re-parses the command line; without it `\bT\d{3,6}\b` arrives mangled). Check that the JSON starts with `[`.

Per repository, recursively, it gives the commits, the tickets found in the commit messages, and the Odoo modules (nearest folder with `__manifest__.py`, as at the new commit) with their changed files. Tests and docs are ignored. It also lists new and removed modules. If a git command fails with "dubious ownership", the script already passes `safe.directory` per command; never write to the server's git configuration. If it reports a missing submodule commit, run `git -C <submodule> fetch` on the server (still read-only) and rerun.

- **Drift.** Every submodule whose checked-out commit differs from the pointer the pull gives is analysed, moved or not; an entry with `drift: true` says what is checked out and what `git submodule update` will reset it to. Show every such entry to the user (what the reset changes, which modules) and **do not go on before they decide** (accept the reset, or fix the server first).
- **New modules** (`new: true`): the skill never installs modules (no `-i`). They are listed in the technical notes as "not installed by this release, install manually if wanted" and are left out of `-u`.
- **Database-affecting or not.** `update: true` means something in the module affects the database: data/view files (xml, csv), migration scripts, translations, model definitions, manifest changes other than version, `post_load`, author/summary-type keys and assets. Model definitions are decided on the **syntax tree**: the field definitions (`fields.X(...)`, `models.Constraint`...) and the `_name`, `_inherit`, `_inherits`, `_table`, `_sql_constraints` attributes of the old and the new file are compared, so ordinary method code (a `domain = [...]` variable) is not a schema change. Modules with only runtime code changes have `update: false`: leave them out of `-u`, the restart picks them up, and list them in the technical notes as "code only, restart suffices". **The script cannot see** a stored compute whose `@api.depends` changed, a changed default, or data written by Python: read the diffs of the code-only modules and move one into the list if it touches the database.
- Check `__manifest__.py` dependency changes by reading the diff. To read a diff yourself: `ssh <ssh> "git -C <path> diff HEAD @{u} -- <file>"` (inside a submodule: `git -C <sub> diff HEAD <sha>`; add `-c safe.directory=<sub>` if git refuses). Read the actual diffs of the user-visible commits; do not trust commit subjects alone.

**The database name and the installed modules.** Ask for the database name now (offer the previous one first). Then, read-only, with the same call pattern as `presence.py`:
```bash
ssh <ssh> "$(printf '%q ' <python> - <odoo_dir>/<odoo_bin> <odoo_dir>/<update_conf> <DB>)" < "${CLAUDE_SKILL_DIR}/scripts/installed_modules.py"
```
It prints the installed modules and the modules whose state is pending (`to upgrade`, `to install`, `to remove`), reading `ir_module_module` through Odoo's configuration loader: credentials are never read, no module is loaded (so no pending upgrade can start), nothing is written.
- **`pending` must be empty.** If a module is `to upgrade` or `to install`, an earlier update did not finish and Odoo would resume it at the next load: stop and tell the user.
- **Keep only the installed modules in the `-u` list.** Odoo's `-u` only touches modules in state `installed` or `to upgrade`; an uninstalled name just logs a warning. A module that is changed but not installed in this database is left out and listed in the notes as "changed, not installed here". Without this filter, a release whose changes are all in modules this database does not install would announce a downtime for nothing.

**Deployment mode.** Once the filtered `-u` list is known:
- **Update mode**: the list is not empty. Phase 7 pulls, stops the services, updates the modules, starts the services. Estimated downtime: `deferral.minutes_per_module` (default 1) minutes per module in the list, at least 1 minute (say "about N minutes"; the real figure is reported afterwards).
- **Restart mode**: the list is empty (only code-only changes, or nothing). Phase 7 pulls and **restarts** the services (`systemctl restart`, which the polkit rule also allows), with no stop, no update, no start chain. The deployment is **always immediate** (no time question, no deferral), and the user release notes **do not mention any downtime or planned time**. Say it to the user in the summary: "no module to update, simple restart".

## 4. User release notes (only when `$ENV.upload_release_notes`)

Skip this phase when `upload_release_notes` is false (say so, and offer to write them anyway if the user wants).

Write `$WORK/release-notes-<YYYY-MM-DD>.html`, self-contained (inline CSS, no external fonts or scripts), responsive, light and dark theme, neutral design. Language `release_notes.language`, in **simple words for `release_notes.audience`** (not developers). Structure:

- Title "Odoo release <date>" and one-paragraph summary.
- Sections grouped by the areas those users know, each change as one short sentence on **what changes for them** and where in Odoo to see it. Fixes: "Fixed: ..." in plain words.
- No ticket numbers, commit hashes, module or technical names. Leave out purely technical changes (refactors, tests, CI, log or security internals), and say so to the operator in the chat when you drop something.
- Date, and "Questions: contact `release_notes.contact`".
- The notice has two styles in the page CSS, so a later swap needs no CSS edit: `.notice` (amber, planned or running update) and `.notice.done` (green, update finished: `background:var(--tag-new);color:var(--tag-new-ink)`).
- A placeholder comment `<!-- maintenance-notice -->` right under the summary. **Update mode only**: phase 6 replaces it with the notice about the planned downtime. In restart mode, leave no notice and no mention of a downtime or a time.

Check the folder naming on the web server before choosing the file name: `ssh <release_notes.ssh> 'ls -lat <remote_dir> | head'` (read-only) and follow the pattern; there may be an index page to update, ask before editing it. Note the folder's owner: an upload may need rights the user does not have (see [reference/server-setup.md](reference/server-setup.md)).

## 5. Technical notes (local only)

Write `$WORK/technical-notes-<YYYY-MM-DD>.html`, self-contained, for the IT approver:

- Header: **the environment and host in a prominent badge**, date, who prepared it, `HEAD -> new` SHAs per repository, branch, **the deployment mode** (update, or simple restart), and for production the people connected at that moment, the chosen time and the estimated downtime (completed in phase 6).
- Link to the user release notes when they exist (relative link to the local file, and the web URL once uploaded).
- Table of resolved tickets: reference, commit subject, repository, commit hash (every ticket found in the commits; commits without a ticket listed separately).
- **Modules to update**: the exact `-u` list (installed modules only; never `-i`; database-affecting modules only; comma separated, copy-ready), with per-module the reasons and files that triggered it, then a second table of the code-only modules left out of `-u`, the modules changed but not installed in this database, flags for migrations, new modules (not installed by this release), deleted/renamed modules, **submodule drift** and what its reset changes, manifest dependency changes (a new dependency of an updated module that is not installed yet is installed by Odoo itself during `-u`: name it as a risk), and new Python requirements (`requirements.txt` changes to install in the virtualenv **before** the update).
- Risks and checks: migrations (what data they touch), changes to `ir.cron`, security files (`ir.model.access.csv`, rules), data files with `noupdate`, a recommendation to back up the database.
- The commands that approval will run, verbatim.

Open the file with `open_command` and show a short summary in chat.

## 6. Approval (blocking)

Summarise: **environment and host**, **deployment mode** (phase 3), repos and commit counts, number of tickets, module list, drift if any, services affected.

**6a. Who is connected (only when `$ENV.presence`, production).** Read-only, with the database name of phase 3:
```bash
ssh <ssh> "$(printf '%q ' <python> - <odoo_dir>/<odoo_bin> <odoo_dir>/<update_conf> <DB>)" < "${CLAUDE_SKILL_DIR}/scripts/presence.py"
```
It counts the employees checked in right now (an attendance without check-out, started in the last 16 hours) out of the active employees, through Odoo's configuration loader: credentials are never read or shown, no module is loaded, nothing is written. Show "N of M employees are checked in right now". If `available` is false (`hr_attendance` not installed) or the script fails, say so and continue without the figure. Never list names.

**6b. When to deploy (only in update mode, only when `$ENV.deferral.enabled`).** Ask with AskUserQuestion: **now**, one option per configured slot (label and time, the next occurrence in `deferral.timezone`: a slot already past today is offered for tomorrow), or **custom time**. Show the estimated downtime and the connected people next to the question. In restart mode, and for an environment without `deferral`, the release is always immediate: do not ask. If the chosen time is less than 30 minutes away, say so: the users will get very little warning, and offer the next slot instead.

**6c. The release notes (only when `$ENV.upload_release_notes`).**
- **Update mode:** replace `<!-- maintenance-notice -->` in the notes with a clear notice, in `release_notes.language`, in the notes' style: the cutoff and the estimate, e.g. "Planned update: Odoo will be unavailable on <date> from <HH:MM> for about <N> minutes. Please save your work before." (an immediate deployment: "Odoo will be unavailable for about <N> minutes, starting now."). Time and date in `deferral.timezone`.
- **Restart mode:** the notes carry no notice and no downtime information.
- The notes are **published now, even when the deployment is deferred**, so the users know in advance. The upload is its own approval, and it also covers the second upload after the deployment (the "done" banner, phase 7 step 6): say so in the question.
```bash
scp "$WORK/release-notes-<date>.html" <release_notes.ssh>:<remote_dir>/
ssh <release_notes.ssh> 'chmod 644 <remote_dir>/release-notes-<date>.html && ls -l <remote_dir>/release-notes-<date>.html'
```
The `chmod 644` keeps the file readable by the web server whatever the uploader's umask. When `release_notes.url_base` is set, check `curl -sI <url_base>release-notes-<date>.html` answers 200 and give the link to the user. Do not use `sudo` for the upload: if the folder is not writable by the user, point to [reference/server-setup.md](reference/server-setup.md) instead of working around it.

**6c-bis. Slack message** (whenever release notes are published): prepare it from [reference/slack.md](reference/slack.md) (upcoming for a deferred deployment, running for an immediate one) and show it in the chat, ready to paste.

**6d. Approval.** Ask with AskUserQuestion, naming the environment, the mode and the time: approve the deployment to `<environment>` (now, or at `<time>`), or stop. Without a clear approval, stop here and leave the files in `$WORK`.

**6e. If the deployment is deferred.** Write `$WORK/deployment.json` with **what was approved, resolved, not references to the config**: environment, time, mode, the SHAs of phase 2, the `-u` list, the database name, the resolved `ssh` target, the repository paths on the server, the services, the python and the update command, the release notes URL. Add the time and estimate to the technical notes and tell the user.

The deployment is **never started by a scheduled task on its own**: this skill can only be started by the user. If the user wants a reminder, schedule a one-shot prompt for that time with the session's scheduling tool (`CronCreate`, load it with `ToolSearch`) whose only job is to **remind the operator to type `/odoo-release` and resume**; otherwise the user starts the skill again at that time.

**Resume mode** (the user types `/odoo-release` again and says to resume): read `$WORK/deployment.json`; re-run phases 1 and 2 and the preflight; verify that the server `HEAD` and `@{u}` still equal the SHAs of the file, that the `-u` list is unchanged, and that the **ssh target, repository paths, database, services and command resolved from the current config are identical to the recorded ones**: stop at the first difference (someone pushed, or the config changed), the plan and the published notes are stale, recompute from phase 3. Never run a deferred deployment before its time. Then show the re-checked state (same SHAs, same list, people checked in now, the running Slack message) and **ask for a fresh "go"** (AskUserQuestion): the previous approval was given hours ago and nobody may be watching. Without that go, do nothing.

## 7. Deploy (after approval)

The **database name** is the one of phase 3. Run each step separately, stop at the first error, and print a progress line before each (`[1/6] Pulling ...`), with the environment in the first line. `<sudo>` is `sudo ` when `use_sudo`.

If `sudo` asks for a password (check with `ssh <ssh> sudo -n true`), you cannot answer it: first try `systemctl --no-ask-password <action>` (polkit may allow it; a denial changes nothing). If it is denied, ask the user to run the command **in their own terminal** (`ssh -t <ssh> 'sudo systemctl ...'`): the `!` prefix of this session has no terminal, so `sudo` cannot prompt there. Continue when they confirm, and verify the result yourself with `systemctl is-active` and the server's `date -u`. Never put a password in a command.

**Slack (update mode):** when the deployment starts (right after the approval for an immediate one, at the time for a deferred one), show the **running** message again in the chat, ready to paste, before the pull. In restart mode, show the new-release message once the restart is done.

**Restart mode** (phase 3): do step 1, then replace steps 2 to 5 by a single restart: note the time, `<sudo>systemctl restart <services>` (one command, the services in the stop order), check `is-active` and the startup log as in step 5, and stop the downtime clock when the main service accepts requests. Then step 6. No update, no Monitor.

1. **Pull**: for each repository `cd <path> && git pull --ff-only && git submodule update --init --recursive`. Check that `git rev-parse HEAD` now equals the SHA from phase 2 and `git submodule status --recursive` shows no `+`/`-`, **and that `git status --porcelain` is empty in every repository and submodule**: a file git could not replace (a folder owned by another user, for example) leaves the old version in the tree, and the old migration would run. Install new requirements if the notes flagged them (with `<python> -m pip`, ask first).
1b. **Pre-stop check, with the services still running (no downtime yet).** Other Odoo processes connected to the database (`ps -eo pid,etime,cmd | grep odoo-bin`; forgotten `odoo-bin shell` sessions of colleagues are common) and the free disk space of `<update_log_dir>`. Run `sessions.py` (same call pattern as `presence.py`, from `${CLAUDE_SKILL_DIR}/scripts/`): before the stop its result is **advisory**, because Odoo's own workers have short transactions; report only the sessions it lists as `idle in transaction` or in a transaction for a long time, and ask the user to close them if they are not Odoo's. Leave other people's idle processes alone.
2. **Stop services**: `<sudo>systemctl stop <services in order>`, then verify with `systemctl is-active` (all must be `inactive`). **Start the downtime clock here**: note the time of the stop (read it on the server with `ssh <ssh> date -u +%FT%TZ`, so local clock differences do not matter).
2b. **Blocker check, right after the stop (seconds, not minutes).** Run `sessions.py ... --after-stop`: the services' own sessions are gone, so every session still in a transaction is a **real blocker** (it holds table locks, even with a plain `SELECT`, and makes a schema change wait). `blocking` must be 0. If not, tell the user at once which session, ask them to close it, and re-run; do not launch the update meanwhile. Sessions can still connect after the check.
3. **Update modules** (note its start and end time too). Launch it detached, so the SSH call returns at once, with a pid file and an exit file that the watcher reads:
   ```bash
   ssh <ssh> 'cd <odoo_dir> && L=<update_log_dir>/odoo-update-<date>.log && rm -f "$L" "$L.exit" "$L.pid" "$L.out" && umask 002 && { setsid sh -c "<python> <odoo_bin> -c <update_conf> --logfile \"$L\" --log-level info -d <DB> -u <modules> --no-http --stop-after-init > \"$L.out\" 2>&1 & echo \$! > \"$L.pid\"; wait \$!; echo exit=\$? > \"$L.exit\"; date -u +%FT%TZ >> \"$L.exit\"" > /dev/null 2>&1 < /dev/null & } && echo started'
   ```
   - **`--logfile` on the command line** makes the log independent of what `update.conf` says (a `logfile` line there would otherwise take the log away from a plain redirect); `<log>.out` keeps what the process prints on stdout and stderr (a crash before logging starts). `update.conf` must not set `syslog`, which wins over `logfile` ([reference/server-setup.md](reference/server-setup.md)).
   - **The `&&` chain stops if `cd` fails**, and nothing is launched. Only the detached process is put in the background, inside the braces: without them (a `;` or a plain `&` on a chain) the SSH call **blocks until the update is over**. The call must return within a second or two; if it does not, something is wrong, say so.
   - **`umask 002`**: the update runs as the SSH user, not as the service user; what it creates (filestore) must stay writable by the service's group.

   **Immediately after launching, without waiting to be asked, start the live stream** with the Monitor tool (`timeout_ms` 1800000, re-arm when it expires and the update is still running), using `${CLAUDE_SKILL_DIR}/scripts/watch_update.sh`:
   ```bash
   ssh <ssh> sh -s -- <update_log_dir>/odoo-update-<date>.log <modules> 30 < "${CLAUDE_SKILL_DIR}/scripts/watch_update.sh"
   ```
   It prints a heartbeat every 30 seconds (the module Odoo is loading, how many of the requested modules were reached and finished, warning and error counts, how long the log has been quiet), prints migration scripts and every `ERROR` / `CRITICAL` / `Traceback` line at once, and ends with `DONE: exit=<code>` (with what the process printed on stdout/stderr if it failed), or `DONE: unknown (process gone)` if the process dies without writing its exit file: never read that as a success. When the log has been quiet for 60 seconds or more, the heartbeat also says what the process is doing and the CPU and I/O since the last heartbeat, which tells a slow migration from a hang.

   **Reporting rules (hard).** The user must never have to ask for progress. (a) **Immediately after the launch and the Monitor start, in the same turn, write**: "Update started at <HH:MM>, <n> modules; one progress line every 30 seconds below." (b) **From the moment the services are stopped, never go more than 30 seconds without writing a line to the user**, including between steps and while you run checks: say what you are doing and why ("checking X because Y"). An unexpected finding is reported at once, not investigated silently. (c) **Every Monitor event gets a message from you**, so the user sees it: the notifications are for you, the user only sees what you write. Relay each event in **one short line** (time, module, n/total, and anything new: a migration, an error, a long silence with its diagnosis). Do not repeat unchanged information at length. A long quiet period is not a failure: say what the diagnosis line says, do not kill anything, and only suggest options (wait, abort) when the quiet lasts over 10 minutes or an error appears. Stop the Monitor when `DONE` arrives.
4. **Evaluate**: the update succeeded only if (a) the process exited 0, (b) the log has no `Traceback` and no `CRITICAL`, and shows `Modules loaded.`, (c) every `ERROR` line was shown to the user and judged (an error that is a configuration notice logged at every start is not a failure; anything else is), and (d) `installed_modules.py` reports **no pending module** (`to upgrade`, `to install`): `Modules loaded.` alone does not prove that the requested modules were updated. Otherwise **do not restart**: show the errors with their context, the log path, and propose options (fix and rerun, roll back the code with `git reset` plus a database restore, which is a decision for the user). The services stay stopped until the user decides.
5. **Restart**: `<sudo>systemctl start <services in reverse order>`, check `is-active` for all and the startup log for errors. **Stop the downtime clock** when the main service is `active` and answers requests (and note that time). If the update failed and the services stay stopped, report the downtime as ongoing since the stop time.
6. **Report**: what was done, **the downtime of the Odoo server, always** (services stopped at `<time>`, back at `<time>`, total `<mm:ss>`, with the part spent on the module update separately; in update mode also the estimate from phase 3 next to the real figure; in restart mode the downtime of the restart), the environment, warnings seen, link to the technical notes. Append the same figures to the technical notes file (a short "Deployment result" section) so the release has a record. Remind the user to check the site and, if the notes were uploaded, share their URL (the Slack message already carries it).

   **Update the published release notes (update mode, when the notes were uploaded).** Once the site is confirmed answering, replace the notice in `$WORK/release-notes-<date>.html` (the `<div class="notice">…</div>` of 6c) by a done notice, in `release_notes.language`, with the **real** downtime (rounded to the minute, never the estimate) and the real times of the stop and the start in `deferral.timezone`:
   ```html
   <div class="notice done">Update done: Odoo was unavailable for about <N> minutes today, from <HH:MM> to <HH:MM>. Everything is back and the changes below are live. Thank you for your patience.</div>
   ```
   If the update failed or the services were not restarted, do not publish a "done" notice: leave the notice as it is and tell the user. Upload again with the same `scp` and `chmod 644` as in 6c (the approval of 6c covers it), then verify what is served: `curl -s <url_base><file>` has the same checksum as the local file and contains `Update done`. Show the "back online" Slack message ([reference/slack.md](reference/slack.md)) with the real downtime. In restart mode the notes carry no notice: nothing to update.

After an aborted or failed update, **never start any Odoo process on that database** (not even `odoo-bin shell` for a "read-only" check) until module states are checked with `installed_modules.py` (it loads no module): Odoo applies modules still marked `to upgrade` when it loads the database, so a new process silently resumes the upgrade, concurrently with any other update. Also tell the user before they start a manual update that no other Odoo process may use the database at the same time.

If the SSH session drops mid-update, do not start a second update: check the process (`pgrep -af odoo-bin`) and the log first.
