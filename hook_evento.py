import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archivos
import donde
import hooks_comun
import permisos
from registro import OPCIONES_CONSULTA

CARPETA = os.path.join(os.path.dirname(donde.config()[0]), "en-vivo")
REGISTRO = os.path.join(CARPETA, "eventos.jsonl")
CANDADO = os.path.join(CARPETA, "eventos.lock")
TOPE = 5 * 1024 * 1024
EDAD_ROTAR = 7 * 86400
RE_PRIMERO = re.compile(rb'\{"t":\s*(\d{9,11})')
ESPERA_CANDADO = 0.5
ESPERA_DE_FONDO = 2.0
COLA_REPETIDO = 4096
MAXIMO_RUTAS = 5
MOTIVOS_PISTA = ("p", "i", "a")
TOPE_RENGLON = 10 ** 7
LARGO_ANALIZADO = 20000
ESPACIOS_POR_CARPETA = 3
LARGO_RUTA_ARCHIVO = 1000

TIPOS = {
    "Read": "leer", "NotebookRead": "leer",
    "Grep": "buscar", "Glob": "buscar", "WebSearch": "buscar", "ToolSearch": "buscar",
    "Edit": "editar", "MultiEdit": "editar", "NotebookEdit": "editar",
    "Write": "crear",
    "Bash": "ejecutar", "PowerShell": "ejecutar",
    "Agent": "agente", "Task": "agente", "Workflow": "agente",
    "WebFetch": "web", "Skill": "otro",
}


COMANDOS = [
    ("commit", re.compile(r"\bgit\b[^|&;]*\bcommit\b")),
    ("compila", re.compile(r"msbuild|\bdotnet\s+(build|publish)|\bcsc(\.exe)?\b|\bcmake\s+--build|\bnpm\s+run\s+build"
                           r"|\bcl\.exe\b")),
    ("prueba", re.compile(r"\bdotnet\s+test\b|\bpytest\b|--check\b|\bnpm\s+test\b")),
    ("git", re.compile(r"\bgit\b")),
    ("base", re.compile(r"\b(?:mysql|psql|sqlite3|sqlcmd|mongosh?|redis-cli)(\.exe)?\b")),
    ("cerebro", re.compile(r"(?:^|[\s\"'/\\(])py(?:thon[\d.]*)?(?:\.exe)?[\"']?\s[^|&;\n]*\b(?:cerebro|neuromapa)\.py\b"
                           r"|(?:^|[\s\"'/\\(&])neuromapa(?:\.cmd)?[\"']?\s+(?:--|abrir\b)")),
]
RE_SALIDA = re.compile(r"(?:Error: )?Exit code (\d{1,10})\b")
EXTENSIONES_SCRIPT = (".ps1", ".sh", ".bat", ".cmd")

MOTIVOS = {"manual", "auto", "startup", "resume", "clear", "compact", "logout", "prompt_input_exit",
           "bypass_permissions_disabled", "other"}
RE_OPCION_CEREBRO = re.compile(r"\b(?:cerebro\.py|neuromapa(?:\.py|\.cmd)?)\b[\"']?([^|&;\n]*)")
RE_OPCION = re.compile(f'(?:^|\\s)--({"|".join(map(re.escape, OPCIONES_CONSULTA))})(?=[\\s=]|$)')
RE_RUTA_SALIDA = re.compile(r"((?:[A-Za-z]:[\\/]|~[\\/]|/(?!/))[^\t\r\n]*?\.md)(?::\d+(?:-\d+)?)?(?=\s|$)", re.I)
RE_PARECIDA = re.compile(r"^  \d+,\d+  (.+)$")
RE_BUSCADA = re.compile(r"^   (?=[A-Za-z]:[\\/]|~[\\/]|/(?!/))(.+)$")

LECTURA = {"cat", "head", "tail", "type", "get-content", "gc"}
BUSQUEDA = {"grep", "egrep", "fgrep", "rg", "select-string", "sls"}
ESCRITURA = {"tee", "tee-object", "set-content", "add-content", "out-file"}
CAMBIO_DE_CARPETA = {"cd", "pushd", "chdir", "set-location", "sl"}
ECO = {"echo", "printf", "print", "write-output", "write-host"}
RED = {"curl", "wget", "invoke-webrequest", "iwr", "invoke-restmethod", "irm", "ssh", "scp", "sftp", "ftp", "rsync", "nc",
       "ncat", "telnet", "http", "https", "xh", "aria2c", "start-bitstransfer"}
