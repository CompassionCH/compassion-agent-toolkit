from openupgradelib import openupgrade

# Templates corrected in <TICKET>: the data files are noupdate, reload them from the files
FIXED_TEMPLATES = [
    "xmlid_of_template_1",
    "xmlid_of_template_2",
]


@openupgrade.migrate()
def migrate(env, version):
    """Flag the corrected templates as updatable so that the update of the data files
    reloads their texts (subject, body and sender fields)."""
    openupgrade.set_xml_ids_noupdate_value(
        env, "<module_name>", FIXED_TEMPLATES, False
    )
