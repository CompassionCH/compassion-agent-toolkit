#!/usr/bin/env python3
"""PII sanitizer for odoo_ticket.py output.

Masks personal data before it is printed (i.e. before Claude sees it). First
names are kept; last names, emails, phones, IBANs, AHV numbers, IPs and street
addresses become tokens like {{NAME_3}}. Tokens are numbered per run and never
stored: the same person has the same token within one output, but {{NAME_1}}
in two outputs are unrelated, so people can't be linked across tickets.

Name detection (Presidio/spaCy, DE/FR/IT/EN, language guessed per line) catches
people not linked to the ticket. It lives in its own venv, installed once with
`odoo_ticket.py install-ner`; both scripts switch into it on their own.

Dry-run: run in your OWN terminal (not via `!` in Claude Code, which would
send the "before" column to Claude):
    python3 sanitizer.py --dry-run T3512
    python3 sanitizer.py --dry-run T3512 --env stage

Sanitized output only (what Claude would get):
    python3 sanitizer.py T3512

Over-masked words (titles, products, common nouns) go in NER_IGNORE.
"""
import argparse
import contextlib
import io
import os
import re
import sys
import xmlrpc.client
from collections import Counter

W = r"[\wÀ-ÿ'’-]"  # word chars incl. accents

PATTERNS = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,3})?\b")),
    ("AHV", re.compile(r"\b756[.\s]?\d{4}[.\s]?\d{4}[.\s]?\d{2}\b")),
    ("PHONE", re.compile(
        r"(?:\+|\b00)\d{2}[\s./-]?\(?0?\)?\d{1,3}(?:[\s./-]?\d{2,4}){2,4}\b"
        r"|\b0\d{2}[\s./-]?\d{3}[\s./-]?\d{2}[\s./-]?\d{2}\b"
        # other local groupings: "079 11 50 990", "08-23 62 14"
        r"|(?<![\d.:-])0\d{1,3}[ -]\d{2,3}(?:[ ]\d{2,3}){1,3}\b")),
    ("IP", re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")),
    ("ADDRESS", re.compile(
        rf"(?i)\b(?:rue|avenue|av\.|chemin|ch\.|route|rte|via|viale|piazza|place|"
        rf"impasse|all[ée]e)\s[^\n,\d]{{1,40}}\d+[a-z]?\b"
        rf"|\b{W}+(?:strasse|straße|str\.|weg|gasse|platz|rain|halde)\s?\d+[a-z]?\b")),
]


NER_MODELS = {
    "en": "en_core_web_md",
    "de": "de_core_news_md",
    "fr": "fr_core_news_md",
    "it": "it_core_news_md",
}
NER_MIN_SCORE = 0.6
CAP_RUN = re.compile(r"[A-ZÀ-Þ][\wÀ-ÿ'’-]*(?:[ \t]+[A-ZÀ-Þ][\wÀ-ÿ'’-]*)*")
# Words the NER models like to mistake for people in our tickets.
NER_IGNORE = {
    "odoo", "compassion", "gmc", "mycompassion", "postfinance", "twint", "mandrill",
    "mailchimp", "wordpress", "claude", "github", "sponsor", "sponsorship", "pate",
    "patin", "parrain", "marraine", "padrino", "madrina",
    "frau", "herr", "mrs", "mr", "mrs.", "mr.", "ms", "ms.", "dr", "dr.",
    "madame", "monsieur", "mme", "m.", "mlle", "signora", "signor", "signore",
    "sig.", "sig.ra",
    "firefox", "chrome", "safari", "edge", "android", "iphone", "ipad", "ios",
    "windows", "outlook", "gmail", "excel", "word", "pdf", "zoom", "teams", "slack",
    "rechnung", "zahlung", "spende", "brief", "facture", "paiement", "lettre",
    "fattura", "pagamento", "lettera",
    # ticket field labels and template words
    "stage", "test", "code", "task", "ticket", "partner", "assignee", "priority",
    "step", "option", "details", "support", "team", "finance",
    # greetings / mail headers
    "hello", "hi", "hey", "dear", "hallo", "liebe", "lieber", "bonjour", "salut",
    "cher", "chère", "ciao", "buongiorno", "caro", "cara", "hej", "skickat",
    "från", "till", "kopia", "ämne", "von", "an", "betreff", "de", "à", "objet",
    # places, languages, faith
    "switzerland", "suisse", "schweiz", "svizzera", "sweden", "sverige", "nordic",
    "english", "french", "german", "italian", "deutsch", "français", "italiano",
    "jesus", "christ", "christus", "jésus", "gesù", "god", "gott", "dieu", "dio",
}


