import re

from mapa import Bloque

LENGUAJE_DE = {".cs": "cs", ".java": "java", ".ts": "ts", ".tsx": "ts", ".mts": "ts", ".cts": "ts", ".kt": "kotlin",
               ".kts": "kotlin", ".go": "go", ".rs": "rust", ".php": "php"}
LENGUAJE_DE.update(dict.fromkeys((".cpp", ".cc", ".cxx", ".c++", ".c", ".h", ".hpp", ".hh", ".hxx", ".h++", ".inl",
                                  ".ipp"), "cpp"))
POR_FIRMA = {"cs", "cpp", "java"}
CONTROL = {"if", "else", "for", "foreach", "while", "do", "switch", "case", "default", "try", "catch", "finally",
           "using", "lock", "fixed", "checked", "unchecked", "return", "throw", "new", "sizeof", "typeof", "nameof",
           "await", "yield", "goto", "when", "with", "get", "set", "init", "add", "remove", "delete", "co_return",
           "co_await", "co_yield", "static_assert", "decltype", "alignof", "constexpr", "var", "base", "this", "__try",
           "__except", "__finally", "__leave", "__if_exists", "__if_not_exists", "synchronized", "super"}
COMENTARIOS = r"//[^\n]*|/\*.*?(?:\*/|\Z)|"
TAPAR = {
    "cs": COMENTARIOS + r'\$*"""(?:.|\n)*?(?:"""|\Z)|\$?@\$?"(?:[^"]|"")*(?:"|\Z)|\$?"(?:[^"\\\n]|\\.)*"?'
                        r"|'(?:[^'\\\n]|\\.){1,8}'",
    "cpp": COMENTARIOS + r'(?:u8|[LuU])?R"([^\s()\\]{0,16})\((?:.|\n)*?(?:\)\1"|\Z)|(?:u8|[LuU])?"(?:[^"\\\n]|\\.)*"?'
                         r"|(?:u8|[LuU])?'(?:[^'\\\n]|\\.){1,8}'",
    "java": COMENTARIOS + r'"""(?:.|\n)*?(?:"""|\Z)|"(?:[^"\\\n]|\\.)*"?|' + r"'(?:[^'\\\n]|\\.){1,8}'",
    "kotlin": COMENTARIOS + r'"""(?:.|\n)*?(?:"""|\Z)|"(?:[^"\\\n]|\\.)*"?|' + r"'(?:[^'\\\n]|\\.){1,8}'",
    "ts": COMENTARIOS + r"(?:(?<=[(,=:\[!&|?;\n])|(?<=\breturn))[ \t]*/(?![/*>])(?:[^/\\\[\n]|\\.|\[(?:[^\]\\\n]|\\.)*\])+"
                        r"/[A-Za-z]*|" + r'`(?:[^`\\]|\\.)*`?|"(?:[^"\\\n]|\\.)*"?|' + r"'(?:[^'\\\n]|\\.)*'?",
    "go": COMENTARIOS + r'`[^`]*`?|"(?:[^"\\\n]|\\.)*"?|' + r"'(?:[^'\\\n]|\\.){1,10}'",
    "rust": COMENTARIOS + r'b?r(#*)"(?:.|\n)*?(?:"\1|\Z)|b?"(?:[^"\\]|\\.)*"?'
                          r"|b?'(?:[^'\\\n]|\\(?:x[0-9a-fA-F]{2}|u\{[0-9a-fA-F]{1,6}\}|.))'",
    "php": COMENTARIOS + r"#(?!\[)[^\n]*|<<<[ \t]*['\"]?(\w+)['\"]?\n.*?\n[ \t]*\1\b|'(?:[^'\\]|\\.)*'?"
                         r'|"(?:[^"\\]|\\.)*"?',
}
TAPAR = {lenguaje: re.compile(patron, re.S) for lenguaje, patron in TAPAR.items()}
RE_COMENTARIOS = re.compile(COMENTARIOS[:-1], re.S)
NOMBRE = r"[A-Za-z_$][\w$]*"
DECLARACIONES = {
    "ts": [("espacio", r"\b(?:namespace|module)\s+[\w.$]+\s*$"),
           ("clase", r"\b(?P<palabra>class|interface|enum)\s+(?P<nombre>" + NOMBRE + ")"),
           ("clase", r"\b(?P<palabra>type)\s+(?P<nombre>" + NOMBRE + r")\s*(?:<[^=]*>)?\s*=\s*$"),
           ("funcion", r"\bfunction\s*\*?\s*(?P<nombre>" + NOMBRE + r")\s*(?:<[^(]*>)?\s*\("),
           ("funcion", r"\b(?:const|let|var)\s+(?P<nombre>" + NOMBRE + r")\s*(?::[^=]*)?=\s*(?:async\s+)?"
                       r"(?:\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)|" + NOMBRE + r")\s*(?::[^=]*)?=>\s*$"),
           ("metodo", r"^[ \t]*(?:(?:public|private|protected|static|async|readonly|override|abstract|declare|get|set)"
                      r"\s+|\*\s*)*(?P<nombre>" + NOMBRE + r")\s*(?:<[^(]*>)?\s*\([^;]*\)\s*(?::[^;]+)?\s*$")],
    "kotlin": [("clase", r"\b(?:(?:data|sealed|open|abstract|inner|enum|annotation|value|private|internal|public|"
                         r"protected)\s+)*(?P<palabra>class|interface|object)\s+(?P<nombre>[A-Za-z_]\w*)"),
               ("clase", r"\bcompanion\s+(?P<palabra>object)(?:\s+(?P<nombre>[A-Za-z_]\w*))?"),
               ("funcion", r"\bfun\s+(?:<[^>]*>\s*)?(?:[\w.<>?]+\.)?(?P<nombre>[A-Za-z_]\w*)\s*\(")],
    "go": [("funcion", r"\bfunc\s+(?:\(\s*(?:\w+\s+)?\*?\s*(?P<dueno>\w+)(?:\[[^\]]*\])?\s*\)\s*)?(?P<nombre>\w+)\s*"
                       r"(?:\[[^\]]*\])?\s*\("),
           ("clase", r"\btype\s+(?P<nombre>\w+)(?:\[[^\]]*\])?\s+(?P<palabra>struct|interface)\s*$")],
    "rust": [("funcion", r"\bfn\s+(?P<nombre>\w+)"),
             ("clase", r"\b(?P<palabra>struct|enum|trait|union)\s+(?P<nombre>\w+)"),
             ("clase", r"\b(?P<palabra>impl)\b(?:\s*<[^{]*?>)?\s+(?P<nombre>[\w:<>, &']+?(?:\s+for\s+[\w:<>, &']+?)?)"
                       r"\s*(?:where\b[^{]*)?$"),
             ("clase", r"\b(?P<palabra>mod)\s+(?P<nombre>\w+)\s*$")],
    "php": [("espacio", r"\bnamespace\s+[\w\\]+\s*$"),
            ("clase", r"(?<!new )\b(?P<palabra>class|interface|trait|enum)\s+(?P<nombre>\w+)"),
            ("funcion", r"\bfunction\s+&?\s*(?P<nombre>\w+)\s*\(")],
}
DECLARACIONES = {lenguaje: [(tipo, re.compile(patron, re.M)) for tipo, patron in lista]
                 for lenguaje, lista in DECLARACIONES.items()}
