import ast
import bisect
import re
import sys
import time
from pathlib import Path

from textos import cantidad, miles, sin_marcas

CARPETA = Path(__file__).resolve().parent
EXTENSIONES_JS = {".js", ".mjs", ".cjs"}
EXTENSIONES_HTML = {".html", ".htm"}
EXTENSIONES_CSS = {".css"}
EXTENSIONES_PY = {".py", ".pyw"}
ANTES_DE_REGEX = {"return", "typeof", "case", "do", "else", "in", "of", "new", "delete", "void", "throw",
                  "instanceof", "yield", "await"}
NO_SON_METODOS = {"if", "for", "while", "switch", "catch", "with", "function", "return", "typeof", "new",
                  "delete", "void", "do", "else", "try", "finally", "in", "of", "instanceof", "await", "yield"}
ANTES_DE_METODO = {"{", ",", "}", ";", "async", "get", "set", "static", "*"}
BIBLIOTECAS_SIN_PREFIJO = {"d3"}
FIN_DE_EXPRESION = {"const", "let", "var", "function", "class"}
LARGO_MINIMO_ANONIMA = 10
FUNCION_GRANDE = 200
GRUPOS_MAXIMOS = 40
LINEAS_POR_GRUPO = 8
ANCHO_RANGO = 13

FICHA = re.compile("|".join([
    r"(?P<espacio>\s+)",
    r"(?P<comentario>//[^\n]*|/\*[\s\S]*?(?:\*/|\Z))",
    r"(?P<cadena>'(?:[^'\\\n]|\\[\s\S])*'?|\"(?:[^\"\\\n]|\\[\s\S])*\"?)",
    r"(?P<nombre>[A-Za-z_$\u0080-￿][\w$\u0080-￿]*)",
    r"(?P<numero>\d[\w.]*|\.\d\w*)",
    r"(?P<plantilla>`)",
    r"(?P<barra>/)",
    r"(?P<signo>=>|===?|!==?|\?\?=?|\?\.|\.\.\.|&&=?|\|\|=?|\*\*=?|<<=?|>>>?=?|\+\+|--|[-+*%&|^<>]=?|[{}()\[\];,.:?~!=#@])",
    r"(?P<otro>[\s\S])",
]))
REGEX_JS = re.compile(r"/(?:[^/\\\[\n]|\\.|\[(?:[^\]\\\n]|\\.)*\])+/[A-Za-z]*")
CUERPO_PLANTILLA = re.compile(r"(?:[^`\\$]|\\[\s\S]|\$(?!\{))*")
ETIQUETA = re.compile(r"<(script|style)\b[^>]*>", re.I)
ID_HTML = re.compile(r"\sid\s*=\s*[\"']([^\"']+)[\"']")
DEF_PY = re.compile(r"^([ \t]*)(async\s+def|def|class)\s+(\w+)")


class Bloque:
    __slots__ = ("tipo", "nombre", "inicio", "fin", "padre")

    def __init__(self, tipo, nombre, inicio, fin=None, padre=None):
        self.tipo = tipo
        self.nombre = nombre
        self.inicio = inicio
        self.fin = fin
        self.padre = padre


class Lineas:
    def __init__(self, texto):
        self.saltos = [m.start() for m in re.finditer("\n", texto)]

    def de(self, posicion):
        return bisect.bisect_left(self.saltos, posicion) + 1


def fichas_js(texto, desde, hasta):
    fichas = []
    pila = []
    pos = desde
    en_plantilla = False
    while pos < hasta:
        if en_plantilla:
            pos = CUERPO_PLANTILLA.match(texto, pos, hasta).end()
            if pos >= hasta:
                break
            en_plantilla = False
            if texto[pos] == "`":
                pos += 1
            else:
                pila.append("${")
                fichas.append(("signo", "(", pos))
                pos += 2
            continue
        m = FICHA.match(texto, pos, hasta)
        tipo = m.lastgroup
        if tipo in ("espacio", "comentario"):
            pos = m.end()
            continue
        if tipo == "barra":
            if puede_ser_regex(fichas):
                r = REGEX_JS.match(texto, pos, hasta)
                if r:
                    fichas.append(("cadena", "/", pos))
                    pos = r.end()
                    continue
            fichas.append(("signo", "/", pos))
            pos += 1
            continue
        if tipo == "plantilla":
            fichas.append(("cadena", "`", pos))
            pos += 1
            en_plantilla = True
            continue
        valor = m.group()
        if valor == "{":
            pila.append("{")
        elif valor == "}" and pila:
            if pila.pop() == "${":
                fichas.append(("signo", ")", pos))
                pos += 1
                en_plantilla = True
                continue
        fichas.append((tipo, valor, pos))
        pos = m.end()
    return fichas


