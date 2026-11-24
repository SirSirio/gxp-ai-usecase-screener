"""Turn source documents into sections that keep the document's own section ids.

Why this matters: a citation is only useful if it points to a real section a QA reviewer can open
("Annex 22 §3.3"), not to "page 4, characters 1200-2300". So parsing is section-aware.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from app.ingest.sources import Heading, Source

LINE_NUMBER = re.compile(r"^\d{1,4}$")  # EC/FDA drafts print line numbers as separate lines
PAGE_LABEL = re.compile(r"^Page \d+ of \d+$")
MARKER = re.compile(r"^(?:[IVX]{1,4}|[A-Ha-h]|\d{1,2}(?:\.\d{1,2}){0,3})\.?$")  # "2.1." alone on a line
NUMBERED = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,3})\.?(?:\s+(.*))?$")
ARTICLE = re.compile(r"^Article (\d{1,3})$")
KEEP_HYPHEN = {
    "risk", "data", "self", "human", "non", "pre", "post", "re", "co", "multi", "real", "high", "low",
    "well", "cross", "sub", "semi", "long", "short", "time", "case", "e", "in", "out", "end", "user",
    "third", "fit", "up", "over", "under", "on", "off", "ink", "wet", "hold", "machine", "open",
}


@dataclass
class Section:
    doc_id: str
    section: str
    title: str
    parent_title: str
    page_start: int
    page_end: int
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return join_lines(self.lines)


def join_lines(lines: list[str]) -> str:
    """Join wrapped PDF lines into prose, repairing words hyphenated across line breaks."""
    out = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not out:
            out = line
        elif out.endswith("-") and line[:1].islower():
            last_word = re.split(r"[\s(]", out[:-1])[-1].lower()
            out = out + line if last_word in KEEP_HYPHEN else out[:-1] + line
        else:
            out = f"{out} {line}"
    out = re.sub(r"\s+", " ", out)
    out = re.sub(r"(\w)- (\w)", lambda m: f"{m.group(1)}-{m.group(2)}", out)  # "risk- based" -> "risk-based"
    return out.strip()


def read_lines(src: Source, raw_dir: Path) -> list[tuple[int, str]]:
    """Read (page, line) pairs, dropping line numbers, page labels and running headers."""
    path = raw_dir / src.filename
    pages: list[tuple[int, str]] = []
    if path.suffix == ".pdf":
        with pymupdf.open(path) as doc:
            for i in range(src.start_page, doc.page_count):
                pages.append((i + 1, doc[i].get_text()))
    else:
        pages.append((1, path.read_text(encoding="utf-8")))

    drops = [re.compile(p) for p in src.drop_patterns]
    lines: list[tuple[int, str]] = []
    for page, text in pages:
        for raw in text.splitlines():
            line = raw.strip().replace(" ", " ")
            if not line or LINE_NUMBER.match(line) or PAGE_LABEL.match(line):
                continue
            if any(d.search(line) for d in drops):
                continue
            lines.append((page, line))

    if src.start_pattern:
        start = re.compile(src.start_pattern)
        idx = next((i for i, (_, ln) in enumerate(lines) if start.search(ln)), 0)
        lines = lines[idx:]
    if src.end_pattern:
        end = re.compile(src.end_pattern)
        idx = next((i for i, (_, ln) in enumerate(lines) if end.search(ln)), len(lines))
        lines = lines[:idx]
    return merge_markers(lines)


def merge_markers(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """PDFs often put the number on its own line ("2.1." / "Personnel. ..."). Re-attach it."""
    out: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        page, line = lines[i]
        if MARKER.match(line) and i + 1 < len(lines) and not MARKER.match(lines[i + 1][1]):
            out.append((page, f"{line} {lines[i + 1][1]}"))
            i += 2
            continue
        out.append((page, line))
        i += 1
    return out


def _is_group_title(line: str) -> bool:
    """ALL-CAPS lines like 'DATA GOVERNANCE SYSTEMS' are group headings, not body text."""
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters) and not NUMBERED.match(line)


def _plausible_next(new: tuple[int, ...], cur: tuple[int, ...] | None) -> bool:
    """Accept a number as a new section only if it can follow the current one.

    Stops dates ("30 June 2011") and wrapped numbers in prose from being read as headings.
    """
    if cur is None:
        return new[-1] in (0, 1)
    candidates = {cur + (1,)}
    for k in range(len(cur)):
        candidates.add(cur[:k] + (cur[k] + 1,))
    return new in candidates


def _split_title(rest: str) -> tuple[str | None, bool]:
    """Return (title, title_is_whole_line). '2.1. Personnel. In order to ...' -> ('Personnel', False)."""
    rest = rest.strip()
    if not rest:
        return None, True
    words = rest.split()
    small = {"of", "and", "the", "for", "in", "to", "a", "an", "as", "on", "or", "with", "within", "by"}
    capitalised = [w for w in words if w.lower() not in small]
    looks_like_heading = capitalised and sum(w[:1].isupper() for w in capitalised) / len(capitalised) >= 0.6
    if len(rest) <= 90 and not rest.endswith((".", ",", ";")) and rest[:1].isupper() and (looks_like_heading or len(words) <= 3):
        return (rest.title() if rest.isupper() else rest).rstrip(":").replace(" Of ", " of "), True
    m = re.match(r"^([A-Z][\w\s\-/,()’'&]{1,60}?)\.\s", rest)
    if m:
        return m.group(1).strip(), False
    return None, False


def _match_named(line: str, named: tuple[Heading, ...]) -> tuple[str, str] | None:
    for h in named:
        m = re.search(h.pattern, line)
        if m:
            if "{n}" in h.section:
                n = m.group(1)
                rest = line[m.end():].strip(" .:")
                return h.section.replace("{n}", n), (rest or h.title.replace("{n}", n))
            return h.section, h.title
    return None


def parse_numbered(src: Source, lines: list[tuple[int, str]]) -> list[Section]:
    sections: list[Section] = []
    titles: dict[str, str] = {}
    cur_num: tuple[int, ...] | None = None
    group = ""
    current: Section | None = None

    def parent_of(num: str) -> str:
        parts = num.split(".")
        if len(parts) == 1:
            return ""
        for k in range(len(parts) - 1, 0, -1):
            t = titles.get(".".join(parts[:k]))
            if t:
                return t
        return group

    for page, line in lines:
        named = _match_named(line, src.named_headings)
        if named:
            sec_id, title = named
            current = Section(src.doc_id, sec_id, title, "", page, page)
            sections.append(current)
            titles[sec_id] = title
            continue
        if _is_group_title(line):
            group = line.title()
            continue
        m = NUMBERED.match(line)
        if m:
            num = tuple(int(x) for x in m.group(1).split("."))
            too_high = src.max_top_level is not None and num[0] > src.max_top_level
            if not too_high and _plausible_next(num, cur_num):
                cur_num = num
                sec_id = ".".join(str(x) for x in num)
                title, whole = _split_title(m.group(2) or "")
                parent = parent_of(sec_id)
                titles[sec_id] = title or ""
                current = Section(src.doc_id, sec_id, title or parent or f"Section {sec_id}", parent, page, page)
                if m.group(2) and not whole:
                    current.lines.append(m.group(2))
                sections.append(current)
                continue
        if current is not None:
            current.lines.append(line)
            current.page_end = page
    return sections


def parse_headings(src: Source, lines: list[tuple[int, str]]) -> list[Section]:
    """Explicit, ordered heading list. Only the next unused heading is tested, so a table of
    contents or a repeated phrase later in the text cannot restart the sequence."""
    sections: list[Section] = []
    pending = list(src.headings)
    current: Section | None = None
    for page, line in lines:
        hit = None
        for j, h in enumerate(pending[:3]):  # allow a missing heading, but stay in order
            if re.search(h.pattern, line):
                hit = j
                break
        if hit is not None:
            h = pending[hit]
            pending = pending[hit + 1:]
            parent = ""
            if "." in h.section:
                parent = next((s.title for s in reversed(sections) if s.section == h.section.rsplit(".", 1)[0]), "")
            current = Section(src.doc_id, h.section, h.title, parent, page, page)
            sections.append(current)
            m = re.search(h.pattern, line)
            rest = line[m.end():].strip() if m else ""
            if h.section in ("intro",) or (rest and len(rest) > 40):
                current.lines.append(line)
            continue
        if current is not None:
            current.lines.append(line)
            current.page_end = page
    return sections


def parse_articles(src: Source, lines: list[tuple[int, str]]) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    last_num = 0
    keep = set(src.articles)
    i = 0
    while i < len(lines):
        page, line = lines[i]
        m = ARTICLE.match(line)
        if m and int(m.group(1)) == last_num + 1:
            last_num = int(m.group(1))
            title = lines[i + 1][1] if i + 1 < len(lines) else ""
            current = Section(src.doc_id, f"art-{last_num}", f"Article {last_num}: {title.strip('` ')}", "", page, page) if last_num in keep else None
            if current:
                sections.append(current)
            i += 2
            continue
        annex = re.match(r"^ANNEX ([IVX]+)$", line)
        if annex and last_num > 100:  # annexes follow the last article (113)
            roman = annex.group(1)
            title = lines[i + 1][1] if i + 1 < len(lines) else ""
            current = Section(src.doc_id, f"annex-{roman}", f"Annex {roman}: {title}", "", page, page) if roman in src.annexes else None
            if current:
                sections.append(current)
            i += 2
            continue
        if current is not None and not _is_group_title(line):
            current.lines.append(line)
            current.page_end = page
        i += 1
    return sections


PARSERS = {"numbered": parse_numbered, "headings": parse_headings, "articles": parse_articles}


def parse_source(src: Source, raw_dir: Path) -> list[Section]:
    lines = read_lines(src, raw_dir)
    sections = PARSERS[src.parser](src, lines)
    return [s for s in sections if s.text or s.title]
