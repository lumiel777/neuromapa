import re
import subprocess
from collections import Counter
from pathlib import Path

import cerebro as nucleo
import procesos

RE_SIMBOLO = re.compile(r"^(?:(?P<dueno>[A-Za-z_]\w*)\s*(?:\.|::|->))?\s*(?P<nombre>~?[A-Za-z_]\w*)\s*(?:\(\s*\))?$")
EXTENSIONES = ("*.cs", "*.cpp", "*.cc", "*.cxx", "*.c", "*.h", "*.hpp", "*.hh", "*.hxx", "*.inl", "*.java", "*.ts", "*.tsx",
               "*.js", "*.mjs", "*.cjs", "*.kt", "*.kts", "*.go", "*.rs", "*.php", "*.py")
TIPOS_DE_FUNCION = ("funcion", "metodo")
TOPE_ARCHIVOS = 400
TOPE_COINCIDENCIAS = 20000
MOSTRAR_LLAMADAS = 15
MOSTRAR_NOTAS = 12
ESPERA_GIT = 60
PROPIOS = (None, "this", "self", "base", "super", "parent", "static")
NO_SON_LLAMADAS = {"if", "for", "foreach", "while", "switch", "catch", "return", "new", "typeof", "sizeof", "nameof"}


def es_simbolo(consulta):
    q = consulta.strip().strip("`'\"").strip()
    m = RE_SIMBOLO.match(q)
    if not m or m.group("nombre").lower() in NO_SON_LLAMADAS:
        return None
    return m.group("dueno"), m.group("nombre")


def raices():
    import medico
    vistas = []
    for proyecto in medico.CODIGO:
        for raiz in proyecto["codigo"]:
            ruta = raiz["ruta"]
            if Path(ruta).is_dir() and not nucleo.es_de_red(ruta) and ruta not in [r for _, r in vistas]:
                vistas.append((proyecto["alias"], ruta))
    return vistas


