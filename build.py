"""Build index.html and the résumés from content.toml.

    python build.py

Writes index.html (from site.template.html). Then, for each [[resumes]] target in
content.toml, writes resume/content-<file>.tex and, if the local résumé source
resume/resume.tex exists, compiles resume/<file>.pdf and checks it is one page.
Stdlib only (Python 3.11+).
"""
import html
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent
RESUME = ROOT / "resume"


def fallbacks(medium):
    # A résumé target like "resume-eng" falls back to "resume", then "text".
    return [medium, "resume", "text"] if medium.startswith("resume-") else [medium, "text"]


def pick(v, medium):
    """Resolve a value for one medium: variant tables -> that medium's text (None = hidden)."""
    if isinstance(v, dict):
        v = next((v[k] for k in fallbacks(medium) if k in v), None)
    if isinstance(v, str):
        return " ".join(v.split())
    return v


def shown(entries, medium):
    # `on` may list "site", "resume" (every résumé target), or a specific target id.
    def on(e):
        o = e.get("on", ["site", "resume"])
        return medium in o or (medium.startswith("resume-") and "resume" in o)
    return [e for e in entries if on(e)]


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

    # Research entries render as cards ahead of the projects, tagged "Research".
    research = [dict(r, category=r.get("category", "Research")) for r in c.get("research", [])]
    cards = []
    for p in shown(research, S) + shown(c["projects"], S):
        tags = [f'<span class="tag highlight">{h(p["category"])}</span>'] + [
            f'<span class="tag">{h(t)}</span>'
            for t in texts([p.get("stack"), p.get("course"), p.get("date")], S)]
        metrics = "\n".join(
            f"            <li><strong>{h(m['value'])}</strong>{h(m['label'])}</li>"
            for m in p.get("metrics", []))
        if metrics:
            metrics = f'\n          <ul class="project-metrics">\n{metrics}\n          </ul>'
        link = p.get("link")
        open_tag = (f'<a class="project-card" href="{html.escape(link)}" target="_blank">'
                    if link else '<div class="project-card">')
        # "GitHub ↗" affordance; the arrow icon comes from the sprite in site.template.html
        label = "GitHub" if link and "github.com" in link else "View"
        arrow = (f'\n        <span class="project-link" aria-hidden="true">{label}'
                 '<svg class="icon"><use href="#i-arrow" /></svg></span>') if link else ""
        cards.append(f"""      {open_tag}
        <div class="project-body">
          <div class="project-tags">
            {''.join(tags)}
          </div>
          <h3 class="project-title">{h(pick(p['name'], S))}</h3>
          <p class="project-desc">{h(pick(p['desc'], S))}</p>{metrics}
        </div>{arrow}
      {'</a>' if link else '</div>'}""")
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


def item_name(p, R):
    # Bold name; a hyperlink when the entry has `link` (needs hyperref in resume.tex).
    name = rf"\textbf{{{t(pick(p['name'], R))}}}"
    return rf"\href{{{p['link']}}}{{{name}}}" if p.get("link") else name


def sect_summary(c, R):
    return [r"\sect{SUMMARY}", t(pick(c["summary"], R))]


def sect_education(c, R):
    SEP = r"\sep "
    L = [r"\sect{EDUCATION}"]
    for e in c["education"]:
        L.append(rf"\entry{{{t(e['school'])}}}{{{t(e['location'])}}}{{{t(e['date'])}}}")
        L.append(SEP.join(t(x) for x in [e["degree"]] + texts(e["details"], R)))
        if cw := pick(e.get("coursework"), R):
            L.append(r"\par Coursework: " + t(cw))
    return L


def sect_research(c, R):
    L = [r"\sect{RESEARCH}", r"\begin{itemize}[itemsep=2.52bp]"]
    for p in shown(c.get("research", []), R):
        d = pick(p.get("date"), R)
        date = f" ({t(d)})" if d else ""
        L.append(rf"  \item {item_name(p, R)}{date} — " + t(pick(p["desc"], R)))
    return L + [r"\end{itemize}"]


def sect_experience(c, R):
    L = [r"\sect{EXPERIENCE}"]
    for j in shown(c["experience"], R):
        L.append(rf"\entry{{{t(j['title'])}, {t(j['org'])}}}{{{t(j['location'])}}}"
                 rf"{{{t(j['start'])} – {t(j['end'])}}}")
        if items := texts(j["bullets"], R):  # a job can show with no bullets on a target
            L += [r"\begin{itemize}"] + [rf"  \item {t(b)}" for b in items] + [r"\end{itemize}"]
    return L


def sect_projects(c, R):
    L = [r"\sect{PROJECTS}", r"\begin{itemize}[itemsep=2.52bp]"]
    for p in shown(c["projects"], R):
        stack = pick(p.get("stack"), R)
        L.append(rf"  \item {item_name(p, R)} — " + (f"{t(stack)}. " if stack else "")
                 + t(pick(p["desc"], R)))
    return L + [r"\end{itemize}"]


def sect_skills(c, R):
    SEP = r"\sep "
    L = [r"\sect{TECHNICAL SKILLS}"]
    for s in shown(c["skills"], R):
        line = rf"\textbf{{{t(pick(s['label'], R))}}}~~" + t(", ".join(texts(s["items"], R)))
        if s.get("familiar"):
            line += SEP + "Familiar with: " + t(", ".join(s["familiar"]))
        L.append(line + r"\par")
    return L


def sect_honors(c, R):
    L = [r"\sect{LEADERSHIP \& AWARDS}", r"\begin{itemize}[itemsep=2.52bp]"]
    for x in shown(c["honors"], R):
        line = rf"  \item \textbf{{{t(x['title'])}}}, {t(x['org'])}"
        if x.get("date"):
            line += f" ({t(x['date'])})"
        if note := pick(x.get("note"), R):
            line += f" — {t(note)}"
        L.append(line + ".")
    return L + [r"\end{itemize}"]


SECTIONS = {"summary": sect_summary, "education": sect_education, "research": sect_research,
            "experience": sect_experience, "projects": sect_projects, "skills": sect_skills,
            "honors": sect_honors}


def build_resume(c, target):
    R, file = target["id"], target["file"]
    L = [f"% GENERATED from content.toml by build.py (target {R}) -- do not edit", ""]
    for name in target["sections"]:
        L += SECTIONS[name](c, R) + [""]
    tex = "\n".join(L) + "\n"
    (RESUME / f"content-{file}.tex").write_text(tex, encoding="utf-8", newline="\n")

    if not (RESUME / "resume.tex").exists():
        print(f"resume/resume.tex not found (it's local-only); skipped {file}.pdf")
        return
    # resume.tex does \input{content}; point it at this target, then compile under its name.
    shutil.copyfile(RESUME / f"content-{file}.tex", RESUME / "content.tex")
    subprocess.run(["latexmk", "-xelatex", "-cd", "-quiet", "-g", f"-jobname={file}",
                    "resume/resume.tex"], cwd=ROOT, check=True)
    log = (RESUME / f"{file}.log").read_text(encoding="utf-8", errors="replace")
    pages = re.search(r"Output written on \S+ \((\d+) page", log)
    if not pages or pages.group(1) != "1":
        sys.exit(f"{file}.pdf is {pages.group(1) if pages else '?'} pages, must be 1 — trim content.toml")


if __name__ == "__main__":
    content = tomllib.loads((ROOT / "content.toml").read_text(encoding="utf-8"))
    build_site(content)
    for target in content["resumes"]:
        build_resume(content, target)
    print("built index.html and " + ", ".join(f"resume/{r['file']}.pdf" for r in content["resumes"]))
