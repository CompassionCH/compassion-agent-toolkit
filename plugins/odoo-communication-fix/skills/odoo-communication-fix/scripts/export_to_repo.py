#!/usr/bin/env python3
"""Write the corrected templates to a repository that keeps one HTML file per
communication config and language (the "comm-rules" repository).

Usage:
  export_to_repo.py --db swiss18 --repo ~/Dev/comm-rules --ids 56 449 59 [--dry-run]

File name: "<config name>_<EN|FR|DE|IT>.html", where the config name is the name of
the utm.source of the partner.communication.config that uses the template. The content
is the body_html of the database for that language, byte for byte (no added newline).
A template used by several configs is written for each of them. Files that do not
exist yet are created. Nothing is committed. Needs psycopg2.
"""
import argparse
import os

import psycopg2

LANGS = (("en_US", "EN"), ("fr_CH", "FR"), ("de_DE", "DE"), ("it_IT", "IT"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ids", nargs="+", type=int, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cur = psycopg2.connect(dbname=args.db).cursor()
    cur.execute("""select t.id, s.name, t.body_html
                   from partner_communication_config c
                   join utm_source s on s.id = c.source_id
                   join mail_template t on t.id = c.email_template_id
                   where t.id in %s order by t.id, s.name""", (tuple(args.ids),))
    rows = cur.fetchall()
    missing = set(args.ids) - {r[0] for r in rows}
    if missing:
        print("No communication config uses template(s):", sorted(missing))
    for tid, name, body in rows:
        for lang, suffix in LANGS:
            value = body.get(lang)
            if value is None:
                print(f"{tid:5d} {name}_{suffix}.html: no {lang} text in the database")
                continue
            path = os.path.join(os.path.expanduser(args.repo), f"{name}_{suffix}.html")
            old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            status = "created" if old is None else ("unchanged" if old == value else "updated")
            if status != "unchanged" and not args.dry_run:
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(value)
            print(f"{tid:5d} {os.path.basename(path):60s} {status}")


if __name__ == "__main__":
    main()