RE_SIGUE_OTRA = re.compile(r"\n[ \t]*(?:if|for|while|switch|when|else|return|match|loop|do|try|catch|val|var|let|const"
                           r"|defer|go|select|unsafe|throw|await|yield)\b")
RE_DIRECTIVA = re.compile(r"[ \t]*#[ \t]*(\w+)(.*)")
RE_SIGNOS = re.compile(r"[{}();]")
RE_PREFIJO = re.compile(r"\s*(?:\[\[[^\]]*\]\]\s*|\[[^\]\n]*\]\s*|(?:public|private|protected|signals|slots)\s*:(?!:)\s*"
                        r"|typedef\s+|template\s*<|export\s+|@(?!interface\b)\w+(?:\.\w+)*(?:\s*\((?:[^()]|\([^()]*\))*\))?"
                        r"\s*)")
MODIFICADORES = (r"(?:public|private|protected|internal|static|sealed|abstract|partial|readonly|ref|unsafe|new|file|"
                 r"virtual|override|extern|async|volatile|inline|explicit|friend|mutable|constexpr|consteval|final|"
                 r"strictfp|non-sealed|synchronized|native|transient)")
RE_CLASE = re.compile(r"(?:" + MODIFICADORES + r"\s+)*@?(class|struct|interface|record|enum|union)"
                      r"(?:\s+(?:class|struct))?\s+(?:[A-Z_][A-Z0-9_]*\s+)*([A-Za-z_]\w*)")
RE_ESPACIO = re.compile(r"(?:inline\s+)?namespace(?:\s+([\w.:]+))?\s*$|extern\s*$")
RE_LLAMADA = re.compile(r"(operator\s*(?:\(\)|\[\]|[^\s(\w]+|\w+)|~?[A-Za-z_]\w*(?:\s*::\s*~?[A-Za-z_]\w*)*)\s*"
                        r"(?:<(?:[^<>(){};=]|<[^<>(){};=]*>)*>)?\s*\(")
