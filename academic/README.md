# Academic deliverables

Material for the Design/Implementation Phase progress review of Capstone
Project 1 (group G053), and the sources to rebuild all of it.

| What | File |
| --- | --- |
| Progress presentation (20 slides, speaker notes name the presenter) | [progress-review/Progress_Review_PPT.pptx](progress-review/Progress_Review_PPT.pptx), PDF copy alongside |
| Progress report (SRS, design diagrams, implementation, results, Annexure-2 details) | [progress-review/progress_report.pdf](progress-review/progress_report.pdf) |
| First research paper, IEEE conference format (A4) | [paper/relai_paper.pdf](paper/relai_paper.pdf) |
| Design diagrams (architecture, class, sequence, DFD 0 and 1, ER, Gantt, classifier) | [diagrams/](diagrams/) |
| Experiment data behind every number | [results/](results/) |
| Code and terminal snapshots | [snapshots/](snapshots/) |
| Sample HTML report | [results/sample_report.html](results/sample_report.html) |

## Rebuild

```bash
# numbers, CSV files, captured CLI output, sample report (project venv)
python academic/results/make_results.py

# diagrams and plots (needs pdflatex with TikZ, pgfplots, pgfgantt)
academic/diagrams/build.sh

# snapshots and slides (needs a venv with pygments, pillow, python-pptx)
python academic/snapshots/make_snapshots.py
python academic/progress-review/build_ppt.py docs/Project_PPT_template.pptx

# paper and report
(cd academic/paper && pdflatex relai_paper.tex && pdflatex relai_paper.tex)
(cd academic/progress-review && pdflatex progress_report.tex && pdflatex progress_report.tex)
```

The institute template for the slides lives in `docs/`, which stays on each
member's machine and is not tracked.
