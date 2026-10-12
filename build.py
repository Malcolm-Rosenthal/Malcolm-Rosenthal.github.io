#!/usr/bin/env python3
"""Turn content/ into the website in docs/.

    python3 build.py

Needs nothing installed beyond Python 3: the Markdown converter is the single
file tools/markdown2.py, kept in this repo.

HOW THE SITE IS LAID OUT ON DISK

    content/home.md            the note on the home board
    content/<section>/         one folder per mat on the home board
        index.md               the section's own page, and its settings
        <page>.md              one door on that mat, one page behind it
        anything else          pictures, PDFs: copied across untouched

    templates/base.html        the frame every page is poured into
    assets/                    stylesheet, script, site-wide images
    docs/                      THE OUTPUT. Wiped and rebuilt every run; never
                               edit anything in it by hand.

Every .md file may start with settings between two lines of three dashes:

    ---
    title: Publications
    order: 1
    ---

Settings a PAGE understands:
    title   the door's name and the page's heading (default: from the file name)
    order   position among its siblings, low first (default 100)
    date    2026-10-04. Dated pages sort newest first and show the date.
    note    a small line under the name on the door
    link    a web address. The door goes straight there and no page is made.
    draft   yes: skip this file entirely
    layout  cv: a CV, typed line by line (see the note at the top of cv.md)
    parent  the slug of another page in this folder. The page then has no door
            on the mat; its door goes in the parent's text, and the trail runs
            through the parent.
    papers  references from the CV to show beside the page, as documents.
            A few words from each title, separated by |, e.g.
            papers: novel substrate-borne | microhabitat specialization
    pdf     a PDF in the same folder, offered as "Download PDF" at the top.
            Left out quietly while the file is not there yet.

Settings a SECTION's index.md understands, as well as title and order:
    mat     slate, moss, tan, indigo or plum
    page    no: the section has no page of its own, only a mat (Elsewhere)
    show    how many doors the home board shows before the "more" door
    more    the name of that "more" door, which leads to the section page

In any text:
    {{door: slug}}      on a line of its own: a door to that page in this
                        folder. Several such lines together sit side by side.
    {{todo: a note}}    a dashed box saying what still goes here.
Titles may use *italics* (species names).

Settings home.md understands: title, kicker, subtitle (the line under the name;
a | starts a new line),
photo (a path inside assets/),
age-figures (default 4), and born: 1990-01-31, 1990-01-31T14:30, or with the
clock's offset from UTC, 1990-01-31T14:30-05:00. Any page can then use:

    I am {{age-hours}} hours old.

The number is worked out in the visitor's browser on every visit, to four
significant figures (age-figures) in scientific notation. The build also writes in the value
as of build day, for the rare browser that runs no JavaScript.
"""

import html
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
OUT = ROOT / "docs"
ASSETS = ROOT / "assets"

sys.path.insert(0, str(ROOT / "tools"))
import markdown2  # noqa: E402

MD_EXTRAS = ["fenced-code-blocks", "tables", "footnotes", "strike", "smarty-pants", "header-ids", "cuddled-lists"]
MATS = ("slate", "moss", "tan", "indigo", "plum")
esc = html.escape


# ---- reading ---------------------------------------------------------------

def read(path):
    """A file's settings and its Markdown. Settings are plain `key: value`
    lines; the value is everything after the FIRST colon, so a web address
    survives."""
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        head, sep, rest = text[3:].partition("\n---")
        if sep:
            body = rest.split("\n", 1)[1] if "\n" in rest else ""
            for line in head.splitlines():
                key, colon, value = line.partition(":")
                if colon and key.strip():
                    meta[key.strip().lower()] = value.strip()
    return meta, body.strip()


def title_from(stem):
    return stem.replace("-", " ").replace("_", " ").strip().capitalize()


