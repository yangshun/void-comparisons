#!/usr/bin/env python3
"""Build the single-page comparison site from the Markdown deliverables."""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inventory_view import inventory_view  # noqa: E402

HERE = Path(__file__).resolve().parent
# usage: python3 tools/build.py [ROOT] [TEMPLATE] [OUT]; defaults build ../index.html from the Markdown next to tools/
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent
TEMPLATE = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "template.html"
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "index.html"

AREAS = [
    ("01-routing", "routing", "Routing"),
    ("02-rendering", "rendering", "Rendering modes"),
    ("03-data-loading", "data-loading", "Data loading"),
    ("04-mutations", "mutations", "Mutations"),
    ("05-caching", "caching", "Caching & revalidation"),
    ("06-server-api", "server-api", "Server & API"),
    ("07-loading-error", "loading-error", "Loading & error states"),
    ("08-type-safety", "type-safety", "Type safety"),
    ("09-metadata-seo", "metadata-seo", "Metadata & SEO"),
    ("10-assets", "assets", "Images, fonts & scripts"),
    ("11-styling", "styling", "CSS & styling"),
    ("12-markdown", "markdown", "Markdown & content"),
    ("13-build-deploy", "build-deploy", "Build output & deployment"),
    ("14-dev-tooling", "dev-tooling", "Dev tooling & observability"),
]
SOURCES = [
    ("void", "Void 1.5"),
    ("nextjs", "Next.js 16.4"),
    ("react-router", "React Router 8"),
    ("tanstack-start", "TanStack Start 1.169"),
    ("nuxt", "Nuxt 5 (pre-release)"),
    ("sveltekit", "SvelteKit 3"),
    ("solidstart", "SolidStart 2.0"),
    ("astro", "Astro 7.4"),
]
FILE_TO_VIEW = {f"{f}.md": slug for f, slug, _ in AREAS}
FILE_TO_VIEW.update({"bugs.md": "bugs", "quick-wins.md": "quick-wins", "README.md": "overview"})


def pandoc(md: str, prefix: str) -> str:
    res = subprocess.run(
        ["pandoc", "-f", "gfm", "-t", "html5", "--columns=100000", f"--id-prefix={prefix}-"],
        input=md.encode(), capture_output=True, check=True,
    )
    return res.stdout.decode()


PREV_RE = re.compile(r"(Table stakes|Common|Differentiator)( \((?:\d|\d–\d)[^)<]*\))")
PREV_CLASS = {"Table stakes": "ts", "Common": "cm", "Differentiator": "df"}

MARKER_INFO = {
    "[exp]": ("exp", "exp", "experimental, unstable or canary"),
    "[CC]": ("cc", "CC", "Next.js with Cache Components on"),
    "[prev]": ("prev", "prev", "Next.js pre-16 caching model"),
    "[N5]": ("n5", "N5", "new or changed in Nuxt 5"),
    "(src)": ("src", "src", "found in Void's source, not its docs"),
    "(unverified)": ("unv", "unverified", "not confirmed in docs or source"),
}
MARKER_RE = re.compile("|".join(re.escape(k) for k in MARKER_INFO))


def badge(tok):
    cls, label, title = MARKER_INFO[tok]
    return f'<span class="mk mk-{cls}" title="{html.escape(title)}">{label}</span>'


def markers(html_text: str) -> str:
    """Turn marker tokens into badges in text, never inside tags or code."""
    parts = re.split(r"(<code>.*?</code>|<[^>]+>)", html_text, flags=re.S)
    for i in range(0, len(parts), 2):
        parts[i] = MARKER_RE.sub(lambda m: badge(m.group(0)), parts[i])
    return "".join(parts)


VER_RE = re.compile(r"^(?P<name>.+?) (?P<ver>\d[^\s(]*(?: pre-release)?)(?: \((?P<det>[^)]*)\))?$")


def legend_html(rows):
    out = ['<dl class="legend" aria-label="How to read this page">']
    for key, val in rows:
        if key == "Versions":
            items = []
            for v in val.split(" · "):
                m = VER_RE.match(v.strip())
                name, ver, det = (m.group("name"), m.group("ver"), m.group("det")) if m else (v, "", None)
                cls = ' class="is-void"' if name == "Void" else ""
                items.append(f'<li{cls}><strong>{html.escape(name)}</strong> {html.escape(ver)}'
                             + (f' <span>{html.escape(det)}</span>' if det else "") + "</li>")
            dd = f'<ul class="legend-versions">{"".join(items)}</ul>'
        elif key == "Short names":
            items = []
            for v in val.split(" · "):
                short, _, full = v.partition(" = ")
                items.append(f'<li><b>{html.escape(short)}</b> {html.escape(full)}</li>')
            dd = f'<ul class="legend-inline">{"".join(items)}</ul>'
        elif key == "Markers":
            items = []
            for v in val.split(" · "):
                tok, _, meaning = v.partition(" ")
                items.append(f'<li>{badge(tok)}<span>{html.escape(meaning)}</span></li>')
            dd = f'<ul class="legend-markers">{"".join(items)}</ul>'
        else:
            dd = f"<p>{inline_md(val)}</p>"
        out.append(f'<div class="legend-row"><dt>{html.escape(key)}</dt><dd>{dd}</dd></div>')
    out.append("</dl>")
    return "".join(out)


