"""Model: reload corrected mail templates from the data files of the module.

Copy to <module>/migrations/<version>/post-migration.py (a POST migration: the .po files
are loaded after it, see "Why" below), fill the constants and raise the manifest version
above ir_module_module.latest_version of the target databases.

Why not just clear the noupdate flag?
  The data files are <odoo noupdate="1">. In update mode Odoo skips an existing record
  of such a file before reading its fields (odoo/tools/convert.py, _tag_record); the
  noupdate flag of ir_model_data is a second, separate check. Clearing the flag in the
  database therefore reloads nothing. Loading the records in mode "init" does.
Why not openupgrade.load_data()?
  It loads the whole file and cannot select records: the templates of the file that
  were not corrected would be reset to the code version too. This helper loads only the
  listed records, from the data file itself (no copy of the data in the migrations).
Why drop the translations first?
  When the structure of the English text changes, Odoo keeps the old translated values
  and the .po file (loaded afterwards, without overwrite) does not replace them.
  Dropping the non-English values of body_html and subject lets the .po files fill them.
"""
from io import BytesIO

from lxml import etree
from openupgradelib import openupgrade

from odoo import tools

MODULE = "<module_name>"
# Only run for databases where this module is installed. Use it when the code is shared
# with another organisation that has its own texts (Compassion Switzerland / Nordic).
# None = always run. 'to upgrade' is needed: dependents of the updated module are
# 'to upgrade', not 'installed', while the migration runs.
REQUIRED_MODULE = None  # e.g. "partner_communication_switzerland"
# Templates corrected in <TICKET>, by data file
FIXED_TEMPLATES = {
    "data/<file>.xml": ["xmlid_of_template_1", "xmlid_of_template_2"],
}


@openupgrade.migrate()
def migrate(env, version):
    """Reload the texts (subject, body and sender fields) of the corrected templates."""
    if REQUIRED_MODULE:
        env.cr.execute(
            "SELECT 1 FROM ir_module_module "
            "WHERE name = %s AND state IN ('installed', 'to upgrade')",
            (REQUIRED_MODULE,),
        )
        if not env.cr.fetchone():
            return
    for filename, xmlids in FIXED_TEMPLATES.items():
        _reload_records(env, filename, xmlids)


def _reload_records(env, filename, xmlids):
    """Load only the given records of a data file, the other records of the file
    must keep their database values."""
    with tools.file_open(f"{MODULE}/{filename}", "rb") as fp:
        source = etree.parse(fp).getroot()
    selection = etree.Element("odoo", noupdate="1")
    selection.extend(r for r in source.iter("record") if r.get("id") in xmlids)
    assert len(selection) == len(xmlids), f"Missing records in {filename}"
    # Drop the translated values, they are loaded again from the .po files
    env.cr.execute(
        """
        UPDATE mail_template t
        SET body_html = jsonb_build_object('en_US', t.body_html->>'en_US'),
            subject = jsonb_build_object('en_US', t.subject->>'en_US')
        FROM ir_model_data d
        WHERE d.model = 'mail.template' AND d.res_id = t.id
          AND d.module = %s AND d.name IN %s
        """,
        (MODULE, tuple(xmlids)),
    )
    stream = BytesIO(etree.tostring(selection))
    stream.name = filename
    # Mode init loads the records even if they exist and the file is noupdate
    tools.convert_xml_import(env, MODULE, stream, mode="init")
