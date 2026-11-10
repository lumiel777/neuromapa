import bisect
import collections
import datetime
import hashlib
import json
import os
import re
import shutil
import time
import urllib.parse
from pathlib import Path

import archivos
from archivos import escribir_atomico
from textos import cantidad, decimal, miles, recortar, sin_wiki

BOM = b"\xef\xbb\xbf"
RESPALDOS = "respaldos"
SECCION_CHICA = 3000
LARGO_TITULO = 90
LARGO_GANCHO = 150
LARGO_GANCHO_CORTO = 60
PESADAS = 5
RE_TITULO = re.compile(r"^ {0,3}(#{1,6})[ \t]+\S")
RE_ITEM = re.compile(r"^(?:[-*+]|\d{1,3}[.)])[ \t]+\S")
RE_REGLA = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})[ \t]*$")
RE_CERCO = re.compile(r"^ {0,3}(```|~~~)")
RE_PARTE = re.compile(r"-historia-(\d+)$", re.I)
RE_TOMO = re.compile(r"-parte-(\d+)$", re.I)
RE_TITULO_DE_TOMO = re.compile(r",? parte \d+$", re.I)
RE_ENLACE = re.compile(r"\[[^\]\n]*\]\(\s*<?(?:\./)?([^)>#\s]+\.md)[)#>\s]", re.I)
RE_MARCA_ARCHIVO = re.compile(r"\((?:archivo|archive|archived)\)", re.I)
RE_RENGLON_DE_UNA = re.compile(r"^([ \t]*[-*+][ \t]+)\[([^\]\n]+)\]\(\s*(<[^>\n]+>|[^)\s]+)\s*\)[ \t]*(?:[—–-]+[ \t]*)?(.*)$")
RE_TITULO_DE_HISTORIA = re.compile(r"[,:]?\s*(?:historia|history)\s+\d+\s*\((?:archivo|archive|archived)\)\s*$", re.I)
RE_VIGENTE = re.compile(r"\s*\((?:vigente|actual|current)\)\s*$", re.I)
RE_SELLO = re.compile(r"^\s*(?:modified|created|updated|originSessionId)\s*:", re.I)
RE_NOMBRE_MALO = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RE_NAME = re.compile(r"^name[ \t]*:[ \t]*(.*?)[ \t]*\r?$", re.M)
RE_CADENA_JSON = re.compile(r'"(?:[^"\\\n]|\\.)*"')
DATOS_CON_RUTAS = (("hechos.json", ("nota",)), ("descartados.json", ("ruta",)), ("sugerencias.json", ("de", "a")))
CLASES = {"name": ("el name del encabezado", "el name del encabezado"), "wiki": ("enlace [[…]]", "enlaces [[…]]"),
          "enlace": ("enlace de Markdown", "enlaces de Markdown"),
          "archivo": ("nombre del archivo", "nombres del archivo"),
          "nombre": ("mención del nombre", "menciones del nombre")}
TOPE_AFUERA = 12
TOPE_EJEMPLOS = 3
RE_FECHA_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
RE_FECHA_CORTA = re.compile(r"(?<![\d/.,])(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?![\d/])")
LARGO_FECHA = 120
ENTRADAS_MINIMAS = 4
ENTRADAS_QUE_QUEDAN = 3
ORDEN_MINIMO = 0.9
ALIVIO_MINIMO = 0.05
QUIETA = 600
VUELTAS = 8
HISTORIA_LLENA = 0.8
REGISTRO = "partidas.log"
ULTIMAS = 10
RANGO_DE_CORTE = {"regla": 7, "item": 8, "parrafo": 9}
RE_DESCRIPCION_SOLA = re.compile(r"^(.*?: )(\d+) entradas? viejas?, del (\d{1,2}/\d{1,2}/\d{4}) al (\d{1,2}/\d{1,2}/\d{4})"
                                 r"(; lo vigente está en .+)$")
RE_DESCRIPTION = re.compile(r"^description[ \t]*:.*$", re.M)
RE_YA_DICE_ARCHIVO = re.compile(r"\s*(?:(?i:\((?:archivo|archive|archived)\))|(?:ARCHIVO|ARCHIVE|ARCHIVED)\b)")


def leer(ruta):
    crudo = Path(ruta).read_bytes()
    bom = crudo.startswith(BOM)
    return crudo, bom, crudo[len(BOM) if bom else 0:].decode("utf-8")


def renglones_de(texto):
    partes = texto.split("\n")
    return [p + "\n" for p in partes[:-1]] + ([partes[-1]] if partes[-1] else [])


def fin_de_renglon(texto):
    return "\r\n" if texto.count("\r\n") * 2 > texto.count("\n") else "\n"


def pelado(renglon):
    return renglon.rstrip("\r\n")


def con_fin(renglones, fin):
    return [pelado(r) + fin for r in renglones]


def fin_de_cabeza(renglones):
    if not renglones or renglones[0].strip() != "---":
        return 0
    for i in range(1, len(renglones)):
        if renglones[i].strip() in ("---", "..."):
            return i + 1
    return 0


def piezas_de(renglones):
    piezas = []
    cerco = ""
    en_blanco = True
    for i in range(fin_de_cabeza(renglones), len(renglones)):
        crudo = pelado(renglones[i])
        clase, nivel = "", 0
        marca = RE_CERCO.match(crudo)
        if cerco:
            if marca and marca.group(1) == cerco:
                cerco = ""
        else:
            titulo = RE_TITULO.match(crudo)
            anterior = piezas[-1]["clase"] if piezas else ""
            if titulo:
                clase, nivel = "titulo", len(titulo.group(1))
            elif en_blanco and RE_REGLA.match(crudo):
                clase = "regla"
            elif RE_ITEM.match(crudo):
                clase = "item"
            elif crudo.strip() and (not anterior or (en_blanco and not crudo[0].isspace()
                                                     and anterior in ("item", "regla"))):
                clase = "parrafo"
            if marca:
                cerco = marca.group(1)
        if clase:
            piezas.append({"clase": clase, "nivel": nivel, "desde": i, "hasta": i + 1, "titulo": crudo.strip()})
        elif piezas:
            piezas[-1]["hasta"] = i + 1
        en_blanco = not crudo.strip()
    for k, p in enumerate(piezas):
        p["n"] = k + 1
        p["bytes"] = sum(len(r.encode("utf-8")) for r in renglones[p["desde"]:p["hasta"]])
    for k, p in enumerate(piezas):
        if p["clase"] != "titulo":
            continue
        fin = k
        for j in range(k + 1, len(piezas)):
            if piezas[j]["clase"] == "titulo" and piezas[j]["nivel"] <= p["nivel"]:
                break
            fin = j
        p["fin_seccion"] = fin + 1
        p["bytes_seccion"] = sum(q["bytes"] for q in piezas[k:fin + 1])
    return piezas


def limpiar(texto):
    texto = sin_wiki(texto)
    texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texto)
    texto = re.sub(r"^(?:#{1,6}|[-*+]|\d{1,3}[.)])[ \t]+", "", texto.strip())
    return re.sub(r"\s+", " ", texto.replace("**", "").replace("`", "")).strip()


def kb(cuantos):
    return f"{decimal(cuantos / 1000)} KB"


def medidas(cuantos_renglones, cuantos_bytes):
    import medico
    tokens = int(cuantos_bytes / medico.BYTES_POR_TOKEN)
    entra = cuantos_renglones <= medico.LINEAS_READ and tokens <= medico.TOKENS_READ
    sobra = max(0, int((tokens - medico.TOKENS_READ) * medico.BYTES_POR_TOKEN))
    return tokens, entra, sobra


def elegir(pedido, total):
    numeros = set()
    for parte in str(pedido).replace(" ", "").split(","):
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", parte)
        if not m:
            return None, "--mover lleva números de pieza, como salen en la lista: 3-17, o 3,5,8-12."
        desde, hasta = int(m.group(1)), int(m.group(2) or m.group(1))
        if not 1 <= desde <= hasta <= total:
            return None, f"no hay pieza {parte}: la nota tiene {cantidad(total, 'pieza', 'piezas')}."
        numeros.update(range(desde, hasta + 1))
    return sorted(numeros), None


def corridas_de(numeros):
    corridas = []
    for n in numeros:
        if corridas and corridas[-1][-1] == n - 1:
            corridas[-1].append(n)
        else:
            corridas.append([n])
    return corridas


def siguiente_parte(carpeta, base, tomo=False):
    patron, palabra = (RE_TOMO, "parte") if tomo else (RE_PARTE, "historia")
    usados = [int(m.group(1)) for p in Path(carpeta).glob(f"{glob_literal(base)}-{palabra}-*.md")
              for m in [patron.search(p.stem)] if m and p.stem[:m.start()].lower() == base.lower()]
    return max(usados, default=int(tomo)) + 1


def glob_literal(texto):
    return re.sub(r"([\[\]*?])", r"[\1]", texto)


def enlace_a(nombre):
    return f"[{nombre}](<{nombre}>)" if re.search(r"\s", nombre) else f"[{nombre}]({nombre})"


def cabeza_para(cabeza, nombre, descripcion, fin):
    salida = []
    saltando = False
    puso_nombre = puso_descripcion = False
    for renglon in cabeza[1:-1]:
        crudo = pelado(renglon)
        clave = re.match(r"^([\w\-]+)[ \t]*:", crudo)
        if clave and clave.group(1) == "name":
            salida.append(f"name: {nombre}")
            puso_nombre, saltando = True, False
        elif clave and clave.group(1) == "description":
            salida.append(f"description: {json.dumps(descripcion, ensure_ascii=False)}")
            puso_descripcion, saltando = True, True
        elif saltando and not clave and (not crudo.strip() or crudo[0].isspace()):
            continue
        elif RE_SELLO.match(crudo):
            saltando = False
        else:
            saltando = False
            salida.append(crudo)
    if not puso_descripcion:
        salida.insert(1 if puso_nombre else 0, f"description: {json.dumps(descripcion, ensure_ascii=False)}")
    if not puso_nombre:
        salida.insert(0, f"name: {nombre}")
    return [r + fin for r in ["---"] + salida + ["---"]]


