#!/usr/bin/env python3
"""Genera el documento Word "Fundamentos del Proyecto SGE".

Produce docs/Fundamentos_SGE.docx: un manual de todo lo que se debe saber
para trabajar en el proyecto Stochastic Green Edge (conceptos, definiciones,
fundamentos matematicos, arquitectura, herramientas, metodologia y glosario).

Uso:
    pip install python-docx
    python docs/generate_fundamentos_docx.py
"""
from __future__ import annotations

import os

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Inches

# Paleta (verde sostenible + gris pizarra)
GREEN = RGBColor(0x1B, 0x7A, 0x3D)
DARK = RGBColor(0x1F, 0x2A, 0x24)
GREY = RGBColor(0x55, 0x5F, 0x5A)


def set_cell_bg(cell, hex_color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): hex_color})
    tc_pr.append(shd)


def add_title_page(doc: Document) -> None:
    doc.add_paragraph()
    doc.add_paragraph()
    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Stochastic Green Edge (SGE)")
    r.font.size = Pt(30)
    r.font.bold = True
    r.font.color.rgb = GREEN

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Fundamentos del proyecto")
    r.font.size = Pt(20)
    r.font.color.rgb = DARK

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Todo lo que deberias saber antes de desarrollar:\n"
                  "conceptos, definiciones, matematicas, arquitectura y herramientas")
    r.font.size = Pt(13)
    r.font.italic = True
    r.font.color.rgb = GREY

    for _ in range(6):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Ciberseguridad sostenible - Green & Edge Computing - Teoria de Juegos")
    r.font.size = Pt(11)
    r.font.color.rgb = GREY

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Documento de referencia tecnica - Version 1.0")
    r.font.size = Pt(10)
    r.font.color.rgb = GREY

    doc.add_page_break()


def h1(doc: Document, text: str):
    p = doc.add_heading(text, level=1)
    for r in p.runs:
        r.font.color.rgb = GREEN
    return p


def h2(doc: Document, text: str):
    p = doc.add_heading(text, level=2)
    for r in p.runs:
        r.font.color.rgb = DARK
    return p


def h3(doc: Document, text: str):
    p = doc.add_heading(text, level=3)
    for r in p.runs:
        r.font.color.rgb = GREY
    return p


def para(doc: Document, text: str):
    p = doc.add_paragraph(text)
    p.paragraph_format.space_after = Pt(6)
    return p


