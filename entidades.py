import bisect
import re
import sys
import threading
from collections import Counter
from pathlib import Path

import cerebro as nucleo
import medico

EXTENSIONES = ("cs", "py", "ps1", "ini", "txt", "sql", "ts", "dll", "exe")
RE_EXTENSION = re.compile(f'\\.(?:{"|".join(EXTENSIONES)})(?![\\w\\-]|\\.\\w)', re.I)
PREFIJOS_TABLA = f'(?:{"|".join(re.escape(p) for p in nucleo.CONFIG["prefijos_tabla"])})'
NUNCA = r"(?!)"
RE_TABLA = re.compile(f"`({PREFIJOS_TABLA}_[a-z0-9_]+)`" if nucleo.CONFIG["prefijos_tabla"] else NUNCA)
RE_LETRA = re.compile(r"[^\W\d_]")
RE_UNIDAD = re.compile(r"^[A-Za-z]:$")
RE_SEPARADORES = re.compile(r"[\\/]+")
RE_HEX = re.compile(r"^[0-9a-f]{7,40}$")
RE_TABLA_SUELTA = re.compile(f"^{PREFIJOS_TABLA}_[a-z0-9_]+$" if nucleo.CONFIG["prefijos_tabla"] else NUNCA)
CORTES = set(" \t\n`'\"<>|*?()[]{},;=")
NOMBRE_CORTADO = "%)"
TIPOS = ("archivos", "commits", "tablas")
TOPE_RARA = 3
DOMINIO = 4
MINIMO_COMPARTIDAS = 2
MOSTRAR_COMPARTIDAS = 5
NOMBRES_LEEME = {"leeme.md", "readme.md"}
GENERICOS = {"program.cs", "assemblyinfo.cs", "settings.designer.cs", "resources.designer.cs", "main.py", "__init__.py",
             "setup.py", "test.py", "setup.exe", "readme.txt", "log.txt", "requirements.txt", "config.ini", "settings.ini",
             "desktop.ini", "index.ts", "types.ts", "utils.ts", "route.ts", "page.ts", "layout.ts"}
SIN_PROYECTO = ""
LINEAS_CONSOLA = 40
CON_RENGLON = 12
ANCHO_RENGLON = 110
PROYECTOS = nucleo.CONFIG["proyectos"]
RAIZ = {p["alias"]: nucleo.normalizar(p["raiz"]) for p in PROYECTOS}
PERMITIDOS = {extension: {RAIZ[p["alias"]] for p in PROYECTOS if extension in p["extensiones"]}
              for extension in {e for p in PROYECTOS for e in p["extensiones"]}}
REMITE = {RAIZ[p["alias"]]: RAIZ[p["remite_a"]] for p in PROYECTOS if p.get("remite_a")}
SECCIONES = [(p["marca_seccion"], RAIZ[p["alias"]]) for p in PROYECTOS if p.get("marca_seccion")]
PREFIJOS = [(p["prefijo_carpeta"].lower(), RAIZ[p["alias"]]) for p in PROYECTOS if p.get("prefijo_carpeta")]


def encajar(contexto, permitidos):
    if permitidos is None or contexto in permitidos:
        return contexto
    if len(permitidos) == 1:
        return next(iter(permitidos))
    if REMITE.get(contexto) in permitidos:
        return REMITE[contexto]
    return None


def por_prefijo(componentes):
    for prefijo, raiz in PREFIJOS:
        if any(c.lower().startswith(prefijo) for c in componentes):
            return raiz
    return None


def alias(raiz):
    if not raiz:
        return SIN_PROYECTO
    clave = nucleo.normalizar(raiz)
    return nucleo.ALIAS_PROYECTO.get(clave) or Path(str(raiz)).name


def lineas_de(nodo, posiciones):
    cuerpo = nodo["_cuerpo"]
    desfase = nodo.get("_desfase", 0)
    salida = {}
    previa, cuenta = 0, 0
    for posicion in sorted(set(posiciones)):
        cuenta += cuerpo.count("\n", previa, posicion)
        previa = posicion
        salida[posicion] = desfase + cuenta + 1
    return salida


class Registro:
    def __init__(self):
        self.menciones = {}
        self.mostrado = {}

    def anotar(self, tipo, clave, mostrado, proyecto, origen, posicion):
        llave = (tipo, clave, proyecto)
        notas = self.menciones.setdefault(llave, {})
        if origen not in notas or posicion < notas[origen]:
            notas[origen] = posicion
        self.mostrado.setdefault(llave, Counter())[mostrado] += 1

    def mover(self, desde, hacia):
        for origen, posicion in self.menciones.pop(desde).items():
            notas = self.menciones.setdefault(hacia, {})
            if origen not in notas or posicion < notas[origen]:
                notas[origen] = posicion
        self.mostrado.setdefault(hacia, Counter()).update(self.mostrado.pop(desde))

    def nombre(self, llave):
        contador = self.mostrado.get(llave)
        return contador.most_common(1)[0][0] if contador else llave[1]