FAMILIAS = [
    ("lee", LECTURA | {"less", "more", "wc", "awk", "stat", "file", "xxd", "od", "hexdump", "sha256sum", "md5sum",
                       "get-filehash", "certutil"}),
    ("busca", BUSQUEDA | {"find", "findstr"}),
    ("lista", {"ls", "dir", "get-childitem", "gci", "tree", "du", "ll", "test-path"}),
    ("python", {"python", "python3", "py", "pip", "pip3", "pyflakes", "pylint", "mypy", "ruff"}),
    ("node", {"node", "npm", "npx", "pnpm", "yarn", "bun", "deno", "tsc"}),
    ("red", RED),
    ("archivos", ESCRITURA | {"cp", "mv", "rm", "mkdir", "rmdir", "touch", "ln", "copy", "move", "del", "erase", "ren",
                              "copy-item", "cpi", "move-item", "mi", "remove-item", "ri", "new-item", "ni", "rename-item",
                              "rni", "unzip", "zip", "tar", "7z", "expand-archive", "compress-archive", "robocopy",
                              "xcopy"}),
    ("sistema", {"ps", "tasklist", "taskkill", "kill", "stop-process", "get-process", "gps", "where", "which",
                 "get-command", "gcm", "chmod", "chown", "icacls", "whoami", "hostname", "uname", "systeminfo",
                 "get-ciminstance", "get-wmiobject", "netstat", "sleep", "start-sleep", "date", "get-date", "start-process",
                 "get-item", "gi", "get-itemproperty", "reg", "sc"}),
    ("script", {"bash", "sh", "zsh", "pwsh", "powershell", "cmd", "source"}),
]
ANTES_DEL_VERBO = {"sudo", "command", "builtin", "exec", "time", "nohup", "&", "!", "then", "do", "else", "(", "{"}
SEPARADORES = {"&&", "||", ";", "|", "\n"}
NULOS = {"/dev/null", "$null", "nul"}
FAMILIA = {"grep": "grep", "egrep": "grep", "fgrep": "grep", "rg": "rg", "select-string": "sls", "sls": "sls"}
OPCION_PATRON = {"grep": {"-e", "--regexp", "-f", "--file"}, "rg": {"-e", "--regexp", "-f", "--file"}, "sls": {"-pattern"}}
OPCION_RUTA = {"grep": set(), "rg": set(), "sls": {"-path", "-literalpath"}}
OPCION_CON_VALOR = {
    "grep": {"-A", "-B", "-C", "-m", "-d", "-D", "--max-count", "--context", "--after-context", "--before-context",
             "--include", "--exclude", "--exclude-dir", "--exclude-from", "--directories", "--devices", "--label"},
    "rg": {"-A", "-B", "-C", "-m", "-g", "-t", "-T", "-j", "-M", "-r", "-E", "--glob", "--iglob", "--type", "--type-not",
           "--max-count", "--replace", "--encoding", "--context", "--after-context", "--before-context", "--threads",
           "--max-columns", "--max-depth", "--sort", "--sortr", "--colors", "--pre", "--pre-glob", "--type-add",
           "--path-separator", "--max-filesize", "--engine", "--ignore-file"},
    "sls": {"-encoding", "-context", "-exclude", "-include", "-culture", "-inputobject"},
}

RE_PIEZA = re.compile(r'"(?:[^"\\]|\\.)*"?|\'[^\']*\'?|&&|\|\||[;|\n]|[^"\'&|;\n]+|&')
RE_PALABRA = re.compile(r"[^\s\"'`|;&<>(){}=,*?$]+")
RE_FIN_MD = re.compile(r"\.md(?![\w.\-])", re.I)
RE_CAMINO = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/~.])")
RE_ARCHIVO = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/]|~[\\/]|\.{1,2}[\\/])")
RE_HOST = re.compile(r"^[\w\-]+(?:\.[\w\-]+)*\.[A-Za-z]{2,24}(?::\d+)?[/?#]")
RE_RED = re.compile(r"^(?:\d{1,3}(?:\.\d{1,3}){3}|\[[0-9a-f:.]*\]|localhost)(?::\d+)?(?:[/\\?#]|$)", re.I)
RE_CARPETAS = re.compile(r"[\\/]+")
RE_REDIRIGE = re.compile(r"(\d|\*)?>>?\s*(&?)\s*([^\s;&|]*)")
RE_ASIGNACION = re.compile(r"^[A-Za-z_]\w*=")
RE_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1([^\n]*)\n.*?(?:^\s*\2\s*$|\Z)", re.S | re.M)
RE_HERE_STRING = re.compile(r"@(['\"])\r?\n.*?(?:\r?\n\1@|\Z)", re.S)
RE_UNIDAD_BASH = re.compile(r"^/([A-Za-z])(?=/|$)")
RE_NOMBRE = hooks_comun.RE_NOMBRE
RE_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
RE_HERRAMIENTA = re.compile(r"[\w.:\-]{1,120}\Z")
RE_SESION = re.compile(r"[0-9A-Za-z\-]{1,8}\Z")
ANTES_DE_UNA_RUTA = "$*?}=%"