RE_PROPIEDAD = re.compile(r"(?:" + MODIFICADORES + r"\s+)*(?:event\s+)?[\w<>\[\],.?:*&\s]+?\s+"
                          r"(this\s*\[[^\]]*\]|[A-Za-z_]\w*)\s*$")
RE_INICIALIZADORES = re.compile(r"\)\s*(?:const\s*)?(?:noexcept\s*(?:\([^)]*\))?\s*)?:(?!:)")


def tapar(texto, lenguaje):
    blanco = lambda m: re.sub(r"[^\n]", " ", m.group(0))
    texto = TAPAR[lenguaje].sub(blanco, texto)
    if lenguaje not in ("cs", "cpp"):
        return texto
    renglones = texto.split("\n")
    pila = []
    sigue = False
    for k, renglon in enumerate(renglones):
        directiva = RE_DIRECTIVA.match(renglon) if not sigue else None
        if sigue or directiva:
            sigue = renglon.rstrip().endswith("\\")
            if directiva:
                palabra, resto = directiva.group(1), directiva.group(2).strip()
                falsa = resto in ("0", "false")
                if palabra in ("if", "ifdef", "ifndef"):
                    afuera = not pila or pila[-1]["activa"]
                    activa = afuera and not (palabra == "if" and falsa)
                    pila.append({"afuera": afuera, "activa": activa, "tomada": activa})
                elif palabra in ("elif", "elseif") and pila:
                    actual = pila[-1]
                    actual["activa"] = actual["afuera"] and not actual["tomada"] and not falsa
                    actual["tomada"] = actual["tomada"] or actual["activa"]
                elif palabra == "else" and pila:
                    actual = pila[-1]
                    actual["activa"] = actual["afuera"] and not actual["tomada"]
                    actual["tomada"] = True
                elif palabra == "endif" and pila:
                    pila.pop()
            renglones[k] = " " * len(renglon)
        elif pila and not pila[-1]["activa"]:
            renglones[k] = " " * len(renglon)
    return "\n".join(renglones)


def nucleo_de(cabeza):
    desde = 0
    while True:
        m = RE_PREFIJO.match(cabeza, desde)
        if not m or m.end() == desde:
            return desde
        desde = m.end()
        if cabeza[desde - 1] == "<":
            profundidad = 1
            while desde < len(cabeza) and profundidad:
                profundidad += {"<": 1, ">": -1}.get(cabeza[desde], 0)
                desde += 1


def palabras(texto):
    return re.findall(r"[A-Za-z_]\w*", texto)


def es_firma(cabeza, desde, lenguaje):
    control = CONTROL - {"default"} if lenguaje == "java" else CONTROL
    for m in RE_LLAMADA.finditer(cabeza, desde):
        nombre = re.sub(r"\s+", "", m.group(1))
        antes = cabeza[desde:m.start()]
        ultimo = nombre.split("::")[-1].lstrip("~")
        if ultimo in control or "=" in antes or "(" in antes or antes.rstrip().endswith((".", "->")) \
                or set(palabras(antes)) & control - {"synchronized"}:
            return None
        profundidad, k = 0, m.end() - 1
        while k < len(cabeza):
            profundidad += {"(": 1, ")": -1}.get(cabeza[k], 0)
            if profundidad == 0:
                break
            k += 1
        cola = cabeza[k + 1:]
        if lenguaje == "cpp":
            if re.search(r"=(?!\s*(?:0|default|delete)\s*$)", cola):
                return None
        elif "=" in re.sub(r"=>.*", "", cola) or "->" in cola:
            return None
        return m.start(1), nombre
    return None


def por_palabras(cabeza, lenguaje, padre):
    mejor = None
    for tipo, patron in DECLARACIONES[lenguaje]:
        if tipo == "metodo" and (padre is None or padre.tipo != "clase"):
            continue
        for m in patron.finditer(cabeza):
            if mejor is None or m.start() > mejor[1].start():
                mejor = (tipo, m)
    if mejor is None:
        return None
    tipo, m = mejor
    if RE_SIGUE_OTRA.search(cabeza, m.start()):
        return None
    if tipo == "espacio":
        return "espacio", None, None
    grupos = m.groupdict()
    nombre = grupos.get("nombre")
    if tipo == "clase" and not nombre:
        nombre = "Companion"
    if not nombre or nombre in CONTROL or nombre in ("function", "constructor") and tipo != "metodo":
        return None
    nombre = re.sub(r"\s+", " ", nombre).strip()
    lugar = m.start("nombre") if grupos.get("nombre") else m.start()
    if grupos.get("dueno"):
        nombre = f'{grupos["dueno"]}.{nombre}'
    if tipo == "clase":
        return "clase", nombre, lugar, grupos.get("palabra") or "class"
    return "metodo", nombre, lugar


