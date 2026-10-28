# Local instance: reproduce & verify

How to run Step 2 (reproduce) and Step 4 (verify) of `/ticket`. The concrete values (URLs,
database names, addons path, ports, login) come from the repository's `CLAUDE.md`.

## The two runtimes — don't mix them

| Use | Runtime | Database | Port |
|---|---|---|---|
| **Browser repro/verify** (JS, UI, data) | the user's running instance | their app database | theirs (often 8069) |
| **Python tests** | a CLI run **you** start | a dedicated **test** database | a free one, e.g. 8169 |

Never run Python tests against the app database. Ask before starting, stopping or
restarting the user's instance: it may run in their IDE or under a debugger. A standing
answer in the repo's `CLAUDE.md` (and how to start it) saves asking each time.

## Front-end (browser) reproduction with agent-browser

Check the instance is up first: `curl -s -o /dev/null -w '%{http_code}' <local-url>/web/login`
→ `200`. If it's down, ask whether you start it or they do.

### Login

Odoo's login form needs a real password; an XML-RPC API key won't do. Preferred (keeps the
secret out of the chat and shell history): the user saves it once into agent-browser's
auth vault, you reuse it:

```bash
# the user runs once, in their own terminal (password on stdin, then Ctrl+D):
agent-browser auth save odoo-local --url <local-url>/web/login \
  --username <login> --password-stdin
# you, each session:
agent-browser auth login odoo-local
agent-browser wait --url "**/web**"
```

If the account lacks a right (AccessError), stop and ask the user to grant the specific
group; don't work around it.

### Capture JS errors

Clear the console before the action, trigger the bug, then read it:

```bash
agent-browser console --clear
# ...perform the click-path...
agent-browser console            # look for the Uncaught TypeError / traceback
```

### Driving Odoo views (tips)

- Snapshot interactive-only: `agent-browser snapshot -i -c`. Refs go stale after every
  navigation/dialog: re-snapshot.
- After clicking an action button, `agent-browser wait --load networkidle` before the next
  snapshot.
- A backend record by id: `agent-browser open "<local-url>/web#id=<id>&model=<model>&view_type=form"`.
- Buttons are found by their label text: `agent-browser find text "Log interaction" click`.

### Verifying a JS fix without a restart

Static JS lives in an asset bundle; an edited file doesn't show until the bundle
regenerates. Open with **`?debug=assets`** so each file is served unbundled; the edited
file loads on a hard reload, no `-u`/restart needed:

```bash
agent-browser open "<local-url>/web?debug=assets"
agent-browser reload --hard
```

Then redo the exact repro click-path and confirm `agent-browser console` is clean **and**
the intended behavior happens.

## Back-end (Python) tests

Use the test command from the repository's `CLAUDE.md`. Its usual shape:

```bash
odoo-bin -c <config> -d <test-db> --addons-path=<core addons>,<every addons repo> \
  --http-port=<free port> -u <module> --test-enable --stop-after-init
```

- Pass an explicit `--addons-path` covering every repository the module depends on: test
  base classes import across repos.
- Single test: add `--test-tags /<module>:TestClass.test_method`.
- Module not yet in the test database: `-i <module>` instead of `-u`.
- Runs are slow: run them in the background and surface the traceback verbatim on failure.
- Never `--dev=all` (silent pdb freeze).
