import json
import math
import re
import time
from collections import Counter
from pathlib import Path

import buscador
import cerebro as nucleo
import permisos
from archivos import escribir_atomico
from medico import linea_en, sin_tildes
from textos import cantidad, decimal

UMBRAL = 0.35
UMBRAL_MEMORIA = 0.25
CASI_IGUAL = 0.70
TOPE_NOTAS = 60
PESO_FICHA = 3
MINIMO_LETRAS = 3
PALABRAS_COMPARTIDAS = 5
UMBRAL_AVISO = 0.25
VENTAJA = 1.5
CUANTAS = 5
TRAMO = 5
REPITE_MINIMO = 0.15
PALABRAS_MINIMAS = 40
ANCHO_PASAJE = 110
LARGO_CONSULTA_COMO_RUTA = 400
EXTENSIONES_BORRADOR = {".md", ".txt"}
VERSION = "1"
CACHE = nucleo.DATOS / "en-vivo" / "parecidas.json"

RE_URL = re.compile(r"(?:https?|ftp)://\S+|www\.\S+", re.I)
RE_PALABRA = re.compile(r"\w{%d,}" % MINIMO_LETRAS)
RE_CRUDA = re.compile(r"[a-z0-9]+")
RE_NUMERO = re.compile(r"(?:(?<=[-_ ])v)?\d+")
RE_SEPARADOR = re.compile(r"[-_ .]+")
RE_ESPACIOS = re.compile(r"\s+")
_utiles = {}


def utiles(crudo):
    hecho = _utiles.get(crudo)
    if hecho is None:
        hecho = tuple(f for f in buscador.formas(crudo) if len(f) >= MINIMO_LETRAS and not f.isdigit())
        _utiles[crudo] = hecho
    return hecho


def contar(texto, cuenta=None, peso=1):
    if cuenta is None:
        cuenta = {}
    if "://" in texto or "www." in texto:
        texto = RE_URL.sub(" ", texto)
    for crudo, veces in Counter(RE_PALABRA.findall(texto.lower())).items():
        for f in utiles(crudo):
            cuenta[f] = cuenta.get(f, 0) + veces * peso
    return cuenta


def version():
    return f"{VERSION}:{MINIMO_LETRAS}:{len(buscador.VACIAS)}"


class Cache:
    def __init__(self, ruta=CACHE):
        self.ruta = ruta
        self.antes = {}
        self.ahora = {}
        self.leidas = 0
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = None
        if isinstance(datos, dict) and datos.get("version") == version() and isinstance(datos.get("notas"), dict):
            self.antes = datos["notas"]

    def cuerpo(self, nodo):
        clave = nodo["ruta"]
        mtime, tamano = nodo.get("_firma") or nucleo.firma(clave)
        guardado = self.antes.get(clave)
        if (mtime is not None and isinstance(guardado, list) and len(guardado) == 3
                and guardado[0] == mtime and guardado[1] == tamano == nodo["bytes"] and isinstance(guardado[2], dict)):
            cuenta = guardado[2]
        else:
            cuenta = contar(nodo["_cuerpo"])
            self.leidas += 1
        if mtime is not None and tamano == nodo["bytes"]:
            self.ahora[clave] = [mtime, tamano, cuenta]
        return dict(cuenta)

    def guardar(self):
        if not self.leidas and self.ahora.keys() == self.antes.keys():
            return
        try:
            permisos.crear(self.ruta.parent)
            escribir_atomico(self.ruta, json.dumps({"version": version(), "notas": self.ahora},
                                                          ensure_ascii=False, separators=(",", ":")))
        except OSError as error:
            nucleo.avisar(f"no pude guardar la caché de parecidas: {error}")


