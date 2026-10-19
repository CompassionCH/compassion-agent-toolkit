#!/usr/bin/env python3
"""List the fields/methods used by mail templates that are defined only in modules
outside the dependency closure of the module that ships the templates.

A template that reads such an attribute works in your database (the module is
installed) but fails to render in a fresh environment (another country, CI, tests).

Usage:
  check_dependencies.py --module partner_communication_compassion \
      --xml data/child_letter_emails.xml data/depart_communications.xml \
      [--ids new_letter final_letter] [--root ~/Dev] [--version 18]

  --xml   data files of the module (relative to the module folder or absolute)
  --ids   xmlids of the records to check (default: all mail.template records of the files)
Looks for modules in NN-addons, NN-odoo, NN-enterprise under --root. Nothing is written.
How to handle a hit: see reference/rules.md ("Optional fields").
"""
import argparse
import ast
import os
import re
import sys

from lxml import etree

SKIP_DIRS = {".git", "node_modules", "static", "i18n", "tests", "migrations", "__pycache__"}
# ORM / Python names that are never a field defined by a module
NOISE = {"ids", "id", "filtered", "mapped", "sorted", "upper", "lower", "title", "get", "format",
         "join", "replace", "split", "strip", "items", "keys", "values", "append", "with_context",
         "sudo", "browse", "exists", "ensure_one", "write", "create", "search", "env", "name",
         "days", "year", "month", "day"}


def find_modules(root, version):
    mods = {}
    bases = [f"{root}/{version}-addons", f"{root}/{version}-odoo/addons",
             f"{root}/{version}-odoo/odoo/addons", f"{root}/{version}-enterprise"]
    for base in bases:
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            if "__manifest__.py" in fn:
                name = os.path.basename(dp)
                if name.startswith("test_"):
                    continue
                try:
                    manifest = ast.literal_eval(open(os.path.join(dp, "__manifest__.py")).read())
                except Exception:
                    continue
                mods.setdefault(name, (dp, manifest.get("depends", [])))
    return mods


def closure(mods, name, seen=None):
    seen = seen if seen is not None else set()
    if name in seen or name not in mods:
        return seen
    seen.add(name)
    for dep in mods[name][1]:
        closure(mods, dep, seen)
    return seen


def definitions(mods):
    defs = {}
    pattern = re.compile(r"^\s{4}(\w+)\s*=\s*fields\.\w+|^\s{4}def (\w+)\(", re.M)
    for name, (path, _) in mods.items():
        for dp, dn, fn in os.walk(path):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            for f in fn:
                if f.endswith(".py"):
                    try:
                        src = open(os.path.join(dp, f), encoding="utf-8").read()
                    except Exception:
                        continue
                    for m in pattern.finditer(src):
                        defs.setdefault(m.group(1) or m.group(2), set()).add(name)
    return defs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module", required=True)
    ap.add_argument("--xml", nargs="+", required=True)
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--root", default=os.path.expanduser("~/Dev"))
    ap.add_argument("--version", default="18")
    args = ap.parse_args()

    mods = find_modules(args.root, args.version)
    if args.module not in mods:
        sys.exit(f"module {args.module} not found under {args.root}")
    inside = closure(mods, args.module)
    defs = definitions(mods)
    print(f"{args.module}: dependency closure of {len(inside)} modules")
    found = False
    for xml in args.xml:
        path = xml if os.path.isabs(xml) else os.path.join(mods[args.module][0], xml)
        for rec in etree.parse(path).getroot().iter("record"):
            if rec.get("model") != "mail.template":
                continue
            if args.ids and rec.get("id") not in args.ids:
                continue
            raw = " ".join(etree.tostring(f, encoding="unicode") for f in rec.findall("field"))
            # attributes protected with  'field' in record._fields
            guarded = set(re.findall(r"(?:'|&#x27;|&quot;|\")(\w+)(?:'|&#x27;|&quot;|\")\s+in\s+[^<>]*?_fields", raw))
            text = re.sub(r"&[a-z]+;|&#x27;", " ", raw)
            attrs = set(re.findall(r"\.(?:with_context\([^)]*\)\.)?([a-z_][a-z0-9_]*)\b", text)) - NOISE
            outside = {a: sorted(defs[a])[:3] for a in sorted(attrs) if a in defs and not (defs[a] & inside)}
            risky = {a: m for a, m in outside.items() if a not in guarded}
            ok_guarded = sorted(set(outside) & guarded)
            found = found or bool(risky)
            print(f"  {rec.get('id')}: UNGUARDED {risky}" if risky else f"  {rec.get('id')}: ok", f"(guarded: {ok_guarded})" if ok_guarded else "")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