def clase_comando(comando):
    comando = str(comando or "")[:LARGO_ANALIZADO]
    minusculas = comando.lower()
    for nombre, patron in COMANDOS:
        if patron.search(minusculas):
            return nombre
    return familia_de(*primer_programa(comando))


def primer_programa(comando):
    for _, libre in segmentos(sin_textos_largos(comando)):
        verbo, resto = verbo_y_resto(libre)
        if verbo and verbo not in CAMBIO_DE_CARPETA:
            return verbo, resto
    return "", []


def familia_de(verbo, resto):
    if verbo == "sed":
        return "lee" if es_sed_lectura(resto) else "archivos"
    if verbo.endswith(EXTENSIONES_SCRIPT):
        return "script"
    return next((nombre for nombre, verbos in FAMILIAS if verbo in verbos), "otro")


def lineas(texto):
    texto = str(texto or "")
    return texto.count("\n") + (1 if texto and not texto.endswith("\n") else 0)


def corto(valor, largo=100):
    valor = str(valor or "")
    return valor if len(valor) <= largo else f"{valor[: largo - 1]}…"


def ruta_guardable(valor):
    if not isinstance(valor, str) or "://" in valor or valor.strip().lower().startswith(("data:", "mailto:", "javascript:")):
        return ""
    return "" if RE_CONTROL.search(valor) else valor


def ruta_de_archivo(valor):
    valor = ruta_guardable(valor)
    if not valor or len(valor) > LARGO_RUTA_ARCHIVO or not RE_ARCHIVO.match(valor) or valor.find(":", 2) >= 0:
        return ""
    partes = [p for p in RE_CARPETAS.split(valor) if p]
    return valor if all(p == p.strip() and p.count(" ") <= ESPACIOS_POR_CARPETA for p in partes) else ""


def de_red(ruta):
    return ruta.replace("/", "\\").startswith("\\\\")


nombre_seguro = hooks_comun.nombre_seguro


def host_de(url):
    import urllib.parse
    try:
        host = urllib.parse.urlsplit(str(url or "")).hostname or ""
    except ValueError:
        return ""
    return host if RE_NOMBRE.match(host) else ""


def segmentos(comando):
    lista, piezas, libre = [], [], []
    for m in RE_PIEZA.finditer(comando):
        pieza = m.group()
        if pieza in SEPARADORES:
            lista.append((piezas, "".join(libre)))
            piezas, libre = [], []
            continue
        piezas.append(pieza)
        libre.append(" " if pieza[0] in "\"'" else pieza)
    lista.append((piezas, "".join(libre)))
    return lista


def palabras_de(piezas):
    salida = []
    for pieza in piezas:
        if pieza[0] in "\"'":
            salida.append(pieza)
        else:
            salida.extend(pieza.split())
    return salida


def argumentos(palabras):
    i = 0
    while i < len(palabras) and (palabras[i] in ANTES_DEL_VERBO or RE_ASIGNACION.match(palabras[i])):
        i += 1
    return palabras[i + 1:]