def bullet(doc: Document, text: str, bold_lead: str | None = None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    return p


def numbered(doc: Document, text: str, bold_lead: str | None = None):
    p = doc.add_paragraph(style="List Number")
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    return p


def deflist(doc: Document, term: str, definition: str):
    """Termino en negrita seguido de su definicion, en un mismo parrafo."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(f"{term}. ")
    r.bold = True
    r.font.color.rgb = DARK
    p.add_run(definition)
    return p


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float] | None = None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for i, htext in enumerate(headers):
        hdr[i].text = ""
        run = hdr[i].paragraphs[0].add_run(htext)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.font.size = Pt(10)
        set_cell_bg(hdr[i], "1B7A3D")
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(val)
            run.font.size = Pt(9.5)
    if widths:
        for i, w in enumerate(widths):
            for row in table.rows:
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return table


def callout(doc: Document, text: str, label: str = "Idea clave"):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.rows[0].cells[0]
    set_cell_bg(cell, "E8F3EC")
    cell.text = ""
    p = cell.paragraphs[0]
    r = p.add_run(f"{label}: ")
    r.bold = True
    r.font.color.rgb = GREEN
    p.add_run(text)
    doc.add_paragraph()
    return table


# --------------------------------------------------------------------------- #
#  Construccion del documento
# --------------------------------------------------------------------------- #
def build() -> Document:
    doc = Document()

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = DARK

    add_title_page(doc)

    # ---- Como usar este documento ---------------------------------------- #
    h1(doc, "Como usar este documento")
    para(doc, "Este manual reune, de forma progresiva, todos los conceptos, definiciones, "
              "fundamentos matematicos, decisiones de arquitectura y herramientas necesarios "
              "para entender y contribuir al proyecto Stochastic Green Edge (SGE). Esta pensado "
              "tanto para alguien que se incorpora sin contexto previo como para consultarlo "
              "puntualmente durante el desarrollo.")
    bullet(doc, "Si eres nuevo: leelo en orden. Cada capitulo asume solo lo visto en los anteriores.",
           bold_lead="")
    bullet(doc, "Si buscas un termino concreto: ve directo al Glosario (capitulo final).",
           bold_lead="")
    bullet(doc, "Si vas a programar: presta especial atencion a los capitulos de arquitectura, "
                "herramientas y metodologia experimental.", bold_lead="")
    callout(doc, "SGE protege APIs e infraestructuras en el borde revisando el trafico de forma "
                 "inteligente e intermitente (no todo, todo el tiempo), usando teoria de juegos para "
                 "decidir cuando vale la pena inspeccionar a fondo. Asi detecta casi las mismas "
                 "amenazas gastando mucha menos energia y emitiendo menos CO2.",
            label="SGE en una frase")

    # ---- 1. Vision general ----------------------------------------------- #
    h1(doc, "1. Vision general del proyecto")
    h2(doc, "1.1 El problema")
    para(doc, "La practica de seguridad dominante somete el 100% del trafico entrante de una API a "
              "inspeccion profunda (sanitizacion exhaustiva, validacion criptografica, analisis de "
              "payload y, cada vez mas, invocacion de modelos de lenguaje). Ese gasto es elevado, "
              "constante e invariante al riesgo: se procesa con la misma intensidad el trafico "
              "legitimo (la gran mayoria) que el realmente peligroso. El resultado es un consumo "
              "electrico sostenido y una huella de carbono alta y constante, en contradiccion directa "
              "con los principios del computo verde.")
    h2(doc, "1.2 La idea de SGE")
    para(doc, "SGE invierte ese paradigma. Trata la inspeccion profunda como un recurso energetico "
              "escaso y lo asigna selectivamente: un filtro Edge de baja potencia resuelve de forma "
              "barata la mayoria del trafico benigno o ruidoso, y solo escala a la inspeccion costosa "
              "la fraccion sospechosa. La decision de escalar se modela como un juego no cooperativo "
              "entre un Defensor y un Atacante y se resuelve con el equilibrio de Nash en estrategias "
              "mixtas, obteniendo una politica de inspeccion aleatorizada que un adversario racional "
              "no puede eludir de forma sistematica.")
    h2(doc, "1.3 Resultado esperado")
    para(doc, "En la simulacion de referencia (2.000 peticiones, semilla 7) SGE reduce el consumo "
              "energetico un 85,9% (de 30.010 a 4.225 Joules) y, en la misma proporcion, la huella de "
              "carbono, manteniendo una mitigacion de amenazas del 94,38%. A escala de una API con "
              "10^9 peticiones/mes, ello equivale a evitar del orden de 2 toneladas de CO2 al ano.")
    add_table(
        doc,
        ["Enfoque", "Mitigacion global", "Mitigacion avanzada", "Energia (J)"],
        [
            ["Tradicional (inspeccion 100%)", "100%", "100%", "30.010"],
            ["SGE Adaptativo (Nash)", "94,38%", "78,95%", "4.225"],
            ["Edge-only (nunca escala)", "75,53%", "0%", "2.000"],
        ],
        widths=[2.6, 1.4, 1.5, 1.1],
    )

    # ---- 2. Ciberseguridad ----------------------------------------------- #
    h1(doc, "2. Fundamentos de ciberseguridad de APIs")
    h2(doc, "2.1 Conceptos base")
    deflist(doc, "API (Interfaz de Programacion de Aplicaciones)",
            "puerta de entrada por la que dos programas se comunican. SGE protege estas puertas.")
    deflist(doc, "Peticion / Respuesta (request/response)",
            "una peticion es una solicitud del cliente; la respuesta es lo que devuelve el servidor.")
    deflist(doc, "Payload (carga util)",
            "el contenido concreto que viaja dentro de una peticion. Dentro del payload pueden "
            "esconderse ataques; por eso a veces hay que inspeccionarlo.")
    deflist(doc, "HTTP / REST",
            "el idioma estandar de la web y el estilo de API mas comun sobre el. SGE se centra, en "
            "esta fase, exclusivamente en trafico HTTP/REST.")
    deflist(doc, "Gateway / Proxy (pasarela)",
            "componente intermedio por el que pasa todo el trafico; puede inspeccionarlo, filtrarlo o "
            "bloquearlo. Es donde SGE aplica su decision.")
    deflist(doc, "WAF (Web Application Firewall)",
            "cortafuegos de aplicaciones web basado en firmas y reglas. SGE es complementario: le "
            "aporta la capa de eficiencia energetica de la que carece.")
    deflist(doc, "DPI (Deep Packet Inspection) / inspeccion profunda",
            "analisis exhaustivo del contenido del trafico. Es la operacion costosa que SGE reserva "
            "solo para el trafico sospechoso.")
    deflist(doc, "Rate limiting (limitacion de tasa)",
            "poner un limite al numero de peticiones por unidad de tiempo; frena bots ruidosos de "
            "forma barata en el borde.")
    deflist(doc, "Latencia de cola (tail latency)",
            "el tiempo de respuesta en los peores casos (percentiles altos); estabilizarla es un "
            "beneficio operativo de descargar trafico al Edge.")

    h2(doc, "2.2 Amenazas que SGE combate")
    deflist(doc, "Prompt injection (inyeccion de instrucciones)",
            "ataque contra sistemas basados en modelos de lenguaje: se esconden instrucciones "
            "maliciosas dentro de un texto para que el modelo ignore sus reglas o filtre informacion. "
            "Es un vector emergente y especialmente costoso de inspeccionar.")
    deflist(doc, "Inyeccion SQL/comandos (SQLi/CMDi)",
            "payloads maliciosos que manipulan una consulta o ejecutan comandos no previstos.")
    deflist(doc, "Abuso de peticiones (request abuse)",
            "uso indebido de la API: demasiadas peticiones, exploracion o explotacion no permitida.")
    deflist(doc, "DoS/DDoS (denegacion de servicio)",
            "saturar el sistema con trafico para dejarlo inoperativo para usuarios legitimos.")
    deflist(doc, "Bots ruidosos",
            "trafico automatizado de alta frecuencia y firma anomala; se neutraliza barato en el Edge.")
    deflist(doc, "Ataque avanzado / sigiloso (dirigido)",
            "adversario que imita trafico legitimo; es la fraccion pequena que si justifica la "
            "inspeccion profunda, y que no es directamente observable.")
    deflist(doc, "Adversario racional",
            "en teoria de juegos, atacante que elige la accion que maximiza su beneficio esperado; "
            "modelarlo asi es lo que hace robusta a la politica de SGE.")
    deflist(doc, "Vector de ataque",
            "la via o metodo concreto de un ataque (prompt injection, SQLi, etc.).")

    h2(doc, "2.3 Como se mide la seguridad")
    deflist(doc, "TPR (tasa de verdaderos positivos) / tasa de deteccion",
            "de todos los ataques reales, cuantos se detectan. Mas alto es mejor.")
    deflist(doc, "FPR (tasa de falsos positivos)",
            "peticiones legitimas marcadas por error como ataque. Mas bajo es mejor.")
    deflist(doc, "Falso negativo",
            "un ataque real que no se detecta: el error mas peligroso en seguridad.")
    deflist(doc, "Tasa de mitigacion",
            "porcentaje de ataques efectivamente neutralizados; en SGE actua como restriccion de "
            "calidad de servicio que no debe degradarse.")

    # ---- 3. Green Computing ---------------------------------------------- #
    h1(doc, "3. Green Computing y sostenibilidad")
    para(doc, "El segundo gran objetivo de SGE, en pie de igualdad con la seguridad, es reducir el "
              "consumo de energia y las emisiones. Estos son los conceptos imprescindibles.")
    deflist(doc, "Green Computing (computo verde)",
            "diseno y uso de la tecnologia para minimizar el consumo energetico y las emisiones "
            "asociadas, eliminando el sobreprocesamiento innecesario (ecodiseno de software).")
    deflist(doc, "Huella de carbono (gCO2e)",
            "gramos de CO2 equivalente emitidos por consumir cierta energia. SGE busca reducir la "
            "huella por peticion procesada.")
    deflist(doc, "PUE (Power Usage Effectiveness)",
            "factor que captura el sobrecosto energetico del centro de datos (refrigeracion, "
            "distribucion); tipicamente 1,4-1,6.")
    deflist(doc, "Intensidad de red (I_grid)",
            "cuanto CO2 se emite por unidad de electricidad segun como se genere en una region "
            "(kgCO2eq/kWh). No es lo mismo energia solar que carbon.")
    deflist(doc, "SCI (Software Carbon Intensity)",
            "especificacion de la Green Software Foundation para medir la intensidad de carbono del "
            "software; base para reportes ESG auditables.")
    deflist(doc, "ESG (alcances 2 y 3)",
            "marcos de reporte ambiental, social y de gobernanza; SGE aporta una palanca cuantificable "
            "y auditable de reduccion de emisiones.")
    h2(doc, "3.1 El modelo de carbono")
    para(doc, "La huella de carbono de una carga de computo se modela como el producto de la energia "
              "consumida por el sobrecosto del centro de datos y la intensidad de la red electrica:")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("E(CO2)  =  W  x  PUE  x  I_grid")
    r.bold = True
    r.font.color.rgb = GREEN
    callout(doc, "Como PUE e I_grid son constantes para una infraestructura dada, la reduccion "
                 "relativa de emisiones coincide exactamente con la reduccion relativa de energia: "
                 "ahorrar Joules es, uno a uno, ahorrar carbono. Este es el pilar del proyecto.",
            label="Piedra angular")

    # ---- 4. Edge y Serverless -------------------------------------------- #
    h1(doc, "4. Edge Computing y Serverless")
    deflist(doc, "Edge Computing (computo en el borde)",
            "procesar los datos cerca de donde se generan, en dispositivos con recursos limitados. "
            "Ahorrar energia alli es especialmente valioso.")
    deflist(doc, "Serverless (computo sin servidor)",
            "funciones efimeras que solo consumen recursos cuando se invocan; en reposo no gastan "
            "energia. SGE explota esta propiedad activandolas lo menos posible.")
    deflist(doc, "Cold start (arranque en frio)",
            "penalizacion de energia/latencia al activar una funcion serverless tras un periodo de "
            "inactividad. Es el evento mas costoso y SGE busca minimizarlos.")
    deflist(doc, "Load shedding / offload",
            "descargar trabajo de la capa costosa a la barata; SGE resuelve ~95% del trafico en el "
            "Edge, protegiendo al nucleo de picos y ataques de agotamiento de recursos.")
    h2(doc, "4.1 La asimetria de costos: 1 : 15 : 25")
    para(doc, "SGE modela dos capas con costos energeticos radicalmente asimetricos, en unidades "
              "relativas de Joules/ciclos:")
    add_table(
        doc,
        ["Capa / evento", "Simbolo", "Costo relativo", "Descripcion"],
        [
            ["Filtro Edge (paso rapido)", "C_edge", "1", "Baja potencia, cercano al usuario"],
            ["Serverless (ejecucion tibia)", "C_exec", "15", "Inspeccion profunda bajo demanda"],
            ["Serverless (arranque en frio)", "C_cold", "25", "Penalizacion tras inactividad"],
        ],
        widths=[2.4, 1.0, 1.2, 2.6],
    )
    callout(doc, "Cada peticion resuelta en el Edge en lugar de escalar ahorra entre 14 y 24 unidades "
                 "de energia. Ese es el origen cuantitativo del ahorro del 85,9%.")

    # ---- 5. Fundamentos matematicos -------------------------------------- #
    h1(doc, "5. Fundamentos matematicos: estocastica y teoria de juegos")
    h2(doc, "5.1 Nociones de probabilidad")
    deflist(doc, "Estocastico (probabilistico)",
            "que incluye azar controlado: no siempre hace lo mismo, decide con probabilidades. SGE no "
            "inspecciona siempre; escala con cierta probabilidad, lo que lo hace impredecible para el "
            "atacante y mas barato.")
    deflist(doc, "Determinista",
            "lo contrario: ante la misma entrada siempre hace lo mismo. La inspeccion continua clasica "
            "es determinista.")
    deflist(doc, "Utilidad esperada",
            "el valor promedio ponderado por probabilidades de un resultado; los jugadores racionales "
            "eligen para maximizarla.")
    deflist(doc, "Muestreo (sampling)",
            "revisar solo una parte del trafico. El muestreo uniforme fijo (p. ej. 10% siempre) es un "
            "baseline; SGE elige de forma inteligente, no fija.")
    deflist(doc, "Cadenas de Markov / procesos de decision",
            "modelos de sistemas que cambian de estado con ciertas probabilidades; base para politicas "
            "adaptativas con memoria (trabajo futuro).")

    h2(doc, "5.2 Teoria de juegos")
    deflist(doc, "Teoria de juegos",
            "rama de las matematicas que estudia decisiones entre partes cuyo resultado depende de lo "
            "que hagan las demas.")
    deflist(doc, "Juego no cooperativo",
            "los jugadores actuan por su propio interes, sin acuerdos vinculantes (Defensor vs. "
            "Atacante).")
    deflist(doc, "Jugadores, acciones, payoff",
            "quienes deciden, que pueden hacer y cuanto ganan/pierden segun las acciones combinadas. "
            "En SGE el payoff del Defensor mezcla seguridad, energia y dano.")
    deflist(doc, "Informacion imperfecta",
            "el Defensor no observa la clase real de la peticion; solo infiere una puntuacion de "
            "sospecha. Esto obliga a una solucion probabilistica.")
    deflist(doc, "Estrategia pura vs. mixta",
            "una estrategia pura elige siempre una accion; una mixta elige con probabilidades "
            "(p. ej. 'escalar el 30% de las veces'). SGE calcula una estrategia mixta.")
    deflist(doc, "Matriz de pagos (juego bimatriz 2x2)",
            "tabla que recoge la utilidad de cada jugador para cada combinacion de acciones; SGE la "
            "resuelve en forma cerrada, en microsegundos.")
    deflist(doc, "Matching pennies",
            "estructura de juego sin equilibrio en estrategias puras (cada uno quiere anticipar y el "
            "otro evitarlo); es la del juego Defensor-Atacante de SGE, por eso la solucion es mixta.")

    h2(doc, "5.3 El Equilibrio de Nash y el principio de indiferencia")
    deflist(doc, "Equilibrio de Nash",
            "situacion estable en la que ningun jugador gana nada cambiando su estrategia por su "
            "cuenta, dado lo que hace el otro. SGE busca la politica de inspeccion que es la mejor "
            "respuesta frente a un atacante que tambien juega optimo.")
    deflist(doc, "Principio de indiferencia",
            "en un juego 2x2 sin equilibrio puro, cada jugador aleatoriza de modo que su rival quede "
            "indiferente entre sus dos acciones; de aqui salen las probabilidades del equilibrio.")
    para(doc, "La funcion de utilidad del Defensor integra tres terminos ponderados (alfa, beta, "
              "gamma):")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("U_D = alfa * R  -  beta * C_energia  -  gamma * C_dano")
    r.bold = True
    r.font.color.rgb = GREEN
    para(doc, "El termino de energia penaliza gastar recursos; el de dano penaliza no gastarlos "
              "cuando habria sido necesario. El equilibrio resuelve esa tension: en el punto optimo, "
              "el Joule marginal invertido en inspeccionar iguala exactamente la seguridad marginal "
              "obtenida. El sistema ni sobre-inspecciona (malgastar energia) ni sub-inspecciona "
              "(aceptar dano evitable).")
    callout(doc, "La probabilidad de escalar a la inspeccion profunda crece de forma monotona con la "
                 "puntuacion de sospecha: casi nula para trafico benigno y alta ante anomalias reales.")

    # ---- 6. El modelo SGE ------------------------------------------------ #
    h1(doc, "6. El modelo SGE en detalle")
    h2(doc, "6.1 Arquitectura de dos capas")
    bullet(doc, "resuelve barato (costo 1) la mayoria del trafico, extrae metricas ligeras "
                "(frecuencia de IP, tamano de payload, anomalia de User-Agent), aplica rate-limiting "
                "y ejecuta el motor de decision de Nash.", bold_lead="Capa Edge (baja potencia): ")
    bullet(doc, "funcion efimera de inspeccion profunda (costo 15, o 25 en frio) que solo se activa "
                "cuando el motor lo decide; al invocarse detecta de forma fiable la amenaza.",
           bold_lead="Capa Serverless (bajo demanda): ")
    h2(doc, "6.2 La puntuacion de sospecha")
    para(doc, "El Edge no observa la naturaleza real de la peticion; infiere una sospecha s en [0,1] "
              "a partir de senales baratas, dominada por la anomalia del payload:")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("s = 0,15 * IP  +  0,15 * User-Agent  +  0,70 * anomalia_payload")
    r.bold = True
    r.font.color.rgb = GREEN
    para(doc, "La sospecha modula el riesgo y, con el, la severidad del dano y la ganancia del "
              "atacante: el juego (y su equilibrio) es especifico de cada peticion.")
    h2(doc, "6.3 Por que es tan eficiente")
    numbered(doc, "El ~80% de trafico legitimo produce sospecha baja: nunca activa la capa costosa "
                  "(se sirve a costo 1).")
    numbered(doc, "El ~15% de bots ruidosos se frena en el Edge por rate-limiting, tambien a costo 1.")
    numbered(doc, "Solo el ~5% sospechoso escala a Serverless, concentrando alli todo el gasto.")

    # ---- 7. Herramientas ------------------------------------------------- #
    h1(doc, "7. Herramientas y stack tecnologico")
    para(doc, "Conjunto de tecnologias del prototipo actual y de una eventual implementacion de "
              "produccion. No es imprescindible dominarlas todas de inmediato, pero conviene conocer "
              "para que sirve cada una.")
    h2(doc, "7.1 Lenguajes y computo cientifico")
    deflist(doc, "Python 3",
            "lenguaje del prototipo y del motor matematico; rapido para expresar y calibrar el modelo.")
    deflist(doc, "NumPy / SciPy",
            "librerias de computo numerico y cientifico para algebra lineal y resolucion del juego.")
    deflist(doc, "Matplotlib",
            "generacion de las figuras del paper (consumo, Pareto, carbono).")
    deflist(doc, "Go (recomendado para el plano de datos)",
            "lenguaje de sistemas cloud (Kubernetes, Envoy); concurrencia con goroutines, binario "
            "estatico y bajo consumo, ideal para la pasarela/Edge de alto rendimiento.")
    deflist(doc, "gRPC",
            "protocolo de comunicacion eficiente entre servicios; opcion para conectar la capa Edge "
            "(Go) con el motor de analisis (Python).")
    h2(doc, "7.2 Calidad, pruebas y reproducibilidad")
    deflist(doc, "Ruff",
            "analizador estatico (linter) de Python muy rapido; verifica el estilo y detecta errores.")
    deflist(doc, "Pytest",
            "framework de pruebas; el prototipo se valida con 13 tests (motor de Nash, condicion de "
            "indiferencia y simulacion).")
    deflist(doc, "Semilla aleatoria (seed-7)",
            "numero que fija el azar para que los experimentos sean reproducibles bit a bit; todos los "
            "resultados se reportan bajo semilla 7.")
    deflist(doc, "Git / GitHub",
            "control de versiones y colaboracion (ramas, pull requests, revision de codigo).")
    h2(doc, "7.3 Documentacion cientifica")
    deflist(doc, "LaTeX",
            "sistema de composicion de documentos tecnicos; el paper (paper.tex y paper_sostenible.tex) "
            "se escribe en LaTeX con figuras en PNG.")
    deflist(doc, "Markdown",
            "formato ligero para documentacion del repositorio (objetivos, alcance, glosario).")
    h2(doc, "7.4 Servicios cloud de referencia (AWS) y contexto de despliegue")
    para(doc, "SGE es complementario a los controles nativos de la nube; actua como capa de eficiencia "
              "sobre ellos. Servicios habituales de mitigacion:")
    add_table(
        doc,
        ["Amenaza", "Mitigacion nativa (AWS)"],
        [
            ["Inyeccion / prompt injection", "AWS WAF, API Gateway (throttling), Bedrock Guardrails, Lambda"],
            ["DDoS", "AWS Shield, CloudFront, Route 53, reglas rate-based de WAF"],
            ["Credenciales/IAM", "IAM (minimo privilegio), Access Analyzer, MFA, GuardDuty"],
            ["Fuga de datos", "Amazon Macie, KMS (cifrado), VPC endpoints"],
            ["APIs inseguras", "API Gateway authorizers, Cognito, Verified Permissions"],
        ],
        widths=[2.2, 4.2],
    )
    deflist(doc, "Docker / Kubernetes",
            "empaquetado en contenedores y orquestacion; la capa Edge se materializa como middleware "
            "sin estado replicable.")

    # ---- 8. Metodologia -------------------------------------------------- #
    h1(doc, "8. Metodologia experimental y benchmarking")
    deflist(doc, "Prototipo funcional",
            "primera version que ya funciona para demostrar la idea, sin ser producto de produccion.")
    deflist(doc, "Baseline (linea base)",
            "metodo de referencia con el que se compara: (a) inspeccion continua del 100% y (b) "
            "muestreo uniforme fijo / Edge-only.")
    deflist(doc, "Escenario de trafico",
            "mezcla realista de prueba: 80% legitimo, 15% bots ruidosos, 5% ataques dirigidos.")
    deflist(doc, "Frontera de Pareto / trade-off",
            "conjunto de mejores soluciones del compromiso seguridad-energia; SGE se situa en una "
            "frontera mejor que los metodos clasicos.")
    deflist(doc, "Analisis de sensibilidad",
            "comprobar cuanto cambian los resultados al variar parametros; la reduccion proporcional "
            "del 85,9% es independiente de las hipotesis absolutas.")
    deflist(doc, "Reproducibilidad",
            "que cualquiera pueda repetir el experimento (misma semilla y entorno) y obtener los "
            "mismos numeros; da credibilidad cientifica.")
    h2(doc, "8.1 Metricas clave (KPIs)")
    add_table(
        doc,
        ["Dimension", "Metrica", "Sentido"],
        [
            ["Deteccion", "TPR, FPR por vector", "Mas TPR y menos FPR es mejor"],
            ["Eficiencia", "J/req, CPU-ms/req, gCO2e/req", "Menor es mejor"],
            ["Compromiso", "Posicion en frontera de Pareto", "Dominar a los baselines"],
            ["Reproducibilidad", "Determinismo bajo seed-7", "Resultados identicos al repetir"],
        ],
        widths=[1.6, 2.6, 2.2],
    )

    # ---- 9. Objetivos y alcance (resumen) -------------------------------- #
    h1(doc, "9. Objetivos y alcance (resumen operativo)")
    h2(doc, "9.1 Objetivo general")
    para(doc, "Disenar, implementar y validar un motor de decision estocastico basado en teoria de "
              "juegos para la intercepcion eficiente y segura de amenazas en APIs e infraestructuras "
              "Edge, minimizando el consumo energetico y la huella de carbono sin degradar la "
              "seguridad.")
    h2(doc, "9.2 Objetivos especificos")
    numbered(doc, "logica estocastica y de teoria de juegos (Nash, estrategia mixta, seed-7).",
             bold_lead="OE-1: ")
    numbered(doc, "capa de seguridad en APIs e inspeccion de payloads/prompts (prompt injection).",
             bold_lead="OE-2: ")
    numbered(doc, "medicion y reduccion del consumo energetico (gCO2e) integrada en el payoff.",
             bold_lead="OE-3: ")
    numbered(doc, "validacion y benchmarking frente a metodos convencionales.", bold_lead="OE-4: ")
    h2(doc, "9.3 Dentro / fuera de alcance")
    bullet(doc, "algoritmo Nash reproducible, filtrado HTTP/REST, inspeccion de payloads/prompts, "
                "metricas energeticas y prototipo + benchmarking.", bold_lead="In-scope: ")
    bullet(doc, "despliegue multirregion a gran escala, GUIs complejas de administracion, protocolos "
                "industriales no HTTP/REST y hardening/certificacion productiva.",
           bold_lead="Out-of-scope: ")

    # ---- 10. Ruta de aprendizaje ----------------------------------------- #
    h1(doc, "10. Ruta de aprendizaje sugerida")
    numbered(doc, "Conceptos de APIs, HTTP/REST y payloads (capitulo 2).")
    numbered(doc, "Panorama de amenazas, con enfasis en prompt injection (capitulo 2).")
    numbered(doc, "Green Computing: energia, PUE, huella de carbono (capitulo 3).")
    numbered(doc, "Edge y Serverless, y la asimetria de costos 1:15:25 (capitulo 4).")
    numbered(doc, "Probabilidad basica y utilidad esperada (capitulo 5.1).")
    numbered(doc, "Teoria de juegos: estrategias mixtas y equilibrio de Nash (capitulo 5.2-5.3).")
    numbered(doc, "El modelo SGE: arquitectura, sospecha y eficiencia (capitulo 6).")
    numbered(doc, "Herramientas del stack, empezando por Python/NumPy y Pytest (capitulo 7).")
    numbered(doc, "Metodologia experimental y reproducibilidad con seed-7 (capitulo 8).")

    # ---- 11. Glosario ---------------------------------------------------- #
    h1(doc, "11. Glosario rapido")
    glossary = [
        ("API", "Puerta de entrada por la que se comunican dos programas."),
        ("Payload", "Contenido concreto que viaja dentro de una peticion."),
        ("Edge", "Procesar cerca del origen, con recursos limitados."),
        ("Serverless", "Funciones que solo consumen recursos al invocarse."),
        ("Cold start", "Penalizacion energetica al activar una funcion tras inactividad."),
        ("Prompt injection", "Esconder ordenes maliciosas en un texto para enganar a una IA."),
        ("WAF", "Cortafuegos de aplicaciones web basado en reglas/firmas."),
        ("Rate limiting", "Limitar el numero de peticiones por unidad de tiempo."),
        ("Estocastico", "Que decide con probabilidades (azar controlado)."),
        ("Teoria de juegos", "Matematica de decisiones entre partes interdependientes."),
        ("Estrategia mixta", "Elegir acciones con probabilidades, no siempre la misma."),
        ("Equilibrio de Nash", "Punto estable donde nadie gana desviandose por su cuenta."),
        ("Principio de indiferencia", "Aleatorizar para dejar al rival indiferente entre sus acciones."),
        ("Payoff", "Lo que gana o pierde un jugador segun las acciones."),
        ("Green Computing", "Disenar tecnologia para gastar menos energia y emitir menos CO2."),
        ("gCO2e", "Gramos de CO2 equivalente emitidos."),
        ("PUE", "Sobrecosto energetico del centro de datos (refrigeracion, etc.)."),
        ("I_grid", "Intensidad de carbono de la electricidad segun la region."),
        ("SCI", "Software Carbon Intensity: metrica de carbono del software."),
        ("TPR / tasa de deteccion", "Porcentaje de ataques reales detectados."),
        ("FPR", "Porcentaje de peticiones legitimas marcadas por error."),
        ("Baseline", "Metodo de referencia con el que se compara."),
        ("Frontera de Pareto", "Mejor compromiso posible entre seguridad y energia."),
        ("seed-7", "Semilla que fija el azar para reproducir experimentos."),
        ("Load shedding", "Descargar trabajo de la capa costosa a la barata."),
    ]
    for term, definition in glossary:
        deflist(doc, term, definition)

    # ---- 12. Referencias ------------------------------------------------- #
    h1(doc, "12. Lecturas y referencias recomendadas")
    refs = [
        "Alpcan & Basar. Network Security: A Decision and Game-Theoretic Approach. Cambridge, 2010.",
        "Manshaei et al. Game theory meets network security and privacy. ACM CSUR, 2013.",
        "Murugesan & Gangadharan (eds.). Harnessing Green IT: Principles and Practices. Wiley, 2012.",
        "Radu. Green Cloud Computing: An Energy-Efficient Ecodesign for IT. Energies, 2017.",
        "Castro et al. The rise of serverless computing. Communications of the ACM, 2019.",
        "Masanet et al. Recalibrating global data center energy-use estimates. Science, 2020.",
        "OWASP Top 10 for Large Language Model Applications (2023-2025).",
        "OWASP API Security Top 10 (2023).",
        "Green Software Foundation. Software Carbon Intensity (SCI) Specification, 2024.",
    ]
    for ref in refs:
        bullet(doc, ref)

    return doc


def main() -> None:
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "Fundamentos_SGE.docx")
    doc = build()
    doc.save(out_path)
    print(f"Documento generado: {out_path}")


if __name__ == "__main__":
    main()