class Estado:
    def __init__(self, cerebro):
        self.cerebro = cerebro
        self.registro = Registro()
        self.hashes = set()
        self.commits = {}
        self.consultados = []
        self.hilo = None
        self.carpetas = 0
        self.secciones_de_nota = {}
        self.raiz_de_seccion = {}
        self.de_la_nota = {}
        self.leemes = []
        self.leeme_exacto = {}
        for nodo in cerebro.nodos:
            if Path(nodo["ruta"]).name.lower() in NOMBRES_LEEME:
                carpeta = cerebro.carpeta_de[nodo["id"]]
                self.leemes.append((carpeta, nodo["id"]))
                self.leeme_exacto[carpeta] = nodo["id"]

    def leeme_de(self, componentes, absoluta, proyecto):
        if absoluta:
            return self.leeme_exacto.get(nucleo.normalizar("\\".join(componentes)))
        sufijo = "\\" + "\\".join(c.lower() for c in componentes)
        candidatos = [i for carpeta, i in self.leemes if carpeta.endswith(sufijo)]
        if len(candidatos) > 1 and proyecto:
            base = f"{nucleo.normalizar(proyecto)}\\"
            candidatos = [i for i in candidatos if self.cerebro.carpeta_de[i].startswith(base)]
        return candidatos[0] if len(candidatos) == 1 else None

    def seccion_de(self, origen, posicion):
        if origen not in self.secciones_de_nota:
            cuerpo = self.cerebro.por_id[origen]["_cuerpo"]
            self.secciones_de_nota[origen] = [(marca, raiz) for marca, raiz in SECCIONES if marca.search(cuerpo)]
        if not self.secciones_de_nota[origen]:
            return None
        comienzos, secciones = self.cerebro.secciones_con_posicion(origen)
        i = bisect.bisect_right(comienzos, posicion) - 1
        if i < 0:
            return None
        if (origen, i) not in self.raiz_de_seccion:
            titulos = [secciones[i]["titulo"]] if secciones[i]["nivel"] > 1 else []
            nivel = secciones[i]["nivel"]
            for s in reversed(secciones[:i]):
                if 1 < s["nivel"] < nivel:
                    titulos.append(s["titulo"])
                    nivel = s["nivel"]
            self.raiz_de_seccion[(origen, i)] = next((raiz for marca, raiz in self.secciones_de_nota[origen]
                                                      if any(marca.search(t) for t in titulos)), None)
        return self.raiz_de_seccion[(origen, i)]

    def proyecto_de_mencion(self, origen, cuerpo, inicio, extension):
        cerebro = self.cerebro
        permitidos = PERMITIDOS.get(extension)
        a = cuerpo.rfind("\n", 0, inicio) + 1
        b = cuerpo.find("\n", inicio)
        proyecto = nucleo.proyecto_unico(cuerpo[a:] if b < 0 else cuerpo[a:b], permitidos)
        if proyecto:
            return proyecto
        if not cerebro.fuente_de[origen].get("memoria"):
            return encajar(cerebro.proyecto_de.get(origen), permitidos)
        seccion = self.seccion_de(origen, inicio)
        if seccion:
            return encajar(seccion, permitidos)
        if origen not in self.de_la_nota:
            nodo = cerebro.por_id[origen]
            self.de_la_nota[origen] = nucleo.proyecto_unico(f'{nodo["titulo"]}\n{nodo["descripcion"] or ""}')
        contexto = self.de_la_nota[origen]
        if contexto is None:
            contexto = cerebro.proyecto_por_contexto(origen, cuerpo, inicio, None, False)
        return encajar(contexto, permitidos)

    def extraer(self, nodo):
        cerebro = self.cerebro
        origen = nodo["id"]
        cuerpo = nodo["_cuerpo"]
        por_renglon = {}
        for m in RE_EXTENSION.finditer(cuerpo):
            inicio = m.start()
            while inicio > 0 and (cuerpo[inicio - 1].isalnum() or cuerpo[inicio - 1] in "_.-"):
                inicio -= 1
            while inicio < m.start() and not (cuerpo[inicio].isalnum() or cuerpo[inicio] == "_"):
                inicio += 1
            if not RE_LETRA.search(cuerpo, inicio, m.start()) or (inicio > 0 and cuerpo[inicio - 1] in NOMBRE_CORTADO):
                continue
            nombre = cuerpo[inicio:m.end()]
            i = inicio
            while i > 0 and cuerpo[i - 1] not in CORTES:
                i -= 1
            trozo = cuerpo[i:inicio]
            if "://" in trozo or trozo.lower().startswith("www."):
                continue
            componentes = [c for c in RE_SEPARADORES.split(trozo) if c and c not in (".", "..")]
            absoluta = bool(componentes) and RE_UNIDAD.match(componentes[0]) is not None
            proyecto = None
            if absoluta:
                proyecto = nucleo.proyecto_de_ruta(nucleo.normalizar(trozo + nombre))
            else:
                proyecto = por_prefijo(componentes)
            if proyecto is None:
                extension = nombre[nombre.rfind(".") + 1:].lower()
                llave = (cuerpo.rfind("\n", 0, inicio), extension)
                if llave not in por_renglon:
                    por_renglon[llave] = self.proyecto_de_mencion(origen, cuerpo, inicio, extension)
                proyecto = por_renglon[llave]
            self.registro.anotar("archivos", nombre.lower(), nombre, alias(proyecto), origen, inicio)
            if componentes and (not absoluta or len(componentes) > 1):
                leeme = self.leeme_de(componentes, absoluta, proyecto)
                if leeme and leeme != origen:
                    antes = cerebro.fuertes.get((origen, leeme))
                    cerebro.agregar(origen, leeme, "carpeta", f"cita {trozo}{nombre}")
                    if antes is None and (origen, leeme) in cerebro.fuertes:
                        self.carpetas += 1
        for m in RE_TABLA.finditer(cuerpo):
            valor = m.group(1)
            self.registro.anotar("tablas", valor.lower(), valor, SIN_PROYECTO, origen, m.start(1))
        citas = medico.extraer_commits(cuerpo)
        cerebro.citas_commits[origen] = citas
        for valor, inicio, _ in citas:
            self.hashes.add(valor)
            self.registro.anotar("commits", valor, valor, SIN_PROYECTO, origen, inicio)

    def preparar(self):
        for nodo in self.cerebro.nodos:
            self.extraer(nodo)
        self.adoptar_proyectos()
        if self.hashes:
            self.hilo = threading.Thread(target=self.consultar, daemon=True)
            self.hilo.start()
        return self

    def consultar(self):
        try:
            self.commits, self.consultados = medico.consultar_commits(self.hashes)
        except Exception:
            self.commits, self.consultados = {}, []

    def adoptar_proyectos(self):
        conocidos = {}
        for (tipo, clave, proyecto), notas in self.registro.menciones.items():
            if tipo == "archivos" and proyecto != SIN_PROYECTO:
                conocidos.setdefault(clave, Counter())[proyecto] += len(notas)
        for llave in [k for k in self.registro.menciones if k[0] == "archivos" and k[2] == SIN_PROYECTO]:
            cuentas = conocidos.get(llave[1])
            if not cuentas:
                continue
            proyecto, veces = cuentas.most_common(1)[0]
            if veces >= DOMINIO * (sum(cuentas.values()) - veces):
                self.registro.mover(llave, ("archivos", llave[1], proyecto))

    def unir_commits(self):
        registro = self.registro
        for llave in [k for k in registro.menciones if k[0] == "commits"]:
            dato = self.commits.get(llave[1])
            if dato and dato.get("sha"):
                destino = ("commits", dato["sha"], SIN_PROYECTO)
                if destino != llave:
                    registro.mover(llave, destino)

    def terminar(self):
        if self.hilo is not None:
            self.hilo.join()
        self.unir_commits()
        cerebro = self.cerebro
        indice = {tipo: [] for tipo in TIPOS}
        posiciones = {}
        for llave, notas in self.registro.menciones.items():
            for origen, posicion in notas.items():
                posiciones.setdefault(origen, []).append(posicion)
        lineas = {origen: lineas_de(cerebro.por_id[origen], lista) for origen, lista in posiciones.items()}
        por_sha = {}
        for dato in self.commits.values():
            if dato and dato.get("sha"):
                por_sha[dato["sha"]] = dato
        for llave, notas in self.registro.menciones.items():
            tipo, clave, proyecto = llave
            lista = [[origen, lineas[origen][posicion]] for origen, posicion in
                     sorted(notas.items(), key=lambda par: nucleo.orden_natural(par[0]))]
            entrada = {"valor": self.registro.nombre(llave)}
            if tipo == "archivos":
                entrada["proyecto"] = proyecto
            elif tipo == "commits":
                dato = por_sha.get(clave) or self.commits.get(clave)
                entrada["valor"] = min(self.registro.mostrado[llave], key=lambda h: (len(h), h))
                if dato:
                    entrada["sha"] = dato.get("sha")
                    entrada["repo"] = alias(dato["repo"])
                    entrada["fecha"] = dato.get("fecha")
                    entrada["asunto"] = nucleo.recortar(dato.get("asunto") or "", 100)
                else:
                    entrada["repo"] = None
            entrada["notas"] = lista
            indice[tipo].append(entrada)
        for tipo in TIPOS:
            indice[tipo].sort(key=lambda e: (e["valor"].lower(), e.get("proyecto", "")))
        cerebro.entidades = indice
        agregadas = self.comparten()
        cerebro.resumen_entidades = {
            "archivos": len(indice["archivos"]),
            "commits": len(indice["commits"]),
            "verificados": sum(1 for e in indice["commits"] if e.get("repo")),
            "consultados": len(self.consultados),
            "tablas": len(indice["tablas"]),
            "menciones": sum(len(e["notas"]) for tipo in TIPOS for e in indice[tipo]),
            "comparten": agregadas,
            "carpetas": self.carpetas,
        }
        return agregadas

    def comparten(self):
        cerebro = self.cerebro
        unidos = set()
        for de, a in cerebro.fuertes:
            unidos.add((de, a))
            unidos.add((a, de))
        for de, a, _ in cerebro.otras:
            unidos.add((de, a))
            unidos.add((a, de))
        pares = {}
        for tipo in TIPOS:
            for entrada in cerebro.entidades[tipo]:
                if tipo == "commits" and not entrada.get("repo"):
                    continue
                if tipo == "archivos" and entrada["valor"].lower() in GENERICOS:
                    continue
                notas = [n for n, _ in entrada["notas"]]
                if not 2 <= len(notas) <= TOPE_RARA:
                    continue
                for x in range(len(notas)):
                    for y in range(x + 1, len(notas)):
                        a, b = sorted((notas[x], notas[y]))
                        pares.setdefault((a, b), []).append(entrada["valor"])
        agregadas = 0
        for (a, b), valores in sorted(pares.items()):
            if len(valores) < MINIMO_COMPARTIDAS or (a, b) in unidos:
                continue
            if cerebro.por_id[a]["tipo"] == "handoff" and cerebro.por_id[b]["tipo"] == "handoff":
                continue
            valores = sorted(set(valores), key=str.lower)
            texto = f'comparten {", ".join(valores[:MOSTRAR_COMPARTIDAS])}'
            if len(valores) > MOSTRAR_COMPARTIDAS:
                texto += f" y {len(valores) - MOSTRAR_COMPARTIDAS} más"
            cerebro.agregar(a, b, "comparte", texto)
            cerebro.pares_comparten[(a, b)] = {"comparten": valores[:12], "cuantas": len(valores)}
            agregadas += 1
        return agregadas