def vectores(cuentas, tope=TOPE_NOTAS):
    total = len(cuentas)
    df = Counter()
    for cuenta in cuentas:
        df.update(cuenta.keys())
    idf = {p: math.log(total / d) for p, d in df.items() if 2 <= d <= tope}
    salida = []
    for cuenta in cuentas:
        v = {p: (1 + math.log(tf)) * idf[p] for p, tf in cuenta.items() if p in idf}
        norma = math.sqrt(sum(x * x for x in v.values()))
        salida.append({p: x / norma for p, x in v.items()} if norma else v)
    return salida


def cosenos(vectores_, minimo, aislados_desde=None):
    if aislados_desde is None:
        aislados_desde = len(vectores_)
    listas = {}
    for i, v in enumerate(vectores_):
        for p, x in v.items():
            listas.setdefault(p, []).append((i, x))
    total = len(vectores_)
    filas = [{} for _ in range(min(aislados_desde, total))]
    for lista in listas.values():
        for k in range(len(lista) - 1):
            i, xi = lista[k]
            if i >= aislados_desde:
                break
            fila = filas[i]
            for j, xj in lista[k + 1:]:
                fila[j] = fila.get(j, 0.0) + xi * xj
    pares = [(s, i, j) for i, fila in enumerate(filas) for j, s in fila.items() if s >= minimo and s > 0 and j > i]
    pares.sort(key=lambda par: (-par[0], par[1], par[2]))
    return pares


def comparten(va, vb, cuantas=PALABRAS_COMPARTIDAS):
    chico, grande = (va, vb) if len(va) <= len(vb) else (vb, va)
    comunes = [(chico[p] * grande[p], p) for p in chico if p in grande]
    comunes.sort(key=lambda par: (-par[0], par[1]))
    return [p for _, p in comunes[:cuantas]]


def sin_numeros(nombre):
    return RE_SEPARADOR.sub("-", RE_NUMERO.sub("", nombre)).strip("-")


def hermanas(ruta_a, ruta_b):
    a, b = Path(ruta_a), Path(ruta_b)
    misma_carpeta = nucleo.normalizar(a.parent) == nucleo.normalizar(b.parent)
    na, nb = a.stem.lower(), b.stem.lower()
    if na == nb:
        return None if misma_carpeta else "plantilla"
    if sin_numeros(na) == sin_numeros(nb):
        return "partes"
    partes_a, partes_b = RE_SEPARADOR.split(na), RE_SEPARADOR.split(nb)
    if misma_carpeta:
        if any(p.isdigit() for p in partes_a) and any(p.isdigit() for p in partes_b):
            return "plantilla"
        return None
    comun = 0
    for x, y in zip(partes_a, partes_b):
        if x != y:
            break
        comun += 1
    return "plantilla" if comun >= 2 else None


def texto_par(puntaje, palabras, parentesco, casi_igual):
    lista = ", ".join(palabras)
    if parentesco == "plantilla":
        return (f"parecidas por plantilla {decimal(puntaje, 2)}: son de la misma serie o plantilla a propósito, "
                f"no hace falta fusionarlas (comparten {lista})")
    if parentesco == "partes":
        return f"parecen partes de lo mismo {decimal(puntaje, 2)}: convendría que una nombre a la otra (comparten {lista})"
    if casi_igual:
        return f"casi iguales {decimal(puntaje, 2)}: ¿una repite a la otra? (comparten {lista})"
    return f"parecida {decimal(puntaje, 2)}: comparten {lista}"


