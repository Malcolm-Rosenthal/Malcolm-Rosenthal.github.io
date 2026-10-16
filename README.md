# malcolm-rosenthal.github.io

A hand-built site: plain HTML and CSS, no Quarto, no Jekyll.

## Writing

Everything you write lives in `content/`. Each folder is a mat on the home
board; each `.md` file in it is a door, with a page behind it.

    content/home.md              the note on the home board
    content/research/index.md    the Research page itself
    content/research/talks.md    a door on the Research mat

A file starts with a few settings between two `---` lines, then Markdown:

    ---
    title: A post about spiders
    date: 2026-10-04
    ---

    The text, in Markdown.

- A new blog post is a new file in `content/blog/` with a `date`.
- A new door is a new file in that section's folder. `order: 2` places it.
- A new mat is a new folder with an `index.md` in it.
- A picture goes in the same folder as the page that uses it:
  `![what it shows](spider.jpg)`.
- `draft: yes` keeps a file off the site.
- `link: https://...` makes a door that goes straight to another site.

The full list of settings is at the top of `build.py`.

## Building

    python3 build.py

This rebuilds the whole site into `docs/`. Open `docs/index.html` to look at
it. Never edit `docs/` by hand: it is wiped on every build.

## Where things are

    content/     your words
    assets/      the stylesheet (site.css), the style switch (site.js), images
    templates/   the frame every page is poured into
    tools/       the Markdown converter (markdown2, MIT licence), one file
    build.py     the script that turns content/ into docs/
    docs/        the built site, which is what GitHub serves