def preparar(cerebro):
    return Estado(cerebro).preparar()


def partir_ruta(consulta):
    q = consulta.strip().strip("`'\"").strip()
    partes = [p for p in RE_SEPARADORES.split(q) if p]
    if len(partes) < 2:
        return None, None
    raiz = None
    if RE_UNIDAD.match(partes[0]):
        raiz = nucleo.proyecto_de_ruta(nucleo.normalizar(q))
    else:
        raiz = por_prefijo(partes[:-1]) or nucleo.proyecto_unico(q)
    return partes[-1], (alias(raiz) if raiz else None)


def quien_nombra(cerebro, consulta):
    nombre, proyecto = partir_ruta(consulta)
    if nombre:
        tipo, hallados, parecidos = quien_nombra(cerebro, nombre)
        if tipo == "archivos" and proyecto:
            hallados = [e for e in hallados if e["proyecto"] == proyecto] or hallados
        return tipo, hallados, parecidos
    q = consulta.strip().strip("`'\"").strip()
    ql = q.lower()
    indice = cerebro.entidades or {tipo: [] for tipo in TIPOS}
    if RE_HEX.match(ql):
        hallados = [e for e in indice["commits"]
                    if (e["sha"].startswith(ql) if e.get("sha") else (e["valor"].startswith(ql) or ql.startswith(e["valor"])))]
        if hallados:
            return "commits", hallados, []
        datos, _ = medico.consultar_commits([ql])
        dato = datos.get(ql)
        if dato:
            return "commits", [{"valor": ql, "sha": dato.get("sha"), "repo": alias(dato["repo"]), "fecha": dato.get("fecha"),
                                "asunto": dato.get("asunto") or "", "notas": []}], []
    if RE_TABLA_SUELTA.match(ql):
        hallados = [e for e in indice["tablas"] if e["valor"].lower() == ql]
        if hallados:
            return "tablas", hallados, []
    hallados = [e for e in indice["archivos"] if e["valor"].lower() == ql]
    if not hallados and "." not in ql:
        hallados = [e for e in indice["archivos"] if e["valor"].lower().rsplit(".", 1)[0] == ql]
    if hallados:
        return "archivos", hallados, []
    parecidos = sorted({e["valor"] for tipo in TIPOS for e in indice[tipo] if ql and ql in e["valor"].lower()}, key=str.lower)
    return None, [], parecidos[:12]


