#!/usr/bin/env python3
"""Compare the corrected templates of a reference database (source of truth) with a
test database that went through the migration.

Usage:
  compare_databases.py --ref swiss18 --test swiss18_new --config templates.json

templates.json is the one of sync_to_code.py (id = id in the reference database,
module + xmlid = the record in the test database). Checks, per template:
  * fr/de/it body, subject and sender fields identical;
  * English body identical once whitespace is normalised and the
    data-o-mail-quote attributes (added by Odoo when it loads HTML) are ignored;
  * no duplicate template with the same English name in the test database.
Exit code 1 if something differs. Read only. Needs psycopg2 and lxml.
"""
import argparse
import hashlib
import json
import re
import sys

import psycopg2
from lxml import etree, html


def norm(text):
    root = html.fragment_fromstring(text or "<p/>", create_parent="x")
    for el in list(root.iter("html", "body")):
        el.drop_tag()
    out = etree.tostring(root, method="c14n").decode()
    out = out.replace(' data-o-mail-quote="1"', "").replace(' data-o-mail-quote-node="1"', "")
    return re.sub(r"\s+", " ", re.sub(r">\s+<", "><", out)).strip()


def md5(value):
    return hashlib.md5(json.dumps(value, sort_keys=True).encode()).hexdigest()[:8]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--test", required=True)
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = json.load(open(args.config))
    ref = psycopg2.connect(dbname=args.ref).cursor()
    test = psycopg2.connect(dbname=args.test).cursor()
    bad = 0
    for t in cfg["templates"]:
        ref.execute("select name->>'en_US', body_html, subject, email_from, reply_to, partner_to from mail_template where id=%s", (t["id"],))
        r = ref.fetchone()
        test.execute("""select t.id, t.body_html, t.subject, t.email_from, t.reply_to, t.partner_to
                        from mail_template t join ir_model_data d on d.model='mail.template' and d.res_id=t.id
                        where d.module=%s and d.name=%s""", (t["module"], t["xmlid"]))
        x = test.fetchone()
        if not r or not x:
            print(f"{t['xmlid']:45s} MISSING (ref={bool(r)} test={bool(x)})"); bad += 1; continue
        problems = []
        for lang in cfg.get("langs", ["fr_CH", "de_DE", "it_IT"]):
            if (r[1] or {}).get(lang) != (x[1] or {}).get(lang):
                problems.append(f"body {lang}")
        if norm((r[1] or {}).get("en_US")) != norm((x[1] or {}).get("en_US")):
            problems.append("body en_US")
        if md5(r[2]) != md5(x[2]):
            problems.append("subject")
        if r[3:] != x[3:]:
            problems.append("sender fields")
        test.execute("select count(*) from mail_template where name->>'en_US'=%s", (r[0],))
        if test.fetchone()[0] > 1:
            problems.append("DUPLICATE name")
        print(f"{t['xmlid']:45s} {'OK' if not problems else 'DIFFERENT: ' + ', '.join(problems)}")
        bad += bool(problems)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