def split_legend(md: str):
    """Return (md without the legend block, [(key, value)]) for an area file."""
    lines = md.split("\n")
    first_h2 = next(i for i, l in enumerate(lines) if l.startswith("## "))
    rows = []
    for l in lines[1:first_h2]:
        m = re.match(r"^\*\*(.+?):\*\* (.*)$", l.strip())
        if m:
            rows.append((m.group(1), m.group(2)))
    return "\n".join([lines[0], ""] + lines[first_h2:]), rows


def post(html_text: str) -> str:
    # wrap tables so only they scroll sideways
    html_text = html_text.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    # highlight Void rows (first cell starts with Void)
    html_text = re.sub(r'<tr(?: class="(?:odd|even)")?>(\s*<td[^>]*>\s*(?:<strong>)?Void\b)', r'<tr class="void-row">\1', html_text)
    html_text = markers(html_text)
    # prevalence chips
    html_text = PREV_RE.sub(lambda m: f'<span class="pv pv-{PREV_CLASS[m.group(1)]}">{m.group(1)}{m.group(2)}</span>', html_text)
    # cross-links to other area files become in-page views
    def relink(m):
        target = m.group(1).split("/")[-1]
        if target in FILE_TO_VIEW:
            return f'href="#{FILE_TO_VIEW[target]}"'
        if m.group(1).rstrip("/") == "inventories":
            return 'href="#src-void"'
        if m.group(1).rstrip("/") == "areas":
            return 'href="#routing"'
        return m.group(0)
    html_text = re.sub(r'href="((?:\.\./)?(?:areas/|inventories/)?[A-Za-z0-9-]*(?:\.md)?/?)"', relink, html_text)
    return html_text


STATUS_LABEL = {"missing": "Missing", "partial": "Partial", "none": "None"}


def gap_callouts(html_text: str) -> str:
    """Wrap each "Void gap:" verdict (and the list that continues it) in an alert box."""
    from bs4 import BeautifulSoup, NavigableString
    soup = BeautifulSoup(html_text, "html.parser")
    for para in soup.find_all("p"):
        first = para.find(True)
        if not first or first.name != "strong" or not first.get_text().startswith("Void gap"):
            continue
        if para.contents and isinstance(para.contents[0], NavigableString) and para.contents[0].strip():
            continue  # "Void gap" is not at the start of the paragraph
        label_text = first.get_text()
        first.extract()
        verdict = (label_text.split(":", 1)[1] if ":" in label_text else "").strip()
        rest = para.get_text().strip()
        lead = (verdict or rest).lower()
        status = ("missing" if lead.startswith("missing") else "none" if lead.startswith(("none", "mostly none"))
                  else "partial")
        # drop the status word from the text when it stands alone ("partial." / "missing:" / "none;")
        if verdict == "" and para.contents and isinstance(para.contents[0], NavigableString):
            txt = str(para.contents[0])
            m = re.match(r"^\s*(missing|partial|none)\s*[.:;]\s*", txt, re.I)
            if m:
                txt = txt[m.end():]
            else:
                txt = txt.lstrip()
            txt = txt[:1].upper() + txt[1:]
            para.contents[0].replace_with(NavigableString(txt))
        box = soup.new_tag("div", attrs={"class": f"callout callout-{status}", "role": "note"})
        title = soup.new_tag("p", attrs={"class": "callout-title"})
        title.append(soup.new_tag("span"))
        title.span.string = "Void gap"
        pill = soup.new_tag("span", attrs={"class": "callout-status"})
        pill.string = STATUS_LABEL[status]
        title.append(pill)
        nxt = para.find_next_sibling()
        between_is_blank = True
        if nxt is not None:
            sib = para.next_sibling
            while sib is not None and sib is not nxt:
                if not (isinstance(sib, NavigableString) and not sib.strip()):
                    between_is_blank = False
                sib = sib.next_sibling
        follow = nxt if (nxt is not None and nxt.name in ("ul", "ol") and between_is_blank) else None
        para.insert_before(box)
        box.append(title)
        if para.get_text().strip():
            box.append(para.extract())
        else:
            para.extract()
        if follow is not None:
            box.append(follow.extract())
    return str(soup)