def linea_de_texto(nodo, linea, valor):
    numero = linea - nodo.get("_desfase", 0) - 1
    renglones = nodo["_cuerpo"].split("\n")
    if not 0 <= numero < len(renglones):
        return ""
    renglon = renglones[numero]
    donde = renglon.lower().find(valor.lower())
    if donde < 0:
        return nucleo.recortar(re.sub(r"\s+", " ", renglon).strip(), ANCHO_RENGLON)
    return nucleo.fragmento(renglon, donde, donde + len(valor), ANCHO_RENGLON)


def texto_entidad(cerebro, consulta, tope=LINEAS_CONSOLA):
    tipo, hallados, parecidos = quien_nombra(cerebro, consulta)
    lineas = []
    nombre, proyecto = partir_ruta(consulta)
    if nombre:
        lineas.append("Busco por el nombre, «" + nombre + "»" + (", en el proyecto " + proyecto if proyecto else "")
                      + ": el índice guarda el nombre del archivo y su proyecto, no la carpeta.")
    sin_repos = " (no hay repositorios git en la configuración para buscarlo)"
    if not hallados:
        como_commit = (" y no es un commit de ningún repo conocido." if medico.repos_conocidos()
                       else f"; no pude buscarlo como commit{sin_repos}.")
        lineas.append("Ninguna nota nombra «" + consulta + "»"
                      + (como_commit if RE_HEX.match(consulta.strip().strip("`'\"").lower()) else "."))
        if parecidos:
            lineas.append(f'Parecidos: {", ".join(parecidos)}')
        return lineas, 1
    for entrada in hallados:
        if len(lineas) >= tope:
            break
        cuantas = len(entrada["notas"])
        cabeza = entrada["valor"]
        if tipo == "archivos":
            cabeza += f' ({entrada["proyecto"] or "sin proyecto claro"})'
        elif tipo == "commits":
            if entrada.get("repo"):
                cabeza += f' · {entrada["repo"]} · {entrada.get("fecha") or "sin fecha"} · «{entrada.get("asunto", "")}»'
            else:
                cabeza += " · no está en ningún repo conocido" if medico.repos_conocidos() else f" · sin verificar{sin_repos}"
        cabeza += f': {"ninguna nota lo cita" if not cuantas else str(cuantas) + (" nota" if cuantas == 1 else " notas")}'
        lineas.append(cabeza)
        con_renglon = sum(len(e["notas"]) for e in hallados) <= CON_RENGLON
        for n, (origen, linea) in enumerate(entrada["notas"]):
            if len(lineas) >= tope - (2 if con_renglon else 1):
                lineas.append(f"  … y {cuantas - n} más (están todas en datos['entidades'] del JSON)")
                break
            nodo = cerebro.por_id[origen]
            lineas.append(f'  {nodo["ruta"]}:{linea} — {nucleo.recortar(nodo["titulo"], 60)}')
            renglon = linea_de_texto(nodo, linea, entrada["valor"]) if con_renglon else ""
            if renglon:
                lineas.append(f"      {renglon}")
    return lineas[:tope], 0


def main(consulta):
    if not consulta or not consulta.strip():
        print("Falta qué buscar: un archivo (riego.py), un commit (a1b2c3d) o una tabla (pedidos).")
        return 1
    cerebro = nucleo.desde_disco()
    if cerebro.resumen_entidades is None:
        print("No pude armar el índice de entidades.")
        return 1
    lineas, codigo = texto_entidad(cerebro, consulta)
    for linea in lineas:
        print(linea)
    return codigo


if __name__ == "__main__":
    sys.exit(main(" ".join(sys.argv[1:])))
