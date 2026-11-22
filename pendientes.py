import bisect
import datetime
import os
import re
from collections import Counter
from pathlib import Path

import cerebro as nucleo
from textos import cantidad, detalle, recortar, sin_wiki, tapar_cercos

VIEJO = 14
LARGO = 170
CORTO = 45
POR_CLASE = 8
CERCA = 1
TODOS = ("todos", "todo", "all")
RE_CORTE = re.compile(r"(?<=[.;!?])[ \t]+|\n[ \t]*\n|\n(?=[ \t]*(?:[-*+]|\d{1,3}[.)])[ \t])|\n(?=#{1,6}[ \t])")
RE_COMIENZO = re.compile(r"[\s\-*+#>\d.)\[\]]*")
RE_TACHADO = re.compile(r"~~.*?~~", re.S)
RE_CERRADO = re.compile(r"\bhech[oa]s?\b|\bresuelt[oa]s?\b|\barreglad[oa]s?\b|\blist[oa]s?\b|✅|\bdone\b|\bfixed\b|\bsolved\b", re.I)
SIN_FALTA = "".join(f"(?<!{antes} )(?<!{antes.capitalize()} )" for antes in (
    "hace", "hacen", "hacía", "hacia", "hizo", "haga", "hagan", "sin", "no", "la", "por", "una", "ni", "nunca", "le",
    "les", "me", "nos", "si", "cuando"))
RE_PROBADO = re.compile(r"\bprobad[oa]s?\b|\bverificad[oa]s?\b|\bse (?:revisaron|arreglaron|prob[oó])\b", re.I)
ANTES_DE_LA_FRASE = 300
RE_INICIO_DE_ITEM = re.compile(r"\n[ \t]*\n|\n(?=[ \t]*(?:[-*+]|\d{1,3}[.)])[ \t])|\n(?=#{1,6}[ \t])")
RE_RUTA_ABSOLUTA = re.compile(r"(?<![\w/\\])(?:[A-Za-z]:[\\/]|/(?=\w))[^\s`'\"()<>|*?,;«»]*")
CLASES = (
    ("probar", "Falta probar",
     re.compile(r"\bsin probar\b|\bfaltan? (?:solo )?probar\w*|\bnot tested\b|\buntested\b", re.I)),
    ("decidir", "Falta decidir",
     re.compile(r"\b[Ff]altan? (?:solo )?decidir\w*|\b[Ss]in decidir\b|\b[Pp]ara decidir\b"
                r"|\b(?:lo|la|los|las) deciden? [A-ZÁÉÍÓÚ]\w+"
                r"|(?<!cuando )(?<!mientras )(?<!si )\b[Ee]speran? (?:el |la |su |una |las |los )?(?:«dale»|dale\b|OK\b|ok\b"
                r"|visto bueno|decisi[oó]n|decisiones"
                r"|respuesta)|\b[Tt]o be decided\b")),
    ("commit", "Sin commit", re.compile(r"\bsin commit(?:ear|eado|eada|eados|eadas)?\b|\buncommitted\b", re.I)),
    ("hacer", "Falta hacer",
     re.compile(r"(?<![\w«“\"])(?:FALTAN?|PENDIENTES?)\b|\bTODO:|^[ \t]*(?:[-*+]|\d{1,3}[.)])[ \t]+\[ \]|\b[Ss]in empezar\b"
                r"|\b[Pp]endientes?:|\b(?:[Qq]ueda|[Qq]uedan|[Ss]igue|[Ss]iguen) pendientes?\b|"
                + SIN_FALTA + r"\b[Ff]altan?\b(?! de\b)(?! nada\b)", re.M)),
)
NOMBRE = {clave: nombre for clave, nombre, _ in CLASES}


def limpio(texto):
    texto = sin_wiki(texto)
    texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texto)
    texto = re.sub(r"^[ \t]*(?:#{1,6}|[-*+]|\d{1,3}[.)])[ \t]+(?:\[ \][ \t]*)?", "", texto.strip())
    return re.sub(r"\s+", " ", texto.replace("**", "").replace("`", "")).strip()


def frases_de(cuerpo):
    cortes = [0]
    for m in RE_CORTE.finditer(cuerpo):
        cortes.append(m.end())
    cortes.append(len(cuerpo))
    return cortes


