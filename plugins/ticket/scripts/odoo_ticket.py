#!/usr/bin/env python3
"""Read-only Odoo ticket CLI (project.task / helpdesk.ticket) over XML-RPC.

Prints a ticket as markdown (description + comment thread + attachments) so
Claude can read it. Tickets are referenced by their task code (T2917), not the
Odoo db id. Stdlib only; name detection runs in its own venv (install-ner).

    python3 odoo_ticket.py setup               # once, in your own terminal
    python3 odoo_ticket.py install-ner         # once: Presidio + spaCy models
    python3 odoo_ticket.py whoami
    python3 odoo_ticket.py fetch T3124
    python3 odoo_ticket.py search "payment slip" --limit 10
    python3 odoo_ticket.py list | stats | explore

Personal data: every read is sanitized (sanitizer.py): last names, emails,
phones, addresses become {{TOKENS}} numbered per run (not linkable across
runs); first names are kept. `--raw` disables this (the plugin's hook asks the
user first).

Config: ~/.config/compassion-odoo/config.ini, one section per environment
(prod, stage, local), written by `setup`. Never put it in a repository.
"""
import argparse
import configparser
import os
import re
import socket
import sys
import unicodedata
import xmlrpc.client
from collections import Counter, defaultdict
from datetime import datetime
from html.parser import HTMLParser

# First access to a DB loads its registry, which can take a while on a big
# instance. Allow generous time, but don't hang forever.
socket.setdefaulttimeout(180)

CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "compassion-odoo")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.ini")
NER_VENV = os.path.join(
    os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"),
    "compassion-odoo", "venv")
NER_PACKAGES = [
    "presidio-analyzer==2.2.364", "spacy==3.8.16",
    *(f"https://github.com/explosion/spacy-models/releases/download/{m}-3.8.0/"
      f"{m}-3.8.0-py3-none-any.whl"
      for m in ("en_core_web_md", "de_core_news_md", "fr_core_news_md", "it_core_news_md")),
]
def setup_hint(env):
    flag = "" if env == "prod" else f" --env {env}"
    return ("Run once, in your own terminal (not in Claude):\n"
            f"  python3 {os.path.abspath(__file__)}{flag} setup")

DEFAULT_BOT_LOGIN = "claudecode@compassion.ch"

KEYMAP = {"url": "ODOO_URL", "db": "ODOO_DB", "login": "ODOO_LOGIN", "api_key": "ODOO_API_KEY"}


def load_config(env):
    """Read the [env] section (prod/stage/local) from the user's config.ini."""
    if not os.path.exists(CONFIG_PATH):
        sys.exit(f"No config at {CONFIG_PATH}.\n{setup_hint(env)}")
    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH)
    if env not in parser:
        avail = ", ".join(parser.sections()) or "(none)"
        sys.exit(f"No [{env}] section in {CONFIG_PATH} (has: {avail}).\n"
                 f"{setup_hint(env)}")
    section = parser[env]
    cfg = {"ENV": env}
    for ini_key, cfg_key in KEYMAP.items():
        val = section.get(ini_key, "").strip()
        if not val:
            sys.exit(f"[{env}] in {CONFIG_PATH} is missing '{ini_key}'.\n"
                     f"{setup_hint(env)}")
        cfg[cfg_key] = val
    cfg["ODOO_URL"] = cfg["ODOO_URL"].rstrip("/")
    # The human behind the shared bot account, for `list` and `stats`.
    cfg["ODOO_ME"] = section.get("me", "").strip()
    cfg["ODOO_ME_ID"] = section.get("me_id", "").strip()
    return cfg


def _normalize_url(url):
    url = url.strip().rstrip("/")
    if url and "://" not in url:
        url = "https://" + url
    return url


