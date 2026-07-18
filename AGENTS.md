# AGENTS.md

## Cursor Cloud specific instructions

### Proyecto
Stochastic Green Edge (SGE): prototipo en Python de defensa adaptativa para APIs
(Edge + Serverless) que usa Teoria de Juegos (Equilibrio de Nash en estrategias
mixtas) para balancear seguridad y consumo energetico. Es un servicio de
simulacion por linea de comandos; NO expone un servidor HTTP persistente.

### Entorno
- Python 3.12. Las dependencias (`numpy`, `pytest`, `ruff`) se instalan a nivel de
  sistema mediante el update script (`pip install --break-system-packages`), por lo
  que NO hace falta activar ningun virtualenv: usar `python3`, `pytest` y `ruff`
  directamente. `numpy` ya viene en la imagen base; el update script solo refresca
  las versiones fijadas en `requirements.txt`.
- Paquete principal: `sge/`. Punto de entrada: `main.py`.

### Comandos (desde la raiz del repo)
- Ejecutar la app / demo: `python3 main.py` (flags en `README.md`, p.ej.
  `--demo-nash`, `--requests N`, `--seed S`).
- Pruebas: `pytest` (config en `pyproject.toml`, `testpaths=tests`).
- Lint: `ruff check .` (auto-fix: `ruff check . --fix`).

### Gotchas no obvios
- La herramienta de escritura de archivos de este entorno puede guardar fuentes en
  UTF-16 (bytes nulos), lo que rompe la importacion de Python y `pytest`
  ("source code string cannot contain null bytes"). Si aparece ese error, convertir
  el archivo afectado a UTF-8: `iconv -f UTF-16LE -t UTF-8 f.py -o f.py`. Verificar
  con `python3 -c "print(open('f.py','rb').read().count(b'\x00'))"` (debe dar 0).
- La simulacion es estocastica pero reproducible via `--seed` (y el `seed` de
  `run_simulation`/`generate_traffic`). Al ajustar parametros en `sge/config.py`,
  validar la estabilidad de las metricas en varias semillas.
- El calculo del Nash prioriza el equilibrio interior mixto; ante una estrategia
  dominante devuelve el equilibrio puro (ver `NashEquilibrium.kind`).

### Paper (paper/)
- `paper/paper.tex` es el paper academico (LaTeX); `paper/paper.pdf` es el PDF
  compilado ya versionado.
- Reproducir datos y figuras: `python3 paper/run_experiments.py` (usa `matplotlib`,
  incluido en `requirements.txt`; escribe `paper/results.json` y `paper/figures/`).
- Recompilar el PDF requiere una cadena LaTeX que NO instala el update script (es
  dependencia de sistema): `apt-get install -y texlive-latex-base texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra`
  y luego `cd paper && pdflatex paper.tex` (dos pasadas para refs/figuras).
