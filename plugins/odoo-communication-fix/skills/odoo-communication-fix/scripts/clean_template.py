#!/usr/bin/env python3
"""Automatic cleanup of a communication (mail.template) QWeb body.

Usage: clean_template.py FILE --lang de_DE [--check]

Applies the rules that never need a decision from the owner:
  * remove the outer <div class="communication-text"> wrapper and any <div>/<span>
    that only wraps the t-set lines; t-set lines live directly under <body>
  * remove inline style attributes, except the ones that draw a button
  * <p><t t-out="x"></t></p>  ->  <p t-out="x"/>
  * signature: only for send_mode == 'digital', regular signature, in a <p t-out/>
  * website links: /de_DE/ -> /de/, /fr_CH/ -> /fr/, /it_IT/ -> /it/
  * remove the t-set variables that are never used in an expression (iterative)

Prints what it did. With --check nothing is written. The file is validated as XML.
"""
import argparse
import html
import re
import sys
import xml.dom.minidom as minidom

URL_CODES = {"de_DE": "de", "fr_CH": "fr", "it_IT": "it", "en_US": None}
TSET_RE = re.compile(r'[ \t]*<t\s+t-set="(\w+)"[^>]*?/>[ \t]*\n?', re.S)
ATTR_RE = re.compile(r'\bt-(?!set\b)[\w-]+="([^"]*)"')
SIDE_EFFECT_RE = re.compile(r"\.(append|extend|update|add|remove|pop|sort|insert)\(")
URLS_RE = re.compile(
    r'<t t-set="urls" t-value="\[\]"/>\s*'
    r'<t t-foreach="(?P<seq>[^"]*)" t-as="\w+">\s*'
    r'<t t-if="[^"]*">\s*<t t-set="\w+"[^>]*/>\s*</t>\s*</t>'
)
STRING_RE = re.compile(r"'[^'\n]*'|\"[^\"\n]*\"")


def remove_wrappers(s, log):
    m = re.search(r'<div class="communication-text"[^>]*>', s)
    if m:
        s = s[: m.start()] + s[m.end():]
        k = s.rindex("</div>")
        s = s[:k] + s[k + len("</div>"):]
        log.append("removed the communication-text wrapper")
    m = re.search(r"(<body>\s*)<(div|span)>", s)
    if m:
        tag = m.group(2)
        start = m.end()
        end = s.index("</%s>" % tag, start)
        block = s[start:end]
        if "<div" not in block and not re.sub(r"<[^>]*>", "", block).strip():
            s = s[: m.end() - len(tag) - 2] + block + s[end + len(tag) + 3:]
            log.append("removed the <%s> around the t-set lines" % tag)
    return s


def remove_styles(s, log):
    count = 0

    def keep(tag, style, rest):
        if tag == "a" and ("background-color" in style or "border-radius" in style):
            return True
        if tag == "div" and "text-align" in style and "border-radius" in rest[:600]:
            return True
        return False

    def repl(m):
        nonlocal count
        tag, style = m.group(1), html.unescape(m.group(3))
        if keep(tag, style, s[m.end():]):
            return m.group(0)
        count += 1
        return m.group(0).replace(m.group(2), "")

    # <tag ... style="..." ...>
    pat = re.compile(r'<(\w+)\b[^>]*?(\s+(?:t-att-)?style="([^"]*)")[^>]*>')
    s = pat.sub(repl, s)
    if count:
        log.append("removed %d style attribute(s) (button styles kept)" % count)
    return s


def shorthand_p(s, log):
    pat = re.compile(r'<p>\s*<t t-out="([^"]*)"\s*(?:/>|>\s*</t>)\s*</p>')
    s, n = pat.subn(lambda m: '<p t-out="%s"/>' % m.group(1), s)
    if n:
        log.append('%d <p t-out="..."/> shorthand' % n)
    return s


def signature(s, log):
    s = s.replace(".short_signature", ".signature")
    pat = re.compile(
        r'<t t-if="[^"]*">\s*(?:<p>\s*)?<t t-out="(object\.[^"]*signature)\s*"\s*'
        r"(?:/>|>\s*</t>)\s*(?:</p>)?\s*</t>"
    )
    new = (
        "<t t-if=\"object.send_mode == 'digital'\">\n"
        '        <p t-out="\\1"/>\n    </t>'
    )
    s, n = pat.subn(new, s)
    if n:
        log.append("signature only for send_mode == 'digital' (%d)" % n)
    return s


def url_codes(s, lang, log):
    code = URL_CODES.get(lang)
    if lang == "en_US" or not code:
        return s
    n = s.count("/%s/" % lang) + s.count("/%s\"" % lang)
    s = s.replace("/%s/" % lang, "/%s/" % code).replace('/%s"' % lang, '/%s"' % code)
    if n:
        log.append("website link codes /%s/ -> /%s/ (%d)" % (lang, code, n))
    return s


def expression_text(s, exclude_span=None):
    """Concatenate all t-* attribute values, without string literals."""
    out = []
    for m in ATTR_RE.finditer(s):
        if exclude_span and exclude_span[0] <= m.start() < exclude_span[1]:
            continue
        out.append(STRING_RE.sub("''", html.unescape(m.group(1))))
    return "\n".join(out)


def fix_urls(s, log):
    """The urls list built by t-foreach + append is lost out of its scope (NameError)."""
    s, n = URLS_RE.subn(
        lambda m: '<t t-set="urls" t-value="list(dict.fromkeys(%s))"/>' % m.group("seq"),
        s,
    )
    if n:
        log.append("urls list built in one expression (dict.fromkeys)")
    return s


def prune(s, log):
    removed = []
    while True:
        for m in TSET_RE.finditer(s):
            name = m.group(1)
            if SIDE_EFFECT_RE.search(html.unescape(m.group(0))):
                continue  # t-set used for its side effect (e.g. urls.append)
            used = re.search(
                r"(?<![\w.])%s\b" % name, expression_text(s, (m.start(), m.end()))
            )
            if not used:
                s = s[: m.start()] + s[m.end():]
                removed.append(name)
                break
        else:
            break
    if removed:
        log.append("removed unused t-set: %s" % ", ".join(removed))
    # empty conditional blocks left behind
    empty = re.compile(r'[ \t]*<t t-if="[^"]*">\s*</t>\n?')
    s, n = empty.subn("", s)
    if n:
        log.append("removed %d empty t-if block(s)" % n)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--lang", required=True, choices=sorted(URL_CODES))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    s = open(a.file, encoding="utf-8").read()
    log = []
    for step in (remove_wrappers, remove_styles, shorthand_p, signature, fix_urls):
        s = step(s, log)
    s = url_codes(s, a.lang, log)
    s = prune(s, log)
    s = re.sub(r"(t-value=\"[^\"]*?)\s+\"", r"\1\"", s)
    minidom.parseString(s)  # raises if the result is not valid XML
    print("\n".join(log) if log else "nothing to clean")
    if not a.check:
        open(a.file, "w", encoding="utf-8").write(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