def es_subsecuencia(corta, larga):
    resto = iter(larga)
    return all(any(x == y for y in resto) for x in corta)


def huella_de(*partes):
    suma = hashlib.sha256()
    for parte in partes:
        dato = parte if isinstance(parte, bytes) else str(parte).encode("utf-8")
        suma.update(len(dato).to_bytes(8, "big") + dato)
    return suma.hexdigest()[:8]


def tallo_de(enlace):
    return Path(enlace.strip("<> ")).stem.lower()


def lo_que_agrega(titulo, nombre):
    resto = RE_TITULO_DE_HISTORIA.sub("", titulo).strip()
    if nombre and resto.lower().startswith(nombre.lower()):
        resto = resto[len(nombre):]
    return resto.strip(" ,:;—–-")


def sigue_abajo(renglones, i):
    siguiente = pelado(renglones[i + 1]) if i + 1 < len(renglones) else ""
    return bool(siguiente.strip()) and siguiente[:1] in " \t" and not RE_ITEM.match(siguiente.lstrip())


def juntar_historias(texto, familia=None, minimo=2, titulo=""):
    renglones = renglones_de(texto)
    sueltas = {}
    juntas = {}
    trabadas = set()
    for i, renglon in enumerate(renglones):
        crudo = pelado(renglon)
        enlaces = list(RE_ENLACE.finditer(crudo))
        de_historia = [tallo_de(m.group(1)) for m in enlaces if RE_PARTE.search(tallo_de(m.group(1)))]
        if not de_historia or not RE_ITEM.match(crudo.lstrip()):
            continue
        clave = RE_PARTE.sub("", de_historia[0])
        if familia is not None and clave != familia:
            continue
        una = RE_RENGLON_DE_UNA.match(crudo) if len(enlaces) == 1 else None
        if sigue_abajo(renglones, i):
            trabadas.add(clave)
        elif RE_MARCA_ARCHIVO.search(crudo[:enlaces[0].start()]):
            juntas.setdefault(clave, i)
        elif una and tallo_de(una.group(3)) == de_historia[0]:
            sueltas.setdefault(clave, []).append((int(RE_PARTE.search(de_historia[0]).group(1)), i, una))
    cambios = []
    sobran = set()
    for clave, lista in sueltas.items():
        lista.sort(key=lambda x: x[:2])
        if len(lista) + (clave in juntas) < minimo or clave in trabadas:
            continue
        nombre = next((RE_TITULO_DE_HISTORIA.sub("", t).strip() for t in [m.group(2) for _, _, m in lista] + [titulo]
                       if RE_TITULO_DE_HISTORIA.search(t) and RE_TITULO_DE_HISTORIA.sub("", t).strip()), "")
        pedazos = []
        for numero, _, m in lista:
            dice = " — ".join(x for x in (lo_que_agrega(m.group(2), nombre), m.group(4).strip()) if x)
            pedazos.append(f"[{numero}]({m.group(3)})" + (f" {dice}" if dice else ""))
        if clave in juntas:
            lugar = juntas[clave]
            nuevo = pelado(renglones[lugar]).rstrip() + "".join(f"; {p}" for p in pedazos)
        else:
            if not nombre:
                continue
            lugar = min(i for _, i, _ in lista)
            nuevo = f"{lista[0][2].group(1)}{nombre}, historias (archivo): " + "; ".join(pedazos)
        renglones[lugar] = nuevo + (renglones[lugar][len(pelado(renglones[lugar])):] or fin_de_renglon(texto))
        sobran |= {i for _, i, _ in lista if i != lugar}
        cambios.append({"familia": clave, "juntadas": len(lista) + (clave in juntas), "dice": nuevo.strip(),
                        "ganchos": [m.group(4).strip() for _, _, m in lista],
                        "palabras": {p for _, _, m in lista
                                     for p in re.findall(r"\w{3,}", RE_TITULO_DE_HISTORIA.sub("", m.group(2)).lower())}})
    salida = "".join(r for i, r in enumerate(renglones) if i not in sobran)
    antes = sorted(m.group(1).lower() for m in RE_ENLACE.finditer(texto))
    if antes != sorted(m.group(1).lower() for m in RE_ENLACE.finditer(salida)) or any(
            g not in salida for c in cambios for g in c["ganchos"]) or any(
            p not in salida.lower() for c in cambios for p in c["palabras"]):
        return texto, []
    for cambio in cambios:
        cambio["renglon"] = next((n for n, r in enumerate(renglones_de(salida), 1) if pelado(r).strip() == cambio["dice"]), 0)
    return salida, cambios


def cambio_de_indice(texto, fuente, destino, titulo, gancho, numero, tomo=False):
    fin = fin_de_renglon(texto)
    base = RE_PARTE.sub("", Path(fuente).stem).lower()
    raiz = RE_TOMO.sub("", base)
    juntadas = []
    if not tomo:
        texto, juntadas = juntar_historias(texto, base, 1, titulo)
    renglones = renglones_de(texto)

    def de_la_familia(enlace):
        tallo = Path(enlace).stem.lower()
        if tomo:
            return RE_TOMO.sub("", RE_PARTE.sub("", tallo)) == raiz
        return bool(RE_PARTE.search(tallo)) and RE_PARTE.sub("", tallo) == base

    propio = nombrada = None
    for i, renglon in enumerate(renglones):
        enlaces = [m.group(1) for m in RE_ENLACE.finditer(renglon)]
        nombres = [Path(e).name.lower() for e in enlaces]
        if Path(destino).name.lower() in nombres:
            return None, "el índice ya nombra esa nota"
        primero = RE_ENLACE.search(renglon)
        hermanas = [n for n in nombres if RE_PARTE.sub("", Path(n).stem) == base and RE_PARTE.search(Path(n).stem)]
        if not tomo and hermanas and RE_MARCA_ARCHIVO.search(renglon[:primero.start()]):
            agregado = f"; [{numero or Path(destino).stem}]({destino}) {recortar(gancho, LARGO_GANCHO_CORTO)}"
            renglones[i] = pelado(renglon).rstrip() + agregado + (renglon[len(pelado(renglon)):] or fin)
            if juntadas:
                return "".join(renglones), (f"el renglón {i + 1} del índice pasa a juntar las historias de la nota: "
                                            f"«{pelado(renglones[i]).strip()}»")
            return "".join(renglones), f"al final del renglón {i + 1} del índice: «{agregado[2:]}»"
        if propio is None and nombres[:1] == [Path(fuente).name.lower()]:
            propio = i
        elif nombrada is None and Path(fuente).name.lower() in nombres:
            nombrada = i
    propio = nombrada if propio is None else propio
    if propio is None:
        return None, "el índice no lista la nota: no le agrego nada"
    viñeta = re.match(r"^[ \t]*(?:[-*+][ \t]+)?", renglones[propio]).group(0)
    while propio + 1 < len(renglones) and any(
            de_la_familia(m.group(1)) for m in RE_ENLACE.finditer(renglones[propio + 1])):
        propio += 1
    nuevo = f"{viñeta}[{titulo}]({destino}) — {recortar(gancho, LARGO_GANCHO)}"
    if not renglones[propio].endswith("\n"):
        renglones[propio] += fin
    renglones.insert(propio + 1, nuevo + fin)
    return "".join(renglones), f"renglón nuevo debajo del {propio + 1} del índice: «{nuevo.strip()}»"


