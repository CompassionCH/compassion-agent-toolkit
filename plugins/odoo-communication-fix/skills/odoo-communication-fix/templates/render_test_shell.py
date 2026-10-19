"""Model: render corrected templates on real jobs without saving anything.

Run (ask the user first, test database only):
  python3 odoo-bin shell -c odoo.conf -d <TEST_DB> --no-http --log-level=error < render_test_shell.py
Everything is rolled back at the end. Fill the constants. What it checks:
  * the sender / subject inline templates (engine inline_template);
  * the body (engine qweb + post_process, like the wizards) in each language;
  * a job with SEVERAL objects (children / sponsorships of one partner): the text must
    still make sense, per-object data (a reason, a country) must not come from [:1].
"""
import re

JOB_ID = 0  # an existing job of the right config, to render single-object texts
CONFIG_ID = 0  # config of the template, to create test jobs
PARTNER_ID = 0  # a sponsor with several sponsorships
OBJECT_IDS = []  # their ids (recurring.contract or correspondence, as the config needs)
BODIES = {}  # {"en_US": "<body xml>", "fr_CH": "...", ...} the new bodies to test

T = env["mail.template"]


def render(body, job, lang, engine="qweb"):
    options = {"post_process": True} if engine == "qweb" else {}
    out = T.with_context(lang=lang)._render_template(
        body, "partner.communication.job", [job.id], engine=engine, options=options
    )[job.id]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(out))).strip()


job = env["partner.communication.job"].browse(JOB_ID)
for lang, body in BODIES.items():
    print("single", lang, "|", render(body, job, lang)[:300])

# Creating a job merges it into a pending job of the same partner and config, which
# would silently test the wrong job: disable the merge with same_job_search.
ctx = {"no_print": True, "same_job_search": [("id", "=", 0)]}
many = env["partner.communication.job"].with_context(**ctx).create(
    {"partner_id": PARTNER_ID, "config_id": CONFIG_ID, "send_mode": "digital",
     "object_ids": ",".join(map(str, OBJECT_IDS))}
)
for lang, body in BODIES.items():
    print("several", lang, "|", render(body, many.with_context(lang=lang), lang)[:400])

# Optional fields: a guard must work in both engines
print(render("<t t-out=\"'nope_field' in object._fields\"/>", job, "en_US"))
env.cr.rollback()