def sin_patron(palabras, verbo):
    familia = FAMILIA[verbo]
    patron, ruta, con_valor = OPCION_PATRON[familia], OPCION_RUTA[familia], OPCION_CON_VALOR[familia]
    salida = []
    patron_dado = saltar = es_ruta = solo_posicionales = False
    for palabra in palabras:
        if saltar:
            saltar = False
            continue
        if es_ruta:
            salida.append(palabra)
            es_ruta = False
            continue
        crudo = sin_comillas(palabra)
        if not solo_posicionales and crudo == "--":
            solo_posicionales = True
            continue
        if not solo_posicionales and len(crudo) > 1 and crudo[0] == "-":
            nombre, igual, _ = crudo.partition("=")
            if familia == "sls":
                nombre = nombre.lower()
            if nombre in patron:
                patron_dado = True
                saltar = not igual
            elif nombre in ruta:
                es_ruta = not igual
            elif nombre in con_valor:
                saltar = not igual
            continue
        if not patron_dado:
            patron_dado = True
            continue
        salida.append(palabra)
    return salida


def parece_ruta(texto):
    if len(texto) > 400 or "\n" in texto or not RE_CAMINO.match(texto) or not texto.lower().endswith(".md"):
        return False
    if "://" in texto or texto.find(":", 2) >= 0:
        return False
    return all(parte == parte.strip() and parte.count(" ") <= ESPACIOS_POR_CARPETA for parte in RE_CARPETAS.split(texto))


def candidatas(palabras, entera=False, adentro=False):
    for palabra in palabras:
        if ".md" not in palabra.lower():
            continue
        if palabra[0] in "\"'":
            dentro = palabra[1:-1] if len(palabra) > 1 and palabra[-1] == palabra[0] else palabra[1:]
            if entera and not adentro and parece_ruta(dentro):
                yield dentro
                continue
            if "://" in dentro:
                continue
            if not adentro:
                yield from candidatas(palabras_de([m.group() for m in RE_PIEZA.finditer(dentro)]), False, True)
                continue
            palabra = dentro
        yield from de_palabra(palabra)


def de_palabra(texto):
    for suelta in texto.split():
        suelta = suelta.strip("\"'")
        if "://" in suelta or RE_HOST.match(suelta) or RE_RED.match(suelta):
            continue
        for m in RE_PALABRA.finditer(suelta):
            if m.start() and suelta[m.start() - 1] in ANTES_DE_UNA_RUTA:
                continue
            fin = 0
            for f in RE_FIN_MD.finditer(m.group()):
                fin = f.end()
            palabra = m.group()[:fin]
            if 4 <= len(palabra) <= 400 and palabra[-4] not in "/\\":
                yield palabra


def sin_comillas(palabra):
    return palabra.strip("\"'")


def sin_textos_largos(comando):
    comando = RE_HEREDOC.sub(lambda m: f"<<{m.group(2)}{m.group(3)}\n", comando)
    return RE_HERE_STRING.sub("''", comando)


def sin_textos(palabras):
    return [p for p in palabras if p[0] not in "\"'" or parece_ruta(sin_comillas(p))]


def destinos(libre):
    return [m.group(3) for m in RE_REDIRIGE.finditer(libre) if m.group(1) != "2" and not m.group(2) and m.group(3)]


def verbo_y_resto(texto):
    palabras = texto.split()
    i = 0
    while i < len(palabras) and (palabras[i] in ANTES_DEL_VERBO or RE_ASIGNACION.match(palabras[i])):
        i += 1
    if i >= len(palabras):
        return "", []
    verbo = sin_comillas(palabras[i].lstrip("({!")).replace("\\", "/").rsplit("/", 1)[-1].lower()
    if verbo.endswith(".exe"):
        verbo = verbo[:-4]
    return verbo, palabras[i + 1:]


def es_sed_lectura(resto):
    lee = False
    for palabra in resto:
        if palabra in ("--quiet", "--silent") or re.match(r"^-[A-Za-z]*n[A-Za-z]*$", palabra):
            lee = True
        if palabra.startswith("-i") or palabra.startswith("--in-place"):
            return False
    return lee


def escribe_a_archivo(libre):
    for m in RE_REDIRIGE.finditer(libre):
        if m.group(1) == "2" or m.group(2) == "&":
            continue
        destino = m.group(3).lower()
        if destino and destino not in NULOS:
            return True
    return False


def unidad(ruta):
    m = RE_UNIDAD_BASH.match(ruta)
    return f'{m.group(1).upper()}:{ruta[m.end():] or "/"}' if m else ruta


def relativa(crudo):
    ruta = unidad(crudo.strip())
    return not (ruta.startswith(("~", "/", "\\")) or (len(ruta) > 1 and ruta[1] == ":"))


