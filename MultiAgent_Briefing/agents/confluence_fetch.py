"""
Confluence storage-format adapters.

The REST API returns Confluence *storage format* - XHTML with `ac:` macro
elements - not the simplified text the section parser was written and tested
against. Rather than rewrite a parser that has already been proven on 21 live
pages, this module adapts the input to it.

Two things live here:

  storage_to_text   storage XHTML  ->  the plain-text-with-#-headings form
                    that agents/confluence_reader.py already parses

  parse_table       storage XHTML  ->  a list of row dicts, keyed by the
                    table's own header cells

Real quirks handled, all observed in live pages:

  * status macros carry their label in an ac:parameter, not as element text
  * text is frequently wrapped in <ac:inline-comment-marker> - the tag must go
    but the text inside it must stay
  * headings appear as <h1><strong>Example</strong></h1>, so bold survives
    into the heading text
  * images are <ac:image> elements with no text at all, and need to remain
    countable so a section that is only a diagram is not mistaken for empty
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

# --------------------------------------------------------------------------
# Status macro: the visible label is in <ac:parameter ac:name="title">.
_STATUS_MACRO = re.compile(
    r'<ac:structured-macro[^>]*ac:name="status".*?</ac:structured-macro>',
    re.DOTALL | re.IGNORECASE,
)
_STATUS_TITLE = re.compile(
    r'<ac:parameter[^>]*ac:name="title"[^>]*>(.*?)</ac:parameter>',
    re.DOTALL | re.IGNORECASE,
)

_HEADING = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.DOTALL | re.IGNORECASE)
_IMAGE = re.compile(r"<ac:image\b.*?(?:/>|</ac:image>)", re.DOTALL | re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


def _status_replacement(match: re.Match) -> str:
    """Render a status macro as a marker the section parser recognises.

    Deliberately NOT an element: everything left in angle brackets is stripped
    later, so a tag here would be removed before it could be read.
    """
    title = _STATUS_TITLE.search(match.group(0))
    label = title.group(1).strip() if title else ""
    return f"\n[[STATUS:{label}]]\n"


def _emphasis(text: str, tags: str, mark: str) -> str:
    """Convert an emphasis element to its Markdown marker, as a matched pair.

    Replacing each tag independently produces markers that Markdown will not
    render - `** text**` needs the space outside the marker, not inside, and a
    marker landing mid-word does nothing. Live solving-method pages are full of
    bold that starts or ends on a space, so the whitespace is moved out of the
    markers here. Otherwise the ticket shows literal asterisks.
    """
    pattern = re.compile(rf"<(?:{tags})[^>]*>(.*?)</(?:{tags})>",
                         re.DOTALL | re.IGNORECASE)

    def replace(match: re.Match) -> str:
        inner = match.group(1)
        core = inner.strip()
        if not core:
            return inner                     # emphasis around nothing
        lead = inner[:len(inner) - len(inner.lstrip())]
        trail = inner[len(inner.rstrip()):]
        return f"{lead}{mark}{core}{mark}{trail}"

    return pattern.sub(replace, text)


def _inline_marks(text: str) -> str:
    """Keep the meaning of inline formatting, drop the markup.

    Italics are deliberately dropped rather than converted. Markdown marks
    italics with underscores, and these pages are full of underscores that are
    part of the content - `exit_entrance`, `motorway_link`, `sharp_right`. A
    converter that paired them would corrupt real property names, and one that
    emitted them anyway would show literal underscores in the ticket. Italics
    in a rule specification carry no meaning worth that risk.
    """
    text = _emphasis(text, "strong|b", "**")
    text = _emphasis(text, "em|i", "")
    text = _emphasis(text, "code", "`")
    # Any emphasis tag left over was unclosed in the source. Drop it rather
    # than leave a lone marker that would render as a stray asterisk.
    text = re.sub(r"</?(?:strong|b|em|i|code)[^>]*>", "", text,
                  flags=re.IGNORECASE)
    return text


def storage_to_text(storage: str) -> str:
    """Convert storage XHTML into the form the section parser expects."""
    if not storage:
        return ""

    text = _STATUS_MACRO.sub(_status_replacement, storage)

    # Images must survive as something countable - a section holding only a
    # diagram is meaningful, and must not read as empty.
    text = _IMAGE.sub("\n![](image)\n", text)

    # Headings become ATX headings. Inline marks inside them are kept because
    # the parser strips them itself when comparing names.
    def heading(match: re.Match) -> str:
        level = int(match.group(1))
        inner = _TAG.sub("", _inline_marks(match.group(2)))
        return f"\n\n{'#' * level} {inner.strip()}\n\n"

    text = _HEADING.sub(heading, text)

    # Block boundaries become newlines, so paragraphs do not run together.
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(?:p|div|tr|table|ul|ol|blockquote)>", "\n\n", text,
                  flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "\n* ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)

    text = _inline_marks(text)

    # Everything left is markup - including ac:inline-comment-marker, whose
    # inner text must be preserved. Stripping tags rather than elements is
    # exactly what achieves that.
    text = _TAG.sub("", text)

    text = html.unescape(text)
    text = text.replace("‌", "")            # zero-width non-joiner
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# --------------------------------------------------------------------------
class _TableParser(HTMLParser):
    """Collect every table on a page as a list of rows of cell text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag in ("br", "p", "li") and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(c for c in self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table":
            if self._depth == 1 and self._table is not None:
                self.tables.append(self._table)
                self._table = None
            self._depth = max(0, self._depth - 1)

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def parse_table(storage: str, *, table_index: int = 0,
                required_columns: list[str] | None = None) -> tuple[list[dict], list[str]]:
    """Extract one table as row dicts keyed by its header cells.

    When `required_columns` is given, the table containing all of them is
    chosen instead of `table_index` - which is safer on a page that grows an
    extra table later.
    """
    warnings: list[str] = []
    parser = _TableParser()
    parser.feed(storage)
    tables = [t for t in parser.tables if len(t) > 1]

    if not tables:
        return [], ["no table with data rows found on the page"]

    chosen = None
    if required_columns:
        for table in tables:
            header = [h.strip() for h in table[0]]
            if all(any(c == col for c in header) for col in required_columns):
                chosen = table
                break
        if chosen is None:
            warnings.append(
                "no table contained all of: " + ", ".join(required_columns))
    if chosen is None:
        if table_index >= len(tables):
            return [], [f"page has {len(tables)} table(s); index {table_index} asked for"]
        chosen = tables[table_index]

    header = [h.strip() for h in chosen[0]]
    if len(set(header)) != len(header):
        warnings.append("table has duplicate column headers; later ones win")

    rows = []
    for raw in chosen[1:]:
        # A short row means trailing empty cells were omitted, which is normal.
        padded = list(raw) + [""] * (len(header) - len(raw))
        rows.append({header[i]: padded[i] for i in range(len(header))})

    return rows, warnings
