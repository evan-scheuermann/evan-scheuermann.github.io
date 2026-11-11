"""Build index.html and the résumé from content.toml.

    python build.py

Writes index.html (from site.template.html) and resume/content.tex, then, if the local
résumé source resume/resume.tex exists, compiles resume/resume.pdf and checks it is one page.
Stdlib only (Python 3.11+).
"""
import html
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent
RESUME = ROOT / "resume"


def pick(v, medium):
    """Resolve a value for one medium: variant tables -> that medium's text (None = hidden)."""
    if isinstance(v, dict):
        v = v.get(medium, v.get("text"))
    if isinstance(v, str):
        return " ".join(v.split())
    return v


def shown(entries, medium):
    return [e for e in entries if medium in e.get("on", ["site", "resume"])]


def texts(values, medium):
    return [t for t in (pick(v, medium) for v in values) if t]


# ------------------------------------------------------------------ site

def h(s):
    return html.escape(s, quote=False)


def site_dates(start, end):
    # "May 2026" – "Aug 2026" -> "May – Aug 2026"
    if start[-4:] == end[-4:] and start[-4:].isdigit():
        start = start[:-5]
    return f"{start} – {end}"


def build_site(c):
    S = "site"
    out = {"summary": h(pick(c["summary"], S))}
    out["about"] = "\n".join(f"      <p>{h(pick(p, S))}</p>" for p in c["about"])

    out["education"] = "\n".join(
        f"""          <li>
            <strong>{h(e['school'])}</strong>
            <span>{h(e['degree'])}</span>
            <span>{h(' · '.join(texts(e['details'], S) + ([e['date']] if e['date'] else [])))}</span>
          </li>""" for e in c["education"])

    out["honors"] = "\n".join(
        f"""          <li>
            <strong>{h(x['title'])}</strong>
            <span>{h(' · '.join(texts([x.get('org'), x.get('date'), x.get('note')], S)))}</span>
          </li>""" for x in shown(c["honors"], S))

    jobs, earlier = [], []
    for j in shown(c["experience"], S):
        if j.get("brief"):
            yr = lambda d: d[-4:] if d[-4:].isdigit() else d  # "Nov 2024" -> "2024"; "Present" stays
            earlier.append(f"{h(j['title'])}, {h(j['org'])} ({yr(j['start'])}–{yr(j['end'])})")
            continue
        bullets = "\n".join(f"        <li>{h(b)}</li>" for b in texts(j["bullets"], S))
        jobs.append(f"""    <div class="job">
      <div class="job-head">
        <h3 class="job-title">{h(j['title'])}</h3>
        <span class="job-date">{site_dates(j['start'], j['end'])}</span>
      </div>
      <p class="job-org">{h(j['org'])} · {h(j['location'])}</p>
      <ul>
{bullets}
      </ul>
    </div>""")
    if earlier:
        joined = " ·\n      ".join(earlier)
        jobs.append(f'    <p class="job-earlier">\n      Earlier: {joined}\n    </p>')
    out["experience"] = "\n\n".join(jobs)

    cards = []
    for p in shown(c["projects"], S):
        tags = [f'<span class="tag highlight">{h(p["category"])}</span>'] + [
            f'<span class="tag">{h(t)}</span>' for t in texts([p.get("stack"), p.get("course")], S)]
        metrics = "\n".join(
            f"            <li><strong>{h(m['value'])}</strong>{h(m['label'])}</li>"
            for m in p.get("metrics", []))
        cards.append(f"""      <a class="project-card" href="{html.escape(p['link'])}" target="_blank">
        <div class="project-body">
          <div class="project-tags">
            {''.join(tags)}
          </div>
          <h3 class="project-title">{h(pick(p['name'], S))}</h3>
          <p class="project-desc">{h(pick(p['desc'], S))}</p>
          <ul class="project-metrics">
{metrics}
          </ul>
        </div>
        <span class="project-arrow" aria-hidden="true">↗</span>
      </a>""")
    out["projects"] = "\n\n".join(cards)

    rows = []
    for s in shown(c["skills"], S):
        text = ", ".join(texts(s["items"], S))
        if s.get("familiar"):
            text += "; familiar with " + " and ".join(s["familiar"])
        rows.append(f"      <dt>{h(pick(s['label'], S))}</dt>\n      <dd>{h(text)}</dd>")
    out["skills"] = "\n".join(rows)

    page = (ROOT / "site.template.html").read_text(encoding="utf-8")
    for key, val in out.items():
        page = page.replace("{{" + key + "}}", val)
    if leftover := re.findall(r"\{\{\w+\}\}", page):
        sys.exit(f"unfilled template markers: {leftover}")
    (ROOT / "index.html").write_text(page, encoding="utf-8", newline="\n")