def puede_ser_regex(fichas):
    if not fichas:
        return True
    tipo, valor, _ = fichas[-1]
    if tipo == "nombre":
        return valor in ANTES_DE_REGEX
    if tipo in ("numero", "cadena"):
        return False
    return valor not in (")", "]", "}")


def es(fichas, i, valor):
    return 0 <= i < len(fichas) and fichas[i][1] == valor and fichas[i][0] != "cadena"


def es_nombre(fichas, i):
    return 0 <= i < len(fichas) and fichas[i][0] == "nombre"


def nombre_asignado(fichas, k):
    if es(fichas, k, "="):
        cadena = []
        j = k - 1
        while es_nombre(fichas, j):
            cadena.append(fichas[j])
            if es(fichas, j - 1, ".") or es(fichas, j - 1, "?."):
                j -= 2
            else:
                break
        if cadena:
            cadena.reverse()
            return ".".join(f[1] for f in cadena), cadena[0][2]
        return None
    if es(fichas, k, ":") and 0 <= k - 1 and fichas[k - 1][0] in ("nombre", "cadena") \
            and (es(fichas, k - 2, "{") or es(fichas, k - 2, ",")):
        clave = fichas[k - 1][1]
        if fichas[k - 1][0] == "cadena":
            clave = clave.strip("'\"")
        return clave, fichas[k - 1][2]
    return None


def nombre_de_llamada(fichas, pila):
    if not pila or pila[-1][0] != "(":
        return None
    j = pila[-1][1]
    if not es_nombre(fichas, j - 1) or fichas[j - 1][1] in NO_SON_METODOS:
        return None
    llamada = fichas[j - 1][1]
    if es(fichas, j - 2, ".") and es_nombre(fichas, j - 3) and fichas[j - 3][1] not in BIBLIOTECAS_SIN_PREFIJO:
        llamada = f"{fichas[j - 3][1]}.{llamada}"
    if j + 1 < len(fichas) and fichas[j + 1][0] == "cadena" and fichas[j + 1][1] not in ("`", "/"):
        return f"{llamada}({fichas[j + 1][1]}, …)"
    return f"{llamada}(…)"


def funcion_que_arranca(fichas, k, pila):
    if es_nombre(fichas, k) and fichas[k][1] == "async":
        k -= 1
    nombrada = nombre_asignado(fichas, k)
    if nombrada:
        return "funcion", nombrada[0], nombrada[1]
    llamada = nombre_de_llamada(fichas, pila)
    if llamada:
        return "anonima", llamada, None
    return None


def funcion_de_llave(fichas, i, parejas, pila):
    if i == 0:
        return None
    if es(fichas, i - 1, ")") and (i - 1) in parejas:
        j = parejas[i - 1]
        k = j - 1
        if not es_nombre(fichas, k):
            return None
        palabra = fichas[k][1]
        if palabra == "function":
            info = funcion_que_arranca(fichas, k - 1, pila)
            if info:
                return info[0], info[1], info[2] if info[2] is not None else fichas[k][2]
            return None
        if es(fichas, k - 1, "function") or (es(fichas, k - 1, "*") and es(fichas, k - 2, "function")):
            inicio = k - 1 if es(fichas, k - 1, "function") else k - 2
            if es_nombre(fichas, inicio - 1) and fichas[inicio - 1][1] == "async":
                inicio -= 1
            return "funcion", palabra, fichas[inicio][2]
        if palabra in NO_SON_METODOS:
            return None
        anterior = fichas[k - 1][1] if k > 0 else "{"
        if k == 0 or (anterior in ANTES_DE_METODO and fichas[k - 1][0] != "cadena"):
            inicio = k
            while inicio > 0 and fichas[inicio - 1][0] == "nombre" and fichas[inicio - 1][1] in ("async", "get", "set", "static"):
                inicio -= 1
            return "metodo", palabra, fichas[inicio][2]
        return None
    j = i - 1
    while j >= 0 and i - j <= 6 and (es_nombre(fichas, j) or es(fichas, j, ".")):
        if fichas[j][1] == "class":
            if es_nombre(fichas, j + 1) and fichas[j + 1][1] != "extends":
                return "clase", fichas[j + 1][1], fichas[j][2]
            nombrada = nombre_asignado(fichas, j - 1)
            if nombrada:
                return "clase", nombrada[0], nombrada[1]
            return None
        j -= 1
    return None