def planear(ruta, mover, destino="", titulo="", descripcion="", memoria=False, indice=None, titulo_nota="", gancho="",
            corte=None):
    ruta = Path(ruta)
    tomo = corte is not None
    if archivos.es_sensible(str(ruta)):
        return None, "ese archivo tiene nombre de clave o de secreto: no lo toco."
    try:
        crudo, bom, texto = leer(ruta)
    except OSError as error:
        return None, f"no pude leer {ruta.name} ({error.strerror or error})."
    except UnicodeDecodeError:
        return None, f"{ruta.name} no está en UTF-8: no lo toco."
    renglones = renglones_de(texto)
    piezas = piezas_de(renglones)
    if not piezas:
        return None, f"{ruta.name} no tiene piezas para mover."
    if tomo:
        cabeza_hasta = fin_de_cabeza(renglones)
        if not (cabeza_hasta < corte < len(renglones) and renglones[corte].strip()
                and any(r.strip() for r in renglones[cabeza_hasta:corte])):
            return None, f"{ruta.name} no se puede cortar en el renglón {corte + 1}."
        numeros = [p["n"] for p in piezas if p["desde"] >= corte]
    else:
        numeros, error = elegir(mover, len(piezas))
        if error:
            return None, error
        if len(numeros) == len(piezas):
            return None, "eso se lleva la nota entera: elegí solo lo viejo."
    fin = fin_de_renglon(texto)
    base = (RE_TOMO if tomo else RE_PARTE).sub("", ruta.stem)
    if destino:
        nombre = destino if destino.lower().endswith(".md") else f"{destino}.md"
        ruta_destino = Path(os.path.normpath(os.path.join(str(ruta.parent), nombre)))
    else:
        palabra = "parte" if tomo else "historia"
        ruta_destino = ruta.parent / f"{base}-{palabra}-{siguiente_parte(ruta.parent, base, tomo)}.md"
    if os.path.normcase(str(ruta_destino)) == os.path.normcase(str(ruta)):
        return None, "el destino es la misma nota."
    if archivos.es_sensible(str(ruta_destino)):
        return None, "el destino tiene nombre de clave o de secreto: no lo toco."
    existe = ruta_destino.is_file()
    crudo_destino = b""
    if existe:
        try:
            crudo_destino, bom_destino, texto_destino = leer(ruta_destino)
        except OSError as error:
            return None, f"no pude leer {ruta_destino.name} ({error.strerror or error})."
        except UnicodeDecodeError:
            return None, f"{ruta_destino.name} no está en UTF-8: no lo toco."
    tramos = []
    for desde, hasta in ([(corte, len(renglones))] if tomo else
                         [(piezas[c[0] - 1]["desde"], piezas[c[-1] - 1]["hasta"]) for c in corridas_de(numeros)]):
        while hasta > desde and not renglones[hasta - 1].strip():
            hasta -= 1
        tramos.append((desde, hasta))
    movidas = [piezas[n - 1] for n in numeros]
    if tomo and not (movidas and movidas[0]["desde"] == corte):
        movidas.insert(0, {"clase": "parrafo", "nivel": 0, "titulo": pelado(renglones[corte]).strip()})
    parte = (RE_TOMO if tomo else RE_PARTE).search(ruta_destino.stem)
    numero = int(parte.group(1)) if parte else 0
    cabeza = renglones[:fin_de_cabeza(renglones)]
    titulo_nota = RE_VIGENTE.sub("", titulo_nota) or next(
        (limpiar(p["titulo"]) for p in piezas if p["clase"] == "titulo" and p["nivel"] == 1), "") or ruta.stem
    if tomo:
        titulo_nota = RE_TITULO_DE_TOMO.sub("", titulo_nota) or ruta.stem
    relativo = os.path.relpath(str(ruta_destino), str(ruta.parent)).replace("\\", "/")
    de_vuelta = os.path.relpath(str(ruta), str(ruta_destino.parent)).replace("\\", "/")
    referencia = f"[[{ruta_destino.stem}]]" if memoria else enlace_a(relativo)
    cuantas = cantidad(len(movidas), "pieza", "piezas")
    como_item = movidas[0]["clase"] == "item"
    lo_que_lleva = lo_primero = ""
    if tomo:
        titulos = [p for p in movidas if p["clase"] == "titulo"]
        arriba_de_todo = min((p["nivel"] for p in titulos), default=0)
        cabezas = movidas[:1] + [p for p in titulos if p["nivel"] == arriba_de_todo and p is not movidas[0]]
        cabezas = cabezas if titulos else movidas
        lo_que_lleva = "; ".join(f'«{recortar(limpiar(p["titulo"]), 50)}»' for p in cabezas[:3]) + (
            "…" if len(cabezas) > 3 else "")
        lo_primero = f'«{recortar(limpiar(cabezas[0]["titulo"]), 50)}»' + (" y lo que sigue" if len(cabezas) > 1 else "")
        rastro = f"{'- ' if como_item else ''}Sigue en {referencia} ({cuantas}): {lo_que_lleva}"
    else:
        rastro = (f"- Lo que seguía acá ({cuantas}) pasó a {referencia}." if como_item
                  else f"Lo que estaba acá ({cuantas}) pasó a {referencia}.")
    quedan = []
    llevadas = []
    cursor = 0
    lugar_del_rastro = 0
    for k, (desde, hasta) in enumerate(tramos):
        quedan += renglones[cursor:desde]
        if k == 0:
            if tomo and not como_item and quedan and quedan[-1].strip():
                quedan.append(fin)
            lugar_del_rastro = len(quedan)
            quedan.append(rastro + fin)
            if not como_item and hasta < len(renglones) and renglones[hasta].strip():
                quedan.append(fin)
        llevadas.append(renglones[desde:hasta])
        cursor = hasta
    quedan += renglones[cursor:]
    if not existe:
        vuelta = f"[[{ruta.stem}]]" if memoria else enlace_a(de_vuelta)
        if tomo:
            titulo_destino = titulo or f"{titulo_nota}, parte {numero}"
            dicho = descripcion or f"Parte {numero} de «{titulo_nota}» (sigue de {ruta.stem}): {lo_que_lleva}"
            nivel = movidas[0]["nivel"] or 7
            seccion = next((p for p in reversed(piezas) if p["desde"] < corte and p["clase"] == "titulo"
                            and p["nivel"] < nivel), None)
            de_donde = (f'; lo primero es de la sección «{recortar(limpiar(seccion["titulo"]), 60)}»'
                        if seccion and seccion["nivel"] >= 2 else "")
            presentacion = (f"Sigue de {vuelta}{de_donde}. No es archivo: es la misma nota, que se partió sola porque "
                            "estaba por no entrar en una lectura.")
        else:
            titulo_destino = titulo or (f"{titulo_nota}, historia {numero} (archivo)" if numero
                                        else f"{titulo_nota} (archivo)")
            primeras = "; ".join(recortar(limpiar(p["titulo"]), 50) for p in movidas[:3])
            dicho = descripcion or (f"Parte vieja de «{titulo_nota}» ({cuantas}): {primeras}"
                                    f"{'…' if len(movidas) > 3 else ''}; lo vigente está en {ruta.stem}")
            dicho = dicho if RE_YA_DICE_ARCHIVO.match(dicho) else f"(archivo) {dicho}"
            presentacion = f"Lo vigente está en {vuelta}."
        arriba = (cabeza_para(cabeza, ruta_destino.stem, dicho, fin) + [fin] if memoria and cabeza else [])
        arriba += [f"# {titulo_destino}{fin}", fin, f"{presentacion}{fin}"]
        fin_destino = fin
        bom_destino = bom
    else:
        titulo_destino, dicho = titulo, ""
        fin_destino = fin_de_renglon(texto_destino)
        arriba = renglones_de(texto_destino)
        if arriba and not arriba[-1].endswith("\n"):
            arriba[-1] += fin_destino
        if titulo:
            arriba += [fin_destino, f"## {titulo}{fin_destino}"]
    nuevo_destino = list(arriba)
    for tramo in llevadas:
        nuevo_destino.append(fin_destino)
        nuevo_destino += con_fin(tramo, fin_destino)
    original = [pelado(r) for r in renglones if r.strip()]
    sin_rastro = [pelado(r) for i, r in enumerate(quedan) if r.strip() and i != lugar_del_rastro]
    lo_movido = [pelado(r) for tramo in llevadas for r in tramo if r.strip()]
    if (len(original) != len(sin_rastro) + len(lo_movido) or not es_subsecuencia(sin_rastro, original)
            or not es_subsecuencia(lo_movido, original)
            or not es_subsecuencia(lo_movido, [pelado(r) for r in nuevo_destino])):
        return None, "la cuenta de renglones no cierra: no toco nada (es un error del programa, avisá)."
    bytes_fuente = (BOM if bom else b"") + "".join(quedan).encode("utf-8")
    bytes_destino = (BOM if bom_destino else b"") + "".join(nuevo_destino).encode("utf-8")
    avisos = []
    for n in numeros:
        p = piezas[n - 1]
        if p["clase"] == "titulo" and p["fin_seccion"] > p["n"] and any(
                m not in numeros for m in range(p["n"] + 1, p["fin_seccion"] + 1)):
            avisos.append(f'la pieza {n} es un título («{recortar(limpiar(p["titulo"]), 50)}») y debajo le quedan piezas '
                          "que no se mueven: van a quedar bajo el título de arriba.")
    if not existe and memoria and not cabeza:
        avisos.append("la nota no tiene encabezado (name, description, type): la nueva tampoco lo va a tener.")
    edad = time.time() - ruta.stat().st_mtime
    if 0 <= edad < 120:
        avisos.append(f"la nota se guardó hace {int(edad)} s: si otro chat la está escribiendo, mejor esperar.")
    plan = {
        "ruta": ruta, "destino": ruta_destino, "existe": existe, "memoria": memoria, "indice": indice,
        "numeros": numeros, "movidas": movidas, "tramos": tramos, "rastro": rastro, "titulo": titulo_destino,
        "descripcion": dicho, "gancho": gancho or (f"sigue de {ruta.stem}: {lo_primero}" if tomo else ""),
        "numero": numero, "tomo": tomo, "lo_que_lleva": lo_que_lleva, "bytes_fuente": bytes_fuente,
        "bytes_destino": bytes_destino,
        "antes_fuente": crudo, "antes_destino": crudo_destino if existe else None,
        "renglones_antes": len(renglones), "renglones_despues": len(quedan), "renglones_movidos": sum(len(t) for t in llevadas),
        "primera": pelado(llevadas[0][0]), "ultima": pelado(llevadas[-1][-1]), "avisos": avisos,
        "huella": huella_de(os.path.normcase(str(ruta)), crudo, ",".join(map(str, numeros)),
                            os.path.normcase(str(ruta_destino)), crudo_destino if existe else b"(nueva)",
                            titulo, descripcion, gancho, *([f"corte {corte}"] if tomo else [])),
    }
    return plan, None


def indice_para(plan):
    if not plan["indice"] or (plan["existe"] and not plan.get("gancho_viejo")):
        return None, None, ""
    try:
        crudo, bom, texto = leer(plan["indice"])
    except (OSError, UnicodeDecodeError):
        return None, None, "no pude leer el índice: no le agrego nada"
    if plan["existe"]:
        patron = re.compile(r"(\]\(\s*<?(?:\./)?" + re.escape(plan["destino"].name) + r">?\s*\)\s*(?:[—–-]+\s*)?)"
                            + re.escape(plan["gancho_viejo"]))
        nuevo, cuantas = patron.subn(lambda m: m.group(1) + plan["gancho"], texto, count=1)
        if not cuantas:
            return None, None, ""
        return crudo, (BOM if bom else b"") + nuevo.encode("utf-8"), (
            f'el renglón de {plan["destino"].name} en el índice pasa a decir «{plan["gancho"]}»')
    gancho = plan["gancho"] or RE_YA_DICE_ARCHIVO.sub("", plan["descripcion"], count=1).strip()
    nuevo, dicho = cambio_de_indice(texto, plan["ruta"].name, plan["destino"].name, plan["titulo"], gancho,
                                    plan["numero"], plan.get("tomo", False))
    if nuevo is None:
        return None, None, dicho
    return crudo, (BOM if bom else b"") + nuevo.encode("utf-8"), dicho


def respaldar(datos, rutas, ahora=None, que="partir"):
    import permisos
    sello = time.strftime("%Y%m%d-%H%M%S", time.localtime(ahora))
    carpeta = Path(datos) / RESPALDOS / f"{sello}-{que}"
    k = 1
    while carpeta.exists():
        k += 1
        carpeta = Path(datos) / RESPALDOS / f"{sello}-{que}-{k}"
    permisos.crear(carpeta)
    for i, ruta in enumerate(rutas):
        shutil.copy2(str(ruta), str(carpeta / f"{i + 1}-{Path(ruta).name}"))
    return carpeta