# ------------------------------------------------------------------ résumé

TEX_ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
           "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\^{}"}


def t(s):
    return "".join(TEX_ESC.get(ch, ch) for ch in s)


def build_resume(c):
    R = "resume"
    SEP = r"\sep "
    L = ["% GENERATED from content.toml by build.py -- do not edit", ""]

    L += [r"\sect{SUMMARY}", t(pick(c["summary"], R)), "", r"\sect{EDUCATION}"]
    for e in c["education"]:
        L.append(rf"\entry{{{t(e['school'])}}}{{{t(e['location'])}}}{{{t(e['date'])}}}")
        L.append(SEP.join(t(x) for x in [e["degree"]] + texts(e["details"], R)))

    L += ["", r"\sect{TECHNICAL SKILLS}"]
    for s in shown(c["skills"], R):
        line = rf"\textbf{{{t(pick(s['label'], R))}}}~~" + t(", ".join(texts(s["items"], R)))
        if s.get("familiar"):
            line += SEP + "Familiar with: " + t(", ".join(s["familiar"]))
        L.append(line + r"\par")

    L += ["", r"\sect{EXPERIENCE}"]
    for j in shown(c["experience"], R):
        L.append(rf"\entry{{{t(j['title'])}, {t(j['org'])}}}{{{t(j['location'])}}}"
                 rf"{{{t(j['start'])} – {t(j['end'])}}}")
        L.append(r"\begin{itemize}")
        L += [rf"  \item {t(b)}" for b in texts(j["bullets"], R)]
        L.append(r"\end{itemize}")

    L += ["", r"\sect{PROJECTS}", r"\begin{itemize}[itemsep=2.52bp]"]
    for p in shown(c["projects"], R):
        head = rf"  \item \textbf{{{t(pick(p['name'], R))}}} — "
        stack = pick(p.get("stack"), R)
        L.append(head + (f"{t(stack)}. " if stack else "") + t(pick(p["desc"], R)))
    L.append(r"\end{itemize}")

    L += ["", r"\sect{LEADERSHIP \& AWARDS}", r"\begin{itemize}[itemsep=2.52bp]"]
    for x in shown(c["honors"], R):
        line = rf"  \item \textbf{{{t(x['title'])}}}, {t(x['org'])}"
        if x.get("date"):
            line += f" ({t(x['date'])})"
        if note := pick(x.get("note"), R):
            line += f" — {t(note)}"
        L.append(line + ".")
    L.append(r"\end{itemize}")

    (RESUME / "content.tex").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")

    if not (RESUME / "resume.tex").exists():
        print("resume/resume.tex not found (it's local-only); skipped PDF build")
        return
    subprocess.run(["latexmk", "-xelatex", "-cd", "-quiet", "resume/resume.tex"],
                   cwd=ROOT, check=True)
    log = (RESUME / "resume.log").read_text(encoding="utf-8", errors="replace")
    pages = re.search(r"Output written on \S+ \((\d+) page", log)
    if not pages or pages.group(1) != "1":
        sys.exit(f"résumé is {pages.group(1) if pages else '?'} pages, must be 1 — trim content.toml")


if __name__ == "__main__":
    content = tomllib.loads((ROOT / "content.toml").read_text(encoding="utf-8"))
    build_site(content)
    build_resume(content)
    print("built index.html and resume/resume.pdf")
