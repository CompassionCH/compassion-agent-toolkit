# Progress table (which templates are done)

The developer guide (a Claude Docs document) ends with a table of **every `mail.template` used by an active `partner.communication.config`**, with its status. The skill reads it to know what is left and updates it when a template is finished.

- Document: https://claude.ai/code/artifact/b488034b-69d5-4186-964f-5026cbe2877e
- Doc id `b488034b-69d5-4186-964f-5026cbe2877e`, body of the tab (prose node) `cfdaa3c7-2d28`.
- Section: heading "Progress: communication templates to fix", then one table, columns `Communication config | Template ID | Uses | Status | Ticket`. One row per config, **sorted by `Uses`, highest first** (248 rows on 19 October 2026: 243 distinct templates, a template used by several configs has one row per config).
- `Uses` = number of `partner.communication.job` of that config, cancelled ones excluded, created in the 12 months before the latest job of the backup (15 October 2025 to 15 October 2026). Work from the top of the table: the most used communications first.
- `Status` is `Todo` or `Done`; `Ticket` is the ticket that did it (`T3527`).
- IDs (config name, template id) are the same in every developer's database because everybody works from production backups. A config created after that backup has no row: add one at the end of the table.

## Tools

Use the Claude Docs tools (`read`, `update`, `guide`). They are deferred: load them with `ToolSearch` (`select:mcp__claude_ai_Claude_Docs__read,mcp__claude_ai_Claude_Docs__update,mcp__claude_ai_Claude_Docs__guide`), then call `guide(items=["topic.index"])` and `guide(items=["topic.editing"])` once. If the tools or the document are not available to you (the document is private until its owner shares it), say so and give the user the rows to change by hand. Never block the work on it.

## Read

- A template or config: `read(ref={"object":"node","id":"cfdaa3c7-2d28"}, engine="prose", container={"kind":"project","id":"b488034b-69d5-4186-964f-5026cbe2877e"}, payload={"kind":"search","text":"<config name or template id>"})`. The hit shows the table id and the row id.
- A row: `payload={"kind":"view","parentId":"<row id>"}`.
- The whole table (about 12 KB): `payload={"kind":"view","parentId":"<table id>"}`. Use it to list the `Todo` rows (already in usage order) and propose the first ones to the user.
- Remember the `rev` of your last read: the guards below use it.

## Update (tested)

When a template is cleaned, written to the database and synced to the code (SKILL.md section 4 done), for **every row with that Template ID**:
1. Row number `N` = position in the table, header row = 0 (read the row with `view` to be sure; the order is by usage, so never reuse a row number from an earlier session). Table id `T` from the search hit. Columns: config 0, template id 1, uses 2, status 3, ticket 4.
2. One `update(ref=node, engine="prose", container=..., payload={"ops":[...]})` with:
   ```
   {"op":"replace","target":{"kind":"find","text":"Todo","within":{"kind":"cell","table":"<T>","row":N,"col":3}},
    "with":{"from":{"kind":"inline","content":"Done"},"as":"text"}},
   {"op":"replace","target":{"kind":"cell","table":"<T>","row":N,"col":4},"ifRev":<rev of your read>,
    "with":{"from":{"kind":"inline","content":"<TICKET>"},"as":"text"}}
   ```
   (the ticket cell is empty, so it is replaced as a whole cell, which needs `ifRev`).
3. Update the count in the sentence above the table (`"6 of 248"`, `"6 of 243"`) with a `find` + `replace` `"as":"text"`.
4. If a guard refuses (`guard_mismatch`, `find_none`), someone edited the table: read it again and redo only that row. Never force.

Only mark `Done` what the user accepted and what is in the database and the code. To undo a mistake, put `Todo` back and delete the ticket text (`delete` with a `find` target inside the cell).

## Refresh the list and the usage

New active configs, or a new backup:
```sql
select s.name, t.id,
       count(j.id) filter (where j.state <> 'cancel') as uses
from partner_communication_config c
join utm_source s on s.id = c.source_id
join mail_template t on t.id = c.email_template_id
left join partner_communication_job j on j.config_id = c.id
     and j.create_date >= (select max(create_date) from partner_communication_job) - interval '1 year'
where c.active group by c.id, s.name, t.id
order by uses desc, lower(s.name), t.id;
```
To refresh the whole table: read the current `Status` and `Ticket` of every row first, rebuild the markdown table in the order of the query (keep the statuses), then `replace` the table block (`"as":"markdown"`, guarded with its `ifHash` and `ifRev` from a fresh read) and update the date and the counts in the sentence above it. For a single missing config, `insert` one row at the end (`"as":"blocks"`, `side` `"end"` on the table id, see `guide topic.editing`).
