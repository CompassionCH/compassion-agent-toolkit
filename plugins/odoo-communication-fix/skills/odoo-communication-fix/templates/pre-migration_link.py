"""Model: link a template that only exists in the databases to its new xmlid.

Use when a corrected template had no source (xmlid ``__import__.NN``) and you created
its record in the data files. Copy to <module>/migrations/<version>/pre-migration.py
(PRE: the link must exist before the data files load, otherwise the update creates a
duplicate record). The texts are reloaded by post-migration_reload.py.
"""
from openupgradelib import openupgrade

XMLID_MODULE = "<module_name>"
XMLID_NAME = "<new_xmlid>"
TEMPLATE_NAME = "<English name of the existing template>"
# Same meaning as in post-migration_reload.py (None = always run)
REQUIRED_MODULE = None


@openupgrade.migrate()
def migrate(env, version):
    if REQUIRED_MODULE:
        env.cr.execute(
            "SELECT 1 FROM ir_module_module "
            "WHERE name = %s AND state IN ('installed', 'to upgrade')",
            (REQUIRED_MODULE,),
        )
        if not env.cr.fetchone():
            return
    _link_template(env)


def _link_template(env):
    if env.ref(f"{XMLID_MODULE}.{XMLID_NAME}", raise_if_not_found=False):
        return
    # Prefer the template a communication config already uses
    env.cr.execute(
        """
        SELECT t.id
        FROM mail_template t
        JOIN ir_model m ON m.id = t.model_id
        LEFT JOIN partner_communication_config c ON c.email_template_id = t.id
        WHERE m.model = 'partner.communication.job'
          AND t.name->>'en_US' = %s
        ORDER BY (c.id IS NULL), t.id
        LIMIT 1
        """,
        (TEMPLATE_NAME,),
    )
    row = env.cr.fetchone()
    if row:
        openupgrade.add_xmlid(
            env.cr, XMLID_MODULE, XMLID_NAME, "mail.template", row[0], noupdate=True
        )