def aplicar(plan, datos, ahora=None):
    crudo_indice, bytes_indice, dicho_indice = indice_para(plan)
    viejos = [plan["ruta"]] + ([plan["destino"]] if plan["existe"] else []) + ([plan["indice"]] if bytes_indice else [])
    carpeta = respaldar(datos, viejos, ahora)
    escritos = []
    try:
        ahora_destino = Path(plan["destino"]).read_bytes() if Path(plan["destino"]).is_file() else None
        if Path(plan["ruta"]).read_bytes() != plan["antes_fuente"] or ahora_destino != plan["antes_destino"]:
            raise RuntimeError("una de las dos notas cambió mientras se hacía el cambio")
        escribir_atomico(plan["destino"], plan["bytes_destino"])
        escritos.append((plan["destino"], plan["antes_destino"]))
        escribir_atomico(plan["ruta"], plan["bytes_fuente"])
        escritos.append((plan["ruta"], plan["antes_fuente"]))
        if bytes_indice:
            if Path(plan["indice"]).read_bytes() != crudo_indice:
                raise RuntimeError("el índice cambió mientras se hacía el cambio")
            escribir_atomico(plan["indice"], bytes_indice)
            escritos.append((plan["indice"], crudo_indice))
    except BaseException as error:
        for ruta, antes in reversed(escritos):
            if antes is None:
                os.remove(str(ruta))
            else:
                escribir_atomico(ruta, antes)
        if not isinstance(error, Exception):
            raise
        return None, dicho_indice, f"{error}: dejé todo como estaba."
    return carpeta, dicho_indice, None


def lista_de(ruta):
    crudo, _, texto = leer(ruta)
    renglones = renglones_de(texto)
    piezas = piezas_de(renglones)
    tokens, entra, sobra = medidas(len(renglones), len(crudo))
    salida = [f"{Path(ruta).name}: {cantidad(len(renglones), 'renglón', 'renglones')}, {kb(len(crudo))}, ~{miles(tokens)} "
              f"tokens. " + ("Entra en un Read." if entra else "NO entra en un Read: tienen que salir al menos "
                             f"{kb(sobra)}.") + f" Tiene {cantidad(len(piezas), 'pieza', 'piezas')}:"]

    def fila(numeros, p_desde, p_hasta, cuantos, texto_fila, sangria):
        lugar = f"r.{p_desde + 1}-{p_hasta}"
        return f"{numeros:>9}  {lugar:<13} {kb(cuantos):>9}  {'  ' * sangria}{texto_fila}"

    nivel = 0
    i = 0
    while i < len(piezas):
        p = piezas[i]
        if p["clase"] == "titulo":
            nivel = p["nivel"]
            seccion = f'  (sección entera: {p["n"]}-{p["fin_seccion"]})' if p["fin_seccion"] > p["n"] else ""
            salida.append(fila(str(p["n"]), p["desde"], p["hasta"], p["bytes"],
                               recortar(p["titulo"], LARGO_TITULO) + seccion, nivel - 1))
            i += 1
            continue
        j = i
        while j < len(piezas) and piezas[j]["clase"] != "titulo":
            j += 1
        tanda = piezas[i:j]
        peso = sum(q["bytes"] for q in tanda)
        if len(tanda) > 1 and peso < SECCION_CHICA:
            salida.append(fila(f'{tanda[0]["n"]}-{tanda[-1]["n"]}', tanda[0]["desde"], tanda[-1]["hasta"], peso,
                               f"({len(tanda)} piezas chicas)", nivel))
        else:
            for q in tanda:
                salida.append(fila(str(q["n"]), q["desde"], q["hasta"], q["bytes"],
                                   recortar(q["titulo"], LARGO_TITULO), nivel))
        i = j
    pesadas = sorted((q for q in piezas if q["clase"] != "titulo"), key=lambda q: -q["bytes"])[:PESADAS]
    if pesadas and not entra:
        salida.append("Las piezas más pesadas: " + ", ".join(f'{q["n"]} ({kb(q["bytes"])})' for q in pesadas) + ".")
    return salida


def resolver(nota):
    import cerebro as nucleo
    directa = Path(os.path.abspath(nota))
    cerebro = nucleo.desde_disco(con_entidades=False)
    if directa.is_file():
        identificador = cerebro.por_ruta.get(nucleo.normalizar(directa))
        candidatos = [cerebro.por_id[identificador]] if identificador else []
        if not candidatos:
            real = os.path.normcase(os.path.realpath(str(directa)))
            candidatos = [n for n in cerebro.nodos if Path(n["ruta"]).name.lower() == directa.name.lower()
                          and os.path.normcase(os.path.realpath(n["ruta"])) == real]
        if not candidatos:
            return {"ruta": directa, "memoria": False, "indice": None, "nodo": None, "cerebro": cerebro}, None
    else:
        pedido = Path(nota).name.lower()
        pedido = pedido if pedido.endswith(".md") else f"{pedido}.md"
        candidatos = [n for n in cerebro.nodos if Path(n["ruta"]).name.lower() == pedido]
    if not candidatos:
        return None, f"no encontré la nota {nota}: pasá su ruta o su nombre de archivo."
    if len(candidatos) > 1:
        rutas = "; ".join(n["ruta"] for n in candidatos[:5])
        return None, f"hay {len(candidatos)} notas que se llaman así ({rutas}): pasá la ruta entera."
    nodo = candidatos[0]
    if nodo["tipo"] == "indice":
        return None, "esa nota es un índice: no se parte, se acortan sus renglones."
    memoria = bool(cerebro.fuente_de[nodo["id"]].get("memoria"))
    indice = None
    if memoria:
        carpeta = cerebro.carpeta_de[nodo["id"]]
        indice = next((Path(n["ruta"]) for n in cerebro.nodos
                       if n["tipo"] == "indice" and cerebro.carpeta_de[n["id"]] == carpeta), None)
    return {"ruta": Path(nodo["ruta"]), "memoria": memoria, "indice": indice, "nodo": nodo, "cerebro": cerebro}, None


def citas_por_renglon(contexto):
    if not contexto["nodo"]:
        return []
    patron = re.compile(re.escape(contexto["ruta"].name) + r":\d+", re.I)
    salida = []
    for nodo in contexto["cerebro"].nodos:
        cuantas = len(patron.findall(nodo["_cuerpo"]))
        if cuantas and nodo["id"] != contexto["nodo"]["id"]:
            salida.append((Path(nodo["ruta"]).name, cuantas))
    return salida


def main_partir(nota, mover="", destino="", titulo="", descripcion="", confirmar="", gancho=""):
    import cerebro as nucleo
    import configuracion
    contexto, error = resolver(nota)
    if error:
        print(f"Error: {error}")
        return 2
    ruta = contexto["ruta"]
    comando = f'{configuracion.comando()} --partir "{ruta}"'
    if not mover:
        try:
            for linea in lista_de(ruta):
                print(linea)
        except (OSError, UnicodeDecodeError) as error:
            print(f"Error: no pude leer {ruta.name} ({error}).")
            return 2
        print(f"Para ver el plan de pasar piezas a otra nota (no cambia nada): {comando} --mover 3-17")
        print("Con --destino NOTA van a esa nota (si existe, al final); sin eso, a una nueva «…-historia-N».")
        return 0
    plan, error = planear(ruta, mover, destino, titulo, descripcion, contexto["memoria"], contexto["indice"],
                          contexto["nodo"]["titulo"] if contexto["nodo"] else "", gancho)
    if error:
        print(f"Error: {error}")
        return 2
    _, _, dicho_indice = indice_para(plan)
    tokens, entra, _ = medidas(plan["renglones_despues"], len(plan["bytes_fuente"]))
    tokens_destino, entra_destino, _ = medidas(plan["bytes_destino"].count(b"\n"), len(plan["bytes_destino"]))
    donde = (f'al final de {plan["destino"].name}, que ya existe' if plan["existe"]
             else f'a {plan["destino"].name}, nueva')
    lineas = [
        f'De {ruta.name} {"se va" if len(plan["movidas"]) == 1 else "se van"} '
        f'{cantidad(len(plan["movidas"]), "pieza", "piezas")} '
        f'({cantidad(plan["renglones_movidos"], "renglón", "renglones")}) {donde}.',
        f'  Primer renglón que se va: «{recortar(plan["primera"], LARGO_TITULO)}»',
        f'  Último renglón que se va: «{recortar(plan["ultima"], LARGO_TITULO)}»',
        f'  En su lugar queda: «{plan["rastro"]}»',
        f'  {ruta.name} queda en {cantidad(plan["renglones_despues"], "renglón", "renglones")}, '
        f'{kb(len(plan["bytes_fuente"]))}, ~{miles(tokens)} tokens: ' + ("entra en un Read." if entra
                                                                         else "todavía NO entra en un Read."),
        f'  {plan["destino"].name} queda en {kb(len(plan["bytes_destino"]))}, ~{miles(tokens_destino)} tokens'
        + ("." if entra_destino else ": NO entra en un Read."),
    ]
    if not plan["existe"]:
        lineas.append(f'  Título de la nueva: «{plan["titulo"]}»')
        if plan["memoria"]:
            lineas.append(f'  Su description: «{plan["descripcion"]}»')
            if not descripcion:
                lineas.append("  (Conviene pasar una mejor con --descripcion \"…\": es lo que Claude lee para decidir si "
                              "la abre; y con --gancho \"…\", lo que va a decir de ella el índice.)")
    if dicho_indice:
        lineas.append(f"  Índice: {dicho_indice}.")
    citas = citas_por_renglon(contexto)
    if citas:
        nombres = ", ".join(f"{nombre} ({cuantas})" for nombre, cuantas in citas[:5])
        plan["avisos"].append(f"otras notas citan renglones de {ruta.name} por número ({nombres}): después del cambio "
                              "el médico dice cuáles quedaron corridos.")
    lineas += [f"  Aviso: {aviso}" for aviso in plan["avisos"]]
    if not confirmar:
        print("Plan (todavía no cambié nada):")
        for linea in lineas:
            print(linea)
        extras = "".join(f' {opcion} "{valor}"' for opcion, valor in (("--destino", destino), ("--titulo", titulo),
                                                                      ("--descripcion", descripcion),
                                                                      ("--gancho", gancho)) if valor)
        print(f'Para hacerlo: {comando} --mover {mover}{extras} --confirmar {plan["huella"]}')
        return 0
    if confirmar.strip().lower() != plan["huella"]:
        print("Error: esa confirmación no es la de este plan (la nota o el destino cambiaron, o el pedido es otro). "
              "Pedí el plan de nuevo, sin --confirmar, y usá la que muestre.")
        return 2
    guardar_historial()
    carpeta, dicho_indice, error = aplicar(plan, nucleo.DATOS)
    if error:
        print(f"Error: {error}")
        return 1
    guardar_historial()
    print("Hecho:")
    for linea in [lineas[0].replace(" se van ", " se fueron ").replace(" se va ", " se fue ")] + lineas[3:6]:
        print(linea)
    if dicho_indice:
        print(f"  Índice: {dicho_indice}.")
    print(f"  Copia de cómo estaba todo antes: {carpeta}")
    print(f"Conviene correr {configuracion.comando()} --salud para ver que no quedó nada suelto.")
    return 0