def funcion_de_flecha(fichas, a, parejas, pila):
    if es(fichas, a - 1, ")") and (a - 1) in parejas:
        k = parejas[a - 1] - 1
    elif es_nombre(fichas, a - 1):
        k = a - 2
    else:
        return None
    info = funcion_que_arranca(fichas, k, pila)
    if not info:
        return None
    inicio = info[2]
    if inicio is None:
        inicio = fichas[k + 1][2] if not (es_nombre(fichas, k) and fichas[k][1] == "async") else fichas[k][2]
    return info[0], info[1], inicio


def padre_en_pila(pila):
    for entrada in reversed(pila):
        if entrada[2] is not None:
            return entrada[2]
    return None


def estructura_js(texto, desde, hasta, lineas):
    fichas = fichas_js(texto, desde, hasta)
    bloques = []
    pila = []
    parejas = {}
    flecha_con_cuerpo = None
    pendientes = []

    def cerrar_pendientes(profundidad, i):
        while pendientes and pendientes[-1][0] >= profundidad:
            _, bloque = pendientes.pop()
            ultimo = fichas[i - 1][2] if i > 0 else desde
            bloque.fin = max(bloque.inicio, lineas.de(ultimo))
            bloques.append(bloque)

    for i, (tipo, valor, pos) in enumerate(fichas):
        if tipo == "nombre" and valor in FIN_DE_EXPRESION:
            cerrar_pendientes(len(pila), i)
            continue
        if tipo != "signo":
            continue
        if valor in ("(", "[", "{"):
            bloque = None
            if valor == "{":
                info = flecha_con_cuerpo if flecha_con_cuerpo and flecha_con_cuerpo[0] == i else None
                info = info[1] if info else funcion_de_llave(fichas, i, parejas, pila)
                if info:
                    bloque = Bloque(info[0], info[1], lineas.de(info[2]), padre=padre_en_pila(pila))
            pila.append((valor, i, bloque))
            continue
        if valor in (")", "]", "}"):
            cerrar_pendientes(len(pila), i)
            if not pila:
                continue
            _, j, bloque = pila.pop()
            if valor == ")":
                parejas[i] = j
            if bloque is not None:
                bloque.fin = lineas.de(pos)
                if bloque.tipo != "anonima" or bloque.fin - bloque.inicio + 1 >= LARGO_MINIMO_ANONIMA:
                    bloques.append(bloque)
            continue
        if valor in (";", ","):
            cerrar_pendientes(len(pila), i)
            continue
        if valor == "=>":
            info = funcion_de_flecha(fichas, i, parejas, pila)
            if not info:
                continue
            if es(fichas, i + 1, "{"):
                flecha_con_cuerpo = (i + 1, info)
            elif info[0] == "funcion":
                pendientes.append((len(pila), Bloque(info[0], info[1], lineas.de(info[2]), padre=padre_en_pila(pila))))
    cerrar_pendientes(0, len(fichas))
    return bloques


def reglas_css(texto, desde, hasta, lineas):
    reglas = []
    pila = []
    selector_desde = desde
    pos = desde
    while pos < hasta:
        c = texto[pos]
        if c == "/" and texto.startswith("/*", pos):
            fin = texto.find("*/", pos + 2, hasta)
            pos = hasta if fin < 0 else fin + 2
            continue
        if c in "\"'":
            fin = pos + 1
            while fin < hasta and texto[fin] != c and texto[fin] != "\n":
                fin += 2 if texto[fin] == "\\" else 1
            pos = fin + 1
            continue
        if c == "{":
            selector = " ".join(re.sub(r"/\*[\s\S]*?\*/", " ", texto[selector_desde:pos]).split())
            bloque = Bloque("regla", selector, lineas.de(pos), padre=pila[-1] if pila else None)
            pila.append(bloque)
            selector_desde = pos + 1
        elif c == "}":
            if pila:
                bloque = pila.pop()
                bloque.fin = lineas.de(pos)
                reglas.append(bloque)
            selector_desde = pos + 1
        elif c == ";":
            selector_desde = pos + 1
        pos += 1
    return reglas


