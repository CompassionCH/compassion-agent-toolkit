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
A module that does not exist at the old commit is `new: true, update: false`:
the release never installs modules, and `-u` ignores a module that is not
installed anyway.

Every submodule whose checked-out commit differs from the pointer that the
pull would give is analysed, whether the pointer moved or not (`drift: true`
when the server has a different commit checked out than the recorded one):
`git submodule update` resets it, so what it changes must be known.

Whether a Python change touches the schema is decided on the syntax tree, not
on words in the diff: the field definitions (`fields.X(...)`, `models.Constraint`
...) and the `_name`, `_inherit`, `_inherits`, `_table`, `_sql_constraints`
class attributes of the old and the new file are compared. A stored compute
whose `@api.depends` changed is NOT detected: read such diffs.
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
# Class attributes that define a model for the database
SCHEMA_ATTRS = {"_name", "_inherit", "_inherits", "_table", "_sql_constraints"}


def _is_schema_call(value):
    """fields.Char(...), models.Constraint(...), models.Index(...)."""
    if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)):
        return False
    owner = value.func.value
    if not isinstance(owner, ast.Name):
        return False
    return owner.id == "fields" or (
        owner.id == "models" and value.func.attr in ("Constraint", "Index", "UniqueIndex")
    )


def schema_signature(source):
    """{(class, attribute): dump} of the field definitions and the model keys."""
    sig = {}
    for cls in ast.walk(ast.parse(source)):
        if not isinstance(cls, ast.ClassDef):
            continue
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign):
                targets, value = stmt.targets, stmt.value
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                targets, value = [stmt.target], stmt.value
            else:
                continue
            for target in targets:
                if isinstance(target, ast.Name) and (
                    target.id in SCHEMA_ATTRS or _is_schema_call(value)
                ):
                    sig[(cls.name, target.id)] = ast.dump(value)
    return sig


def source_at(path, rev, f):
    res = subprocess.run(["git", "-c", f"safe.directory={os.path.abspath(path)}", "-C", path,
                          "show", f"{rev}:{f}"], capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else ""


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
        try:
            if schema_signature(source_at(path, base, f)) != schema_signature(source_at(path, new, f)):
                return "model definition (fields/schema)"
        except SyntaxError:
            return "python file not parsable: schema change not excluded"
    return None  # js, scss, css, other python: runtime code only


def analyse(name, path, base, new, result, drift=None):
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
    added = {os.path.basename(m) for m in new_mods - old_mods}
    for mname, mod in changed.items():
        if mname in added:
            mod.update(update=False, new=True, reasons=["new module: never installed by the release"])
        else:
            mod["update"] = bool(mod["reasons"])
    result.append({
        "repo": name, "from": base[:10], "to": new[:10], "commits": commits,
        "modules": changed,
        "new_modules": sorted(added),
        "removed_modules": sorted(os.path.basename(m) for m in old_mods - new_mods),
        **({"drift": True, "note": drift} if drift else {}),
    })
    old_p, new_p = pointers(path, base), pointers(path, new)
    for sub, sha in new_p.items():
        subpath = os.path.join(path, sub)
        if not os.path.exists(os.path.join(subpath, ".git")):
            continue  # not initialised on this server: the update will not touch it
        if sub not in old_p:
            result.append({"repo": f"{name}/{sub}", "from": None, "to": sha[:10],
                           "commits": [], "modules": {}, "note": "new submodule"})
            continue
        # The superproject fetch also fetches changed submodules (on-demand);
        # if the commit is still missing, say so instead of guessing.
        if git(subpath, "cat-file", "-t", sha, check=False).strip() != "commit":
            sys.exit(f"{subpath}: commit {sha} not fetched; run `git -C {subpath} fetch`")
        current = git(subpath, "rev-parse", "HEAD").strip()
        if current == sha:
            continue
        # What `git submodule update` will change in the submodule, pointer moved or not
        drift = None
        if current != old_p[sub]:
            drift = (f"checked out at {current[:10]} while the repository records {old_p[sub][:10]}: "
                     f"`git submodule update` resets it to {sha[:10]}")
        analyse(f"{name}/{sub}", subpath, current, sha, result, drift)


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
