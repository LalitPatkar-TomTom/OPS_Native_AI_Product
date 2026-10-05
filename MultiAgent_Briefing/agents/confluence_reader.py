"""
Confluence Reader  -  generic read-and-extract engine.

Read-only. Knows how to talk to Confluence and pull named values out of pages.
Knows nothing about CC rules, ADP, or the process - it is told what to fetch
by the process spec.

The section extractor below is deliberately tolerant. Every quirk it handles
was observed in the 21 live Lanes solving-method pages, not imagined:

  heading case        "Rule Clarification" vs "Rule clarification"
  bold headings       "# **Solution**"
  extra whitespace    "#  **Example**"
  stray characters    "# Solution ￼"   (object-replacement char, 2 pages)
  heading levels      "# False Positive" vs "## False Positive"
  name variants       "False Positive" vs "False/Positives"
  badge position      usually first line, but on one page it sits *after*
                      the first heading
  badge case          "behavior-error" vs "Behavior-Error"
  sub-sections        "## Example 1" / "## Example 2" nested under "# Example"
  missing name line   some pages have no bold rule-name line at all

Anything it cannot resolve is reported in `warnings` rather than guessed at.
The caller decides whether to fall back to an LLM.
"""

from __future__ import annotations

import re
import unicodedata

# --------------------------------------------------------------------------
# Section vocabulary. Each canonical name maps to the variants seen in the
# wild. Matching is case-insensitive and whitespace-insensitive.
# --------------------------------------------------------------------------
SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "rule_clarification": ("rule clarification", "rule clarifications"),
    "example":            ("example", "examples"),
    "solution":           ("solution", "solutions"),
    "false_positive":     ("false positive", "false positives",
                           "false/positive", "false/positives"),
}

BEHAVIOUR_VALUES = ("behavior-error", "behavior-warning")

# A markdown ATX heading: leading #s, then the text.
_HEADING = re.compile(r"^(#{1,6})\s*(.+?)\s*$", re.MULTILINE)

# The status badge arrives in one of two shapes, depending on how the page
# was fetched: as a <custom> element, or as the [[STATUS:...]] marker that
# agents/confluence_fetch.py emits when converting storage format.
_BADGE = re.compile(
    r'<custom\s+data-type="status"[^>]*>\s*(.*?)\s*</custom>'
    r'|\[\[STATUS:\s*(.*?)\s*\]\]',
    re.IGNORECASE | re.DOTALL,
)

# Inline images - counted, then stripped from the text we return.
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


def _clean_heading(raw: str) -> str:
    """Reduce a heading to a comparable form.

    Strips bold/italic markers, the object-replacement character and other
    format controls, collapses whitespace, lowercases.
    """
    text = unicodedata.normalize("NFKC", raw)
    # Drop characters that carry no meaning but break naive comparison.
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    text = text.replace("￼", " ")          # object replacement char
    text = re.sub(r"[*_`]+", " ", text)         # bold / italic / code marks
    text = re.sub(r"[:\-–—]+$", " ", text)   # trailing punctuation
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _canonical_section(heading: str) -> str | None:
    """Map a cleaned heading onto a canonical section name, if it is one."""
    cleaned = _clean_heading(heading)
    for canonical, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            # Exact match, or the alias plus a numeric suffix ("example 1").
            if cleaned == alias or re.fullmatch(rf"{re.escape(alias)}\s*\d*", cleaned):
                return canonical
    return None


def extract_behaviour(body: str) -> tuple[str | None, list[str]]:
    """Pull the behaviour class out of the status badge.

    Returns the normalised value ("behavior-error" / "behavior-warning") and
    any warnings. The badge is normally the first thing on the page but is not
    guaranteed to be, so the whole body is searched.
    """
    warnings: list[str] = []
    matches = [next(g for g in m if g) for m in _BADGE.findall(body)
               if any(m)]
    if not matches:
        return None, ["no status badge found on the page"]

    normalised = _clean_heading(matches[0]).replace(" ", "-")
    if normalised not in BEHAVIOUR_VALUES:
        # Tolerate "behaviour" spelling and stray separators.
        normalised = normalised.replace("behaviour", "behavior")
    if normalised not in BEHAVIOUR_VALUES:
        warnings.append(f"unrecognised behaviour badge: {matches[0]!r}")
        return None, warnings

    # If the badge is not in the first non-empty line, say so - it means the
    # page deviates from the template and is worth a human glance.
    first_line = next((ln for ln in body.splitlines() if ln.strip()), "")
    if not _BADGE.search(first_line):
        warnings.append("status badge is not the first element on the page")

    return normalised, warnings


