import json
import os
import re
from pathlib import Path

import cerebro as nucleo
import configuracion
import medico
from archivos import escribir_atomico

PROPUESTAS = nucleo.DATOS / "hechos-propuestos.json"
NUMERO = r"(\d{1,3}(?:\.\d{3})+|\d{1,6})"
UNIDADES = {"líneas": "lineas", "lineas": "lineas", "renglones": "lineas", "archivos": "archivos", "carpetas": "carpetas",
            "skills": "carpetas", "notas": "notas", "lines": "lineas", "files": "archivos", "folders": "carpetas",
            "directories": "carpetas", "notes": "notas"}
NOMBRE_TIPO = {"lineas": "líneas", "archivos": "archivos", "carpetas": "carpetas", "notas": "notas"}
RE_CIFRA = re.compile(f'(?<![\\w.,/\\\\])\\*{{0,2}}{NUMERO}\\*{{0,2}}\\s+({"|".join(UNIDADES)})\\b', re.I)
RE_CANDIDATA = re.compile(r"`([^`\n]{2,260})`|([A-Za-z]:[\\/][^\s`'\"<>|*?]+)")
RE_CERCO = re.compile(r"^(```|~~~)", re.M)
RE_ANTES_DE_RUTA = re.compile(r"\*{0,2}\s+(?:en|de|del|in|of)\s+", re.I)
TOPE_TEXTO = 160


def fuera_de_cercos(texto):
    marcas = [m.start() for m in RE_CERCO.finditer(texto)]
    cercos = list(zip(marcas[0::2], marcas[1::2] + [len(texto)] * (len(marcas) % 2)))
    return lambda posicion: not any(a <= posicion < b for a, b in cercos)


def oracion(texto, inicio, fin):
    a = max(texto.rfind(". ", 0, inicio) + 2, texto.rfind("\n", 0, inicio) + 1, 0)
    cortes = [x for x in (texto.find(". ", fin), texto.find("\n", fin)) if x >= 0]
    return a, min(cortes) if cortes else len(texto)


def cuentas_de(tipo, ruta):
    if tipo == "lineas":
        return [{"tipo": "lineas", "archivo": ruta}]
    if tipo == "carpetas":
        return [{"tipo": "carpetas", "carpeta": ruta}]
    base = {"tipo": "archivos", "carpeta": ruta}
    if tipo == "notas":
        base["extensiones"] = [".md"]
    return [base, dict(base, recursivo=True)]


def patron_para(texto, inicio, unidad):
    linea = texto.rfind("\n", 0, inicio) + 1
    for largo in (24, 48, 96):
        patron = f"{re.escape(texto[max(linea, inicio - largo):inicio])}{NUMERO}\\*{{0,2}}\\s+{re.escape(unidad)}"
        if len(re.findall(patron, texto)) == 1:
            return patron
    return None