def lugar_del_nombre(crudo):
    desde, hasta = 0, len(crudo)
    if crudo.startswith("<") and crudo.endswith(">"):
        desde, hasta = 1, hasta - 1
    hasta = min((i for i in (crudo.find("#", desde, hasta), crudo.find("?", desde, hasta)) if i >= 0), default=hasta)
    barra = max(crudo.rfind("/", desde, hasta), crudo.rfind("\\", desde, hasta))
    desde = barra + 1 if barra >= 0 else desde
    while desde < hasta and crudo[desde].isspace():
        desde += 1
    while hasta > desde and crudo[hasta - 1].isspace():
        hasta -= 1
    return desde, hasta


def destino_de_enlace(carpeta, crudo):
    import cerebro as nucleo
    destino = crudo.strip()
    if destino.startswith("<") and destino.endswith(">"):
        destino = destino[1:-1].strip()
    limpio = destino.split("#")[0].split("?")[0]
    if limpio.lower().startswith("file:"):
        limpio = re.sub(r"^file:/*", "", limpio, flags=re.I)
    elif nucleo.RE_ESQUEMA.match(limpio):
        return ""
    limpio = urllib.parse.unquote(limpio)
    if not limpio.lower().endswith(".md"):
        return ""
    if re.match(r"^[A-Za-z]:[\\/]", limpio):
        return nucleo.normalizar(os.path.normpath(limpio))
    relativo = limpio.lstrip("\\/") if limpio[:1] in ("\\", "/") else limpio
    return nucleo.normalizar(os.path.normpath(os.path.join(str(carpeta), relativo)))


def referencias_en(cerebro, origen, texto, objetivo, nuevo):
    import cerebro as nucleo
    ruta_vieja = nucleo.normalizar(objetivo["ruta"])
    archivo_viejo = Path(objetivo["ruta"]).name.lower()
    fichas = {objetivo["slug"].lower(), Path(objetivo["ruta"]).stem.lower()}
    carpeta = Path(origen["ruta"]).parent
    hallados = []
    dudosos = []

    def sumar(desde, hasta, reemplazo, clase):
        if desde < hasta and not any(a < hasta and desde < b for a, b, _, _ in hallados):
            hallados.append((desde, hasta, reemplazo, clase))

    renglones = renglones_de(texto)
    cabeza = sum(len(r) for r in renglones[:fin_de_cabeza(renglones)])
    nombre_de_la_nota = RE_NAME.search(texto, 0, cabeza)
    if origen["id"] == objetivo["id"]:
        if nombre_de_la_nota and nucleo.desentrecomillar(nombre_de_la_nota.group(1)) != nuevo:
            sumar(nombre_de_la_nota.start(1), nombre_de_la_nota.end(1), nuevo, "name")
        nombre_de_la_nota = None
    for m in nucleo.RE_WIKI.finditer(texto):
        crudo = m.group(1)
        dicho = crudo.strip()
        if cerebro.resolver_wiki(origen["id"], dicho)[0] != objetivo["id"]:
            continue
        desde = m.start(1) + len(crudo) - len(crudo.lstrip())
        corte = max(dicho.rfind("/"), dicho.rfind("\\")) + 1
        sumar(desde + corte, desde + len(dicho), nuevo + (".md" if dicho.lower().endswith(".md") else ""), "wiki")
    for m in nucleo.RE_ENLACE.finditer(texto):
        crudo = m.group(2)
        if destino_de_enlace(carpeta, crudo) != ruta_vieja and cerebro.enlace_lleva_a(origen["id"], crudo) != objetivo["id"]:
            continue
        desde, hasta = lugar_del_nombre(crudo)
        con_md = urllib.parse.unquote(crudo[desde:hasta]).lower().endswith(".md")
        archivo = f"{nuevo}.md" if con_md else nuevo
        if "%" in crudo[desde:hasta] or (re.search(r"\s", archivo) and not crudo.startswith("<")):
            archivo = urllib.parse.quote(archivo)
        sumar(m.start(2) + desde, m.start(2) + hasta, archivo, "enlace")
    for m in nucleo.RE_MD.finditer(texto):
        i = m.start()
        while i > 0 and nucleo.es_nombre(texto[i - 1]):
            i -= 1
        while i < m.start() and texto[i] == ".":
            i += 1
        if i >= m.start() or texto[i:m.end()].lower() != archivo_viejo:
            continue
        hallado = cerebro.recorrer_ruta(texto, i, archivo_viejo)
        if hallado is None or objetivo["id"] not in hallado[1]:
            continue
        candidatos = sorted(hallado[1])
        if len(candidatos) == 1 or cerebro.mismo_lugar(origen["id"], candidatos) == [objetivo["id"]]:
            sumar(i, m.end(), f"{nuevo}.md", "archivo")
        elif not any(a <= i < b for a, b, _, _ in hallados):
            dudosos.append(i)
    raras = []
    if cerebro.fuente_de[objetivo["id"]].get("memoria"):
        tramos = nucleo.tramos_de_codigo(texto)
        for m in nucleo.RE_TOKEN.finditer(texto):
            ficha = m.group(0).lower()
            ids = cerebro.slugs_mencionables.get(ficha, ())
            if ficha not in fichas or objetivo["id"] not in ids:
                continue
            if texto[m.end():m.end() + 3].lower() == ".md" or texto[max(0, m.start() - 2):m.start()] == "[[":
                continue
            if nombre_de_la_nota and nombre_de_la_nota.start(1) <= m.start() < nombre_de_la_nota.end(1):
                continue
            destino = None
            for grupo in cerebro.memorias_preferidas(origen["id"]):
                propios = sorted(c for c in ids if cerebro.por_id[c]["grupo"] == grupo)
                if propios:
                    if len(propios) == 1:
                        destino = propios[0]
                    elif objetivo["id"] in propios:
                        dudosos.append(m.start())
                    break
            if destino != objetivo["id"]:
                continue
            if pegada_a_una_ruta(texto, m.start(), m.end()) or not sola_o_fuera_de_codigo(texto, tramos, m):
                raras.append((m.start(), m.end()))
                continue
            sumar(m.start(), m.end(), nuevo, "nombre")
    return sorted(hallados), dudosos, raras


def pegada_a_una_ruta(texto, desde, hasta):
    antes = texto[desde - 1] if desde else ""
    return antes in ("\\", "/") or texto[hasta:hasta + 1] in ("\\", "/") or bool(re.match(r"\.\w", texto[hasta:hasta + 2]))


def sola_o_fuera_de_codigo(texto, tramos, m):
    k = bisect.bisect_right(tramos, (m.start(), float("inf"))) - 1
    if k < 0 or m.start() >= tramos[k][1]:
        return True
    a, b = tramos[k]
    return texto[a:b].strip("`").strip().lower() == m.group(0).lower()


def con_reemplazos(texto, hallados):
    partes = []
    cursor = 0
    for desde, hasta, reemplazo, _ in hallados:
        partes += [texto[cursor:desde], reemplazo]
        cursor = hasta
    return "".join(partes) + texto[cursor:]


def renglon_de(texto, posicion):
    return texto.count("\n", 0, posicion) + 1


