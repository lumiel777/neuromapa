import bisect
import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import threading
import time
import urllib.parse
from pathlib import Path

import cerebro as nucleo
import configuracion
import permisos
from archivos import escribir_atomico, leer_objeto_json
from textos import cantidad, citar, decimal, miles

TONOS = ("peligro", "aviso", "revisar", "info")
LINEAS_READ = 2000
TOKENS_READ = 25000
BYTES_POR_TOKEN = 2.0
LINEAS_INDICE = 200
AVISO_INDICE = 150
BYTES_INDICE = 25000
AVISO_BYTES_INDICE = 18750
DESCRIPCION_MINIMA = 30
LARGO_CITA = 120
TIPOS_MEMORIA = {"user", "feedback", "project", "reference"}
PRIORIDAD_GRUPO = {f["id"]: f["prioridad"] for f in nucleo.FUENTES if "prioridad" in f}

RE_BACKTICK = re.compile(r"`([^`\n]{1,300})`")
RE_HASH = re.compile(r"^([0-9a-f]{7,40})(?:\.\.\.?([0-9a-f]{7,40}))?$")
RE_CONTEXTO_SESION = re.compile(r"sesi[oó]n|session|uuid|chat|conversaci", re.I)
RE_CONTEXTO_HUELLA = re.compile(r"\b(?:sha\d*(?:sum)?|md5|crc\d*|hash|huellas?|checksum|blake\d*|xxh\d*)\b|suma de control", re.I)
RE_HASH_CORTADO = re.compile(r"^([0-9a-f]{7,40})(?:…|\.\.\.)?$", re.I)
RE_UNIDAD = re.compile(r"(?<!\w)[A-Za-z]:[\\/]")
PROHIBIDOS_EN_RUTA = set("`*<>|\"?:()\n")
RE_YA_NO_ESTA = re.compile(r"\bborrad[oa]s?\b|\bse\s+borr[oó]\b|\bno\s+existen?\b|\belimin|\bya\s+no\s+est|\bse\s+sac[oó]\b"
                           r"|\brenombr|\bse\s+movi[oó]\b|\bmovid[oa]s?\b|\bfantasmas?\b", re.I)
RE_NEGADO = re.compile(r"\bno\s*$", re.I)
RE_CIFRA = re.compile(r"(?<![\w.,:/\-#+~(])(\d{1,5})((?:[ \t]+[a-z]+){1,3})")
RE_CIFRA_RELATIVA = re.compile(r"\b(?:otros|otras|mas\s+de|menos\s+de|unos|unas|casi)\s+$")
RE_NUMERO_SUELTO = re.compile(r"(?<![\w.,])\d{1,5}(?![\d])")
MESES = {"enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "septiembre", "octubre",
         "noviembre", "diciembre"}
PALABRAS_SIN_CIFRA = MESES | {"para", "como", "veces", "desde", "hasta", "entre", "sobre", "cada", "menos", "anos", "dias",
                              "horas", "minutos", "segundos", "semanas", "meses", "hace", "porque", "donde", "cuando",
                              "tiene", "tienen", "esta", "estan", "pero", "solo", "todos", "todas", "otro", "otra", "otros",
                              "otras", "este", "estos", "esos", "esas", "nuevo", "nueva", "nuevos", "nuevas", "mismo",
                              "misma", "mismos", "quedan", "eran", "fueron", "total", "ellos", "ellas", "tambien",
                              "despues", "antes", "segun", "contra"}
RE_SIN_PROBAR = re.compile(r"\bsin\s+probar\b|\bfalta(?:n)?\s+probar\w*"
                           r"|\bno\s+(?:esta(?:n)?\s+|fue(?:ron)?\s+|se\s+)?probad[oa]s?\b"
                           r"|\bno\s+se\s+prob(?:o|aron)\b|\bpendientes?\s+de\s+prob\w+|\bsin\s+prueba\b")
RE_PROBADO = re.compile(r"\bprobad[oa]s?\b|\bse\s+prob(?:o|aron)\b|\bprobe\b|\bprobamos\b|\bprobo\b")
RE_NEGACION_ANTES = re.compile(r"\b(?:sin|no|falta|faltan|pendientes?\s+de)\s+(?:\w+\s+){0,2}$")
RE_PRUEBA_RAPIDA = re.compile(r"prob|prueba", re.I)
RE_PROBLEMA = re.compile(
    r"\bno (?:aparece|aparecen|anda|andan|funciona|funcionan|se ve|se ven|sale|salen|llega|llegan|carga|cargan|abre|abren"
    r"|guarda|lee|puede|pueden|descifra|toma|responde|cobra|da|muestra|comprueba|comprueban|pide|piden|verifica"
    r"|verifican)\b|\bal reves\b|\bcruzad[oa]s\b|\bsin pedir\b|\bposible error\b|\bsin arreglar\b|\bfalta arreglar"
    r"|\bsigue (?:roto|rota|rotos|fallando|sin)\b|\btodavia no\b|\bse caen?\b|\bse traba\b|\bfallan?\b|\brot[oa]\b|\bbug\b"
    r"|\bdoes ?n[o']?t (?:work|show)\b|\bbroken\b|\bnot working\b")
RE_BIEN = re.compile(r"\b(?:no|nunca|sin|ni) (?:se (?:caen?|traba)|fallan?|rot[oa]|bug)\b")
RE_RESUELTO_CERCA = re.compile(r"arreglad|resuelt|\bhech[oa]\b|✅|~~|\bfixed\b|\bsolved\b|\bya (?:anda|aparece|sale|funciona)")
RE_RESUELTO = re.compile(f"{RE_RESUELTO_CERCA.pattern}|corregid")
RE_SIN_TOCAR = re.compile(r"\bsin tocar\b|\bqueda(?:n)? (?:igual|pendientes?|como est)|\bno se toca(?:n)?\b"
                          r"|\bno (?:lo|la|los|las) toque\b|\bleft (?:as is|untouched)\b|\bnot (?:touched|changed)\b")
RE_FRASE_COMMIT = re.compile(r"(?<=[.;!?])\s+|\n\s*\n")
DIAS_RESUELTO = 60
PALABRA_RARA = 4
RARAS_EN_COMUN = 2
PUNTAJE_RESUELTO = 20.0
PUNTAJE_CON_UNA_RARA = 30.0
VECINOS_RESUELTO = 1
LINEAS_DE_ITEM = 8
LINEAS_DE_ITEM_RESUELTO = 15
VENTANA_RESUELTO = 4
RE_ORACION = re.compile(r"(?:[^.;!?]|[.;!?](?!\s))+[.;!?]*")
RE_ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")

CODIGO = [p for p in nucleo.CONFIG["proyectos"] if p["codigo"]]
REMITE = {p["alias"]: p["remite_a"] for p in CODIGO if p.get("remite_a")}
QUIEN = nucleo.CONFIG["usuario"] or "el usuario"
PODA_CODIGO = {"bin", "obj", ".git", ".vs", "packages", "node_modules", "dist", "__pycache__", ".venv", "venv"}
VENTANA_ANCLA = 15
GRUPOS_ANCLAS_RESUMIDAS = {f["id"] for f in nucleo.FUENTES if f.get("anclas_resumidas")}
RE_PARECE_CODIGO = re.compile(r"[a-z][A-Z]|_|\.|\(|=")
MINIMO_PALABRA_SUELTA = 6
FINALES_DE_ORACION = (".", ":", ";", "!", "?")
EXT_ANCLA = ("cs", "py", "js", "jsx", "mjs", "cjs", "ts", "tsx", "java", "kt", "go", "rs", "php", "swift", "c", "h", "cc", "cpp",
             "hpp")
RE_ANCLA = re.compile(r"\.(" + "|".join(sorted(EXT_ANCLA, key=len, reverse=True))
                      + r"):(\d{1,6})(?:[ \t]*[-–][ \t]*(\d{1,6}))?((?:,\d{1,6})*)(?!\w|\.\d)", re.I)
EXTENSIONES_ANCLA = frozenset(f".{e}" for e in EXT_ANCLA)
RE_NOMBRE_CS = re.compile(r"^[A-Za-z_][\w.\-]*$")
CARACTERES_RUTA = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-\\/")
RE_ANCLA_SUELTA = re.compile(r"`:(\d{1,6})(?:[-–](\d{1,6}))?`")
PALABRAS_DE_CARPETA = 3
RE_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
TANDA_DIFF = 100
RE_ANTES_DE_CARPETA = re.compile(r"^.*[^\w.\-]")
RE_CORTE_DE_CLAUSULA = re.compile(r"\.(?=\s)|;")
MODIFICADORES_CS = (r"(?:public|private|protected|internal|static|override|virtual|async|unsafe|partial|sealed|abstract"
                    r"|extern|new|readonly)")
RE_DECLARACION = re.compile(r"^\s*(?:\[[^\]]*\]\s*)*(?:" + MODIFICADORES_CS + r"\s+)+(?:[\w<>\[\],.?]+\s+)*?(\w+)\s*"
                            r"(?:<[^>()]*>)?\s*\("
                            r"|^\s*(?:" + MODIFICADORES_CS + r"\s+)*(?:class|struct|enum|interface)\s+(\w+)")
RE_CASE = re.compile(r"^(\s*)case\b")
CONTROL = r"(?:if|for|foreach|while|switch|catch|return|else|do|try|using|lock|with|match|when|new|throw|await|typeof|sizeof)"
RE_DECLARACION_OTRAS = re.compile(
    r"^\s*(?:[@\w]+\s+)*?(?:function\*?|func|fn|fun)\s+(?:\([^)]*\)\s*)?(?:<[^>]*>\s*)?(?:\w+\.)?(\w+)"
    r"|^\s*(?:[@\w]+\s+)*?(?:class|struct|enum|interface|trait|impl|object)\s+(\w+)"
    r"|^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function\b|\([^)]*\)[^=]*=>|\w+\s*=>)"
    r"|^\s*(?:(?:public|private|protected|static|async|get|set|readonly|override|abstract|final|virtual|inline)\s+)*"
    r"(?:[\w<>\[\],.*&:]+\s+)*?(?!" + CONTROL + r"\b)(\w+)\s*\([^;]*\)\s*(?:const\s*)?(?::\s*[^{;]+)?\{?\s*$")
RE_DECLARACION_PY = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)|^\s*class\s+(\w+)")
RE_LITERALES_CS = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'|//.*')
TOPE_DECLARACION = 200
TOPE_BLOQUE = 400
LINEAS_DE_FIRMA = 8
EXT_ARCHIVO = {"cs", "ini", "txt", "md", "json", "jsonl", "yaml", "yml", "toml", "dll", "exe", "py", "sql", "ts", "tsx", "js",
               "jsx", "mjs", "css", "html", "bat", "cmd", "ps1", "sh", "dat", "bin", "xml", "csproj", "sln", "log", "png", "jpg",
               "jpeg", "gif", "svg", "webp", "zip", "pem", "key", "pdb", "config", "resx"}
RE_EXT_ARCHIVO = re.compile(r"\.(?:" + "|".join(sorted(EXT_ARCHIVO | {e.lstrip(".") for p in nucleo.CONFIG["proyectos"]
                                                                       for e in p["extensiones"]})) + r")$", re.I)
RE_IDENTIFICADOR = re.compile(r"^([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)(?:\([^()]*\))?;?$")
RE_PUNTUACION_CODIGO = re.compile(r"[()=\[\]<>!&|{}]")
PALABRAS_CSHARP = {"true", "false", "null", "void", "bool", "byte", "uint", "long", "ulong", "short", "ushort", "char",
                   "string", "int", "else", "case", "break", "return", "static", "public", "private", "protected",
                   "internal", "class", "struct", "object", "this", "base", "new", "var", "float", "double", "while",
                   "switch", "default", "const", "readonly", "using", "lock", "catch", "throw", "finally"}
PALABRAS_OTRAS = {"self", "none", "def", "elif", "lambda", "function", "undefined", "nullptr"}
SHA_VACIO = "0" * 40
COMMITS_CONOCIDOS = {}
COMMITS_AUSENTES = {}
REPOS_QUE_RESPONDIERON = set()
VIDA_AUSENTE = 600.0
CANDADO_COMMITS = threading.Lock()
CACHE_COMMITS = nucleo.DATOS / "en-vivo" / "commits.json"
CACHE_ANCLAS = nucleo.DATOS / "en-vivo" / "anclas-git.json"
MOVIDA_MINIMA = VENTANA_ANCLA
TOLERANCIA_MOVIDA = 3
VENTANA_TRABAJO = 24 * 3600
VERSION_CACHE_COMMITS = 1
CACHE_COMMITS_LEIDA = []

HECHOS = nucleo.DATOS / "hechos.json"
DESCARTADOS = nucleo.DATOS / "descartados.json"
TONOS_DESCARTABLES = ("revisar",)
RE_CADENA_CS = re.compile(r'"(?:[^"\\\n]|\\.)*"')
TIPOS_HECHO = ("lineas", "archivos", "carpetas", "no_utf8", "cadenas_en_bloque")


SIN_TILDES = str.maketrans("áéíóúüñàèìòùâêîôûÁÉÍÓÚÜÑ", "aeiouunaeiouaeiouaeiouun")


def sin_tildes(texto):
    return texto.translate(SIN_TILDES).lower()


def hallazgo(regla, nota, linea, tono, texto, arreglo):
    return {"regla": regla, "nota": nota, "linea": linea, "tono": tono, "texto": texto, "arreglo": arreglo}


def indice_principal(cerebro):
    return next((n["id"] for n in cerebro.nodos if n["tipo"] == "indice"), None)


def linea_en(nodo, posicion):
    return nodo.get("_desfase", 0) + nodo["_cuerpo"].count("\n", 0, posicion) + 1


def linea_de_clave(nodo, clave):
    cabeza = nodo.get("_cabeza", "")
    m = re.search(f"^[ \\t]*{re.escape(clave)}[ \\t]*:", cabeza, re.M)
    return cabeza.count("\n", 0, m.start()) + 1 if m else 1


def repos_conocidos():
    candidatos = [raiz for raiz, _ in nucleo.RAICES_PROYECTO] + nucleo.carpetas_propias()
    salida = []
    for raiz in candidatos:
        if os.path.exists(os.path.join(raiz, ".git")) and nucleo.normalizar(raiz) not in (nucleo.normalizar(r) for r in salida):
            salida.append(raiz)
    return salida


def es_huella(texto, inicio, desde):
    antes = texto[max(desde, inicio - 60, texto.rfind("\n", 0, inicio) + 1):inicio]
    return bool(RE_CONTEXTO_HUELLA.search(antes)) and not re.search(r"commit", antes, re.I)


def huellas_de(texto):
    salida = set()
    anterior = 0
    for m in RE_BACKTICK.finditer(texto):
        desde, anterior = anterior, m.end()
        h = RE_HASH_CORTADO.match(m.group(1).strip())
        if h and es_huella(texto, m.start(), desde):
            salida.add(h.group(1).lower())
    return salida


