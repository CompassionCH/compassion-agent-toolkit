# First run: config and name detection

Every ticket skill calls `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py"`. On a new
machine it stops with one of two messages. Handle them like this, then rerun the command
that failed.

## "No config at …" / "No [<env>] section …"

The user hasn't configured that environment yet. The config holds an API key, so:

- **They run `setup` in their own terminal**, not in this session and not with `!`. Show
  them the exact command the error printed (it already contains the right path, plus
  `--env <env>` when needed).
- `setup` asks for the Odoo URL, the database, the login of the account Claude reads
  with, its API key (typed hidden) and their own Odoo login (for `/ticket-list` and
  `/ticket-stats`). It writes `~/.config/compassion-odoo/config.ini` (mode 600), tests
  the connection and stores their Odoo user id; if the shared account can't see their
  user, they pick themselves from the list of task assignees.
- The values come from the team; the bot account's API key is in the team key vault
  (search for `claudecode`). Don't guess them.
- **Never ask for the API key in the chat, and never read the config file.** If the user
  pastes a key anyway, tell them it has now been sent to Anthropic and should be rotated.

## "Name detection is not installed …"

Without it, only the regex layer runs and names of people not linked to the ticket can
leak. Offer the one-time install (about 1 GB, Presidio + spaCy models for EN/DE/FR/IT,
into `~/.local/share/compassion-odoo/venv`). With the user's yes, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odoo_ticket.py" install-ner
```

It needs Python's `venv` module (on Debian/Ubuntu: `python3-venv`). If pip can't find
wheels for a very new Python, the user reruns it with an older `python3.x` themselves. `--regex-only`
only runs in the user's own terminal: if they accept weaker masking, they run it there.

## Masked output

Read commands print last names, emails, phones and addresses as tokens like `{{NAME_1}}` /
`{{EMAIL_1}}` (first names stay). Tokens are numbered per run: within one output the same
token is the same person, but `{{NAME_1}}` in two different outputs are unrelated, so
never link people across outputs by token. `--raw` only runs in the user's own terminal:
if they need unmasked data, they run it there and paste what's needed.
