# AGENTS.md

A feature gap analysis of Void (native "Void app" mode) against seven metaframeworks, written in Markdown, plus a single-page website built from it. The site is `index.html`, served by GitHub Pages at https://yangshun.github.io/void-comparisons/ from the root of `main`.

## Layout

| Path | What it is |
|---|---|
| `README.md` | Short intro that points readers to the site. Not part of the site |
| `overview.md` | Summary, versions compared, roadmap, method. Becomes the site's Overview page word for word |
| `areas/NN-slug.md` | The 14 area comparisons |
| `inventories/*.md` | Raw per-framework inventories. Where they disagree with an area file, the area file wins; don't "fix" an inventory to match |
| `bugs.md`, `quick-wins.md` | Bugs found in Void's source; small fixes |
| `tools/` | The site build (see `tools/README.md`) |
| `index.html` | **Generated.** Never edit it by hand |

## Rebuild the site after every Markdown change

GitHub Pages serves whatever `index.html` is on `main`, and nothing rebuilds it automatically. After changing any Markdown file other than `README.md` and `AGENTS.md`, or anything in `tools/`, rebuild and commit `index.html` in the same commit:

```bash
python3 tools/build.py
```

It needs Python 3.10+ with `beautifulsoup4`, and `pandoc` 3.x on the `PATH`. If `python3` is too old, let `uv` supply one:

```bash
uv run --no-project --python '>=3.10' --with beautifulsoup4 python tools/build.py
```

A successful build prints `wrote …/index.html (… MB), N gap rows`. Check the result by opening `index.html` in a browser.

## Markdown the build depends on

`tools/build.py` parses the Markdown, so these structures must stay intact:

- **Area file header.** `# N. Title`, then only `**Key:** value` lines (`Versions`, `Markers`, `Paths`) before the first `## `. They become the page's legend. Any other text in that block is dropped from the site.
- **Gap list.** The `## Gap list…` section is a four-column table: gap, who has it, prevalence, notes. The prevalence cell starts with `Table stakes`, `Common` or `Differentiator` followed by a count, e.g. `Common (5)`. It feeds the gap explorer and the Overview's area cards. Escape a literal pipe in a cell as `\|`.
- **Verdicts.** A paragraph starting `**Void gap:**` followed by `missing`, `partial` or `none` becomes a colored alert box.
- **Markers.** `[exp]`, `[CC]`, `[prev]`, `[N5]`, `(src)` and `(unverified)` become badges. A new marker needs an entry in `MARKER_INFO` in `build.py`.
- **Overview.** The build drops the first `# ` heading of `overview.md` (the page header shows the title) and puts the area cards where `<!--AREA-GRID-->` is. Keep that placeholder, and write the rest as it should read on the site.
- **Adding an area or a framework** means updating `AREAS` or `SOURCES` in `build.py`.

## Content conventions

- Compare behavior, not API names, down to individual options. Cite a file for each claim: a docs path, or a Void source path. In area files, short Void paths like `pages/scan.ts` are under `packages/void/src/`.
- Check every "Void lacks X" against Void's source (`packages/`), not only its docs.
- Prevalence counts how many of the other seven have the capability: Table stakes is 6–7, Common is 3–5, Differentiator is 1–2. It is a count, not a priority. Nothing in this repo is scored or graded.
- In `bugs.md`, remove a bug's row once it's fixed.
- The "Versions compared" tables in `overview.md` record the exact commit read for each framework. To update the analysis, diff each repo from its recorded commit (`overview.md` shows the command), re-check only the affected areas, then update those tables.
