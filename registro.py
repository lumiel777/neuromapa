import json
import math
import re

OPCIONES_CONSULTA = ("sobre", "buscar", "parecidas", "salud", "entidad", "mapa", "choques", "gasto", "lecciones",
                     "aprendido", "proponer-hechos", "aprobar-hecho")
VENTANA_CHOQUE = 15 * 60
T_DE_LINEA = re.compile(rb'\{\s*"t"\s*:\s*(-?[0-9][0-9.eE+\-]*)')
PRUEBAS = "sesiones-de-prueba.txt"
RE_SESION = re.compile(r"[0-9a-f]{8}\Z")


def sesiones_de_prueba(en_vivo):
    try:
        with open(en_vivo / PRUEBAS, encoding="utf-8") as f:
            return frozenset(linea.strip() for linea in f if RE_SESION.match(linea.strip()))
    except OSError:
        return frozenset()


def de_prueba(ev, pruebas):
    return bool(ev.get("z")) or str(ev.get("s") or "") in pruebas


def numero(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return 0
    return valor if math.isfinite(valor) else 0


def archivos_desde(en_vivo, desde):
    fechados = []
    for archivo in en_vivo.glob("eventos-*.jsonl"):
        try:
            fechado = archivo.stat().st_mtime
        except OSError:
            continue
        if fechado >= desde:
            fechados.append((fechado, archivo.name, archivo))
    fechados.sort()
    return [archivo for _, _, archivo in fechados] + [en_vivo / "eventos.jsonl"]


def lineas_desde(en_vivo, desde):
    for archivo in archivos_desde(en_vivo, desde):
        try:
            yield from archivo.read_bytes().split(b"\n")
        except OSError:
            continue


def eventos(lineas, desde, marcas=()):
    for linea in lineas:
        if marcas and not any(m in linea for m in marcas):
            continue
        previo = T_DE_LINEA.match(linea)
        if previo:
            try:
                if float(previo.group(1)) < desde:
                    continue
            except ValueError:
                pass
        try:
            ev = json.loads(linea.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, RecursionError):
            continue
        if isinstance(ev, dict) and numero(ev.get("t")) >= desde:
            yield ev