def clasificar(cabeza, lenguaje, padre=None):
    if lenguaje not in POR_FIRMA:
        return por_palabras(cabeza, lenguaje, padre)
    desde = nucleo_de(cabeza)
    resto = cabeza[desde:]
    if not resto.strip():
        return None
    if RE_ESPACIO.match(resto.strip()):
        return "espacio", None, None
    m = RE_CLASE.match(resto.lstrip())
    if m:
        corrido = len(resto) - len(resto.lstrip())
        return "clase", m.group(2), desde + corrido + m.start(2), m.group(1)
    firma = es_firma(cabeza, desde, lenguaje)
    if firma:
        return "metodo", firma[1], firma[0]
    if lenguaje == "cs":
        m = RE_PROPIEDAD.match(resto)
        if m and not set(palabras(resto)) & CONTROL - {"this"} and "=" not in resto:
            return "propiedad", re.sub(r"\s+", "", m.group(1)), desde + m.start(1)
    return None


def estructura(texto, lenguaje, lineas):
    t = tapar(texto, lenguaje)
    bloques = []
    pila = []
    parentesis = 0
    comienzo = 0
    signos = list(RE_SIGNOS.finditer(t))
    i = 0
    while i < len(signos):
        m = signos[i]
        c, pos = m.group(0), m.start()
        if c == "(":
            parentesis += 1
        elif c == ")":
            parentesis = max(0, parentesis - 1)
        elif c == ";":
            if parentesis == 0:
                if lenguaje == "cs":
                    corto(bloques, pila, t[comienzo:pos], comienzo, lineas)
                comienzo = pos + 1
        elif c == "{":
            cabeza = t[comienzo:pos]
            if parentesis == 0 and (lenguaje == "cpp" and RE_INICIALIZADORES.search(cabeza)
                                    and re.search(r"[\w>]\s*$", cabeza)
                                    or lenguaje == "ts" and es_tipo_ts(texto[comienzo:pos])):
                profundidad = 0
                while i < len(signos):
                    profundidad += {"{": 1, "}": -1}.get(signos[i].group(0), 0)
                    if profundidad == 0:
                        break
                    i += 1
                i += 1
                continue
            padre = padre_de(pila)
            info = clasificar(cabeza, lenguaje, padre) if parentesis == 0 else None
            bloque = None
            if info and info[0] in ("clase", "metodo", "propiedad"):
                tipo = info[0]
                if tipo == "metodo":
                    metodo = (padre is not None and padre.tipo == "clase") or "::" in info[1] or "." in info[1]
                    tipo = "metodo" if metodo else "funcion"
                bloque = Bloque(tipo, info[1], lineas.de(comienzo + info[2]), padre=padre)
                if info[0] == "clase":
                    bloque.palabra = info[3]
                bloques.append(bloque)
            pila.append((bloque, parentesis, comienzo))
            parentesis = 0
            comienzo = pos + 1
        elif c == "}":
            previo = None
            if pila:
                bloque, parentesis, previo = pila.pop()
                if bloque is not None:
                    bloque.fin = lineas.de(pos)
            comienzo = previo if parentesis and previo is not None else pos + 1
        i += 1
    return bloques


def es_tipo_ts(cabeza):
    sin_flechas = RE_COMENTARIOS.sub(" ", cabeza).replace("=>", "")
    return bool(re.search(r"\)\s*:\s*$|\)\s*:[^{;=]*[|&,]\s*$", sin_flechas)) \
        or sin_flechas.count("<") > sin_flechas.count(">")


def padre_de(pila):
    return next((b for b, _, _ in reversed(pila) if b is not None), None)


def corto(bloques, pila, cabeza, comienzo, lineas):
    if "=>" not in cabeza:
        return
    antes = cabeza[:cabeza.index("=>")]
    info = clasificar(antes, "cs")
    if not info or info[0] not in ("metodo", "propiedad"):
        return
    padre = padre_de(pila)
    tipo = info[0] if info[0] == "propiedad" else ("metodo" if padre is not None and padre.tipo == "clase" else "funcion")
    linea = lineas.de(comienzo + info[2])
    bloques.append(Bloque(tipo, info[1], linea, lineas.de(comienzo + len(cabeza)), padre))
