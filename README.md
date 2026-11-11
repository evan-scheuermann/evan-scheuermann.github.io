# evan-scheuermann.github.io

Personal portfolio site, served by GitHub Pages at <https://evan-scheuermann.github.io>.
It's a single static page with no build step.

| Path | What it is |
| --- | --- |
| `index.html` | The whole site: markup and inline CSS (fonts from Google Fonts) |
| `headshot.jpg`, `favicon.svg`, `apple-touch-icon.png` | Image assets |
| `resume/resume.pdf` | Résumé, linked from the site's nav, hero and footer |

## Résumé

`resume/` is the résumé workspace. **Only `resume/resume.pdf` is committed.** Everything
else there (the LaTeX source `resume.tex`, build files, and `resume-archive/` with
older versions and notes) is gitignored on purpose and stays local.

To update the résumé:

1. Edit `resume/resume.tex`.
2. Build it (from the repo root; `-cd` makes latexmk work inside `resume/`):
   ```sh
   latexmk -xelatex -cd resume/resume.tex   # writes resume/resume.pdf
   latexmk -c -cd resume/resume.tex         # optional: clean up aux/log files
   ```
   This needs XeLaTeX (for example TinyTeX or TeX Live) and the Arial system font.
   The source is tuned to match the original Word layout line for line.
3. Commit `resume/resume.pdf`.
