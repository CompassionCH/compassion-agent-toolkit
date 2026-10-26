#!/usr/bin/env python3
"""Who else is connected to the Odoo database, and could block an update.

Runs ON THE SERVER with the Python of the Odoo virtualenv, BEFORE the services
are stopped (so it costs no downtime). Read-only: one `SELECT` on the
PostgreSQL activity views, in a read-only transaction. Credentials stay in the
Odoo configuration file, read by Odoo's own loader, never printed. No Odoo
module is loaded.

  ssh <ssh> "$(printf '%q ' <python> - <odoo_dir>/<odoo_bin> <odoo_dir>/<conf> <db>)" < sessions.py

Prints one JSON line:
  {"sessions": [{"pid": 1, "state": "idle", "idle_seconds": 120, "in_transaction": false}],
   "blocking": 0, "exclusive_locks": 0}
`blocking` counts the sessions that are `idle in transaction` or hold an
exclusive-type lock: they can make a schema change wait. Plain `idle` sessions
(for example a forgotten `odoo-bin shell`) hold nothing and are harmless.
"""
import json
import os
import sys


def main():
    odoo_bin, conf, db = sys.argv[1:4]
    sys.path.insert(0, os.path.dirname(os.path.abspath(odoo_bin)))
    import odoo
    from odoo.tools import config

    config.parse_config(["-c", conf, "-d", db])
    cr = odoo.sql_db.db_connect(db).cursor()
    try:
        cr.execute("SET TRANSACTION READ ONLY")
        cr.execute(
            """
            SELECT a.pid, a.state,
                   COALESCE(ROUND(EXTRACT(EPOCH FROM NOW() - a.state_change)), 0),
                   EXISTS (
                       SELECT 1 FROM pg_locks l
                       WHERE l.pid = a.pid AND l.granted
                         AND l.mode IN ('AccessExclusiveLock', 'ExclusiveLock',
                                        'ShareRowExclusiveLock', 'ShareUpdateExclusiveLock')
                   )
            FROM pg_stat_activity a
            WHERE a.datname = %s AND a.pid <> pg_backend_pid()
            ORDER BY a.state_change
            """,
            [db],
        )
        sessions, blocking, locks = [], 0, 0
        for pid, state, idle, excl in cr.fetchall():
            in_tx = state.startswith("idle in transaction") or state == "active"
            sessions.append(
                {"pid": pid, "state": state, "idle_seconds": int(idle), "in_transaction": in_tx}
            )
            locks += 1 if excl else 0
            blocking += 1 if (state.startswith("idle in transaction") or excl) else 0
        print(json.dumps({"sessions": sessions, "blocking": blocking, "exclusive_locks": locks}))
    finally:
        cr.rollback()
        cr.close()


if __name__ == "__main__":
    main()