def ruta_md(crudo, base):
    ruta = crudo.strip()
    if not ruta or "://" in ruta or ruta.find(":", 2) >= 0:
        return None
    ruta = unidad(ruta)
    if de_red(ruta) or (base and de_red(base) and relativa(ruta)):
        return None
    if ruta.startswith("~"):
        ruta = os.path.expanduser(ruta)
    while "\\\\" in ruta:
        ruta = ruta.replace("\\\\", "\\")
    if not (len(ruta) > 1 and ruta[1] == ":") and not ruta.startswith(("/", "\\")):
        if not base:
            return corto(ruta, 300)
        ruta = os.path.join(base, ruta)
    return corto(os.path.normpath(ruta), 300)


def carpeta_nueva(resto, base):
    palabras = [p for p in resto if not p.startswith("-")]
    if not palabras:
        return None
    crudo = " ".join(palabras)
    if crudo[0] in "\"'":
        cierre = crudo.find(crudo[0], 1)
        destino = crudo[1:cierre] if cierre > 0 else crudo[1:]
    else:
        destino = palabras[0]
    if not destino or "$" in destino:
        return None
    destino = unidad(destino)
    if de_red(destino):
        return None
    if destino.startswith("~"):
        return os.path.expanduser(destino)
    if len(destino) > 1 and destino[1] == ":" or destino.startswith(("/", "\\")):
        return destino
    return os.path.join(base, destino) if base else None


def notas_de_comando(comando, cwd):
    if not isinstance(comando, str):
        return None, []
    comando = sin_textos_largos(comando[:LARGO_ANALIZADO])
    if ".md" not in comando.lower():
        return None, []
    base = str(cwd or "") or None
    grupos = {"leer": [], "buscar": [], "ejecutar": []}
    escribe = False
    for piezas, libre in segmentos(comando):
        if escribe_a_archivo(libre):
            escribe = True
        verbo, resto = verbo_y_resto("".join(piezas))
        if verbo in CAMBIO_DE_CARPETA:
            base = carpeta_nueva(resto, base)
            continue
        if verbo in RED:
            continue
        if verbo in ESCRITURA:
            escribe = True
        palabras = palabras_de(piezas)
        if verbo in LECTURA or (verbo == "sed" and es_sed_lectura(resto)):
            clase = "leer"
            elegidas = candidatas(argumentos(palabras), True)
        elif verbo in BUSQUEDA:
            clase = "buscar"
            elegidas = candidatas(sin_patron(argumentos(palabras), verbo), True)
        elif verbo in ECO:
            clase = "ejecutar"
            elegidas = candidatas(destinos(libre))
        else:
            clase = "ejecutar"
            elegidas = candidatas(sin_textos(palabras), True)
        salidas = {sin_comillas(d) for d in destinos(libre)}
        for crudo in elegidas:
            ruta = ruta_md(crudo, base)
            if ruta and (verbo in ECO or crudo in salidas or ((base or not relativa(crudo)) and os.path.isfile(ruta))):
                grupos[clase].append(ruta)
    if escribe:
        grupos["ejecutar"] = grupos["leer"] + grupos["ejecutar"]
        grupos["leer"] = []
    for clase in ("leer", "buscar"):
        if grupos[clase]:
            break
    else:
        clase = "ejecutar"
    rutas = []
    for ruta in grupos[clase]:
        if ruta not in rutas:
            rutas.append(ruta)
            if len(rutas) >= MAXIMO_RUTAS:
                break
    return (clase if clase != "ejecutar" else None), rutas


def opcion_cerebro(comando):
    m = RE_OPCION_CEREBRO.search(str(comando or "")[:LARGO_ANALIZADO].lower())
    if not m:
        return ""
    opcion = RE_OPCION.search(m.group(1))
    return opcion.group(1) if opcion else ""


def texto_salida(respuesta):
    if isinstance(respuesta, dict):
        respuesta = respuesta.get("stdout")
    if not isinstance(respuesta, str):
        return ""
    if len(respuesta) > 2 * LARGO_ANALIZADO:
        return f"{respuesta[:LARGO_ANALIZADO]}\n{respuesta[-LARGO_ANALIZADO:]}"
    return respuesta


def ruta_de_salida(texto):
    m = RE_RUTA_SALIDA.match(texto.strip())
    if not m:
        return None
    ruta = m.group(1)
    return corto(ruta, 300) if len(ruta) <= 300 and parece_ruta(ruta) else None