def h2_toc(html_text: str):
    return [(m.group(1), re.sub(r"<[^>]+>", "", m.group(2)))
            for m in re.finditer(r'<h2 id="([^"]+)">(.*?)</h2>', html_text)]


def inline_md(s: str) -> str:
    s = s.strip().replace("\\|", "|")
    parts = re.split(r"(`[^`]+`)", s)
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append(f"<code>{html.escape(p[1:-1])}</code>")
        else:
            t = html.escape(p, quote=False)
            t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
            t = re.sub(r"(?<![*\w])\*(?!\*)(.+?)(?<!\*)\*(?![*\w])", r"<em>\1</em>", t)
            t = MARKER_RE.sub(lambda m: badge(m.group(0)), t)
            t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
            t = PREV_RE.sub(lambda m: f'<span class="pv pv-{PREV_CLASS[m.group(1)]}">{m.group(1)}{m.group(2)}</span>', t)
            out.append(t)
    return "".join(out)


def gap_rows(md: str):
    sec = re.search(r"^## Gap list.*?$(.*?)(?=^## |\Z)", md, re.S | re.M)
    if not sec:
        return []
    rows = []
    lines = [l for l in sec.group(1).splitlines() if l.startswith("|")]
    for line in lines[2:]:
        cells = [c for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if len(cells) < 4:
            continue
        gap, who, prev, notes = cells[0], cells[1], cells[2], "|".join(cells[3:])
        p = prev.strip().lower()
        cat = "ts" if p.startswith("table stakes") else "cm" if p.startswith("common") else "df" if p.startswith("differentiator") else "ot"
        rows.append({"gap": inline_md(gap), "who": inline_md(who), "prev": inline_md(prev), "cat": cat,
                     "notes": inline_md(notes), "text": re.sub(r"[`*]", "", f"{gap} {who} {notes}").lower()})
    return rows


views = {}      # slug -> html
nav_areas = []
all_gaps = []
area_counts = []

for fname, slug, name in AREAS:
    md = (ROOT / "areas" / f"{fname}.md").read_text()
    md_body, legend_rows = split_legend(md)
    body = post(pandoc(md_body, slug))
    if legend_rows:
        body = body.replace("</h1>", "</h1>" + legend_html(legend_rows), 1)
    body = gap_callouts(body)
    toc = h2_toc(body)
    toc_html = "".join(f'<li><button type="button" class="jump" data-target="{i}">{html.escape(t)}</button></li>' for i, t in toc)
    num = int(fname[:2])
    rows = gap_rows(md)  # gap table is parsed from the full file
    for r in rows:
        r["area"] = slug
        r["areaName"] = name
        r["areaNum"] = num
    all_gaps.extend(rows)
    counts = {k: sum(1 for r in rows if r["cat"] == k) for k in ("ts", "cm", "df")}
    area_counts.append((num, slug, name, counts, len(rows)))
    toc_nav = f'<nav class="onpage" aria-label="Sections in this area"><ul>{toc_html}</ul></nav>'
    body = re.sub(r'(<h1 id="[^"]+">)\d+\.\s*', r'\1', body, count=1)
    views[slug] = f'<article class="doc">{body}</article>'
    nav_areas.append((num, slug, name, counts))

for slug, name in SOURCES:
    md = (ROOT / "inventories" / f"{slug}.md").read_text()
    body = post(pandoc(md, f"src-{slug}"))
    views[f"src-{slug}"] = inventory_view(slug, body)

# ---------- overview ----------
readme = (ROOT / "README.md").read_text()
readme = re.sub(r"^# .*?\n", "", readme, count=1)                       # title rendered by the page header
readme = readme.replace("*Prepared 2026-11-04. Covers", "*Covers", 1)
readme = readme.replace("This folder compares", "This page compares")
readme = re.sub(r"## Contents\n.*?(?=## Versions compared)", "<!--AREA-GRID-->\n\n", readme, flags=re.S)
readme = readme.replace("The inventories in `inventories/` are", "The inventories under **Sources** are")
readme = readme.replace("in `inventories/`", "under Sources")
overview = post(pandoc(readme, "overview"))

grid = [f'<section class="area-grid-wrap" aria-labelledby="areas-h"><h2 id="areas-h">The {len(AREAS)} areas</h2>'
        '<p class="grid-note">Each area page opens with a summary, Void\'s gaps (with how many of the other seven frameworks have each one) '
        'and where Void is ahead, followed by a capability-by-capability comparison of all eight frameworks. Counts below are gap-list rows.</p>'
        '<ol class="area-grid">']
for num, slug, name, counts, total in area_counts:
    bar = "".join(
        f'<span class="seg seg-{k}" style="flex-grow:{counts[k]}" title="{lbl}: {counts[k]}"></span>'
        for k, lbl in (("ts", "Table stakes"), ("cm", "Common"), ("df", "Differentiator")) if counts[k])
    grid.append(
        f'<li><a class="area-card" href="#{slug}">'
        f'<span class="area-name">{html.escape(name)}</span>'
        f'<span class="area-bar" aria-hidden="true">{bar}</span>'
        f'<span class="area-counts"><span class="c-ts">{counts["ts"]} table stakes</span> · '
        f'<span class="c-cm">{counts["cm"]} common</span> · <span class="c-df">{counts["df"]} differentiator</span></span>'
        f'</a></li>')
grid.append("</ol></section>")
overview = overview.replace("<!--AREA-GRID-->", "".join(grid))
HERO = ('<header class="hero">'
        '<h1>Void vs. the major metaframeworks</h1>'
        '<p class="lede">Void 1.5.0 compared with Next.js, React Router, TanStack Start, Nuxt, SvelteKit, SolidStart '
        f'and Astro across {len(AREAS)} areas, down to props and options, to find Void\'s feature gaps and guide its roadmap.</p>'
        '<div class="hero-actions"><a class="btn btn-primary" href="#gaps">Open the gap explorer</a>'
        '<a class="btn" href="#routing">Start with routing</a></div>'
        '</header>')
ov_toc = "".join(f'<li><button type="button" class="jump" data-target="{i}">{html.escape(t)}</button></li>' for i, t in h2_toc(overview))
ov_nav = f'<nav class="onpage" aria-label="Sections on this page"><ul>{ov_toc}</ul></nav>'
views["bugs"] = f'<article class="doc">{post(pandoc((ROOT / "bugs.md").read_text(), "bugs"))}</article>'
views["quick-wins"] = f'<article class="doc">{post(pandoc((ROOT / "quick-wins.md").read_text(), "quick-wins"))}</article>'
views["overview"] = HERO + f'<article class="doc doc-overview">{overview}</article>'

# ---------- nav ----------
def nav_item(slug, label, extra=""):
    return f'<li><a href="#{slug}" data-view="{slug}">{extra}<span>{html.escape(label)}</span></a></li>'

nav = ['<p class="nav-group">Summary</p><ul>',
       nav_item("overview", "Overview"),
       nav_item("gaps", "Gap explorer"),
       nav_item("bugs", "Bugs found"),
       nav_item("quick-wins", "Quick wins"),
       '</ul><p class="nav-group">Areas</p><ul>']
for num, slug, name, counts in nav_areas:
    nav.append(nav_item(slug, name))
nav.append('</ul><p class="nav-group">Sources</p><ul>')
for slug, name in SOURCES:
    nav.append(nav_item(f"src-{slug}", name))
nav.append("</ul>")

options = ['<option value="overview">Overview</option>', '<option value="gaps">Gap explorer</option>',
           '<option value="bugs">Bugs found</option>', '<option value="quick-wins">Quick wins</option>',
           '<optgroup label="Areas">']
options += [f'<option value="{slug}">{html.escape(name)}</option>' for num, slug, name, _ in nav_areas]
options.append('</optgroup><optgroup label="Sources">')
options += [f'<option value="src-{slug}">{html.escape(name)}</option>' for slug, name in SOURCES]
options.append("</optgroup>")

area_opts = "".join(f'<option value="{slug}">{html.escape(name)}</option>' for num, slug, name, _ in nav_areas)

templates = "".join(f'<template id="view-{slug}">{content}</template>'
                    for slug, content in views.items() if slug != "overview")
titles = {"overview": "Overview", "gaps": "Gap explorer", "bugs": "Bugs found", "quick-wins": "Quick wins"}
titles.update({slug: f"{num}. {name}" for num, slug, name, _ in nav_areas})
titles.update({f"src-{slug}": f"Inventory: {name}" for slug, name in SOURCES})

page = TEMPLATE.read_text()
page = (page.replace("%%NAV%%", "".join(nav))
            .replace("%%NAV_OPTIONS%%", "".join(options))
            .replace("%%OVERVIEW%%", views["overview"])
            .replace("%%TEMPLATES%%", templates)
            .replace("%%AREA_OPTIONS%%", area_opts)
            .replace("%%GAPS_JSON%%", json.dumps(all_gaps, ensure_ascii=False).replace("</", "<\\/"))
            .replace("%%TITLES_JSON%%", json.dumps(titles, ensure_ascii=False))
            .replace("%%GAP_TOTAL%%", str(len(all_gaps)))
            .replace("%%AREA_COUNT%%", str(len(AREAS))))
OUT.write_text(page)
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB), {len(all_gaps)} gap rows")
for num, slug, name, counts, total in area_counts:
    print(num, slug, counts, total)