def marcar(cerebro, cache=None):
    comienzo = time.perf_counter()
    if cache is None:
        cache = Cache()
    orden = [n for n in cerebro.nodos if n["tipo"] != "handoff"] + [n for n in cerebro.nodos if n["tipo"] == "handoff"]
    primer_handoff = sum(1 for n in orden if n["tipo"] != "handoff")
    cuentas = []
    for nodo in orden:
        cuenta = cache.cuerpo(nodo)
        contar(f'{nodo["titulo"]}\n{nodo["descripcion"] or ""}', cuenta, PESO_FICHA)
        cuentas.append(cuenta)
    cache.guardar()
    vs = vectores(cuentas)
    unidos = set()
    for de, a in cerebro.fuertes:
        unidos.add((de, a))
        unidos.add((a, de))
    for de, a, _ in cerebro.otras:
        unidos.add((de, a))
        unidos.add((a, de))
    es_memoria = [bool(cerebro.fuente_de[n["id"]].get("memoria")) and n["tipo"] != "indice" for n in orden]
    padres = {}
    for (de, a), (clase, _) in cerebro.fuertes.items():
        if clase in ("indice", "wiki", "enlace"):
            padres.setdefault(a, set()).add(de)
    agregadas = 0
    memorias = []
    for puntaje, i, j in cosenos(vs, min(UMBRAL, UMBRAL_MEMORIA), primer_handoff):
        a, b = sorted((orden[i]["id"], orden[j]["id"]))
        if (a, b) in unidos:
            continue
        palabras = comparten(vs[i], vs[j])
        parentesco = hermanas(cerebro.por_id[a]["ruta"], cerebro.por_id[b]["ruta"])
        comun = sorted(padres.get(a, set()) & padres.get(b, set()),
                       key=lambda x: (cerebro.por_id[x]["tipo"] == "indice", x)) if parentesco else []
        partes_de = Path(cerebro.por_id[comun[0]]["ruta"]).name if comun else ""
        if es_memoria[i] and es_memoria[j] and puntaje >= UMBRAL_MEMORIA:
            par = {"a": a, "b": b, "puntaje": round(puntaje, 3), "comparten": palabras}
            if partes_de:
                par["partesDe"] = partes_de
            memorias.append(par)
        if puntaje < UMBRAL:
            continue
        casi_igual = puntaje >= CASI_IGUAL and parentesco is None
        if partes_de:
            texto = (f"partes de {partes_de}, a propósito {decimal(puntaje, 2)}: no hace falta fusionarlas "
                     f'(comparten {", ".join(palabras)})')
        else:
            texto = texto_par(puntaje, palabras, parentesco, casi_igual)
        cerebro.agregar(a, b, "parecida", texto)
        datos = {"puntaje": round(puntaje, 3), "comparten": palabras}
        if parentesco:
            datos["hermanas"] = parentesco
        if partes_de:
            datos["partesDe"] = partes_de
        if casi_igual:
            datos["casiIgual"] = True
        cerebro.pares_parecidos[(a, b)] = datos
        agregadas += 1
    cerebro.memorias_parecidas = memorias
    cerebro.tiempo_parecidas = time.perf_counter() - comienzo
    cerebro.parecidas_recontadas = cache.leidas
    return agregadas


def separar_palabras(texto):
    return RE_CRUDA.findall(sin_tildes(texto))


def lugares_de(texto):
    return [m.start() for m in RE_CRUDA.finditer(sin_tildes(texto))]


def tramos(palabras):
    return list(zip(*(palabras[k:] for k in range(TRAMO))))


def primeras_apariciones(palabras):
    primera = {}
    for k, t in enumerate(tramos(palabras)):
        primera.setdefault(t, k)
    return primera


def cobertura(propios, primera):
    cubiertas = 0
    hasta = 0
    racha = None
    mejor = None
    for k, t in enumerate(propios):
        if t not in primera:
            continue
        desde = max(k, hasta)
        cubiertas += k + TRAMO - desde
        if racha is not None and k < hasta:
            racha[1] = k + TRAMO
        else:
            racha = [k, k + TRAMO, primera[t]]
        hasta = k + TRAMO
        if mejor is None or racha[1] - racha[0] > mejor[1] - mejor[0]:
            mejor = list(racha)
    return cubiertas, mejor


def pasaje(texto, lugares, palabras, desde, hasta):
    fin = lugares[hasta - 1] + len(palabras[hasta - 1])
    trozo = RE_ESPACIOS.sub(" ", texto[lugares[desde]:fin]).strip()
    return trozo if len(trozo) <= ANCHO_PASAJE else f"{trozo[:ANCHO_PASAJE - 1].rstrip()}…"


