from __future__ import annotations
import bleach
from html2text import html2text

# Basic, readable email-safe tags. Add/remove as you need.
ALLOWED_TAGS = [
    "p","br","hr","div","span","blockquote",
    "ul","ol","li",
    "strong","b","em","i","u","code","pre",
    "table","thead","tbody","tfoot","tr","th","td",
    "a","img",
]
ALLOWED_ATTRS = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title", "width", "height"],
    # allow simple formatting on spans/divs if you want (careful with style)
}
ALLOWED_PROTOCOLS = ["http","https","mailto","cid","data"]  # cid/data optional

def sanitize_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    # Strip scripts, on* handlers, javascript: URIs, etc.
    cleaned = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    # Optional: linkify plain URLs
    cleaned = bleach.linkify(cleaned, callbacks=[bleach.linkifier.DEFAULT_CALLBACK])
    return cleaned

def html_to_text(raw_html: str) -> str:
    """Plaintext fallback for previews/search."""
    return html2text(raw_html or "").strip()
