"""Presentation for the per-framework inventory pages.

The inventory text is left as written. This module only restructures the rendered HTML:
a facts card, the original intro collapsed under "About this inventory", one collapsible
row per capability (name, status, one-sentence summary), muted citations, and links from
each section to its area comparison page.
"""
import html
import re

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

FACTS = {
    "void": [("Version", "1.5.0"), ("UI libraries", "React 19, Vue 3.5, Svelte 5, Solid 1.9"), ("Bundler", "Vite 8"),
             ("Server", "Hono"), ("Runtime", "Cloudflare Workers by default; Node, Bun or Deno")],
    "nextjs": [("Version", "16.4 (App Router)"), ("UI library", "React 19.2+"), ("Bundler", "Turbopack (Webpack optional)"),
               ("Server", "Next.js Node server"), ("Runtime", "Node.js 20.9+")],
    "react-router": [("Version", "8.x, framework mode"), ("UI library", "React 19.2+"), ("Bundler", "Vite 7+"),
                     ("Server", "Fetch request handler with host adapters"), ("Runtime", "Node by default; Cloudflare Workers")],
    "tanstack-start": [("Version", "1.169+"), ("UI library", "React 18 or 19 (a Solid version also exists)"), ("Bundler", "Vite 8 or Rsbuild"),
                       ("Server", "Start's fetch handler, deployed through Nitro"), ("Runtime", "Node by default; Cloudflare, Netlify")],
    "nuxt": [("Version", "5.0 pre-release (4.x is stable)"), ("UI library", "Vue 3"), ("Bundler", "Vite 8 with Rolldown"),
             ("Server", "Nitro v3 (h3 v2)"), ("Runtime", "Node by default; other hosts through Nitro presets")],
    "sveltekit": [("Version", "3.x"), ("UI library", "Svelte 5"), ("Bundler", "Vite 8 with Rolldown"),
                  ("Server", "SvelteKit's own request handler"), ("Runtime", "Node by default; adapters for Bun, Cloudflare, Netlify, Vercel, static")],
    "solidstart": [("Version", "2.0"), ("UI library", "Solid 1.9"), ("Bundler", "Vite 8 or 9"),
                   ("Server", "h3 v2 through a deploy plugin (Nitro, Netlify or Cloudflare)"), ("Runtime", "Set by the deploy plugin")],
    "astro": [("Version", "7.4"), ("UI library", "Astro components, plus React, Preact, Vue, Svelte or Solid islands"),
              ("Bundler", "Vite 8 with a Rust compiler"), ("Server", "Astro's fetch pipeline, replaceable in src/fetch.ts"),
              ("Runtime", "Static by default; Node, Cloudflare and others through adapters")],
}
DOCS = {
    "void": ("voidzero-dev/void", "65eb7f07f020fda6586dba4c2d2d03aaab000cc3", "2026-11-04"),
    "nextjs": ("vercel/next.js", "a47959503adac8080a8b9a35f79617740d97925f", "2026-11-03"),
    "react-router": ("remix-run/react-router", "db80dda076ec9cdcefff480079252fe0c977710e", "2026-11-02"),
    "tanstack-start": ("TanStack/router", "da8c28c498230a5730ce75b2693baeeb3ef68ac1", "2026-11-03"),
    "nuxt": ("nuxt/nuxt", "9496b7e5fe75740a5f8ef9826a2918667e4b4a82", "2026-11-03"),
    "sveltekit": ("sveltejs/kit", "fe4deb1b76d876bdca56db489388c98ed74973f5", "2026-11-04"),
    "solidstart": ("solidjs/solid-docs", "9a9d77a75642f6e2ab68d80b0081d45ad3424b13", "2026-10-29"),
    "astro": ("withastro/docs", "c73a3bea5a635c1afce0f0516ff22ecb34a3d7d4", "2026-11-03"),
}
# the inventories keep the original 12 area headings; area 10 was later split into three pages
SECTION_LINKS = {
    1: [("routing", "Routing")], 2: [("rendering", "Rendering modes")], 3: [("data-loading", "Data loading")],
    4: [("mutations", "Mutations")], 5: [("caching", "Caching & revalidation")], 6: [("server-api", "Server & API")],
    7: [("loading-error", "Loading & error states")], 8: [("type-safety", "Type safety")], 9: [("metadata-seo", "Metadata & SEO")],
    10: [("assets", "Images, fonts & scripts"), ("styling", "CSS & styling"), ("markdown", "Markdown & content")],
    11: [("build-deploy", "Build output & deployment")], 12: [("dev-tooling", "Dev tooling & observability")],
}

STATUS_RE = re.compile(
    r"^\s*(supported|partially supported|partial|not supported|not found(?: in docs)?|undocumented|not applicable|n/a)\b", re.I)
