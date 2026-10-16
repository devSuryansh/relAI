"""Render code excerpts and terminal output as PNG images for slides and reports.

    /path/to/venv-with-pygments-and-pillow/bin/python academic/snapshots/make_snapshots.py

Code excerpts are cut from the real source by function name, so every image
shows committed code with its real line numbers.
"""

from __future__ import annotations

import ast
import io
import os
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import PythonLexer, YamlLexer

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RESULTS = ROOT / "academic" / "results"
PROJECT_PYTHON = ROOT / ".venv" / "bin" / "python"
FONT = "DejaVu Sans Mono"
FONT_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
BOLD_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
BG = (30, 34, 42)
BAR = (44, 49, 60)
FG = (220, 224, 232)
DIM = (140, 150, 165)

CODE = [
    ("code_fault_policy", "src/relai/env.py", ["FaultPolicy.fault_for"]),
    ("code_evaluate", "src/relai/harness.py", ["evaluate", "_pass_at_k", "_pass_hat_k"]),
    ("code_error_episodes", "src/relai/analysis.py", ["error_episodes"]),
    ("code_analyze", "src/relai/analysis.py", ["analyze"]),
    ("code_pareto", "src/relai/optimize.py", ["dominates", "pareto_front", "recommend"]),
    ("code_mcnemar", "src/relai/stats.py", ["mcnemar_exact", "compare"]),
    ("code_retry_agent", "src/relai/baselines.py", ["RetryAgent.attempt"]),
]

TERMINAL = [
    ("term_run", "cli_run.txt"),
    ("term_stress", "cli_stress.txt"),
    ("term_sweep", "cli_sweep.txt"),
    ("term_selfcheck", "cli_selfcheck.txt"),
    ("term_demo", "cli_demo.txt"),
]


def main() -> None:
    for name, path, symbols in CODE:
        source = (ROOT / path).read_text(encoding="utf-8")
        blocks = [_extract(source, symbol) for symbol in symbols]
        for index, (start, text) in enumerate(blocks):
            image = _code_image(text, start)
            suffix = f"_{index + 1}" if len(blocks) > 1 else ""
            _framed(image, f"{path}  (line {start})").save(OUT / f"{name}{suffix}.png")
        print(f"rendered {name}")

    suite = (ROOT / "src/relai/suites/reliability.yaml").read_text(encoding="utf-8").splitlines()
    first = next(i for i, line in enumerate(suite) if "id: latest_order_status" in line)
    excerpt = "\n".join(suite[first - 1 : first + 11])
    _framed(_code_image(excerpt, first, lexer=YamlLexer()), "src/relai/suites/reliability.yaml").save(
        OUT / "code_suite_yaml.png"
    )

    for name, filename in TERMINAL:
        text = (RESULTS / filename).read_text(encoding="utf-8").rstrip()
        _framed(_terminal_image(text), "Terminal").save(OUT / f"{name}.png")
        print(f"rendered {name}")

    plain = {**os.environ, "NO_COLOR": "1", "TERM": "dumb"}
    tests = subprocess.run(
        [str(PROJECT_PYTHON), "-m", "pytest", "-q", "--color=no", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=plain,
    )
    lines = _strip_ansi(tests.stdout).strip().splitlines()
    shown = "$ pytest -q\n" + "\n".join(lines[-3:])
    lint = subprocess.run(
        [str(PROJECT_PYTHON), "-m", "ruff", "check", "--no-cache", "src", "tests", "examples"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=plain,
    )
    shown += "\n$ ruff check src tests examples\n" + _strip_ansi(lint.stdout).strip()
    _framed(_terminal_image(shown), "Terminal").save(OUT / "term_tests.png")
    print("rendered term_tests")


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _extract(source: str, dotted: str) -> tuple[int, str]:
    """Return (first line number, text) of a function or method by dotted name."""
    tree = ast.parse(source)
    scope: list[ast.stmt] = tree.body
    node: ast.AST | None = None
    for part in dotted.split("."):
        node = next(
            n
            for n in scope
            if isinstance(n, ast.FunctionDef | ast.ClassDef) and n.name == part
        )
        scope = getattr(node, "body", [])
    assert node is not None
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    lines = source.splitlines()[start - 1 : node.end_lineno]
    indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
    return start, "\n".join(line[indent:] for line in lines)


def _code_image(text: str, start: int, lexer=None) -> Image.Image:
    formatter = ImageFormatter(
        font_name=FONT,
        font_size=22,
        style="one-dark",
        line_numbers=True,
        line_number_start=start,
        line_number_bg="#1e222a",
        line_number_fg="#5c6370",
        line_number_separator=False,
        line_number_chars=4,
        line_number_pad=14,
        image_pad=22,
        line_pad=6,
    )
    data = highlight(text, lexer or PythonLexer(), formatter)
    return Image.open(io.BytesIO(data)).convert("RGB")


def _terminal_image(text: str) -> Image.Image:
    font = ImageFont.truetype(FONT_FILE, 21)
    bold = ImageFont.truetype(BOLD_FILE, 21)
    lines = text.splitlines() or [""]
    width = max(int(font.getlength(line)) for line in lines) + 56
    height = len(lines) * 30 + 44
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    for row, line in enumerate(lines):
        y = 22 + row * 30
        if line.startswith("$ "):
            draw.text((28, y), "$", font=bold, fill=(152, 195, 121))
            draw.text((28 + font.getlength("$ "), y), line[2:], font=bold, fill=(229, 192, 123))
        else:
            color = DIM if set(line.strip()) <= set("- ") else FG
            draw.text((28, y), line, font=font, fill=color)
    return image


def _framed(content: Image.Image, title: str) -> Image.Image:
    bar = 44
    width = max(content.width, 700)
    frame = Image.new("RGB", (width, content.height + bar), BG)
    draw = ImageDraw.Draw(frame)
    draw.rectangle([0, 0, width, bar], fill=BAR)
    for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        x = 22 + i * 26
        draw.ellipse([x, 15, x + 14, 29], fill=color)
    font = ImageFont.truetype(FONT_FILE, 18)
    draw.text((110, 12), title, font=font, fill=DIM)
    frame.paste(content, (0, bar))
    return frame


if __name__ == "__main__":
    main()