def extraer_commits(texto):
    salida = []
    anterior = 0
    for m in RE_BACKTICK.finditer(texto):
        desde, anterior = anterior, m.end()
        contenido = m.group(1).strip()
        h = RE_HASH.match(contenido)
        if not h:
            continue
        if RE_CONTEXTO_SESION.search(texto[max(0, m.start() - 40):m.start()]):
            continue
        if es_huella(texto, m.start(), desde):
            continue
        for valor in (h.group(1), h.group(2)):
            if valor and re.search(r"[a-f]", valor, re.I) and re.search(r"\d", valor):
                salida.append((valor.lower(), m.start(), m.end()))
    return salida


def verificar_commits(hashes, repos=None, espera=5.0):
    datos, consultados = consultar_commits(hashes, repos, espera)
    return {h: (d["repo"] if d else None) for h, d in datos.items()}, consultados


def leer_commit(crudo):
    cabeza, _, mensaje = crudo.partition(b"\n\n")
    fecha = None
    for linea in cabeza.split(b"\n"):
        if not linea.startswith(b"committer "):
            continue
        partes = linea.rsplit(b" ", 2)
        try:
            zona = partes[2].decode("ascii")
            desfase = datetime.timedelta(hours=int(zona[1:3]), minutes=int(zona[3:5]))
            zona_horaria = datetime.timezone(-desfase if zona[0] == "-" else desfase)
            fecha = datetime.datetime.fromtimestamp(int(partes[1]), zona_horaria).strftime("%Y-%m-%d")
        except (ValueError, IndexError, OverflowError, OSError):
            fecha = None
        break
    asunto = mensaje.decode("utf-8", "replace").strip().split("\n", 1)[0].strip() if mensaje else ""
    return fecha, asunto


def leer_lote(datos, pedidos, repo, hallados):
    pos = 0
    for h in pedidos:
        fin = datos.find(b"\n", pos)
        if fin < 0:
            return
        partes = datos[pos:fin].split()
        pos = fin + 1
        if len(partes) >= 3 and partes[1] == b"commit":
            try:
                tamano = int(partes[2])
            except ValueError:
                return
            if h not in hallados:
                fecha, asunto = leer_commit(datos[pos:pos + tamano])
                hallados[h] = {"repo": repo, "sha": partes[0].decode("ascii", "replace"), "fecha": fecha, "asunto": asunto}
            pos += tamano + 1
        elif len(partes) >= 2 and partes[-1] == b"ambiguous" and h not in hallados:
            hallados[h] = {"repo": repo, "sha": None, "fecha": None, "asunto": ""}