def coincidencias(raiz, nombre):
    try:
        r = procesos.correr(["git", "-C", raiz, "grep", "--untracked", "-n", "-I", "-w", "-F", "-e", nombre, "--",
                             *EXTENSIONES],
                            ESPERA_GIT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode not in (0, 1):
        return None
    salida = {}
    for renglon in r.stdout.splitlines()[:TOPE_COINCIDENCIAS]:
        partes = renglon.split(":", 2)
        if len(partes) == 3 and partes[1].isdigit():
            salida.setdefault(str(Path(raiz) / partes[0]), []).append((int(partes[1]), partes[2]))
    return {ruta: renglones for ruta, renglones in salida.items() if not descartado(ruta)}


def descartado(ruta):
    import medico
    carpetas = Path(ruta).parts[:-1]
    return nucleo.excluido(ruta) or any(nucleo.carpeta_podada(c) or c.lower() in medico.PODA_CODIGO for c in carpetas)


def dueno_de(bloque):
    padre = bloque.padre
    while padre is not None and padre.tipo != "clase":
        padre = padre.padre
    return padre.nombre if padre is not None else ""


def nombre_corto(nombre):
    return re.split(r"::|\.", nombre)[-1]


def camino(bloque):
    partes = [bloque.nombre]
    padre = bloque.padre
    while padre is not None:
        partes.append(padre.nombre)
        padre = padre.padre
    return ".".join(reversed(partes))


def mas_adentro(bloques, linea):
    dentro = [b for b in bloques if b.tipo in TIPOS_DE_FUNCION and b.inicio <= linea <= (b.fin or b.inicio)]
    return min(dentro, key=lambda b: (b.fin or b.inicio) - b.inicio) if dentro else None


def buscar(dueno, nombre):
    import mapa
    llamada = re.compile(r"(?:(?P<quien>[A-Za-z_]\w*)\s*(?:\.|::|->)\s*)?(?<![\w])" + re.escape(nombre)
                         + r"\s*(?:<[^()<>]*>)?\s*\(")
    definiciones, llamadas, sin_git, recortado = [], [], [], False
    mirados = 0
    for alias, raiz in raices():
        hallados = coincidencias(raiz, nombre)
        if hallados is None:
            sin_git.append(raiz)
            continue
        for ruta, renglones in hallados.items():
            if mirados >= TOPE_ARCHIVOS:
                recortado = True
                break
            mirados += 1
            armado = mapa.armar(Path(ruta)) if mapa.archivo_local(Path(ruta)) else None
            if armado is None:
                continue
            bloques = armado[1]
            propias = [b for b in bloques if nombre_corto(b.nombre) == nombre
                       and (not dueno or dueno == dueno_de_funcion(b))]
            for b in propias:
                definiciones.append((ruta, b, alias))
            inicios = {b.inicio for b in propias}
            for numero, texto in renglones:
                if numero in inicios:
                    continue
                for m in llamada.finditer(texto):
                    quien = m.group("quien")
                    llamadas.append((ruta, numero, quien, mas_adentro(bloques, numero), alias))
                    break
    return definiciones, llamadas, sin_git, recortado


def texto_simbolo(cerebro, consulta):
    dueno, nombre = es_simbolo(consulta) or (None, None)
    if not nombre:
        return None
    definiciones, llamadas, sin_git, recortado = buscar(dueno, nombre)
    notas = notas_que_nombran(cerebro, dueno, nombre)
    if not definiciones and not notas:
        return None
    pedido = f"{dueno}.{nombre}" if dueno else nombre
    lineas = [f"«{pedido}» como función o clase del código:"]
    if definiciones:
        lineas.append(f"Dónde está ({len(definiciones)}):")
        for ruta, b, alias in definiciones[:MOSTRAR_LLAMADAS]:
            lineas.append(f"  {ruta}:{b.inicio}-{b.fin or b.inicio}  {b.palabra + ' ' if b.tipo == 'clase' else ''}"
                          f"{camino(b)}  ({alias})")
    else:
        lineas.append("No la encontré definida en el código de los proyectos (solo en las notas).")
    funciones = [b for _, b, _ in definiciones if b.tipo in TIPOS_DE_FUNCION]
    duenos = {dueno_de_funcion(b) for b in funciones}
    probables = []
    if any(b.tipo == "clase" for _, b, _ in definiciones):
        seguras, titulo = llamadas, "Dónde se usa (se crea o se llama)"
    elif len(duenos) > 1 and not dueno:
        seguras, titulo = [], ""
        nombres = ", ".join(sorted(d or "sueltas" for d in duenos)[:6])
        lineas.append(f"Hay {len(duenos)} con ese nombre en clases distintas ({nombres}): pedí Clase.Metodo para ver quién "
                      "llama a cuál.")
    else:
        propio = dueno if dueno is not None else next(iter(duenos), "")
        if propio:
            seguras = [c for c in llamadas if c[2] == propio
                       or (c[2] in PROPIOS and c[3] is not None and dueno_de_funcion(c[3]) == propio)]
            probables = [c for c in llamadas if c not in seguras and c[2] is not None and c[2] not in PROPIOS
                         and len(duenos) == 1]
        else:
            seguras = [c for c in llamadas if c[2] is None]
        titulo = "Quién la llama"
    if titulo:
        if seguras:
            lineas += lista_de_llamadas(f"{titulo} (lo seguro", seguras)
        elif definiciones:
            lineas.append(f"{titulo}: ninguna llamada segura en el código de los proyectos.")
        if probables:
            lineas += lista_de_llamadas("Probables, desde otra variable (x." + nombre + "(…); sin saber el tipo, puede ser "
                                        "otra clase con un método igual", probables, MOSTRAR_LLAMADAS // 3)
    if recortado:
        lineas.append(f"(Miré los primeros {TOPE_ARCHIVOS} archivos donde aparece el nombre: es muy común.)")
    if sin_git:
        lineas.append(f"(No busqué en {', '.join(sin_git)}: no es un repositorio git.)")
    lineas.append(f"Notas que la nombran ({len(notas)}):" if notas else "Ninguna nota la nombra.")
    for nodo, linea, renglon in notas[:MOSTRAR_NOTAS]:
        lineas.append(f'  {nodo["ruta"]}:{linea} — {nucleo.recortar(nodo["titulo"], 60)}')
        lineas.append(f"      {renglon}")
    if len(notas) > MOSTRAR_NOTAS:
        lineas.append(f"  … y {len(notas) - MOSTRAR_NOTAS} más")
    return lineas


def dueno_de_funcion(bloque):
    propio = dueno_de(bloque)
    if propio:
        return propio
    partes = re.split(r"::|\.", bloque.nombre)
    return partes[-2] if len(partes) > 1 else ""


def lista_de_llamadas(titulo, llamadas, tope=MOSTRAR_LLAMADAS):
    por_lugar = Counter((ruta, camino(f) if f else "(fuera de una función)", f.inicio if f else numero)
                        for ruta, numero, _, f, _ in llamadas)
    archivos = len({ruta for ruta, *_ in llamadas})
    salida = [f"{titulo}: {len(llamadas)} {'llamada' if len(llamadas) == 1 else 'llamadas'} desde {len(por_lugar)} "
              f"{'lugar' if len(por_lugar) == 1 else 'lugares'} en {archivos} {'archivo' if archivos == 1 else 'archivos'}):"]
    for (ruta, quien, linea), veces in por_lugar.most_common(tope):
        salida.append(f"  {ruta}:{linea}  en {quien}" + (f"  (×{veces})" if veces > 1 else ""))
    if len(por_lugar) > tope:
        salida.append(f"  … y {len(por_lugar) - tope} lugares más")
    return salida


def notas_que_nombran(cerebro, dueno, nombre):
    if dueno:
        patron = re.compile(rf"(?<![\w]){re.escape(dueno)}\s*(?:\.|::|->)\s*{re.escape(nombre)}(?![\w])")
    else:
        patron = re.compile(rf"`{re.escape(nombre)}(?:\(\))?`|(?<![\w.]){re.escape(nombre)}\s*\(")
    salida = []
    for nodo in cerebro.nodos:
        m = patron.search(nodo["_cuerpo"])
        if not m:
            continue
        linea = nodo.get("_desfase", 0) + nodo["_cuerpo"].count("\n", 0, m.start()) + 1
        salida.append((nodo, linea, nucleo.fragmento(nodo["_cuerpo"], m.start(), m.end(), 110)))
    return salida
