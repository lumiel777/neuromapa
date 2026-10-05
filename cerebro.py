import argparse
import base64
import bisect
import datetime
import fnmatch
import hashlib
import importlib
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

import configuracion
import registro
from archivos import es_sensible, escribir_atomico
from textos import cantidad, decimal, detalle

CARPETA = Path(__file__).resolve().parent
MARCADOR = "/*__CEREBRO__*/"
VENDOR = CARPETA / "vendor"
RE_LIBRERIA = re.compile(r"const (URL_\w+) = '(https://[^']+)';")
RE_INTEGRIDAD = re.compile(r"\[(URL_\w+)\]: '(sha384-[A-Za-z0-9+/=]+)'")
LIMITE_TEXTO = 60000
NOMBRES_SALUD = {"rotos": "Enlaces rotos", "huerfanos": "Huérfanas", "sinIndice": "Memorias sin índice",
                 "indiceRoto": "Índice roto", "ambiguos": "Menciones ambiguas", "handoffsAbiertos": "Handoffs abiertos",
                 "respuestasSinAcuse": "Respuestas sin acuse", "medico": "Del médico", "anclas": "Anclas a revisar",
                 "hechos": "Hechos a revisar", "repiteClaude": "Memorias que repiten el CLAUDE.md",
                 "memoriasParecidas": "Memorias parecidas"}
try:
    CONFIG = configuracion.actual()
except configuracion.ConfigInvalida as error:
    if __name__ != "__main__":
        raise
    sys.exit(f"Error en la configuración: {error}")
DATOS = CONFIG["datos"]


def carpetas_propias():
    propias = [CARPETA] + ([DATOS] if (Path(DATOS) / "cerebro.py").is_file() else [])
    return list(dict.fromkeys(os.path.normpath(str(c)) for c in propias))


FUENTES = CONFIG["fuentes"]
GRUPOS_REGISTRO = {f["id"] for f in FUENTES if f.get("registro")}
GRUPOS_HISTORICOS = {f["id"] for f in FUENTES if f.get("historico")}

CARPETAS_PODADAS = set(CONFIG["podar"])
PODAR_SI_CONTIENE = CONFIG["podar_si_contiene"]
CARPETAS_PESADAS = CONFIG["carpetas_pesadas"]
FRAGMENTOS_EXCLUIDOS = CONFIG["excluir_fragmentos"]
RAICES_PROYECTO = [(p["raiz"], p["marca"]) for p in CONFIG["proyectos"]]
HANDOFFS = CONFIG["handoffs"]
NUNCA = r"(?!)"
PREFIJO_HANDOFF = HANDOFFS["prefijo"].lower() if HANDOFFS else ""
RE_PREFIJO = re.escape(HANDOFFS["prefijo"]) if HANDOFFS else NUNCA
LADO_DE_PALABRA = {p: lado["id"] for lado in (HANDOFFS["lados"] if HANDOFFS else []) for p in lado["palabras"]}
FUERZA = {"wiki": 0, "indice": 1, "enlace": 2, "responde": 3, "mencion": 4, "carpeta": 5}
ORDEN_CLASES = ["wiki", "indice", "enlace", "responde", "mencion", "carpeta", "cadena", "sugerida", "parecida", "comparte",
                "aprendida", "duplicado"]
NOMBRE_CLASE = {"wiki": "Wiki [[…]]", "indice": "Índice", "enlace": "Enlace", "responde": "Responde", "mencion": "Mención",
                "carpeta": "Carpeta", "cadena": "Cadena", "sugerida": "Sugerida", "parecida": "Parecida",
                "comparte": "Comparte", "aprendida": "Aprendida", "duplicado": "Duplicado"}
NOMBRE_TIPO = {"instrucciones": "Instrucciones", "indice": "Índice", "user": "Usuario", "feedback": "Feedback",
               "project": "Proyecto", "reference": "Referencia", "doc": "Documento", "handoff": "Handoff"}
SEPARADORES = "\\/"
DELIMITADORES = set(" \t\r\n`'\"<>|*?()[]{},;=")

RE_MD = re.compile(r"\.md(?!\w)", re.I)
RE_WIKI = re.compile(r"\[\[([^\[\]\n|#]{1,150})(?:[|#][^\[\]\n]*)?\]\]")
RE_ENLACE = re.compile(r"\[([^\[\]\n]*)\]\(\s*(<[^>\n]+>|[^)\s]+)(?:\s+[\"'][^\"'\n]*[\"'])?\s*\)")
RE_INDICE = re.compile(r"^[ \t]*[-*+][ \t]+\[([^\]\n]+)\]\(\s*<?([^)\s>]+)>?\s*\)[ \t]*(?:[—–-]+[ \t]*)?(.*)$", re.M)
RE_HANDOFF = re.compile(f"(?<![\\w\\-.]){RE_PREFIJO}_(\\d+)(?![\\w\\-])(?!\\.md)", re.I)
RE_HANDOFF_ARCHIVO = re.compile(f"^{RE_PREFIJO}(?:_(\\d+))?(?:_[^.]*)?\\.md$", re.I)
RE_TOKEN = re.compile(r"(?<![\w\-])\w+(?:-\w+)+(?![\w\-])")
RE_GENERICO = re.compile(r"(?<!\w)(?:un|una|unos|unas|cualquier|cada|alg[uú]n|otros?|otras?|varios|varias|los|las|tus|sus|"
                         r"an|any|each|every|some|other|your|their)\s+[`\"'«]?\Z", re.I)
RE_ESQUEMA = re.compile(r"^[a-z][a-z0-9+.\-]+:", re.I)
RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
RE_META = re.compile(r"^(?:escrito\b|fecha\s*:|estado\s*:)", re.I)
RE_REGLA = re.compile(r"[-*_=\s]{3,}")
REF_HANDOFF = f"(?:{RE_PREFIJO}_)?(\\d+)(?:\\.md)?(?![\\w\\-])"
RE_CAB_FECHA = re.compile(r"\bEscrito\s+(?:el\s+)?(\d{4}-\d{2}-\d{2})", re.I)
RE_CAB_LADO = re.compile(r"\bdesde\s+el\s+(?:chat|lado)\s+(?:de\s+la|del)\s+("
                         + ("|".join(re.escape(p) for p in sorted(LADO_DE_PALABRA, key=len, reverse=True)) or NUNCA)
                         + r")\b", re.I)
RE_RESPONDE = re.compile(r"(?<!no\s)\b(?:(?:responde|sigue)\s+(?:al|a)|retoma(?:\s+el\s+punto\s+\d+)?\s+(?:del|de|al|a))\s+"
                         + REF_HANDOFF + r"((?:\s*,?\s+y\s+(?:al|a)\s+" + REF_HANDOFF.replace("(\\d+)", "\\d+") + r")*)", re.I)
RE_RESPONDE_DOC = re.compile(r"(?<!no\s)\bresponde\s+(?:al|a)\s+([\w\-.]+?\.md)(?![\w\-])", re.I)
RE_TITULO_RESPUESTA = re.compile(f"\\brespuesta\\s+al\\s+(?:handoff\\s+)?{REF_HANDOFF}", re.I)
RE_SIN_RESPUESTA = re.compile(r"\bno\s+responde\b|\babre\s+tema\b|\bpedido\s+nuevo\b|\bnuevo\s+pedido\b"
                              r"|\bindependiente\s+del?\b", re.I)
RE_CIERRA = re.compile(r"\bcierra\s+el\s+tema\b|\bno\s+pide\s+nada\b", re.I)
RE_CLASES_PAGINA = re.compile(r"\bconst\s+ORDEN_CLASES\s*=\s*\[([^\]]*)\]")
EQUIVALENTE_EN_PAGINA = {"responde": "cadena", "carpeta": "mencion"}
RE_PIDE = re.compile(r"(?<!no\s)\b(?:pide|piden|pedimos|pregunta|preguntan|preguntamos|necesita|necesitan|necesitamos"
                     r"|esperamos|esperan)\b|¿", re.I)
RE_CERRADO_AJENO = re.compile(r"\b(?:el|al)\s+(\d+)\b[^.;:]{0,30}?\bqued[óo]\s+(?:le[ií]do|respondido|cerrado)"
                              r"|\bda\s+por\s+recibido\s+el\s+(\d+)\b", re.I)
RE_NUMERO = re.compile(r"\d+")
RE_ENCABEZADO = re.compile(r"^ {0,3}(#{1,4})[ \t]+(.+?)[ \t#]*$")
RE_ARCHIVO = re.compile(r"\((?:archivo|archive|archived)\)", re.I)
TRAMO_ABIERTOS = 20


def avisar(mensaje):
    print(f"Aviso: {mensaje}", file=sys.stderr)


def es_changelog(ruta):
    return Path(ruta).stem.lower().startswith("changelog")


def es_archivo(nodo):
    return bool(RE_ARCHIVO.search(nodo.get("titulo") or ""))


def es_historica(nodo):
    return nodo["grupo"] in GRUPOS_HISTORICOS or es_changelog(nodo["ruta"]) or es_archivo(nodo)


def normalizar(ruta):
    return os.path.normpath(str(ruta)).replace("/", "\\").lower()


def es_de_red(ruta):
    return str(ruta).strip().replace("/", "\\").startswith("\\\\")


CLAUDE_EXCLUIDA = [normalizar(r) for r in CONFIG["excluir_claude_bajo"]]


def excluido(ruta):
    clave = normalizar(ruta)
    if any(f in clave for f in FRAGMENTOS_EXCLUIDOS):
        return True
    return "\\.claude\\" in clave and any(clave.startswith(f"{base}\\") for base in CLAUDE_EXCLUIDA)