def tapado(cuerpo):
    def blanco(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    return RE_TACHADO.sub(blanco, tapar_cercos(cuerpo))


def de_la_nota(nodo, hoy):
    import medico
    import ordenar
    cuerpo = nodo["_cuerpo"]
    visible = tapado(cuerpo)
    cortes = frases_de(cuerpo)
    renglones = ordenar.renglones_de(cuerpo)
    piezas = ordenar.piezas_de(renglones)
    comienzos = [p["desde"] for p in piezas]
    hallados = {}
    for clave, _, patron in CLASES:
        for m in patron.finditer(visible):
            k = bisect.bisect_right(cortes, m.start()) - 1
            if k in hallados:
                continue
            desde, hasta = cortes[k], cortes[min(k + 1, len(cortes) - 1)]
            frase = limpio(visible[desde:hasta])
            if m.group(0).lower() == "para decidir" and not RE_COMIENZO.fullmatch(visible[desde:m.start()]):
                continue
            if clave != "commit" and (RE_PROBADO if clave == "probar" else RE_CERRADO).search(frase):
                hallados[k] = None
                continue
            if len(frase) < CORTO and k > 0 and "\n" not in visible[cortes[k - 1]:desde]:
                frase = f"{limpio(visible[cortes[k - 1]:desde])} {frase}".strip()
            renglon = cuerpo.count("\n", 0, m.start())
            pieza = piezas[bisect.bisect_right(comienzos, renglon) - 1] if comienzos and renglon >= comienzos[0] else None
            fecha = ordenar.fecha_de(frase, hoy) or (ordenar.fecha_de(ordenar.limpiar(pieza["titulo"]), hoy) if pieza else None)
            hallados[k] = {"clase": clave, "nota": nodo["id"], "ruta": nodo["ruta"], "titulo": nodo["titulo"] or nodo["id"],
                           "linea": medico.linea_en(nodo, m.start()), "texto": recortar(frase, LARGO), "fecha": fecha}
            if clave == "commit":
                hallados[k]["_frase"] = visible[desde:hasta]
                hallados[k]["_antes"] = visible[inicio_del_item(visible, desde):desde]
    return [hallados[k] for k in sorted(hallados) if hallados[k]]


def juntar(cerebro, hoy=None):
    hoy = hoy or datetime.date.today()
    salida = []
    for nodo in cerebro.nodos:
        if not cerebro.fuente_de.get(nodo["id"], {}).get("memoria") or nodo["tipo"] == "indice" or nucleo.es_archivo(nodo):
            continue
        for p in de_la_nota(nodo, hoy):
            p["dias"] = (hoy - p["fecha"]).days if p["fecha"] else None
            salida.append(p)
    return salida


def marcar_resueltos(cerebro, lista):
    import medico
    try:
        avisos = medico.regla_resuelto(cerebro)
    except Exception:
        return None
    lineas = {}
    for h in avisos:
        if h["regla"] == "yaResuelto" and h["linea"]:
            lineas.setdefault(h["nota"], []).append(h["linea"])
    for p in lista:
        p["quizas"] = any(abs(p["linea"] - n) <= CERCA for n in lineas.get(p["nota"], ()))
    return sum(1 for p in lista if p["quizas"])


def inicio_del_item(texto, desde):
    ventana = max(0, desde - ANTES_DE_LA_FRASE)
    return max((m.end() for m in RE_INICIO_DE_ITEM.finditer(texto, ventana, desde)), default=ventana)


def repo_nombrado(texto, repos):
    rutas = RE_RUTA_ABSOLUTA.findall(texto)
    if not rutas:
        return None
    clave = nucleo.normalizar(rutas[-1].rstrip(".:\\/"))
    return max((r for r in repos if clave == nucleo.normalizar(r) or clave.startswith(nucleo.normalizar(r) + "\\")),
               key=len, default="")


def estado_git(repo):
    import medico
    cambios = medico.correr_git(repo, ["status", "--porcelain"])
    ultimo = (medico.correr_git(repo, ["log", "-1", "--format=%ct"]) or "").strip()
    if cambios is None or not ultimo.isdigit():
        return False, None
    return not cambios.strip(), int(ultimo)


def marcar_commiteados(cerebro, lista, de_nodo, repos=None, estado=None):
    import buscador
    import consultas
    import medico
    repos = medico.repos_conocidos() if repos is None else repos
    estado = estado or estado_git
    clave_de_grupo = {g["id"]: g["clave"] for g in buscador.grupos_base()}
    repo_de_clave = {consultas.clave(r).rstrip("/"): r for r in repos}
    estados = {}
    for p in lista:
        if p["clase"] != "commit":
            continue
        repo = repo_nombrado(p.get("_frase", ""), repos)
        if repo is None:
            repo = repo_nombrado(p.get("_antes", ""), repos)
        if repo is None:
            repo = repo_de_clave.get(clave_de_grupo.get(de_nodo.get(p["nota"])))
        if not repo:
            continue
        if repo not in estados:
            estados[repo] = estado(repo) or (False, None)
        limpio, ultimo = estados[repo]
        desde = datetime.datetime.combine(p["fecha"], datetime.time.min).timestamp() if p["fecha"] else 0
        if limpio and ultimo and ultimo >= desde:
            p["commiteado"] = repo
    return sum(1 for p in lista if p.get("commiteado"))


def elegir(pedido, grupos, de_nodo, cwd):
    import buscador
    import consultas
    pedido = (pedido or "").strip()
    if pedido.lower() in TODOS:
        return None, None
    if pedido:
        norma = pedido.lower()
        hallados = [g for g in grupos if norma in (g["id"].lower(), g["nombre"].lower())] or [
            g for g in grupos if norma in g["nombre"].lower() or norma in g["id"].lower()]
        if len(hallados) != 1:
            return None, (f"no conozco el proyecto «{pedido}»" if not hallados else f"«{pedido}» puede ser más de uno") + (
                ": " + ", ".join(f'«{g["nombre"]}»' for g in grupos) + ", o «todos».")
        return hallados[0], None
    lista = buscador.proyectos_conocidos()
    raiz = buscador.raiz_que_contiene(consultas.clave(cwd), lista)
    if not raiz:
        return None, None
    alias = next(str(p.get("alias") or r.rsplit("/", 1)[-1]).lower() for r, p in lista if r == raiz)
    return next((g for g in grupos if g["id"] == alias), None), None


def renglon_de(p):
    cuando = ""
    if p["fecha"]:
        cuando = f' · {p["fecha"].day}/{p["fecha"].month}' + (f' (hace {p["dias"]} días)' if p["dias"] > VIEJO else "")
    quizas = " · quizás ya está resuelto" if p.get("quizas") else ""
    if p.get("commiteado"):
        quizas += f' · quizás ya está commiteado: {Path(p["commiteado"]).name} no tiene nada sin commit'
    return f'  {Path(p["ruta"]).name}:{p["linea"]}{cuando}{quizas} — {p["texto"]}'


def texto(lista, grupos, de_nodo, elegido, todo=False, resueltos=None, comando=""):
    nombre = {g["id"]: g["nombre"] for g in grupos}
    propios = [p for p in lista if elegido is None or de_nodo.get(p["nota"]) == elegido["id"]]
    donde = f' de «{elegido["nombre"]}»' if elegido else ""
    if not propios:
        lineas = [f"No encontré pendientes anotados{donde}."]
    else:
        viejos = sum(1 for p in propios if p["dias"] is not None and p["dias"] > VIEJO)
        quizas = sum(1 for p in propios if p.get("quizas"))
        commiteados = sum(1 for p in propios if p.get("commiteado"))
        extras = [cantidad(viejos, "con más de", "con más de") + f" {VIEJO} días"] if viejos else []
        extras += [cantidad(quizas, "que quizás ya está resuelto", "que quizás ya están resueltos")] if quizas else []
        extras += [cantidad(commiteados, "que quizás ya está commiteado", "que quizás ya están commiteados")
                   ] if commiteados else []
        lineas = [f'Pendientes anotados{donde}: {len(propios)} en '
                  f'{cantidad(len({p["nota"] for p in propios}), "nota", "notas")}'
                  + (f' ({"; ".join(extras)})' if extras else "") + "."]
        for clave, titulo, _ in CLASES:
            de_clase = sorted((p for p in propios if p["clase"] == clave),
                              key=lambda p: (p["fecha"] is None, p["fecha"] or datetime.date.min, p["ruta"].lower(), p["linea"]))
            if not de_clase:
                continue
            lineas.append(f"{titulo} ({len(de_clase)}):")
            if elegido is None:
                por_grupo = Counter(nombre.get(de_nodo.get(p["nota"]), "Sin proyecto") for p in de_clase)
                lineas.append("  por proyecto: " + ", ".join(f"{n} {c}" for n, c in por_grupo.most_common()))
            for p in de_clase if todo else de_clase[:POR_CLASE]:
                lineas.append(renglon_de(p))
            if not todo and len(de_clase) > POR_CLASE:
                lineas.append(f"  … y {len(de_clase) - POR_CLASE} más (con --todo salen todos)")
    if resueltos is None and propios:
        lineas.append("No pude mirar los commits: no marco los que quizás ya están resueltos.")
    if elegido:
        otros = Counter(nombre.get(de_nodo.get(p["nota"]), "Sin proyecto") for p in lista
                        if de_nodo.get(p["nota"]) != elegido["id"])
        if otros:
            lineas.append("En los otros proyectos: " + ", ".join(f"{n} {c}" for n, c in otros.most_common())
                          + f'. Para verlos: {comando} --pendientes "NOMBRE" (o todos).')
    lineas.append("Son frases de las notas que dicen que algo falta, está sin probar, sin decidir o sin commit; las que ya "
                  "dicen «hecho» o están tachadas no salen. La fecha es la que está escrita en la frase o en su título.")
    return lineas


def main(pedido, todo=False):
    import buscador
    import configuracion
    cerebro = nucleo.desde_disco()
    try:
        de_nodo, grupos = buscador.grupos_de_proyecto(cerebro)
    except Exception as error:
        print(f"No pude agrupar las notas por proyecto ({detalle(error)}).")
        return 1
    elegido, error = elegir(pedido, grupos, de_nodo, os.getcwd())
    if error:
        print(f"Error: {error}")
        return 1
    lista = juntar(cerebro)
    resueltos = marcar_resueltos(cerebro, lista)
    marcar_commiteados(cerebro, lista, de_nodo)
    for linea in texto(lista, grupos, de_nodo, elegido, todo, resueltos, configuracion.comando()):
        print(linea)
    return 0
