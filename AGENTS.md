# AGENTS.md

## Cursor Cloud specific instructions

### Proyecto
Stochastic Green Edge (SGE): prototipo en Python de defensa adaptativa para APIs
(Edge + Serverless) que usa Teoria de Juegos (Equilibrio de Nash en estrategias
mixtas) para balancear seguridad y consumo energetico. Es un servicio de
simulacion por linea de comandos; no expone un servidor HTTP persistente.

### Entorno
- Python 3.12 con `venv` en `.venv/`. Dependencias en `requirements.txt` (numpy,
  pytest, ruff). Activar con `source .venv/bin/activate`.
- El paquete principal es `sge/`; el punto de entrada es `main.py`.

### Comandos (todo desde la raiz del repo, con el venv activo)
- Ejecutar la app / demo: `python main.py` (ver flags en `README.md`, p.ej.
  `--demo-nash`, `--requests`, `--seed`).
- Pruebas: `pytest` (config en `pyproject.toml`, `testpaths=tests`).
- Lint: `ruff check .` (auto-fix: `ruff check . --fix`).

### Gotchas no obvios
- La herramienta de escritura de archivos de este entorno puede guardar fuentes en
  UTF-16 (bytes nulos), lo que rompe la importacion de Python y `pytest`
  ("source code string cannot contain null bytes"). Si aparece ese error, convertir
  el archivo afectado a UTF-8, por ejemplo:
  `iconv -f UTF-16LE -t UTF-8 archivo.py -o archivo.py`. Verificar con
  `python3 -c "print(open('archivo.py','rb').read().count(b'\x00'))"` (debe ser 0).
- La simulacion es estocastica pero reproducible mediante `--seed` (y el `seed` de
  `run_simulation`/`generate_traffic`). Al ajustar parametros del modelo en
  `sge/config.py`, validar la estabilidad de metricas en varias semillas.
- El calculo del Nash prioriza el equilibrio interior mixto; para juegos con
  estrategia dominante devuelve el equilibrio puro (`NashEquilibrium.kind`).
