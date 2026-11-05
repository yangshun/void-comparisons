"""The document shell (doctype, <head>, <body>) around the built page.

claude.ai wraps a published page in its own shell, so the copy published there must not
have one (build with --artifact). index.html is opened as a file or served as-is, so it
gets this copy of claude.ai's shell and renders the same way: standards mode, UTF-8, the
phone viewport and the same small reset.
"""

HEAD = (
    "<!doctype html>\n"
    '<html lang="en">\n'
    "<head>\n"
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
    "<style>"
    ":root{color-scheme:light;box-sizing:border-box;"
    "padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
    "html{scroll-padding-top:env(safe-area-inset-top,0px)}"
    "body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#000}"
    "img{max-width:100%}"
    "[hidden]:not([hidden=until-found i]){display:none!important}"
    "</style>\n"
    "</head>\n"
    "<body>\n"
)
TAIL = "\n</body>\n</html>\n"


def wrap(page: str) -> str:
    return HEAD + page + TAIL