class Sanitizer:
    def __init__(self, ner=False):
        self.tokens = {}  # (kind, real lower) -> token, this run only
        self.counts = Counter()  # tokens issued per kind
        self.known = []  # (compiled regex, kind, real value) for exact-value masking
        self.first_names = set()
        self.stats = Counter()
        self.analyzer = self._load_ner() if ner else None

    def token(self, kind, real):
        key = (kind, real.strip().lower())
        if key not in self.tokens:
            self.counts[kind] += 1
            self.tokens[key] = "{{%s_%d}}" % (kind, self.counts[kind])
        self.stats[kind] += 1
        return self.tokens[key]

    # -- known people (exact matches, the reliable part) ----------------------

    def add_person(self, name=None, firstname=None, lastname=None, **values):
        """Register a partner. Last name is masked, first name kept; any extra
        values (email=, phone=, street=, …) are masked wherever they appear."""
        if firstname:
            self.first_names.update(p.lower() for p in firstname.split())
        if lastname:
            self._add_known("NAME", lastname)
        elif name and not firstname:
            # No firstname/lastname split (e.g. a company): mask the whole name.
            self._add_known("NAME", name)
        for kind, val in values.items():
            if val and isinstance(val, str) and len(val.strip()) > 2:
                self._add_known(kind.upper(), val)

    def _add_known(self, kind, real):
        real = real.strip()
        # Bot/test accounts ("Claude Code", "… Test") have common words as
        # last names; masking those everywhere would wreck the ticket text.
        if len(real) < 2 or (kind == "NAME" and real.lower() in NER_IGNORE):
            return
        rx = re.compile(rf"(?<!{W}){re.escape(real)}(?!{W})", re.IGNORECASE)
        self.known.append((rx, kind, real))
        # Longest first so "Müller-Schmid" wins over "Müller".
        self.known.sort(key=lambda k: -len(k[2]))

    # -- sanitize -------------------------------------------------------------

    def sanitize(self, text):
        # "Anna  Müller" (double space) slips past NER; collapse between letters
        # only, so indentation and code alignment stay intact.
        text = re.sub(r"(?<=[^\W\d_]) {2,}(?=[^\W\d_])", " ", text)
        for rx, kind, real in self.known:
            text = rx.sub(lambda m, k=kind, r=real: self.token(k, r), text)
        for kind, rx in PATTERNS:
            text = rx.sub(lambda m, k=kind: self.token(k, m.group(0)), text)
        if self.analyzer:
            text = self._sanitize_ner(text)
            # A surname NER caught once must be masked everywhere it occurs.
            for rx, kind, real in self.known:
                text = rx.sub(lambda m, k=kind, r=real: self.token(k, r), text)
        return text

    # -- optional NER layer ---------------------------------------------------

    def _load_ner(self):
        try:
            import spacy.util
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
        except ImportError:
            print("[sanitizer] name detection not installed (odoo_ticket.py install-ner)",
                  file=sys.stderr)
            return None
        models = [{"lang_code": lang, "model_name": m} for lang, m in NER_MODELS.items()
                  if spacy.util.is_package(m)]
        if not models:
            print("[sanitizer] no spaCy models installed", file=sys.stderr)
            return None
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy", "models": models})
        self.ner_langs = [m["lang_code"] for m in models]
        self.stopwords = {lang: spacy.util.get_lang_class(lang).Defaults.stop_words
                          for lang in self.ner_langs}
        return AnalyzerEngine(nlp_engine=provider.create_engine(),
                              supported_languages=self.ner_langs)

    def _guess_lang(self, line):
        # Tickets mix DE/FR/IT/EN line by line; a model run on the wrong
        # language tags whole sentences as names.
        words = re.findall(rf"{W}+", line.lower())
        scores = {lang: sum(w in sw for w in words) for lang, sw in self.stopwords.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] else self.ner_langs[0]

    def _ner_spans(self, text):
        spans, offset = [], 0
        for line in text.split("\n"):
            if line.strip():
                hits = self.analyzer.analyze(text=line, language=self._guess_lang(line),
                                             entities=["PERSON"],
                                             score_threshold=NER_MIN_SCORE)
                for h in hits:
                    # Names are capitalized: keep only runs of capitalized words,
                    # dropping verbs/markdown the model swallowed into the span.
                    for m in CAP_RUN.finditer(line, h.start, h.end):
                        spans.append((offset + m.start(), offset + m.end()))
            offset += len(line) + 1
        return sorted(set(spans))

    def _sanitize_ner(self, text):
        for start, end in reversed(self._ner_spans(text)):
            span = text[start:end]
            if re.search(r"[{}@\d\n]", span):
                continue
            # Drop titles/product names at either edge ("Frau Petra Huber").
            pos = [m for m in re.finditer(r"\S+", span) if m.group().lower() not in NER_IGNORE]
            if not pos:
                continue
            start, end = start + pos[0].start(), start + pos[-1].end()
            span = text[start:end]
            words = span.split()
            # Keep a leading first name; a lone unknown word may be a surname.
            if len(words) > 1 or words[0].lower() in self.first_names:
                keep, rest = words[0], " ".join(words[1:])
                new = keep + (" " + self.token("NAME", rest) if rest else "")
                for w in words[1:]:
                    self._add_known("NAME", w)
            else:
                # Not propagated: lone capitalized words are often false hits
                # ("Stage", "Test") and would get masked everywhere.
                new = self.token("NAME", span)
            text = text[:start] + new + text[end:]
        return text


