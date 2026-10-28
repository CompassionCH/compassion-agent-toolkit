---
name: ticket-list
description: List your open Compassion Odoo tickets (project.task) across all projects, grouped by stage, with a direct URL for each so you can pick one to work on. Use when the user invokes /ticket-list (optionally "/ticket-list all"), or says "what are my tickets", "show my open tasks", "my backlog".
---

# /ticket-list — list my tickets

Show the tickets assigned to **you** (`project.task` where `user_id` = the configured
`me`), across all projects, grouped by stage with a clickable URL for each — so you can see
your work-in-progress and open one. By default it hides completed tickets; `all` includes
them.

```
/ticket-list        → your OPEN tickets (hides Done/Cancelled/In Production/Complete/Rejected/Merge/User Acceptance)
/ticket-list all    → ALL your tickets, including completed
```

This is **read-only** — it never writes. Default env is **prod** (where your real tickets
live); pass `--env local` for the local DB.

## Run

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py" list           # open tickets
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py" list --all     # include completed
```

- "Mine" = the user set during `setup` (the human, not the shared bot account). Missing
  or not found → the command says so; the user reruns `setup` in their own terminal.
  `--assignee` takes a login, a name or an Odoo user id. To list someone else's, add
  `--assignee <login-or-name>`.
- Map the skill argument: bare `/ticket-list` → `list`; `/ticket-list all` → `list --all`.
- Another environment: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py" --env local list`.

> If the command stops on a missing config or name detection, or to read masked
> output (`{{NAME_1}}` tokens) correctly, follow `${CLAUDE_PLUGIN_ROOT}/skills/ticket/references/first-run.md`.

## Present

The command already prints grouped markdown (stage headers, actionable-first: In Progress →
Blocked → In Review → Ready → Backlog → New Request → other). Within each stage, rows are
sorted **most-important-first**: by `priority` (desc) then oldest-first. Each row shows the
**`T####` code**, short title, project, and a direct form URL, plus **priority + age**:

- **Priority** — the `project.task.priority` selection, rendered as stars:
  `⭐⭐⭐` Very High (`3`), `⭐⭐` High (`2`), `⭐` Important (`1`), _(no star)_ Normal (`0`).
  A footer line lists the starred tickets highest-first.
- **Age** — days since `create_date` (e.g. `142d`), so a long-stale ticket is visible.

**Relay that list to the user as-is** (it's the deliverable). Briefly note the totals
(e.g. "9 open across 4 stages").

## Recommend

After relaying the list, add a short **"What to work on next"** paragraph (2–4 sentences).
This is the analysis the tool can't do — weigh the three signals together:

1. **Priority stars** — the requester's/PM's explicit urgency; the dominant signal.
2. **Stage actionability** — a `Blocked` ticket can't be started even if high-priority
   (say so, and note it's waiting on something); prefer tickets in actionable stages
   (In Progress → Ready → Backlog).
3. **Age** — among equal priority, an older ticket has been waiting longer; break ties by age.

Recommend **one** ticket (occasionally a close second) with a one-line reason, e.g.
_"T3029 (⭐ Important, 136d) — highest actionable ticket; T3022 outranks it but is Blocked."_
Keep it a recommendation — the user chooses. They open a URL or say "work on T####" (which
is `/ticket`). Don't auto-continue into another flow.

## Notes

- "Completed" is a fixed stage-name set: **Done, Cancelled, In Production, Complete,
  Rejected, Merge, User Acceptance** (English dev-project stages — your tickets live there).
  If a French/German "done" stage ever leaks into the open list, add it to
  `LIST_CLOSED_STAGES` in the plugin's `scripts/odoo_ticket.py`.
- Requires no special permissions beyond the bot account's normal read access (it reads
  your `project.task` records, not private contacts).
- Caps at 500 tasks (more than enough for one person).
