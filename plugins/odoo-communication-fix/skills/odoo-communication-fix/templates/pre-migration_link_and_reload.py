from openupgradelib import openupgrade

XMLID_MODULE = "partner_communication_compassion"
XMLID_NAME = "final_letter"
TEMPLATE_NAME = "B2S Final Letter"
# Templates corrected in T3527: the data files are noupdate, reload them from the files
FIXED_TEMPLATES = [
    "new_letter",
    XMLID_NAME,
    "email_child_planned_exit",
    "email_child_unplanned_exit",
]


@openupgrade.migrate()
def migrate(env, version):
    """The B2S Final Letter e-mail only existed in the databases (imported, without
    xmlid) while the config pointed to the New letter template in the data files.
    The template is now declared in the data files as ``final_letter``: link the
    existing record to this xmlid, otherwise the update would create a duplicate.
    The corrected templates are then flagged as updatable so that the update of the
    data files reloads their texts (subject, body and sender fields).
    """
    _link_final_letter(env)
    # Force the reload of the corrected templates by the update of the data files
    openupgrade.set_xml_ids_noupdate_value(env, XMLID_MODULE, FIXED_TEMPLATES, False)


def _link_final_letter(env):
    if env.ref(f"{XMLID_MODULE}.{XMLID_NAME}", raise_if_not_found=False):
        return
    # Prefer the template the final letter config already uses
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
            env.cr,
            XMLID_MODULE,
            XMLID_NAME,
            "mail.template",
            row[0],
            noupdate=True,
        )