def leer_cache_commits(ruta=None):
    if CACHE_COMMITS_LEIDA:
        return
    CACHE_COMMITS_LEIDA.append(True)
    try:
        datos = json.loads(Path(ruta or CACHE_COMMITS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(datos, dict) or datos.get("version") != VERSION_CACHE_COMMITS:
        return
    carpetas = {}
    conocidos = datos.get("conocidos")
    for h, dato in (conocidos.items() if isinstance(conocidos, dict) else ()):
        if not isinstance(dato, dict) or not isinstance(dato.get("repo"), str):
            continue
        repo = dato["repo"]
        if repo not in carpetas:
            carpetas[repo] = os.path.isdir(os.path.join(repo, ".git"))
        if carpetas[repo]:
            COMMITS_CONOCIDOS.setdefault(h, {"repo": repo, "sha": dato.get("sha"), "fecha": dato.get("fecha"),
                                             "asunto": dato.get("asunto") or ""})
    ausentes = datos.get("ausentes")
    for h, valor in (ausentes.items() if isinstance(ausentes, dict) else ()):
        if isinstance(valor, list) and len(valor) == 2 and isinstance(valor[0], list) and isinstance(valor[1], (int, float)):
            COMMITS_AUSENTES.setdefault(h, (tuple(valor[0]), float(valor[1])))
    respondieron = datos.get("repos")
    if isinstance(respondieron, list):
        REPOS_QUE_RESPONDIERON.update(r for r in respondieron if isinstance(r, str))


def guardar_cache_commits(ruta=None):
    ruta = ruta or CACHE_COMMITS
    with CANDADO_COMMITS:
        datos = {"version": VERSION_CACHE_COMMITS,
                 "repos": sorted(REPOS_QUE_RESPONDIERON),
                 "conocidos": dict(sorted(COMMITS_CONOCIDOS.items())),
                 "ausentes": {h: [list(v[0]), v[1]] for h, v in sorted(COMMITS_AUSENTES.items())}}
    try:
        permisos.crear(Path(ruta).parent)
        escribir_atomico(Path(ruta), json.dumps(datos, ensure_ascii=False, separators=(",", ":")))
    except OSError:
        pass


def consultar_commits(hashes, repos=None, espera=5.0):
    lista = sorted({h.lower() for h in hashes})
    if not lista:
        return {}, []
    repos = repos_conocidos() if repos is None else list(repos)
    llave_repos = tuple(nucleo.normalizar(r) for r in repos)
    ahora = time.time()
    with CANDADO_COMMITS:
        leer_cache_commits()
        faltan = [h for h in lista if h not in COMMITS_CONOCIDOS
                  and not (COMMITS_AUSENTES.get(h, (None, 0))[0] == llave_repos
                           and ahora - COMMITS_AUSENTES[h][1] < VIDA_AUSENTE)]
    if faltan:
        entrada = "".join(f"{h}^{{commit}}\n" for h in faltan).encode("ascii")
        respuestas = {}

        def consultar(repo):
            try:
                proceso = subprocess.run(["git", "-C", repo, "cat-file", "--batch"], input=entrada,
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=espera,
                                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except (OSError, subprocess.SubprocessError):
                return
            if proceso.returncode == 0:
                respuestas[repo] = proceso.stdout

        hilos = [threading.Thread(target=consultar, args=(repo,), daemon=True) for repo in repos]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(espera + 1)
        hallados = {}
        for repo in repos:
            if repo in respuestas:
                leer_lote(respuestas[repo], faltan, repo, hallados)
        with CANDADO_COMMITS:
            COMMITS_CONOCIDOS.update(hallados)
            for repo in repos:
                clave = nucleo.normalizar(repo)
                if repo in respuestas:
                    REPOS_QUE_RESPONDIERON.add(clave)
                else:
                    REPOS_QUE_RESPONDIERON.discard(clave)
            if len(respuestas) == len(repos):
                for h in faltan:
                    if h not in hallados:
                        COMMITS_AUSENTES[h] = (llave_repos, ahora)
        if respuestas:
            guardar_cache_commits()
    with CANDADO_COMMITS:
        consultados = [repo for repo in repos if nucleo.normalizar(repo) in REPOS_QUE_RESPONDIERON]
        return {h: COMMITS_CONOCIDOS.get(h) for h in lista}, consultados


class Rutas:
    def __init__(self, cerebro):
        self.cerebro = cerebro
        self.existe_cache = {}

    def existe(self, ruta):
        clave = nucleo.normalizar(ruta)
        if clave not in self.existe_cache:
            self.existe_cache[clave] = os.path.exists(ruta)
        return self.existe_cache[clave]

    def bases(self, origen):
        return bases_de(self.cerebro.por_id[origen]["ruta"], self.cerebro.proyecto_de.get(origen))

    def resolver(self, origen, ruta_texto):
        return resolver_ruta(ruta_texto, self.bases(origen), self.existe)


def bases_de(ruta_nota, proyecto):
    salida = [str(Path(ruta_nota).parent)]
    for raiz, _ in nucleo.RAICES_PROYECTO:
        if proyecto and nucleo.normalizar(raiz) == proyecto:
            salida.insert(1, raiz)
        else:
            salida.append(raiz)
    return salida


def resolver_ruta(ruta_texto, bases, existe=os.path.exists):
    crudo = ruta_texto.strip()
    if "%" in crudo:
        crudo = urllib.parse.unquote(crudo)
    if nucleo.es_de_red(crudo):
        return None, False, False
    if re.match(r"^[A-Za-z]:[\\/]", crudo) or (os.sep == "/" and crudo.startswith("/")):
        ruta = os.path.normpath(crudo)
        return ruta, existe(ruta), True
    relativa = crudo.replace("/", os.sep).replace("\\", os.sep)
    primera = next((c for c in relativa.split(os.sep) if c not in (".", "..")), "")
    plausible = None
    for base in bases:
        ruta = os.path.normpath(os.path.join(base, relativa))
        if existe(ruta):
            return ruta, True, False
        if plausible is None and primera and existe(os.path.join(base, primera)):
            plausible = ruta
    return plausible, False, False


_anclas = {}


def ancla_de(extensiones):
    clave = tuple(sorted(e.lower() for e in extensiones))
    if clave not in _anclas:
        _anclas[clave] = re.compile(f'(?:{"|".join(re.escape(e) for e in clave)})(?![\\w\\-])', re.I)
    return _anclas[clave]


def extraer_rutas(texto, extensiones=(".md",)):
    salida = []
    for m in ancla_de(extensiones).finditer(texto):
        fin = m.end()
        a = texto.rfind("\n", 0, m.start()) + 1
        tramo = texto[a:fin]
        inicio = None
        for d in RE_UNIDAD.finditer(tramo):
            if not any(c in PROHIBIDOS_EN_RUTA for c in tramo[d.end():]):
                entre_comillas = d.start() > 0 and tramo[d.start() - 1] == "`" and texto[fin:fin + 1] == "`"
                if entre_comillas or not re.search(r"\s", tramo[d.start():]):
                    inicio = a + d.start()
                break
        if inicio is None:
            k = m.start()
            while k > a and (texto[k - 1].isalnum() or texto[k - 1] in "_-.[]\\/"):
                k -= 1
            if texto[k:m.start()].count("\\") + texto[k:m.start()].count("/") == 0:
                continue
            if k > a and texto[k - 1] in ":%$~":
                continue
            if texto[fin:fin + 1] == "`":
                abre = texto.rfind("`", a, k)
                if abre >= 0 and not any(c in PROHIBIDOS_EN_RUTA for c in texto[abre + 1:k]):
                    k = abre + 1
            inicio = k
        ruta = texto[inicio:fin]
        nombre = re.split(r"[\\/]", ruta)[-1]
        if not nombre[:-len(m.group(0))] or re.search(r"\s", nombre) or "…" in ruta:
            continue
        salida.append((ruta, inicio, fin))
    return salida


es_historica = nucleo.es_historica


def alrededor(texto, posicion, despues=80):
    a = texto.rfind("\n", 0, posicion) + 1
    return texto[a:posicion + despues]


def rutas_rotas(ruta_nota, texto, antes=""):
    fuente = nucleo.fuente_de_ruta(ruta_nota)
    if fuente is None or fuente.get("historico") or nucleo.es_changelog(ruta_nota):
        return []
    clave = nucleo.normalizar(ruta_nota)
    proyecto = next((nucleo.normalizar(r) for r, _ in nucleo.RAICES_PROYECTO if clave.startswith(f"{nucleo.normalizar(r)}\\")),
                    None)
    bases = bases_de(ruta_nota, proyecto)
    ya = {r for r, _, _ in extraer_rutas(antes or "")}
    salida = []
    for ruta_texto, inicio, fin in extraer_rutas(texto or ""):
        if ruta_texto in ya:
            continue
        ruta, existe, _ = resolver_ruta(ruta_texto, bases)
        if ruta is None or existe or ruta in salida or RE_YA_NO_ESTA.search(alrededor(texto, inicio, fin - inicio + 80)):
            continue
        salida.append(ruta)
    return salida


def destinos_de_enlaces(texto):
    salida = [m.group(1).strip() for m in nucleo.RE_WIKI.finditer(texto)]
    for m in nucleo.RE_ENLACE.finditer(texto):
        destino = m.group(2).strip()
        if destino.startswith("<") and destino.endswith(">"):
            destino = destino[1:-1].strip()
        if destino.split("#")[0].split("?")[0].lower().endswith(".md") and not nucleo.RE_ESQUEMA.match(destino):
            salida.append(destino)
    return salida


def enlaces_rotos(ruta_nota, texto, antes=""):
    fuente = nucleo.fuente_de_ruta(ruta_nota)
    if fuente is None or fuente.get("historico") or fuente.get("registro"):
        return []
    ya = set(destinos_de_enlaces(antes or ""))
    carpeta = Path(ruta_nota).parent
    dudosos = []
    for destino in destinos_de_enlaces(texto or ""):
        limpio = urllib.parse.unquote(destino.split("#")[0].split("?")[0])
        nombre = limpio if limpio.lower().endswith(".md") else f"{limpio}.md"
        if destino not in ya and destino not in dudosos and not (carpeta / nombre).is_file():
            dudosos.append(destino)
    if not dudosos:
        return []
    cerebro = nucleo.desde_disco(con_entidades=False)
    origen = cerebro.por_ruta.get(nucleo.normalizar(ruta_nota))
    rotos = {x["destino"] for x in cerebro.rotos if x["de"] == origen and x["clase"] != "indice"}
    return [d for d in dudosos if d in rotos]


def regla_rutas(cerebro, rutas):
    salida = []
    fuera = {}
    for nodo in cerebro.nodos:
        origen = nodo["id"]
        cuerpo = nodo["_cuerpo"]
        historica = es_historica(nodo)
        vistos = set()
        for ruta_texto, inicio, fin in extraer_rutas(cuerpo):
            ruta, existe, absoluta = rutas.resolver(origen, ruta_texto)
            if ruta is None:
                continue
            clave = nucleo.normalizar(ruta)
            if clave in vistos or clave in cerebro.por_ruta:
                continue
            vistos.add(clave)
            if existe:
                if nucleo.excluido(clave) or nucleo.dentro_de_fuentes(clave) or not absoluta:
                    continue
                fuera.setdefault(clave, (ruta, []))[1].append((origen, linea_en(nodo, inicio)))
                continue
            if historica or RE_YA_NO_ESTA.search(alrededor(cuerpo, inicio, fin - inicio + 80)):
                continue
            salida.append(hallazgo(
                "rutaVieja", origen, linea_en(nodo, inicio), "aviso",
                f'Nombra {ruta}, que no existe{"" if absoluta else " (la leí como ruta relativa)"}.',
                "Si se movió, poner la ruta nueva; si se borró a propósito, decirlo en el mismo renglón o sacar la ruta."))
    for clave, (ruta, citas) in sorted(fuera.items()):
        origen, linea = citas[0]
        otras = len(citas) - 1
        extra = "" if not otras else (" También la nombra otra nota." if otras == 1
                                      else f" También la nombran otras {otras} notas.")
        salida.append(hallazgo(
            "fueraDelCerebro", origen, linea, "info",
            f"Nombra {ruta}, que existe pero el cerebro no la lee.{extra}",
            "Si es una nota que Claude tiene que encontrar, sumar su carpeta a «fuentes» en config.json."))
    return salida


def regla_commits(cerebro, repos=None):
    citas = []
    ya_extraidas = getattr(cerebro, "citas_commits", None) or {}
    for nodo in cerebro.nodos:
        propias = ya_extraidas.get(nodo["id"])
        for valor, inicio, _ in (extraer_commits(nodo["_cuerpo"]) if propias is None else propias):
            citas.append((valor, nodo, inicio))
    if not citas:
        return []
    repos = repos_conocidos() if repos is None else list(repos)
    propio = nucleo.normalizar(nucleo.CARPETA)
    de_proyectos = [r for r in repos if nucleo.normalizar(r) != propio]
    if not de_proyectos:
        arreglo = ("Si alguno tiene su repositorio, revisá su «raiz» en config.json: tiene que ser la carpeta donde está "
                   ".git." if nucleo.CONFIG["proyectos"]
                   else "Para que los verifique, sumá tus proyectos a «proyectos» en config.json.")
        return [hallazgo("commits", indice_principal(cerebro), None, "info",
                         "Ningún proyecto de la configuración tiene su propio repositorio git (una carpeta .git en su "
                         "«raiz»): los commits citados no se verificaron.", arreglo)]
    encontrados, consultados = verificar_commits([c[0] for c in citas], repos)
    if not any(nucleo.normalizar(r) != propio for r in consultados):
        return [hallazgo("commits", indice_principal(cerebro), None, "info",
                         "No pude consultar git: los commits citados quedaron sin verificar.",
                         "Revisar que git esté en el PATH.")]
    salida = []
    vistos = set()
    huellas = set().union(*(huellas_de(n["_cuerpo"]) for n in cerebro.nodos))
    nombres = ", ".join(Path(r).name or r for r in consultados)
    for valor, nodo, inicio in citas:
        if encontrados.get(valor) or (nodo["id"], valor) in vistos:
            continue
        if any(h.startswith(valor) or valor.startswith(h) for h in huellas):
            continue
        if RE_YA_NO_ESTA.search(alrededor(nodo["_cuerpo"], inicio)):
            continue
        if RE_NEGADO.search(nodo["_cuerpo"][max(0, inicio - 8):inicio]):
            continue
        vistos.add((nodo["id"], valor))
        salida.append(hallazgo(
            "commitInexistente", nodo["id"], linea_en(nodo, inicio), "aviso",
            f"Cita el commit {valor}, que no está en ningún repo conocido ({nombres}).",
            "Buscar el hash correcto con git log y corregirlo. Si no es un commit (la huella de un archivo, por ejemplo), "
            "decirlo al lado («huella», «sha256») o sacar las comillas."))
    return salida


def regla_tamano(cerebro):
    salida = []
    for nodo in cerebro.nodos:
        tokens = int(nodo["bytes"] / BYTES_POR_TOKEN)
        lineas = nodo["lineas"]
        if lineas <= LINEAS_READ and tokens <= TOKENS_READ:
            continue
        motivos = []
        if lineas > LINEAS_READ:
            motivos.append(f"{miles(lineas)} líneas (Read trae {miles(LINEAS_READ)})")
        if tokens > TOKENS_READ:
            motivos.append(f"~{miles(tokens)} tokens (el tope de Read es {miles(TOKENS_READ)})")
        if cerebro.fuente_de[nodo["id"]].get("memoria"):
            salida.append(hallazgo(
                "noEntraEnRead", nodo["id"], 1, "aviso",
                f'Es una memoria y no entra en un Read: {" y ".join(motivos)}. Read muestra solo el principio y avisa '
                "que la vista es parcial, así que lo último que se agregó no se ve de una.",
                f"Pasar lo viejo a notas de archivo y dejar en esta solo lo vigente (lo decide {QUIEN})."))
        else:
            salida.append(hallazgo(
                "noEntraEnRead", nodo["id"], 1, "info",
                f'Referencia larga: {" y ".join(motivos)}. Read la muestra por partes y avisa que la vista es parcial.',
                f"Para ir directo a lo que hace falta: {configuracion.comando()} --buscar \"tema\", "
                "que da la sección y la línea."))
    return salida


def linea_del_corte(ruta, tope):
    try:
        datos = Path(ruta).read_bytes()
    except OSError:
        return None
    return datos[:tope].count(b"\n") + 1 if len(datos) > tope else None


def regla_indice(cerebro):
    salida = []
    topes = f"{LINEAS_INDICE} líneas o {BYTES_INDICE // 1000} KB"
    for nodo in cerebro.nodos:
        if nodo["tipo"] != "indice":
            continue
        lineas = nodo["lineas"]
        entradas = len(cerebro.listados_por_indice.get(nodo["id"], ()))
        kb = decimal(nodo["bytes"] / 1000)
        texto = (f'{Path(nodo["ruta"]).name}: {lineas} de {LINEAS_INDICE} líneas y {kb} de {BYTES_INDICE // 1000} KB, '
                 f'{entradas} entradas.')
        cortes = ([LINEAS_INDICE + 1] if lineas > LINEAS_INDICE else []) + \
                 ([linea_del_corte(nodo["ruta"], BYTES_INDICE)] if nodo["bytes"] > BYTES_INDICE else [])
        if cortes:
            linea = min((c for c in cortes if c), default=None)
            desde = f"desde la línea {linea} no lo ve" if linea else "lo de abajo no lo ve"
            salida.append(hallazgo("presupuestoIndice", nodo["id"], linea, "peligro",
                                   f"{texto} Claude solo lee las primeras {topes} al arrancar (lo que llegue antes): "
                                   f"{desde}.",
                                   f"Juntar entradas o acortar ganchos (con OK de {QUIEN}, "
                                   "porque cambia lo que Claude ve al arrancar)."))
        elif lineas >= AVISO_INDICE or nodo["bytes"] >= AVISO_BYTES_INDICE:
            salida.append(hallazgo("presupuestoIndice", nodo["id"], None, "aviso",
                                   f"{texto} Se está acercando al tope que Claude lee al arrancar.",
                                   f"Pensar qué entradas se pueden juntar o acortar antes de llegar a {topes}."))
        else:
            salida.append(hallazgo("presupuestoIndice", nodo["id"], None, "info", f"{texto} Entra entero.", ""))
    for x in cerebro.indice_roto:
        indice = cerebro.por_id.get(x["indice"])
        linea = None
        if indice:
            posicion = indice["_cuerpo"].find(x["destino"])
            linea = linea_en(indice, posicion) if posicion >= 0 else None
        salida.append(hallazgo("indiceRoto", x["indice"], linea, "peligro",
                               f'El índice apunta a {citar(x["destino"], LARGO_CITA)}, que no existe.',
                               "Sacar la línea del índice o corregir el nombre del archivo."))
    for x in cerebro.rotos:
        nota = cerebro.por_id.get(x["de"])
        if x["clase"] == "indice" or nota is None:
            continue
        posicion = nota["_cuerpo"].find(x["destino"])
        salida.append(hallazgo("enlaceRoto", x["de"], linea_en(nota, posicion) if posicion >= 0 else None, "aviso",
                               f'Enlaza a {citar(x["destino"], LARGO_CITA)}, que no lleva a ninguna nota.',
                               "Corregir el nombre o la ruta, o sacar el enlace si esa nota ya no existe."))
    for identificador in cerebro.sin_indice:
        salida.append(hallazgo("sinIndice", identificador, None, "aviso",
                               "Es una memoria que MEMORY.md no lista: Claude no la ve al arrancar.",
                               "Sumarla al índice con una línea que diga cuándo abrirla."))
    for identificador, via in sorted(cerebro.por_enlace.items()):
        nota = cerebro.por_id.get(via)
        nombre = Path(nota["ruta"]).name if nota else via
        salida.append(hallazgo("llegaPorEnlace", identificador, None, "info",
                               f"MEMORY.md no la lista, pero se llega por {nombre}, que sí está en el índice.",
                               ""))
    return salida


def es_floja(descripcion, nodo):
    d = sin_tildes(nucleo.limpiar_md(descripcion)).strip(" .")
    if len(d) < DESCRIPCION_MINIMA:
        return True
    nombres = {sin_tildes(nodo["slug"]).replace("-", " "), sin_tildes(Path(nodo["ruta"]).stem).replace("-", " "),
               sin_tildes(nodo["titulo"])}
    return d.replace("-", " ") in nombres


def regla_frontmatter(cerebro):
    salida = []
    for nodo in cerebro.nodos:
        if not cerebro.fuente_de[nodo["id"]].get("memoria") or nodo["tipo"] == "indice":
            continue
        frontmatter = nodo.get("_frontmatter") or {}
        faltan = []
        if not frontmatter:
            salida.append(hallazgo("frontmatter", nodo["id"], 1, "aviso",
                                   "No tiene frontmatter (name, description, type): Claude no sabe de qué trata sin abrirla.",
                                   "Agregar el bloque --- con name, description y metadata.type."))
            continue
        nombre = nucleo.dato(frontmatter, "name")
        tipo = nucleo.dato(frontmatter, "type", True)
        descripcion = nucleo.dato(frontmatter, "description")
        if not nombre:
            faltan.append("name")
        if not descripcion:
            faltan.append("description")
        if not tipo:
            faltan.append("type")
        if faltan:
            salida.append(hallazgo("frontmatter", nodo["id"], 1, "aviso",
                                   f'Al frontmatter le falta {", ".join(faltan)}.',
                                   "Completarlo: la description es lo que Claude usa para decidir si abre la nota."))
        if tipo and tipo not in TIPOS_MEMORIA:
            salida.append(hallazgo("frontmatter", nodo["id"], linea_de_clave(nodo, "type"), "revisar",
                                   f"El type es {citar(tipo, LARGO_CITA)}, que no es user, feedback, project ni reference.",
                                   "Poner uno de los cuatro tipos."))
        if nombre and nombre != Path(nodo["ruta"]).stem:
            salida.append(hallazgo("frontmatter", nodo["id"], linea_de_clave(nodo, "name"), "revisar",
                                   f'El name dice {citar(nombre, LARGO_CITA)} y el archivo se llama {Path(nodo["ruta"]).name}: '
                                   "los [[enlaces]] pueden ir a parar a otro lado.",
                                   "Que el name sea igual al nombre del archivo sin .md."))
        if descripcion and es_floja(descripcion, nodo):
            salida.append(hallazgo("descripcionFloja", nodo["id"], linea_de_clave(nodo, "description"), "revisar",
                                   f"La description ({citar(descripcion, 60)}) casi no dice nada.",
                                   "Escribir en una frase qué hay adentro y cuándo conviene abrirla."))
    for identificador, (indice, gancho, _) in cerebro.ganchos.items():
        nodo = cerebro.por_id.get(identificador)
        if nodo is None or not cerebro.fuente_de[identificador].get("memoria"):
            continue
        if len(gancho) < 15:
            indice_nodo = cerebro.por_id[indice]
            salida.append(hallazgo("ganchoFlojo", indice, linea_en(indice_nodo, cerebro.ganchos[identificador][2]), "revisar",
                                   f'La línea del índice para {Path(nodo["ruta"]).name} no dice cuándo abrirla'
                                   + (" (está vacía)." if not gancho else "."),
                                   "Agregar después del enlace una frase corta con lo esencial."))
    return salida


def cifras(texto):
    normal = sin_tildes(texto)
    salida = {}
    for m in RE_CIFRA.finditer(normal):
        if RE_CIFRA_RELATIVA.search(normal[max(0, m.start() - 12):m.start()]):
            continue
        numero = int(m.group(1))
        for palabra in m.group(2).split():
            if len(palabra) >= 4 and palabra not in PALABRAS_SIN_CIFRA:
                salida.setdefault(palabra, {}).setdefault(numero, re.sub(r"\s+", " ", texto[m.start():m.end()]))
    numeros = {int(n) for n in RE_NUMERO_SUELTO.findall(normal)}
    return salida, numeros


def regla_cifras(cerebro):
    salida = []
    for nodo in cerebro.nodos:
        if not cerebro.fuente_de[nodo["id"]].get("memoria") or nodo["tipo"] == "indice":
            continue
        descripcion = nucleo.dato(nodo.get("_frontmatter") or {}, "description")
        gancho = cerebro.ganchos.get(nodo["id"], (None, "", 0))
        de_desc = cifras(descripcion)
        de_gancho = cifras(gancho[1])
        del_cuerpo = cifras(nodo["_cuerpo"])
        avisadas = set()
        comparaciones = [("la description", de_desc, "el índice", de_gancho, False),
                         ("la description", de_desc, "el cuerpo", del_cuerpo, True),
                         ("el índice", de_gancho, "el cuerpo", del_cuerpo, True)]
        for nombre_a, (a, _), nombre_b, (b, numeros_b), pedir_unico in comparaciones:
            for palabra in sorted(set(a) & set(b)):
                if set(a[palabra]) & numeros_b or (pedir_unico and len(b[palabra]) != 1):
                    continue
                llave = (frozenset(a[palabra]), frozenset(b[palabra]))
                if llave in avisadas:
                    continue
                avisadas.add(llave)
                linea = linea_de_clave(nodo, "description") if nombre_a == "la description" else None
                dice_a = " o ".join(citar(f, LARGO_CITA) for _, f in sorted(a[palabra].items()))
                dice_b = " o ".join(citar(f, LARGO_CITA) for _, f in sorted(b[palabra].items()))
                salida.append(hallazgo(
                    "cifras", nodo["id"], linea, "revisar",
                    f"{nombre_a[0].upper()}{nombre_a[1:]} dice {dice_a} y {nombre_b} dice {dice_b}.",
                    "Revisar cuál vale y dejar el mismo número en los dos lados (puede ser lo mismo contado distinto)."))
    return salida


def oraciones(cuerpo, filtro=""):
    lineas = cuerpo.split("\n")
    parrafo = []
    inicio = 0
    posicion = 0
    en_codigo = False
    for linea in lineas + [""]:
        s = linea.strip()
        if s.startswith("```") or s.startswith("~~~"):
            en_codigo = not en_codigo
        corta = en_codigo or not s or RE_ITEM.match(linea) or s.startswith("#")
        if corta and parrafo:
            texto = "\n".join(parrafo)
            if not filtro or filtro in texto:
                for m in RE_ORACION.finditer(texto):
                    if m.group(0).strip():
                        yield inicio + m.start(), m.group(0)
            parrafo = []
        if not en_codigo and s and not s.startswith("#") and not s.startswith("```") and not s.startswith("~~~"):
            if not parrafo:
                inicio = posicion
            parrafo.append(linea)
        posicion += len(linea) + 1


def probado_en(texto):
    normal = sin_tildes(texto)
    for m in RE_PROBADO.finditer(normal):
        if not RE_NEGACION_ANTES.search(normal[max(0, m.start() - 30):m.start()]):
            return m.start()
    return None


def estado_de(cerebro, identificador, cache):
    if identificador in cache:
        return cache[identificador]
    nodo = cerebro.por_id[identificador]
    cuerpo = nodo["_cuerpo"]
    normal = sin_tildes(cuerpo)
    descripcion = nucleo.dato(nodo.get("_frontmatter") or {}, "description")
    negado_en_cuerpo = RE_SIN_PROBAR.search(normal) is not None
    positivo = None
    if not negado_en_cuerpo:
        posicion = probado_en(cuerpo)
        if posicion is not None:
            positivo = linea_en(nodo, posicion)
        elif descripcion and probado_en(descripcion) is not None:
            positivo = linea_de_clave(nodo, "description")
    negada_desc = (bool(descripcion) and RE_SIN_PROBAR.search(sin_tildes(descripcion)) is not None
                   and probado_en(descripcion) is None)
    cache[identificador] = (positivo, negada_desc)
    return cache[identificador]


def regla_probado(cerebro):
    salida = []
    cache = {}
    vistos = set()
    for nodo in cerebro.nodos:
        origen = nodo["id"]
        if nodo["tipo"] == "handoff" or es_historica(nodo) or "[[" not in nodo["_cuerpo"]:
            continue
        if not RE_PRUEBA_RAPIDA.search(nodo["_cuerpo"]):
            continue
        for inicio, oracion in oraciones(nodo["_cuerpo"], "[["):
            if "[[" not in oracion:
                continue
            normal = sin_tildes(oracion)
            negada = RE_SIN_PROBAR.search(normal) is not None
            positiva = probado_en(oracion) is not None
            if negada == positiva:
                continue
            for m in nucleo.RE_WIKI.finditer(oracion):
                destino, _ = cerebro.resolver_wiki(origen, m.group(1).strip())
                if not destino or destino == origen or (origen, destino) in vistos:
                    continue
                positivo, negada_desc = estado_de(cerebro, destino, cache)
                nombre = Path(cerebro.por_id[destino]["ruta"]).name
                if negada and positivo:
                    vistos.add((origen, destino))
                    salida.append(hallazgo(
                        "probadoOSinProbar", origen, linea_en(nodo, inicio), "revisar",
                        f"Dice que {nombre} está sin probar, pero esa nota dice que se probó (línea {positivo}).",
                        "Revisar cuál vale y actualizar la que quedó vieja."))
                elif positiva and negada_desc:
                    vistos.add((origen, destino))
                    salida.append(hallazgo(
                        "probadoOSinProbar", destino, linea_de_clave(cerebro.por_id[destino], "description"), "revisar",
                        f'Su description dice que falta probar, pero {Path(nodo["ruta"]).name}:{linea_en(nodo, inicio)} '
                        "dice que se probó.",
                        "Revisar cuál vale y actualizar la que quedó vieja."))
    return salida


def palabras_utiles(texto):
    import buscador
    return {t for t in buscador.terminos(texto) if len(t) >= 3 and not (t.isdigit() and len(t) < 4)}


def commits_recientes(repos, dias=DIAS_RESUELTO):
    def leer(repo):
        crudo = correr_git(repo, ["log", f"--since={dias}.days", "--format=%x01%h%x02%ct%x02%B%x03", "--name-only",
                                  "--diff-merges=first-parent"], espera=15)
        salida = []
        for bloque in (crudo or "").split("\x01")[1:]:
            cabeza, _, nombres = bloque.partition("\x03")
            partes = cabeza.split("\x02", 2)
            if len(partes) != 3 or not partes[1].isdecimal():
                continue
            mensaje = partes[2].strip()
            asunto = mensaje.split("\n", 1)[0].strip()
            salida.append({"repo": repo, "sha": partes[0], "tiempo": int(partes[1]), "asunto": asunto, "mensaje": mensaje,
                           "palabras": palabras_utiles(mensaje), "delAsunto": palabras_utiles(asunto),
                           "tocados": {nucleo.normalizar(os.path.join(repo, n.strip()))
                                       for n in nombres.split("\n") if n.strip()}})
        return salida

    return [c for lista in en_paralelo([lambda r=r: leer(r) for r in repos], espera=20) for c in (lista or [])]


def codigo_nombrado(texto):
    import buscador
    return {c[0] for c in map(buscador.cita_de_codigo, buscador.RE_CODIGO.finditer(texto)) if c}


def deja_sin_tocar(mensaje, propias):
    return any(RE_SIN_TOCAR.search(sin_tildes(frase)) and len(palabras_utiles(frase) & propias) >= 2
               for frase in RE_FRASE_COMMIT.split(mensaje))


def sangria_de(renglon):
    return len(renglon) - len(renglon.lstrip())


def item_de(renglones, i, desde, hasta):
    propia = sangria_de(renglones[i])
    j = i
    while not RE_ITEM.match(renglones[j]) or (j < i and sangria_de(renglones[j]) >= propia):
        if j < i and not RE_ITEM.match(renglones[j]) and sangria_de(renglones[j]) < propia:
            return None
        j -= 1
        if j < desde:
            return None
    sangria = sangria_de(renglones[j])
    k = j
    while k < min(hasta, j + LINEAS_DE_ITEM_RESUELTO) and sangria_de(renglones[k + 1]) > sangria:
        k += 1
    return j, k


def problemas_de(nodo):
    renglones = nodo["_cuerpo"].split("\n")
    posiciones, desde, hasta = [], [], [0] * len(renglones)
    posicion = comienzo = 0
    for i, renglon in enumerate(renglones):
        posiciones.append(posicion)
        posicion += len(renglon) + 1
        if not renglon.strip():
            comienzo = i + 1
        desde.append(comienzo)
    fin = len(renglones) - 1
    for i in range(len(renglones) - 1, -1, -1):
        if not renglones[i].strip():
            fin = i - 1
        hasta[i] = fin
    salida = []
    for i, renglon in enumerate(renglones):
        normal = sin_tildes(renglon)
        if not RE_PROBLEMA.search(RE_BIEN.sub(" ", normal)) or RE_RESUELTO.search(normal):
            continue
        a, b = max(desde[i], i - VENTANA_RESUELTO), min(hasta[i], i + VENTANA_RESUELTO)
        cerca = renglones[a:b + 1]
        item = item_de(renglones, i, desde[i], hasta[i])
        if item:
            cerca = cerca + renglones[item[0]:item[1] + 1]
        if RE_RESUELTO_CERCA.search(sin_tildes(" ".join(cerca))):
            continue
        vecinos = 0 if renglon.lstrip().startswith("|") else VECINOS_RESUELTO
        a, b = max(desde[i], i - vecinos), min(hasta[i], i + vecinos)
        if RE_ITEM.match(renglon):
            sangria = len(renglon) - len(renglon.lstrip())
            while b < min(hasta[i], i + LINEAS_DE_ITEM) and len(renglones[b + 1]) - len(renglones[b + 1].lstrip()) > sangria:
                b += 1
        salida.append({"linea": linea_en(nodo, posiciones[i]), "renglon": renglon.strip(),
                       "contexto": " ".join(renglones[a:b + 1]), "bloque": desde[i]})
    return salida


def fechas_de_renglones(pedidos, repos):
    fechas = {}
    por_repo = {}
    for ruta, lineas in pedidos.items():
        repo = repo_de(ruta, repos)
        if repo:
            por_repo[(repo, ruta)] = lineas
        elif proyectos_de_memoria(ruta):
            try:
                tiempo = os.path.getmtime(ruta)
            except OSError:
                continue
            for n in lineas:
                fechas[(ruta, n)] = tiempo
    claves = sorted(por_repo)
    culpas = en_paralelo([lambda c=c: culpa_de_lineas(c[0], c[1], por_repo[c]) for c in claves], espera=20)
    for (repo, ruta), culpa in zip(claves, culpas):
        for n, (sha, tiempo) in (culpa or {}).items():
            if sha != SHA_VACIO and tiempo:
                fechas[(ruta, n)] = tiempo
    return fechas


def regla_resuelto(cerebro, repos=None):
    repos = repos_conocidos() if repos is None else list(repos)
    candidatos = {}
    for nodo in cerebro.nodos:
        if nodo["tipo"] == "handoff" or es_historica(nodo) or nodo["grupo"] in GRUPOS_ANCLAS_RESUMIDAS:
            continue
        problemas = problemas_de(nodo)
        if problemas:
            candidatos[nodo["ruta"]] = (nodo, problemas)
    commits = commits_recientes(repos) if candidatos and repos else []
    if not commits:
        if candidatos and repos and not any(correr_git(r, ["rev-parse", "--git-dir"]) for r in repos):
            return [hallazgo("yaResuelto", indice_principal(cerebro), None, "info",
                             "No pude leer los commits: git no respondió en ningún repo, así que no revisé si los problemas "
                             "anotados ya están resueltos.", "Ver que git esté instalado y en el PATH.")]
        return []
    veces = {}
    for c in commits:
        for palabra in c["palabras"]:
            veces[palabra] = veces.get(palabra, 0) + 1
    fechas = fechas_de_renglones({ruta: [p["linea"] for p in lista] for ruta, (_, lista) in candidatos.items()}, repos)
    salida = []
    for ruta, (nodo, problemas) in candidatos.items():
        clave = nucleo.normalizar(ruta)
        repo = repo_de(ruta, repos)
        mejores = {}
        for p in problemas:
            fecha = fechas.get((ruta, p["linea"]))
            if not fecha:
                continue
            propias, del_renglon = palabras_utiles(p["contexto"]), palabras_utiles(p["renglon"])
            nombrados = codigo_nombrado(p["contexto"])
            for c in commits:
                if c["tiempo"] <= fecha or clave in c["tocados"] or (repo and c["repo"] != repo):
                    continue
                if nombrados and not nombrados & {os.path.basename(t).lower() for t in c["tocados"]}:
                    continue
                if deja_sin_tocar(c.get("mensaje", ""), propias):
                    continue
                comunes = propias & c["palabras"]
                raras = [w for w in comunes if veces[w] <= PALABRA_RARA]
                if not raras or not comunes & del_renglon or not propias & c["delAsunto"]:
                    continue
                puntaje = sum(math.log(len(commits) / veces[w]) for w in comunes)
                if len(raras) < RARAS_EN_COMUN and puntaje < PUNTAJE_CON_UNA_RARA:
                    continue
                if puntaje >= PUNTAJE_RESUELTO and puntaje > mejores.get(p["bloque"], (0.0,))[0]:
                    mejores[p["bloque"]] = (puntaje, p, c)
        for _, p, c in sorted(mejores.values(), key=lambda x: x[1]["linea"]):
            asunto = citar(c["asunto"].replace(". ", "; "), LARGO_CITA)
            renglon = citar(p["renglon"].replace("**", ""), LARGO_CITA)
            salida.append(hallazgo(
                "yaResuelto", nodo["id"], p["linea"], "revisar",
                f'Puede que ya esté resuelto: el commit {c["sha"]} ({dia(c["tiempo"])}) {asunto} es posterior a este '
                f"renglón y toca lo mismo. El renglón dice {renglon}.",
                f"Comprobar en el código si quedó resuelto y, si es así, actualizar la nota (lo decide {QUIEN})."))
    return salida


def alcance(cerebro):
    salidas = {}
    for de, a in cerebro.fuertes:
        salidas.setdefault(de, []).append(a)
    raices = [n["id"] for n in cerebro.nodos if n["tipo"] in ("indice", "instrucciones")]
    saltos = {r: 0 for r in raices}
    frente = list(raices)
    while frente:
        siguiente = []
        for actual in frente:
            for vecino in salidas.get(actual, ()):
                if vecino not in saltos:
                    saltos[vecino] = saltos[actual] + 1
                    siguiente.append(vecino)
        frente = siguiente
    return saltos


def regla_huerfanas(cerebro, saltos):
    con_entrada = {a for (de, a) in cerebro.fuertes if de != a} | set(cerebro.sin_indice)
    salida = []
    inalcanzables = [n for n in cerebro.nodos if n["id"] not in saltos]
    for nodo in inalcanzables:
        if nodo["tipo"] in ("indice", "instrucciones", "handoff") or nodo["id"] in con_entrada:
            continue
        salida.append(hallazgo(
            "huerfanaReal", nodo["id"], None, "aviso",
            "Ninguna nota la nombra y no se llega a ella desde MEMORY.md ni desde los CLAUDE.md: "
            "Claude no la va a encontrar sola.",
            "Nombrarla desde la nota o el LEEME que trata ese tema, o sumarla al índice si es memoria."))
    if inalcanzables:
        handoffs = sum(1 for n in inalcanzables if n["tipo"] == "handoff")
        salida.append(hallazgo(
            "alcance", indice_principal(cerebro), None, "info",
            f"{len(inalcanzables)} de {len(cerebro.nodos)} notas no se alcanzan siguiendo enlaces desde MEMORY.md "
            "y los CLAUDE.md" + (f" ({handoffs} son handoffs)" if handoffs else "") + ".",
            ""))
    return salida


def proyectos_de_memoria(ruta_nota):
    carpeta = os.path.realpath(os.path.dirname(ruta_nota))
    return [p.parent.name for p in Path(carpeta).parent.parent.glob("*/memory") if os.path.realpath(p) == carpeta]


def regla_repite_claude(cerebro):
    import parecidas
    cerebro.repite_claude = parecidas.repite_claude(cerebro)
    salida = []
    for r in cerebro.repite_claude:
        instrucciones = cerebro.por_id[r["instrucciones"]]
        proyectos = proyectos_de_memoria(cerebro.por_id[r["nota"]]["ruta"])
        repetido = (f'El {round(r["parte"] * 100)} % de su texto ({r["palabras"]} de {r["total"]} palabras) ya está en '
                    f'{instrucciones["ruta"]}. El tramo más largo ({r["largo"]} palabras) está en '
                    f'{Path(instrucciones["ruta"]).name}:{r["lineaInstrucciones"]}: {citar(r["pasaje"])}.')
        if len(proyectos) > 1:
            salida.append(hallazgo(
                "repiteClaude", r["nota"], r["linea"], "info",
                f"{repetido} Esta memoria la comparten chats que arrancan en {len(proyectos)} carpetas distintas, "
                "y los que no arrancan ahí no cargan ese CLAUDE.md: la repetición les sirve.",
                ""))
        else:
            salida.append(hallazgo(
                "repiteClaude", r["nota"], r["linea"], "aviso",
                f"{repetido} Claude ya carga ese CLAUDE.md en cada chat.",
                f"Si la repetición no es a propósito, dejar en la nota solo lo que agrega y remitir a CLAUDE.md "
                f"(lo decide {QUIEN})."))
    return salida


def regla_memorias_parecidas(cerebro):
    salida = []
    for par in getattr(cerebro, "memorias_parecidas", []):
        if par.get("partesDe"):
            salida.append(hallazgo(
                "memoriasParecidas", par["a"], None, "info",
                f'Se parece a {Path(cerebro.por_id[par["b"]]["ruta"]).name}, pero son partes de {par["partesDe"]}, '
                "partidas a propósito.", ""))
            continue
        salida.append(hallazgo(
            "memoriasParecidas", par["a"], None, "revisar",
            f'Se parece a {Path(cerebro.por_id[par["b"]]["ruta"]).name} ({decimal(par["puntaje"], 2)}) '
            f'y ninguna nombra a la otra; comparten {", ".join(par["comparten"])}.',
            "Ver si es la misma memoria partida en dos: fusionarlas o, si son temas distintos, que una nombre a la otra."))
    return salida


def correr_git(repo, argumentos, espera=5.0):
    try:
        proceso = subprocess.run(["git", "-C", repo] + argumentos, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 text=True, encoding="utf-8", errors="replace", timeout=espera,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return None
    return proceso.stdout if proceso.returncode == 0 else None


def en_paralelo(tareas, espera=6.0):
    resultados = [None] * len(tareas)

    def correr(i, tarea):
        try:
            resultados[i] = tarea()
        except Exception:
            resultados[i] = None

    hilos = [threading.Thread(target=correr, args=(i, t), daemon=True) for i, t in enumerate(tareas)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(espera)
    return resultados


def repo_de(ruta, repos):
    clave = nucleo.normalizar(ruta)
    for repo in repos:
        if clave.startswith(f"{nucleo.normalizar(repo)}\\"):
            return repo
    return None


def dia(tiempo):
    d = datetime.datetime.fromtimestamp(tiempo)
    return f"{d.day}/{d.month}"


def fecha_y_hora(tiempo):
    return datetime.datetime.fromtimestamp(tiempo).strftime("%Y-%m-%d %H:%M")


def sin_blancos(texto):
    return texto.replace(" ", "").replace("\t", "").replace("\r", "")


def raices_de_codigo(base):
    return next((p["codigo"] for p in CODIGO if p["alias"] == base), [])


class Codigo:
    def __init__(self):
        self.indices = {}
        self.archivos = {}

    def indice(self, base):
        if base not in self.indices:
            indice = {}
            for raiz in raices_de_codigo(base):
                for carpeta, subcarpetas, archivos in os.walk(raiz["ruta"]):
                    subcarpetas[:] = [s for s in subcarpetas if s.lower() not in PODA_CODIGO and not nucleo.carpeta_podada(s)]
                    for nombre in archivos:
                        if os.path.splitext(nombre)[1].lower() in EXTENSIONES_ANCLA:
                            indice.setdefault(nombre.lower(), []).append(os.path.join(carpeta, nombre))
            self.indices[base] = indice
        return self.indices[base]

    def resolver(self, base, carpeta, nombre, ext, contexto, nota_ruta, antes=()):
        archivo = (f"{nombre}.{ext}").lower()
        lista = self.indice(base).get(archivo, [])
        if len(lista) > 1 and carpeta:
            limpia = carpeta.replace("/", "\\").strip("\\").lower()
            variantes = [limpia] + [f'{" ".join(antes[-i:]).lower()} {limpia}' for i in range(1, len(antes) + 1)]
            mejor = []
            for variante in variantes:
                sufijo = "\\" + variante + "\\" + archivo
                filtradas = [r for r in lista if r.lower().endswith(sufijo)]
                if len(filtradas) == 1:
                    mejor = filtradas
                    break
                if filtradas and (not mejor or len(filtradas) < len(mejor)):
                    mejor = filtradas
            lista = mejor
        raices = raices_de_codigo(base)
        if len(lista) > 1 and len(raices) > 1:
            nota = nucleo.normalizar(nota_ruta)
            for raiz in raices:
                base_raiz = f'{nucleo.normalizar(raiz["ruta"])}\\'
                if nota.startswith(base_raiz):
                    propias = [r for r in lista if nucleo.normalizar(r).startswith(base_raiz)]
                    lista = propias or lista
        if len(lista) > 1 and len(raices) > 1:
            marcadas = [r for r in lista for raiz in raices if raiz["marca"] and raiz["marca"].search(contexto)
                        and nucleo.normalizar(r).startswith(f'{nucleo.normalizar(raiz["ruta"])}\\')]
            lista = marcadas or lista
        return lista

    def archivo(self, ruta):
        if ruta not in self.archivos:
            try:
                with open(ruta, "rb") as f:
                    texto = f.read().decode("latin-1")
            except OSError:
                self.archivos[ruta] = None
                return None
            lineas = texto.split("\n")
            total = len(lineas) - 1 if texto.endswith("\n") else len(lineas)
            self.archivos[ruta] = {"texto": texto, "lineas": lineas, "total": total, "compacto": None,
                                   "ext": os.path.splitext(ruta)[1][1:].lower()}
        return self.archivos[ruta]

    def compacto(self, datos):
        if datos["compacto"] is None:
            datos["compacto"] = sin_blancos(datos["texto"])
        return datos["compacto"]

    def aparece(self, datos, busqueda, desde, hasta):
        a = max(0, desde - 1)
        b = min(len(datos["lineas"]), hasta)
        if a >= b:
            return False
        if busqueda[0] == "palabra":
            return next(self.buscar_todas("\n".join(datos["lineas"][a:b]), busqueda[1], True), None) is not None
        return busqueda[1] in sin_blancos("\n".join(datos["lineas"][a:b]))

    @staticmethod
    def llaves(linea):
        limpia = RE_LITERALES_CS.sub("", linea)
        return [c for c in limpia if c in "{}"]

    @staticmethod
    def sangria(linea):
        return len(linea.expandtabs(4)) - len(linea.expandtabs(4).lstrip())

    def fin_por_sangria(self, lineas, desde, tope):
        base = self.sangria(lineas[desde - 1])
        fin = None
        for numero in range(desde + 1, min(len(lineas), desde + tope) + 1):
            linea = lineas[numero - 1]
            if not linea.strip() or linea.lstrip().startswith("#"):
                continue
            if self.sangria(linea) <= base:
                break
            fin = numero
        return fin

    def encierra_por_sangria(self, lineas, declaracion, objetivo):
        base = self.sangria(lineas[declaracion - 1])
        for numero in range(declaracion + 1, objetivo + 1):
            linea = lineas[numero - 1]
            if linea.strip() and not linea.lstrip().startswith("#") and self.sangria(linea) <= base:
                return False
        return objetivo > declaracion

    def fin_de_bloque(self, datos, desde, tope=TOPE_BLOQUE):
        if datos.get("ext") == "py":
            return self.fin_por_sangria(datos["lineas"], desde, tope)
        lineas = datos["lineas"]
        profundidad = 0
        abierto = False
        for numero in range(desde, min(len(lineas), desde + tope) + 1):
            for llave in self.llaves(lineas[numero - 1]):
                profundidad += 1 if llave == "{" else -1
                abierto = abierto or llave == "{"
                if abierto and profundidad <= 0:
                    return numero
            if not abierto and self.sin_cuerpo(lineas[numero - 1], numero - desde):
                return None
        return None

    def encierra(self, datos, declaracion, objetivo):
        if datos.get("ext") == "py":
            return self.encierra_por_sangria(datos["lineas"], declaracion, objetivo)
        lineas = datos["lineas"]
        caso = RE_CASE.match(lineas[declaracion - 1])
        if caso:
            sangria = len(caso.group(1).expandtabs(4))
            solo_casos = True
            for numero in range(declaracion + 1, objetivo):
                linea = lineas[numero - 1]
                limpia = linea.strip()
                if not limpia:
                    continue
                if solo_casos and RE_CASE.match(linea):
                    continue
                solo_casos = False
                if len(linea.expandtabs(4)) - len(linea.expandtabs(4).lstrip()) <= sangria and not limpia.startswith("{"):
                    return False
            return True
        profundidad = 0
        abierto = False
        for numero in range(declaracion, objetivo):
            for llave in self.llaves(lineas[numero - 1]):
                profundidad += 1 if llave == "{" else -1
                abierto = abierto or llave == "{"
                if abierto and profundidad <= 0:
                    return False
            if not abierto and self.sin_cuerpo(lineas[numero - 1], numero - declaracion):
                return False
        return abierto and profundidad > 0

    @staticmethod
    def sin_cuerpo(linea, desde_la_firma):
        return desde_la_firma >= LINEAS_DE_FIRMA or ";" in RE_LITERALES_CS.sub("", linea) or "=>" in linea

    @staticmethod
    def declarado(linea, ext):
        m = (RE_DECLARACION if ext == "cs" else RE_DECLARACION_PY if ext == "py" else RE_DECLARACION_OTRAS).match(linea)
        if not m:
            return None
        if ext in ("cs", "py"):
            return m.group(1) or m.group(2), bool(m.group(1))
        return next(g for g in m.groups() if g), m.group(2) is None

    def declara(self, linea, palabra, ext="cs"):
        if palabra not in linea:
            return False
        declarado = self.declarado(linea, ext)
        if declarado:
            return declarado[0] == palabra
        return ext != "py" and bool(RE_CASE.match(linea)) and next(self.buscar_todas(linea, palabra, True), None) is not None

    def declarada_arriba(self, datos, busqueda, desde):
        lineas = datos["lineas"]
        if busqueda[0] != "palabra" or not 1 <= desde <= len(lineas):
            return False
        for numero in range(desde, max(0, desde - TOPE_DECLARACION), -1):
            if self.declara(lineas[numero - 1], busqueda[1], datos.get("ext", "cs")):
                return self.encierra(datos, numero, desde)
        return False

    def en_metodo_citado(self, datos, busqueda, desde, hasta):
        lineas = datos["lineas"]
        if not 1 <= desde <= len(lineas):
            return False
        declarado = self.declarado(lineas[desde - 1], datos.get("ext", "cs"))
        if not declarado or not declarado[1]:
            return False
        fin = self.fin_de_bloque(datos, desde)
        return bool(fin) and fin > hasta + VENTANA_ANCLA and self.aparece(datos, busqueda, desde, fin)

    def ubicaciones(self, datos, busqueda, tope=5000):
        llave = busqueda
        cache = datos.setdefault("ubicaciones", {})
        if llave in cache:
            return cache[llave]
        if busqueda[0] == "palabra":
            texto = datos["texto"]
            posiciones = self.buscar_todas(texto, busqueda[1], True)
        else:
            texto = self.compacto(datos)
            posiciones = self.buscar_todas(texto, busqueda[1], False)
        salida = []
        linea = 1
        anterior = 0
        for posicion in posiciones:
            linea += texto.count("\n", anterior, posicion)
            anterior = posicion
            salida.append(linea)
            if len(salida) >= tope:
                break
        cache[llave] = salida
        return salida

    @staticmethod
    def buscar_todas(texto, trozo, palabra_entera):
        largo = len(trozo)
        total = len(texto)
        i = texto.find(trozo)
        while i >= 0:
            if not palabra_entera:
                yield i
            else:
                antes = texto[i - 1] if i else " "
                despues = texto[i + largo] if i + largo < total else " "
                if not (antes.isalnum() or antes == "_") and not (despues.isalnum() or despues == "_"):
                    yield i
            i = texto.find(trozo, i + 1)


def que_buscar(crudo):
    if len(crudo) < 4 or RE_ANCLA.search(crudo) or crudo.startswith(":") or "\\" in crudo or "/" in crudo:
        return None
    if "..." in crudo or "…" in crudo or RE_EXT_ARCHIVO.search(crudo):
        return None
    if RE_HASH.match(crudo) and re.search(r"[a-f]", crudo) and re.search(r"\d", crudo):
        return None
    if crudo.isdigit():
        return ("palabra", crudo)
    m = re.match(r"^\[([A-Za-z_]\w*)\]$", crudo)
    if m:
        return ("palabra", f"[{m.group(1)}") if len(m.group(1)) >= 3 else None
    m = RE_IDENTIFICADOR.match(crudo)
    if m:
        partes = m.group(1).split(".")
        palabra = partes[-1] if len(partes[-1]) >= 4 else m.group(1)
        if len(palabra) < 4 or palabra.lower() in PALABRAS_CSHARP or palabra.lower() in PALABRAS_OTRAS:
            return None
        return ("palabra", palabra)
    if RE_PUNTUACION_CODIGO.search(crudo):
        compacto = re.sub(r"\s+", "", crudo)
        return ("trozo", compacto) if len(compacto) >= 6 else None
    return None


def buscables(texto, desde, hasta):
    salida = []
    for m in RE_BACKTICK.finditer(texto, desde, hasta):
        busqueda = que_buscar(m.group(1).strip())
        if busqueda:
            salida.append((m.start(), m.end(), m.group(1).strip(), busqueda))
    return salida


def es_prosa(linea):
    s = linea.strip()
    return bool(s) and not s.startswith(("|", "#", "```", "~~~", ">")) and not RE_ITEM.match(linea)


def contexto_de(cuerpo, a, b):
    if buscables(cuerpo, a, b) or not es_prosa(cuerpo[a:b]):
        return a, b
    inicio, fin = a, b
    if a > 0:
        p = cuerpo.rfind("\n", 0, a - 1) + 1
        anterior = cuerpo[p:a - 1]
        if es_prosa(anterior) and not anterior.rstrip().endswith(FINALES_DE_ORACION):
            corte = max(anterior.rfind(". "), anterior.rfind("; "))
            inicio = p + corte + 2 if corte >= 0 else p
    if b < len(cuerpo) and not cuerpo[a:b].rstrip().endswith(FINALES_DE_ORACION):
        q = cuerpo.find("\n", b + 1)
        q = len(cuerpo) if q < 0 else q
        siguiente = cuerpo[b + 1:q]
        if es_prosa(siguiente) and not RE_ITEM.match(siguiente):
            corte = siguiente.find(". ")
            fin = b + 1 + corte + 1 if corte >= 0 else q
    return inicio, fin


def base_de_linea(texto, encabezado, base_nota):
    if not CODIGO:
        return None
    marcados = [p["alias"] for p in CODIGO if p["marca"].search(texto)]
    if len(marcados) > 1:
        return None
    if marcados:
        return marcados[0]
    otros = [p["alias"] for p in CODIGO[1:] if p["marca"].search(encabezado)]
    if len(otros) == 1 and not CODIGO[0]["marca"].search(encabezado):
        return otros[0]
    return base_nota


def base_de_nota(cerebro, nodo, descripcion):
    proyecto = cerebro.proyecto_de.get(nodo["id"])
    for p in CODIGO[1:]:
        if proyecto == nucleo.normalizar(p["raiz"]) or p["marca"].search(f'{nodo["titulo"]} {descripcion}'):
            return p["alias"]
    return CODIGO[0]["alias"] if CODIGO else None


def corto(ruta):
    for i, p in enumerate(CODIGO):
        raiz = p["raiz"]
        if nucleo.normalizar(ruta).startswith(f"{nucleo.normalizar(raiz)}\\"):
            return ("" if i == 0 else p["alias"] + ": ") + ruta[len(raiz) + 1:]
    return ruta


def palabras_de_carpeta(texto):
    salida = []
    for palabra in reversed(texto.split()[-PALABRAS_DE_CARPETA:]):
        limpia = RE_ANTES_DE_CARPETA.sub("", palabra)
        if limpia:
            salida.insert(0, limpia)
        if limpia != palabra:
            break
    return salida


def anclas_de_nodo(nodo):
    cuerpo = nodo["_cuerpo"]
    lineas = {}
    for m in RE_ANCLA.finditer(cuerpo):
        k = m.start()
        while k > 0 and cuerpo[k - 1] in CARACTERES_RUTA:
            k -= 1
        token = cuerpo[k:m.start()]
        corte = max(token.rfind("\\"), token.rfind("/"))
        nombre = token[corte + 1:]
        if not RE_NOMBRE_CS.match(nombre):
            continue
        a = cuerpo.rfind("\n", 0, k) + 1
        desde = int(m.group(2))
        hasta = int(m.group(3)) if m.group(3) else desde
        antes = palabras_de_carpeta(cuerpo[a:k]) if corte >= 0 and k > a and cuerpo[k - 1] == " " else []
        lineas.setdefault(a, []).append({"inicio": k, "fin": m.end(), "carpeta": token[:corte + 1], "nombre": nombre,
                                         "ext": m.group(1).lower(), "desde": desde, "hasta": max(desde, hasta),
                                         "cita": cuerpo[k:m.end()], "extras": [int(x) for x in m.group(4).split(",") if x],
                                         "antes": antes})
    for a, grupo in lineas.items():
        b = cuerpo.find("\n", a)
        b = len(cuerpo) if b < 0 else b
        for s in RE_ANCLA_SUELTA.finditer(cuerpo, a, b):
            previas = [x for x in grupo if x["fin"] <= s.start()]
            if not previas:
                continue
            base = max(previas, key=lambda x: x["fin"])
            desde = int(s.group(1))
            hasta = int(s.group(2)) if s.group(2) else desde
            grupo.append(dict(base, inicio=s.start(), fin=s.end(), desde=desde, hasta=max(desde, hasta), extras=[], suelta=True,
                              cita=f'{base["nombre"]}.{base["ext"]}{s.group(0).strip("`")}'))
    return lineas


def clausulas(cuerpo, inicio, fin):
    tildes = [(m.start(), m.end()) for m in RE_BACKTICK.finditer(cuerpo, inicio, fin)]
    cortes = [m.start() for m in RE_CORTE_DE_CLAUSULA.finditer(cuerpo, inicio, fin)
              if not any(a < m.start() < b for a, b in tildes)]

    def clausula(posicion, ancla=None):
        k = bisect.bisect_right(cortes, posicion)
        if ancla is not None and k > 0:
            hasta = cortes[k] if k < len(cortes) else fin
            resto = cuerpo[cortes[k - 1] + 1:ancla["inicio"]] + cuerpo[ancla["fin"]:hasta]
            if not re.search(r"\w", resto):
                k -= 1
        return k
    return clausula


def agrupar_opciones(opciones, separacion):
    grupos = []
    for opcion in sorted(opciones, key=lambda o: o[1]):
        if grupos and opcion[1] - grupos[-1][-1][1] <= separacion:
            grupos[-1].append(opcion)
        else:
            grupos.append([opcion])
    return sorted(grupos, key=lambda g: (-len(g), min(g)))


def ancla_del_identificador(grupo, c_inicio, c_fin, clausula):
    propia = clausula(c_inicio)
    candidatas = [x for x in grupo if clausula(x["inicio"], x) == propia]
    if any(x["fin"] <= c_inicio for x in candidatas):
        candidatas = [x for x in candidatas if not (x.get("suelta") and x["inicio"] >= c_fin)]
    if not candidatas:
        return None
    return min(candidatas, key=lambda x: (x["inicio"] - c_fin if c_fin <= x["inicio"] else max(0, c_inicio - x["fin"]),
                                          x["inicio"]))


def mapear_linea(linea, hunks):
    desplazamiento = 0
    for a, b, c, d in hunks:
        viejo = a if b else a + 1
        nuevo = c if d else c + 1
        if linea < viejo:
            break
        if b and linea <= a + b - 1:
            return None
        desplazamiento = (nuevo + d) - (viejo + b)
    return linea + desplazamiento


def hunks_de_diff(salida):
    por_archivo = {}
    actual = None
    anterior = ""
    for renglon in salida.split("\n"):
        if renglon.startswith("+++ ") and anterior.startswith("--- "):
            actual = renglon[6:].rstrip("\t") if renglon.startswith("+++ b/") else None
            if actual is not None:
                por_archivo[actual] = None if anterior == "--- /dev/null" else []
        elif actual is not None and por_archivo[actual] is not None and renglon.startswith("@@"):
            m = RE_HUNK.match(renglon)
            if m:
                por_archivo[actual].append([int(g) if g is not None else 1 for g in m.groups()])
        anterior = renglon
    return por_archivo


def commits_por_archivo(repo, relativas):
    salida = correr_git(repo, ["-c", "core.quotePath=false", "log", "--format=%x01%H %ct", "--name-only", "--"]
                        + [":(literal)" + r for r in sorted(relativas)], espera=30)
    por_archivo = {}
    actual = None
    for linea in (salida or "").split("\n"):
        if linea.startswith("\x01"):
            partes = linea[1:].split()
            actual = (partes[0], int(partes[1])) if len(partes) == 2 and partes[1].isdecimal() else None
        elif linea.strip() and actual:
            por_archivo.setdefault(linea.strip(), []).append(actual)
    return por_archivo


def anclas_movidas(candidatas, repos=None, cache=None):
    repos = repos_conocidos() if repos is None else list(repos)
    if not candidatas or not repos:
        return []
    ruta_cache = CACHE_ANCLAS if cache is None else Path(cache)
    guardado = leer_objeto_json(ruta_cache)
    cabezas = {r: (correr_git(r, ["rev-parse", "HEAD"]) or "").strip() for r in repos}
    commits = guardado.get("commits") if isinstance(guardado.get("commits"), dict) else {}
    viejos = guardado.get("hunks") if guardado.get("cabezas") == cabezas and isinstance(guardado.get("hunks"), dict) else {}
    pedidos = {}
    for c in candidatas:
        pedidos.setdefault(c["_nota_ruta"], []).append(c["linea"])
    fechas = fechas_de_renglones(pedidos, repos)
    usados_commits, grupos, asignadas, por_repo = {}, {}, [], {}
    for c in candidatas:
        cuando = fechas.get((c["_nota_ruta"], c["linea"]))
        repo = repo_de(c["archivo"], repos)
        if not cuando or not repo or not cabezas.get(repo):
            continue
        llave = f"{repo}|{int(cuando // 3600)}"
        if llave not in commits:
            commits[llave] = (correr_git(repo, ["rev-list", "-1", f"--before={int(cuando)}", "HEAD"]) or "").strip()
        usados_commits[llave] = commits[llave]
        if commits[llave] and commits[llave] != cabezas[repo]:
            relativa = os.path.relpath(c["archivo"], repo).replace("\\", "/")
            asignadas.append([c, repo, relativa, cuando, commits[llave], None])
            por_repo.setdefault(repo, set()).add(relativa)
    historias = {repo: commits_por_archivo(repo, relativas) for repo, relativas in por_repo.items()}
    for asignada in asignadas:
        _, repo, relativa, cuando, _, _ = asignada
        cerca = [sha for sha, t in historias[repo].get(relativa, ()) if cuando < t <= cuando + VENTANA_TRABAJO]
        asignada[5] = cerca[0] if cerca else None
        for commit in filter(None, asignada[4:6]):
            if commit != cabezas[repo]:
                grupos.setdefault((repo, commit), set()).add(relativa)
    hunks = {}
    for (repo, commit), relativas in grupos.items():
        faltan = sorted(r for r in relativas if f"{repo}|{commit}|{r}" not in viejos)
        hunks.update({f"{repo}|{commit}|{r}": viejos[f"{repo}|{commit}|{r}"] for r in relativas if r not in faltan})
        for i in range(0, len(faltan), TANDA_DIFF):
            tanda = faltan[i:i + TANDA_DIFF]
            salida = correr_git(repo, ["-c", "core.quotePath=false", "diff", "-U0", "-M", commit, cabezas[repo], "--"]
                                + [":(literal)" + r for r in tanda], espera=60)
            if salida is not None:
                hallados = hunks_de_diff(salida)
                hunks.update({f"{repo}|{commit}|{r}": hallados.get(r, []) for r in tanda})
    try:
        permisos.crear(ruta_cache.parent)
        escribir_atomico(ruta_cache, json.dumps({"cabezas": cabezas, "commits": usados_commits, "hunks": hunks},
                                                separators=(",", ":")))
    except OSError:
        pass
    salida = []
    for c, repo, relativa, _, antes, despues in asignadas:
        nuevas = []
        for commit in (antes, despues):
            if commit is None:
                continue
            if commit == cabezas[repo]:
                nuevas.append(c["desde"])
                continue
            lista = hunks.get(f"{repo}|{commit}|{relativa}")
            nuevas.append(None if lista is None else mapear_linea(c["desde"], lista))
        if nuevas and None not in nuevas and max(nuevas) - min(nuevas) <= TOLERANCIA_MOVIDA \
                and abs(nuevas[0] - c["desde"]) >= MOVIDA_MINIMA:
            salida.append((c, nuevas[0]))
    return salida


def archivos_del_ancla(codigo, base, ancla, texto, ruta_nota, remite=None):
    remite = REMITE if remite is None else remite
    for proyecto in (base, remite.get(base)):
        if proyecto:
            lista = codigo.resolver(proyecto, ancla["carpeta"], ancla["nombre"], ancla["ext"], texto, ruta_nota,
                                    ancla.get("antes", ()))
            if lista:
                return lista
    return []


def revisar_anclas(cerebro, codigo=None):
    codigo = codigo or Codigo()
    cuentas = {"citadas": 0, "revisadas": 0, "conNombre": 0, "ambiguas": 0, "sinArchivo": 0, "otroProyecto": 0}
    marcadas = []
    sin_nombre = []
    vistas = set()
    for nodo in cerebro.nodos:
        if es_historica(nodo) or not RE_ANCLA.search(nodo["_cuerpo"]):
            continue
        cuerpo = nodo["_cuerpo"]
        resumida = nodo["grupo"] in GRUPOS_ANCLAS_RESUMIDAS
        descripcion = nucleo.dato(nodo.get("_frontmatter") or {}, "description") or ""
        base_nota = base_de_nota(cerebro, nodo, descripcion)
        for a, grupo in sorted(anclas_de_nodo(nodo).items()):
            b = cuerpo.find("\n", a)
            b = len(cuerpo) if b < 0 else b
            inicio, fin = contexto_de(cuerpo, a, b)
            texto = cuerpo[inicio:fin]
            h = cuerpo.rfind("\n#", 0, a)
            encabezado = cuerpo[h + 1:cuerpo.find("\n", h + 1)] if h >= 0 else ""
            base = base_de_linea(texto, encabezado, base_nota)
            cuentas["citadas"] += len(grupo)
            if base is None:
                cuentas["otroProyecto"] += len(grupo)
                continue
            propios = identificadores_propios(cuerpo, inicio, fin, grupo)
            for ancla in grupo:
                lista = archivos_del_ancla(codigo, base, ancla, texto, nodo["ruta"])
                if not lista:
                    cuentas["sinArchivo"] += 1
                    continue
                if len(lista) > 1:
                    cuentas["ambiguas"] += 1
                    continue
                ruta = lista[0]
                llave = (nodo["id"], nucleo.normalizar(ruta), ancla["desde"], ancla["hasta"])
                if llave in vistas:
                    continue
                vistas.add(llave)
                datos = codigo.archivo(ruta)
                if datos is None:
                    cuentas["sinArchivo"] += 1
                    continue
                cuentas["revisadas"] += 1
                buscados = propios[id(ancla)]
                if buscados:
                    cuentas["conNombre"] += 1
                estado, propuesta, por, competidores = estado_del_ancla(codigo, datos, ancla, buscados, resumida)
                registro = {
                    "nota": nodo["id"], "linea": linea_en(nodo, ancla["inicio"]), "cita": ancla["cita"],
                    "archivo": ruta, "desde": ancla["desde"], "hasta": ancla["hasta"], "largo": datos["total"],
                    "estado": estado, "por": por, "propuesta": propuesta, "competidores": competidores,
                    "buscados": [c for c, _ in buscados], "base": base, "_nota_ruta": nodo["ruta"],
                    "_resumida": resumida,
                }
                if estado is not None:
                    marcadas.append(registro)
                elif not buscados:
                    sin_nombre.append(registro)
    for registro, nueva in anclas_movidas(sin_nombre):
        registro.update(estado="movida", propuesta=nueva)
        marcadas.append(registro)
    return marcadas, cuentas


def identificadores_propios(cuerpo, inicio, fin, grupo):
    clausula = clausulas(cuerpo, inicio, fin)
    propios = {id(x): [] for x in grupo}
    for c_inicio, c_fin, crudo, busqueda in buscables(cuerpo, inicio, fin):
        if any(x["inicio"] <= c_inicio < x["fin"] for x in grupo):
            continue
        if busqueda[0] == "palabra" and len(busqueda[1]) < MINIMO_PALABRA_SUELTA and not RE_PARECE_CODIGO.search(crudo) \
                and not crudo.startswith("["):
            continue
        cercana = ancla_del_identificador(grupo, c_inicio, c_fin, clausula)
        if cercana is not None and busqueda[1].lower() != cercana["nombre"].lower():
            propios[id(cercana)].append((crudo, busqueda))
    return propios


def estado_del_ancla(codigo, datos, ancla, buscados, resumida):
    ventanas = [(ancla["desde"], ancla["hasta"])] + [(e, e) for e in ancla["extras"]]
    estado, propuesta, por, competidores = None, None, None, []
    if buscados and not any(codigo.aparece(datos, bq, d - VENTANA_ANCLA, h + VENTANA_ANCLA)
                            for _, bq in buscados for d, h in ventanas):
        envuelven = [any(codigo.declarada_arriba(datos, bq, d) for d, _ in ventanas) for _, bq in buscados]
        especificos = [(crudo, bq) for (crudo, bq), envuelve in zip(buscados, envuelven) if not envuelve]
        hallados = []
        if any(codigo.en_metodo_citado(datos, bq, d, h) for _, bq in especificos for d, h in ventanas):
            bien = True
        elif resumida:
            bien = any(envuelven)
        else:
            hallados = [(crudo, bq, codigo.ubicaciones(datos, bq)) for crudo, bq in especificos]
            hallados = [x for x in hallados if x[2]]
            bien = any(envuelven) and not hallados
        opciones = []
        if resumida and not bien:
            estado = "corrida"
        elif not bien:
            for crudo, _, encontradas in hallados:
                mejor = min(encontradas, key=lambda n: abs(n - ancla["desde"]))
                opciones.append((abs(mejor - ancla["desde"]), mejor, crudo))
        if opciones:
            estado = "corrida"
            grupos = agrupar_opciones(opciones, 2 * VENTANA_ANCLA + ancla["hasta"] - ancla["desde"])
            if len(grupos) > 1 and len(grupos[0]) == len(grupos[1]):
                competidores = [{"por": c, "linea": m} for _, m, c in sorted(opciones, key=lambda o: o[1])]
            else:
                _, propuesta, por = min(grupos[0])
    if estado is None and max([ancla["hasta"]] + ancla["extras"]) > datos["total"]:
        estado = "fuera"
    return estado, propuesta, por, competidores


def culpa_de_lineas(repo, nota, lineas):
    argumentos = ["blame", "--line-porcelain"]
    for n in sorted(lineas):
        argumentos += ["-L", f"{n},{n}"]
    salida = correr_git(repo, argumentos + ["--", os.path.relpath(nota, repo)])
    if salida is None:
        return {}
    resultado = {}
    actual = None
    for linea in salida.split("\n"):
        if linea.startswith("\t"):
            if actual:
                resultado[actual[1]] = (actual[0], actual[2])
            actual = None
            continue
        partes = linea.split(" ")
        if actual is None and len(partes) >= 3 and re.fullmatch(r"[0-9a-f]{40}", partes[0]):
            actual = [partes[0], int(partes[2]), None]
        elif actual is not None and partes[0] == "committer-time" and len(partes) > 1 and partes[1].isdecimal():
            actual[2] = int(partes[1])
    return resultado


def historia_anclas(marcadas, repos=None):
    repos = repos_conocidos() if repos is None else repos
    por_nota = {}
    for ancla in marcadas:
        repo = repo_de(ancla["_nota_ruta"], repos)
        if repo:
            por_nota.setdefault((repo, ancla["_nota_ruta"]), set()).add(ancla["linea"])
    claves = sorted(por_nota)
    pedidos = {}
    for ancla in marcadas:
        repo = repo_de(ancla["archivo"], repos)
        if repo and repo_de(ancla["_nota_ruta"], repos):
            ancla["_repo"] = repo
            pedidos.setdefault(repo, set()).add(os.path.relpath(ancla["archivo"], repo).replace("\\", "/"))
    repos_log = sorted(pedidos)

    def log(repo):
        salida = correr_git(repo, ["log", "--format=%x01%h %ct", "--name-only", "--"]
                            + [":(literal)" + a for a in sorted(pedidos[repo])])
        if salida is None:
            return None
        cambios = {}
        actual = None
        for linea in salida.split("\n"):
            if linea.startswith("\x01"):
                partes = linea[1:].split()
                actual = (partes[0], int(partes[1])) if len(partes) == 2 and partes[1].isdecimal() else None
            elif linea.strip() and actual:
                cambios.setdefault(linea.strip().lower(), []).append(actual)
        return cambios

    tareas = [lambda c=c: culpa_de_lineas(c[0], c[1], por_nota[c]) for c in claves] + [lambda r=r: log(r) for r in repos_log]
    resultados = en_paralelo(tareas)
    culpas = resultados[:len(claves)]
    registros = dict(zip(repos_log, resultados[len(claves):]))
    fecha_de = {}
    for (repo, nota), culpa in zip(claves, culpas):
        for linea, (sha, tiempo) in (culpa or {}).items():
            if sha != SHA_VACIO and tiempo:
                fecha_de[(nucleo.normalizar(nota), linea)] = (sha[:7], tiempo)
    for ancla in marcadas:
        fecha = fecha_de.get((nucleo.normalizar(ancla["_nota_ruta"]), ancla["linea"]))
        repo = ancla.pop("_repo", None)
        if not fecha or registros.get(repo) is None:
            continue
        relativa = os.path.relpath(ancla["archivo"], repo).replace("\\", "/").lower()
        despues = sorted((t, h) for h, t in registros[repo].get(relativa, ()) if t > fecha[1])
        ancla["renglon"] = {"commit": fecha[0], "fecha": fecha_y_hora(fecha[1])}
        ancla["cambiosDespues"] = [{"commit": h, "fecha": fecha_y_hora(t)} for t, h in despues]
        ancla["_texto_historia"] = texto_historia(ancla, fecha, despues)
    return marcadas


def texto_historia(ancla, fecha, despues):
    nombre = Path(ancla["archivo"]).name
    cabeza = f" El renglón de la nota es del {dia(fecha[1])} ({fecha[0]})"
    if not despues:
        return (f"{cabeza} y {nombre} no tiene commits posteriores: el número pudo estar mal desde el principio "
                "o el cambio todavía no está commiteado.")
    nombrados = [f"{h} ({dia(t)})" for t, h in despues[:3]]
    resto = len(despues) - len(nombrados)
    if resto:
        nombrados.append(cantidad(resto, "commit más", "commits más"))
    return f"{cabeza}; después {nombre} cambió en {lista_humana(nombrados)}."


def rango(desde, hasta):
    return str(desde) if hasta == desde else f"{desde}-{hasta}"


def regla_anclas(cerebro):
    todas, cuentas = revisar_anclas(cerebro)
    marcadas = [a for a in todas if not a["_resumida"]]
    resumidas = {}
    for a in todas:
        if a["_resumida"]:
            resumidas[a["nota"]] = resumidas.get(a["nota"], 0) + 1
    historia_anclas(marcadas)
    salida = []
    for nota, veces in sorted(resumidas.items()):
        salida.append(hallazgo("anclas", nota, None, "info",
                               cantidad(veces, "ancla archivo:línea ya no coincide", "anclas archivo:línea ya no coinciden")
                               + " con el código. Es de la auditoría: registra cómo estaba el código cuando se escribió, "
                               "así que no se detallan.",
                               "Si se va a usar una de esas líneas, buscar el lugar por nombre antes de abrirla."))
    for ancla in marcadas:
        nombre = Path(ancla["archivo"]).name
        donde = corto(ancla["archivo"])
        largo = ancla["hasta"] - ancla["desde"]
        propuesta = rango(ancla["propuesta"], ancla["propuesta"] + largo) if ancla["propuesta"] else None
        if ancla["estado"] == "corrida" and ancla["competidores"]:
            lugares = [f'{citar(c["por"], LARGO_CITA)} en la {c["linea"]}' for c in ancla["competidores"]]
            texto = (f'Cita {ancla["cita"]}, pero ningún nombre de la cita aparece cerca ni en el bloque que la contiene: '
                     f"en {donde} están lejos entre sí ({lista_humana(lugares)}), así que no propongo un número.")
            if ancla["hasta"] > ancla["largo"]:
                texto += f' Además el archivo tiene {ancla["largo"]} líneas.'
            arreglo = "Revisar a mano a qué apunta la cita; si se corrige, citar por nombre para que no se vuelva a correr."
        elif ancla["estado"] == "corrida":
            texto = (f'Cita {ancla["cita"]} por {citar(ancla["por"], LARGO_CITA)}, que ya no está cerca de esa línea: en {donde} '
                     f"está en la {propuesta}.")
            if ancla["hasta"] > ancla["largo"]:
                texto += f' Además el archivo tiene {ancla["largo"]} líneas.'
            arreglo = f"Revisar y poner {nombre}:{propuesta}, o citar por nombre para que no se vuelva a correr."
        elif ancla["estado"] == "movida":
            texto = (f'Cita {ancla["cita"]}, y desde que se escribió ese renglón el código de alrededor se movió: según '
                     f"git, esa línea de {donde} hoy está en la {propuesta}.")
            arreglo = f"Revisar y poner {nombre}:{propuesta}, o citar por nombre para que no se vuelva a correr."
        else:
            texto = f'Cita {ancla["cita"]}, pero {donde} tiene {ancla["largo"]} líneas.'
            arreglo = "Revisar a qué apuntaba y poner la línea actual, o citar por nombre."
        texto += ancla.pop("_texto_historia", "")
        ancla.pop("_nota_ruta", None)
        ancla.pop("_resumida", None)
        ancla["archivo"] = donde
        ancla["propuesta"] = propuesta
        salida.append(hallazgo("anclaCorrida", ancla["nota"], ancla["linea"], "revisar", texto, arreglo))
    cerebro.anclas = marcadas
    if cuentas["citadas"]:
        partes = [f'{cuentas["revisadas"]} comprobadas contra el código ({cuentas["conNombre"]} con un nombre para buscar)']
        if cuentas["ambiguas"]:
            partes.append(f'{cuentas["ambiguas"]} salteadas porque hay varios archivos con ese nombre')
        if cuentas["sinArchivo"]:
            partes.append(f'{cuentas["sinArchivo"]} sin un archivo de código con ese nombre')
        arreglo = ""
        if cuentas["otroProyecto"] and not CODIGO:
            partes.append(f'{cuentas["otroProyecto"]} salteadas porque ningún proyecto de config.json dice dónde está su código')
            arreglo = "Para que las compare con el código, sumá sus carpetas en «codigo» de cada proyecto, en config.json."
        elif cuentas["otroProyecto"]:
            nombres = [p["alias"] for p in CODIGO]
            por = f'habla del {" y del ".join(nombres)}' if len(nombres) == 2 else "nombra más de un proyecto"
            partes.append(f'{cuentas["otroProyecto"]} salteadas porque el renglón {por}')
        salida.append(hallazgo("anclas", indice_principal(cerebro), None, "info",
                               f'Anclas archivo:línea: {cuentas["citadas"]} citadas fuera de los históricos; '
                               f'{", ".join(partes)}; {len(marcadas)} para revisar.', arreglo))
    return salida


class Huerfano(Exception):
    pass


def leer_hechos(ruta=HECHOS):
    if not os.path.exists(ruta):
        return [], None
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        return [], str(error)
    lista = datos.get("hechos") if isinstance(datos, dict) else datos
    if not isinstance(lista, list):
        return [], "no tiene una lista «hechos»"
    return [h for h in lista if isinstance(h, dict)], None


def nodo_de_nota(cerebro, nota):
    if not isinstance(nota, str) or not nota:
        return None
    clave = nucleo.normalizar(nota)
    if clave in cerebro.por_ruta:
        return cerebro.por_ruta[clave]
    if nota in cerebro.por_id:
        return nota
    nombre = nota.lower()
    candidatos = [n["id"] for n in cerebro.nodos if nombre in (Path(n["ruta"]).name.lower(), Path(n["ruta"]).stem.lower())]
    return candidatos[0] if len(candidatos) == 1 else None


def recorrer(como):
    carpeta = como.get("carpeta")
    if not isinstance(carpeta, str) or not os.path.isdir(carpeta):
        raise Huerfano(f"no existe la carpeta {carpeta}")
    extensiones = tuple(e.lower() for e in como.get("extensiones", ()))
    excluir = re.compile(como["excluir"], re.I) if como.get("excluir") else None
    excluir_carpetas = {c.lower() for c in como.get("excluir_carpetas", ())}
    for raiz, subcarpetas, archivos in os.walk(carpeta):
        if como.get("recursivo"):
            subcarpetas[:] = [s for s in subcarpetas if s.lower() not in excluir_carpetas]
        else:
            subcarpetas[:] = []
        for nombre in archivos:
            if extensiones and not nombre.lower().endswith(extensiones):
                continue
            ruta = os.path.join(raiz, nombre)
            relativa = os.path.relpath(ruta, carpeta)
            if excluir and excluir.search(relativa):
                continue
            yield relativa, ruta


def es_utf8(ruta):
    with open(ruta, "rb") as f:
        datos = f.read()
    if datos.isascii():
        return True
    try:
        datos.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def leer_codigo(archivo):
    try:
        with open(archivo, "rb") as f:
            return f.read()
    except (OSError, TypeError, ValueError):
        raise Huerfano(f"no existe {archivo}")


def contar(como):
    tipo = como.get("tipo")
    if tipo == "lineas":
        datos = leer_codigo(como.get("archivo"))
        return datos.count(b"\n") + (1 if datos and not datos.endswith(b"\n") else 0), None
    if tipo == "archivos":
        nombres = [r for r, _ in recorrer(como)]
        return len(nombres), nombres
    if tipo == "no_utf8":
        nombres = []
        for relativa, ruta in recorrer(como):
            try:
                if not es_utf8(ruta):
                    nombres.append(relativa)
            except OSError:
                continue
        return len(nombres), nombres
    if tipo == "carpetas":
        carpeta = como.get("carpeta")
        if not isinstance(carpeta, str) or not os.path.isdir(carpeta):
            raise Huerfano(f"no existe la carpeta {carpeta}")
        excluir = re.compile(como["excluir"], re.I) if como.get("excluir") else None
        con_archivo = como.get("con_archivo")
        nombres = [e.name for e in os.scandir(carpeta) if e.is_dir()
                   and not (excluir and excluir.search(e.name))
                   and not (con_archivo and not os.path.exists(os.path.join(e.path, con_archivo)))]
        return len(nombres), nombres
    if tipo == "cadenas_en_bloque":
        texto = leer_codigo(como.get("archivo")).decode("latin-1")
        desde = como.get("desde") or ""
        hasta = como.get("hasta") or ""
        i = texto.find(desde) if desde else -1
        if i < 0:
            raise Huerfano(f'{citar(desde, LARGO_CITA)} ya no aparece en {Path(como["archivo"]).name}')
        j = texto.find(hasta, i + len(desde)) if hasta else -1
        if j < 0:
            raise Huerfano(f"después de {citar(desde, LARGO_CITA)} no aparece {citar(hasta, LARGO_CITA)}")
        return len(RE_CADENA_CS.findall(texto, i + len(desde), j)), None
    raise Huerfano(f'el tipo {citar(tipo, LARGO_CITA)} no existe (valen: {", ".join(TIPOS_HECHO)})')


def nombres_en_bloque(texto, inicio):
    fin = texto.find("\n\n", inicio)
    fin = len(texto) if fin < 0 else fin
    salida = []
    for m in RE_BACKTICK.finditer(texto, inicio, fin):
        c = m.group(1).strip()
        if c.endswith(("\\", "/")) or ":" in c or not re.search(r"\.\w{2,5}$", c):
            continue
        salida.append(c.replace("/", "\\"))
    return salida


def numero_de(m):
    for grupo in m.groups() or (m.group(0),):
        if grupo:
            limpio = re.sub(r"[.,\s]", "", grupo)
            if limpio.isdecimal():
                return int(limpio)
    return None


def evaluar_hecho(cerebro, hecho, textos, cuentas):
    nota = hecho.get("nota")
    como = hecho.get("como_contar") if isinstance(hecho.get("como_contar"), dict) else {}
    que = hecho.get("que") or (f'{como.get("tipo")} de {como.get("archivo") or como.get("carpeta")}')
    base = {"notaTexto": nota, "que": que, "tipo": como.get("tipo"), "nota": None, "linea": None, "dice": None,
            "disco": None, "sobra": [], "falta": [], "estado": "ok", "motivo": ""}

    def huerfano(motivo, linea=None):
        return [dict(base, estado="huerfano", motivo=motivo, linea=linea)]

    identificador = nodo_de_nota(cerebro, nota)
    if identificador is None:
        return huerfano(f"la nota {citar(nota, LARGO_CITA)} no está en el cerebro")
    base["nota"] = identificador
    try:
        patron = re.compile(hecho.get("patron") or "", re.M)
    except re.error as error:
        return huerfano(f"el patrón no es una expresión regular válida ({error})")
    if not hecho.get("patron"):
        return huerfano("falta el patrón")
    ruta = cerebro.por_id[identificador]["ruta"]
    if ruta not in textos:
        try:
            with open(ruta, encoding="utf-8-sig", errors="replace") as f:
                textos[ruta] = f.read()
        except OSError:
            textos[ruta] = ""
    texto = textos[ruta]
    coincidencias = [m for m in patron.finditer(texto) if numero_de(m) is not None]
    if not coincidencias:
        return huerfano("la nota ya no dice eso: el patrón no aparece")
    try:
        llave = json.dumps(como, sort_keys=True)
        if llave not in cuentas:
            try:
                cuentas[llave] = contar(como)
            except (Huerfano, OSError, re.error) as error:
                cuentas[llave] = error
        if isinstance(cuentas[llave], Exception):
            raise cuentas[llave]
        disco, nombres = cuentas[llave]
    except Huerfano as error:
        return huerfano(str(error), texto.count("\n", 0, coincidencias[0].start()) + 1)
    except (OSError, re.error) as error:
        return huerfano(f"{type(error).__name__}: {error}", texto.count("\n", 0, coincidencias[0].start()) + 1)
    suma = hecho.get("suma") if isinstance(hecho.get("suma"), int) else 0
    salida = []
    for m in coincidencias:
        registro = dict(base, linea=texto.count("\n", 0, m.start()) + 1, dice=numero_de(m) + suma, disco=disco)
        if hecho.get("lista") and nombres is not None:
            en_nota = {n.lower(): n for n in nombres_en_bloque(texto, m.start())}
            en_disco = {n.lower(): n for n in nombres}
            registro["sobra"] = sorted(en_nota[k] for k in set(en_nota) - set(en_disco))
            registro["falta"] = sorted(en_disco[k] for k in set(en_disco) - set(en_nota))
        if registro["dice"] != disco or registro["sobra"] or registro["falta"]:
            registro["estado"] = "distinto"
        salida.append(registro)
    return salida


def lista_humana(nombres, tope=6):
    if len(nombres) > tope:
        return f'{", ".join(nombres[:tope])} y {len(nombres) - tope} más'
    if len(nombres) > 1:
        return f'{", ".join(nombres[:-1])} y {nombres[-1]}'
    return nombres[0]


def regla_hechos(cerebro, ruta=HECHOS):
    hechos, error = leer_hechos(ruta)
    salida = []
    if error:
        cerebro.hechos = []
        return [hallazgo("hechoHuerfano", indice_principal(cerebro), None, "revisar",
                         f"No pude leer {ruta}: {error}.", "Corregir el JSON de hechos.json.")]
    textos = {}
    cuentas = {}
    registros = []
    base = Path(ruta).parent
    for hecho in hechos:
        como = hecho.get("como_contar")
        if isinstance(como, dict):
            como = {k: nucleo.configuracion.resolver(v, base) if k in ("archivo", "carpeta") and isinstance(v, str) and v else v
                    for k, v in como.items()}
            hecho = dict(hecho, como_contar=como)
        registros += evaluar_hecho(cerebro, hecho, textos, cuentas)
    for r in registros:
        if r["estado"] == "ok":
            continue
        if r["estado"] == "huerfano":
            salida.append(hallazgo("hechoHuerfano", r["nota"] or indice_principal(cerebro), r["linea"], "revisar",
                                   f'Hecho huérfano ({r["que"]}): {r["motivo"]}.',
                                   f"Actualizar o sacar ese hecho de {ruta}."))
            continue
        if r["dice"] != r["disco"]:
            texto = f'Dice {r["dice"]} ({r["que"]}) y hoy son {r["disco"]}.'
        else:
            texto = f'El número coincide ({r["disco"]}, {r["que"]}), pero la lista no.'
        if r["sobra"]:
            texto += f' Nombra y ya no está: {lista_humana(r["sobra"])}.'
        if r["falta"]:
            texto += f' Falta: {lista_humana(r["falta"])}.'
        salida.append(hallazgo("hecho", r["nota"], r["linea"], "revisar", texto,
                               f"Revisar y actualizar la nota (lo decide {QUIEN}). "
                               "Si cambió el criterio, ajustar el hecho en hechos.json."))
    cerebro.hechos = [r for r in registros if r["estado"] != "ok"]
    return salida


def orden(cerebro, h):
    nodo = cerebro.por_id.get(h["nota"]) if h["nota"] else None
    grupo = PRIORIDAD_GRUPO.get(nodo["grupo"], 2) if nodo else 2
    return (TONOS.index(h["tono"]), grupo, h["regla"], nodo["id"] if nodo else "", h["linea"] or 0)


def renglon_actual(cerebro, h, leidos):
    nodo = cerebro.por_id.get(h["nota"]) if h["nota"] else None
    if not nodo:
        return None
    if not h["linea"]:
        return h["texto"]
    if nodo["ruta"] not in leidos:
        try:
            leidos[nodo["ruta"]] = Path(nodo["ruta"]).read_text(encoding="utf-8", errors="replace").split("\n")
        except OSError:
            leidos[nodo["ruta"]] = []
    lineas = leidos[nodo["ruta"]]
    return lineas[h["linea"] - 1].strip() if 0 < h["linea"] <= len(lineas) else None


def clave_descarte(cerebro, h, leidos):
    renglon = renglon_actual(cerebro, h, leidos)
    if renglon is None or h["tono"] not in TONOS_DESCARTABLES:
        return None
    return (h["regla"], nucleo.normalizar(cerebro.por_id[h["nota"]]["ruta"]),
            hashlib.sha1(renglon.encode("utf-8")).hexdigest()[:16])


def cargar_descartados(ruta=None):
    lista = leer_objeto_json(ruta or DESCARTADOS).get("descartados")
    return [d for d in lista if isinstance(d, dict) and all(isinstance(d.get(k), str) for k in ("regla", "ruta", "huella"))] \
        if isinstance(lista, list) else []


def separar_descartados(cerebro, hallazgos, descartados=None):
    descartados = cargar_descartados() if descartados is None else descartados
    if not descartados:
        return hallazgos, []
    claves = {(d["regla"], nucleo.normalizar(d["ruta"]), d["huella"]) for d in descartados}
    leidos = {}
    vigentes, aparte = [], []
    for h in hallazgos:
        (aparte if clave_descarte(cerebro, h, leidos) in claves else vigentes).append(h)
    return vigentes, aparte


def revisar(cerebro, saltos=None, filtrar=True):
    if saltos is None:
        saltos = alcance(cerebro)
    rutas = Rutas(cerebro)
    en_fondo = {}

    def fondo(nombre, regla):
        def correr():
            try:
                en_fondo[nombre] = regla(cerebro)
            except Exception as error:
                en_fondo[nombre] = error
        hilo = threading.Thread(target=correr, daemon=True)
        hilo.start()
        return hilo

    hilos = [fondo("commits", regla_commits), fondo("hechos", regla_hechos), fondo("resuelto", regla_resuelto)]
    hallazgos = []
    hallazgos += regla_indice(cerebro)
    hallazgos += regla_frontmatter(cerebro)
    hallazgos += regla_rutas(cerebro, rutas)
    hallazgos += regla_tamano(cerebro)
    hallazgos += regla_cifras(cerebro)
    hallazgos += regla_probado(cerebro)
    hallazgos += regla_huerfanas(cerebro, saltos)
    hallazgos += regla_memorias_parecidas(cerebro)
    try:
        hallazgos += regla_repite_claude(cerebro)
    except Exception as error:
        hallazgos.append(hallazgo("repiteClaude", indice_principal(cerebro), None, "info",
                                  f"La revisión de lo que repite CLAUDE.md falló: {type(error).__name__}: {error}.", ""))
    try:
        hallazgos += regla_anclas(cerebro)
    except Exception as error:
        hallazgos.append(hallazgo("anclas", indice_principal(cerebro), None, "info",
                                  f"La revisión de anclas falló: {type(error).__name__}: {error}.", ""))
    for hilo in hilos:
        hilo.join()
    if isinstance(en_fondo.get("commits"), Exception):
        error = en_fondo["commits"]
        hallazgos.append(hallazgo("commitInexistente", indice_principal(cerebro), None, "info",
                                  f"La revisión de commits falló: {type(error).__name__}: {error}.", ""))
    else:
        hallazgos += en_fondo.get("commits") or []
    if isinstance(en_fondo.get("hechos"), Exception):
        error = en_fondo["hechos"]
        hallazgos.append(hallazgo("hechoHuerfano", indice_principal(cerebro), None, "info",
                                  f"La revisión de hechos.json falló: {type(error).__name__}: {error}.", ""))
    else:
        hallazgos += en_fondo.get("hechos") or []
    if isinstance(en_fondo.get("resuelto"), Exception):
        error = en_fondo["resuelto"]
        hallazgos.append(hallazgo("yaResuelto", indice_principal(cerebro), None, "info",
                                  f"La revisión de problemas ya resueltos falló: {type(error).__name__}: {error}.", ""))
    else:
        hallazgos += en_fondo.get("resuelto") or []
    hallazgos.sort(key=lambda h: orden(cerebro, h))
    if filtrar:
        hallazgos, cerebro.descartados = separar_descartados(cerebro, hallazgos)
    return hallazgos


ETIQUETA = {"peligro": "GRAVE  ", "aviso": "AVISO  ", "revisar": "REVISAR", "info": "INFO   "}
NOMBRE_DEL_TONO = {"peligro": ("grave", "graves"), "aviso": ("aviso", "avisos"), "revisar": ("para revisar", "para revisar"),
                   "info": ("dato", "datos")}
SIEMPRE_EN_CONSOLA = {"presupuestoIndice"}


def informe(cerebro, hallazgos, maximo=30, segundos=None, avisos_aparte=0):
    cuentas = {t: sum(1 for h in hallazgos if h["tono"] == t) for t in TONOS}
    cuentas["aviso"] += avisos_aparte
    cabeza = f"Médico de la memoria: {cantidad(len(cerebro.nodos), 'nota revisada', 'notas revisadas')}"
    if segundos is not None:
        cabeza += f" en {decimal(segundos)} s"
    cabeza += ". " + ", ".join(cantidad(cuentas[t], *NOMBRE_DEL_TONO[t]) for t in TONOS) + "."
    lineas = [cabeza]
    apartados = len(getattr(cerebro, "descartados", None) or ())
    pie = [f"Descartados a mano (no se muestran): {cantidad(apartados, 'aviso', 'avisos')}; "
           f"{configuracion.comando()} --descartados los lista."] if apartados else []
    if not cerebro.nodos:
        lineas.append(nucleo.donde_busque())
    if not hallazgos:
        if cerebro.nodos:
            lineas.append("En las notas no encontré nada." if avisos_aparte else "No encontré nada.")
        return lineas + pie
    if cuentas["revisar"]:
        pie.append(f"Si un «para revisar» ya está comprobado y la nota no necesita cambios: "
                   f"{configuracion.comando()} --descartar-aviso RUTA:LÍNEA (vuelve si el renglón cambia).")
    lugar = maximo - 1 if maximo else len(hallazgos)
    if len(hallazgos) <= lugar:
        mostrar = hallazgos
    else:
        fijos = [h for h in hallazgos if h["regla"] in SIEMPRE_EN_CONSOLA]
        resto = [h for h in hallazgos if h["regla"] not in SIEMPRE_EN_CONSOLA]
        elegidos = {id(h) for h in fijos + resto[:max(0, lugar - 1 - len(fijos))]}
        mostrar = [h for h in hallazgos if id(h) in elegidos]
    for h in mostrar:
        nodo = cerebro.por_id.get(h["nota"]) if h["nota"] else None
        donde = (nodo["ruta"] if nodo else "(general)") + (f':{h["linea"]}' if h["linea"] else "")
        texto = f'{ETIQUETA[h["tono"]]} {donde} — {h["texto"]}'
        if h["arreglo"]:
            texto += f' → {h["arreglo"]}'
        lineas.append(texto)
    if len(mostrar) < len(hallazgos):
        vistos = {id(h) for h in mostrar}
        afuera = {}
        for h in hallazgos:
            if id(h) not in vistos:
                afuera[h["regla"]] = afuera.get(h["regla"], 0) + 1
        detalle = ", ".join(f"{n} {regla}" for regla, n in sorted(afuera.items(), key=lambda x: (-x[1], x[0])))
        lineas.append(f"… y {len(hallazgos) - len(mostrar)} más: {detalle}. "
                      f"Para verlos todos acá: {configuracion.comando()} --salud --todo.")
    return lineas + pie


def lugar_pedido(texto):
    texto = texto.strip().strip("\"'")
    ruta, _, linea = texto.rpartition(":")
    if len(ruta) > 1 and linea.isdigit():
        return ruta, int(linea)
    return texto, None


def donde_esta(cerebro, h):
    return cerebro.por_id[h["nota"]]["ruta"] + (f':{h["linea"]}' if h["linea"] else "")


def guardar_descartados(lista, ruta=None):
    escribir_atomico(ruta or DESCARTADOS, json.dumps({"descartados": lista}, ensure_ascii=False, indent=1) + "\n")


def main_descartar_aviso(lugar, motivo=""):
    ruta, linea = lugar_pedido(lugar)
    cerebro = nucleo.desde_disco()
    clave = nucleo.normalizar(ruta)
    aca = [h for h in revisar(cerebro, filtrar=False) if h["nota"] in cerebro.por_id and h["linea"] == linea
           and nucleo.normalizar(cerebro.por_id[h["nota"]]["ruta"]) == clave]
    leidos = {}
    elegidos = [(h, c) for h in aca for c in [clave_descarte(cerebro, h, leidos)] if c]
    if not elegidos:
        print("Error: " + ("solo se descartan los «para revisar» (las sospechas del médico); los avisos y los graves son "
                           "problemas concretos y se arreglan en la nota (si una ruta falta a propósito, decilo en el "
                           "mismo renglón)." if aca else
                           f"el médico no marca nada en {lugar.strip()}. Copiá RUTA:LÍNEA tal como sale en "
                           f"{configuracion.comando()} --salud."))
        return 2
    lista = cargar_descartados()
    ya = {(d["regla"], nucleo.normalizar(d["ruta"]), d["huella"]) for d in lista}
    for h, c in elegidos:
        if c not in ya:
            lista.append({"regla": h["regla"], "ruta": cerebro.por_id[h["nota"]]["ruta"], "linea": h["linea"] or 0,
                          "huella": c[2], "motivo": motivo.strip()[:300], "fecha": time.strftime("%Y-%m-%d")})
        print(f'Descartado: {ETIQUETA[h["tono"]].strip()} {donde_esta(cerebro, h)} — {citar(h["texto"], 160)} '
              "Ya no sale en --salud, la página ni la pista; si ese renglón cambia, vuelve a revisarse.")
    guardar_descartados(lista)
    return 0


def main_descartados():
    lista = cargar_descartados()
    if not lista:
        print("No hay avisos del médico descartados a mano.")
        return 0
    cerebro = nucleo.desde_disco()
    leidos = {}
    vigentes = {clave_descarte(cerebro, h, leidos) for h in revisar(cerebro, filtrar=False)}
    print(f"Avisos del médico descartados a mano: {len(lista)}.")
    for d in lista:
        sigue = (d["regla"], nucleo.normalizar(d["ruta"]), d["huella"]) in vigentes
        estado = "callado" if sigue else "ya no aplica (el renglón cambió o el médico dejó de marcarlo)"
        motivo = f' · motivo: {citar(d["motivo"], 160)}' if d.get("motivo") else ""
        donde = d["ruta"] + (f':{d["linea"]}' if d.get("linea") else "")
        print(f'  {donde} · {d["regla"]} · {d.get("fecha", "")} · {estado}{motivo}')
    print(f"Para que uno vuelva a salir: {configuracion.comando()} --recuperar-aviso RUTA:LÍNEA.")
    return 0


def main_recuperar_aviso(lugar):
    ruta, linea = lugar_pedido(lugar)
    lista = cargar_descartados()
    clave = nucleo.normalizar(ruta)
    quedan = [d for d in lista if not (nucleo.normalizar(d["ruta"]) == clave and (d.get("linea") or None) == linea)]
    if len(quedan) == len(lista):
        print(f"Error: no hay ningún aviso descartado en {lugar.strip()} ({configuracion.comando()} --descartados los lista).")
        return 2
    guardar_descartados(quedan)
    print(f"Listo: {cantidad(len(lista) - len(quedan), 'aviso vuelve', 'avisos vuelven')} a salir en {lugar.strip()}.")
    return 0