def fuentes_de_instrucciones(cerebro):
    salida = []
    for nodo in cerebro.nodos:
        if nodo["tipo"] != "instrucciones":
            continue
        salida.append((nodo, primeras_apariciones(separar_palabras(nodo["_cuerpo"]))))
    return salida


def repite_claude(cerebro):
    fuentes = fuentes_de_instrucciones(cerebro)
    lugares_fuente = {}
    salida = []
    for nodo in cerebro.nodos:
        if not cerebro.fuente_de[nodo["id"]].get("memoria") or nodo["tipo"] == "indice":
            continue
        palabras = separar_palabras(nodo["_cuerpo"])
        if len(palabras) < PALABRAS_MINIMAS:
            continue
        propios = tramos(palabras)
        mejor = None
        for instrucciones, primera in fuentes:
            if sum(map(primera.__contains__, propios)) * TRAMO < REPITE_MINIMO * len(palabras):
                continue
            cubiertas, racha = cobertura(propios, primera)
            if racha is None:
                continue
            parte = cubiertas / len(palabras)
            if mejor is None or parte > mejor[0]:
                mejor = (parte, cubiertas, racha, instrucciones)
        if mejor is None or mejor[0] < REPITE_MINIMO:
            continue
        parte, cubiertas, racha, instrucciones = mejor
        lugares = lugares_de(nodo["_cuerpo"])
        if instrucciones["id"] not in lugares_fuente:
            lugares_fuente[instrucciones["id"]] = lugares_de(instrucciones["_cuerpo"])
        lugares_i = lugares_fuente[instrucciones["id"]]
        salida.append({
            "nota": nodo["id"],
            "instrucciones": instrucciones["id"],
            "parte": round(parte, 3),
            "palabras": cubiertas,
            "total": len(palabras),
            "linea": linea_en(nodo, lugares[racha[0]]),
            "lineaInstrucciones": linea_en(instrucciones, lugares_i[racha[2]]),
            "largo": racha[1] - racha[0],
            "pasaje": pasaje(nodo["_cuerpo"], lugares, palabras, racha[0], racha[1]),
        })
    salida.sort(key=lambda r: (-r["parte"], r["nota"]))
    return salida


def documento(identificador, ruta, titulo, descripcion, cuerpo):
    return {"id": identificador, "ruta": ruta, "titulo": titulo or Path(ruta).stem, "descripcion": descripcion or "",
            "cuerpo": cuerpo}


def documentos_de_memoria(cerebro):
    return [documento(n["id"], n["ruta"], n["titulo"], n["descripcion"], n["_cuerpo"]) for n in cerebro.nodos
            if cerebro.fuente_de[n["id"]].get("memoria") and n["tipo"] != "indice"]


def leer_borrador(consulta):
    if len(consulta) <= LARGO_CONSULTA_COMO_RUTA and "\n" not in consulta:
        ruta = Path(consulta.strip().strip('"'))
        try:
            es_archivo = ruta.suffix.lower() in EXTENSIONES_BORRADOR and ruta.is_file()
        except (OSError, ValueError):
            es_archivo = False
        if es_archivo:
            texto, _ = nucleo.leer_texto(ruta)
            if texto is not None:
                return texto.replace("\r\n", "\n").replace("\r", "\n"), ruta
    return consulta, None