def carpeta_podada(nombre):
    n = nombre.lower()
    return n in CARPETAS_PODADAS or any(f in n for f in PODAR_SI_CONTIENE)


def carpeta_pesada(nombre):
    n = nombre.lower()
    return next((p for p in CARPETAS_PESADAS if p["contiene"] in n), None)


def saltea_pesada(carpetas):
    for i, carpeta in enumerate(carpetas[:-1]):
        pesada = carpeta_pesada(carpeta)
        if pesada and carpetas[i + 1] not in pesada["bajar_solo"]:
            return True
    return False


def fuente_de_ruta(ruta):
    clave = normalizar(ruta)
    if not clave.endswith(".md") or excluido(clave):
        return None
    for fuente in FUENTES:
        for raiz, recursivo, _ in fuente["raices"]:
            base = normalizar(raiz)
            if not clave.startswith(f"{base}\\"):
                continue
            carpetas = clave[len(base) + 1:].split("\\")[:-1]
            if not recursivo:
                if not carpetas:
                    return fuente
                continue
            if any(carpeta_podada(c) for c in carpetas) or saltea_pesada(carpetas):
                continue
            return fuente
    return None


def dentro_de_fuentes(ruta):
    return fuente_de_ruta(ruta) is not None


_listados = {}
podadas = {}
delicadas = {}


def archivo_propio(ruta, raiz):
    destino = os.path.normcase(os.path.realpath(ruta))
    base = os.path.normcase(os.path.realpath(raiz)).rstrip("\\/")
    return os.path.isfile(destino) and destino.startswith(base + os.sep)


def listar(raiz, recursivo, avisar_si_falta=True):
    llave = (normalizar(raiz), recursivo)
    if llave in _listados:
        return _listados[llave]
    base = Path(raiz)
    salida = []

    def sumar(ruta):
        if es_sensible(ruta):
            delicadas[normalizar(ruta)] = str(ruta)
        else:
            salida.append(ruta)

    if not base.is_dir():
        if avisar_si_falta:
            avisar(f"no existe la carpeta {base}")
    elif not recursivo:
        for p in base.iterdir():
            if p.suffix.lower() == ".md" and archivo_propio(p, base):
                sumar(p)
    else:
        for actual, carpetas, archivos in os.walk(base):
            carpetas[:] = [c for c in carpetas if not carpeta_podada(c)]
            for c in [c for c in carpetas if es_sensible(os.path.join(actual, c))]:
                delicadas[normalizar(os.path.join(actual, c))] = os.path.join(actual, c)
            carpetas[:] = [c for c in carpetas if not es_sensible(os.path.join(actual, c))]
            pesada = carpeta_pesada(os.path.basename(actual))
            if pesada:
                salteadas = [c for c in carpetas if c.lower() not in pesada["bajar_solo"]]
                if salteadas:
                    podadas[normalizar(actual)] = (actual, len(salteadas))
                carpetas[:] = [c for c in carpetas if c.lower() in pesada["bajar_solo"]]
            for a in archivos:
                if a.lower().endswith(".md") and archivo_propio(Path(actual) / a, base):
                    sumar(Path(actual) / a)
    salida.sort(key=lambda p: orden_natural(str(p)))
    _listados[llave] = salida
    return salida


def huella(extras=()):
    _listados.clear()
    vistos = set()
    partes = []
    for fuente in FUENTES:
        for raiz, recursivo, _ in fuente["raices"]:
            for ruta in listar(raiz, recursivo, False):
                clave = normalizar(ruta)
                if clave in vistos or excluido(clave):
                    continue
                vistos.add(clave)
                partes.append((clave,) + firma(ruta))
    for ruta in extras:
        partes.append((normalizar(ruta),) + firma(ruta))
    return tuple(partes)


def firma(ruta):
    try:
        s = os.stat(ruta)
    except OSError:
        return (None, None)
    return (s.st_mtime_ns, s.st_size)


def orden_natural(texto):
    return [int(t) if t.isdecimal() else t.lower() for t in re.split(r"(\d+)", texto)]


def leer_texto(ruta):
    crudo = ruta.read_bytes()
    for codificacion in ("utf-8-sig", "cp1252"):
        try:
            return crudo.decode(codificacion), len(crudo)
        except UnicodeDecodeError:
            continue
    return None, len(crudo)


def desentrecomillar(valor):
    v = valor.strip()
    if len(v) >= 2 and v[0] == v[-1] == '"':
        try:
            return json.loads(v)
        except ValueError:
            return v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1].replace("''", "'")
    return v


def separar_frontmatter(texto):
    lineas = texto.split("\n")
    if not lineas or lineas[0].strip() != "---":
        return {}, texto
    fin = None
    for i in range(1, len(lineas)):
        if lineas[i].strip() in ("---", "..."):
            fin = i
            break
    if fin is None:
        return {}, texto
    datos = {}
    padre = None
    for linea in lineas[1:fin]:
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        m = re.match(r"^(\s*)([\w\-]+)\s*:\s*(.*)$", linea)
        if not m:
            continue
        sangria, clave, valor = m.groups()
        if not sangria:
            if valor.strip() == "":
                datos[clave] = {}
                padre = clave
            else:
                datos[clave] = desentrecomillar(valor)
                padre = None
        elif padre is not None:
            datos[padre][clave] = desentrecomillar(valor)
    if not datos:
        return {}, texto
    return datos, "\n".join(lineas[fin + 1:])


def valores_frontmatter(frontmatter):
    salida = []
    for valor in frontmatter.values():
        if isinstance(valor, dict):
            salida.extend(v for v in valor.values() if isinstance(v, str) and v.strip())
        elif isinstance(valor, str) and valor.strip():
            salida.append(valor)
    return salida


def proyecto_de_ruta(ruta_normalizada):
    for raiz, _ in RAICES_PROYECTO:
        base = normalizar(raiz)
        if ruta_normalizada.startswith(f"{base}\\"):
            return base
    return None


MARCA_DE_PROYECTO = {normalizar(raiz): marca for raiz, marca in RAICES_PROYECTO}
ALIAS_PROYECTO = {normalizar(p["raiz"]): p["alias"] for p in CONFIG["proyectos"]}
PISTAS_DE_PROYECTO = tuple(sorted({pista for p in CONFIG["proyectos"] for pista in p["pistas"]}))


def proyecto_unico(texto, permitidos=None):
    minusculas = texto.lower()
    if not any(pista in minusculas for pista in PISTAS_DE_PROYECTO):
        return None
    marcados = [raiz for raiz, marca in MARCA_DE_PROYECTO.items()
                if (permitidos is None or raiz in permitidos) and marca.search(texto)]
    return marcados[0] if len(marcados) == 1 else None


def dato(frontmatter, clave, primero_metadata=False):
    meta = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
    arriba = frontmatter.get(clave)
    arriba = arriba if isinstance(arriba, str) else ""
    abajo = meta.get(clave, "")
    abajo = abajo if isinstance(abajo, str) else ""
    return (abajo or arriba) if primero_metadata else (arriba or abajo)


def formatear_fecha(valor):
    s = str(valor).strip()
    if not s:
        return ""
    try:
        d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return s[:16].replace("T", " ")
    if d.tzinfo is not None:
        d = d.astimezone()
    return d.strftime("%Y-%m-%d %H:%M")


def limpiar_md(s):
    s = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]", r"\1", s)
    s = s.replace("**", "").replace("`", "")
    s = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def recortar(s, largo):
    return s if len(s) <= largo else f"{s[:largo - 1].rstrip()}…"


def primer_encabezado(cuerpo):
    en_codigo = False
    for linea in cuerpo.split("\n"):
        s = linea.strip()
        if s.startswith("```") or s.startswith("~~~"):
            en_codigo = not en_codigo
            continue
        if en_codigo:
            continue
        m = re.match(r"^ {0,3}#[ \t]+(.+?)[ \t#]*$", linea)
        if m:
            return limpiar_md(m.group(1))
    return ""


def seccionar(cuerpo):
    secciones = []
    lineas = cuerpo.split("\n")
    titulo, nivel, desde = "", 0, 0
    en_codigo = False

    def cerrar(hasta):
        texto = "\n".join(lineas[desde:hasta])
        if titulo or texto.strip():
            secciones.append({"titulo": titulo, "nivel": nivel, "linea": desde, "texto": texto})

    for i, linea in enumerate(lineas):
        s = linea.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            en_codigo = not en_codigo
            continue
        if en_codigo or not s.startswith("#"):
            continue
        m = RE_ENCABEZADO.match(linea)
        if m:
            cerrar(i)
            titulo, nivel, desde = limpiar_md(m.group(2)), len(m.group(1)), i
    cerrar(len(lineas))
    return secciones


def es_meta(s):
    return RE_META.match(limpiar_md(s).lstrip("*_ ")) is not None


def parrafo_y_meta(cuerpo):
    en_codigo = False
    partes = []
    meta = []
    en_meta = False
    cursiva = False
    extendido = False
    largo = 0
    for linea in cuerpo.split("\n"):
        s = linea.strip()
        if s.startswith("```") or s.startswith("~~~"):
            if partes:
                break
            en_meta = False
            en_codigo = not en_codigo
            continue
        if en_codigo:
            continue
        s = re.sub(r"^(>\s*)+", "", s)
        if en_meta:
            if s and not s.startswith("#") and not RE_REGLA.fullmatch(s):
                meta.append(s)
                if cursiva and s.endswith("*"):
                    en_meta = False
                continue
            en_meta = False
        if not s:
            if partes:
                if extendido or largo > 400 or not partes[-1].rstrip("*_ ").endswith(":"):
                    break
                extendido = True
            continue
        if s.startswith("#") or s.startswith("|") or s.startswith("<") or RE_REGLA.fullmatch(s):
            if partes:
                break
            continue
        if not partes and not meta and es_meta(s):
            meta.append(s)
            cursiva = s.startswith("*") or s.startswith("_")
            en_meta = not (cursiva and len(s) > 1 and s.endswith("*"))
            continue
        partes.append(re.sub(r"^([-*+]|\d+\.)\s+", "", s))
        largo += len(partes[-1])
        if largo > 400:
            break
    return limpiar_md(" ".join(partes)), limpiar_md(" ".join(meta))


