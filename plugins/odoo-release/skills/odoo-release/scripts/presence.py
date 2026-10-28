#!/usr/bin/env python3
"""How many people are at work right now, from the HR attendance of Odoo.

Runs ON THE SERVER with the Python of the Odoo virtualenv. Read-only: one
`SELECT`, in a read-only transaction, nothing is written.

The database credentials stay in the Odoo configuration file: Odoo's own
configuration loader reads it, this script never prints or returns it. No
Odoo registry is loaded (no module is loaded, so no pending upgrade can start).

  ssh <ssh> "$(printf '%q ' <python> - <odoo_dir>/<odoo_bin> <odoo_dir>/<conf> <db> [stale hours])" \
      < presence.py

Prints one JSON line:
  {"available": true, "checked_in": 12, "employees": 80, "stale_hours": 16}
or {"available": false, "reason": "..."} when hr_attendance is not installed.

"Checked in" = an attendance without check-out, started less than `stale hours`
ago (default 16): older open attendances are forgotten check-outs, not people
at their desk.
"""
import json
import os
import sys


def main():
    odoo_bin, conf, db = sys.argv[1:4]
    stale_hours = float(sys.argv[4]) if len(sys.argv) > 4 else 16.0
    sys.path.insert(0, os.path.dirname(os.path.abspath(odoo_bin)))
    import odoo
    from odoo.tools import config

    config.parse_config(["-c", conf, "-d", db])
    cr = odoo.sql_db.db_connect(db).cursor()
    try:
        cr.execute("SET TRANSACTION READ ONLY")
        cr.execute("SELECT to_regclass('hr_attendance') IS NOT NULL")
        if not cr.fetchone()[0]:
            print(json.dumps({"available": False, "reason": "hr_attendance is not installed"}))
            return
        cr.execute(
            """
            SELECT COUNT(DISTINCT employee_id) FROM hr_attendance
            WHERE check_out IS NULL
                AND check_in > (NOW() AT TIME ZONE 'UTC') - (%s * INTERVAL '1 hour')
            """,
            [stale_hours],
        )
        checked_in = cr.fetchone()[0]
        cr.execute("SELECT COUNT(*) FROM hr_employee WHERE active")
        employees = cr.fetchone()[0]
        print(
            json.dumps(
                {
                    "available": True,
                    "checked_in": checked_in,
                    "employees": employees,
                    "stale_hours": stale_hours,
                }
            )
        )
    finally:
        cr.rollback()
        cr.close()


if __name__ == "__main__":
    main()
