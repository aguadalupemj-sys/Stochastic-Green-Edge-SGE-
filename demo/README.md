# Demo interactivo de SGE — API Gateway con panel en vivo

Este demo levanta una **pasarela HTTP** que aplica la defensa adaptativa de
**Stochastic Green Edge (SGE)** a cada petición y muestra, en un **panel web en
tiempo real**, la seguridad lograda y la **energía / huella de carbono ahorradas**
frente a la inspección tradicional del 100 %.

Solo usa la **biblioteca estándar de Python** + `numpy` (ya requerido por `sge`).
No hace falta instalar nada más.

## Cómo ejecutarlo

Desde la raíz del repositorio:

```bash
python demo/gateway.py
```

Luego abre **http://localhost:8000** en tu navegador.

En el panel puedes:

- **Generar 500 / 2000 peticiones** con la mezcla realista (80 % legítimo, 15 % bots,
  5 % ataques avanzados) y ver cómo suben la mitigación y el ahorro de energía.
- **Enviar peticiones individuales** (legítimo, bot, *SQL injection*, *prompt
  injection*) y ver la decisión de SGE en el registro: si se sirve barato en el Edge,
  se bloquea, o se **escala** a la inspección profunda.
- Ver en vivo la **energía adaptativa vs. tradicional**, el **% ahorrado** y el
  **CO₂ evitado** (proyectado a una API de 10⁹ peticiones/mes).

## Generar tráfico real (opcional)

Con el gateway corriendo, en otra terminal:

```bash
python demo/load_test.py --n 2000
```

Esto envía peticiones HTTP reales a la pasarela y el panel se actualiza solo.

## Qué demuestra

- El **filtro Edge** resuelve la mayoría del tráfico al costo mínimo (1 unidad).
- El **motor de Nash** solo escala a la capa Serverless (costo 15–25) el tráfico
  sospechoso, incluidos los intentos de **inyección de prompts**.
- Resultado típico: **~94 % de mitigación** con **~86 % menos de energía** — y, por
  tanto, una reducción proporcional de la huella de carbono.

> Nota de arquitectura: este demo está en Python por claridad. En producción, el plano
> de datos (Edge) se implementaría en **Go** por rendimiento, reservando **Python**
> para el motor matemático y la calibración *offline* (ver el paper, sección de
> viabilidad técnica).