STATUS_TAIL_RE = re.compile(r"^\s*(?:/\s*not (?:found|supported)(?: in docs)?)?[\s.:;,—–-]*")
STATUS_CHIP = {"supported": ("Supported", "sup"), "partially supported": ("Partial", "par"), "partial": ("Partial", "par"),
               "not supported": ("Not supported", "not"), "not found": ("Not found", "nf"), "not found in docs": ("Not found", "nf"),
               "undocumented": ("Undocumented", "nf"), "not applicable": ("N/A", "nf"), "n/a": ("N/A", "nf")}
BLOCK_TAGS = {"p", "ul", "ol", "div", "table", "pre", "blockquote", "dl", "details", "h3", "h4"}
ABBREV_RE = re.compile(r"\b(e\.g|i\.e|vs|etc|cf|approx)\.$", re.I)


def _text(node) -> str:
    if isinstance(node, Comment):
        return ""
    return str(node) if isinstance(node, NavigableString) else node.get_text()


def _sentence_end(text: str, start: int) -> int:
    for m in re.finditer(r"[.!?](?=\s+[A-Z(`\[\"“*])", text[start:]):
        i = start + m.end()
        if ABBREV_RE.search(text[max(start, i - 8):i]):
            continue
        return i
    return len(text)


def _html_range(nodes, start: int, end: int) -> str:
    """HTML for the plain-text range [start, end) of a run of inline nodes; tags are kept whole."""
    out, pos = [], 0
    for n in nodes:
        t = _text(n)
        a, b = pos, pos + len(t)
        pos = b
        if b <= start:
            continue
        if a >= end:
            break
        if isinstance(n, NavigableString):
            if not isinstance(n, Comment):
                out.append(html.escape(t[max(start - a, 0):min(end - a, len(t))], quote=False))
        elif a >= start:
            out.append(str(n))
    return "".join(out)


def _summary(nodes, s0: int) -> str:
    plain = "".join(_text(n) for n in nodes)
    s0 += len(plain[s0:]) - len(plain[s0:].lstrip(" .:;,—–-*\n"))
    end = _sentence_end(plain, s0)
    if end - s0 < 50 and end < len(plain):
        end = _sentence_end(plain, end + 1)
    ellipsis = False
    if end - s0 > 210:
        cut = plain.rfind(" ", s0, s0 + 190)
        end, ellipsis = (cut if cut > s0 else s0 + 190), True
    return _html_range(nodes, s0, end).strip() + ("…" if ellipsis else "")


def _inline_run(container):
    run = []
    for c in container.contents:
        if isinstance(c, Tag) and c.name in BLOCK_TAGS:
            break
        run.append(c)
    return run


def _first_content(node):
    for c in node.contents:
        if isinstance(c, NavigableString) and not c.strip():
            continue
        return c
    return None


def _eligible(li: Tag) -> bool:
    first = _first_content(li)
    lead_parent = first if isinstance(first, Tag) and first.name == "p" else li
    strong = _first_content(lead_parent)
    if not (isinstance(strong, Tag) and strong.name == "strong"):
        return False
    name = strong.get_text().strip().rstrip(":").strip()
    return bool(name) and len(name) <= 90


def _capability_row(soup, li: Tag):
    """Turn a '<li><strong>Name</strong>: text…' item into a collapsible capability row, or None."""
    first = _first_content(li)
    lead_parent = first if isinstance(first, Tag) and first.name == "p" else li
    strong = _first_content(lead_parent)
    if not (isinstance(strong, Tag) and strong.name == "strong"):
        return None
    name = strong.get_text().strip().rstrip(":").strip()
    if not name or len(name) > 90:
        return None
    strong.extract()
    nxt = lead_parent.contents[0] if lead_parent.contents else None
    if isinstance(nxt, NavigableString) and str(nxt).lstrip().startswith(":"):
        nxt.replace_with(NavigableString(str(nxt).lstrip()[1:].lstrip()))
    # inline run that forms the lead sentence(s)
    lead_nodes = []
    for c in lead_parent.contents:
        if isinstance(c, Tag) and c.name in BLOCK_TAGS:
            break
        lead_nodes.append(c)
    plain = "".join(_text(n) for n in lead_nodes)
    chip_label, chip_cls, qualifier = "", "none", ""
    s0 = len(plain) - len(plain.lstrip())
    lead_first = next((n for n in lead_nodes if _text(n).strip()), None)
    if isinstance(lead_first, Tag) and lead_first.name == "strong" and STATUS_RE.match(lead_first.get_text()):
        # status written in bold, e.g. "**Supported (two separate mechanisms)**."
        st = lead_first.get_text()
        m = STATUS_RE.match(st)
        chip_label, chip_cls = STATUS_CHIP[m.group(1).lower()]
        qualifier = st[m.end():].strip().strip("()[]").strip(" .:;,—–-")
        s0 = plain.index(st) + len(st)
    else:
        m = STATUS_RE.match(plain)
        if m:
            chip_label, chip_cls = STATUS_CHIP[m.group(1).lower()]
            s0 = m.end()
            s0 += STATUS_TAIL_RE.match(plain[s0:]).end()
    summary = _summary(lead_nodes, s0)
    if not re.sub(r"<[^>]+>", "", summary).strip(" .") and qualifier:
        summary = html.escape(qualifier) + "."
    if not re.sub(r"<[^>]+>", "", summary).strip(" ."):
        # the detail starts in a nested list or paragraph: summarise its first item
        scope = li.contents if lead_parent is li else lead_parent.find_next_siblings()
        block = next((c for c in scope if isinstance(c, Tag) and c.name in ("ul", "ol", "p")), None)
        if block is not None:
            item = block.find("li") if block.name in ("ul", "ol") else block
            if item is not None:
                inner = _first_content(item)
                src = inner if isinstance(inner, Tag) and inner.name == "p" else item
                summary = _summary(_inline_run(src), 0)
    summary = summary[:1].upper() + summary[1:] if summary[:1].isalpha() else summary

    box = soup.new_tag("details", attrs={"class": "cap"})
    summ = soup.new_tag("summary")
    summ.append(BeautifulSoup(
        f'<span class="cap-head"><span class="cap-name">{html.escape(name)}</span>'
        + (f'<span class="st st-{chip_cls}">{html.escape(chip_label)}</span>' if chip_label else "")
        + '</span>'
        + (f'<span class="cap-sum">{summary}</span>' if summary.strip() else ""), "html.parser"))
    body = soup.new_tag("div", attrs={"class": "cap-body"})
    for c in list(li.contents):
        body.append(c.extract())
    box.append(summ)
    box.append(body)
    return box


