#!/usr/bin/env bash
# Compile every diagram to PDF (for LaTeX documents) and PNG (for slides).
set -euo pipefail
cd "$(dirname "$0")"
targets=("$@")
if [ ${#targets[@]} -eq 0 ]; then
  targets=(*.tex)
fi
for tex in "${targets[@]}"; do
  [ "$tex" = "relai-style.tex" ] && continue
  name="${tex%.tex}"
  pdflatex -interaction=nonstopmode -halt-on-error "$tex" >"/tmp/relai-diagram-$name.log" 2>&1 || {
    echo "FAILED: $tex (see /tmp/relai-diagram-$name.log)"
    grep -m5 -A3 '^!' "/tmp/relai-diagram-$name.log" || true
    exit 1
  }
  pdftoppm -png -r 200 -singlefile "$name.pdf" "$name"
  echo "built $name.pdf and $name.png"
done
rm -f ./*.aux ./*.log
