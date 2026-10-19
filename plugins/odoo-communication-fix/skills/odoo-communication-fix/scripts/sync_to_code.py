#!/usr/bin/env python3
"""Sync mail.template records from a database (source of truth) to the Odoo
source code: XML data files (English subject/body) and the .po files.

Usage:
  sync_to_code.py --db <database> --config templates.json [--dry-run] [--create-missing]

templates.json (paths are absolute or relative to the config file):
{
  "langs": ["fr_CH", "de_DE", "it_IT"],
  "templates": [
    {"id": 56, "module": "partner_communication_compassion", "xmlid": "new_letter",
     "xml_file": "/path/to/module/data/child_letter_emails.xml",
     "i18n_dir": "/path/to/module/i18n"}
  ]
}
What it does for every template:
  * XML: replaces <field name="subject"> and <field name="body_html" type="html"> of the
    record (the QWeb body without <html><body>). With --create-missing a record that
    does not exist in the file yet is created from the database values.
  * .po: sets msgid = English value of the database, msgstr = translation of the database,
    for the fields name, subject and body_html. Missing entries get the
    "#. module: <module>" comment required by the OCA po checks.
Requires psycopg2, polib, lxml. Nothing is written with --dry-run.
"""
import argparse
import html
import json
import os
import re
import sys
from xml.sax.saxutils import escape

import polib
import psycopg2
from lxml import etree


def load(path, base):
    return path if os.path.isabs(path) else os.path.join(base, path)


def xml_body(body, indent="                "):
    root = etree.fromstring(body)
    bd = root.find("body")
    out = (bd.text or "") + "".join(etree.tostring(c, encoding="unicode") for c in bd)
    out = out.replace("\xa0", "&#160;")
    lines = [l.rstrip() for l in out.strip("\n").split("\n") if l.strip()]
    common = min(len(l) - len(l.lstrip()) for l in lines)
    return "\n" + "\n".join(indent + l[common:] for l in lines) + "\n            "


def new_record(xid, d, model_ref):
    return f"""        <record id="{xid}" model="mail.template">
            <field name="name">{escape(d['name']['en_US'])}</field>
            <field name="model_id" ref="{model_ref}" />
            <field name="email_from">{escape(d['email_from'] or '')}</field>
            <field name="reply_to">{escape(d['reply_to'] or '')}</field>
            <field name="partner_to">{escape(d['partner_to'] or '')}</field>
            <field name="subject">PLACEHOLDER</field>
            <field name="body_html" type="html">PLACEHOLDER</field>
        </record>
"""


def update_xml(path, edits, create_missing, data):
    s = open(path, encoding="utf-8").read()
    original = s
    for tid, xid, model_ref in edits:
        d = data[tid]
        m = re.search(r'<record id="%s" model="mail.template">.*?</record>' % re.escape(xid), s, re.S)
        if not m:
            if not create_missing:
                print("  XML record %s missing in %s (use --create-missing)" % (xid, path))
                continue
            s = s.replace("</odoo>", new_record(xid, d, model_ref) + "</odoo>", 1)
            m = re.search(r'<record id="%s" model="mail.template">.*?</record>' % re.escape(xid), s, re.S)
        rec = m.group(0)
        new = rec
        sm = re.search(r'<field\s+name="subject"\s*>.*?</field>', new, re.S)
        new = new.replace(sm.group(0), '<field name="subject">%s</field>' % escape(d["subject"]["en_US"]), 1)
        bm = re.search(r'(<field name="body_html" type="html">).*?(</field>)', new, re.S)
        new = new[: bm.start()] + bm.group(1) + xml_body(d["body"]["en_US"]) + bm.group(2) + new[bm.end():]
        s = s.replace(rec, new, 1)
    return original, s


def set_entry(po, key, module, msgid, msgstr):
    ents = [e for e in po if any(o[0] == key for o in e.occurrences)]
    if ents:
        e = ents[0]
        assert len(e.occurrences) == 1, "entry shared by several records: " + key
        e.msgid, e.msgstr = msgid, msgstr
        e.flags = [f for f in e.flags if f != "fuzzy"]
        return
    e = po.find(msgid)
    if e:
        e.occurrences.append((key, ""))
        e.msgstr = msgstr
        return
    po.append(polib.POEntry(msgid=msgid, msgstr=msgstr, occurrences=[(key, "")],
                            comment="module: " + module))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--create-missing", action="store_true")
    a = ap.parse_args()
    base = os.path.dirname(os.path.abspath(a.config))
    cfg = json.load(open(a.config))
    langs = cfg.get("langs", ["fr_CH", "de_DE", "it_IT"])
    conn = psycopg2.connect(dbname=a.db)
    cur = conn.cursor()
    data = {}
    for t in cfg["templates"]:
        cur.execute(
            "select name, subject, body_html, email_from, reply_to, partner_to, model_id "
            "from mail_template where id=%s", (t["id"],))
        row = cur.fetchone()
        assert row, "template %s not found in %s" % (t["id"], a.db)
        n, s, b, ef, rt, pt, model_id = row
        cur.execute(
            "select module||'.'||name from ir_model_data where model='ir.model' and res_id=%s",
            (model_id,))
        mref = (cur.fetchone() or ["base.model_res_partner"])[0]
        data[t["id"]] = dict(name=n, subject=s, body=b, email_from=ef, reply_to=rt, partner_to=pt, model_ref=mref)
    changed = []
    by_file = {}
    for t in cfg["templates"]:
        by_file.setdefault(load(t["xml_file"], base), []).append((t["id"], t["xmlid"], data[t["id"]]["model_ref"]))
    for path, edits in by_file.items():
        old, new = update_xml(path, edits, a.create_missing, data)
        if old != new:
            changed.append(path)
            if not a.dry_run:
                open(path, "w", encoding="utf-8").write(new)
    for t in cfg["templates"]:
        mod, xid, d = t["module"], t["xmlid"], data[t["id"]]
        for lang in langs:
            path = os.path.join(load(t["i18n_dir"], base), lang + ".po")
            po = polib.pofile(path, wrapwidth=78)
            for fld, src in (("name", d["name"]), ("subject", d["subject"]), ("body_html", d["body"])):
                en = src["en_US"]
                tr = src.get(lang) or ""
                if fld == "name" and tr == en:
                    tr = ""
                set_entry(po, "model:mail.template,%s:%s.%s" % (fld, mod, xid), mod, en, tr)
            if str(po) != open(path, encoding="utf-8").read():
                changed.append(path)
                if not a.dry_run:
                    po.save(path)
    print(("would change" if a.dry_run else "changed"), len(set(changed)), "file(s):")
    for p in sorted(set(changed)):
        print(" ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