def leer(ruta):
    try:
        with open(ruta, encoding="utf-8-sig", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def cubiertas(cerebro):
    hechos, _ = medico.leer_hechos()
    salida = set()
    for h in hechos:
        identificador = medico.nodo_de_nota(cerebro, h.get("nota"))
        if identificador is None or not h.get("patron"):
            continue
        texto = leer(cerebro.por_id[identificador]["ruta"])
        try:
            for m in re.finditer(h["patron"], texto, re.M):
                salida.add((identificador, texto.count("\n", 0, m.start()) + 1))
        except re.error:
            continue
    return salida


def revisables(cerebro, nodo):
    if medico.es_historica(nodo) or nodo["tipo"] == "handoff":
        return False
    fuente = cerebro.fuente_de.get(nodo["id"], {})
    if fuente.get("anclas_resumidas"):
        return False
    return bool(fuente.get("memoria") or fuente.get("foco") or nodo["tipo"] in ("instrucciones", "indice"))


def proponer(cerebro):
    rutas = medico.Rutas(cerebro)
    ya = cubiertas(cerebro)
    salida = []
    for nodo in cerebro.nodos:
        if not revisables(cerebro, nodo):
            continue
        texto = leer(nodo["ruta"])
        afuera = fuera_de_cercos(texto)
        for m in RE_CIFRA.finditer(texto):
            linea = texto.count("\n", 0, m.start()) + 1
            if not afuera(m.start()) or (nodo["id"], linea) in ya:
                continue
            unidad = m.group(2)
            tipo = UNIDADES[unidad.lower()]
            dice = medico.numero_de(m)
            if dice is None or (dice >= 1000 and dice % 1000 == 0):
                continue
            a, b = oracion(texto, m.start(), m.end())
            pegadas = []
            for c in RE_CANDIDATA.finditer(texto, a, b):
                entre = texto[c.end():m.start()] if c.end() <= m.start() else texto[m.end():c.start()]
                if c.end() <= m.start():
                    if len(entre) > 40 or "`" in entre or ". " in entre:
                        continue
                elif not RE_ANTES_DE_RUTA.fullmatch(entre):
                    continue
                ruta, existe, _ = rutas.resolver(nodo["id"], (c.group(1) or c.group(2)).rstrip(".,;:)"))
                if existe and (os.path.isfile(ruta) if tipo == "lineas" else os.path.isdir(ruta)):
                    pegadas.append((len(entre), os.path.normpath(ruta)))
            if not pegadas:
                continue
            ruta = min(pegadas)[1]
            elegida = None
            for como in cuentas_de(tipo, ruta):
                try:
                    hoy, _ = medico.contar(como)
                except (medico.Huerfano, OSError, re.error):
                    continue
                if elegida is None or hoy == dice:
                    elegida = (como, hoy)
                if hoy == dice:
                    break
            patron = patron_para(texto, m.start(1), unidad)
            if elegida is None or patron is None:
                continue
            como, hoy = elegida
            que = f'{NOMBRE_TIPO[tipo]} de {Path(ruta).name or ruta}{" (con subcarpetas)" if como.get("recursivo") else ""}'
            salida.append({"nota": nodo["ruta"], "id": nodo["id"], "linea": linea, "que": que, "patron": patron,
                           "como_contar": como, "dice": dice, "hoy": hoy, "coincide": hoy == dice,
                           "texto": nucleo.recortar(re.sub(r"\s+", " ", texto[a:b]).strip(), TOPE_TEXTO)})
    salida.sort(key=lambda p: (not p["coincide"], p["nota"].lower(), p["linea"]))
    for i, p in enumerate(salida, 1):
        p["numero"] = i
    return salida


def texto_propuestas(propuestas):
    if not propuestas:
        return ["Memoria con pruebas: no encontré datos nuevos que se puedan comprobar solos (una cifra de líneas, "
                "archivos o carpetas al lado de una ruta que exista)."]
    buenas = [p for p in propuestas if p["coincide"]]
    otras = [p for p in propuestas if not p["coincide"]]
    cuantos = ("1 dato de las notas se puede comprobar solo" if len(propuestas) == 1
               else f"{len(propuestas)} datos de las notas se pueden comprobar solos")
    lineas = [f"Memoria con pruebas: {cuantos} contra el disco."]

    def fila(p):
        return [f'  {p["numero"]}. {p["nota"]}:{p["linea"]} — {p["que"]}: dice {p["dice"]}, hoy {p["hoy"]}',
                f'     «{p["texto"]}»']
    if buenas:
        lineas.append("Coinciden hoy (sirven como prueba: el médico avisa el día que cambien):")
        for p in buenas:
            lineas += fila(p)
    if otras:
        lineas.append("No coinciden hoy (la nota quedó vieja, o es un dato de un momento que no tiene que seguir valiendo):")
        for p in otras:
            lineas += fila(p)
    ejemplo = "1" if len(propuestas) == 1 else "1,2"
    usuario = nucleo.CONFIG["usuario"] or "el usuario"
    lineas.append(f"Para sumar las que sirvan a hechos.json: {configuracion.comando()} --aprobar-hecho {ejemplo} "
                  f"(lo decide {usuario}). La lista quedó en {PROPUESTAS}.")
    return lineas


def main_proponer():
    propuestas = proponer(nucleo.desde_disco(con_entidades=False))
    escribir_atomico(PROPUESTAS, json.dumps({"propuestas": propuestas}, ensure_ascii=False, indent=1))
    for linea in texto_propuestas(propuestas):
        print(linea)
    return 0


def relativa_si_adentro(ruta, base):
    try:
        relativa = os.path.relpath(ruta, base)
    except ValueError:
        return ruta
    return ruta if relativa.startswith("..") else relativa.replace("\\", "/")


def renglones_hecho(propuesta, base):
    como = dict(propuesta["como_contar"])
    for clave in ("archivo", "carpeta"):
        if como.get(clave):
            como[clave] = relativa_si_adentro(como[clave], base)
    adentro = relativa_si_adentro(propuesta["nota"], base) != propuesta["nota"]
    campos = [("nota", propuesta["id"] if adentro else propuesta["nota"]), ("que", propuesta["que"]),
              ("patron", propuesta["patron"])]
    cuerpo = ",\n".join(f"      \"{k}\": {json.dumps(v, ensure_ascii=False)}" for k, v in campos)
    return f"    {{\n{cuerpo},\n      \"como_contar\": {json.dumps(como, ensure_ascii=False)}\n    }}"


def main_aprobar(numeros):
    try:
        elegidos = sorted({int(x) for x in str(numeros).replace(" ", "").split(",") if x})
    except ValueError:
        print("Error: --aprobar-hecho lleva números separados por coma, como salieron en --proponer-hechos.")
        return 2
    try:
        propuestas = json.loads(PROPUESTAS.read_text(encoding="utf-8"))["propuestas"]
    except (OSError, ValueError, KeyError, TypeError):
        print(f"Error: no hay propuestas; corré antes {configuracion.comando()} --proponer-hechos.")
        return 2
    por_numero = {p.get("numero"): p for p in propuestas}
    faltan = [n for n in elegidos if n not in por_numero]
    if faltan or not elegidos:
        print(f'Error: no hay propuesta con el número {", ".join(str(n) for n in faltan or ["(ninguno)"])}.')
        return 2
    ruta = Path(medico.HECHOS)
    texto = ruta.read_text(encoding="utf-8-sig") if ruta.exists() else '{\n  "hechos": [\n  ]\n}\n'
    cierre = texto.rfind("]")
    if cierre < 0:
        print(f"Error: {ruta} no tiene la lista «hechos».")
        return 2
    antes = texto[:cierre].rstrip()
    nuevos = [renglones_hecho(por_numero[n], ruta.parent) for n in elegidos]
    separador = "\n" if antes.endswith("[") else ",\n"
    nuevo = antes + separador + ",\n".join(nuevos) + "\n  " + texto[cierre:]
    try:
        json.loads(nuevo)
    except ValueError as error:
        print(f"Error: el hechos.json resultante no sería JSON válido ({error}); no toqué nada.")
        return 2
    escribir_atomico(ruta, nuevo)
    restantes = [p for p in propuestas if p.get("numero") not in elegidos]
    escribir_atomico(PROPUESTAS, json.dumps({"propuestas": restantes}, ensure_ascii=False, indent=1))
    for n in elegidos:
        p = por_numero[n]
        print(f'Sumado a hechos.json: {p["nota"]}:{p["linea"]} — {p["que"]} (dice {p["dice"]}, hoy {p["hoy"]}).')
    return 0