def _wrap_citations(soup):
    for s in list(soup.find_all(string=re.compile(r"\bSources?:"))):
        if isinstance(s, Comment) or s.find_parent(["code", "summary", "h1", "h2", "h3"]):
            continue
        txt = str(s)
        i = re.search(r"\bSources?:", txt).start()
        following, sib = [], s.next_sibling
        while sib is not None and not (isinstance(sib, Tag) and sib.name in BLOCK_TAGS):
            following.append(sib)
            sib = sib.next_sibling
        before = NavigableString(txt[:i].rstrip() + " ")
        cite = soup.new_tag("span", attrs={"class": "cite"})
        cite.append(NavigableString(txt[i:]))
        s.replace_with(before)
        before.insert_after(cite)
        for f in following:
            cite.append(f.extract())


def facts_html(slug: str) -> str:
    rows = "".join(f'<div><dt>{html.escape(k)}</dt><dd>{html.escape(v)}</dd></div>' for k, v in FACTS[slug])
    repo, sha, date = DOCS[slug]
    rows += (f'<div><dt>Docs read</dt><dd><a href="https://github.com/{repo}/commit/{sha}">{html.escape(repo)} '
             f'<code>{sha[:7]}</code></a> · {date}</dd></div>')
    return f'<dl class="facts">{rows}</dl>'


def inventory_view(slug: str, body_html: str) -> str:
    soup = BeautifulSoup(body_html, "html.parser")
    h1 = soup.find("h1")
    # 1) intro → collapsed "About this inventory"
    intro = []
    sib = h1.next_sibling
    while sib is not None and not (isinstance(sib, Tag) and sib.name == "h2"):
        nxt = sib.next_sibling
        intro.append(sib.extract())
        sib = nxt
    about = soup.new_tag("details", attrs={"class": "about"})
    about.append(BeautifulSoup("<summary>About this inventory: how the version was determined, conventions, recent changes</summary>", "html.parser"))
    inner = soup.new_tag("div", attrs={"class": "about-body"})
    for n in intro:
        inner.append(n)
    about.append(inner)
    head = BeautifulSoup(
        facts_html(slug)
        + '<div class="inv-bar"><p class="inv-note">Raw research notes behind the area comparisons. Where they disagree, '
          'the area page has the corrected, source-checked version.</p>'
          '<button type="button" class="expand-all" aria-pressed="false">Expand all</button></div>', "html.parser")
    h1.insert_after(about)
    h1.insert_after(head)
    # 2) section links + capability rows
    for h2 in soup.find_all("h2"):
        m = re.match(r"\s*(\d+)\.", h2.get_text())
        if m and int(m.group(1)) in SECTION_LINKS:
            links = " · ".join(f'<a href="#{s}">{html.escape(n)}</a>' for s, n in SECTION_LINKS[int(m.group(1))])
            h2.insert_after(BeautifulSoup(f'<p class="compare-link">Compare all eight frameworks: {links}</p>', "html.parser"))
    for ul in soup.find_all("ul", recursive=False):
        items = ul.find_all("li", recursive=False)
        if not items or not all(_eligible(li) for li in items):
            continue
        rows = [_capability_row(soup, li) for li in items]
        box = soup.new_tag("div", attrs={"class": "cap-list"})
        for r in rows:
            box.append(r)
        ul.replace_with(box)
    # 3) muted citations
    _wrap_citations(soup)
    return f'<article class="doc doc-inventory">{soup}</article>'
