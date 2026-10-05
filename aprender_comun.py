import gzip
import json
import math
import re
import tempfile
import time

import configuracion
import consultas
import permisos
import registro
from archivos import EXT_CODIGO, es_sensible

PRUEBAS = registro.PRUEBAS
ARCHIVO = "aprendido.json"
CANDADO = "aprendido.lock"
SIGUE = "aprendido.sigue"
VISTO = "aprendido.visto"
VERSION = 3
VIDA_MEDIA = 14 * 86400
VENTANA_COMPLETA = 4 * VIDA_MEDIA
CADA = 10 * 60
VENTANA = 8
HUECO = 30 * 60
MISMO_PEDIDO = 30
SEGUIR = 30 * 60
DESPUES_DE_PISTA = 10
PISTAS_ABIERTAS = 3
PESO_PISTA = 0.5
PESO_PROPIO = 0.5
MINIMO = 0.1
VECINOS = 30
VISTOS = 300
PARES = 3000
DIAS = 14
TANDA = 100000
SEGUNDOS = 2.5
MARGEN = 60
MINIMO_CHARLAS = 0.3
PREFIJO_CHARLA = "charla:"
HERRAMIENTAS_CHARLA = {"Read": "leer", "NotebookRead": "leer", "Edit": "editar", "MultiEdit": "editar",
                       "NotebookEdit": "editar", "Write": "crear"}
APOYO = 1.5
MOSTRAR = 8
FUERZA_MINIMA = 0.1
FUERZA_CODIGO = 0.15
PARTE_PROYECTO = 0.05
MINIMO_PROYECTO = 20
PARTES_CORTO = 3
MOSTRADAS_MINIMAS = 3
PESO_GENERAL = 3
PREMIO_PISTA = 0.1
RECIENTE = 3 * 3600
MEDIA_RECIENTE = 3600
PESO_RECIENTE = 0.25
A_MANO = 30 * 60
COLA = 1024 * 1024
FUERZA_MAPA = 0.2
ARISTAS_MAPA = 150
OLVIDOS = 2000
MOSTRAR_DETALLE = 12
ESPERA_OLVIDO = 5.0
APAGADO = "El aprendizaje está apagado («aprender»: false en config.json): no anota ni usa nada."
TOQUES = ("leer", "editar", "crear")
CAMPOS_DIA = ("pedidos", "toques", "pistas", "seguidas", "notas", "notas_ap", "seguidas_ap", "codigo", "codigo_visto",
              "codigo_ap", "codigo_ap_visto", "utiles", "pistas_sa", "utiles_sa", "notas_sa", "seguidas_sa", "codigo_sa",
              "codigo_visto_sa")
RE_SESION = registro.RE_SESION
RE_WORKTREE = re.compile(r"[\\/]\.claude[\\/]worktrees[\\/][^\\/]+", re.I)
RE_AJENO = re.compile(r"/(?:node_modules|\.git|__pycache__|\.next|\.venv|venv|site-packages)/")
RE_ROTADO = re.compile(r"^eventos-(\d{8}-\d{6}(?:-\d+)?)\.jsonl(\.gz)?\Z")
TEMPORAL = consultas.clave(tempfile.gettempdir()).rstrip("/") + "/claude/"
CHATS = consultas.clave(configuracion.carpeta_de_claude() / "projects").rstrip("/") + "/"


def en_vivo():
    return configuracion.actual()["datos"] / "en-vivo"


def prendido():
    try:
        return configuracion.actual()["aprender"]
    except Exception:
        return False


def mas_nueva(crudo):
    version = crudo.get("version") if isinstance(crudo, dict) else None
    return isinstance(version, int) and not isinstance(version, bool) and version > VERSION


def pruebas(carpeta):
    return set(registro.sesiones_de_prueba(carpeta))


def marcar_pruebas(carpeta, sesiones):
    nuevas = sorted({str(s)[:8] for s in sesiones if RE_SESION.match(str(s)[:8])} - pruebas(carpeta))
    if nuevas:
        permisos.crear(carpeta)
        with open(carpeta / PRUEBAS, "a", encoding="utf-8", newline="\n") as f:
            f.write("".join(f"{s}\n" for s in nuevas))
    return len(nuevas)


def sesion_de_corrida(crudo):
    for linea in crudo.splitlines()[:5]:
        try:
            evento = json.loads(linea)
        except ValueError:
            continue
        if isinstance(evento, dict) and isinstance(evento.get("session_id"), str):
            return evento["session_id"]
    return None


def clave(ruta):
    return consultas.clave(ruta)


def nombre(c):
    return c.rsplit("/", 1)[-1]


def util(c):
    if not c or "://" in c or c.endswith("/") or "." not in nombre(c) or es_sensible(c):
        return False
    if c.startswith(TEMPORAL) or "/tool-results/" in c or RE_AJENO.search(c):
        return False
    return not c.startswith(CHATS) or "/memory/" in c


def rutas_de(ev):
    rutas = [ev["f"]] if isinstance(ev.get("f"), str) else []
    fs = ev.get("fs")
    if ev.get("k") == "leer" and isinstance(fs, list):
        rutas += [r for r in fs[:5] if isinstance(r, str)]
    return rutas


def dia_de(t):
    try:
        return time.strftime("%Y-%m-%d", time.localtime(t))
    except (OverflowError, OSError, ValueError):
        return "sin-fecha"


def numeros(valor, largo):
    return isinstance(valor, list) and len(valor) == largo and all(es_numero(x) for x in valor)


def es_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def tabla(valor):
    return valor if isinstance(valor, dict) else {}


def textos(valor):
    return isinstance(valor, list) and all(isinstance(x, str) for x in valor)


def registros(carpeta, desde):
    rotados = {}
    for archivo in carpeta.glob("eventos-*.jsonl*"):
        m = RE_ROTADO.match(archivo.name)
        if not m:
            continue
        try:
            if archivo.stat().st_mtime < desde:
                continue
        except OSError:
            continue
        if m.group(1) not in rotados or not m.group(2):
            rotados[m.group(1)] = archivo
    return [rotados[k] for k in sorted(rotados)] + [carpeta / "eventos.jsonl"]


def lineas_de(archivos):
    for archivo in archivos:
        try:
            crudo = archivo.read_bytes()
            if archivo.name.endswith(".gz"):
                crudo = gzip.decompress(crudo)
        except (OSError, EOFError, gzip.BadGzipFile):
            continue
        yield from crudo.split(b"\n")


def es_nota(c):
    return c.endswith(".md")


def raices():
    import cerebro as nucleo
    return [clave(p["raiz"]) for p in nucleo.CONFIG["proyectos"]] + [clave(c) for c in nucleo.carpetas_propias()]


def raiz_de(c, lista):
    return max((r for r in lista if c == r or c.startswith(r + "/")), key=len, default=c)


def proyecto_de(c, lista):
    r = raiz_de(c, lista)
    return r if r in lista else ""


def es_de_codigo(c):
    return "." in nombre(c) and c.rsplit(".", 1)[-1] in EXT_CODIGO


def decimal(x):
    return format(x, ".2f").replace(".", ",")