def leer_cabecera(cuerpo):
    inicio = cuerpo[:3000]
    titulo = primer_encabezado(inicio)
    _, texto = parrafo_y_meta(inicio)
    texto = texto[:900]
    fecha = RE_CAB_FECHA.search(texto)
    lado = RE_CAB_LADO.search(texto)
    lado = lado.group(1).lower() if lado else ""
    respuestas = []
    for m in RE_RESPONDE.finditer(texto):
        numeros = [int(m.group(1))] + [int(n) for n in RE_NUMERO.findall(m.group(2) or "")]
        respuestas.append((numeros, fragmento(texto, m.start(), m.end())))
    for m in RE_TITULO_RESPUESTA.finditer(titulo):
        respuestas.append(([int(m.group(1))], fragmento(titulo, m.start(), m.end())))
    documentos = [(m.group(1), fragmento(texto, m.start(), m.end())) for m in RE_RESPONDE_DOC.finditer(texto)
                  if not re.fullmatch(f"{RE_PREFIJO}_\\d+\\.md", m.group(1), re.I)]
    cerrados = {int(m.group(1) or m.group(2)) for m in RE_CERRADO_AJENO.finditer(texto)}
    return {
        "texto": texto,
        "fecha": fecha.group(1) if fecha else "",
        "lado": LADO_DE_PALABRA.get(lado, ""),
        "respuestas": respuestas,
        "documentos": documentos,
        "ninguno": bool(RE_SIN_RESPUESTA.search(texto)),
        "cierra": bool(RE_CIERRA.search(texto)),
        "pide": bool(RE_PIDE.search(RE_CIERRA.sub("", texto))),
        "cerrados": cerrados,
    }


