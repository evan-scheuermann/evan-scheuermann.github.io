# evan-scheuermann.github.io

Personal portfolio site, served by GitHub Pages at <https://evan-scheuermann.github.io>.
GitHub Pages serves the committed files as-is. The site and the résumé are both generated
locally from one content file.

| Path | What it is |
| --- | --- |
| `content.toml` | **Source of truth** for the site and every résumé variant. **Gitignored; kept local only.** |
| `build.py` | Generates `index.html` and one PDF per `[[resumes]]` target from `content.toml` (Python 3.11+, stdlib only) |
| `site.template.html` | Site layout: markup, inline CSS, nav/hero/footer, with `{{markers}}` where content goes |
| `index.html` | **Generated.** Don't edit it directly; it's committed because Pages serves it |
| `headshot.jpg`, `favicon.svg`, `apple-touch-icon.png` | Image assets |
| `resume/resume.pdf` | Generated engineering résumé (target `resume-eng`), linked from the site's nav, hero and footer. Other targets (e.g. `resume-med.pdf`) build locally and are not committed |

## Updating content

1. Edit `content.toml`. Conventions are in the comments at the top of the file. In short:
   - Any text can be one string (used on both) or `{ site = "...", resume = "..." }` when the
     two need different wording. Give only one of the two keys to show it in one place only.
   - Whole entries take `on = ["site"]` or `on = ["resume"]` to appear in just one.
   - The résumé is denser and has to fit on one page, so its wording usually differs.
2. Run `python build.py` from the repo root. It writes `index.html`, then for each `[[resumes]]`
   target writes `resume/content-<file>.tex`, compiles `resume/<file>.pdf`, and fails if any
   résumé runs past one page.
3. Commit `index.html` and `resume/resume.pdf` (not `content.toml`, which is gitignored).

Layout changes go in `site.template.html` (site) or `resume/resume.tex` (résumé), followed by
a rebuild. To rebuild only the site without recompiling the PDFs:
`python -c "import tomllib,build; build.build_site(tomllib.loads(open('content.toml',encoding='utf-8').read()))"`

## Theme

The site has a Light / Dark / System toggle in the nav, defaulting to System. Everything
lives in `site.template.html`:

- Colors are CSS variables. Dark is the base `:root`, and the light palette appears twice:
  once under `prefers-color-scheme: light` (System mode) and once under
  `:root[data-theme="light"]`. Keep the two blocks identical.
- A tiny script in `<head>` applies a saved choice before first paint. The script at the end of
  `<body>` runs the toggle and highlights the nav link for the section in view.
- The choice is saved in `localStorage` under `theme` (`light` or `dark`). No key means System.
- Icons are an inline Lucide SVG sprite at the top of `<body>`. `build.py` uses `#i-arrow` from it.

## Résumé

`resume/` is the résumé workspace. **Only `resume/resume.pdf` is committed.** Everything
else there is gitignored on purpose and stays local: the LaTeX source `resume.tex` (layout,
macros, and the contact header with the phone number), the generated `content.tex`, build
files, and `resume-archive/` with older versions and notes.

`resume.tex` holds only the layout and header and pulls in `content.tex` with `\input`. The
PDF build needs XeLaTeX and latexmk (for example TinyTeX or TeX Live) plus the Arial system
font; the source is tuned to match the original Word layout line for line. On a fresh clone
without `resume.tex`, `build.py` still regenerates the site and skips the PDF.

To clean up LaTeX aux/log files: `latexmk -c -cd resume/resume.tex`.
