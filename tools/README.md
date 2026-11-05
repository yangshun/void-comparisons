# Building the webpage

`index.html` is generated from the Markdown files in this folder. Edit the Markdown, then rebuild:

```bash
python3 tools/build.py
```

That reads `README.md`, `bugs.md`, `quick-wins.md`, `areas/*.md` and `inventories/*.md`, and writes `index.html` next to them. Open `index.html` directly in a browser, or serve it as a static file (GitHub Pages works).

To republish the [claude.ai copy](https://claude.ai/artifact/7SaRtCXEFiUJHB3hfDq5ns), build with `--artifact`:

```bash
python3 tools/build.py --artifact
```

That writes `artifact.html`, the same page without the `<!doctype>`, `<head>` and `<body>` tags, because claude.ai adds its own. Publish that file, not `index.html`. It is ignored by git.

Requirements: Python 3.10+, `pandoc` 3.x on the `PATH`, and the Python package `beautifulsoup4`.

| File | What it does |
|---|---|
| `build.py` | Converts each Markdown file with pandoc, adds the page features (gap explorer, legends, marker badges, "Void gap" alerts, navigation) and fills `template.html` |
| `inventory_view.py` | Turns the framework inventories into a facts card plus collapsible capability rows |
| `template.html` | The page shell: styles, layout and the page's JavaScript |
| `page_shell.py` | The doctype, charset, viewport and reset that `index.html` gets around the page, copied from what claude.ai adds when publishing |

A few things live only in the build files, not in the Markdown: the Overview's title block, the area cards on the Overview, the facts cards on the inventory pages (in `inventory_view.py`), and a few labels in the sidebar and footer.