def fragmento(texto, inicio, fin, ancho=120):
    extra = max(0, ancho - (fin - inicio))
    a = max(0, inicio - extra // 2)
    b = min(len(texto), fin + (extra - (inicio - a)))
    s = re.sub(r"\s+", " ", texto[a:b]).strip()
    return ("…" if a > 0 else "") + s + ("…" if b < len(texto) else "")


def es_nombre(c):
    return c.isalnum() or c in "_-."


def carpeta_nombrada(carpeta, renglon):
    partes = carpeta.split("\\")
    if len(partes) < 3:
        return False
    cola = "\\".join(partes[-2:])
    i = renglon.find(cola)
    while i >= 0:
        fin = i + len(cola)
        if (i == 0 or not es_nombre(renglon[i - 1])) and (fin == len(renglon) or not es_nombre(renglon[fin])):
            return True
        i = renglon.find(cola, i + 1)
    return False


class Cerebro:
    def __init__(self):
        self.nodos = []
        self.por_id = {}
        self.por_ruta = {}
        self.carpeta_de = {}
        self.textos_de = {}
        self.proyecto_de = {}
        self.fuente_de = {}
        self.fuertes = {}
        self.salientes = {}
        self.entrantes = {}
        self.otras = {}
        self.rotos = []
        self.rotos_vistos = set()
        self.ambiguos = []
        self.ambiguos_vistos = set()
        self.indice_roto = []
        self.sin_indice = []
        self.indexadas = set()
        self.por_enlace = {}
        self.titulo_indice = {}
        self.listados_por_indice = {}
        self.spans_indice = {}
        self.trie = {"hijos": {}, "ids": set()}
        self.slugs_memoria = {}
        self.slugs_mencionables = {}
        self.por_nombre_sin_md = {}
        self.handoff_por_numero = {}
        self.cabeceras = {}
        self.declaran = set()
        self.respuestas_rechazadas = []
        self.handoffs_abiertos = []
        self.respuestas_sin_acuse = []
        self.ganchos = {}
        self.secciones_de = {}
        self.proyecto_de_seccion = {}
        self.entidades = {}
        self.citas_commits = {}
        self.pares_comparten = {}
        self.resumen_entidades = None
        self.medico = []
        self.anclas = []
        self.hechos = []
        self.pares_parecidos = {}
        self.memorias_parecidas = []
        self.repite_claude = []
        self.tiempo_parecidas = None
        self.parecidas_recontadas = 0
        self.no_leidos = []
        self.sugerencias_sin_resolver = []
        self.duplicados_juntados = 0
        self.sugeridas_fundidas = 0

    def recolectar(self):
        reclamados = set()
        for fuente in FUENTES:
            patron = fuente.get("patron", "*.md").lower()
            excluir = [e.lower() for e in fuente.get("excluir", [])]
            for raiz, recursivo, alias in fuente["raices"]:
                for ruta in listar(raiz, recursivo):
                    clave = normalizar(ruta)
                    nombre = ruta.name.lower()
                    if clave in reclamados or excluido(ruta):
                        continue
                    if not fnmatch.fnmatchcase(nombre, patron):
                        continue
                    if any(fnmatch.fnmatchcase(nombre, e) for e in excluir):
                        continue
                    reclamados.add(clave)
                    relativa = os.path.relpath(str(ruta), raiz).replace("\\", "/")
                    identificador = fuente["id"] + ":" + (alias + "/" if alias else "") + relativa
                    self.crear_nodo(fuente, ruta, identificador)

    def crear_nodo(self, fuente, ruta, identificador):
        try:
            texto, tamano = leer_texto(ruta)
        except OSError as error:
            self.no_leidos.append(f"{ruta} ({error})")
            return
        if texto is None:
            self.no_leidos.append(f"{ruta} (ni UTF-8 ni cp1252)")
            return
        if identificador in self.por_id:
            avisar(f"id repetido {identificador}")
            return
        texto = texto.replace("\r\n", "\n").replace("\r", "\n")
        frontmatter, cuerpo = separar_frontmatter(texto)
        nombre = ruta.name
        nombre_l = nombre.lower()
        if nombre_l == "memory.md":
            tipo = "indice"
        elif nombre_l == "claude.md":
            tipo = "instrucciones"
        elif PREFIJO_HANDOFF and nombre_l.startswith(PREFIJO_HANDOFF):
            tipo = "handoff"
        elif fuente.get("memoria"):
            tipo = dato(frontmatter, "type", True) or "doc"
        else:
            tipo = "doc"
        slug = dato(frontmatter, "name") or ruta.stem
        estado = ruta.stat()
        modificado = datetime.datetime.fromtimestamp(estado.st_mtime).strftime("%Y-%m-%d %H:%M")
        del_encabezado = formatear_fecha(dato(frontmatter, "modified", True))
        if RE_FECHA.match(del_encabezado):
            modificado = max(modificado, del_encabezado)
        cuerpo_limpio = cuerpo.lstrip("\n")
        recortado = len(cuerpo_limpio) > LIMITE_TEXTO
        if recortado:
            aviso = "\n\n… (recortado: el archivo sigue en disco)"
            cuerpo_limpio = cuerpo_limpio[:LIMITE_TEXTO - len(aviso)] + aviso
        lineas = texto.count("\n") + (0 if texto.endswith("\n") or not texto else 1)
        nodo = {
            "id": identificador,
            "titulo": "",
            "ruta": str(ruta),
            "grupo": fuente["id"],
            "tipo": tipo,
            "slug": slug,
            "descripcion": dato(frontmatter, "description"),
            "modificado": modificado,
            "lineas": lineas,
            "bytes": tamano,
            "texto": cuerpo_limpio,
        }
        if recortado:
            nodo["recortado"] = True
        nodo["_cuerpo"] = cuerpo
        nodo["_cabeza"] = texto[:len(texto) - len(cuerpo)]
        nodo["_desfase"] = nodo["_cabeza"].count("\n")
        antes_del_texto = nodo["_desfase"] + len(cuerpo) - len(cuerpo.lstrip("\n"))
        if antes_del_texto:
            nodo["desfase"] = antes_del_texto
        nodo["_frontmatter"] = frontmatter
        nodo["_firma"] = (estado.st_mtime_ns, estado.st_size)
        if tipo == "handoff":
            cabecera = leer_cabecera(cuerpo)
            self.cabeceras[identificador] = cabecera
            nodo["fecha"] = cabecera["fecha"]
            nodo["lado"] = cabecera["lado"]
        self.nodos.append(nodo)
        self.por_id[identificador] = nodo
        self.por_ruta[normalizar(ruta)] = identificador
        self.carpeta_de[identificador] = normalizar(ruta.parent)
        self.textos_de[identificador] = [cuerpo] + valores_frontmatter(frontmatter)
        if fuente.get("memoria") and fuente.get("proyecto"):
            self.proyecto_de[identificador] = normalizar(fuente["proyecto"])
        else:
            self.proyecto_de[identificador] = proyecto_de_ruta(normalizar(ruta))
        self.fuente_de[identificador] = fuente

    def indexar(self):
        for nodo in self.nodos:
            identificador = nodo["id"]
            partes = normalizar(nodo["ruta"]).split("\\")
            t = self.trie
            for componente in reversed(partes):
                t = t["hijos"].setdefault(componente, {"hijos": {}, "ids": set()})
                t["ids"].add(identificador)
            nombre = Path(nodo["ruta"]).name
            self.por_nombre_sin_md.setdefault(Path(nombre).stem.lower(), []).append(identificador)
            m = RE_HANDOFF_ARCHIVO.match(nombre)
            if m and m.group(1) and nombre.lower() == f"{PREFIJO_HANDOFF}_{m.group(1)}.md":
                self.handoff_por_numero[int(m.group(1))] = identificador
            if self.fuente_de[identificador].get("memoria"):
                grupo = nodo["grupo"]
                for s in {nodo["slug"].lower(), Path(nombre).stem.lower()}:
                    self.slugs_memoria.setdefault(grupo, {}).setdefault(s, identificador)
                    if len(s) >= 8 and "-" in s:
                        self.slugs_mencionables.setdefault(s, set()).add(identificador)
        self.ordenar_trie(self.trie)

    def ordenar_trie(self, t):
        t["orden"] = sorted(t["hijos"].items(), key=lambda par: -len(par[0]))
        for hijo in t["hijos"].values():
            self.ordenar_trie(hijo)

    def memorias_preferidas(self, origen):
        fuente = self.fuente_de[origen]
        memorias = [f for f in FUENTES if f.get("memoria")]
        if fuente.get("memoria"):
            return [fuente["id"]] + [f["id"] for f in memorias if f["id"] != fuente["id"]]
        ruta = normalizar(self.por_id[origen]["ruta"])
        propias = [f["id"] for f in memorias if ruta.startswith(f'{normalizar(f["proyecto"])}\\')]
        return propias + [f["id"] for f in memorias if f["id"] not in propias]

    def agregar(self, de, a, clase, texto):
        if de == a or de not in self.por_id or a not in self.por_id:
            return
        if clase not in ("sugerida", "duplicado"):
            texto = recortar(texto, 160)
        if clase in FUERZA:
            actual = self.fuertes.get((de, a))
            if actual is None or FUERZA[clase] < FUERZA[actual[0]]:
                self.fuertes[(de, a)] = (clase, texto)
                self.salientes.setdefault(de, set()).add(a)
                self.entrantes.setdefault(a, set()).add(de)
        elif clase == "duplicado" and (a, de, clase) in self.otras:
            self.duplicados_juntados += 1
            previo = self.otras[(a, de, clase)]
            if texto and texto != previo:
                self.otras[(a, de, clase)] = f"{previo} · {texto}" if previo else texto
        else:
            self.otras.setdefault((de, a, clase), texto)

    def de_registro(self, de):
        nodo = self.por_id.get(de)
        return nodo is not None and nodo["grupo"] in GRUPOS_REGISTRO

    def roto(self, de, destino, clase):
        llave = (de, destino.lower(), clase)
        if self.de_registro(de):
            return
        if llave not in self.rotos_vistos:
            self.rotos_vistos.add(llave)
            self.rotos.append({"de": de, "destino": destino, "clase": clase})

    def ambiguo(self, de, mencion, candidatos):
        llave = (de, mencion.lower())
        if self.de_registro(de):
            return
        if llave not in self.ambiguos_vistos:
            self.ambiguos_vistos.add(llave)
            self.ambiguos.append({"de": de, "mencion": mencion, "candidatos": sorted(candidatos)})

    def mismo_lugar(self, origen, candidatos):
        return [c for c in candidatos if self.carpeta_de[c] == self.carpeta_de[origen]]

    def analizar_indices(self):
        for nodo in self.nodos:
            if nodo["tipo"] != "indice":
                continue
            origen = nodo["id"]
            texto = nodo["_cuerpo"]
            carpeta = Path(nodo["ruta"]).parent
            listados = set()
            spans = []
            for m in RE_INDICE.finditer(texto):
                titulo, destino, gancho = m.group(1), m.group(2), m.group(3)
                spans.append((m.start(), m.end()))
                limpio = urllib.parse.unquote(destino.split("#")[0].split("?")[0])
                if not limpio.lower().endswith(".md") or es_de_red(limpio):
                    continue
                objetivo = os.path.normpath(os.path.join(str(carpeta), limpio))
                identificador = self.por_ruta.get(normalizar(objetivo))
                if identificador:
                    listados.add(identificador)
                    self.titulo_indice.setdefault(identificador, limpiar_md(titulo))
                    self.ganchos.setdefault(identificador, (origen, limpiar_md(gancho), m.start()))
                    self.agregar(origen, identificador, "indice", limpiar_md(gancho) or limpiar_md(titulo))
                elif not os.path.exists(objetivo):
                    self.indice_roto.append({"indice": origen, "destino": destino})
                    self.roto(origen, destino, "indice")
            self.listados_por_indice[origen] = listados
            self.spans_indice[origen] = spans
        for fuente in FUENTES:
            if not fuente.get("memoria"):
                continue
            del_grupo = [n for n in self.nodos if n["grupo"] == fuente["id"]]
            indices = [n["id"] for n in del_grupo if n["tipo"] == "indice"]
            listados = set()
            for i in indices:
                listados |= self.listados_por_indice.get(i, set())
            self.indexadas |= listados
            for n in del_grupo:
                if n["tipo"] != "indice" and n["id"] not in listados:
                    self.sin_indice.append(n["id"])

    def resolver_sin_indice(self):
        quedan = []
        for identificador in self.sin_indice:
            vias = sorted(de for de in self.entrantes.get(identificador, ())
                          if de in self.indexadas and self.fuertes[(de, identificador)][0] in ("wiki", "enlace"))
            if vias:
                self.por_enlace[identificador] = vias[0]
            else:
                quedan.append(identificador)
        self.sin_indice = quedan

    def completar_titulos(self):
        for nodo in self.nodos:
            titulo = self.titulo_indice.get(nodo["id"]) or primer_encabezado(nodo["_cuerpo"])
            nodo["titulo"] = titulo or Path(nodo["ruta"]).stem
            if not nodo["descripcion"]:
                if nodo["tipo"] == "indice":
                    cantidad = len(self.listados_por_indice.get(nodo["id"], ()))
                    nodo["descripcion"] = f"Índice de la memoria: {cantidad} entradas"
                else:
                    parrafo, meta = parrafo_y_meta(nodo["_cuerpo"])
                    nodo["descripcion"] = recortar(parrafo or meta, 220)
                    if meta:
                        nodo["meta"] = recortar(meta, 300)

    def resolver_wiki(self, origen, destino):
        d = destino.strip()
        if d.lower().endswith(".md"):
            d = d[:-3]
        dl = d.lower()
        for grupo in self.memorias_preferidas(origen):
            encontrado = self.slugs_memoria.get(grupo, {}).get(dl)
            if encontrado:
                return encontrado, None
        candidatos = self.por_nombre_sin_md.get(dl, [])
        if len(candidatos) == 1:
            return candidatos[0], None
        if len(candidatos) > 1:
            mismos = self.mismo_lugar(origen, candidatos)
            if len(mismos) == 1:
                return mismos[0], None
            return None, candidatos
        return None, None

    def analizar_wiki(self, origen, texto):
        for m in RE_WIKI.finditer(texto):
            destino = m.group(1).strip()
            encontrado, candidatos = self.resolver_wiki(origen, destino)
            if encontrado:
                self.agregar(origen, encontrado, "wiki", fragmento(texto, m.start(), m.end()))
            elif candidatos:
                self.ambiguo(origen, m.group(0), candidatos)
            else:
                self.roto(origen, destino, "wiki")

    def analizar_enlaces(self, origen, texto, spans):
        carpeta = Path(self.por_id[origen]["ruta"]).parent
        inicios = [a for a, _ in spans]
        for m in RE_ENLACE.finditer(texto):
            k = bisect.bisect_right(inicios, m.start()) - 1
            if k >= 0 and m.start() < spans[k][1]:
                continue
            destino = m.group(2).strip()
            if destino.startswith("<") and destino.endswith(">"):
                destino = destino[1:-1].strip()
            limpio = destino.split("#")[0].split("?")[0]
            if limpio.lower().startswith("file:"):
                limpio = re.sub(r"^file:/*", "", limpio, flags=re.I)
            elif RE_ESQUEMA.match(limpio):
                continue
            limpio = urllib.parse.unquote(limpio)
            if not limpio.lower().endswith(".md"):
                continue
            if re.match(r"^[A-Za-z]:[\\/]", limpio):
                objetivo = os.path.normpath(limpio)
            else:
                objetivo = os.path.normpath(os.path.join(str(carpeta), limpio.lstrip("\\/") if limpio[:1] in "\\/" else limpio))
            identificador = self.por_ruta.get(normalizar(objetivo))
            if identificador:
                self.agregar(origen, identificador, "enlace", fragmento(texto, m.start(), m.end()))
            else:
                self.roto(origen, destino, "enlace")

    def recorrer_ruta(self, texto, inicio_nombre, nombre):
        t = self.trie["hijos"].get(nombre)
        if t is None:
            return None
        inicio = inicio_nombre
        profundidad = 1
        while True:
            k = inicio
            while k > 0 and texto[k - 1] in SEPARADORES:
                k -= 1
            if k == inicio:
                break
            siguiente = None
            for componente, hijo in t["orden"]:
                largo = len(componente)
                if largo > k or texto[k - largo:k].lower() != componente:
                    continue
                if k - largo > 0 and es_nombre(texto[k - largo - 1]):
                    continue
                siguiente = (hijo, k - largo)
                break
            if siguiente:
                t, inicio = siguiente
                profundidad += 1
                continue
            j = k
            while j > 0 and texto[j - 1] not in DELIMITADORES and texto[j - 1] not in SEPARADORES:
                j -= 1
            previo = texto[j:k]
            if previo and previo not in (".", "..", "~") and previo[0] not in "%$":
                return None
            break
        return inicio, t["ids"], profundidad > 1

    def secciones_con_posicion(self, origen):
        if origen not in self.secciones_de:
            cuerpo = self.por_id[origen]["_cuerpo"]
            inicios = [0]
            i = cuerpo.find("\n")
            while i >= 0:
                inicios.append(i + 1)
                i = cuerpo.find("\n", i + 1)
            secciones = seccionar(cuerpo)
            self.secciones_de[origen] = ([inicios[s["linea"]] for s in secciones], secciones)
        return self.secciones_de[origen]

    def proyecto_por_contexto(self, origen, texto, posicion, permitidos=None, con_nota=True):
        nodo = self.por_id[origen]
        clave_permitidos = tuple(sorted(permitidos)) if permitidos is not None else None
        if texto is nodo["_cuerpo"]:
            comienzos, secciones = self.secciones_con_posicion(origen)
            i = bisect.bisect_right(comienzos, posicion) - 1
            if i >= 0:
                llave = (origen, i, clave_permitidos)
                if llave not in self.proyecto_de_seccion:
                    proyecto = proyecto_unico(secciones[i]["texto"], permitidos)
                    if proyecto is None:
                        titulos = []
                        nivel = secciones[i]["nivel"]
                        for s in reversed(secciones[:i]):
                            if 1 < s["nivel"] < nivel:
                                titulos.append(s["titulo"])
                                nivel = s["nivel"]
                        proyecto = proyecto_unico("\n".join(titulos), permitidos) if titulos else None
                    self.proyecto_de_seccion[llave] = proyecto
                if self.proyecto_de_seccion[llave]:
                    return self.proyecto_de_seccion[llave]
        if not con_nota:
            return None
        return proyecto_unico(f'{nodo["titulo"]}\n{nodo["descripcion"] or ""}', permitidos)

    def desempatar(self, origen, linea, candidatos, resueltos, texto=None, posicion=0):
        marcados = [c for c in candidatos
                    if MARCA_DE_PROYECTO.get(self.proyecto_de[c]) and MARCA_DE_PROYECTO[self.proyecto_de[c]].search(linea)]
        if len(marcados) == 1:
            return marcados[0]
        renglon = linea.lower().replace("/", "\\")
        nombradas = [c for c in candidatos if carpeta_nombrada(self.carpeta_de[c], renglon)]
        if len(nombradas) == 1:
            return nombradas[0]
        ya = [c for c in candidatos if c in resueltos]
        if len(ya) == 1:
            return ya[0]
        carpeta = self.carpeta_de[origen]
        ancestros = [c for c in candidatos if carpeta.startswith(f"{self.carpeta_de[c]}\\")]
        if ancestros:
            hondo = max(len(self.carpeta_de[c]) for c in ancestros)
            mas_cerca = [c for c in ancestros if len(self.carpeta_de[c]) == hondo]
            if len(mas_cerca) == 1:
                return mas_cerca[0]
        if self.fuente_de[origen].get("memoria"):
            permitidos = {self.proyecto_de[c] for c in candidatos if self.proyecto_de[c]}
            proyecto = self.proyecto_por_contexto(origen, texto, posicion, permitidos) if texto is not None else None
        else:
            proyecto = self.proyecto_de[origen]
        propios = [c for c in candidatos if proyecto and self.proyecto_de[c] == proyecto]
        if len(propios) == 1:
            return propios[0]
        return None

    def analizar_menciones(self, origen, textos):
        pendientes = []
        for texto in textos:
            for m in RE_MD.finditer(texto):
                i = m.start()
                while i > 0 and es_nombre(texto[i - 1]):
                    i -= 1
                while i < m.start() and texto[i] == ".":
                    i += 1
                if i >= m.start():
                    continue
                nombre = texto[i:m.end()].lower()
                resultado = self.recorrer_ruta(texto, i, nombre)
                if resultado is None:
                    continue
                inicio, ids, _ = resultado
                candidatos = sorted(ids)
                mismos = candidatos if len(candidatos) == 1 else self.mismo_lugar(origen, candidatos)
                if len(mismos) == 1:
                    self.agregar(origen, mismos[0], "mencion", fragmento(texto, inicio, m.end()))
                else:
                    pendientes.append((texto, inicio, m.end(), candidatos))
            for m in RE_HANDOFF.finditer(texto):
                destino = self.handoff_por_numero.get(int(m.group(1)))
                if destino:
                    self.agregar(origen, destino, "mencion", fragmento(texto, m.start(), m.end()))
            for m in RE_TOKEN.finditer(texto):
                token = m.group(0).lower()
                ids = self.slugs_mencionables.get(token)
                if not ids:
                    continue
                if texto[m.end():m.end() + 3].lower() == ".md" or texto[max(0, m.start() - 2):m.start()] == "[[":
                    continue
                destino = None
                for grupo in self.memorias_preferidas(origen):
                    propios = [c for c in ids if self.por_id[c]["grupo"] == grupo]
                    if propios:
                        destino = propios[0]
                        break
                if destino:
                    self.agregar(origen, destino, "mencion", fragmento(texto, m.start(), m.end()))
        resueltos = set(self.salientes.get(origen, ()))
        for texto, inicio, fin, candidatos in pendientes:
            a = texto.rfind("\n", 0, inicio) + 1
            b = texto.find("\n", fin)
            linea = texto[a:] if b < 0 else texto[a:b]
            destino = self.desempatar(origen, linea, candidatos, resueltos, texto, inicio)
            if destino:
                self.agregar(origen, destino, "mencion", fragmento(texto, inicio, fin))
            elif not any((origen, c) in self.fuertes for c in candidatos) \
                    and not RE_GENERICO.search(texto[max(0, inicio - 24):inicio]):
                self.ambiguo(origen, texto[inicio:fin], candidatos)

    def resolver_documento(self, origen, nombre):
        candidatos = self.por_nombre_sin_md.get(Path(nombre).stem.lower(), [])
        if len(candidatos) > 1:
            candidatos = self.mismo_lugar(origen, candidatos)
        return candidatos[0] if len(candidatos) == 1 else None

    def analizar_respuestas(self):
        numero_de = {i: n for n, i in self.handoff_por_numero.items()}
        respondidos = set()
        cerrados = set()
        for origen, cabecera in self.cabeceras.items():
            destinos = []
            for numeros, texto in cabecera["respuestas"]:
                for numero in numeros:
                    destino = self.handoff_por_numero.get(numero)
                    if destino is None:
                        self.respuestas_rechazadas.append((origen, numero))
                        continue
                    if destino != origen and destino not in destinos:
                        destinos.append(destino)
                        self.agregar(origen, destino, "responde", texto)
            for nombre, texto in cabecera["documentos"]:
                destino = self.resolver_documento(origen, nombre)
                if destino and destino != origen and destino not in destinos:
                    destinos.append(destino)
                    self.agregar(origen, destino, "responde", texto)
            if destinos:
                self.por_id[origen]["responde"] = destinos
                respondidos.update(destinos)
            if destinos or cabecera["ninguno"]:
                self.declaran.add(origen)
            cerrados.update(self.handoff_por_numero[n] for n in cabecera["cerrados"] if n in self.handoff_por_numero)
        if not numero_de:
            return
        ultimo = max(numero_de.values())
        for identificador, numero in sorted(numero_de.items(), key=lambda par: par[1]):
            cabecera = self.cabeceras.get(identificador)
            if numero <= ultimo - TRAMO_ABIERTOS or cabecera is None:
                continue
            if identificador in respondidos or identificador in cerrados or cabecera["cierra"]:
                continue
            respuesta = self.por_id[identificador].get("responde") and not cabecera["pide"]
            (self.respuestas_sin_acuse if respuesta else self.handoffs_abiertos).append({
                "id": identificador,
                "numero": numero,
                "fecha": cabecera["fecha"],
                "lado": cabecera["lado"],
                "titulo": self.por_id[identificador]["titulo"],
            })

    def analizar_cadena(self):
        handoffs = [n for n in self.nodos if n["tipo"] == "handoff"]
        numerados = sorted(self.handoff_por_numero.items())
        base = [n["id"] for n in handoffs if Path(n["ruta"]).name.lower() == f"{PREFIJO_HANDOFF}.md"]
        sueltos = sorted((n["id"] for n in handoffs if n["id"] not in base
                          and n["id"] not in self.handoff_por_numero.values()), key=orden_natural)
        secuencia = [(None, i) for i in base + sueltos] + [(numero, i) for numero, i in numerados]
        for (n1, a), (n2, b) in zip(secuencia, secuencia[1:]):
            if b in self.declaran or any(self.fuertes.get(par, ("",))[0] == "responde" for par in ((a, b), (b, a))):
                continue
            nombre_b = Path(self.por_id[b]["ruta"]).stem
            texto = f"sigue en {nombre_b}"
            if n2 is not None:
                faltan = list(range((n1 if n1 is not None else 1) + 1, n2))
                if faltan:
                    texto += f' (no existe{"n" if len(faltan) > 1 else ""} el {", ".join(str(f) for f in faltan)})'
            self.agregar(a, b, "cadena", texto)

    def cargar_sugerencias(self, ruta):
        if not ruta.is_file():
            return 0
        try:
            crudo = ruta.read_text(encoding="utf-8-sig")
        except (OSError, ValueError) as error:
            avisar(f"no pude leer {ruta}: {error}")
            return 0
        try:
            lista = json.loads(crudo)
        except ValueError as error:
            reparado = re.sub(r'\\\\|\\(?!["/u])', lambda m: m.group(0) if m.group(0) == "\\\\" else "\\\\", crudo)
            try:
                lista = json.loads(reparado)
                avisar(f"{ruta.name} tiene barras invertidas sin duplicar; lo leí igual")
            except ValueError:
                avisar(f"no pude leer {ruta}: {error}")
                return 0
        if not isinstance(lista, list):
            avisar(f"{ruta} no es una lista")
            return 0
        cargadas = 0
        for item in lista:
            if not isinstance(item, dict):
                continue
            de = self.resolver_ruta_o_id(item.get("de", ""))
            a = self.resolver_ruta_o_id(item.get("a", ""))
            clase = item.get("clase", "sugerida")
            if clase not in ("sugerida", "duplicado"):
                clase = "sugerida"
            if not de or not a or de == a:
                self.sugerencias_sin_resolver.append(f'{item.get("de", "")} -> {item.get("a", "")}')
                continue
            self.agregar(de, a, clase, str(item.get("motivo", "")))
            cargadas += 1
        self.fundir_sugeridas()
        return cargadas

    def fundir_sugeridas(self):
        for de, a, clase in list(self.otras):
            if clase != "sugerida":
                continue
            for llave in ((de, a, "duplicado"), (a, de, "duplicado")):
                if llave not in self.otras:
                    continue
                sugerida = self.otras.pop((de, a, "sugerida"))
                previo = self.otras[llave]
                if sugerida and sugerida not in previo:
                    self.otras[llave] = f"{previo} · {sugerida}" if previo else sugerida
                self.sugeridas_fundidas += 1
                break

    def resolver_ruta_o_id(self, valor):
        if not isinstance(valor, str) or not valor.strip():
            return None
        if valor in self.por_id:
            return valor
        return self.por_ruta.get(normalizar(valor.strip()))

    def parecidas(self):
        try:
            import parecidas
            return parecidas.marcar(self)
        except Exception as error:
            avisar(f"no pude buscar las notas parecidas ({detalle(error)})")
            return 0

    def preparar_entidades(self):
        try:
            import entidades
            return entidades.preparar(self)
        except Exception as error:
            avisar(f"no pude armar el índice de entidades ({detalle(error)})")
            return None

    def terminar_entidades(self, estado):
        try:
            return estado.terminar()
        except Exception as error:
            avisar(f"no pude terminar el índice de entidades ({detalle(error)})")
            self.entidades = {}
            self.resumen_entidades = None
            return 0

    def analizar(self, ruta_sugerencias, con_parecidas=True, con_entidades=True):
        self.indexar()
        self.analizar_indices()
        self.completar_titulos()
        for nodo in self.nodos:
            origen = nodo["id"]
            textos = self.textos_de[origen]
            for i, texto in enumerate(textos):
                self.analizar_wiki(origen, texto)
                self.analizar_enlaces(origen, texto, self.spans_indice.get(origen, []) if i == 0 else [])
            self.analizar_menciones(origen, textos)
        self.analizar_respuestas()
        self.analizar_cadena()
        self.resolver_sin_indice()
        cargadas = self.cargar_sugerencias(ruta_sugerencias)
        estado = self.preparar_entidades() if con_entidades else None
        if con_parecidas:
            self.parecidas()
        if estado is not None:
            self.terminar_entidades(estado)
        return cargadas

    def armar(self):
        aristas = [{"de": de, "a": a, "clase": clase, "texto": texto} for (de, a), (clase, texto) in self.fuertes.items()]
        aristas += [{"de": de, "a": a, "clase": clase, "texto": texto} for (de, a, clase), texto in self.otras.items()]
        aprendido, de_aprendido = self.lo_aprendido()
        aristas += de_aprendido
        for arista in aristas:
            if arista["clase"] == "parecida":
                arista.update(self.pares_parecidos.get((arista["de"], arista["a"]), {}))
            elif arista["clase"] == "comparte":
                arista.update(self.pares_comparten.get((arista["de"], arista["a"]), {}))
        aristas.sort(key=lambda x: (ORDEN_CLASES.index(x["clase"]), x["de"], x["a"]))
        conectados = set()
        for de, a in self.fuertes:
            conectados.add(de)
            conectados.add(a)
        con_cadena = set(self.handoff_por_numero.values())
        for de, a, clase in self.otras:
            if clase == "cadena":
                con_cadena.add(de)
                con_cadena.add(a)
        huerfanos = [n["id"] for n in self.nodos if n["id"] not in conectados and n["tipo"] not in ("indice", "instrucciones")
                     and not (n["tipo"] == "handoff" and n["id"] in con_cadena)]
        cantidades = {}
        for n in self.nodos:
            cantidades[n["grupo"]] = cantidades.get(n["grupo"], 0) + 1
        grupos = [dict({"id": f["id"], "nombre": f["nombre"], "color": f["color"], "cantidad": cantidades.get(f["id"], 0)},
                       **{k: f[k] for k in ("lobulo", "ancla") if k in f}) for f in FUENTES]
        orden_grupo = {f["id"]: i for i, f in enumerate(FUENTES)}
        nodos = sorted(self.nodos, key=lambda n: (orden_grupo[n["grupo"]], orden_natural(n["id"])))
        nodos = [{k: v for k, v in n.items() if not k.startswith("_")} for n in nodos]
        return {
            "generado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "usuario": CONFIG["usuario"],
            "carpeta": str(CARPETA),
            "proyectos": [{"raiz": p["raiz"], "alias": p["alias"]} for p in CONFIG["proyectos"]],
            "aliasRutas": [list(par) for par in CONFIG["alias_rutas"]],
            "lobulos": CONFIG["lobulos"],
            "opcionesConsulta": list(registro.OPCIONES_CONSULTA),
            "minutosChoque": registro.VENTANA_CHOQUE // 60,
            "handoffs": {"nombre": HANDOFFS["nombre"], "prefijo": HANDOFFS["prefijo"],
                         "lados": [{"id": x["id"], "nombre": x["nombre"]} for x in HANDOFFS["lados"]]} if HANDOFFS else None,
            "grupos": grupos,
            "nodos": nodos,
            "aristas": aristas,
            "salud": {
                "rotos": self.rotos,
                "huerfanos": huerfanos,
                "sinIndice": self.sin_indice,
                "indiceRoto": self.indice_roto,
                "ambiguos": self.ambiguos,
                "handoffsAbiertos": self.handoffs_abiertos,
                "respuestasSinAcuse": self.respuestas_sin_acuse,
                "medico": self.medico,
                "anclas": self.anclas,
                "hechos": self.hechos,
                "repiteClaude": self.repite_claude,
                "memoriasParecidas": self.memorias_parecidas,
            },
            "podadas": [{"ruta": ruta, "salteadas": cantidad} for ruta, cantidad in sorted(podadas.values())],
            "entidades": self.entidades,
            "aprendido": aprendido,
            "aprender": bool(CONFIG.get("aprender", True)),
        }

    def lo_aprendido(self):
        try:
            import aprender
            return aprender.para_la_pagina(self.nodos)
        except Exception as error:
            avisar(f"no pude leer lo aprendido ({detalle(error)})")
            return None, []


def librerias_locales(html, carpeta=None):
    carpeta = Path(carpeta) if carpeta else VENDOR
    huellas = dict(RE_INTEGRIDAD.findall(html))
    bloques = []
    for nombre, url in RE_LIBRERIA.findall(html):
        archivo = carpeta / url.rsplit("/", 1)[-1]
        if nombre not in huellas or not archivo.is_file():
            continue
        datos = archivo.read_bytes()
        if f'sha384-{base64.b64encode(hashlib.sha384(datos).digest()).decode("ascii")}' != huellas[nombre]:
            avisar(f"{archivo} no coincide con la huella que espera la página: la sigo bajando de internet")
            continue
        bloques.append("<script>" + datos.decode("utf-8", "replace").replace("</script", "<\\/script") + "</script>")
    return "\n".join(bloques)


def clases_de_la_pagina(html):
    m = RE_CLASES_PAGINA.search(html)
    return set(re.findall(r"['\"](\w+)['\"]", m.group(1))) if m else None


def aristas_compatibles(aristas, conocidas):
    if conocidas is None:
        return []
    ya = {(x["clase"], x["de"], x["a"]) for x in aristas}
    salida = []
    for x in aristas:
        equivale = EQUIVALENTE_EN_PAGINA.get(x["clase"])
        if not equivale or x["clase"] in conocidas or equivale not in conocidas:
            continue
        if (equivale, x["de"], x["a"]) in ya or (equivale, x["a"], x["de"]) in ya:
            continue
        ya.add((equivale, x["de"], x["a"]))
        salida.append({"de": x["de"], "a": x["a"], "clase": equivale, "texto": x["texto"], "equivale": x["clase"]})
    return salida


def a_javascript(datos):
    js = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    js = re.sub(r"<(?=!--|script)", lambda m: "\\u003c", js, flags=re.I)
    return js.replace("</", "<\\/")


def desde_disco(con_parecidas=False, con_entidades=True):
    _listados.clear()
    cerebro = Cerebro()
    cerebro.recolectar()
    cerebro.analizar(DATOS / "sugerencias.json", con_parecidas=con_parecidas, con_entidades=con_entidades)
    return cerebro


def diagnosticar(cerebro):
    try:
        import medico
        saltos = medico.alcance(cerebro)
        cerebro.medico = medico.revisar(cerebro, saltos)
    except Exception as error:
        avisar(f"el médico falló y la salud quedó sin revisar ({detalle(error)})")
        cerebro.medico = []
        return None
    for nodo in cerebro.nodos:
        if nodo["id"] in saltos:
            nodo["saltos"] = saltos[nodo["id"]]
    return medico


TEXTOS_ARGPARSE = {
    "usage: ": "uso: ", "options": "opciones", "positional arguments": "argumentos",
    "show this help message and exit": "muestra esta ayuda y sale", " (default: %(default)s)": " (por defecto: %(default)s)",
    "%(prog)s: warning: %(message)s\n": "%(prog)s: aviso: %(message)s\n",
    "argument %(argument_name)s: %(message)s": "opción %(argument_name)s: %(message)s",
    "ambiguous option: %(option)s could match %(matches)s": "opción ambigua: %(option)s puede ser %(matches)s",
    "expected one argument": "le falta el valor", "expected at least one argument": "le falta al menos un valor",
    "expected at most one argument": "acepta como mucho un valor", "ignored explicit argument %r": "se ignoró el valor %r",
    "invalid %(type)s value: %(value)r": "valor inválido (%(type)s): %(value)r",
    "invalid choice: %(value)r (choose from %(choices)s)": "valor inválido: %(value)r (elegí entre %(choices)s)",
    "not allowed with argument %s": "no va junto con %s", "one of the arguments %s is required": "falta una de estas: %s",
    "the following arguments are required: %s": "faltan estas opciones: %s",
    "unrecognized arguments: %s": "no conozco estas opciones: %s",
    "show program's version number and exit": "muestra la versión y sale",
}


def version():
    try:
        return json.loads((CARPETA / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError, TypeError):
        return "sin versión"


def donde_busque(mostrar=4):
    raices = list(dict.fromkeys(str(r) for f in FUENTES for r, _, _ in f["raices"]))
    lugares = "; ".join(raices[:mostrar]) + (f" y {len(raices) - mostrar} más" if len(raices) > mostrar else "")
    memoria = configuracion.carpeta_de_claude() / "projects"
    return (f"No encontré ninguna nota. Busqué en: {lugares or 'ninguna carpeta'}. La memoria de Claude Code aparece en "
            f"{memoria}{os.sep}<proyecto>{os.sep}memory cuando guarda la primera; si tus notas están en otro lado, "
            "sumalas a «fuentes» en config.json.")


def plural_en_castellano(uno, varios, n):
    if uno == "expected %s argument":
        return "le falta %s valor" if n == 1 else "le faltan %s valores"
    return uno if n == 1 else varios


def argparse_en_castellano():
    argparse._ = lambda texto: TEXTOS_ARGPARSE.get(texto, texto)
    argparse.ngettext = plural_en_castellano


def armar_parser(epilogo):
    argparse_en_castellano()
    parser = argparse.ArgumentParser(description="Arma el mapa de las notas .md (cerebro.html).", epilog=epilogo,
                                     allow_abbrev=False)
    parser.add_argument("--version", action="version", version=f"Neuromapa {version()}")
    parser.add_argument("--json", dest="ruta_json", help="vuelca además el JSON puro en esta ruta")
    parser.add_argument("--plantilla", default=str(CARPETA / "plantilla.html"), help="la plantilla de la página")
    parser.add_argument("--salida", default=str(DATOS / "cerebro.html"),
                        help="dónde escribe la página (sin esta opción, cerebro.html en la carpeta de datos)")
    parser.add_argument("--sugerencias", default=str(DATOS / "sugerencias.json"),
                        help="el archivo de conexiones sugeridas a mano (sugerencias.json)")
    parser.add_argument("--demo", action="store_true",
                        help="usa las notas de ejemplo de la carpeta demo, con su propio config.json, sin tocar las tuyas")
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--salud", action="store_true",
                      help="solo revisa la memoria e imprime lo que encontró, sin escribir cerebro.html")
    modo.add_argument("--buscar", metavar="TEXTO",
                      help="busca en el texto completo de las notas y muestra las mejores, con sección y línea")
    modo.add_argument("--sobre", metavar="TEMA",
                      help="junta lo que dicen las notas de un tema, por tipo, y dice qué leer primero")
    parser.add_argument("--todo", action="store_true",
                        help="con --buscar o --sobre: suma los grupos que no están en el foco; "
                             "con --mapa: también las funciones internas; con --salud: muestra todos los hallazgos")
    parser.add_argument("--cuantos", type=int, default=8, help="con --buscar: cuántas notas mostrar")
    modo.add_argument("--parecidas", metavar="TEXTO_O_RUTA",
                      help="antes de crear una memoria: dice si ya hay una parecida (top 5 y palabras compartidas)")
    modo.add_argument("--entidad", metavar="NOMBRE",
                      help="qué notas nombran un archivo (riego.py), un commit (a1b2c3d) o una tabla (pedidos)")
    modo.add_argument("--mapa", nargs="+", metavar=("ARCHIVO", "PALABRA"),
                      help="funciones y bloques de un .html, .js, .css o .py con su línea de inicio y fin; "
                           "con una palabra, solo los que la nombran o la contienen")
    modo.add_argument("--choques", nargs="?", const=24, type=int, metavar="HORAS",
                      help=f"archivos que editaron dos chats o agentes con menos de {registro.VENTANA_CHOQUE // 60} "
                           "min entre uno y otro (últimas 24 h, o las horas que digas)")
    modo.add_argument("--gasto", nargs="?", const=1, type=int, metavar="HORAS",
                      help="tokens que usó cada chat (y sus agentes) en la última hora, o las horas que digas, "
                           "y los agentes que quedaron quietos sin terminar")
    modo.add_argument("--lecciones", nargs="?", const=7, type=int, metavar="DÍAS",
                      help="errores de las herramientas de archivos que se repiten (últimos 7 días), con la regla que "
                           "los evitaría y si están bajando")
    modo.add_argument("--aprendido", nargs="?", const="7", metavar="DÍAS_O_ARCHIVO",
                      help="lo que Neuromapa aprendió de tu uso (qué archivos se abren juntos y qué pistas sirvieron), "
                           "con lo de los últimos 7 días o los que digas; con un archivo (nombre o ruta), con qué se "
                           "usa ese")
    modo.add_argument("--olvidar", nargs="+", metavar=("ARCHIVO", "OTRO"),
                      help="borra lo aprendido de un archivo, o con dos, solo la unión entre ellos; lo de antes no "
                           "vuelve y lo que se use desde ahora se aprende de nuevo")
    modo.add_argument("--proponer-hechos", action="store_true",
                      help="busca datos de las notas que se pueden comprobar solos (líneas, archivos o carpetas de una "
                           "ruta) y los propone para hechos.json, sin tocarlo")
    modo.add_argument("--aprobar-hecho", metavar="NÚMEROS",
                      help="suma a hechos.json las propuestas con esos números (1,3), como salieron en --proponer-hechos")
    modo.add_argument("--dormir", action="store_true",
                      help="repasa las notas (líneas de código corridas, cifras viejas, cosas que quizás ya se "
                           "resolvieron) y propone arreglos, sin tocarlas; sola corre una vez por día, con el primer "
                           "pedido")
    modo.add_argument("--propuestas", action="store_true",
                      help="muestra los arreglos que propuso la última pasada de --dormir, numerados")
    modo.add_argument("--aplicar", metavar="NÚMEROS",
                      help="aplica a las notas los arreglos con esos números (1,3, o «todas»), como salieron en "
                           "--propuestas")
    modo.add_argument("--descartar", metavar="NÚMEROS",
                      help="descarta esas propuestas (1,3, o «todas») para que no se vuelvan a proponer")
    modo.add_argument("--descartar-aviso", metavar="RUTA:LÍNEA",
                      help="calla un «para revisar» del médico que ya se comprobó: deja de salir en --salud, la página "
                           "y la pista, hasta que ese renglón cambie")
    parser.add_argument("--motivo", default="", help="con --descartar-aviso: por qué no hace falta tocar la nota")
    modo.add_argument("--descartados", action="store_true",
                      help="lista los avisos del médico descartados a mano y si siguen callados")
    modo.add_argument("--recuperar-aviso", metavar="RUTA:LÍNEA",
                      help="deshace --descartar-aviso: ese aviso vuelve a salir")
    modo.add_argument("--charlas", metavar="PALABRAS",
                      help="busca en las charlas viejas de Claude Code (lo que escribiste vos y lo que respondió Claude, "
                           "nunca lo que devolvieron las herramientas), en el momento y sin guardar copia; las claves "
                           "salen tapadas; --cuantos dice cuántas charlas mostrar")
    modo.add_argument("--historial", nargs="?", const="", metavar="TEXTO",
                      help="los últimos cambios de la memoria, guardados con fecha al terminar cada respuesta; con un "
                           "texto, cuándo apareció o se borró y qué decía (nunca toca las notas)")
    modo.add_argument("--fichas", nargs="?", const=1.0, type=float, metavar="USD",
                      help="arma con Claude una ficha por nota (de qué trata, otras formas de nombrarlo, preguntas que "
                           "responde) para que el buscador la encuentre con otras palabras; solo las nuevas o cambiadas, "
                           "sin pasar ese gasto (1 por defecto); nunca toca las notas")
    return parser


def correr_herramienta(argumentos):
    if argumentos.mapa is not None:
        import mapa
        return mapa.main(argumentos.mapa, argumentos.todo)
    if argumentos.choques is not None:
        import choques
        return choques.main(argumentos.choques)
    if argumentos.gasto is not None:
        import gasto
        return gasto.main(argumentos.gasto)
    if argumentos.lecciones is not None:
        import lecciones
        return lecciones.main(argumentos.lecciones)
    if argumentos.aprendido is not None:
        import aprender
        valor = argumentos.aprendido.strip()
        return aprender.main(int(valor)) if re.fullmatch(r"-?[0-9]+", valor) else aprender.main_detalle(valor)
    if argumentos.olvidar is not None:
        import aprender
        return aprender.main_olvidar(argumentos.olvidar)
    if argumentos.proponer_hechos:
        import pruebas
        return pruebas.main_proponer()
    if argumentos.aprobar_hecho is not None:
        import pruebas
        return pruebas.main_aprobar(argumentos.aprobar_hecho)
    if argumentos.dormir:
        import dormir
        return dormir.main_dormir()
    if argumentos.propuestas:
        import dormir
        return dormir.main_propuestas()
    if argumentos.aplicar is not None:
        import dormir
        return dormir.main_aplicar(argumentos.aplicar)
    if argumentos.descartar is not None:
        import dormir
        return dormir.main_descartar(argumentos.descartar)
    if argumentos.descartar_aviso is not None:
        import medico
        return medico.main_descartar_aviso(argumentos.descartar_aviso, argumentos.motivo)
    if argumentos.descartados:
        import medico
        return medico.main_descartados()
    if argumentos.recuperar_aviso is not None:
        import medico
        return medico.main_recuperar_aviso(argumentos.recuperar_aviso)
    if argumentos.fichas is not None:
        import fichas
        return fichas.main(argumentos.fichas)
    if argumentos.historial is not None:
        import historial
        return historial.main(argumentos.historial)
    if argumentos.charlas is not None:
        import charlas
        return charlas.main(argumentos.charlas, max(1, argumentos.cuantos))
    if argumentos.entidad is not None:
        import entidades
        return entidades.main(argumentos.entidad)
    if argumentos.parecidas is not None:
        import parecidas
        return parecidas.main(argumentos.parecidas)
    if argumentos.buscar is not None or argumentos.sobre is not None:
        import buscador
        consulta = argumentos.sobre if argumentos.sobre is not None else argumentos.buscar
        return buscador.main(consulta, argumentos.sobre is not None, argumentos.todo, max(1, argumentos.cuantos))
    return None


def imprimir_salud(cerebro, medico, todo, segundos):
    otras = [f"AVISO   No pude leer {linea}: el médico no la revisó." for linea in cerebro.no_leidos]
    if delicadas:
        ejemplos = ", ".join(sorted(delicadas.values(), key=orden_natural)[:2])
        otras.append(f"Notas delicadas: {cantidad(len(delicadas), 'nota o carpeta quedó', 'notas o carpetas quedaron')} "
                     f"afuera por el nombre (claves, .env, .ssh…): no se indexan, no se muestran ni se citan ({ejemplos}).")
    for nombre, que, *funcion in (("consultas", "medir las consultas al cerebro"), ("choques", "buscar choques entre chats"),
                        ("gasto", "medir el gasto"), ("aprender", "leer lo aprendido"),
                        ("permisos", "revisar quién puede leer o escribir en las carpetas"),
                        ("hooks_comun", "leer las fallas de los hooks"),
                        ("dormir", "leer las propuestas de la última pasada"),
                        ("historial", "guardar el historial de la memoria"),
                        ("hooks_comun", "ver si Neuromapa está instalado dos veces", "linea_doble")):
        try:
            linea = getattr(importlib.import_module(nombre), funcion[0] if funcion else "linea_salud")()
        except Exception as error:
            avisar(f"no pude {que} ({detalle(error)})")
            continue
        if linea:
            otras.append(linea)
    avisos = sum(1 for linea in otras if linea.startswith("AVISO"))
    for linea in medico.informe(cerebro, cerebro.medico, 0 if todo else 30, segundos, avisos) + otras:
        print(linea)


def main(epilogo=None):
    try:
        if sys.stdout.isatty():
            sys.stdout.reconfigure(errors="replace")
        else:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    argumentos = armar_parser(epilogo).parse_args()
    codigo = correr_herramienta(argumentos)
    if codigo is not None:
        return codigo
    comienzo = time.perf_counter()
    cerebro = Cerebro()
    cerebro.recolectar()
    cantidad_sugerencias = cerebro.analizar(Path(argumentos.sugerencias))
    medico = diagnosticar(cerebro)
    if argumentos.salud:
        if medico is None:
            return 1
        imprimir_salud(cerebro, medico, argumentos.todo, time.perf_counter() - comienzo)
        return 0
    datos = cerebro.armar()
    for linea in cerebro.no_leidos:
        avisar(f"no pude leer {linea}")
    for linea in cerebro.sugerencias_sin_resolver:
        avisar(f"sugerencia que no resuelve a ningún nodo: {linea}")
    if argumentos.ruta_json:
        ruta_json = Path(argumentos.ruta_json)
        ruta_json.parent.mkdir(parents=True, exist_ok=True)
        escribir_atomico(ruta_json, json.dumps(datos, ensure_ascii=False, indent=1))
        print(f"JSON escrito en {ruta_json}")
    imprimir_resumen(cerebro, datos, cantidad_sugerencias)
    codigo = escribir_pagina(datos, Path(argumentos.plantilla), Path(argumentos.salida))
    if codigo == 0:
        print(f"Tardó {decimal(time.perf_counter() - comienzo)} s")
    return codigo


def imprimir_resumen(cerebro, datos, cantidad_sugerencias):
    print("")
    print(f'Nodos: {len(datos["nodos"])}')
    if not datos["nodos"]:
        print(donde_busque())
    for g in datos["grupos"]:
        print(f'  {g["id"].ljust(16)}{str(g["cantidad"]).rjust(5)}  {g["nombre"]}')
    print(f'Aristas: {len(datos["aristas"])}')
    for clase in ORDEN_CLASES:
        cuantas = sum(1 for a in datos["aristas"] if a["clase"] == clase)
        print(f"  {NOMBRE_CLASE[clase].ljust(16)}{str(cuantas).rjust(5)}")
    print(f"Sugerencias cargadas: {cantidad_sugerencias}")
    if cerebro.duplicados_juntados:
        print(f"  {cerebro.duplicados_juntados} duplicados venían en las dos direcciones y quedaron en una sola arista")
    if cerebro.sugeridas_fundidas == 1:
        print("  1 sugerida repetía un par ya marcado como duplicado y quedó sumada a él")
    elif cerebro.sugeridas_fundidas:
        print(f"  {cerebro.sugeridas_fundidas} sugeridas repetían un par ya marcado como duplicado y quedaron sumadas a él")
    print(f"Sugerencias sin resolver: {len(cerebro.sugerencias_sin_resolver)}")
    if cerebro.tiempo_parecidas is not None:
        por_plantilla = sum(1 for d in cerebro.pares_parecidos.values() if d.get("hermanas") == "plantilla")
        print(f"Parecidas: {cantidad(len(cerebro.pares_parecidos), 'par', 'pares')} sin arista ({por_plantilla} por "
              f"plantilla), {cantidad(cerebro.parecidas_recontadas, 'nota recontada', 'notas recontadas')}, "
              f"{decimal(cerebro.tiempo_parecidas, 2)} s")
    if cerebro.resumen_entidades:
        r = cerebro.resumen_entidades
        print(f'Entidades: {cantidad(r["archivos"], "archivo", "archivos")}, {cantidad(r["commits"], "commit", "commits")} '
              f'({r["verificados"]} en git, {cantidad(r["consultados"], "repo", "repos")}), '
              f'{cantidad(r["tablas"], "tabla", "tablas")}, {cantidad(r["menciones"], "mención", "menciones")}; '
              f'{cantidad(r["comparten"], "par comparte", "pares comparten")}, '
              f'{cantidad(r["carpetas"], "nota enlazada", "notas enlazadas")} a un LEEME')
    print("Salud:")
    for clave, valor in datos["salud"].items():
        print(f"  {NOMBRES_SALUD.get(clave, clave).ljust(36)}{str(len(valor)).rjust(5)}")
    if datos["podadas"]:
        bajan = sorted({v for p in CARPETAS_PESADAS for v in p["bajar_solo"].values()})
        print(f'Carpetas pesadas: solo se baja a {", ".join(bajan)} (un .md fuera de ahí no se ve)')
        for p in datos["podadas"]:
            print(f'  {p["ruta"]} ({p["salteadas"]} carpetas salteadas)')


def escribir_pagina(datos, plantilla, salida):
    if not plantilla.is_file():
        print(f"Error: no encuentro la plantilla {plantilla}")
        return 1
    html = plantilla.read_text(encoding="utf-8-sig")
    if MARCADOR not in html:
        print(f"Error: la plantilla no tiene el marcador {MARCADOR}")
        return 1
    compatibles = aristas_compatibles(datos["aristas"], clases_de_la_pagina(html))
    if compatibles:
        cuentas = {}
        for x in compatibles:
            clave = f'{x["equivale"]} como {x["clase"]}'
            cuentas[clave] = cuentas.get(clave, 0) + 1
        detalle = ", ".join(f"{v} {k}" for k, v in sorted(cuentas.items()))
        print(f"La plantilla todavía no dibuja {detalle}: van repetidas con la clase que sí conoce")
    datos_pagina = dict(datos, aristas=datos["aristas"] + compatibles) if compatibles else datos
    locales = librerias_locales(html)
    if locales:
        html = html.replace("</head>", f"{locales}\n</head>", 1)
    html = html.replace(MARCADOR, f"window.CEREBRO = {a_javascript(datos_pagina)};", 1)
    escribir_atomico(salida, html)
    if normalizar(salida.resolve()) == normalizar((DATOS / "cerebro.html").resolve()):
        try:
            import problemas
            raices = [p["raiz"] for p in CONFIG["proyectos"]] + [str(CARPETA)]
            memorias = {f["id"]: f.get("proyecto", "") for f in FUENTES if f.get("memoria")}
            problemas.guardar(problemas.listar(datos, memorias, raices), str(DATOS))
        except Exception as error:
            avisar(f"no pude guardar la lista de problemas para el aviso ({detalle(error)})")
    tamano = salida.stat().st_size
    print(f"HTML: {salida} ({decimal(tamano / 1048576, 2)} MB)")
    return 0


if __name__ == "__main__":
    sys.modules.setdefault("cerebro", sys.modules[__name__])
    sys.exit(main())
