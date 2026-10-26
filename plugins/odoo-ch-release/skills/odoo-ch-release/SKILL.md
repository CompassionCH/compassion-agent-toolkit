---
name: odoo-ch-release
description: Release Odoo custom addons to a production or stage server (asks which). Checks that the local repositories are committed and pushed on the environment's branch, fetches (without pulling) the server over SSH, computes what a pull would bring, writes technical notes (local, for the IT approver) and user release notes (uploaded to a release-notes web server for production), asks for approval (production: shows who is connected and offers to defer the deployment to a quiet moment), then pulls, stops the Odoo services, updates the modules and restarts, or only restarts when no module needs an update. Use for "deploy to production", "deploy to stage", "push the changes to prod", "release to stage", "prepare the release notes".
---

# Release Odoo addons to production or stage

`$SKILL` is the folder this file is in. `$ENV` is the chosen environment block of the configuration (section 0), `$CFG` the whole configuration. `$WORK` is `<workdir_root>/<YYYY-MM-DD>-<environment>/` for this release (JSON and both HTML files). Never write HTML to `/tmp` or the scratchpad: the user's browser may not be able to read it, so `workdir_root` must be a folder the browser can open.

**Hard rules**

- Phases 1 to 5 are **read-only on the server** (only `git fetch`). Nothing is pulled, stopped or updated before the operator approves in phase 6.
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
| `release_notes.organisation`, `audience`, `language`, `contact` | Used to write the user notes: who the readers are, the language, who to contact |
| `workdir_root` | Where release folders are created |
| `ticket_regex` | Regular expression of a ticket reference in commit messages |
| `open_command` | Command that opens a file in the user's browser (`xdg-open`, `open`...) |

Keys of an environment (`$ENV`):

| Key | Meaning |
|---|---|
| `ssh` | SSH host (alias or `user@host`) of the Odoo server |
| `branch` | Branch the master repositories are released from, locally and on the server (`18.0`, `stage`...) |
| `base_branch` | Optional. Branch that must already be contained in `branch` before releasing (stage: the production branch, `18.0`). `null` for production. See phase 1, step 0 |
| `submodule_branch` | Branch the `latest_submodules` are brought to in phase 1. `null`: do not move submodules, only check that the pointers are committed and exist on their remote |
| `repo_paths` | Per repository name, its git root **on the server** (it may be named differently there) |
| `python` | Python of the Odoo virtualenv on the server. **Always** use it on the server, never the system Python |
| `odoo_dir`, `odoo_bin`, `update_conf` | Folder from which Odoo is started, the `odoo-bin` path and the config file used for updates, both relative to `odoo_dir` |
| `services` | Odoo systemd services, in the order to **stop**; they are started in the reverse order |
| `use_sudo` | Whether `systemctl` needs `sudo` |
| `update_log_dir` | Where the update log is written on the server |
| `upload_release_notes` | Whether the user release notes are written and uploaded for this environment (usually production only) |
| `presence` | `true`: before the approval, show how many people are checked in (HR attendance), see phase 6. Usually production only |
| `deferral` | Object, usually production only. `enabled`: offer to defer the deployment; `timezone` (e.g. `Europe/Zurich`); `slots`: list of `{"label", "time"}` (e.g. the 10am break, the lunch break, 5pm; `time` is `HH:MM`, 24 h, in that timezone); `minutes_per_module`: estimated downtime per module to update (default 1). Absent or `enabled: false` (stage): the release is always immediate |

**Asked at every release, never stored:** the environment, the database name (phase 6 when `presence` is on, otherwise phase 7), the deployment time (phase 6, when `deferral` applies) and the approvals. Offer the previous database name of the same environment as the first option when you know it from this conversation, but let the user confirm it.

In the rest of this file `repo.local_path`, `$ENV.ssh` and so on refer to these keys.

## 1. Check the local repositories (blocking)

For each repository of `repos[]`, and for each of its `latest_submodules`:

0. **Only when `$ENV.base_branch` is set (stage): is `branch` behind the base branch?** After `git fetch`, in each master repository count `git rev-list --count origin/<branch>..origin/<base_branch>`. A non-zero count means changes already on the production branch are missing from stage. Show the number of commits per repository (`git log --oneline origin/<branch>..origin/<base_branch>`) and **ask the user** (AskUserQuestion, naming repo, branches and remote) whether to update `<branch>` from `<base_branch>`, **including pushing `origin/<branch>`** (the server pulls from there). If **no**, continue without it and flag in the technical notes that stage lacks those production changes. If **yes**, per master repository, with a clean working tree:
   - **Before merging, check what stage would lose.** List the commits only on `<branch>` (`git log origin/<base_branch>..origin/<branch>`) and the removals or reverts on `<base_branch>` since the merge base (`git log --grep='^Revert\|^REM' <merge-base>..origin/<base_branch>`), in the masters and in their `latest_submodules`. Stage often carries work that production does not (a feature under test, possibly reverted on the base branch): a merge would silently undo it. If there are such commits, show them, say what the merge would remove, and offer: merge anyway, cherry-pick the base commits instead, or skip the update. Also check the project's memory notes about work kept on `<branch>`.
   - If a submodule pointer diverged (neither commit is the ancestor of the other) and the submodule has its own `<branch>` on its remote, the merge must happen **in the submodule first** (same questions, same rules, push the submodule, then bump the pointer in the master). Otherwise stop and ask.
   - `git checkout <branch> && git pull --ff-only`, then `git merge --no-ff origin/<base_branch> -m "<ticket + > UPD merge <base_branch> into <branch>"` (commit message style of the project, ticket first if there is one; fast-forward when possible).
   - Submodule pointers: if both sides moved a pointer, keep the base branch's pointer when the stage one is its ancestor (`git merge-base --is-ancestor`); otherwise see the submodule rule above. Any other conflict: `git merge --abort`, report and stop. Never resolve code conflicts on your own.
   - Run the project's checks if the project asks for them (pre-commit on the merge is not needed), show `git diff --stat origin/<branch>..<branch>`, then push `origin <branch>` (the approval above covers the merge and this push, for these repositories only; say where it went).
   - Then continue with the checks below on the updated branch. Go back to the branch the checkout was on before if the user did not ask to stay.
1. `git fetch`. Masters: check that the checkout is on `$ENV.branch`, the working tree is clean, and `git status -sb` shows no ahead/behind. Submodules: same, on `$ENV.submodule_branch` (skip the branch check when it is `null`). If behind its remote branch, fast-forward (`git pull --ff-only`) after asking; this is the "latest changes" step. Never switch branches with uncommitted changes: stop and report.
2. For each master repository: the submodule pointers are committed (`git status` shows no `modified: <submodule> (new commits)`) and the commit is pushed (`git rev-list origin/<branch>..<branch>` is empty). Check that each pointer's commit exists on the submodule's remote (`git -C <sub> branch -r --contains <sha>` is not empty).
3. Print a table repo / branch / clean / pushed. Any failure stops the release: say which repo and what to do. The local checkout may be on another branch (a feature branch, or `18.0` while releasing stage): do not switch away from uncommitted work, and ask before switching a clean checkout to `$ENV.branch`.

## 2. Fetch the server (do not pull)

Check that every `$ENV.repo_paths` entry exists and is the right repository (`ssh <ssh> 'cd <path> && git remote get-url origin'`, compare with the local `origin`). If a path is wrong, list the folder, ask the user and fix the configuration. Then, for each repository:

```bash
ssh <ssh> "cd <path> && git fetch --recurse-submodules=on-demand && git status -sb | head -3 && git rev-parse HEAD @{u} && git submodule status --recursive"
```
`git fetch` only downloads objects (including the new commits of the submodules whose pointer moved); it changes neither the working tree nor the checked-out commits. Do not run `git pull`, `git submodule update` or `git checkout` in this phase. Warn if the server has local modifications (`git status --porcelain` not empty), is not on `$ENV.branch`, or if `@{u}` differs from the local `$ENV.branch` commit (not pushed, or someone pushed elsewhere). Warn if a submodule on the server is not at the pointer recorded by the current HEAD (`git submodule status` with a `+` prefix): that drift will be overwritten by the update.

### Preflight: can the services be controlled without a password?