def mapa_html(texto, lineas):
    bloques = []
    extra = []
    ids = []
    afuera = []
    cursor = 0
    for m in ETIQUETA.finditer(texto):
        if m.start() < cursor:
            continue
        etiqueta = m.group(1).lower()
        cierre = re.compile(f"</{etiqueta}\\s*>", re.I).search(texto, m.end())
        fin = cierre.start() if cierre else len(texto)
        afuera.append((cursor, m.start()))
        contenedor = Bloque(etiqueta, f"<{etiqueta}>", lineas.de(m.start()), lineas.de(cierre.end() - 1 if cierre else fin))
        bloques.append(contenedor)
        if etiqueta == "script":
            for b in estructura_js(texto, m.end(), fin, lineas):
                if b.padre is None:
                    b.padre = contenedor
                bloques.append(b)
        else:
            for b in reglas_css(texto, m.end(), fin, lineas):
                if b.padre is None:
                    b.padre = contenedor
                extra.append(b)
        cursor = cierre.end() if cierre else len(texto)
    afuera.append((cursor, len(texto)))
    for desde, hasta in afuera:
        for m in ID_HTML.finditer(texto, desde, hasta):
            ids.append(Bloque("id", m.group(1), lineas.de(m.start(1)), lineas.de(m.start(1))))
    return bloques, extra, ids


def mapa_py(texto):
    try:
        arbol = ast.parse(texto)
    except SyntaxError:
        return mapa_py_por_sangria(texto)
    bloques = []

    def recorrer(nodo, padre):
        for hijo in ast.iter_child_nodes(nodo):
            if isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                inicio = min([hijo.lineno] + [d.lineno for d in hijo.decorator_list])
                if isinstance(hijo, ast.ClassDef):
                    tipo = "clase"
                else:
                    tipo = "metodo" if padre is not None and padre.tipo == "clase" else "funcion"
                bloque = Bloque(tipo, hijo.name, inicio, hijo.end_lineno, padre)
                bloques.append(bloque)
                recorrer(hijo, bloque)
            else:
                recorrer(hijo, padre)

    recorrer(arbol, None)
    return bloques


def mapa_py_por_sangria(texto):
    renglones = texto.splitlines()
    abiertos = []
    bloques = []

    def cerrar_hasta(sangria, ultimo):
        while abiertos and abiertos[-1][0] >= sangria:
            _, bloque = abiertos.pop()
            bloque.fin = max(bloque.inicio, ultimo)
            bloques.append(bloque)

    ultimo_con_texto = 0
    for n, renglon in enumerate(renglones, 1):
        limpio = renglon.strip()
        if not limpio or limpio.startswith("#"):
            continue
        sangria = len(renglon) - len(renglon.lstrip())
        cerrar_hasta(sangria, ultimo_con_texto)
        m = DEF_PY.match(renglon)
        if m:
            padre = abiertos[-1][1] if abiertos else None
            tipo = "clase" if m.group(2) == "class" else ("metodo" if padre is not None and padre.tipo == "clase" else "funcion")
            abiertos.append((sangria, Bloque(tipo, m.group(3), n, padre=padre)))
        ultimo_con_texto = n
    cerrar_hasta(-1, ultimo_con_texto)
    return bloques


def nivel(bloque):
    n = 0
    padre = bloque.padre
    while padre is not None:
        if padre.tipo in ("funcion", "metodo", "anonima", "clase"):
            n += 1
        padre = padre.padre
    return n


def es_interna(bloque):
    padre = bloque.padre
    while padre is not None:
        if padre.tipo in ("funcion", "metodo", "anonima") and (padre.fin or padre.inicio) - padre.inicio + 1 < FUNCION_GRANDE:
            return True
        padre = padre.padre
    return False


