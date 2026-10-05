import datetime
import json
import re
import time
import unicodedata
from pathlib import Path

import cerebro as nucleo
import configuracion
from textos import cantidad, decimal, miles

TOPE_CHARLAS = 8
POR_CHARLA = 3
ANCHO = 240
TAPADO = "[tapado]"
CANDIDATOS = (b'"type":"text"', b'"role":"user","content":"')
SALTEAR = ("isMeta", "isCompactSummary", "isVisibleInTranscriptOnly", "isSidechain")
MAQUINA = ("system-reminder", "command-name", "command-message", "command-args", "local-command-stdout",
           "local-command-stderr", "local-command-caveat", "task-notification", "user-prompt-submit-hook",
           "ide_selection", "ide_opened_file", "bash-input", "bash-stdout", "bash-stderr")
RE_MAQUINA = re.compile(r"<(%s)\b[^>]*>.*?</\1>" % "|".join(MAQUINA), re.S)
RE_PALABRA = re.compile(r"\w+")
RE_ESPACIOS = re.compile(r"\s+")
CLAVES = [re.compile(p, re.S) for p in (
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)",
    r"(?<![\w-])(?:sk|pk|rk)-(?:[A-Za-z]+-)?[A-Za-z0-9_-]{16,}",
    r"(?<![\w-])(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{16,}",
    r"(?<![\w-])re_[A-Za-z0-9_]{16,}",
    r"(?<![\w-])gh[pousr]_[A-Za-z0-9]{20,}",
    r"(?<![\w-])github_pat_[A-Za-z0-9_]{20,}",
    r"(?<![\w-])AKIA[0-9A-Z]{16}(?![\w-])",
    r"(?<![\w-])xox[baprs]-[A-Za-z0-9-]{10,}",
    r"(?<![\w-])eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}",
    r"(?<![\w-])(?=[\w-]*[0-9])(?=[\w-]*[A-Z])(?=[\w-]*[a-z])[A-Za-z0-9_-]{32,}={0,2}(?![\w-])",
)]
NOMBRE_SECRETO = r"(?<![\w.-])[\w.-]{0,60}?(?:password|passwd|pwd|contraseña|clave|secret|token|api[_-]?key|apikey)[\w.-]{0,60}"
VALOR = r"[^\s\"',;]{4,}"
VALOR_RARO = r"(?=[^\s\"',;]*[^\sA-Za-zÀ-ÿ\"',;]|[^\s\"',;]{12,})" + VALOR
DATOS_SECRETOS = [re.compile(r"(?i)(" + NOMBRE_SECRETO + r"[\"']?\s*(?:=>|=)\s*[\"']?)(" + VALOR + ")"),
                  re.compile(r"(?i)(" + NOMBRE_SECRETO + r"[\"']?\s*:\s*[\"']?)(" + VALOR_RARO + ")"),
                  re.compile(r"(?i)(" + NOMBRE_SECRETO + r"\s+(?:es|is)\s+[\"']?)(" + VALOR_RARO + ")")]
ACENTOS = str.maketrans({c: unicodedata.normalize("NFD", c)[0] for c in map(chr, range(0xC0, 0x250))
                         if unicodedata.normalize("NFD", c)[0].isascii() and c.isalpha()})


def carpeta():
    return configuracion.carpeta_de_claude() / "projects"


def archivos():
    raiz = carpeta()
    return sorted(raiz.glob("*/*.jsonl")) if raiz.is_dir() else []


def normal(texto):
    return texto.lower().translate(ACENTOS)


