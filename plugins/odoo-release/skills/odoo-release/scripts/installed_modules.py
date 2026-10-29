#!/usr/bin/env python3
"""Which Odoo modules are installed, and whether any upgrade is pending.

Runs ON THE SERVER with the Python of the Odoo virtualenv. Read-only: one
`SELECT` on `ir_module_module`, in a read-only transaction. Credentials stay in
the Odoo configuration file, read by Odoo's own loader, never printed. No Odoo
module is loaded (so no pending upgrade can start).

  ssh <ssh> "$(printf '%q ' <python> - <odoo_dir>/<odoo_bin> <odoo_dir>/<conf> <db>)" \
      < installed_modules.py

Prints one JSON line:
  {"installed": ["base", ...], "pending": {"to upgrade": ["x"], "to install": []}}

Use it (1) to keep only installed modules in `-u`: Odoo's `-u` only touches the
modules in state `installed` or `to upgrade`, an unknown or uninstalled name just
logs a warning, so a release whose changed modules are all uninstalled needs no
update; and (2) after an update, where `pending` must be empty: "Modules loaded."
alone does not prove that the requested modules were updated.
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
        cr.execute("SELECT name, state FROM ir_module_module ORDER BY name")
        installed, pending = [], {}
        for name, state in cr.fetchall():
            if state == "installed":
                installed.append(name)
            elif state in ("to upgrade", "to install", "to remove"):
                pending.setdefault(state, []).append(name)
        print(json.dumps({"installed": installed, "pending": pending}))
    finally:
        cr.rollback()
        cr.close()


if __name__ == "__main__":
    main()
