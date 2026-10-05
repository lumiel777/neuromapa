import json
import time

import configuracion
import gasto
from textos import cantidad, decimal

DIA = 86400
RECIENTE = 2 * DIA
PROPIAS = ("Edit", "Write", "Read", "MultiEdit", "NotebookEdit", "Glob", "Grep")
MARCAS = (b'"tool_use"', b'"is_error":true')
CATEGORIAS = [
    ("editar sin leer", ("file has not been read yet",),
     "Leer el archivo con Read antes de editarlo, y por la misma ruta con la que se lo va a editar (Claude Code exige "
     "haberlo leído en este chat; una carpeta vista por dos caminos cuenta como dos archivos)."),
    ("cambiado por otro", ("modified since read", "has been modified since"),
     "Otro chat, un agente o un programa lo cambió después de leerlo: releerlo justo antes de editar (y mirar "
     "{neuromapa} --choques)."),
    ("texto que no está", ("string to replace not found",),
     "Antes de un Edit, releer el tramo exacto: el texto cambió, o tiene otros espacios o finales de línea."),
    ("texto repetido", ("matches of the string to replace",),
     "Dar más contexto para que el texto a cambiar sea único, o usar replace_all si van todos."),
    ("cambio que no cambia nada", ("no changes to make",),
     "El cambio no cambiaba nada: revisar qué se quería cambiar antes de repetirlo."),
    ("ruta que no existe", ("file does not exist", "path does not exist"),
     "Comprobar la ruta antes de leerla (Glob), con cuidado en las carpetas con espacios."),
    ("archivo demasiado grande", ("exceeds maximum allowed tokens",),
     "Leer por partes (offset y limit) o ir derecho al tramo con {neuromapa} --mapa o Grep."),
    ("parámetros inválidos", ("inputvalidationerror",),
     "Revisar los parámetros de la herramienta antes de llamarla."),
]


def primera_linea(contenido):
    if isinstance(contenido, list):
        contenido = " ".join(x.get("text", "") for x in contenido if isinstance(x, dict))
    return str(contenido or "").strip().split("\n", 1)[0].lower()


def categoria(texto):
    for nombre, pistas, _ in CATEGORIAS:
        if any(p in texto for p in pistas):
            return nombre
    return None


def errores(desde, casa=None):
    salida = []
    for archivo in gasto.transcripciones(desde, casa):
        de_agente = archivo.parent.name == "subagents"
        sesion = archivo.parent.parent.name if de_agente else archivo.stem
        nombres = {}
        try:
            with open(archivo, "rb") as f:
                for linea in f:
                    salida += errores_del_renglon(linea, nombres, sesion, desde)
        except OSError:
            continue
    return salida


def errores_del_renglon(linea, nombres, sesion, desde):
    if not any(m in linea for m in MARCAS):
        return []
    try:
        d = json.loads(linea)
    except ValueError:
        return []
    mensaje = d.get("message") if isinstance(d, dict) else None
    contenido = mensaje.get("content") if isinstance(mensaje, dict) else None
    if not isinstance(contenido, list):
        return []
    salida = []
    for c in contenido:
        if not isinstance(c, dict):
            continue
        if c.get("type") == "tool_use":
            nombres[c.get("id")] = str(c.get("name") or "")
        elif c.get("type") == "tool_result" and c.get("is_error"):
            herramienta = nombres.get(c.get("tool_use_id"), "")
            t = gasto.epoca(d.get("timestamp"))
            if herramienta not in PROPIAS or t is None or t < desde:
                continue
            salida.append({"t": t, "sesion": sesion, "herramienta": herramienta,
                           "categoria": categoria(primera_linea(c.get("content")))})
    return salida


def resumir(lista, ahora, dias):
    grupos = {}
    for e in lista:
        g = grupos.setdefault(e["categoria"], {"veces": 0, "sesiones": set(), "recientes": 0, "herramientas": set()})
        g["veces"] += 1
        g["sesiones"].add(e["sesion"])
        g["herramientas"].add(e["herramienta"])
        g["recientes"] += 1 if ahora - e["t"] <= RECIENTE else 0
    salida = []
    for nombre, leccion in [(n, l) for n, _, l in CATEGORIAS] + [(None, "")]:
        g = grupos.get(nombre)
        if not g:
            continue
        antes_dias = max(dias - RECIENTE / DIA, 1)
        por_dia_antes = (g["veces"] - g["recientes"]) / antes_dias
        por_dia_ahora = g["recientes"] / (RECIENTE / DIA)
        tendencia = ("bajó" if por_dia_ahora < por_dia_antes * 0.6 else "subió" if por_dia_ahora > por_dia_antes * 1.4
                     else "sigue igual")
        salida.append({"categoria": nombre or "otros errores", "leccion": leccion.replace("{neuromapa}", configuracion.comando()),
                       "veces": g["veces"],
                       "chats": len(g["sesiones"]), "recientes": g["recientes"], "herramientas": sorted(g["herramientas"]),
                       "porDiaAntes": por_dia_antes, "porDiaAhora": por_dia_ahora, "tendencia": tendencia if dias > 2 else ""})
    return sorted(salida, key=lambda x: (x["categoria"] == "otros errores", -x["veces"]))


def por_dia(n):
    return decimal(n).replace(",0", "")


def texto(resumen, dias):
    if not resumen:
        return [f"Lecciones (últimos {dias} días): ningún error repetido de las herramientas de archivos."]
    lineas = [f"Lecciones (últimos {dias} días): errores de las herramientas de archivos que se repiten, con la "
              "regla que los evitaría y si están bajando (últimos 2 días contra los anteriores)."]
    for i, r in enumerate(resumen, 1):
        veces = cantidad(r["veces"], "vez", "veces")
        chats = cantidad(r["chats"], "chat", "chats")
        linea = f'{i}. {r["categoria"]} ({", ".join(r["herramientas"])}): {veces} en {chats}'
        if r["tendencia"]:
            linea += (f' · {por_dia(r["porDiaAhora"])} por día los últimos 2 días contra {por_dia(r["porDiaAntes"])} '
                      f'antes: {r["tendencia"]}')
        lineas.append(linea)
        if r["leccion"]:
            lineas.append(f'   Lección: {r["leccion"]}')
    usuario = configuracion.actual()["usuario"] or "el usuario"
    lineas.append(f"Para que una quede como regla, va a la memoria (lo decide {usuario}); "
                  "después esta misma cuenta dice si dejó de pasar.")
    return lineas


def main(dias=7):
    dias = max(1, min(60, int(dias)))
    ahora = time.time()
    for linea in texto(resumir(errores(ahora - dias * DIA), ahora, dias), dias):
        print(linea)
    return 0