def number(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_date(value, where):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        sys.exit(f"{where}: date must look like 2026-10-04, not '{value}'")


def nice_date(d):
    return f"{d.strftime('%B')} {d.day}, {d.year}"


BORN = ""  # set from content/home.md when the build starts
FIGURES = 4


def age_hours(born):
    """The {{age-hours}} tag: a span the script in site.js keeps current."""
    if not born:
        return '<span class="slot" style="display:inline">add born: to content/home.md</span>'
    try:
        start = datetime.fromisoformat(born)
    except ValueError:
        sys.exit(f"content/home.md: born must look like 1990-01-31 or 1990-01-31T14:30, not '{born}'")
    now = datetime.now(start.tzinfo) if start.tzinfo else datetime.now()
    hours = (now - start).total_seconds() / 3600
    mantissa, exponent = f"{hours:.{FIGURES - 1}e}".split("e")
    return (f'<span class="age" data-born="{esc(born, quote=True)}" data-figures="{FIGURES}">'
            f'{mantissa} &times; 10<sup>{int(exponent)}</sup></span>')


def to_html(markdown):
    # After conversion, not before: smarty-pants would curl the quotes in the tag.
    return markdown2.markdown(markdown, extras=MD_EXTRAS).replace("{{age-hours}}", age_hours(BORN))


def inline(text):
    """One line of Markdown, without the paragraph round it."""
    out = markdown2.markdown(text, extras=["smarty-pants"]).strip()
    return out[3:-4] if out.startswith("<p>") and out.endswith("</p>") else out


PUBS = []      # every reference in the CV's publications section
CV_HREF = ""   # where the CV page is, from the top of the site


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_pub(line):
    """Year, title and journal out of one reference line, as typed in cv.md:
    Authors. 2021. Title. ***Journal***, 127: 135-144."""
    m = re.search(r"\.\s(\d{4})\.\s+(.+?)\s+\*\*\*(.+?)\*\*\*", line)
    if not m:
        return None
    year, title, journal = m.group(1), m.group(2).rstrip(". "), m.group(3)
    words = re.sub(r"[*_]", "", title)
    return {"year": year, "title": title, "journal": journal, "plain": words,
            "id": f"pub-{year}-" + slugify(" ".join(words.split()[:5]))}


def render_cv(text):
    """A CV: sections, groups, and entries whose lines stay as typed, with an
    optional date at the right-hand edge after ` | `."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    out, section, anchor = [], "", ""
    for block in re.split(r"\n\s*\n", text.strip()):
        entry, anchor = [], ""
        for line in (l.strip() for l in block.splitlines()):
            if not line:
                continue
            if line.startswith("## ") or line.startswith("### "):
                level = 2 if line.startswith("## ") else 3
                if level == 2:
                    section = line[3:]
                out.append(f"<h{level}>{inline(line[level + 1:])}</h{level}>")
                continue
            if "publications" in section.lower() and not entry:
                pub = parse_pub(line)
                if pub:
                    anchor = f' id="{pub["id"]}"'
                    if not any(q["id"] == pub["id"] for q in PUBS):
                        PUBS.append(pub)
            words, bar, when = line.rpartition(" | ")
            if not bar:
                words, when = line, ""
            right = f'<span class="cv-when">{inline(when)}</span>' if when else ""
            entry.append(f'<div class="cv-line"><span class="cv-what">{inline(words)}</span>{right}</div>')
        if entry:
            solo = " solo" if len(entry) == 1 else ""
            out.append(f'<div class="cv-entry{solo}"{anchor}>{"".join(entry)}</div>')
    return "\n".join(out)


def papers_aside(spec, where, root):
    """The sidebar: each named paper as a document tile that opens its CV entry."""
    tiles = []
    for words in (w.strip() for w in spec.split("|")):
        if not words:
            continue
        hits = [q for q in PUBS if words.lower() in q["plain"].lower()]
        if len(hits) != 1:
            found = "nothing" if not hits else f"{len(hits)} papers"
            sys.exit(f'{where}: papers: "{words}" matches {found} in the CV; use more words from the title')
        q = hits[0]
        tiles.append(
            f'<a class="file" href="{root}{CV_HREF}#{q["id"]}"><span class="fileMark"></span>'
            f'<span class="fileKind">Paper · {q["year"]}</span>'
            f'<span class="fileName">{inline(q["title"])}</span>'
            f'<span class="fileWhere">{inline("*" + q["journal"] + "*")}</span></a>')
    return ('<aside class="side"><section class="mat mc-slate"><h2 class="tab">Papers</h2>'
            f'<div class="files">{"".join(tiles)}</div></section></aside>')


def plain(title):
    """A title as plain text, for the browser tab."""
    return esc(title.replace("*", ""))


def with_doors(body, section, root):
    """Turn {{door: slug}} lines into doors and {{todo: ...}} into notes."""
    by_slug = {p["slug"]: p for p in section["pages"]}

    def one(slug):
        slug = slug.strip()
        if slug not in by_slug:
            sys.exit(f'{{{{door: {slug}}}}}: no page called {slug}.md in content/{section["slug"]}/')
        return door(by_slug[slug], section, root)

    def row(m):
        return '<div class="doors">' + "".join(one(x) for x in re.findall(r"\{\{door:([^}]*)\}\}", m.group(0))) + "</div>"

    body = re.sub(r"<p>\s*(?:\{\{door:[^}]*\}\}\s*)+</p>", row, body)
    body = re.sub(r"\{\{door:([^}]*)\}\}", lambda m: one(m.group(1)), body)
    return re.sub(r"\{\{todo:\s*(.*?)\}\}", r'<span class="slot">\1</span>', body)


def slot(message):
    """What an empty page shows instead of nothing, so it says how to fill it."""
    return f'<span class="slot">{esc(message)}</span>'


def load():
    sections = []
    for folder in sorted(p for p in CONTENT.iterdir() if p.is_dir()):
        index = folder / "index.md"
        meta, body = read(index) if index.exists() else ({}, "")
        mat = meta.get("mat", "slate")
        if mat not in MATS:
            sys.exit(f"{index}: mat must be one of {', '.join(MATS)}, not '{mat}'")
        pages = []
        for f in sorted(folder.glob("*.md")):
            if f.name == "index.md":
                continue
            m, b = read(f)
            if m.get("draft", "").lower() in ("yes", "true"):
                continue
            pages.append({
                "slug": f.stem,
                "src": f.relative_to(ROOT),
                "title": m.get("title") or title_from(f.stem),
                "order": number(m.get("order"), 100),
                "date": parse_date(m.get("date"), f),
                "note": m.get("note", ""),
                "link": m.get("link", ""),
                "layout": m.get("layout", ""),
                "pdf": m.get("pdf", ""),
                "parent": m.get("parent", ""),
                "papers": m.get("papers", ""),
                "body": b,
            })
        slugs = {p["slug"] for p in pages}
        for p in pages:
            if p["parent"] and p["parent"] not in slugs:
                sys.exit(f'{p["src"]}: parent "{p["parent"]}" is not a page in content/{folder.name}/')
        dated = any(p["date"] for p in pages)
        if dated:
            pages.sort(key=lambda p: p["date"] or date.min, reverse=True)
        else:
            pages.sort(key=lambda p: (p["order"], p["title"].lower()))
        sections.append({
            "slug": folder.name,
            "src": index.relative_to(ROOT),
            "title": meta.get("title") or title_from(folder.name),
            "order": number(meta.get("order"), 100),
            "mat": mat,
            "has_page": meta.get("page", "yes").lower() not in ("no", "false"),
            "show": number(meta.get("show"), 0),
            "more": meta.get("more", ""),
            "dated": dated,
            "body": body,
            "pages": pages,
            "top": [p for p in pages if not p["parent"]],
        })
    sections.sort(key=lambda s: (s["order"], s["title"].lower()))
    return sections


# ---- drawing ---------------------------------------------------------------

def door(page, section, root):
    """A door, as seen from a page whose way back to the top is `root`."""
    if page["link"]:
        href = esc(page["link"], quote=True)
    else:
        href = f'{root}{section["slug"]}/{page["slug"]}.html'
    small = page["note"] or (nice_date(page["date"]) if page["date"] else "")
    degree = f'<span class="degree">{esc(small)}</span>' if small else ""
    return f'<a class="door" href="{href}"><span class="name">{inline(page["title"])}</span>{degree}</a>'


def crumb(label, href=None, home=False):
    cls = "crumb home" if home else "crumb"
    label = esc(label) if home else inline(label)
    if href:
        return f'<a class="{cls}" href="{href}">{label}</a>'
    return f'<span class="{cls}">{label}</span>'


SEP = '<span class="sep"></span>'


def render(template, **parts):
    out = template
    for key, value in parts.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build():
    template = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    global BORN, FIGURES
    home_meta, home_body = read(CONTENT / "home.md")
    BORN = home_meta.get("born", "")
    FIGURES = number(home_meta.get("age-figures"), 4)
    site_name = home_meta.get("title", "Home")
    sections = load()
    global CV_HREF
    for sec in sections:
        for q in sec["pages"]:
            if q["layout"] == "cv" and q["body"]:
                CV_HREF = f'{sec["slug"]}/{q["slug"]}.html'
                render_cv(q["body"])

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / ".nojekyll").write_text("")
    shutil.copytree(ASSETS, OUT / "assets", ignore=shutil.ignore_patterns(".DS_Store"))

    # -- the home board -------------------------------------------------------
    kicker = home_meta.get("kicker", "")
    note = ['<section class="note p-note"><span class="pin"></span>']
    if kicker:
        note.append(f'<div class="kicker">{esc(kicker)}</div>')
    note.append(f"<h1>{esc(site_name)}</h1>")
    if home_meta.get("subtitle"):
        lines = [esc(x.strip()) for x in home_meta["subtitle"].split("|")]
        note.append(f'<p class="subtitle">{"<br>".join(lines)}</p>')
    note.append(to_html(home_body) if home_body else slot("Nothing written yet. Write in content/home.md"))
    note.append("</section>")
    main = ['<main class="board">', "".join(note)]
    if home_meta.get("photo"):
        main.append(f'<img class="photo p-photo" alt="" src="assets/{esc(home_meta["photo"], quote=True)}">')

    for s in sections:
        href = f'{s["slug"]}/index.html'
        tab = (f'<a class="tab" href="{href}">{esc(s["title"])}</a>' if s["has_page"]
               else f'<span class="tab">{esc(s["title"])}</span>')
        shown = s["top"][: s["show"]] if s["show"] else s["top"]
        doors = [door(p, s, "") for p in shown]
        if s["has_page"] and s["more"] and len(s["top"]) > len(shown):
            doors.append(f'<a class="door" href="{href}"><span class="name">{esc(s["more"])}</span></a>')
        inside = (f'<div class="doors">{"".join(doors)}</div>' if doors
                  else slot(f'Nothing here yet. Add a file to content/{s["slug"]}/'))
        main.append(f'<section class="mat mc-{s["mat"]} p-{s["slug"]}">{tab}{inside}</section>')
    main.append("</main>")
    write(OUT / "index.html", render(template, head_title=esc(site_name), site_name=esc(site_name), root="",
                                     body_class="", trail=crumb("Home", home=True), main="\n".join(main)))
    count = 1

    # -- section pages and the pages behind their doors -----------------------
    for s in sections:
        folder = OUT / s["slug"]
        for f in (CONTENT / s["slug"]).rglob("*"):  # pictures and the like ride along
            if f.is_file() and f.suffix != ".md" and f.name != ".DS_Store":
                target = folder / f.relative_to(CONTENT / s["slug"])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)

        if s["has_page"]:
            body = with_doors(to_html(s["body"]), s, "../") if s["body"] else slot(f'Nothing written yet. Write in {s["src"]}')
            main = [f'<main class="page"><article class="note long"><h1>{esc(s["title"])}</h1>{body}</article>']
            if s["top"] and s["dated"]:
                rows = "".join(
                    f'<li><span class="when">{esc(nice_date(p["date"])) if p["date"] else ""}</span>'
                    f'<a class="what" href="{esc(p["link"], quote=True) if p["link"] else p["slug"] + ".html"}">'
                    f'{inline(p["title"])}</a></li>' for p in s["top"])
                main.append(f'<section class="mat"><div class="note"><ul class="rows">{rows}</ul></div></section>')
            elif s["top"]:
                doors = "".join(door(p, s, "../") for p in s["top"])
                main.append(f'<section class="mat"><div class="doors">{doors}</div></section>')
            main.append("</main>")
            trail = crumb("Home", "../index.html", home=True) + SEP + crumb(s["title"])
            write(folder / "index.html", render(
                template, head_title=esc(f'{s["title"]} · {site_name}'), site_name=esc(site_name), root="../",
                body_class=f'mc-{s["mat"]}', trail=trail, main="\n".join(main)))
            count += 1

        for p in s["pages"]:
            if p["link"]:
                continue
            when = f'<div class="kicker">{esc(nice_date(p["date"]))}</div>' if p["date"] else ""
            if not p["body"]:
                body = slot(f'Nothing written yet. Write in {p["src"]}')
            elif p["layout"] == "cv":
                body = render_cv(p["body"])
            else:
                body = with_doors(to_html(p["body"]), s, "../")
            kind = " cv" if p["layout"] == "cv" else ""
            if p["pdf"] and (CONTENT / s["slug"] / p["pdf"]).exists():
                href = esc(p["pdf"], quote=True)
                body = f'<p class="download"><a class="btn" href="{href}">Download PDF</a></p>' + body
            side = papers_aside(p["papers"], p["src"], "../") if p["papers"] else ""
            wide = " has-side" if side else ""
            main = (f'<main class="page{wide}"><article class="note long{kind}">{when}<h1>{inline(p["title"])}</h1>'
                    f'{body}</article>{side}</main>')
            trail = crumb("Home", "../index.html", home=True) + SEP
            if s["has_page"]:
                trail += crumb(s["title"], "index.html") + SEP
            chain, up = [], p["parent"]
            by_slug = {q["slug"]: q for q in s["pages"]}
            while up and len(chain) < 10:
                chain.insert(0, by_slug[up])
                up = by_slug[up]["parent"]
            for q in chain:
                trail += crumb(q["title"], q["slug"] + ".html") + SEP
            trail += crumb(p["title"])
            write(folder / f'{p["slug"]}.html', render(
                template, head_title=f'{plain(p["title"])} · {esc(site_name)}', site_name=esc(site_name), root="../",
                body_class=f'mc-{s["mat"]}', trail=trail, main=main))
            count += 1

    print(f"Built {count} pages into docs/. Open docs/index.html to look.")


if __name__ == "__main__":
    build()