def muestra(texto, desde, hasta, ancho=70):
    a = max(texto.rfind("\n", 0, desde) + 1, desde - ancho // 2)
    b = texto.find("\n", hasta)
    b = min(len(texto) if b < 0 else b, hasta + ancho // 2)
    return re.sub(r"\s+", " ", texto[a:b]).strip()


def datos_con_la_ruta(datos, vieja, nueva):
    import cerebro as nucleo
    clave = nucleo.normalizar(vieja)
    salida = []
    for nombre, campos in DATOS_CON_RUTAS:
        ruta = Path(datos) / nombre
        try:
            crudo, bom, texto = leer(ruta)
        except (OSError, UnicodeDecodeError):
            continue
        campo = re.compile(r'"(?:' + "|".join(campos) + r')"\s*:\s*$')
        partes = []
        cursor = cuantas = 0
        for m in RE_CADENA_JSON.finditer(texto):
            try:
                valor = json.loads(m.group(0))
            except ValueError:
                continue
            if nucleo.normalizar(valor) != clave or not campo.search(texto, 0, m.start()):
                continue
            corte = max(valor.rfind("/"), valor.rfind("\\")) + 1
            partes += [texto[cursor:m.start()], json.dumps(valor[:corte] + Path(nueva).name, ensure_ascii=False)]
            cursor = m.end()
            cuantas += 1
        if cuantas:
            despues = (BOM if bom else b"") + ("".join(partes) + texto[cursor:]).encode("utf-8")
            salida.append({"ruta": ruta, "antes": crudo, "despues": despues, "cuantas": cuantas})
    return salida


def planear_nombre(contexto, nuevo, datos):
    import cerebro as nucleo
    cerebro, objetivo = contexto["cerebro"], contexto["nodo"]
    if objetivo is None:
        return None, "esa nota no está en el mapa: no sé quién la nombra, así que cambiale el nombre a mano."
    nuevo = nuevo.strip()
    nuevo = nuevo[:-3] if nuevo.lower().endswith(".md") else nuevo
    ruta = Path(objetivo["ruta"])
    if not nuevo or nuevo.startswith(".") or nuevo.endswith((" ", ".")) or RE_NOMBRE_MALO.search(nuevo):
        return None, "el nombre nuevo va sin carpeta y sin < > : \" / \\ | ? *, y no puede empezar con punto."
    nueva = ruta.with_name(f"{nuevo}.md")
    if os.path.normcase(str(nueva)) == os.path.normcase(str(ruta)):
        return None, "la nota ya se llama así."
    if archivos.es_sensible(str(nueva)) or archivos.es_sensible(str(ruta)):
        return None, "ese nombre es de clave o de secreto: no lo toco."
    es_memoria = bool(cerebro.fuente_de[objetivo["id"]].get("memoria"))
    tomado = cerebro.slugs_memoria.get(objetivo["grupo"], {}).get(nuevo.lower()) if es_memoria else None
    if nueva.exists() or (tomado and tomado != objetivo["id"]):
        return None, f"ya hay una nota que se llama {nuevo}: elegí otro nombre."
    otras = [] if es_memoria else [c for c in cerebro.por_nombre_sin_md.get(nuevo.lower(), []) if c != objetivo["id"]]
    if otras:
        return None, (f'ya hay una nota que se llama {nuevo} en {Path(cerebro.por_id[otras[0]]["ruta"]).parent}: elegí otro '
                      f"nombre (con dos, los [[{nuevo}]] quedarían ambiguos).")
    cambios = []
    afuera = []
    dudosas = []
    raras = []
    ejemplos = []
    for nodo in cerebro.nodos:
        propio = nodo["id"] == objetivo["id"]
        try:
            crudo, bom, texto = leer(nodo["ruta"])
        except (OSError, UnicodeDecodeError) as error:
            if propio:
                return None, f"no pude leer {ruta.name} ({error}): no la toco."
            continue
        hallados, dudosos, de_ruta = referencias_en(cerebro, nodo, texto, objetivo, nuevo)
        dudosas += [(nodo["ruta"], renglon_de(texto, i)) for i in dudosos]
        raras += [(nodo["ruta"], renglon_de(texto, a), muestra(texto, a, b)) for a, b in de_ruta]
        if not hallados and not propio:
            continue
        adentro = propio or bool(cerebro.fuente_de[nodo["id"]].get("memoria")) or nodo["grupo"] == objetivo["grupo"]
        if not adentro or archivos.es_sensible(nodo["ruta"]):
            afuera += [(nodo["ruta"], renglon_de(texto, a), clase, muestra(texto, a, b)) for a, b, _, clase in hallados]
            continue
        ejemplos += [muestra(texto, a, b) for a, b, _, clase in hallados if clase == "nombre"][:TOPE_EJEMPLOS]
        cambios.append({"ruta": Path(nodo["ruta"]), "antes": crudo, "propio": propio,
                        "despues": (BOM if bom else b"") + con_reemplazos(texto, hallados).encode("utf-8"),
                        "clases": collections.Counter(clase for _, _, _, clase in hallados)})
    de_datos = datos_con_la_ruta(datos, str(ruta), str(nueva))
    partes = [os.path.normcase(str(ruta)), nuevo]
    for c in cambios + de_datos:
        partes += [os.path.normcase(str(c["ruta"])), c["antes"]]
    return {"ruta": ruta, "nueva": nueva, "nuevo": nuevo, "cambios": cambios, "datos": de_datos, "afuera": afuera,
            "dudosas": dudosas, "raras": raras, "ejemplos": ejemplos[:TOPE_EJEMPLOS], "huella": huella_de(*partes)}, None


def aplicar_nombre(plan, datos, ahora=None):
    todos = plan["cambios"] + plan["datos"]
    carpeta = respaldar(datos, [c["ruta"] for c in todos], ahora, "renombrar")
    escritos = []
    creada = False
    try:
        for c in todos:
            if Path(c["ruta"]).read_bytes() != c["antes"]:
                raise RuntimeError(f'{Path(c["ruta"]).name} cambió mientras se hacía el cambio')
        if plan["nueva"].exists():
            raise RuntimeError(f'ya existe {plan["nueva"].name}')
        propio = next(c for c in plan["cambios"] if c["propio"])
        escribir_atomico(plan["nueva"], propio["despues"])
        creada = True
        for c in todos:
            if not c.get("propio") and c["despues"] != c["antes"]:
                escribir_atomico(c["ruta"], c["despues"])
                escritos.append((c["ruta"], c["antes"]))
        os.remove(str(plan["ruta"]))
    except BaseException as error:
        for ruta, antes in reversed(escritos):
            escribir_atomico(ruta, antes)
        if creada:
            os.remove(str(plan["nueva"]))
        if not isinstance(error, Exception):
            raise
        return None, f"{error}: dejé todo como estaba."
    return carpeta, None


def main_renombrar(nota, nuevo, confirmar=""):
    import cerebro as nucleo
    import configuracion
    contexto, error = resolver(nota)
    if error and "índice" in error:
        error = "esa nota es un índice: Claude Code lo busca con ese nombre, no se le cambia."
    plan = None
    if not error:
        plan, error = planear_nombre(contexto, nuevo, nucleo.DATOS)
    if error:
        print(f"Error: {error}")
        return 2
    total = collections.Counter()
    for c in plan["cambios"]:
        total.update(c["clases"])
    con_cambios = [c for c in plan["cambios"] if sum(c["clases"].values()) > c["clases"]["name"]]
    por_clase = ", ".join(cantidad(total[clase], *CLASES[clase]) for clase in CLASES if total[clase] and clase != "name")
    lineas = [f'{plan["ruta"].name} pasa a llamarse {plan["nueva"].name}'
              + (" y su encabezado dice el nombre nuevo." if total["name"] else ".")]
    cuantas = sum(total.values()) - total["name"]
    if cuantas:
        lineas.append(f'  Cambio {cantidad(cuantas, "referencia", "referencias")} en '
                      f'{cantidad(len(con_cambios), "archivo", "archivos")} ({por_clase}):')
        lineas.append("    " + ", ".join(f'{c["ruta"].name} ({sum(c["clases"].values()) - c["clases"]["name"]})'
                                         for c in con_cambios))
    else:
        lineas.append("  Ninguna otra nota la nombra.")
    lineas += [f"  Ejemplo de mención del nombre: «{ejemplo}»" for ejemplo in plan["ejemplos"]]
    if plan["datos"]:
        lineas.append("  Datos de Neuromapa que la nombran por su ruta: "
                      + ", ".join(f'{d["ruta"].name} ({d["cuantas"]})' for d in plan["datos"]) + ".")
    if plan["afuera"]:
        lineas.append(f'  No toco {cantidad(len(plan["afuera"]), "referencia", "referencias")} fuera de la memoria '
                      "(cambialas a mano si hace falta):")
        lineas += [f"    {ruta}:{linea} ({CLASES[clase][0]}) «{texto}»"
                   for ruta, linea, clase, texto in plan["afuera"][:TOPE_AFUERA]]
        if len(plan["afuera"]) > TOPE_AFUERA:
            lineas.append(f'    … y {len(plan["afuera"]) - TOPE_AFUERA} más.')
    if plan["dudosas"]:
        lugares = ", ".join(f"{Path(ruta).name}:{linea}" for ruta, linea in plan["dudosas"][:TOPE_AFUERA])
        lineas.append(f'  No toco {cantidad(len(plan["dudosas"]), "mención dudosa", "menciones dudosas")} (hay otra nota '
                      f"con ese nombre de archivo y no se sabe a cuál apunta): {lugares}.")
    if plan["raras"]:
        lineas.append(f'  No toco {cantidad(len(plan["raras"]), "mención", "menciones")} del nombre que están en una ruta, '
                      "un archivo o un comando (si alguna es la nota, cambiala a mano):")
        lineas += [f"    {Path(ruta).name}:{linea} «{texto}»" for ruta, linea, texto in plan["raras"][:TOPE_AFUERA]]
        if len(plan["raras"]) > TOPE_AFUERA:
            lineas.append(f'    … y {len(plan["raras"]) - TOPE_AFUERA} más.')
    comando = f'{configuracion.comando()} --renombrar "{plan["ruta"]}" {plan["nuevo"]}'
    if not confirmar:
        print("Plan (todavía no cambié nada):")
        for linea in lineas:
            print(linea)
        print("  Aviso: un chat abierto que ya leyó la nota la va a buscar con el nombre viejo.")
        print(f'Para hacerlo: {comando} --confirmar {plan["huella"]}')
        return 0
    if confirmar.strip().lower() != plan["huella"]:
        print("Error: esa confirmación no es la de este plan (alguna de las notas cambió, o el pedido es otro). "
              "Pedí el plan de nuevo, sin --confirmar, y usá la que muestre.")
        return 2
    guardar_historial()
    carpeta, error = aplicar_nombre(plan, nucleo.DATOS)
    if error:
        print(f"Error: {error}")
        return 1
    guardar_historial()
    print("Hecho:")
    for linea in [lineas[0].replace(" pasa a llamarse ", " ahora se llama ")] + lineas[1:]:
        print(linea.replace("  Cambio ", "  Cambié ").replace("  No toco ", "  No toqué "))
    print(f"  Copia de cómo estaba todo antes: {carpeta}")
    print(f"  Lo que Neuromapa aprendió del uso de la nota quedó con el nombre viejo y se olvida solo; para borrarlo ya: "
          f'{configuracion.comando()} --olvidar "{plan["ruta"].name}"')
    print(f"Conviene correr {configuracion.comando()} --salud para ver que no quedó nada suelto.")
    return 0


def fecha_de(texto, hoy):
    texto = texto[:LARGO_FECHA]
    iso, corta = RE_FECHA_ISO.search(texto), RE_FECHA_CORTA.search(texto)
    try:
        if iso and (not corta or iso.start() <= corta.start()):
            return datetime.date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        if corta:
            dia, mes = int(corta.group(1)), int(corta.group(2))
            if mes > 12 >= dia:
                dia, mes = mes, dia
            if corta.group(3):
                anio = int(corta.group(3))
                return datetime.date(anio + 2000 if anio < 100 else anio, mes, dia)
            fecha = datetime.date(hoy.year, mes, dia)
            return fecha if fecha <= hoy + datetime.timedelta(days=1) else datetime.date(hoy.year - 1, mes, dia)
    except ValueError:
        return None
    return None


def entradas_de(piezas, hoy):
    grupos = {}
    pila = []
    ultimo_titulo = -1
    for k, p in enumerate(piezas):
        if p["clase"] == "titulo":
            while pila and pila[-1][0] >= p["nivel"]:
                pila.pop()
            llave = ("titulo", p["nivel"], pila[-1][1] if pila else -1)
            pila.append((p["nivel"], k))
            ultimo_titulo = k
            hasta = p["fin_seccion"]
        elif p["clase"] == "item":
            llave = ("item", ultimo_titulo)
            hasta = p["n"]
        else:
            continue
        grupos.setdefault(llave, []).append({"desde": p["n"], "hasta": hasta, "fecha": fecha_de(limpiar(p["titulo"]), hoy),
                                             "bytes": sum(q["bytes"] for q in piezas[k:hasta])})
    return list(grupos.values())


def corridas_con_fecha(unidades):
    i = 0
    while i < len(unidades):
        j = i
        while (j + 1 < len(unidades) and unidades[j]["fecha"] and unidades[j + 1]["fecha"]
               and unidades[j + 1]["desde"] == unidades[j]["hasta"] + 1):
            j += 1
        tramo = unidades[i:j + 1]
        i = j + 1
        if len(tramo) < ENTRADAS_MINIMAS or tramo[0]["fecha"] == tramo[-1]["fecha"]:
            continue
        pares = list(zip(tramo, tramo[1:]))
        bajan = sum(a["fecha"] >= b["fecha"] for a, b in pares)
        suben = sum(a["fecha"] <= b["fecha"] for a, b in pares)
        if max(bajan, suben) >= ORDEN_MINIMO * len(pares):
            yield (list(reversed(tramo)) if bajan >= suben else tramo)


def elegir_viejas(piezas, total, objetivo, hoy, dias_frescos, tope=None):
    limite = None if dias_frescos is None else hoy - datetime.timedelta(days=dias_frescos)
    mejor = None
    for unidades in entradas_de(piezas, hoy):
        for de_vieja_a_nueva in corridas_con_fecha(unidades):
            elegidas = []
            peso = 0
            for u in de_vieja_a_nueva[:len(de_vieja_a_nueva) - ENTRADAS_QUE_QUEDAN]:
                if (limite and u["fecha"] >= limite) or total - peso <= objetivo or (
                        tope and elegidas and peso + u["bytes"] > tope):
                    break
                elegidas.append(u)
                peso += u["bytes"]
            if elegidas and (mejor is None or peso > mejor["bytes"]):
                mejor = {"desde": min(u["desde"] for u in elegidas), "hasta": max(u["hasta"] for u in elegidas),
                         "bytes": peso, "entradas": len(elegidas), "primera": min(u["fecha"] for u in elegidas),
                         "ultima": max(u["fecha"] for u in elegidas), "dias": dias_frescos}
    return mejor


def cortes_de(renglones, piezas, entre_renglones=False):
    rangos = {p["desde"]: p["nivel"] or RANGO_DE_CORTE[p["clase"]] for p in piezas}
    cerco = ""
    en_blanco = False
    titulo_de_arriba = 0
    for i in range(fin_de_cabeza(renglones), len(renglones)):
        crudo = pelado(renglones[i])
        marca = RE_CERCO.match(crudo)
        if cerco:
            if marca and marca.group(1) == cerco:
                cerco = ""
        else:
            if (en_blanco or entre_renglones) and crudo.strip() and not crudo[0].isspace():
                rangos.setdefault(i, RANGO_DE_CORTE["parrafo"])
            if marca:
                cerco = marca.group(1)
        rango = rangos.get(i, 0)
        if titulo_de_arriba and rango > titulo_de_arriba:
            del rangos[i]
        if crudo.strip():
            titulo_de_arriba = rango if 1 <= rango <= 6 else 0
        en_blanco = not crudo.strip()
    return sorted(rangos.items())


def elegir_corte(renglones, piezas, objetivo, techo, alivio):
    antes = [0]
    for renglon in renglones:
        antes.append(antes[-1] + len(renglon.encode("utf-8")))
    primero = next((i for i in range(fin_de_cabeza(renglones), len(renglones)) if renglones[i].strip()), len(renglones))
    mejor = None
    for entre_renglones in (False, True):
        if mejor is not None:
            break
        for i, rango in cortes_de(renglones, piezas, entre_renglones):
            if i <= primero or antes[-1] - antes[i] < alivio or antes[i] < alivio:
                continue
            en_banda = objetivo / 2 <= antes[i] <= (objetivo + techo) / 2
            nota = (not en_banda, rango if en_banda else 0, abs(antes[i] - objetivo))
            if mejor is None or nota < mejor[0]:
                mejor = (nota, i)
    return None if mejor is None else {"corte": mejor[1], "bytes": antes[-1] - antes[mejor[1]]}


def dia_y_mes(fecha):
    return f"{fecha.day}/{fecha.month}/{fecha.year}"


def casi_llenas(cerebro, desde):
    import cerebro as nucleo
    import medico
    tope = medico.TOKENS_READ * medico.BYTES_POR_TOKEN
    for nodo in cerebro.nodos:
        if not cerebro.fuente_de[nodo["id"]].get("memoria") or nodo["tipo"] == "indice" or nucleo.es_archivo(nodo):
            continue
        lleno = max(nodo["bytes"] / tope, nodo["lineas"] / medico.LINEAS_READ)
        if lleno >= desde:
            yield nodo, lleno


def plan_sola(cerebro, nodo, lleno, opciones, hoy):
    import medico
    ruta = Path(nodo["ruta"])
    try:
        crudo, _, texto = leer(ruta)
    except (OSError, UnicodeDecodeError):
        return None, None, "no la pude leer"
    renglones = renglones_de(texto)
    piezas = piezas_de(renglones)
    total = len(crudo)
    objetivo = total * (opciones["hasta"] / 100) / lleno
    techo = total * (opciones["desde"] / 100 - ALIVIO_MINIMO) / lleno
    alivio = ALIVIO_MINIMO * medico.TOKENS_READ * medico.BYTES_POR_TOKEN
    caminos = [c for c in (elegir_viejas(piezas, total, objetivo, hoy, opciones["dias_frescos"]),
                           elegir_viejas(piezas, total, objetivo, hoy, None),
                           elegir_corte(renglones, piezas, objetivo, techo, alivio)) if c and c["bytes"] >= alivio]
    eleccion = next((c for c in caminos if total - c["bytes"] <= techo), None) or max(
        caminos, key=lambda c: c["bytes"], default=None)
    if not eleccion:
        largo = max((len(r.encode("utf-8")) for r in renglones), default=0)
        if largo * 2 > total:
            return None, None, (f"casi todo es un solo renglón de {kb(largo)}, y la nota solo se corta entre renglones: "
                                "hay que pasar ese renglón a ítems o párrafos a mano")
        return None, None, "no tiene ni un renglón suelto por donde cortarla (es un solo bloque de código o con sangría)"
    capacidad = HISTORIA_LLENA * medico.TOKENS_READ * medico.BYTES_POR_TOKEN
    if "corte" not in eleccion and eleccion["bytes"] > capacidad:
        eleccion = elegir_viejas(piezas, total, objetivo, hoy, eleccion["dias"], capacidad) or eleccion
    carpeta = cerebro.carpeta_de[nodo["id"]]
    indice = next((Path(n["ruta"]) for n in cerebro.nodos
                   if n["tipo"] == "indice" and cerebro.carpeta_de[n["id"]] == carpeta), None)
    if "corte" in eleccion:
        plan, error = planear(ruta, "", memoria=True, indice=indice, titulo_nota=nodo["titulo"], corte=eleccion["corte"])
        if error:
            return None, None, error
        if len(plan["bytes_destino"]) > total - alivio:
            return None, None, (f"la parte nueva quedaría casi igual de grande ({kb(len(plan['bytes_destino']))} de "
                                f"{kb(total)}): partirla no la achica")
        return plan, {"tomo": True, "piezas": len(plan["movidas"]),
                      "primero": recortar(limpiar(plan["movidas"][0]["titulo"]), 50)}, None
    dicho = {"entradas": eleccion["entradas"], "primera": dia_y_mes(eleccion["primera"]),
             "ultima": dia_y_mes(eleccion["ultima"])}
    nombre = RE_VIGENTE.sub("", nodo["titulo"] or "") or ruta.stem
    rango = f'del {dicho["primera"]} al {dicho["ultima"]}'
    viejas = cantidad(eleccion["entradas"], "entrada vieja", "entradas viejas")
    piezas_que_van = f'{eleccion["desde"]}-{eleccion["hasta"]}'
    anterior, hecha = historia_con_lugar(cerebro, ruta, eleccion["bytes"])
    if anterior:
        plan, error = planear(ruta, piezas_que_van, destino=Path(anterior["ruta"]).name, titulo=f"Entradas {rango}",
                              memoria=True, indice=indice, titulo_nota=nodo["titulo"])
        if not error:
            primera = min(eleccion["primera"], fecha_escrita(hecha.group(3)))
            ultima = max(eleccion["ultima"], fecha_escrita(hecha.group(4)))
            todas = cantidad(int(hecha.group(2)) + eleccion["entradas"], "entrada vieja", "entradas viejas")
            plan["gancho_viejo"] = f"del {hecha.group(3)} al {hecha.group(4)}"
            plan["gancho"] = f"del {dia_y_mes(primera)} al {dia_y_mes(ultima)}"
            plan["bytes_destino"] = con_descripcion(
                plan["bytes_destino"], f'{hecha.group(1)}{todas}, {plan["gancho"]}{hecha.group(5)}')
        return plan, dicho, error
    plan, error = planear(ruta, piezas_que_van, memoria=True, indice=indice,
                          titulo_nota=nodo["titulo"], gancho=rango,
                          descripcion=f"{nombre}: {viejas}, {rango}; lo vigente está en {ruta.stem}")
    return plan, dicho, error


def fecha_escrita(texto):
    dia, mes, anio = (int(parte) for parte in texto.split("/"))
    return datetime.date(anio, mes, dia)


def historia_con_lugar(cerebro, ruta, peso):
    import cerebro as nucleo
    import medico
    base = RE_PARTE.sub("", ruta.stem)
    ultima = ruta.parent / f"{base}-historia-{siguiente_parte(ruta.parent, base) - 1}.md"
    anterior = cerebro.por_id.get(cerebro.por_ruta.get(nucleo.normalizar(ultima)))
    if not anterior or not nucleo.es_archivo(anterior):
        return None, None
    hecha = RE_DESCRIPCION_SOLA.match(anterior["descripcion"] or "")
    if not hecha:
        return None, None
    try:
        fecha_escrita(hecha.group(3)), fecha_escrita(hecha.group(4))
        lugar = HISTORIA_LLENA * medico.TOKENS_READ * medico.BYTES_POR_TOKEN - os.path.getsize(anterior["ruta"])
    except (OSError, ValueError):
        return None, None
    return (anterior, hecha) if peso <= lugar else (None, None)


def con_descripcion(crudo, descripcion):
    bom = crudo.startswith(BOM)
    texto = crudo[len(BOM) if bom else 0:].decode("utf-8")
    renglones = renglones_de(texto)
    cabeza = sum(len(r) for r in renglones[:fin_de_cabeza(renglones)])
    m = RE_DESCRIPTION.search(texto, 0, cabeza)
    if not m:
        return crudo
    fin = "\r" if m.group(0).endswith("\r") else ""
    nuevo = texto[:m.start()] + f"description: {json.dumps(descripcion, ensure_ascii=False)}{fin}" + texto[m.end():]
    return (BOM if bom else b"") + nuevo.encode("utf-8")


def partir_solas(cerebro, datos, opciones, ahora=None, simular=False, recargar=None):
    ahora = time.time() if ahora is None else ahora
    hoy = datetime.date.fromtimestamp(ahora)
    hechas = []
    saltadas = []
    escritas = {}

    def propia(ruta):
        try:
            return escritas.get(os.path.normcase(str(ruta))) == Path(ruta).read_bytes()
        except OSError:
            return False

    for vuelta in range(VUELTAS if recargar and not simular else 1):
        partio = False
        vistas = {s["nota"] for s in saltadas}
        for nodo, lleno in casi_llenas(cerebro, opciones["desde"] / 100):
            if nodo["ruta"] in vistas:
                continue
            base = {"nota": nodo["ruta"], "lleno": int(lleno * 100)}
            try:
                reposo = (time.time() if vuelta else ahora) - os.path.getmtime(nodo["ruta"])
            except OSError:
                continue
            if not simular and 0 <= reposo < QUIETA and not propia(nodo["ruta"]):
                saltadas.append(dict(base, espera=True,
                                     motivo="se guardó hace menos de 10 minutos; vuelve a probar en media hora"))
                continue
            plan, dicho, error = plan_sola(cerebro, nodo, lleno, opciones, hoy)
            if error:
                saltadas.append(dict(base, motivo=error))
                continue
            hecha = dict(base, destino=str(plan["destino"]), antes=len(plan["antes_fuente"]),
                         despues=len(plan["bytes_fuente"]), lleva=len(plan["bytes_destino"]), t=ahora, **dicho)
            if not simular:
                carpeta, _, error = aplicar(plan, datos, ahora)
                if error:
                    saltadas.append(dict(base, motivo=error))
                    continue
                hecha["respaldo"] = str(carpeta)
                anotar(datos, hecha)
                escritas[os.path.normcase(str(plan["ruta"]))] = plan["bytes_fuente"]
                escritas[os.path.normcase(str(plan["destino"]))] = plan["bytes_destino"]
                partio = True
            hechas.append(hecha)
        if not partio:
            break
        cerebro = recargar()
    return hechas, saltadas


def juntar_indices(cerebro, datos, ahora=None, simular=False):
    ahora = time.time() if ahora is None else ahora
    hechas = []
    saltadas = []
    for nodo in cerebro.nodos:
        if nodo["tipo"] != "indice" or not cerebro.fuente_de[nodo["id"]].get("memoria"):
            continue
        ruta = Path(nodo["ruta"])
        try:
            crudo, bom, texto = leer(ruta)
            reposo = ahora - os.path.getmtime(ruta)
        except (OSError, UnicodeDecodeError):
            continue
        nuevo, cambios = juntar_historias(texto)
        if not cambios:
            continue
        base = {"nota": str(ruta), "indice": True, "lleno": 0}
        if not simular and 0 <= reposo < QUIETA:
            saltadas.append(dict(base, espera=True,
                                 motivo="se guardó hace menos de 10 minutos; vuelve a probar en media hora"))
            continue
        despues = (BOM if bom else b"") + nuevo.encode("utf-8")
        hecha = dict(base, t=ahora, notas=len(cambios), renglones=sum(c["juntadas"] for c in cambios) - len(cambios),
                     antes=len(crudo), despues=len(despues))
        if not simular:
            carpeta = respaldar(datos, [ruta], ahora, "juntar-indice")
            try:
                if ruta.read_bytes() != crudo:
                    raise RuntimeError("el índice cambió mientras se hacía el cambio")
                escribir_atomico(ruta, despues)
            except (OSError, RuntimeError) as error:
                saltadas.append(dict(base, motivo=f"{error}: lo dejé como estaba"))
                continue
            hecha["respaldo"] = str(carpeta)
            anotar(datos, hecha)
        hechas.append(hecha)
    return hechas, saltadas


def lo_que_pasa(hecha, haria=False):
    if hecha.get("indice"):
        return (f'las historias de {cantidad(hecha["notas"], "nota", "notas")} {"quedarían" if haria else "quedaron"} en un '
                f'renglón por nota ({cantidad(hecha["renglones"], "renglón menos", "renglones menos")}), con lo que decía '
                "cada una")
    destino = Path(hecha["destino"]).name
    if hecha.get("tomo"):
        return (f'de «{hecha["primero"]}» en adelante ({cantidad(hecha["piezas"], "pieza", "piezas")}) '
                f'{"pasaría" if haria else "pasó"} a {destino}, que no es archivo sino la segunda parte de la nota')
    return (f'{cantidad(hecha["entradas"], "entrada", "entradas")} (del {hecha["primera"]} al {hecha["ultima"]}) '
            f'{"pasarían" if haria else "pasaron"} a {destino}')


def anotar(datos, hecha):
    estaba = "el índice" if hecha.get("indice") else f'estaba al {hecha["lleno"]} % del tope de una lectura'
    renglon = (f'{time.strftime("%Y-%m-%d %H:%M", time.localtime(hecha["t"]))}  {Path(hecha["nota"]).name} ({estaba}): '
               f'{lo_que_pasa(hecha)}; copia de antes en {Path(hecha["respaldo"]).name}\n')
    try:
        with open(Path(datos) / RESPALDOS / REGISTRO, "a", encoding="utf-8", newline="\n") as registro:
            registro.write(renglon)
    except OSError:
        pass


def ultimas_partidas(datos):
    try:
        return (Path(datos) / RESPALDOS / REGISTRO).read_text(encoding="utf-8").splitlines()[-ULTIMAS:]
    except (OSError, UnicodeDecodeError):
        return []


def main_por_partir():
    import cerebro as nucleo
    import configuracion
    opciones = nucleo.CONFIG.get("partir_sola")
    cerebro = nucleo.desde_disco(con_entidades=False)
    hechas, saltadas = partir_solas(cerebro, nucleo.DATOS, opciones or dict(configuracion.PARTIR_SOLA), simular=True)
    desde = (opciones or configuracion.PARTIR_SOLA)["desde"]
    if not hechas and not saltadas:
        print(f"Ninguna memoria llega al {desde} % del tope de una lectura.")
    juntados = juntar_indices(cerebro, nucleo.DATOS, simular=True)[0]
    for h in juntados:
        print(f'En el índice {Path(h["nota"]).name}, {lo_que_pasa(h, True)}, y quedaría en {kb(h["despues"])} '
              f'(hoy {kb(h["antes"])}).')
    import medico
    llena = desde / 100 * medico.TOKENS_READ * medico.BYTES_POR_TOKEN
    for h in hechas:
        sigue = [Path(h["nota"]).name] if h["despues"] >= llena else []
        sigue += [Path(h["destino"]).name] if h.get("tomo") and h["lleva"] >= llena else []
        print(f'{Path(h["nota"]).name} está al {h["lleno"]} %: {lo_que_pasa(h, True)}, y quedaría en '
              f'{kb(h["despues"])} (hoy {kb(h["antes"])})'
              + (f'; {" y ".join(sigue)} seguiría{"n" if len(sigue) > 1 else ""} pasada{"s" if len(sigue) > 1 else ""} '
                 "del tope, así que la misma pasada la volvería a partir" if sigue else "") + ".")
    for s in saltadas:
        print(f'{Path(s["nota"]).name} está al {s["lleno"]} %, pero {s["motivo"]}. Se puede partir a mano: '
              f'{configuracion.comando()} --partir "{Path(s["nota"]).name}"')
    if hechas or juntados:
        print("Con «partir_sola» prendido en el config.json, la pasada de cada día hace esos cambios y lo avisa."
              if not opciones else "«partir_sola» está prendido: la pasada de cada día hace esos cambios y lo avisa "
              f"({configuracion.comando()} --partir-llenas los hace ahora).")
    ultimas = ultimas_partidas(nucleo.DATOS)
    if ultimas:
        print(f"Lo último que partió sola (el registro entero está en {Path(nucleo.DATOS) / RESPALDOS / REGISTRO}):")
        for renglon in ultimas:
            print(f"  {renglon}")
    return 0


def guardar_historial():
    try:
        import historial
        historial.guardar()
    except Exception:
        pass
