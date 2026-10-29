#!/usr/bin/env python3
"""Who is connected to the Odoo database inside a transaction.

Runs ON THE SERVER with the Python of the Odoo virtualenv. Read-only: one
`SELECT` on `pg_stat_activity`, in a read-only transaction. Credentials stay in
the Odoo configuration file, read by Odoo's own loader, never printed. No Odoo
module is loaded.

  ssh <ssh> "$(printf '%q ' <python> - <odoo_dir>/<odoo_bin> <odoo_dir>/<conf> <db> [--after-stop])" \
      < sessions.py

What blocks an update is a session that is INSIDE a transaction: it holds table
locks until it ends, even a plain `SELECT` (`AccessShareLock` is enough to make
an `ALTER TABLE` wait). A session outside a transaction (`idle`, for example a
forgotten `odoo-bin shell`) holds nothing and is harmless. The locks in
`pg_locks` are deliberately not used: every running transaction holds an
exclusive lock on its own transaction id, so they flag Odoo's own workers.

Two uses, one script:
  - before the stop, the services still run: their short transactions show up,
    so the result is ADVISORY. Only the long ones (`--min-age=N`, default 60 s)
    or the `idle in transaction` ones are worth reporting to the operator.
  - right after the stop (`--after-stop`): the services' own sessions are gone,
    so every session still in a transaction is a REAL blocker.
Sessions can still connect after either check.

Prints one JSON line:
  {"mode": "after-stop", "sessions": [{"pid": 1, "state": "idle in transaction",
   "transaction_seconds": 410, "in_transaction": true}], "blocking": 1}
`state` is "unknown" when PostgreSQL hides it (a session of a role this one
cannot see in full): it is counted as in a transaction, to be safe.
"""
import json
import os
import sys


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    odoo_bin, conf, db = args[:3]
    after_stop = "--after-stop" in sys.argv
    min_age = 60
    for a in sys.argv[1:]:
        if a.startswith("--min-age="):
            min_age = int(a.split("=", 1)[1])
    sys.path.insert(0, os.path.dirname(os.path.abspath(odoo_bin)))
    import odoo
    from odoo.tools import config

    config.parse_config(["-c", conf, "-d", db])
    cr = odoo.sql_db.db_connect(db).cursor()
    try:
        cr.execute("SET TRANSACTION READ ONLY")
        cr.execute(
            """
            SELECT pid, state, xact_start IS NOT NULL,
                   COALESCE(ROUND(EXTRACT(EPOCH FROM NOW() - xact_start)), 0)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            ORDER BY xact_start NULLS LAST
            """,
            [db],
        )
        sessions, blocking = [], 0
        for pid, state, has_xact, xact_age in cr.fetchall():
            state = state or "unknown"
            in_tx = bool(has_xact) or state == "unknown"
            sessions.append(
                {
                    "pid": pid,
                    "state": state,
                    "transaction_seconds": int(xact_age),
                    "in_transaction": in_tx,
                }
            )
            if in_tx and (after_stop or state.startswith("idle in transaction") or xact_age >= min_age):
                blocking += 1
        print(
            json.dumps(
                {
                    "mode": "after-stop" if after_stop else "before-stop (advisory)",
                    "sessions": sessions,
                    "blocking": blocking,
                }
            )
        )
    finally:
        cr.rollback()
        cr.close()


if __name__ == "__main__":
    main()