# -- Odoo glue ----------------------------------------------------------------

PARTNER_FIELDS = ["name", "firstname", "lastname", "email", "phone", "mobile",
                  "street", "street2", "city", "ref", "is_company"]


def register_ticket_people(san, odoo, model=None, rec_id=None):
    """Feed everyone linked to the ticket into the sanitizer: customer,
    assignee, followers, message authors and all visible staff. Without a
    ticket, only staff."""
    rec = {}
    if model:
        task_fields = odoo.execute(model, "fields_get", [], {"attributes": []})
        want = [f for f in ("partner_id", "message_follower_ids", "message_ids")
                if f in task_fields]
        rec = odoo.execute(model, "read", [rec_id], {"fields": want})[0]

    # Many2one display names come back even when the record itself is hidden
    # from us by record rules, so they are the fallback for unreadable people.
    m2o = [rec.get("partner_id")]
    if rec.get("message_follower_ids"):
        m2o += [f["partner_id"] for f in odoo.execute(
            "mail.followers", "read", rec["message_follower_ids"], {"fields": ["partner_id"]})]
    if rec.get("message_ids"):
        m2o += [m["author_id"] for m in odoo.execute(
            "mail.message", "read", rec["message_ids"], {"fields": ["author_id"]})]
    staff = odoo.execute("res.users", "search_read", [["share", "=", False]],
                         {"fields": ["partner_id"]})
    m2o += [u["partner_id"] for u in staff]
    m2o = [v for v in m2o if v]
    # Users this account may not read still show up by name on their tasks;
    # this also covers the ticket's own assignees.
    groups = odoo.execute("project.task", "read_group", [["user_ids", "!=", False]],
                          ["user_ids"], ["user_ids"], {"context": {"active_test": False}})
    for g in groups:
        first, _, last = g["user_ids"][1].rsplit(", ", 1)[-1].partition(" ")
        if last:
            san.add_person(firstname=first, lastname=last)

    pids = {v[0] for v in m2o}
    pfields = odoo.execute("res.partner", "fields_get", [], {"attributes": []})
    fields = [f for f in PARTNER_FIELDS if f in pfields]
    seen = set()
    for p in _read_partners(odoo, list(pids), fields):
        seen.add(p.pop("id"))
        if p.pop("is_company", False):
            continue
        p = {k: v for k, v in p.items() if v}
        san.add_person(
            name=p.pop("name", None), firstname=p.pop("firstname", None),
            lastname=p.pop("lastname", None), **p)

    for v in m2o:
        if v[0] not in seen:
            # "Company, First Last" -> assume "First Last", keep the first word.
            person = v[1].rsplit(", ", 1)[-1]
            first, _, last = person.partition(" ")
            if last:
                san.add_person(firstname=first, lastname=last)


