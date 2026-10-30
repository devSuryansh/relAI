"""The walkthrough site builds as a closed set of linked HTML pages."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from website.build import build_site  # noqa: E402

# filename, title, sidebar group, tour step (None when the page is library-only)
EXPECTED = [
    ("index.html", "What relAI does", "Start here", 1),
    ("install.html", "Install and first run", "Start here", 2),
    ("how-a-run-works.html", "How a run works", "Start here", 3),
    ("seeded-faults.html", "Seeded faults", "Features", 4),
    ("failure-modes.html", "Failure modes", "Features", 5),
    ("scores.html", "Scores", "Features", 6),
    ("plug-in-your-agent.html", "Plug in your agent", "Your agent", 7),
    ("glossary.html", "Glossary", "Glossary", 8),
    ("tasks-and-suites.html", "Tasks and suites", "Features", None),
    ("trajectories.html", "Trajectories", "Features", None),
    ("comparing-agents.html", "Comparing agents", "Features", None),
    ("stress-and-sweeps.html", "Stress and sweeps", "Features", None),
    ("reports.html", "Reports", "Features", None),
    ("self-check.html", "Self-check", "Features", None),
    ("agent-contract.html", "The agent contract", "Your agent", None),
    ("live-models.html", "Live models", "Your agent", None),
    ("your-own-suite.html", "Your own suite", "Your agent", None),
]

BLOCKS = [
    "Definition",
    "Why this helps you",
    "Try this",
    "What you should see",
    "How to read it",
    "Easy to mix up",
    "Next",
]


def _pages(out: Path) -> dict[str, str]:
    build_site(out)
    return {name: (out / name).read_text(encoding="utf-8") for name, *_ in EXPECTED}


def test_build_writes_every_page(tmp_path: Path) -> None:
    texts = _pages(tmp_path)
    assert (tmp_path / "site.css").is_file()
    for name, title, _group, _step in EXPECTED:
        assert f"<h1>{title}</h1>" in texts[name]
        assert f"<title>{title} · relAI</title>" in texts[name]
        assert 'href="site.css"' in texts[name]


def test_sidebar_lists_every_page_and_marks_the_current_one(tmp_path: Path) -> None:
    texts = _pages(tmp_path)
    for name, title, group, _step in EXPECTED:
        page = texts[name]
        assert f'<a href="{name}" aria-current="page">{title}</a>' in page
        assert f'class="group">{group}</p>' in page or f">{group}</p>" in page
        for other, other_title, _other_group, _other_step in EXPECTED:
            assert f'href="{other}"' in page
            assert other_title in page


def test_internal_links_resolve_and_prose_stays_plain(tmp_path: Path) -> None:
    texts = _pages(tmp_path)
    css = (tmp_path / "site.css").read_text(encoding="utf-8")
    for name, text in texts.items():
        for banned in ("\u2014", "\u2013", "\u2019", "\u2018"):
            assert banned not in text, f"{name} contains a curly mark"
            assert banned not in css
        for href in _html_hrefs(text):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target = href.split("#", 1)[0]
            if not target:
                continue
            assert (tmp_path / target).is_file(), f"{name} links to missing {target}"


def test_every_page_uses_the_same_teaching_blocks(tmp_path: Path) -> None:
    texts = _pages(tmp_path)
    for name, text in texts.items():
        for block in BLOCKS:
            assert f"<h2>{block}</h2>" in text, f"{name} is missing {block}"


def test_tour_is_eight_ordered_steps(tmp_path: Path) -> None:
    texts = _pages(tmp_path)
    tour = [item for item in EXPECTED if item[3] is not None]
    assert [step for *_rest, step in tour] == list(range(1, 9))
    for index, (name, _title, _group, step) in enumerate(tour):
        assert f"Step {step} of 8" in texts[name]
        assert 'class="tour"' in texts[name]
        if index + 1 < len(tour):
            nxt = tour[index + 1][0]
            assert f'href="{nxt}"' in texts[name].split('class="tour"', 1)[1][:400]
    library = texts["tasks-and-suites.html"]
    assert 'class="tour"' not in library


def test_sidebar_groups_stay_together_and_placeholders_survive(tmp_path: Path) -> None:
    texts = _pages(tmp_path)
    nav = texts["index.html"].split('aria-label="Documentation">', 1)[1]
    nav = nav.split("</nav>", 1)[0]
    assert nav.index("tasks-and-suites.html") < nav.index("seeded-faults.html")
    assert nav.index("agent-contract.html") < nav.index("plug-in-your-agent.html")
    assert nav.index("your-own-suite.html") < nav.index('class="group">Glossary')
    suite = texts["tasks-and-suites.html"]
    assert "{0}" in suite
    assert "{{0}}" not in suite


def test_published_pages_match_a_fresh_build(tmp_path: Path) -> None:
    fresh = _pages(tmp_path)
    published = ROOT / "website"
    for name, text in fresh.items():
        assert (published / name).read_text(encoding="utf-8") == text
    assert (published / "site.css").read_text(encoding="utf-8") == (
        tmp_path / "site.css"
    ).read_text(encoding="utf-8")


def _html_hrefs(text: str) -> list[str]:
    hrefs: list[str] = []
    needle = 'href="'
    start = 0
    while True:
        found = text.find(needle, start)
        if found < 0:
            return hrefs
        begin = found + len(needle)
        end = text.find('"', begin)
        hrefs.append(text[begin:end])
        start = end + 1