def rango(bloque):
    if bloque.fin is None or bloque.fin == bloque.inicio:
        return str(bloque.inicio)
    return f"{bloque.inicio}-{bloque.fin}"


def etiqueta(bloque):
    if bloque.tipo == "clase":
        return f"class {bloque.nombre}"
    if bloque.tipo == "anonima":
        return f"↳ {bloque.nombre}"
    if bloque.tipo == "id":
        return f"#{bloque.nombre}"
    return bloque.nombre


def renglon(bloque, sangria, cola=""):
    return f'  {rango(bloque).ljust(ANCHO_RANGO)}{"  " * sangria}{etiqueta(bloque)}{cola}'


def camino(bloque):
    partes = []
    padre = bloque.padre
    while padre is not None:
        if padre.tipo in ("funcion", "metodo", "anonima", "clase"):
            partes.append(padre.nombre)
        padre = padre.padre
    return " < ".join(partes)


def resolver(ruta_texto):
    ruta = Path(ruta_texto)
    if ruta.is_file():
        return ruta
    otra = CARPETA / ruta_texto
    if otra.is_file():
        return otra
    return None


def armar(ruta):
    texto = ruta.read_bytes().decode("utf-8-sig", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    lineas = Lineas(texto)
    extension = ruta.suffix.lower()
    extra = []
    ids = []
    if extension in EXTENSIONES_HTML:
        bloques, extra, ids = mapa_html(texto, lineas)
    elif extension in EXTENSIONES_JS:
        bloques = estructura_js(texto, 0, len(texto), lineas)
    elif extension in EXTENSIONES_CSS:
        bloques = []
        extra = reglas_css(texto, 0, len(texto), lineas)
    elif extension in EXTENSIONES_PY:
        bloques = mapa_py(texto)
    else:
        return None
    bloques.sort(key=orden_de_bloque)
    extra.sort(key=orden_de_bloque)
    return texto, bloques, extra, ids


def orden_de_bloque(bloque):
    return bloque.inicio, -(bloque.fin or bloque.inicio)


def contenedores(texto, bloques, extra):
    total = texto.count("\n") + 1
    dueno = [None] * (total + 2)
    for b in sorted(bloques + extra, key=orden_de_bloque):
        for n in range(b.inicio, min(b.fin or b.inicio, total) + 1):
            dueno[n] = b
    return dueno


def listar_todo(bloques, extra, ids, con_internas):
    salida = []
    contenedoras = [b for b in bloques if b.tipo in ("script", "style")]
    funciones = [b for b in bloques if b.tipo not in ("script", "style")]
    if contenedoras:
        salida.append("Bloques")
        for b in contenedoras:
            reglas = sum(1 for r in extra if r.padre is b)
            propias = sum(1 for f in funciones if f.inicio >= b.inicio and (f.fin or f.inicio) <= (b.fin or b.inicio))
            detalle = f"  {miles(propias)} funciones" if b.tipo == "script" and propias else ""
            detalle = f"  {miles(reglas)} reglas" if b.tipo == "style" and reglas else detalle
            salida.append(renglon(b, 0, detalle))
    if funciones:
        internas = {}
        for b in funciones:
            if es_interna(b):
                padre = b.padre
                while padre is not None and (es_interna(padre) or padre.tipo not in ("funcion", "metodo", "anonima", "clase")):
                    padre = padre.padre
                if padre is not None:
                    internas[id(padre)] = internas.get(id(padre), 0) + 1
        visibles = funciones if con_internas else [b for b in funciones if not es_interna(b)]
        titulo = ("Funciones" if con_internas
                  else f"Funciones (las internas de las de menos de {FUNCION_GRANDE} líneas, solo con --todo)")
        salida.append(titulo)
        for b in visibles:
            cola = ""
            if not con_internas and internas.get(id(b)):
                cola = f"  (+{internas[id(b)]} internas)"
            salida.append(renglon(b, nivel(b), cola))
    if ids:
        salida.append(f"ids del HTML ({len(ids)})")
        fila = "  "
        for b in ids:
            pedazo = f"#{b.nombre} {b.inicio}"
            if len(fila) + len(pedazo) + 3 > 110:
                salida.append(fila.rstrip())
                fila = "  "
            fila += f"{pedazo}   "
        salida.append(fila.rstrip())
    if not contenedoras and not funciones and extra:
        salida.append("Reglas")
        for b in extra:
            salida.append(renglon(b, 0))
    return salida


def filtrar(texto, bloques, extra, ids, palabra, afuera):
    buscada = sin_marcas(palabra)
    salida = []
    por_nombre = [b for b in bloques + extra + ids if buscada in sin_marcas(b.nombre)]
    dueno = contenedores(texto, bloques, extra)
    apariciones = {}
    sueltas = []
    for n, linea in enumerate(texto.split("\n"), 1):
        if buscada in sin_marcas(linea):
            b = dueno[n] if n < len(dueno) else None
            if b is None:
                sueltas.append(n)
            else:
                apariciones.setdefault(id(b), (b, []))[1].append(n)

    def lineas_de(numeros):
        if not numeros:
            return ""
        mostradas = ", ".join(str(x) for x in numeros[:LINEAS_POR_GRUPO])
        resto = len(numeros) - LINEAS_POR_GRUPO
        mas = f" y {resto} más" if resto > 0 else ""
        return f"  [{mostradas}{mas}]"

    def detalle(b):
        dentro = camino(b)
        return ("  en " + dentro if dentro else "") + lineas_de(apariciones.get(id(b), (b, []))[1])

    if por_nombre:
        salida.append(f"Por nombre ({len(por_nombre)})")
        for b in sorted(por_nombre, key=lambda b: b.inicio)[:GRUPOS_MAXIMOS]:
            salida.append(renglon(b, 0, detalle(b)))
        if len(por_nombre) > GRUPOS_MAXIMOS:
            salida.append(f"  y {len(por_nombre) - GRUPOS_MAXIMOS} más")
    ya = {id(b) for b in por_nombre}
    grupos = [g for k, g in apariciones.items() if k not in ya]
    grupos.sort(key=lambda g: g[0].inicio)
    total_lineas = sum(len(g[1]) for g in grupos) + len(sueltas)
    if grupos or sueltas:
        lugares = len(grupos) + (1 if sueltas else 0)
        salida.append("Por contenido (" + cantidad(total_lineas, "línea", "líneas") + " en "
                      + cantidad(lugares, "lugar", "lugares") + ")")
        for b, numeros in grupos[:GRUPOS_MAXIMOS]:
            salida.append(renglon(b, 0, detalle(b)))
        if len(grupos) > GRUPOS_MAXIMOS:
            salida.append(f"  y {len(grupos) - GRUPOS_MAXIMOS} lugares más")
        if sueltas:
            salida.append(f"  {afuera.ljust(ANCHO_RANGO)}{lineas_de(sueltas)}")
    if not salida:
        salida.append(f"Nada nombra ni contiene «{palabra}».")
    return salida


def main(argumentos, con_internas=False):
    if not argumentos:
        import configuracion
        print(f"Uso: {configuracion.comando()} --mapa ARCHIVO [palabra]")
        return 1
    comienzo = time.perf_counter()
    ruta = resolver(argumentos[0])
    if ruta is None:
        print(f"No encuentro {argumentos[0]}")
        return 1
    armado = armar(ruta)
    if armado is None:
        print(f"El mapa entiende .html, .js, .css y .py; {ruta.name} no es ninguno.")
        return 1
    texto, bloques, extra, ids = armado
    palabra = " ".join(argumentos[1:]).strip()
    if palabra:
        afuera = "HTML" if ruta.suffix.lower() in EXTENSIONES_HTML else "fuera de funciones"
        cuerpo = filtrar(texto, bloques, extra, ids, palabra, afuera)
    else:
        cuerpo = listar_todo(bloques, extra, ids, con_internas)
    funciones = sum(1 for b in bloques if b.tipo not in ("script", "style"))
    milisegundos = (time.perf_counter() - comienzo) * 1000
    print(ruta.name + " · " + miles(texto.count("\n") + (0 if texto.endswith("\n") else 1)) + " líneas · "
          + miles(funciones) + " funciones · " + format(milisegundos, ".0f") + " ms")
    for linea in cuerpo:
        print(linea)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    todo = "--todo" in sys.argv[1:]
    sys.exit(main([a for a in sys.argv[1:] if a != "--todo"], todo))