Check it here, read-only, so a missing permission is known before the release and not at the stop step (a manual `sudo` stop and start adds minutes of downtime):

```bash
ssh <ssh> 'for u in <services>; do
  if [ "$(systemctl is-active $u)" = active ]; then
    pid=$(systemctl show $u -p MainPID --value)
    systemctl --no-ask-password start $u >/dev/null 2>&1 && echo "$u: allowed (pid $pid untouched: $([ "$pid" = "$(systemctl show $u -p MainPID --value)" ] && echo yes || echo NO))" || echo "$u: NOT allowed"
  else echo "$u: not active, not tested (a start would change its state)"; fi
done
systemctl --no-ask-password start cron.service >/dev/null 2>&1 && echo "control cron.service: allowed (rule TOO BROAD)" || echo "control cron.service: refused (good)"
sudo -n true 2>/dev/null && echo "sudo without password: yes" || echo "sudo without password: no"'
```
This uses the real authorization path. `systemctl start` on a unit that is already running is a no-op (same pid), and polkit decides before systemd looks at the state, so it proves the rule matches the user and the unit; the rule grants `start`, `stop` and `restart` together, so stop is covered too. Do **not** use `pkcheck --detail`: polkit refuses it for non-root users ("Only trusted callers can pass details") and it always looks like "not allowed". Test only units that are active, and never loop over other units than the configured ones, except the `cron.service` control, which must be refused.
- All `allowed`, control refused: stop and start run by the skill, with no manual step.
- `NOT allowed` (and no passwordless sudo): tell the user now, show the polkit rule below, and say that the stop and start will have to be run by them in their own terminal, which adds to the downtime. Offer to continue anyway. Never try to work around it (no password in a command, no `sudo -S`, no edit of sudoers or polkit by yourself without the user's explicit request and a working root access).

The rule that grants exactly this (install as root, once, per server; polkit reloads it by itself; adapt the user and the units):
```js
polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.systemd1.manage-units" &&
        subject.user == "<ssh user>" &&
        ["<service 1>", "<service 2>"].indexOf(action.lookup("unit")) >= 0 &&
        ["start", "stop", "restart"].indexOf(action.lookup("verb")) >= 0) {
        return polkit.Result.YES;
    }
});
```
in `/etc/polkit-1/rules.d/50-odoo-release.rules` (mode 644). It gives no shell and no other unit; it is revoked by deleting the file.

## 3. What will the pull bring

The diff is computed **on the server**, between what is currently checked out there (`HEAD` and each submodule's current commit) and what `git pull && git submodule update` would give (`@{u}` and the submodule commits its tree points to). Run the script over SSH from stdin; it is read-only and nothing is copied to the server:

```bash
ssh <ssh> "$(printf '%q ' <python> - --ticket-regex '<ticket_regex>' <server path of each repo>)" < $SKILL/scripts/release_diff.py > $WORK/diff.json
```
`printf '%q'` protects the regular expression from the remote shell (ssh re-parses the command line; without it `\bT\d{3,6}\b` arrives mangled). Check that the JSON starts with `[`.

Per repository, recursively through moved submodules, it gives the commits, the tickets found in the commit messages, and the Odoo modules (nearest folder with `__manifest__.py`, as at the new commit) with their changed files. Tests and docs are ignored. It also lists new and removed modules. **The skill never installs modules** (no `-i`): new modules are only listed in the technical notes as "not installed by this release, install manually if wanted", and left out of `-u` (updating a module that is not installed does nothing). Check `__manifest__.py` dependency changes by reading the diff. If a git command fails with "dubious ownership", the script already passes `safe.directory` per command; never write to the server's git configuration. If it reports a missing submodule commit, run `git -C <submodule> fetch` on the server (still read-only) and rerun.

To read a diff yourself: `ssh <ssh> "git -C <path> diff HEAD @{u} -- <file>"` (inside a submodule: `git -C <sub> diff HEAD <sha>`; add `-c safe.directory=<sub>` if git refuses).

Odoo updates dependents of an updated module itself; list only the modules that changed. **The `-u` list only holds modules where something affects the database** (`update: true` in the JSON): data/view files (xml, csv), migration scripts, translations, model definitions (field or schema lines in Python), and manifest changes other than version, `post_load`, author/summary-type keys and assets. Modules with only runtime code changes (controllers, methods, js/scss, a `post_load` hook, a version bump) have `update: false`: leave them out of `-u`, since the restart in phase 7 picks them up, and list them separately in the technical notes as "code only, restart suffices". The check is a heuristic on the diff: read the diffs of the code-only modules and move one into the list if you see something that touches the database (an `@api.depends` of a stored compute, a changed default or a `_sql_constraints` the script missed).

Read the actual diffs of the user-visible commits to understand them. Do not trust commit subjects alone.

**Deployment mode.** Once the `-u` list is known:
- **Update mode**: the list is not empty. Phase 7 pulls, stops the services, updates the modules, starts the services. Estimated downtime: `deferral.minutes_per_module` (default 1) minutes per module in the list, at least 1 minute (say "about N minutes"; the real figure is reported afterwards).
- **Restart mode**: the list is empty (only code-only changes, or nothing). Phase 7 pulls and **restarts** the services (`systemctl restart`, which the polkit rule of the preflight also allows), with no stop, no update, no start chain. The deployment is **always immediate** (no time question, no deferral), and the user release notes **do not mention any downtime or planned time**. Say it to the user in the summary: "no module to update, simple restart".

## 4. User release notes (only when `$ENV.upload_release_notes`)

Skip this phase when `upload_release_notes` is false (say so, and offer to write them anyway if the user wants).

Write `$WORK/release-notes-<YYYY-MM-DD>.html`, self-contained (inline CSS, no external fonts or scripts), responsive, light and dark theme, neutral design. Language `release_notes.language`, in **simple words for `release_notes.audience`** (not developers). Structure:

- Title "Odoo release <date>" and one-paragraph summary.
- Sections grouped by the areas those users know, each change as one short sentence on **what changes for them** and where in Odoo to see it. Fixes: "Fixed: ..." in plain words.
- No ticket numbers, commit hashes, module or technical names. Leave out purely technical changes (refactors, tests, CI, log or security internals), and say so to the operator in the chat when you drop something.
- Date, and "Questions: contact `release_notes.contact`".
- A placeholder comment `<!-- maintenance-notice -->` right under the summary. **Update mode only** (see phase 3), phase 6 replaces it with the notice about the planned downtime. In restart mode, leave no notice and no mention of a downtime or a time.

Check the folder naming on the web server before choosing the file name: `ssh <release_notes.ssh> 'ls -lat <remote_dir> | head'` (read-only) and follow the pattern; there may be an index page to update, ask before editing it. Note the folder's owner: an upload may need rights the user does not have.

## 5. Technical notes (local only)

Write `$WORK/technical-notes-<YYYY-MM-DD>.html`, self-contained, for the IT approver:

- Header: **the environment and host in a prominent badge**, date, who prepared it, `HEAD -> new` SHAs per repository, branch, **the deployment mode** (update, or simple restart), and for production the people connected at that moment, the chosen time and the estimated downtime (completed in phase 6).
- Link to the user release notes when they exist (relative link to the local file, and the web URL once uploaded).
- Table of resolved tickets: reference, commit subject, repository, commit hash (every ticket found in the commits; commits without a ticket listed separately).
- **Modules to update**: the exact `-u` list (modules already installed only; never `-i`) (database-affecting modules only, comma separated, copy-ready), with per-module the reasons and files that triggered it, then a second table of the code-only modules left out of `-u`, flags for migrations, new modules (listed as not installed by this release), deleted/renamed modules, manifest dependency changes (a new dependency of an updated module that is not installed yet is installed by Odoo itself during `-u`: name it as a risk), and new Python requirements (`requirements.txt` changes to install in the virtualenv **before** the update).
- Risks and checks: migrations (what data they touch), changes to `ir.cron`, security files (`ir.model.access.csv`, rules), data files with `noupdate`, a recommendation to back up the database.
- The commands that approval will run, verbatim.

Open the file with `open_command` and show a short summary in chat.

## 6. Approval (blocking)

Summarise: **environment and host**, **deployment mode** (phase 3), repos and commit counts, number of tickets, module list, services affected.

**6a. Who is connected (only when `$ENV.presence`, production).** Ask for the database name now (offer the previous one first), then, read-only:
```bash
ssh <ssh> "$(printf '%q ' <python> - <odoo_dir>/<odoo_bin> <odoo_dir>/<update_conf> <DB>)" < $SKILL/scripts/presence.py
```
It counts the employees checked in right now (an attendance without check-out, started in the last 16 hours) out of the active employees, using Odoo's own configuration loader: credentials are never read or shown, no module is loaded (so no pending upgrade can start), nothing is written. Show "N of M employees are checked in right now". If `available` is false (`hr_attendance` not installed) or the script fails, say so and continue without the figure. Never list names.

**6b. When to deploy (only in update mode, only when `$ENV.deferral.enabled`).** Ask with AskUserQuestion: **now**, one option per configured slot (label and time, the next occurrence in `deferral.timezone`: a slot already past today is offered for tomorrow), or **custom time**. Show the estimated downtime and the connected people next to the question. In restart mode, and for an environment without `deferral`, the release is always immediate: do not ask.

**6c. The release notes (only when `$ENV.upload_release_notes`).**
- **Update mode:** replace `<!-- maintenance-notice -->` in the notes with a clear notice, in `release_notes.language`, in the notes' style: the cutoff and the estimate, e.g. "Planned update: Odoo will be unavailable on <date> from <HH:MM> for about <N> minutes. Please save your work before." (an immediate deployment: "Odoo will be unavailable for about <N> minutes, starting now."). Time and date in `deferral.timezone`.
- **Restart mode:** the notes carry no notice and no downtime information.
- The notes are **published now, even when the deployment is deferred**, so the users know in advance. The upload is its own approval:
```bash
scp $WORK/release-notes-<date>.html <release_notes.ssh>:<remote_dir>/
```
(adapt to the permissions found on the server; do not use sudo without asking).

**6d. Approval.** Ask with AskUserQuestion, naming the environment, the mode and the time: approve the deployment to `<environment>` (now, or at `<time>`), or stop. Without a clear approval, stop here and leave the files in `$WORK`.

**6e. If the deployment is deferred.** Write `$WORK/deployment.json` (environment, time, mode, the `-u` list, the SHAs from phase 2, the database name, the release notes URL), add the time and estimate to the technical notes, and tell the user. Then, if the user wants the session to stay open, schedule a one-shot prompt for that time with the session's scheduling tool (`CronCreate`, load it with `ToolSearch`) that runs this skill in resume mode; otherwise the user starts the skill again at that time ("resume the deployment"). **Resume mode**: re-run phases 1 and 2 and the preflight, and verify that the server `HEAD` and `@{u}` still equal the SHAs of `deployment.json` and the `-u` list is unchanged. If anything differs (someone pushed), stop: the plan and the published notes are stale, recompute from phase 3. Otherwise show the people connected again, then run phase 7 without asking the approval again (the approval of 6d was for this time) unless the user cancels. Never run a deferred deployment before its time.

## 7. Deploy (after approval)

The **database name** is the one given in phase 6 (production with `presence`), otherwise ask for it now, offering the previous one first (section 0). Run each step separately, stop at the first error, and print a progress line before each (`[1/6] Pulling ...`), with the environment in the first line. `<sudo>` is `sudo ` when `use_sudo`.

If `sudo` asks for a password (check with `ssh <ssh> sudo -n true`), you cannot answer it: first try `systemctl --no-ask-password <action>` (polkit may allow it; a denial changes nothing). If it is denied, ask the user to run the command **in their own terminal** (`ssh -t <ssh> 'sudo systemctl ...'`): the `!` prefix of this session has no terminal, so `sudo` cannot prompt there. Continue when they confirm, and verify the result yourself with `systemctl is-active` and the server's `date -u`. Never put a password in a command.

**Restart mode** (phase 3): do step 1, then replace steps 2 to 5 by a single restart: note the time, `<sudo>systemctl restart <services>` (one command, the services in the stop order), check `is-active` and the startup log as in step 5, and stop the downtime clock when the main service accepts requests. Then step 6. No update, no Monitor.

1. **Pull**: for each repository `cd <path> && git pull --ff-only && git submodule update --init --recursive`. Check that `git rev-parse HEAD` now equals the SHA from phase 2 and `git submodule status --recursive` shows no `+`/`-`. Install new requirements if the notes flagged them (with `<python> -m pip`, ask first).
2. **Stop services**: `<sudo>systemctl stop <services in order>`, then verify with `systemctl is-active` (all must be `inactive`). **Start the downtime clock here**: note the time of the stop (read it on the server with `ssh <ssh> date -u +%FT%TZ`, so local clock differences do not matter).
3. **Update modules** (note its start and end time too). Launch it detached, so the SSH call returns at once, with a pid file and an exit file that the watcher reads:
   ```bash
   ssh <ssh> 'cd <odoo_dir> && L=<update_log_dir>/odoo-update-<date>.log && rm -f $L.exit && setsid sh -c "<python> <odoo_bin> -c <update_conf> -d <DB> -u <modules> --no-http --stop-after-init > $L 2>&1 & echo \$! > $L.pid; wait \$!; echo exit=\$? > $L.exit; date -u +%FT%TZ >> $L.exit" > /dev/null 2>&1 < /dev/null & echo started'
   ```
   **Immediately after launching, without waiting to be asked, start the live stream** with the Monitor tool (`timeout_ms` 1800000, re-arm when it expires and the update is still running), using `scripts/watch_update.sh`:
   ```bash
   ssh <ssh> sh -s -- <update_log_dir>/odoo-update-<date>.log <modules> 30 < $SKILL/scripts/watch_update.sh
   ```
   It prints a heartbeat every 30 seconds (current module, modules reached out of the total, warning and error counts, how long the log has been quiet), prints migration scripts and every `ERROR` / `CRITICAL` / `Traceback` line at once, and ends with a `DONE: exit=<code>` line. When the log has been quiet for 60 seconds or more, the heartbeat also says what the process is doing (computing, waiting on disk or network files, or waiting for the database), which tells a slow migration from a hang.

   **Reporting rules.** Tell the user, when starting, that a progress line will arrive every 30 seconds in this conversation. Then relay each event in **one short line** (time, module, n/total, and anything new: a migration, an error, a long silence with its diagnosis). Never wait for the user to ask for progress, and do not repeat unchanged information at length. A long quiet period is not a failure: say what the diagnosis line says, do not kill anything, and only suggest options (wait, abort) when the quiet lasts over 10 minutes or an error appears. Stop the Monitor when `DONE` arrives.
4. **Evaluate**: the update succeeded only if the process exited 0 **and** the log has no `ERROR`, `CRITICAL` or `Traceback`, and shows `Modules loaded.` Otherwise **do not restart**: show the errors with their context, the log path, and propose options (fix and rerun, roll back the code with `git reset` plus a database restore, which is a decision for the user). The services stay stopped until the user decides.
5. **Restart**: `<sudo>systemctl start <services in reverse order>`, check `is-active` for all and `journalctl -u <main service> -n 30 --no-pager` for startup errors. **Stop the downtime clock** when the main service is `active` and its log shows it accepts requests (and note that time). If the update failed and the services stay stopped, report the downtime as ongoing since the stop time.
6. **Report**: what was done, **the downtime of the Odoo server, always** (services stopped at `<time>`, back at `<time>`, total `<mm:ss>`, with the part spent on the module update separately; in update mode also the estimate from phase 3 next to the real figure; in restart mode the downtime of the restart), the environment, warnings seen, link to the technical notes. Append the same figures to the technical notes file (a short "Deployment result" section) so the release has a record. Remind the user to check the site and, if the notes were uploaded, share their URL.

After an aborted or failed update, **never start any Odoo process on that database** (not even `odoo-bin shell` for a "read-only" check) until module states are checked (`select name, state from ir_module_module where state not in ('installed','uninstalled','uninstallable')`, run by the user if you have no database access): Odoo applies modules still marked `to upgrade` when it loads the database, so the process silently resumes the upgrade, concurrently with any other update. Also tell the user before they start a manual update that no other Odoo process may use the database at the same time.

If the SSH session drops mid-update, do not start a second update: check the process (`pgrep -af odoo-bin`) and the log first.