def setup(env):
    """Interactive: write one [env] section of config.ini, then test it."""
    import getpass

    if not sys.stdin.isatty():
        sys.exit(f"`setup` asks for an API key: run it in your own terminal.\n{setup_hint(env)}")
    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH)
    old = dict(parser[env]) if env in parser else {}
    print(f"Configuring [{env}] in {CONFIG_PATH}. Enter keeps the value in brackets.")

    def ask(key, prompt, secret=False, default=""):
        cur = old.get(key, default)
        if secret:
            val = getpass.getpass(f"{prompt}{' [keep current]' if cur else ''}: ")
        else:
            val = input(f"{prompt}{f' [{cur}]' if cur else ''}: ")
        return val.strip() or cur

    vals = {
        "url": _normalize_url(ask("url", "Odoo URL, e.g. https://odoo.example.org")),
        "db": ask("db", "Database name"),
        "login": ask("login", "Login of the shared bot account Claude reads with, not your "
                     "own (Enter for the default)", default=DEFAULT_BOT_LOGIN),
        "api_key": ask("api_key", "API key of that bot account, from the team key vault "
                       "(search for claudecode) (hidden)", secret=True),
        "me": ask("me", "Your own Odoo login (only to find your tickets, never to log in)"),
    }
    missing = [k for k in ("url", "db", "login", "api_key") if not vals[k]]
    if missing:
        sys.exit(f"Missing {', '.join(missing)}: nothing written.")
    parser[env] = {k: v for k, v in vals.items() if v}
    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
    fd = os.open(CONFIG_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        parser.write(fh)
    os.chmod(CONFIG_PATH, 0o600)
    print(f"Written. Testing [{env}]...")
    try:
        odoo = Odoo(load_config(env))
    except (OSError, xmlrpc.client.Error) as e:
        sys.exit(f"Could not reach Odoo at {vals['url']}: {e}\n"
                 "Check the URL and database, then run setup again (Enter keeps "
                 "the other values).")
    u = odoo.execute("res.users", "read", [odoo.uid], {"fields": ["name", "login"]})[0]
    print(f"Connected as {u['name']} <{u['login']}>.")
    if vals["me"]:
        me = _pick_me(odoo, vals["me"])
        if me:
            parser[env]["me_id"] = str(me[0])
            with open(CONFIG_PATH, "w") as fh:
                parser.write(fh)
            print(f"You are {me[1]} (user id {me[0]}).")
    print("\nSetup done. Go back to the terminal where Claude is running and run the\n"
          "command again, e.g. /ticket-list or /ticket T1234.")


def _plain(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return re.sub(r"[^a-z ]", "", re.sub(r"\(.*?\)", "", text))


def _login_matches(login, name):
    """jdoe, jane.doe, janed, doe … for "Jane Doe"."""
    local = re.sub(r"[^a-z]", "", _plain(login.split("@")[0]))
    words = _plain(name).split()
    if not local or len(words) < 2:
        return False
    first, last = words[0], words[-1]
    return local in {first[0] + last, first + last, last + first[0], first + last[0], last}


def _pick_me(odoo, login):
    """The user's own (id, name): by login, else matched among the task
    assignees when this account may not read that user. Never lists everyone."""
    users = find_users(odoo, login)
    if len(users) == 1:
        return users[0]
    people = task_assignees(odoo).items()
    guess = [(uid, name) for uid, name in people if _login_matches(login, name)]
    if len(guess) == 1:
        answer = input(f"You are {guess[0][1]}? [Y/n] ").strip().lower()
        if answer in ("", "y", "yes"):
            return guess[0]
    while True:
        typed = input("Your name as shown in Odoo (Enter to skip): ").strip()
        if not typed:
            break
        words = _plain(typed).split()
        found = [(uid, name) for uid, name in people
                 if all(w in _plain(name).split() for w in words)]
        if len(found) == 1:
            return found[0]
        if not found:
            print("No one with tasks matches that name.")
            continue
        for i, (_uid, name) in enumerate(found, 1):
            print(f"  {i}. {name}")
        choice = input("Number (Enter to type again): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(found):
            return found[int(choice) - 1]
    print("Skipped: /ticket-list and /ticket-stats will need --assignee.")
    return None


def install_ner():
    """Create the name-detection venv and install Presidio + 4 spaCy models."""
    import subprocess
    import venv

    print(f"Installing Presidio + spaCy (EN/DE/FR/IT, about 1 GB) into {NER_VENV}")
    py = os.path.join(NER_VENV, "bin", "python")
    if not os.path.exists(py):
        venv.create(NER_VENV, with_pip=True)
    subprocess.check_call([py, "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    subprocess.check_call([py, "-m", "pip", "install", "--quiet", *NER_PACKAGES])
    print("Done: name detection is on for every read.")


class _Stripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "li", "tr", "div"):
            self.parts.append("\n")


def html_to_text(html):
    if not html:
        return ""
    s = _Stripper()
    try:
        s.feed(html)
    except Exception:
        return re.sub(r"<[^>]+>", "", html)
    text = "".join(s.parts)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class Odoo:
    def __init__(self, cfg):
        self.cfg = cfg
        common = xmlrpc.client.ServerProxy(f"{cfg['ODOO_URL']}/xmlrpc/2/common")
        self.uid = common.authenticate(
            cfg["ODOO_DB"], cfg["ODOO_LOGIN"], cfg["ODOO_API_KEY"], {}
        )
        if not self.uid:
            sys.exit("Authentication failed. Check ODOO_LOGIN / ODOO_API_KEY / ODOO_DB.")
        self.models = xmlrpc.client.ServerProxy(f"{cfg['ODOO_URL']}/xmlrpc/2/object")

    def execute(self, model, method, *args, **kw):
        # XML-RPC has no keyword args: execute_kw takes (args_list, kwargs_dict).
        # Allow callers to pass the options dict as the last positional arg.
        args = list(args)
        if args and isinstance(args[-1], dict) and not kw:
            kw = args.pop()
        return self.models.execute_kw(
            self.cfg["ODOO_DB"], self.uid, self.cfg["ODOO_API_KEY"],
            model, method, args, kw or {},
        )

    def model_exists(self, model):
        try:
            # ir.model is admin-only in v18; an unknown model makes this fault.
            self.execute(model, "fields_get", [], {"attributes": ["type"]})
            return True
        except Exception:
            return False


def _name(val):
    """Many2one comes back as [id, 'Name'] or False."""
    return val[1] if isinstance(val, (list, tuple)) and len(val) == 2 else (val or "")


def find_ticket(odoo, raw_id, forced_model=None):
    """Return (model, record_id).

    A user-facing "T####" is the project.task **code** field (shown as
    "[T2917] ..."), NOT the database id — those differ and the id is not
    normally visible. Resolve by code first; helpdesk.ticket uses its "number".
    Only as a last resort do we treat the digits as a raw db id (with a warning),
    since that could otherwise silently hit a different task.
    """
    num = raw_id.upper().lstrip("T").strip()
    code = "T" + num
    candidates = [forced_model] if forced_model else ["project.task", "helpdesk.ticket"]
    for model in candidates:
        if not model or not odoo.model_exists(model):
            continue
        if model == "project.task":
            fields = odoo.execute(model, "fields_get", [], {"attributes": []})
            if "code" in fields:
                for val in (code, num):
                    ids = odoo.execute(model, "search", [["code", "=", val]], limit=1)
                    if ids:
                        return model, ids[0]
        if model == "helpdesk.ticket":
            for domain in ([["number", "=", num]], [["number", "ilike", num]]):
                ids = odoo.execute(model, "search", domain, limit=1)
                if ids:
                    return model, ids[0]
    # Last resort: the digits as a raw db id (forced model, or no code match).
    if num.isdigit():
        for model in candidates:
            if not model or not odoo.model_exists(model):
                continue
            ids = odoo.execute(model, "search", [["id", "=", int(num)]], limit=1)
            if ids:
                print(f"[warn] no ticket code {code!r}; resolved {raw_id!r} as raw "
                      f"{model} db id {num}", file=sys.stderr)
                return model, ids[0]
    return None, None


def fetch(odoo, raw_id, forced_model=None):
    model, rec_id = find_ticket(odoo, raw_id, forced_model)
    if not model:
        sys.exit(f"No ticket found for {raw_id!r} in helpdesk.ticket or project.task.")

    fields = [
        "name", "code", "description", "stage_id", "user_ids", "partner_id",
        "priority", "create_date", "write_date", "number", "team_id",
        "tag_ids", "message_ids",
    ]
    existing = odoo.execute(model, "fields_get", [], {"attributes": ["string"]})
    fields = [f for f in fields if f in existing]
    rec = odoo.execute(model, "read", [rec_id], {"fields": fields})[0]

    # The user-facing reference is the task code (e.g. T2917), not the db id.
    label = rec.get("code") or rec.get("number") or rec_id
    out = [f"# {label}: {rec.get('name', '')}", ""]
    out.append(f"- **Model/ID:** `{model}` #{rec_id}  (db id — not the ticket ref)")
    for key, title in [
        ("stage_id", "Stage"), ("partner_id", "Partner"), ("team_id", "Team"),
        ("priority", "Priority"), ("create_date", "Created"),
        ("write_date", "Updated"),
    ]:
        if key in rec and rec[key] not in (False, None, ""):
            val = _name(rec[key]) if key.endswith("_id") else rec[key]
            out.append(f"- **{title}:** {val}")
    if rec.get("user_ids"):
        out.append(f"- **Assignee:** {_assignees(rec, task_assignees(odoo))}")
    out.append("")
    out.append("## Description")
    out.append(html_to_text(rec.get("description")) or "_(empty)_")

    # Comment thread
    msg_ids = rec.get("message_ids") or []
    if msg_ids:
        msgs = odoo.execute(
            "mail.message", "read", msg_ids,
            {"fields": ["date", "author_id", "subject", "body", "message_type"]},
        )
        msgs = [m for m in msgs if html_to_text(m.get("body"))]
        msgs.sort(key=lambda m: m.get("date") or "")
        if msgs:
            out.append("\n## Thread (%d messages)" % len(msgs))
            for m in msgs:
                who = _name(m.get("author_id")) or "system"
                out.append(f"\n**{m.get('date', '')} — {who}**")
                out.append(html_to_text(m.get("body")))

    # Attachments
    try:
        att = odoo.execute(
            "ir.attachment", "search_read",
            [["res_model", "=", model], ["res_id", "=", rec_id]],
            {"fields": ["name", "mimetype", "file_size"]},
        )
        if att:
            out.append("\n## Attachments")
            for a in att:
                out.append(f"- {a['name']} ({a.get('mimetype', '?')}, {a.get('file_size', 0)} bytes)")
    except Exception:
        pass

    print("\n".join(out))


def search(odoo, term, limit):
    for model in ("helpdesk.ticket", "project.task"):
        if not odoo.model_exists(model):
            continue
        # "code" (T####) on project.task, "number" on helpdesk.ticket.
        existing = odoo.execute(model, "fields_get", [], {"attributes": ["string"]})
        want = [f for f in ("name", "code", "number", "stage_id", "user_ids") if f in existing]
        names = task_assignees(odoo)
        ids = odoo.execute(model, "search_read",
                           ["|", ["name", "ilike", term], ["description", "ilike", term]],
                           {"fields": want, "limit": limit})
        if ids:
            print(f"\n## {model}")
            for r in ids:
                label = r.get("code") or r.get("number") or r["id"]
                print(f"- {label}: {r['name']}  [{_name(r.get('stage_id'))}] "
                      f"-> {_assignees(r, names) or 'unassigned'}")


# Stages treated as "completed/closed" — hidden by the default `list` view.
LIST_CLOSED_STAGES = [
    "Done", "Cancelled", "In Production", "Complete", "Rejected", "Merge",
    "User Acceptance",
]
# Actionable-first ordering for grouping the `list` output.
LIST_STAGE_ORDER = [
    "In Progress", "Blocked", "In Review", "Ready", "Backlog", "New Request",
]
# project.task.priority selection -> stars + human label. Higher = more urgent.
PRIORITY_STARS = {"0": "", "1": "⭐", "2": "⭐⭐", "3": "⭐⭐⭐"}
PRIORITY_LABEL = {"0": "Normal", "1": "Important", "2": "High", "3": "Very High"}


def _priority(t):
    """Normalise a task's priority to an int 0..3 (0 = Normal)."""
    try:
        return max(0, min(3, int(t.get("priority") or 0)))
    except (TypeError, ValueError):
        return 0


def task_assignees(odoo):
    """{user id: name} of everyone with tasks. Many2one names come back even
    for users the account may not read (the res.users record rule hides users
    that are not internal and in another company)."""
    groups = odoo.execute(
        "project.task", "read_group", [["user_ids", "!=", False]], ["user_ids"], ["user_ids"],
        {"context": {"active_test": False}})
    return dict(g["user_ids"] for g in groups)


def _assignees(task, names):
    """user_ids is a bare id list; names come from task_assignees()."""
    return ", ".join(names.get(uid, f"user #{uid}") for uid in task.get("user_ids") or [])


def find_users(odoo, who):
    """[(id, name)] matching a login, a name or an id."""
    who = str(who).strip()
    if who.isdigit():
        return [(int(who), task_assignees(odoo).get(int(who), f"user #{who}"))]
    users = odoo.execute(
        "res.users", "search_read",
        [["share", "=", False], "|", ["login", "=", who], ["name", "ilike", who]],
        {"fields": ["id", "name", "login"]},
    )
    exact = [u for u in users if u["login"] == who]
    if exact or users:
        return [(u["id"], u["name"]) for u in (exact or users)]
    return [(uid, name) for uid, name in task_assignees(odoo).items()
            if who.lower() in name.lower()]


def resolve_user(odoo, assignee=None):
    """{"id", "name"} of --assignee, or of the configured `me`."""
    who = assignee or odoo.cfg.get("ODOO_ME_ID") or odoo.cfg.get("ODOO_ME")
    if not who:
        sys.exit(f"No assignee: pass --assignee <login or name>, or set yourself with "
                 f"setup.\n{setup_hint(odoo.cfg['ENV'])}")
    users = find_users(odoo, who)
    if not users:
        hint = "" if assignee else f"\nRerun setup to pick yourself from a list.\n{setup_hint(odoo.cfg['ENV'])}"
        sys.exit(f"No user matching {who!r}.{hint}")
    if len(users) > 1:
        listing = "\n".join(f"  - {name} (id {uid})" for uid, name in users)
        sys.exit(f"Multiple users match {who!r}:\n{listing}\nBe more specific, or pass the id.")
    return {"id": users[0][0], "name": users[0][1]}


def list_tickets(odoo, show_all=False, assignee=None):
    """List a person's project.task tickets (default: the configured `me`),
    grouped by stage. Hides completed stages unless show_all is set."""
    user = resolve_user(odoo, assignee)

    domain = [["user_ids", "in", [user["id"]]]]
    if not show_all:
        domain.append(["stage_id.name", "not in", LIST_CLOSED_STAGES])
    tasks = odoo.execute(
        "project.task", "search_read", domain,
        {"fields": ["code", "name", "stage_id", "project_id", "priority",
                    "create_date"], "limit": 500},
    )

    now = datetime.utcnow()
    base = odoo.cfg["ODOO_URL"]
    scope = "All" if show_all else "Open"
    print(f"# {scope} tickets for {user['name']} ({len(tasks)})")
    if not tasks:
        print("\n_(none)_")
        return

    by_stage = {}
    for t in tasks:
        by_stage.setdefault(_name(t.get("stage_id")) or "(no stage)", []).append(t)

    def stage_key(s):
        try:
            return (0, LIST_STAGE_ORDER.index(s))
        except ValueError:
            return (1, s.lower())

    # Within a stage, most important first: priority desc, then oldest first.
    def row_key(r):
        cd = _parse_dt(r.get("create_date"))
        return (-_priority(r), cd or datetime.max)

    starred = []  # (priority, stage, code, id) for the recommendation footer
    for stage in sorted(by_stage, key=stage_key):
        rows = by_stage[stage]
        print(f"\n## {stage} ({len(rows)})")
        for t in sorted(rows, key=row_key):
            code = t.get("code") or f"#{t['id']}"
            title = " ".join((t.get("name") or "").split())
            if len(title) > 70:
                title = title[:69] + "…"
            proj = _name(t.get("project_id"))
            pr = _priority(t)
            stars = PRIORITY_STARS[str(pr)]
            cd = _parse_dt(t.get("create_date"))
            age = f"{(now - cd).days}d" if cd else "?"
            prefix = f"{stars} " if stars else ""
            meta = f"{PRIORITY_LABEL[str(pr)]} · {age}"
            print(f"- {prefix}**{code}** · {title}"
                  + (f" · _{proj}_" if proj else "") + f" · {meta}")
            print(f"  {base}/web#id={t['id']}&model=project.task&view_type=form")
            if pr:
                starred.append((pr, stage, code))

    if starred:
        starred.sort(key=lambda x: (-x[0], stage_key(x[1])))
        tops = ", ".join(f"{PRIORITY_STARS[str(p)]} {c} ({PRIORITY_LABEL[str(p)]})"
                         for p, _s, c in starred[:5])
        print(f"\n_Priority tickets (highest first): {tops}_")


# Stage classification for stats: "done" (shipped), "cancelled", else "open".
STATS_DONE_STAGES = {"Done", "Complete", "In Production", "Merge", "Ready to Release"}
STATS_CANCELLED_STAGES = {"Cancelled", "Rejected"}


def _stats_status(stage_name):
    if stage_name in STATS_DONE_STAGES:
        return "done"
    if stage_name in STATS_CANCELLED_STAGES:
        return "cancelled"
    return "open"


def _parse_dt(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def _fmt_dur(days):
    if days is None:
        return "—"
    secs = days * 86400
    if secs < 3600:
        return f"{round(secs / 60)} min"
    if secs < 86400:
        return f"{secs / 3600:.1f} h"
    return f"{days:.1f} d"


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


def _bar(n, mx, width=14):
    if not mx or not n:
        return ""
    return "█" * max(1, round(n / mx * width))


def stats(odoo, show_all=False, assignee=None):
    """Fun aggregate stats over project.task — for one person (default `me`) or
    everyone (--all). Includes archived tasks for full history."""
    user = None if show_all else resolve_user(odoo, assignee)
    names = task_assignees(odoo)

    domain = [] if show_all else [["user_ids", "in", [user["id"]]]]
    tasks = odoo.execute(
        "project.task", "search_read", domain,
        {"fields": ["code", "name", "stage_id", "project_id", "user_ids", "create_date",
                    "date_end", "date_assign", "state", "priority",
                    "working_days_close", "active"],
         "context": {"active_test": False}, "limit": 10000},
    )

    now = datetime.utcnow()
    this_year = now.year
    total = len(tasks)
    done = cancelled = open_ = in_prog = blocked = high = archived_open = 0
    close_days, start_days, wdays = [], [], []
    created_year, done_year, done_month = Counter(), Counter(), Counter()
    created_month = Counter()
    proj = Counter()
    fastest = slowest = oldest_open = None
    aging = {30: 0, 90: 0, 180: 0}
    pp_open, pp_done, pp_done_year = Counter(), Counter(), Counter()
    pp_close = defaultdict(list)
    unassigned = 0

    for t in tasks:
        sname = _name(t.get("stage_id"))
        status = _stats_status(sname)
        cd = _parse_dt(t.get("create_date"))
        ed = _parse_dt(t.get("date_end"))
        ad = _parse_dt(t.get("date_assign"))
        # Credit the first assignee only, as v14's single user_id did.
        uname = _assignees({"user_ids": (t.get("user_ids") or [])[:1]}, names)
        pname = _name(t.get("project_id"))
        code = t.get("code") or f"#{t['id']}"
        if pname:
            proj[pname] += 1
        if cd:
            created_year[cd.year] += 1
            created_month[(cd.year, cd.month)] += 1
        if not uname:
            unassigned += 1
        if str(t.get("priority")) in ("1", "2", "3"):
            high += 1

        if status == "done":
            done += 1
            if t.get("working_days_close"):
                wdays.append(t["working_days_close"])
            if cd and ad and ad >= cd:
                start_days.append((ad - cd).total_seconds() / 86400.0)
            if ed:
                done_year[ed.year] += 1
                done_month[(ed.year, ed.month)] += 1
                if uname:
                    pp_done[uname] += 1
                    if ed.year == this_year:
                        pp_done_year[uname] += 1
                if cd:
                    d = (ed - cd).total_seconds() / 86400.0
                    if d >= 0:
                        close_days.append(d)
                        if uname:
                            pp_close[uname].append(d)
                        if fastest is None or d < fastest[0]:
                            fastest = (d, code)
                        if slowest is None or d > slowest[0]:
                            slowest = (d, code)
        elif status == "cancelled":
            cancelled += 1
        else:
            # Only ACTIVE tasks count as real "open" work; archived-but-unclosed
            # tasks (old migrated junk) are tallied separately, not as backlog.
            if not t.get("active"):
                archived_open += 1
                continue
            open_ += 1
            if uname:
                pp_open[uname] += 1
            if t.get("state") == "04_waiting_normal" or "block" in (sname or "").lower():
                blocked += 1
            if sname == "In Progress":
                in_prog += 1
            if cd:
                age = (now - cd).total_seconds() / 86400.0
                if oldest_open is None or age > oldest_open[0]:
                    oldest_open = (age, code, sname or "no stage")
                for thr in aging:
                    if age > thr:
                        aging[thr] += 1

    # last-12-months velocity
    months12 = set()
    y, mo = now.year, now.month
    for _ in range(12):
        months12.add((y, mo))
        mo -= 1
        if mo == 0:
            mo, y = 12, y - 1
    last12 = sum(c for k, c in done_month.items() if k in months12)
    best_month = max(done_month.items(), key=lambda kv: kv[1]) if done_month else None
    # Only actively-open tasks count as "not completed"; done, cancelled and
    # archived-unclosed are all considered closed/resolved.
    closed = total - open_
    comp_rate = (100.0 * closed / total) if total else 0.0

    # ---- render ----
    scope = "everyone" if show_all else user["name"]
    print(f"🎯 **Ticket stats — {scope}** _(lifetime, incl. archived)_\n")
    arch = f" · 🗄️ {archived_open} archived-unclosed" if archived_open else ""
    print(f"📦 **{total}** total · ✅ {done} done · ❌ {cancelled} cancelled · "
          f"🟢 {open_} open{arch}")
    print(f"🔒 **{comp_rate:.0f}%** closed (done or cancelled) — {open_} still open "
          f"({in_prog} in progress, {blocked} blocked)")
    if high:
        print(f"⭐ {high} starred")
    print(f"⏱️ Median close: **{_fmt_dur(_median(close_days))}** "
          f"(mean {_fmt_dur(sum(close_days) / len(close_days) if close_days else None)}"
          f" · {(_median(wdays) or 0):.1f} working days)")
    if start_days:
        print(f"🏃 Median time-to-start (create→assign): {_fmt_dur(_median(start_days))}")
    if fastest:
        print(f"⚡ Fastest close: {fastest[1]} in {_fmt_dur(fastest[0])} · "
              f"🐌 Slowest: {slowest[1]} in {_fmt_dur(slowest[0])}")
    if oldest_open:
        print(f"⏳ Oldest open: {oldest_open[1]} ({oldest_open[0]:.0f} d, {oldest_open[2]}) · "
              f"🧓 aging: {aging[30]} >30d, {aging[90]} >90d, {aging[180]} >180d")
    avg12 = last12 / 12.0
    bm = (f"{best_month[0][0]}-{best_month[0][1]:02d} ({best_month[1]})"
          if best_month else "—")
    print(f"⚡ Velocity: {avg12:.1f} done/mo (last 12) · best month {bm}")

    # per-year bars
    years = sorted(set(created_year) | set(done_year))
    if years:
        mx = max([created_year[y] for y in years] + [done_year[y] for y in years])
        print("\n📅 **Per year** (created vs ✅ done)")
        for y in years:
            cc, dc = created_year[y], done_year[y]
            print(f"  {y}  created {cc:>4} {_bar(cc, mx)}")
            print(f"        ✅ done {dc:>4} {_bar(dc, mx)}")

    # per-month bars for the current year
    cur_created = {m: c for (yy, m), c in created_month.items() if yy == this_year}
    cur_done = {m: c for (yy, m), c in done_month.items() if yy == this_year}
    months = sorted(set(cur_created) | set(cur_done))
    if months:
        mxm = max([cur_created.get(m, 0) for m in months]
                  + [cur_done.get(m, 0) for m in months])
        print(f"\n🗓️ **Per month in {this_year}** (created vs ✅ done)")
        for m in months:
            cc, dc = cur_created.get(m, 0), cur_done.get(m, 0)
            label = f"{this_year}-{m:02d}"
            print(f"  {label}  created {cc:>4} {_bar(cc, mxm)}")
            print(f"           ✅ done {dc:>4} {_bar(dc, mxm)}")

    if proj:
        print("\n🗂️ **Top projects**")
        for name, n in proj.most_common(5):
            print(f"  - {name}: {n}")

    if show_all:
        print("\n👥 **Leaderboards**")
        print(f"  🤷 Unassigned tasks: {unassigned}")

        def board(title, counter, n=5):
            if counter:
                top = " · ".join(f"{nm} ({c})" for nm, c in counter.most_common(n))
                print(f"  {title}: {top}")
        board("🟢 Most open", pp_open)
        board("✅ Most done (lifetime)", pp_done)
        board(f"🏅 Most done in {this_year}", pp_done_year)
        fast = sorted(
            ((nm, _median(ds)) for nm, ds in pp_close.items() if len(ds) >= 5),
            key=lambda x: x[1],
        )[:5]
        if fast:
            print("  ⚡ Fastest closers — median time-to-close, min 5 closed: "
                  + " · ".join(f"{nm} {_fmt_dur(d)}" for nm, d in fast))


def explore(odoo, project=None, limit=15, offset=0):
    """List UNASSIGNED, open project.task tickets to pick up, ranked by ⭐ stars
    (priority) then oldest-first. Paginated via --limit/--offset."""
    closed = list(STATS_DONE_STAGES | STATS_CANCELLED_STAGES)
    domain = [["user_ids", "=", False], ["stage_id.name", "not in", closed]]
    if project:
        domain.append(["project_id.name", "ilike", project])
    total = odoo.execute("project.task", "search_count", domain)
    tasks = odoo.execute(
        "project.task", "search_read", domain,
        {"fields": ["code", "name", "stage_id", "project_id", "priority",
                    "create_date", "description"],
         "order": "priority desc, create_date asc", "limit": limit, "offset": offset},
    )
    now = datetime.utcnow()
    base = odoo.cfg["ODOO_URL"]
    pscope = f" · project ~ {project!r}" if project else ""
    print(f"# 🔎 Pick-up candidates — unassigned & open{pscope} ({total} total)")
    if not tasks:
        print("\n_(none)_")
        return
    start, end = offset + 1, offset + len(tasks)
    print(f"_Showing {start}–{end}, sorted by ⭐ then oldest._\n")
    for t in tasks:
        try:
            pr = int(t.get("priority") or 0)
        except (TypeError, ValueError):
            pr = 0
        stars = "⭐" * pr if pr else "☆"
        code = t.get("code") or f"#{t['id']}"
        title = " ".join((t.get("name") or "").split())
        if len(title) > 80:
            title = title[:79] + "…"
        cd = _parse_dt(t.get("create_date"))
        age = f"{(now - cd).days}d" if cd else "?"
        snip = " ".join(html_to_text(t.get("description")).split())
        if len(snip) > 140:
            snip = snip[:139] + "…"
        print(f"- {stars} **{code}** · {title} · _{_name(t.get('project_id'))}_ · "
              f"{age} · [{_name(t.get('stage_id'))}]")
        if snip:
            print(f"    {snip}")
        print(f"    🔗 {base}/web#id={t['id']}&model=project.task&view_type=form")
    if end < total:
        more = f"--offset {end}" + (f" --project '{project}'" if project else "")
        print(f"\n_…{total - end} more. Next page: `explore {more}`._")


def _use_venv():
    # Name detection (Presidio/spaCy) lives in its own venv; switch into it so
    # callers can keep running plain `python3 odoo_ticket.py`.
    venv_py = os.path.join(NER_VENV, "bin", "python")
    if os.path.exists(venv_py) and os.path.realpath(sys.prefix) != os.path.realpath(NER_VENV):
        os.execv(venv_py, [venv_py, os.path.abspath(__file__)] + sys.argv[1:])


def main():
    _use_venv()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--env", default=os.environ.get("ODOO_ENV", "prod"),
        help="which config.ini section to use: prod | stage | local (default: prod, or $ODOO_ENV)",
    )
    ap.add_argument(
        "--raw", action="store_true",
        help="print real personal data instead of {{TOKENS}} (see sanitizer.py)",
    )
    ap.add_argument(
        "--regex-only", action="store_true",
        help="sanitize without name detection when it isn't installed (misses some names)",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fetch a ticket by id (e.g. T3124)")
    f.add_argument("ticket")
    f.add_argument("--model", help="force model (helpdesk.ticket | project.task)")
    s = sub.add_parser("search", help="search tickets by text")
    s.add_argument("term")
    s.add_argument("--limit", type=int, default=15)
    ls = sub.add_parser(
        "list", help="list a person's open tickets (default: you), grouped by stage")
    ls.add_argument("--all", action="store_true", dest="show_all",
                    help="include completed tickets too (Done/Cancelled/…)")
    ls.add_argument("--assignee", help="login/name to list for (default: `me` in config.ini)")
    stt = sub.add_parser(
        "stats", help="fun aggregate ticket stats (default: you; --all = everyone)")
    stt.add_argument("--all", action="store_true", dest="show_all",
                     help="aggregate across all users (adds leaderboards)")
    stt.add_argument("--assignee", help="login/name to stat (default: `me` in config.ini)")
    ex = sub.add_parser(
        "explore", help="list unassigned open tickets to pick up (⭐ then oldest), paginated")
    ex.add_argument("--project", help="filter by project name (ilike)")
    ex.add_argument("--limit", type=int, default=15, help="page size (default 15)")
    ex.add_argument("--offset", type=int, default=0, help="skip N for pagination")
    sub.add_parser("whoami", help="verify connection and print logged-in user")
    sub.add_parser("setup", help="write this env's section of config.ini (interactive)")
    sub.add_parser("install-ner", help="install name detection (Presidio + spaCy)")

    args = ap.parse_args()

    if args.cmd == "setup":
        return setup(args.env)
    if args.cmd == "install-ner":
        return install_ner()

    cfg = load_config(args.env)
    print(f"[env: {cfg['ENV']} @ {cfg['ODOO_URL']}]", file=sys.stderr)
    odoo = Odoo(cfg)
    if not args.raw:
        _sanitize_session(odoo, args)
    try:
        _run(odoo, args)
    finally:
        sys.stdout.flush()
        sys.stderr.flush()


def _sanitize_session(odoo, args):
    """Mask personal data in everything this run prints."""
    import sanitizer

    san = sanitizer.Sanitizer(ner=True)
    if not san.analyzer and not args.regex_only:
        sys.exit("Name detection is not installed, so names not linked to the ticket "
                 "would leak. Install it once:\n"
                 f"  python3 {os.path.abspath(__file__)} install-ner\n"
                 "or rerun with --regex-only to accept that.")
    model = rec_id = None
    if getattr(args, "ticket", None):
        model, rec_id = find_ticket(odoo, args.ticket)
    sanitizer.register_ticket_people(san, odoo, model, rec_id)
    sanitizer.protect(san)


def _run(odoo, args):
    if args.cmd == "whoami":
        u = odoo.execute("res.users", "read", [odoo.uid], {"fields": ["name", "login"]})[0]
        print(f"Connected as {u['name']} <{u['login']}> (uid={odoo.uid}) "
              f"on {odoo.cfg['ODOO_DB']} @ {odoo.cfg['ODOO_URL']}")
        for m in ("helpdesk.ticket", "project.task", "crm.request"):
            print(f"  model {m}: {'available' if odoo.model_exists(m) else 'not installed'}")
    elif args.cmd == "fetch":
        fetch(odoo, args.ticket, args.model)
    elif args.cmd == "search":
        search(odoo, args.term, args.limit)
    elif args.cmd == "list":
        list_tickets(odoo, show_all=args.show_all, assignee=args.assignee)
    elif args.cmd == "stats":
        stats(odoo, show_all=args.show_all, assignee=args.assignee)
    elif args.cmd == "explore":
        explore(odoo, project=args.project, limit=args.limit, offset=args.offset)


if __name__ == "__main__":
    main()
