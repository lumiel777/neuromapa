import json
import time

import archivos
import permisos
import registro
from archivos import escribir_atomico, leer_objeto_json
from registro import numero
from textos import cantidad

from aprender_charlas import *
from aprender_comun import *
from aprender_informe import *
from aprender_memoria import *
from aprender_pista import *


def consolidar(carpeta=None, ahora=None, tanda=TANDA, segundos=SEGUNDOS, casa=None):
    carpeta = carpeta or en_vivo()
    ahora = time.time() if ahora is None else ahora
    comienzo = time.perf_counter()
    crudo = leer_objeto_json(carpeta / ARCHIVO)
    if mas_nueva(crudo):
        return Memoria(), 0, True
    memoria = Memoria(crudo)
    cargada = bool(memoria.hecho)
    memoria.envejecer(ahora)
    abiertas = memoria.abiertas()
    desde = memoria.hasta or ahora - VENTANA_COMPLETA
    limite = ahora - MARGEN
    de_prueba = frozenset(pruebas(carpeta))
    cuantos = 0
    completo = True
    hasta = desde
    for ev in registro.eventos(lineas_de(registros(carpeta, desde)), desde):
        t = numero(ev.get("t"))
        if t <= desde or t > limite:
            continue
        if cuantos >= tanda or (segundos is not None and cuantos and cuantos % 1000 == 0
                                and time.perf_counter() - comienzo > segundos):
            completo = False
            break
        try:
            memoria.anotar(ev, de_prueba)
        except (TypeError, ValueError, AttributeError, KeyError):
            pass
        hasta = max(hasta, t)
        cuantos += 1
    memoria.hasta = hasta
    listas = memoria.charlas["listo"]
    if completo and not listas:
        resto = None if segundos is None else segundos - (time.perf_counter() - comienzo)
        if resto is None or resto > MINIMO_CHARLAS:
            importar_charlas(memoria, carpeta, ahora, resto, casa)
        completo = memoria.charlas["listo"]
    memoria.cerrar(limite if completo else hasta)
    if cargada and completo and listas and not cuantos and memoria.abiertas() == abiertas:
        try:
            (carpeta / VISTO).touch()
            (carpeta / SIGUE).unlink(missing_ok=True)
            return memoria, 0, True
        except OSError:
            pass
    memoria.podar()
    memoria.hecho = ahora
    permisos.crear(carpeta)
    escribir_atomico(carpeta / ARCHIVO, json.dumps(memoria.datos(), ensure_ascii=False, separators=(",", ":")))
    sigue = carpeta / SIGUE
    try:
        if completo:
            sigue.unlink(missing_ok=True)
        else:
            sigue.write_bytes(b"")
    except OSError:
        pass
    return memoria, cuantos, completo


def tomar_candado(carpeta):
    return archivos.tomar_candado(carpeta / CANDADO)


def quizas(carpeta=None, ahora=None, cada=CADA):
    if not prendido():
        return False
    carpeta = carpeta or en_vivo()
    ahora = time.time() if ahora is None else ahora
    hecho = 0
    try:
        hecho = (carpeta / ARCHIVO).stat().st_mtime
        hecho = max(hecho, (carpeta / VISTO).stat().st_mtime)
    except OSError:
        pass
    if archivos.reciente(hecho, cada, ahora) and not (carpeta / SIGUE).exists():
        return False
    candado = tomar_candado(carpeta)
    if candado is None and archivos.hay_candados():
        return False
    try:
        consolidar(carpeta, ahora)
    finally:
        archivos.soltar_candado(candado)
    return True


def main(dias=7):
    dias = max(1, dias)
    carpeta = en_vivo()
    if not prendido():
        print(APAGADO)
        return 0
    al_dia(carpeta)
    for linea in texto(cargar(carpeta), dias, carpeta / ARCHIVO):
        print(linea)
    return 0


def al_dia(carpeta):
    candado = tomar_candado(carpeta)
    if candado is not None or not archivos.hay_candados():
        try:
            consolidar(carpeta, segundos=None)
        finally:
            archivos.soltar_candado(candado)


def main_detalle(buscado):
    carpeta = en_vivo()
    if not prendido():
        print(APAGADO)
        return 0
    al_dia(carpeta)
    aprendido = cargar(carpeta)
    if aprendido is None:
        print(texto(None, 1, carpeta / ARCHIVO)[0])
        return 0
    c, problema = elegir(aprendido, buscado)
    for linea in problema or detalle(aprendido, c):
        print(linea)
    return 1 if problema else 0


def olvidar(carpeta, claves, ahora=None):
    crudo = leer_objeto_json(carpeta / ARCHIVO)
    if mas_nueva(crudo):
        return 0
    memoria = Memoria(crudo)
    ahora = time.time() if ahora is None else ahora
    quitados = memoria.olvidar_archivo(claves[0], ahora) if len(claves) == 1 else memoria.olvidar_par(*claves, ahora)
    permisos.crear(carpeta)
    escribir_atomico(carpeta / ARCHIVO, json.dumps(memoria.datos(), ensure_ascii=False, separators=(",", ":")))
    return quitados


def main_olvidar(nombres):
    if not 1 <= len(nombres) <= 2:
        print("--olvidar lleva un archivo (olvida todo lo aprendido de él) o dos (olvida solo la unión entre los dos).")
        return 2
    carpeta = en_vivo()
    if not prendido():
        print(APAGADO)
        return 0
    candado = archivos.tomar_candado(carpeta / CANDADO, ESPERA_OLVIDO)
    if candado is None and archivos.hay_candados():
        print("Lo aprendido se está rearmando justo ahora: probá de nuevo en unos segundos.")
        return 1
    try:
        aprendido = cargar(carpeta)
        if aprendido is None:
            print(texto(None, 1, carpeta / ARCHIVO)[0])
            return 1
        claves = []
        for nombre in nombres:
            c, problema = elegir(aprendido, nombre)
            if problema:
                for linea in problema:
                    print(linea)
                return 1
            claves.append(c)
        if len(claves) == 2 and claves[0] == claves[1]:
            print("Los dos son el mismo archivo: para olvidar todo lo de él, nombralo una sola vez.")
            return 1
        rutas = [aprendido.rutas.get(c, c) for c in claves]
        fuerza = aprendido.fuerza(*claves) if len(claves) == 2 else 0.0
        quitados = olvidar(carpeta, claves)
    finally:
        archivos.soltar_candado(candado)
    despues = "Si se vuelve a usar, lo aprende de nuevo desde ahora; lo de antes ya no vuelve, ni rearmando."
    if len(claves) == 1:
        print(f"Olvidé lo aprendido de {rutas[0]}: {cantidad(quitados[0], 'unión', 'uniones')} del registro y "
              f"{quitados[1]} de las charlas guardadas. {despues}")
    elif any(quitados):
        detalle_fuerza = f" (tenía fuerza {decimal(fuerza)})" if fuerza else ""
        print(f"Olvidé la unión entre {rutas[0]} y {rutas[1]}{detalle_fuerza}. {despues}")
    else:
        print(f"No había una unión aprendida entre {rutas[0]} y {rutas[1]}; igual quedó anotado que no la aprenda de lo "
              "usado hasta ahora.")
    return 0