def secretos_propios():
    try:
        clave = (Path(nucleo.DATOS) / "en-vivo" / "clave.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return []
    return [clave] if len(clave) >= 8 else []


def tapar(texto, propios=()):
    for secreto in propios:
        texto = texto.replace(secreto, TAPADO)
    for patron in CLAVES:
        texto = patron.sub(TAPADO, texto)
    for patron in DATOS_SECRETOS:
        texto = patron.sub(lambda m: m.group(1) + TAPADO, texto)
    return texto


def texto_de(contenido):
    if isinstance(contenido, str):
        partes = [contenido]
    elif isinstance(contenido, list):
        partes = [p.get("text", "") for p in contenido if isinstance(p, dict) and p.get("type") == "text"]
    else:
        partes = []
    return RE_MAQUINA.sub("", "\n".join(p for p in partes if isinstance(p, str))).strip()


def mensajes(ruta):
    try:
        archivo = open(ruta, "rb")
    except OSError:
        return
    with archivo:
        for renglon in archivo:
            if not any(c in renglon for c in CANDIDATOS):
                continue
            try:
                dato = json.loads(renglon)
            except ValueError:
                continue
            if not isinstance(dato, dict) or dato.get("type") not in ("user", "assistant") \
                    or any(dato.get(s) for s in SALTEAR):
                continue
            mensaje = dato.get("message")
            texto = texto_de(mensaje.get("content")) if isinstance(mensaje, dict) else ""
            if texto:
                yield {"uuid": dato.get("uuid") or "", "t": str(dato.get("timestamp") or ""), "quien": dato["type"],
                       "cwd": str(dato.get("cwd") or ""), "sesion": str(dato.get("sessionId") or ruta.stem),
                       "texto": texto}


def patrones(consulta):
    palabras = list(dict.fromkeys(normal(p) for p in RE_PALABRA.findall(consulta)))
    return [re.compile(r"(?<!\w)" + re.escape(p)) for p in palabras]


def buscar(consulta):
    buscadas = patrones(consulta)
    ancla = max(range(len(buscadas)), key=lambda i: len(buscadas[i].pattern))
    propios = secretos_propios()
    hallados, vistos, revisados = [], set(), set()
    charlas = 0
    for ruta in archivos():
        charlas += 1
        for m in mensajes(ruta):
            llave = m["uuid"] or (m["sesion"], m["t"], m["texto"][:80])
            if llave in revisados:
                continue
            revisados.add(llave)
            if not all(p.search(normal(m["texto"])) for p in buscadas):
                continue
            tapado = tapar(m["texto"], propios)
            posiciones = [p.search(normal(tapado)) for p in buscadas]
            if not all(posiciones):
                continue
            m["texto"] = tapado
            m["posicion"] = posiciones[ancla].start()
            hallados.append(m)
    return hallados, charlas, len(revisados)


def fecha(marca):
    try:
        d = datetime.datetime.fromisoformat(marca.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return "?"
    return f"{d.day}/{d.month} {d:%H:%M}"


def recorte(m):
    texto = m["texto"]
    inicio = max(0, m["posicion"] - ANCHO // 3)
    fin = min(len(texto), inicio + ANCHO)
    pedazo = RE_ESPACIOS.sub(" ", texto[inicio:fin]).strip()
    return ("…" if inicio else "") + pedazo + ("…" if fin < len(texto) else "")


def main(consulta, cuantas=TOPE_CHARLAS):
    if not patrones(consulta):
        print('Falta qué buscar: --charlas "palabras".')
        return 2
    comienzo = time.perf_counter()
    hallados, charlas, revisados = buscar(consulta)
    segundos = time.perf_counter() - comienzo
    quien = {"user": nucleo.CONFIG.get("usuario") or "Vos", "assistant": "Claude"}
    por_charla = {}
    for m in sorted(hallados, key=lambda x: x["t"]):
        por_charla.setdefault(m["sesion"], []).append(m)
    orden = sorted(por_charla.values(), key=lambda lista: lista[-1]["t"], reverse=True)
    busque = (f"busqué en {cantidad(charlas, 'charla', 'charlas')} y {miles(revisados)} mensajes, "
              f"{decimal(segundos)} s")
    if not hallados:
        print(f"«{consulta}» no aparece en las charlas guardadas ({busque}).")
        return 0
    print(f"«{consulta}» en las charlas viejas: {cantidad(len(hallados), 'mensaje', 'mensajes')} en "
          f"{cantidad(len(orden), 'charla', 'charlas')} ({busque}). Solo lo que escribieron "
          f"{quien['user']} y Claude, nunca lo que devolvieron las herramientas; lo que parece una clave sale tapado.")
    for lista in orden[:cuantas]:
        primera, ultima = lista[0], lista[-1]
        tramo = fecha(primera["t"]) if len(lista) == 1 else f"del {fecha(primera['t'])} al {fecha(ultima['t'])}"
        print(f"\nCharla {primera['sesion'][:8]} ({ultima['cwd'] or 'sin carpeta'}), {tramo}: "
              f"{cantidad(len(lista), 'mensaje', 'mensajes')}")
        for m in lista[-POR_CHARLA:]:
            print(f"  {fecha(m['t'])} {quien[m['quien']]}: {recorte(m)}")
        if len(lista) > POR_CHARLA:
            print(f"  … y {len(lista) - POR_CHARLA} más antes en esta charla.")
    if len(orden) > cuantas:
        print(f"\n… y {cantidad(len(orden) - cuantas, 'charla más', 'charlas más')} (--cuantos N para verlas).")
    return 0
