---
name: ticket-explore
description: Discover unassigned, open Compassion Odoo tickets (project.task) to pick up and close — ranked by ⭐ priority then oldest-first, paginated, with a recommendation of the best next ticket(s). Use when the user invokes /ticket-explore (optionally "/ticket-explore <project>"), or asks "what should I work on", "find me a ticket", "show the unassigned backlog".
---

# /ticket-explore — find a ticket to pick up

Surface **unassigned, open** `project.task` tickets across all projects, ranked by **⭐ stars
(priority) then oldest-first**, and help the user choose one to work on. The aim is discovery
+ clearing the backlog, so lean toward high-impact, self-contained tickets.

```
/ticket-explore              → top unassigned candidates, ranked
/ticket-explore <project>    → filtered to a project (name match)
```

**Read-only.** Default env **prod**; `--env local` supported.

## Run

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py" explore --limit 15           # page 1
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py" explore --offset 15 --limit 15   # next page
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py" explore --project "MyCompassion" # filter by project
```

> If the command stops on a missing config or name detection, or to read masked
> output (`{{NAME_1}}` tokens) correctly, follow `${CLAUDE_PLUGIN_ROOT}/skills/ticket/references/first-run.md`.

- Map a bare project word after the command to `--project`: `/ticket-explore mycompassion`
  → `explore --project "mycompassion"`.
- Each candidate shows ⭐ stars · `T####` · title · project · age · stage · a description
  snippet · a 🔗 direct URL. The footer reports total pool size and the next-page command.

## Flow

1. **Run page 1** (`--limit 15` so the user always sees ≥10 options) and relay the ranked list.
   When you present it, render each ticket's code as a **clickable markdown link** to its 🔗
   URL — e.g. `**[T2949](<odoo-url>/web#id=3541&model=project.task&view_type=form)**`
   — so the user can jump straight in from the list.
2. **Recommend.** Look over the shown candidates (snippets, stars, age, project) and suggest
   **1–3 good next tickets** — favor: more stars, clear/self-contained scope (a likely quick
   win), and the areas the user works in (ask once if you don't know). One line of *why* per pick,
   each as a clickable link. If a top candidate's snippet is too thin to judge, `fetch` it
   (below) before recommending.
3. **Paginate on demand.** If the user isn't satisfied ("more", "next", "show others"), run the
   next page with `--offset` (advance by the page size) and relay it. Keep going as needed.
4. **On selection — show the full ticket (see below).** When the user picks one, present its
   full details. Then offer to start `/ticket T####` (diagnose → fix). Don't auto-start work.

## On selection — full details (translated)

When the user selects a ticket (or asks to see one), run:
```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py" fetch T####
```
This returns the **description, full message thread / log notes, customer (Partner), assignee,
stage, priority, dates, and attachments**. Present it clearly with:
- A 🔗 link at the top: `<odoo-url>/web#id=<db-id>&model=project.task&view_type=form`
  (the URL is on the `[env: …]` line, the db id in the `fetch` header as `#<id>`).
- **Translation:** Compassion tickets are often in French (or German). If any
  content — description, log notes, thread — is not English, **translate it to English** in
  your presentation, and note "(translated from French)". Keep `T####` codes, names, URLs, and
  code/stack-trace snippets verbatim.
- Summarize the actual ask + any error/stack trace in your own words, then offer next steps
  (start `/ticket`, or open the link).

## What's in the pool

- **Unassigned only** (`user_id` empty) and **open** (stage not in
  *Done/Complete/In Production/Merge/Ready to Release/Cancelled/Rejected*), across all projects.
  The pool is dev-heavy already (IT Department, Backlog Reduction, MyCompassion, Odoo
  migrations) — little CRM/recruitment noise.
- **Sort:** ⭐ `priority` descending (stars 0–3), then **oldest `create_date` first** (drain the
  aging backlog). So the rare ⭐⭐⭐/⭐⭐ tickets float to the very top.

## Notes

- Pure discovery — it never assigns or writes. To actually take a ticket, the user assigns
  it in Odoo, or just start with `/ticket`.
- Pagination is stateless: "more" = re-run with a larger `--offset`. The footer prints the exact
  next command.