def _read_partners(odoo, ids, fields):
    """Batch read; on an access error fall back to one-by-one, skipping the
    records we may not see."""
    try:
        recs = odoo.execute("res.partner", "read", ids, {"fields": fields})
    except xmlrpc.client.Fault:
        recs = []
        for pid in ids:
            try:
                recs += odoo.execute("res.partner", "read", [pid], {"fields": fields})
            except xmlrpc.client.Fault:
                pass
    return recs


class SanitizingStream:
    """Wraps stdout/stderr: every line is sanitized before it is written."""

    def __init__(self, san, raw):
        self.san, self.raw, self.buf = san, raw, ""

    def write(self, s):
        self.buf += s
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            self.raw.write(self.san.sanitize(line) + "\n")
        return len(s)

    def flush(self):
        # Partial line (e.g. an input() prompt).
        if self.buf:
            self.raw.write(self.san.sanitize(self.buf))
            self.buf = ""
        self.raw.flush()

    def __getattr__(self, name):
        return getattr(self.raw, name)


def protect(san):
    """Route all further output of this process through the sanitizer."""
    sys.stdout = SanitizingStream(san, sys.stdout)
    sys.stderr = SanitizingStream(san, sys.stderr)


def fetch_ticket_text(raw_id, env):
    import odoo_ticket as ot
    odoo = ot.Odoo(ot.load_config(env))
    model, rec_id = ot.find_ticket(odoo, raw_id)
    if not model:
        sys.exit(f"No ticket found for {raw_id!r}")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ot.fetch(odoo, raw_id, model)
    return buf.getvalue(), (odoo, model, rec_id)


# -- dry-run output -----------------------------------------------------------

RED, GREEN, DIM, RESET = "\033[31m", "\033[32m", "\033[2m", "\033[0m"


def print_dry_run(before, after, san):
    changed = 0
    for b, a in zip(before.splitlines(), after.splitlines()):
        if b == a:
            print(f"{DIM}  {b}{RESET}")
        else:
            changed += 1
            print(f"{RED}- {b}{RESET}")
            print(f"{GREEN}+ {a}{RESET}")
    print("\n--- summary ---")
    print(f"lines changed: {changed}")
    for kind, n in sorted(san.stats.items()):
        print(f"  {kind:8} {n} replacement(s)")
    print(f"{DIM}Check the green lines for anything still identifying.{RESET}")


def main():
    import odoo_ticket as ot

    venv_py = os.path.join(ot.NER_VENV, "bin", "python")
    if os.path.exists(venv_py) and os.path.realpath(sys.prefix) != os.path.realpath(ot.NER_VENV):
        os.execv(venv_py, [venv_py, os.path.abspath(__file__)] + sys.argv[1:])
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticket", nargs="?", help="ticket code (omit to read stdin)")
    ap.add_argument("--env", default="prod")
    ap.add_argument("--dry-run", action="store_true", help="show before/after")
    ap.add_argument("--regex-only", action="store_true",
                    help="skip name detection (Presidio/spaCy)")
    args = ap.parse_args()

    san = Sanitizer(ner=not args.regex_only)
    if args.ticket:
        text, (odoo, model, rec_id) = fetch_ticket_text(args.ticket, args.env)
        register_ticket_people(san, odoo, model, rec_id)
    else:
        text = sys.stdin.read()

    out = san.sanitize(text)
    if args.dry_run:
        print_dry_run(text, out, san)
    else:
        print(out)


if __name__ == "__main__":
    main()