def recomendadas(opcion, respuesta):
    salida = texto_salida(respuesta)
    if not salida:
        return []
    elegidas = []
    if opcion == "sobre":
        adentro = False
        for linea in salida.splitlines():
            if linea.strip() == "Para leer primero:":
                adentro = True
            elif adentro and linea.startswith("  "):
                elegidas.append(linea)
            elif adentro:
                break
    elif opcion == "parecidas":
        elegidas = [m.group(1) for m in map(RE_PARECIDA.match, salida.splitlines()) if m]
    elif opcion == "buscar":
        elegidas = [m.group(1) for m in map(RE_BUSCADA.match, salida.splitlines()) if m]
    rutas = []
    for linea in elegidas:
        ruta = ruta_de_salida(linea)
        if ruta and ruta not in rutas:
            rutas.append(ruta)
            if len(rutas) >= MAXIMO_RUTAS:
                break
    return rutas


def entero(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


EVENTOS = {
    "PreToolUse": "pre", "PostToolUse": "post", "PostToolUseFailure": "falla",
    "UserPromptSubmit": "usuario", "Stop": "fin",
    "SubagentStop": "sub-fin", "Notification": "espera", "PreCompact": "compacta",
    "SessionStart": "inicio", "SessionEnd": "cierre",
}
DE_HERRAMIENTA = ("pre", "post", "falla")


def armar(datos):
    fase = EVENTOS.get(str(datos.get("hook_event_name") or "PostToolUse"), "otro")
    herramienta = str(datos.get("tool_name") or "")
    entrada = datos.get("tool_input") or {}
    if not isinstance(entrada, dict):
        entrada = {}
    tipo = TIPOS.get(herramienta, "otro") if fase in DE_HERRAMIENTA else fase
    sesion = str(datos.get("session_id") or "")[:8]
    evento = {
        "t": round(time.time(), 3),
        "s": sesion if RE_SESION.match(sesion) else "",
        "e": fase,
        "h": herramienta if RE_HERRAMIENTA.match(herramienta) else "",
        "k": tipo,
    }
    if ruta_guardable(datos.get("cwd")):
        evento["c"] = corto(datos.get("cwd"), 200)
    agente = nombre_seguro(datos.get("agent_id")) or nombre_seguro(datos.get("agent_type"))
    if agente:
        evento["a"] = agente
    if nombre_seguro(datos.get("agent_type")):
        evento["at"] = datos["agent_type"]
    if fase in DE_HERRAMIENTA:
        sumar_de_herramienta(evento, fase, herramienta, tipo, entrada, datos)
    else:
        sumar_de_sesion(evento, fase, datos)
    if hooks_comun.de_prueba():
        evento["z"] = 1
    return evento


def motivo_de(motivo):
    codigo, linea, fin, origen = (list(motivo) + [None] * 4)[:4] if isinstance(motivo, (list, tuple)) else [None] * 4
    renglon = [x if entero(x) and 0 <= x < TOPE_RENGLON else 0 for x in (linea, fin)]
    return [codigo if codigo in MOTIVOS_PISTA else "p"] + renglon + [corto(origen, 300) if ruta_guardable(origen) else ""]


def aviso(sesion, cwd, notas, codigo, notas_aprendidas=(), codigo_aprendido=(), motivos=(), sin_aprendido=False):
    sesion = str(sesion or "")[:8]
    evento = {"t": round(time.time(), 3), "s": sesion if RE_SESION.match(sesion) else "", "e": "aviso", "h": "",
              "k": "aviso"}
    if ruta_guardable(cwd):
        evento["c"] = corto(cwd, 200)
    for campo, rutas, largo in (("fs", notas, 300), ("fc", codigo, 120), ("na", notas_aprendidas, 300),
                                ("ca", codigo_aprendido, 300)):
        rutas = [corto(r, largo) for r in rutas if ruta_guardable(r)][:MAXIMO_RUTAS]
        if rutas:
            evento[campo] = rutas
    if motivos and len(motivos) == len(notas) and "fs" in evento:
        evento["fp"] = [motivo_de(m) for r, m in zip(notas, motivos) if ruta_guardable(r)][:MAXIMO_RUTAS]
    if sin_aprendido:
        evento["sa"] = 1
    if hooks_comun.de_prueba():
        evento["z"] = 1
    return evento


def recuerdo(sesion, cwd, archivo, notas):
    sesion = str(sesion or "")[:8]
    evento = {"t": round(time.time(), 3), "s": sesion if RE_SESION.match(sesion) else "", "e": "recuerda", "h": "",
              "k": "recuerda"}
    if ruta_guardable(cwd):
        evento["c"] = corto(cwd, 200)
    if ruta_guardable(archivo):
        evento["f"] = corto(archivo, 300)
    rutas = [corto(r, 300) for r in notas if ruta_guardable(r)][:MAXIMO_RUTAS]
    if rutas:
        evento["fs"] = rutas
    if hooks_comun.de_prueba():
        evento["z"] = 1
    return evento


def recordatorio(sesion, cwd, motivo, archivos=0):
    sesion = str(sesion or "")[:8]
    evento = {"t": round(time.time(), 3), "s": sesion if RE_SESION.match(sesion) else "", "e": "guarda", "h": "",
              "k": "guarda", "p": motivo if motivo in ("compact", "fin") else "fin"}
    if ruta_guardable(cwd):
        evento["c"] = corto(cwd, 200)
    if entero(archivos) and 0 < archivos < 10 ** 6:
        evento["n"] = archivos
    if hooks_comun.de_prueba():
        evento["z"] = 1
    return evento


def escribir_evento(evento, espera=None):
    llave = (evento.get("s"), evento["id"], evento.get("e")) if evento.get("id") else None
    escribir((f'{json.dumps(evento, ensure_ascii=False, separators=(",", ":"))}\r\n').encode("utf-8"), espera, llave)


def repetido(cola, llave):
    try:
        ultimo = json.loads(cola.rstrip(b"\r\n").rsplit(b"\n", 1)[-1])
        return (ultimo.get("s"), ultimo.get("id"), ultimo.get("e")) == llave
    except (ValueError, AttributeError):
        return False


def sumar_de_sesion(evento, fase, datos):
    if fase == "usuario":
        evento["n"] = len(str(datos.get("prompt") or ""))
    elif fase in ("compacta", "inicio", "cierre"):
        motivo = str(datos.get("trigger") or datos.get("source") or datos.get("reason") or "")
        if motivo:
            evento["p"] = motivo if motivo in MOTIVOS else "otro"


def sumar_de_herramienta(evento, fase, herramienta, tipo, entrada, datos):
    if datos.get("tool_use_id"):
        evento["id"] = str(datos.get("tool_use_id"))[-10:]
    ruta = ruta_de_archivo(entrada.get("file_path") or entrada.get("notebook_path"))
    carpeta = ruta_guardable(entrada.get("path"))
    opcion = sumar_comando(evento, entrada, datos.get("cwd")) if tipo == "ejecutar" else ""
    if opcion:
        tipo = evento["k"] = "consulta"
        evento["p"] = opcion
        evento.pop("fs", None)
    if fase == "pre":
        if ruta:
            evento["f"] = corto(ruta, 300)
        elif tipo == "buscar" and carpeta:
            evento["f"] = corto(carpeta, 300)
        return
    duracion = datos.get("duration_ms")
    if entero(duracion) and 0 <= duracion < 10 ** 8:
        evento["d"] = duracion
    if fase == "falla":
        evento["x"] = [1 if datos.get("is_interrupt") is True else 0, 1 if datos.get("is_timeout") is True else 0]
        salida = RE_SALIDA.match(str(datos.get("error") or "")[:40]) if "b" in evento else None
        if salida and int(salida.group(1)) < 2 ** 32:
            evento["xc"] = int(salida.group(1))
        if ruta:
            evento["f"] = corto(ruta, 300)
        return
    respuesta = datos.get("tool_response")
    if "b" in evento and isinstance(respuesta, dict):
        if respuesta.get("backgroundTaskId") or entrada.get("run_in_background") is True:
            evento["bg"] = 1
        if respuesta.get("returnCodeInterpretation") == "No matches found":
            evento["nr"] = 1
    if opcion:
        try:
            rutas = recomendadas(opcion, respuesta)
        except Exception:
            rutas = []
        if rutas:
            evento["fs"] = rutas
    if tipo == "crear" and isinstance(respuesta, dict) and respuesta.get("type") == "update":
        tipo = evento["k"] = "editar"
    sumar_cantidades(evento, herramienta, entrada, respuesta)
    sumar_destino(evento, tipo, herramienta, entrada, ruta, carpeta)


def sumar_comando(evento, entrada, cwd):
    evento["b"] = clase_comando(entrada.get("command"))
    clase, rutas = notas_de_comando(entrada.get("command"), cwd)
    if rutas:
        evento["fs"] = rutas
        if clase:
            evento["k"] = clase
    return opcion_cerebro(entrada.get("command")) if evento["b"] == "cerebro" and not clase else ""


def sumar_cantidades(evento, herramienta, entrada, respuesta):
    if herramienta in ("Edit", "MultiEdit"):
        cambios = entrada.get("edits") if herramienta == "MultiEdit" else [entrada]
        if isinstance(cambios, list):
            evento["m"] = [sum(lineas(c.get("new_string")) for c in cambios if isinstance(c, dict)),
                           sum(lineas(c.get("old_string")) for c in cambios if isinstance(c, dict))]
    elif herramienta == "Write":
        evento["m"] = [lineas(entrada.get("content")), 0]
    elif herramienta == "Read" and isinstance(respuesta, dict) and isinstance(respuesta.get("file"), dict):
        archivo = respuesta["file"]
        tramo = [archivo.get("startLine"), archivo.get("numLines"), archivo.get("totalLines")]
        if all(entero(x) for x in tramo):
            evento["r"] = tramo


def sumar_destino(evento, tipo, herramienta, entrada, ruta, carpeta):
    if ruta:
        evento["f"] = corto(ruta, 300)
    elif tipo == "buscar":
        if carpeta:
            evento["f"] = corto(carpeta, 300)
    elif tipo == "agente":
        nombre = nombre_seguro(entrada.get("subagent_type"))
        if nombre:
            evento["p"] = nombre
    elif tipo == "web":
        host = host_de(entrada.get("url"))
        if host:
            evento["p"] = host
    elif herramienta == "Skill":
        nombre = nombre_seguro(entrada.get("skill"))
        if nombre:
            evento["p"] = nombre


def primer_momento():
    try:
        with open(REGISTRO, "rb") as f:
            m = RE_PRIMERO.match(f.read(32))
    except OSError:
        return None
    return int(m.group(1)) if m else None


def rotar(ahora=None):
    ahora = time.time() if ahora is None else ahora
    try:
        if os.path.getsize(REGISTRO) > TOPE or ahora - (primer_momento() or ahora) > EDAD_ROTAR:
            base = os.path.join(CARPETA, f'eventos-{time.strftime("%Y%m%d-%H%M%S", time.localtime(ahora))}')
            destino, n = f"{base}.jsonl", 1
            while os.path.exists(destino):
                destino, n = f"{base}-{n}.jsonl", n + 1
            os.rename(REGISTRO, destino)
            return True
    except OSError:
        pass
    return False


def podar(ahora=None):
    import servidor
    hecho = servidor.ordenar_registros(ahora)
    return hecho["borrados"] if hecho else 0


class CandadoOcupado(OSError):
    pass


def tomar_candado(espera=None):
    return archivos.tomar_candado(CANDADO, ESPERA_CANDADO if espera is None else espera)


def soltar_candado(fd):
    archivos.soltar_candado(fd)


def escribir(linea, espera=None, llave=None):
    permisos.crear(CARPETA)
    fd = tomar_candado(espera)
    if fd is None and archivos.hay_candados():
        raise CandadoOcupado("no conseguí el candado del registro: el evento no se guardó")
    rotado = False
    try:
        rotado = rotar()
        with open(REGISTRO, "ab+") as f:
            largo = f.seek(0, os.SEEK_END)
            if largo:
                f.seek(max(0, largo - COLA_REPETIDO))
                cola = f.read()
                if llave is not None and repetido(cola, llave):
                    return
                if not cola.endswith(b"\n"):
                    linea = b"\r\n" + linea
            f.write(linea)
    finally:
        soltar_candado(fd)
    if rotado:
        try:
            podar()
        except Exception:
            hooks_comun.fallo()


def main():
    try:
        datos = hooks_comun.entrada()
        if not (datos.get("tool_name") or datos.get("hook_event_name") in EVENTOS):
            return
        if datos.get("hook_event_name") == "UserPromptSubmit" and hooks_comun.del_sistema(str(datos.get("prompt") or "")):
            return
        evento = armar(datos)
        escribir_evento(evento, ESPERA_DE_FONDO)
        if evento["e"] == "fin":
            import aprender
            aprender.quizas()
    except Exception:
        hooks_comun.fallo()
