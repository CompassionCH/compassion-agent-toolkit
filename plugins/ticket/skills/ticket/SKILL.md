---
name: ticket
description: Work an Odoo ticket (T####) end to end on the local instance — understand, reproduce, propose a fix (stop), fix and verify, clean up, stage (stop; the user commits). Use when the user says "fix ticket T####", "work on T####", "look at T####", or invokes /ticket ####.
---

# /ticket T####

Ticket CLI (read-only, personal data masked):
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py" fetch <number>` (default env prod,
the source of truth). If it stops on a missing config or name detection, or to read the
`{{NAME_1}}` tokens right, follow [references/first-run.md](references/first-run.md).

Local facts (Odoo version, local URL, app and test databases, test command, browser login)
come from the repo's `CLAUDE.md`. Missing → ask, and suggest adding them there.

**Two hard stops:** after step 3 (wait for approval) and after step 6. Never `git commit`
or `git push`: the user does. Never write to Odoo.

1. **Understand.** Fetch the ticket and read the thread and attachments, not just the
   description. Locate the code: most models are `_inherit` overrides, so read the
   override and its base model (often in another repo). Use parallel Explore agents when
   the module is unclear. Name the repo that owns the fix. Pin root cause to file/line.
2. **Reproduce** on the local instance, as in
   [references/local-instance.md](references/local-instance.md): JS bugs in the browser
   with agent-browser, Python bugs with a test on the **test** database. Note the id of
   every record you create or change. Can't reproduce → say so and reason from code.
3. **Propose** root cause, repo + files, diff-level change, how you'll verify. **Stop.**
4. **Fix and verify.** `git fetch` and fast-forward the base branch first (can't → stop
   and ask), then `git checkout -b T<number>-<slug> --no-track origin/<base>`. Edit, rerun
   the step-2 repro until the symptom is gone, then `pre-commit run --all-files` if the
   repo has it. Never call a red run green.
5. **Clean up.** Delete or revert every test record from step 2; list the ids.
6. **Stage** only the files you changed (never the bot-regenerated `README.rst`,
   `static/description/index.html`, `requirements.txt`). Propose
   `[T<number>] FIX|FEAT|REFACTOR|ADD|STYLE|UPD|REF: <summary>`, 1–2 lines. **Stop.**
   Offer a ready-to-paste ticket comment if useful.

Gotchas: ticket ids differ per environment, and a code that isn't found is usually the
wrong code. Ask before starting, stopping or restarting the user's instance (it may run
under a debugger); a hanging page often means a debugger breakpoint. Never `--dev=all`
(silent pdb freeze).