def comparar(texto, documentos, cuantas=CUANTAS, excluir=()):
    frontmatter, cuerpo = nucleo.separar_frontmatter(texto)
    ficha = " ".join(x for x in (nucleo.dato(frontmatter, "name"), nucleo.dato(frontmatter, "description"),
                                 nucleo.primer_encabezado(cuerpo)) if x)
    excluir = {nucleo.normalizar(e) for e in excluir}
    candidatos = [d for d in documentos if nucleo.normalizar(d["ruta"]) not in excluir]
    cuentas = [contar(ficha, contar(cuerpo), PESO_FICHA)]
    for d in candidatos:
        cuentas.append(contar(f'{d["titulo"]}\n{d["descripcion"]}', contar(d["cuerpo"]), PESO_FICHA))
    vs = vectores(cuentas, tope=len(cuentas))
    consulta = vs[0]
    puntajes = []
    for d, v in zip(candidatos, vs[1:]):
        chico, grande = (consulta, v) if len(consulta) <= len(v) else (v, consulta)
        s = sum(x * grande[p] for p, x in chico.items() if p in grande)
        puntajes.append((s, d, v))
    puntajes.sort(key=lambda par: (-par[0], par[1]["id"]))
    resultados = [{"id": d["id"], "ruta": d["ruta"], "titulo": d["titulo"], "puntaje": round(s, 3),
                   "comparten": comparten(consulta, v)} for s, d, v in puntajes[:cuantas] if s > 0]
    primero = resultados[0]["puntaje"] if resultados else 0.0
    segundo = resultados[1]["puntaje"] if len(resultados) > 1 else 0.0
    if primero >= UMBRAL_AVISO and primero >= VENTAJA * segundo:
        veredicto = "repetida"
    elif primero >= UMBRAL_AVISO:
        veredicto = "varias"
    else:
        veredicto = "nueva"
    return {"palabras": len(consulta), "resultados": resultados, "veredicto": veredicto, "cuerpo": cuerpo}


def main(consulta, cuantas=CUANTAS):
    comienzo = time.perf_counter()
    texto, ruta = leer_borrador(consulta)
    if ruta is None and "\n" not in consulta and Path(consulta.strip().strip('"')).suffix.lower() in EXTENSIONES_BORRADOR:
        print(f"No encontré el archivo {consulta.strip()}. Si es un texto, pasalo sin la extensión al final.")
        return 1
    if not texto.strip():
        print("No hay nada que comparar: pasá la ruta de un borrador .md o el texto entre comillas.")
        return 1
    cerebro = nucleo.desde_disco()
    resultado = comparar(texto, documentos_de_memoria(cerebro), cuantas, excluir=[ruta] if ruta else ())
    origen = f"a {ruta}" if ruta else "al texto"
    utiles = cantidad(resultado["palabras"], "palabra útil", "palabras útiles")
    print(f"Parecidas {origen} entre las memorias ({utiles}):")
    if not resultado["resultados"]:
        print("  Ninguna memoria comparte palabras con esto.")
    for r in resultado["resultados"]:
        print(f'  {decimal(r["puntaje"], 2)}  {r["ruta"]} — {r["titulo"]}')
        if r["comparten"]:
            print(f'        comparten: {", ".join(r["comparten"])}')
    if resultado["veredicto"] == "repetida":
        primera = resultado["resultados"][0]
        print(f'AVISO: ya hay una memoria que habla de lo mismo: {Path(primera["ruta"]).name}. '
              "Leela: si el borrador es un caso más de ese tema, conviene sumarlo ahí en vez de crear otra.")
    elif resultado["veredicto"] == "varias":
        print("REVISAR: se parece a varias memorias a la vez; leé las primeras antes de crear otra.")
    else:
        print(f"Ninguna memoria se parece lo suficiente (el aviso salta desde {decimal(UMBRAL_AVISO, 2)} "
              f"y con {decimal(VENTAJA, 2)} veces la segunda).")
    palabras = separar_palabras(resultado["cuerpo"])
    propios = tramos(palabras)
    for instrucciones, primera in fuentes_de_instrucciones(cerebro):
        cubiertas, racha = cobertura(propios, primera)
        if racha is None:
            continue
        parte = cubiertas / len(palabras)
        if parte >= REPITE_MINIMO:
            linea = linea_en(instrucciones, lugares_de(instrucciones["_cuerpo"])[racha[2]])
            print(f'AVISO: el {round(parte * 100)} % del texto ya está en {instrucciones["ruta"]}:{linea}, '
                  "que Claude carga en cada chat.")
    print(f"Tardó {decimal(time.perf_counter() - comienzo, 2)} s")
    return 0