def extract_sections(body: str) -> tuple[dict[str, str], list[str]]:
    """Split a solving-method page into its canonical sections.

    Sub-sections ("Example 1", "Solution 2") are folded into their parent, in
    document order, so a multi-part solution comes back whole.
    """
    warnings: list[str] = []
    headings = list(_HEADING.finditer(body))
    if not headings:
        return {}, ["page has no headings at all"]

    # (canonical name) -> list of (original heading text, body chunk)
    sections: dict[str, list[tuple[str, str]]] = {}
    unknown: list[str] = []

    for i, match in enumerate(headings):
        canonical = _canonical_section(match.group(2))
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        chunk = body[start:end]

        if canonical is None:
            label = _clean_heading(match.group(2))
            if label:
                unknown.append(label)
            continue

        # Keep the heading as written (minus formatting) so a multi-part
        # section can be labelled when we fold it back together.
        label = re.sub(r"[*_`￼]+", "", match.group(2)).strip()
        sections.setdefault(canonical, []).append((label, chunk))

    if unknown:
        warnings.append("unrecognised headings: " + ", ".join(sorted(set(unknown))))

    out: dict[str, str] = {}
    for name, chunks in sections.items():
        if len(chunks) > 1:
            # A section split across sub-headings ("Solution 1", "Solution 2").
            # Keep the labels, otherwise distinct answers read as one
            # run-on paragraph in the ticket.
            parts = []
            for label, chunk in chunks:
                stripped = chunk.strip()
                parts.append(f"**{label}**\n\n{stripped}" if stripped else "")
            joined = "\n\n".join(p for p in parts if p)
        else:
            joined = chunks[0][1]
        image_count = len(_IMAGE.findall(joined))
        text = _IMAGE.sub("", joined)
        text = re.sub(r"‌", "", text)          # zero-width non-joiner
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        out[name] = text
        if image_count:
            out[f"{name}__image_count"] = str(image_count)

    for required in ("rule_clarification", "example", "solution"):
        if required not in out:
            warnings.append(f"required section missing: {required}")
        elif not out[required]:
            warnings.append(f"section present but empty (images only): {required}")

    return out, warnings


def extract_rule_name(rule_clarification: str) -> str | None:
    """Best-effort rule name from the top of the Rule Clarification section.

    Usually the first bold line. Several pages have no bold line, in which
    case the first non-empty line is used. Returns None if neither works -
    the caller already has the name from the analysis table, so this is
    only a cross-check.
    """
    for line in rule_clarification.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        bold = re.fullmatch(r"\*\*(.+?)\*\*", stripped)
        if bold:
            return bold.group(1).strip()
        return re.sub(r"[*_`]+", "", stripped).strip() or None
    return None


def parse_solving_method(rule_id: str, body: str, page_url: str) -> dict:
    """Turn one solving-method page into the fields a ticket needs."""
    behaviour, badge_warnings = extract_behaviour(body)
    sections, section_warnings = extract_sections(body)

    return {
        "rule_id": rule_id,
        "sm_link": page_url,
        "behaviour_class": behaviour,
        "rule_clarification": sections.get("rule_clarification", ""),
        "violation_example": sections.get("example", ""),
        "solution": sections.get("solution", ""),
        "false_positive": sections.get("false_positive", ""),
        "has_false_positive": "false_positive" in sections,
        "image_counts": {
            k.replace("__image_count", ""): int(v)
            for k, v in sections.items()
            if k.endswith("__image_count")
        },
        "warnings": badge_warnings + section_warnings,
    }


def run(task: dict) -> dict:
    """Agent entry point. Same shape as every other agent: dict in, dict out.

    Modes:
      find_page             locate a page by space + title
      read_page             fetch one page's body
      read_table            parse a table on a page into rows
      parse_solving_method  the extractor above, over an already-fetched body
    """
    mode = task.get("mode")

    if mode == "parse_solving_method":
        return parse_solving_method(
            task["rule_id"], task["body"], task.get("page_url", "")
        )

    raise NotImplementedError(
        f"mode {mode!r} not implemented yet - see cc_autosolve_adp.yaml "
        "for the modes this agent must support"
    )
