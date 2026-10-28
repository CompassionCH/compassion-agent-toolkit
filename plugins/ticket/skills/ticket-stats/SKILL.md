---
name: ticket-stats
description: Fun aggregate stats over Compassion Odoo tickets (project.task) — status split, completion times, per-year throughput, superlatives, and (in all-mode) per-person leaderboards. Defaults to your own tickets; "all" aggregates everyone. Use when the user invokes /ticket-stats (optionally "/ticket-stats all"), or asks "ticket stats", "my stats", "team velocity / leaderboard".
---

# /ticket-stats — fun ticket stats

Crunch `project.task` history into a stat card: status split, completion-time median,
per-year created-vs-done, velocity, aging, superlatives — and in all-mode, per-person
leaderboards.

```
/ticket-stats        → your stats (assignee = `me`)
/ticket-stats all    → everyone, + leaderboards
```

**Read-only.** Default env **prod** (real history); `--env local` for the local DB. Stats
cover **full history including archived** tasks.

## Run

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py" stats           # you
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py" stats --all     # everyone + leaderboards
# someone else: --assignee <login-or-name>
```

> If the command stops on a missing config or name detection, or to read masked
> output (`{{NAME_1}}` tokens) correctly, follow `${CLAUDE_PLUGIN_ROOT}/skills/ticket/references/first-run.md`.

- Map the argument: bare `/ticket-stats` → `stats`; `/ticket-stats all` → `stats --all`.
- "You" = the user set during `setup`; `--assignee` takes a login, a name or a user id.

## Present

The command prints a ready-made emoji stat card (status split, ⏱️ completion time, 📅 per-year
bars, 🗓️ per-month bars for the current year, ⚡ velocity, 🏆 superlatives, 🗂️ top projects,
and 👥 leaderboards in all-mode).
**Relay it to the user as-is.** Optionally add one fun one-liner highlighting the standout
number (e.g. fastest closer, oldest open) — but don't pad it.

## What the numbers mean

- **Total** = every task incl. archived. **✅ done** = stages *Done / Complete / In Production
  / Merge / Ready to Release*; **❌ cancelled** = *Cancelled / Rejected*. Both count as
  **closed**. **🔒 closed %** = (total − currently-open) ÷ total — only actively-open tasks
  count as "not completed".
- **🟢 open** counts only **active** tasks (real backlog); 🔵 in-progress / 🔴 blocked are
  subsets. Archived-but-unclosed old tasks show separately as 🗄️ (migration junk) and count
  as closed.
- **⚡ fastest / 🐌 slowest** and **⏳ oldest open** ignore cancelled — fastest/slowest use only
  *done* tasks (`date_end − create_date`); oldest-open uses only active-open. Plus Odoo's
  working-days figure and **time-to-start** = `create_date → date_assign`.
- **Velocity** = done/month over the last 12 months; **best month** = peak calendar month.
- **Leaderboards** (all-mode): most open, most done (lifetime + this year), 🤷 unassigned, and
  **⚡ Fastest closers** = people with **≥5 closed** tasks ranked by their **median**
  create→done time (lowest = fastest).

## Notes

- The done/cancelled stage sets live in `STATS_DONE_STAGES` / `STATS_CANCELLED_STAGES` in
  `odoo_ticket.py` — extend if needed (e.g. localized stage names).
- Pulls up to 10000 tasks in one call (current org ≈ 3.3k) and computes in Python.
- "starred" counts tasks with a non-zero `priority` — at Compassion many tasks are starred,
  so read it as "flagged", not "rare/urgent".
