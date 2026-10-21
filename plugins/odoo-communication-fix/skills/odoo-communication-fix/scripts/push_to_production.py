#!/usr/bin/env python3
"""Push the corrected texts of mail.template records from the local database to the
production database over SSH. OPTIONAL step, only with the explicit permission of the
user, every time: it writes to production.

Usage:
  push_to_production.py --db <local db> --ids 56 449 59 --ssh user@prod-host --prod-db <prod db>
                        [--psql "sudo -u postgres psql"] [--fields body_html subject]
                        [--langs en_US fr_CH de_DE it_IT] [--dry-run] [--rollback] [--yes]

What it does (and nothing else):
  * reads, in the LOCAL database only, the id, the English name and the `--fields`
    (default: body_html and subject) of the given templates;
  * sends ONE transaction to production with, for each template, an UPDATE that merges
    the English text and the translations of `--langs` into the jsonb value of those
    fields (other languages of production are kept):
        UPDATE mail_template SET body_html = body_html || '{...}'::jsonb, ...
        WHERE id = <id> AND name->>'en_US' = '<English name>'
    The id is the same as in the local database (it comes from a production backup). The
    English name is only a guard: if the id or the name differs, the template is not
    updated and the whole transaction is rolled back (nothing is committed).
  * NEVER reads anything from production, never touches other fields (email_from, reply_to,
    partner_to, model, ...), other tables or other records. psql is run with -At and the
    only output is "ok <id>" lines produced by the transaction itself.

Without --ssh the same SQL is run by a local psql (use it to test on a copy). --dry-run
prints what would be sent (ids, names, fields, languages, sizes), no connection at all.
--rollback runs the whole transaction and rolls it back: tests the connection and the
guards without writing. --yes is required for a real push.
Needs psycopg2.
"""
import argparse
import hashlib
import json
import shlex
import subprocess
import sys

import psycopg2

DEFAULT_FIELDS = ["body_html", "subject"]
DEFAULT_LANGS = ["en_US", "fr_CH", "de_DE", "it_IT"]
FIELD_RE_OK = set("abcdefghijklmnopqrstuvwxyz_")


def literal(value):
    """SQL string literal (standard_conforming_strings is on by default)."""
    return "'" + str(value).replace("'", "''") + "'"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, help="local database (read only)")
    ap.add_argument("--ids", nargs="+", type=int, required=True)
    ap.add_argument("--ssh", help="user@host of the production server (omit to use a local psql)")
    ap.add_argument("--prod-db", required=True, help="name of the production database")
    ap.add_argument("--psql", default="psql", help='psql command on the server, e.g. "sudo -u postgres psql"')
    ap.add_argument("--fields", nargs="+", default=DEFAULT_FIELDS)
    ap.add_argument("--langs", nargs="+", default=DEFAULT_LANGS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    for field in args.fields:
        if not field or set(field) - FIELD_RE_OK:
            sys.exit(f"refused field name: {field!r}")
    if args.fields and set(args.fields) - {"body_html", "subject", "name"}:
        sys.exit("only the translated text fields body_html, subject and name can be pushed")

    cur = psycopg2.connect(dbname=args.db).cursor()
    cols = ", ".join(f"t.{f}" for f in args.fields)
    cur.execute(f"select t.id, t.name->>'en_US', {cols} from mail_template t where t.id in %s order by t.id",
                (tuple(args.ids),))
    rows = cur.fetchall()
    missing = set(args.ids) - {r[0] for r in rows}
    if missing:
        sys.exit(f"not in the local database: {sorted(missing)}")

    statements = []
    print(f"{'id':>5}  {'template':50s} fields / languages / size")
    for row in rows:
        tid, name, values = row[0], row[1], row[2:]
        sets = []
        detail = []
        for field, value in zip(args.fields, values):
            value = value or {}
            part = {lang: value[lang] for lang in args.langs if value.get(lang) is not None}
            if "en_US" not in part:
                sys.exit(f"template {tid}: no en_US value for {field}")
            sets.append(f"{field} = coalesce({field}, '{{}}'::jsonb) || {literal(json.dumps(part, ensure_ascii=False))}::jsonb")
            detail.append(f"{field}[{','.join(sorted(part))}] {sum(len(v) for v in part.values())} chars "
                          f"#{hashlib.md5(json.dumps(part, sort_keys=True).encode()).hexdigest()[:6]}")
        print(f"{tid:5d}  {name[:50]:50s} {'; '.join(detail)}")
        statements.append(
            "DO $$ DECLARE n int; BEGIN\n"
            f"  UPDATE mail_template SET {', '.join(sets)}\n"
            f"  WHERE id = {tid} AND name->>'en_US' = {literal(name)};\n"
            "  GET DIAGNOSTICS n = ROW_COUNT;\n"
            f"  IF n <> 1 THEN RAISE EXCEPTION 'template {tid}: not updated (id or English name differs)'; END IF;\n"
            f"  RAISE NOTICE 'ok {tid}';\n"
            "END $$;"
        )

    sql = "\\set ON_ERROR_STOP on\nBEGIN;\n" + "\n".join(statements) + ("\nROLLBACK;" if args.rollback else "\nCOMMIT;") + "\n"
    psql = f"{args.psql} -X -q -At -d {shlex.quote(args.prod_db)}"
    command = ["ssh", args.ssh, psql] if args.ssh else shlex.split(psql)
    print("\ncommand:", " ".join(shlex.quote(c) for c in command))
    print(f"{len(rows)} template(s), fields {args.fields}, languages {args.langs}, "
          f"{'ROLLBACK (test)' if args.rollback else 'COMMIT'}")
    if args.dry_run:
        print("dry run: nothing sent")
        return
    if not args.rollback and not args.yes:
        sys.exit("refused: a real push needs --yes (ask the user first)")
    result = subprocess.run(command, input=sql, text=True, capture_output=True)
    for line in (result.stderr or "").splitlines():
        if "NOTICE" in line or "ERROR" in line or "EXCEPTION" in line:
            print(line)
    if result.returncode != 0:
        sys.exit(f"failed (exit {result.returncode}), the transaction was rolled back, nothing was written")
    print("rolled back (test only)" if args.rollback else "committed")


if __name__ == "__main__":
    main()
