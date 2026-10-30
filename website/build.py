"""Build the walkthrough site from one HTML fragment per topic."""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGES_DIR = ROOT / "pages"

FOOTER = """
<footer>
  <p>These pages open in a browser directly from the <code>website/</code> folder.
  After editing a fragment in <code>website/pages/</code>, regenerate them
  with <code>python website/build.py</code>.</p>
</footer>
""".strip()


@dataclass(frozen=True)
class Page:
    filename: str
    title: str
    group: str
    tour: int | None = None


PAGES: tuple[Page, ...] = (
    Page("index.html", "What relAI does", "Start here", 1),
    Page("install.html", "Install and first run", "Start here", 2),
    Page("how-a-run-works.html", "How a run works", "Start here", 3),
    Page("tasks-and-suites.html", "Tasks and suites", "Features", None),
    Page("trajectories.html", "Trajectories", "Features", None),
    Page("seeded-faults.html", "Seeded faults", "Features", 4),
    Page("failure-modes.html", "Failure modes", "Features", 5),
    Page("scores.html", "Scores", "Features", 6),
    Page("comparing-agents.html", "Comparing agents", "Features", None),
    Page("stress-and-sweeps.html", "Stress and sweeps", "Features", None),
    Page("reports.html", "Reports", "Features", None),
    Page("self-check.html", "Self-check", "Features", None),
    Page("agent-contract.html", "The agent contract", "Your agent", None),
    Page("plug-in-your-agent.html", "Plug in your agent", "Your agent", 7),
    Page("live-models.html", "Live models", "Your agent", None),
    Page("your-own-suite.html", "Your own suite", "Your agent", None),
    Page("glossary.html", "Glossary", "Glossary", 8),
)


def build_site(out_dir: Path | str) -> None:
    """Write one HTML page per topic, plus the shared stylesheet."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    css_src = ROOT / "site.css"
    css_dest = out / "site.css"
    if css_dest.resolve() != css_src.resolve():
        css_dest.write_text(css_src.read_text(encoding="utf-8"), encoding="utf-8")
    tour = [page for page in PAGES if page.tour is not None]
    for page in PAGES:
        body = (PAGES_DIR / page.filename).read_text(encoding="utf-8").strip()
        document = _document(page, body, tour)
        (out / page.filename).write_text(document, encoding="utf-8")


def main() -> None:
    build_site(ROOT)


def _document(page: Page, body: str, tour: list[Page]) -> str:
    title = html.escape(page.title)
    group = html.escape(page.group)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} · relAI</title>
  <link rel="stylesheet" href="site.css">
</head>
<body>
  <a class="skip" href="#content">Skip to content</a>
  {_top()}
  <div class="layout">
    {_sidebar(page)}
    <main id="content">
      <p class="kicker">{group}</p>
      {_tour_strip(page, tour)}
      <h1>{title}</h1>
      {body}
      {FOOTER}
    </main>
  </div>
</body>
</html>
"""


def _top() -> str:
    links: list[str] = []
    seen: set[str] = set()
    for page in PAGES:
        if page.group in seen:
            continue
        seen.add(page.group)
        links.append(f'<a href="{page.filename}">{html.escape(page.group)}</a>')
    joined = "".join(links)
    return (
        '<header class="top">'
        '<a class="brand" href="index.html">relAI <span>Documentation</span></a>'
        f'<nav class="topnav" aria-label="Sections">{joined}</nav>'
        "</header>"
    )


def _sidebar(current: Page) -> str:
    lines = ['<nav class="sidebar" aria-label="Documentation">']
    seen: list[str] = []
    for page in PAGES:
        if page.group not in seen:
            seen.append(page.group)
            lines.append(f'<p class="group">{html.escape(page.group)}</p>')
        current_attr = ' aria-current="page"' if page.filename == current.filename else ""
        number = f'<span class="stepnum">{page.tour}</span>' if page.tour else ""
        lines.append(
            '<div class="item">'
            f'<a href="{page.filename}"{current_attr}>{html.escape(page.title)}</a>'
            f"{number}</div>"
        )
    lines.append("</nav>")
    return "\n".join(lines)


def _tour_strip(page: Page, tour: list[Page]) -> str:
    if page.tour is None:
        return ""
    ordered = sorted(tour, key=lambda item: item.tour or 0)
    index = next(i for i, item in enumerate(ordered) if item.filename == page.filename)
    if index + 1 < len(ordered):
        following = ordered[index + 1]
        tail = f'<a href="{following.filename}">{html.escape(following.title)}</a>'
    else:
        tail = "<span>End of the tour</span>"
    return f'<p class="tour"><span>Step {page.tour} of {len(ordered)}</span>{tail}</p>'


if __name__ == "__main__":
    main()
