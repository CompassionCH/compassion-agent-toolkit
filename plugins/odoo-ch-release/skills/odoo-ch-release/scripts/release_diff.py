#!/usr/bin/env python3
"""Compute what `git pull && git submodule update` would bring, read-only.

It runs ON THE TARGET SERVER (production or stage), after `git fetch`, and compares what is
checked out now (HEAD, submodules as currently checked out) with what the
pull would bring (@{u}, and the submodule commits that its tree points to).

Run it from the local machine, no copy needed (use printf %q to quote the arguments):

  ssh <ssh host> <server python> - [--ticket-regex REGEX] <repo path on the server> ... \
      < release_diff.py > diff.json

Output JSON: a list with, per repository (recursively through moved
submodules): the commits, their T-numbers, the changed Odoo modules with the
files that triggered them, and new / removed modules.

Each changed module has `update: true` when something in it affects the
database (so `-u` is needed) and `update: false` when only code changed
(a service restart is enough). `reasons` says why, `files` lists the changes.
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys

DEFAULT_TICKET_REGEX = r"\bT\d{3,6}\b"
TICKET = re.compile(DEFAULT_TICKET_REGEX)
# Files that do not change module behaviour on their own
IGNORED = re.compile(r"(^|/)(tests?|i18n|static/description|migrations?)/|\.md$|\.rst$|\.pot?$")
RUNTIME = re.compile(r"\.(py|xml|csv|js|scss|css)$")


def git(path, *args, check=True):
    # per-command safe.directory: the worktrees are owned by root; nothing is written to the git config
    res = subprocess.run(["git", "-c", f"safe.directory={os.path.abspath(path)}", "-C", path, *args], capture_output=True, text=True)
    if check and res.returncode:
        sys.exit(f"git {' '.join(args)} failed in {path}: {res.stderr.strip()}")
    return res.stdout


def manifest_dirs(path, rev):
    out = git(path, "ls-tree", "-r", "--name-only", rev)
    return {os.path.dirname(f) for f in out.splitlines() if f.endswith("/__manifest__.py") or f == "__manifest__.py"}


def pointers(path, rev):
    """{submodule path: sha} of a revision, from the tree (gitlinks)."""
    out = git(path, "ls-tree", "-r", rev)
    return {l.split("\t")[1]: l.split()[2] for l in out.splitlines() if l.startswith("160000")}


# Manifest keys that do not change the database content when edited
MANIFEST_NEUTRAL = {"version", "post_load", "author", "website", "license", "maintainers",
                    "development_status", "summary", "description", "category", "images",
                    "external_dependencies", "assets", "sequence"}
# A python diff line touching the schema or what is stored for models
SCHEMA = re.compile(r"fields\.\w+\(|^\s*_(name|inherit|inherits|table|order|rec_name|sql_constraints|"
                    r"parent_name|description|check_company_auto)\b|\b(store|index|compute|related|"
                    r"ondelete|domain|selection|selection_add)\s*=|\bhelp\s*=|\bstring\s*=")


def manifest(path, rev, f):
    res = subprocess.run(["git", "-c", f"safe.directory={os.path.abspath(path)}", "-C", path,
                          "show", f"{rev}:{f}"], capture_output=True, text=True)
    try:
        return ast.literal_eval(res.stdout)
    except (ValueError, SyntaxError):
        return None


def db_reason(path, base, new, f):
    """Why the file affects the database, or None when it is code only."""
    if f.endswith("__manifest__.py"):
        old, cur = manifest(path, base, f), manifest(path, new, f)
        if old is None or cur is None:
            return "manifest not readable"
        keys = sorted(k for k in set(old) | set(cur)
                      if k not in MANIFEST_NEUTRAL and old.get(k) != cur.get(k))
        return "manifest: " + ", ".join(keys) if keys else None
    if re.search(r"(^|/)migrations?/", f):
        return "migration script"
    if f.endswith((".xml", ".csv")):
        return "data/view file"
    if f.endswith(".po"):
        return "translations"
    if f.endswith(".py"):
        diff = git(path, "diff", "-U0", f"{base}..{new}", "--", f)
        lines = [l[1:] for l in diff.splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        if any(SCHEMA.search(l) for l in lines):
            return "model definition (fields/schema)"
    return None  # js, scss, css, other python: runtime code only


def analyse(name, path, base, new, result):
    log = git(path, "log", "--no-merges", "--format=%h%x09%an%x09%s%n%b%x00", f"{base}..{new}")
    commits = []
    for chunk in log.split("\x00"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        head, _, body = chunk.partition("\n")
        h, author, subject = head.split("\t", 2)
        commits.append({"hash": h, "author": author, "subject": subject,
                        "tickets": sorted(set(TICKET.findall(subject + " " + body)))})
    files = git(path, "diff", "--name-only", f"{base}..{new}").splitlines()
    old_mods, new_mods = manifest_dirs(path, base), manifest_dirs(path, new)
    changed = {}
    for f in files:
        if re.search(r"(^|/)(tests?|static/description)/|\.(md|rst|pot)$", f):
            continue
        if not (RUNTIME.search(f) or f.endswith((".po", "__manifest__.py"))):
            continue
        parts = f.split("/")
        for i in range(len(parts) - 1, 0, -1):
            sub = "/".join(parts[:i])
            if sub in new_mods:
                mod = changed.setdefault(parts[i - 1], {"path": sub, "files": [], "reasons": []})
                mod["files"].append(f)
                reason = db_reason(path, base, new, f)
                if reason and reason not in mod["reasons"]:
                    mod["reasons"].append(reason)
                break
    for mod in changed.values():
        mod["update"] = bool(mod["reasons"])
    result.append({
        "repo": name, "from": base[:10], "to": new[:10], "commits": commits,
        "modules": changed,
        "new_modules": sorted(os.path.basename(m) for m in new_mods - old_mods),
        "removed_modules": sorted(os.path.basename(m) for m in old_mods - new_mods),
    })
    old_p, new_p = pointers(path, base), pointers(path, new)
    for sub, sha in new_p.items():
        if old_p.get(sub) == sha:
            continue
        subpath = os.path.join(path, sub)
        if sub not in old_p:
            result.append({"repo": f"{name}/{sub}", "from": None, "to": sha[:10],
                           "commits": [], "modules": {}, "note": "new submodule"})
            continue
        # The superproject fetch also fetches changed submodules (on-demand);
        # if the commit is still missing, say so instead of guessing.
        if git(subpath, "cat-file", "-t", sha, check=False).strip() != "commit":
            sys.exit(f"{subpath}: commit {sha} not fetched; run `git -C {subpath} fetch`")
        # Compare with what is checked out in the submodule now
        current = git(subpath, "rev-parse", "HEAD").strip()
        analyse(f"{name}/{sub}", subpath, current, sha, result)


def main():
    global TICKET
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticket-regex", default=DEFAULT_TICKET_REGEX,
                        help="regex of a ticket reference in commit messages")
    parser.add_argument("repos", nargs="+", help="paths of the repositories on this server")
    args = parser.parse_args()
    TICKET = re.compile(args.ticket_regex)
    result = []
    for path in args.repos:
        base = git(path, "rev-parse", "HEAD").strip()
        new = git(path, "rev-parse", "@{u}").strip()
        analyse(os.path.basename(path.rstrip("/")), path, base, new, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
