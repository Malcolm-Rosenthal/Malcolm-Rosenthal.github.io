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

Settings a SECTION's index.md understands, as well as title and order:
    mat     slate, moss, tan, indigo or plum
    page    no: the section has no page of its own, only a mat (Elsewhere)
    show    how many doors the home board shows before the "more" door
    more    the name of that "more" door, which leads to the section page

Settings home.md understands: title, kicker, photo (a path inside assets/).
"""

import html
import shutil
import sys
from datetime import date
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


def to_html(markdown):
    return markdown2.markdown(markdown, extras=MD_EXTRAS)


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
                "body": b,
            })
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
    return f'<a class="door" href="{href}"><span class="name">{esc(page["title"])}</span>{degree}</a>'


def crumb(label, href=None, home=False):
    cls = "crumb home" if home else "crumb"
    if href:
        return f'<a class="{cls}" href="{href}">{esc(label)}</a>'
    return f'<span class="{cls}">{esc(label)}</span>'


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
    home_meta, home_body = read(CONTENT / "home.md")
    site_name = home_meta.get("title", "Home")
    sections = load()

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
    note.append(to_html(home_body) if home_body else slot("Nothing written yet. Write in content/home.md"))
    note.append("</section>")
    main = ['<main class="board">', "".join(note)]
    if home_meta.get("photo"):
        main.append(f'<img class="photo p-photo" alt="" src="assets/{esc(home_meta["photo"], quote=True)}">')

    for s in sections:
        href = f'{s["slug"]}/index.html'
        tab = (f'<a class="tab" href="{href}">{esc(s["title"])}</a>' if s["has_page"]
               else f'<span class="tab">{esc(s["title"])}</span>')
        shown = s["pages"][: s["show"]] if s["show"] else s["pages"]
        doors = [door(p, s, "") for p in shown]
        if s["has_page"] and s["more"] and len(s["pages"]) > len(shown):
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
            body = to_html(s["body"]) if s["body"] else slot(f'Nothing written yet. Write in {s["src"]}')
            main = [f'<main class="page"><article class="note long"><h1>{esc(s["title"])}</h1>{body}</article>']
            if s["pages"] and s["dated"]:
                rows = "".join(
                    f'<li><span class="when">{esc(nice_date(p["date"])) if p["date"] else ""}</span>'
                    f'<a class="what" href="{esc(p["link"], quote=True) if p["link"] else p["slug"] + ".html"}">'
                    f'{esc(p["title"])}</a></li>' for p in s["pages"])
                main.append(f'<section class="mat"><div class="note"><ul class="rows">{rows}</ul></div></section>')
            elif s["pages"]:
                doors = "".join(door(p, s, "../") for p in s["pages"])
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
            body = to_html(p["body"]) if p["body"] else slot(f'Nothing written yet. Write in {p["src"]}')
            main = (f'<main class="page"><article class="note long">{when}<h1>{esc(p["title"])}</h1>'
                    f'{body}</article></main>')
            trail = crumb("Home", "../index.html", home=True) + SEP
            if s["has_page"]:
                trail += crumb(s["title"], "index.html") + SEP
            trail += crumb(p["title"])
            write(folder / f'{p["slug"]}.html', render(
                template, head_title=esc(f'{p["title"]} · {site_name}'), site_name=esc(site_name), root="../",
                body_class=f'mc-{s["mat"]}', trail=trail, main=main))
            count += 1

    print(f"Built {count} pages into docs/. Open docs/index.html to look.")


if __name__ == "__main__":
    build()
