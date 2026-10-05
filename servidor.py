import gzip
import hmac
import http.client
import http.cookies
import http.server
import json
import math
import os
import queue
import re
import secrets
import socket
import socketserver
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import webbrowser
from collections import deque
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA))
import configuracion
try:
    import cerebro
except configuracion.ConfigInvalida as error:
    if __name__ != "__main__":
        raise
    sys.exit(f"Error en la configuración: {error}")
import buscador
import consultas
import firmas
import permisos
import registro
from archivos import escribir_atomico, hay_candados, leer_objeto_json, soltar_candado, tomar_candado
from registro import T_DE_LINEA, numero
from textos import detalle

EN_VIVO = cerebro.DATOS / "en-vivo"
REGISTRO = EN_VIVO / "eventos.jsonl"
PUERTOS = range(8765, 8771)
OPCIONES = ("--sin-navegador", "--puerto", "--demo", "--apagar-solo", "--reiniciar")
APAGAR_SIN_PESTANAS = 10 * 60
ESPERA_APAGADO = 8
CANDADO_ARRANQUE = "servidor.lock"
ESPERA_ARRANQUE = 60
PREVIOS = 80
TRABAJO_TOPE = 400
VENTANA_TRABAJO = 1800
HUECO_EPISODIO = 600
RECORRIDOS = 20
PASOS = 30
MAXIMO_FS = 5
MOTIVOS_PISTA = ("p", "i", "a")
DEMORA = 2
CADA_HUELLA = 10
EXTRAS = [cerebro.DATOS / "sugerencias.json", CARPETA / "plantilla.html", cerebro.DATOS / "hechos.json",
          cerebro.DATOS / "descartados.json", cerebro.DATOS / "fichas.json"]
DISPARADORES = {cerebro.normalizar(r) for r in EXTRAS}
LARGO_CONSULTA = 300
LARGO_CWD = 300
RESULTADOS = 40
MAXIMO_RESULTADOS = 100
ESTATICOS = {"/cerebro.html"}
ARCHIVO_CLAVE = EN_VIVO / "clave.txt"
GALLETA = "cerebro_clave"
DURACION_GALLETA = 30 * 86400
VIDA_ENTRADA = 60
CABECERA_CLAVE = "X-Cerebro-Clave"
CABECERA_FIRMA = "X-Cerebro-Firma"
SIN_CLAVE = ("<!doctype html><meta charset=\"utf-8\"><title>Neuromapa</title>"
             "<p style=\"font:16px system-ui;margin:40px\">Falta la clave. "
             "Abrí el mapa con <b>/neuromapa:abrir</b> en Claude Code (sin el plugin, <code>sh bin/neuromapa abrir</code>, "
             "o <code>bin\\neuromapa.cmd abrir</code> en Windows): abre el navegador con la clave puesta. Para entrar a "
             "mano, agregale a la dirección <code>?clave=</code> y la clave que está en <code>en-vivo/clave.txt</code>, "
             "en la carpeta de datos de Neuromapa.</p>").encode("utf-8")
ERRORES = {400: "El pedido vino mal armado.", 403: "Desde ahí no se puede entrar al mapa.",
           404: "No hay nada en esa dirección.", 501: "El mapa solo atiende pedidos para ver la página."}
REINTENTOS = 3
ESPERA_GENERAR = 10 * 60
POLITICA = ("default-src 'self'; script-src {scripts}; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; "
            "form-action 'none'; frame-ancestors 'none'")
RE_ETIQUETA_SCRIPT = re.compile(rb"(?m)^<script>")
ROTADOS_AL_ARRANCAR = 7
APRENDER_CADA = 60
RESUMEN = "resumen-dias.json"
VERSION_RESUMEN = 1
DIAS_SIN_COMPRIMIR = 30
RE_ROTADO = re.compile(r"^(eventos-(\d{8})-(\d{6})(?:-\d+)?\.jsonl)(\.gz)?\Z")
RE_OPCION_PAGINA = re.compile(r"[A-Za-z0-9_-]+(?:=[A-Za-z0-9_.%-]*)?")
CAMPOS_USO = ("leer", "editar", "crear", "buscar", "shell", "parcial", "falla")
ANIDADO_SOSPECHOSO = 50
HISTORIA_TOPE = 20000
HISTORIA_DIA = 86400
HISTORIA_MAXIMA = 7 * 86400
HISTORIA_LISTA = 300
HISTORIA_TOCADAS = 40
FASES_HISTORIA = {"post", "usuario", "fin", "sub-fin", "compacta", "espera", "inicio", "cierre", "falla", "aviso",
                  "recuerda", "guarda"}
MOTIVOS_HISTORIA = {"compact", "clear", "startup", "resume", "manual", "auto"}
TIPOS_HISTORIA = {"leer", "editar", "crear", "buscar", "ejecutar", "agente", "web", "otro", "consulta"} | FASES_HISTORIA
COMANDOS_HISTORIA = {"commit", "compila", "prueba", "git", "base", "cerebro", "lee", "busca", "lista", "python", "node",
                     "red", "archivos", "sistema", "script", "otro"}
NOMBRE_SEGURO = re.compile(r"[A-Za-z0-9_.:\-]{1,120}\Z")
EXTENSION = re.compile(r"\.[A-Za-z0-9]{1,12}\Z")
RAICES_HISTORIA = ([(p["raiz"].replace("\\", "/").lower().rstrip("/"), p["alias"]) for p in cerebro.CONFIG["proyectos"]]
                   + [(str(CARPETA).replace("\\", "/").lower(), CARPETA.name)])

clientes = []
clientes_lock = threading.Lock()
regenerar = {"en": 0.0}
regenerar_lock = threading.Lock()
ordenar_lock = threading.Lock()
indice = {"actual": None, "armado": None, "claves": frozenset()}
aprendizaje = {"firma": None, "datos": None, "avisado": False}
aprendizaje_lock = threading.Lock()
programa_cambiado = threading.Event()
entradas = {}
entradas_lock = threading.Lock()


def clave_de_nota(ruta):
    return re.sub(r"/{2,}", "/", consultas.clave(ruta))


def armar_indice():
    try:
        nuevo = buscador.desde_disco()
    except Exception as error:
        print(f"No se pudo armar el índice de búsqueda ({detalle(error)}).")
        return
    indice["claves"] = frozenset(clave_de_nota(n["ruta"]) for n in nuevo.notas)
    indice["actual"] = nuevo
    indice["armado"] = time.time()


def generar():
    try:
        r = subprocess.run([sys.executable, str(CARPETA / "cerebro.py")], cwd=str(CARPETA), env=configuracion.entorno(),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=ESPERA_GENERAR)
    except subprocess.TimeoutExpired:
        print(f"No se pudo regenerar el cerebro: tardó más de {ESPERA_GENERAR // 60} minutos.")
        return False
    if r.returncode != 0:
        print(f'No se pudo regenerar el cerebro:\n{r.stdout or ""}{r.stderr or ""}')
    return r.returncode == 0


def calcular_huella():
    try:
        return cerebro.huella(EXTRAS)
    except Exception:
        return None


def difundir(nombre, datos):
    mensaje = (f"event: {nombre}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n").encode("utf-8")
    with clientes_lock:
        for q in list(clientes):
            try:
                q.put_nowait(mensaje)
            except queue.Full:
                pass


def pedir_regeneracion():
    with regenerar_lock:
        regenerar["en"] = time.time() + DEMORA


def dispara(ruta):
    try:
        return cerebro.normalizar(ruta) in DISPARADORES or cerebro.dentro_de_fuentes(ruta)
    except (TypeError, ValueError):
        return False


def huella_del_programa():
    return tuple(cerebro.firma(p) for p in sorted(CARPETA.glob("*.py")))


def regenerador(ultima):
    armar_indice()
    proxima = time.time() + CADA_HUELLA
    fallas = 0
    programa = huella_del_programa()
    while True:
        time.sleep(0.25)
        ahora = time.time()
        with regenerar_lock:
            toca = bool(regenerar["en"]) and ahora >= regenerar["en"]
            if toca:
                regenerar["en"] = 0.0
        if not toca and ahora >= proxima:
            proxima = ahora + CADA_HUELLA
            h = calcular_huella()
            toca = h is not None and h != ultima
            if programa is not None and huella_del_programa() != programa:
                programa = None
                programa_cambiado.set()
                print("Se actualizó el programa de Neuromapa: este mapa sigue con el de antes. Para usar el nuevo, abrilo "
                      "de nuevo (el mapa nuevo apaga a este solo).", flush=True)
        if toca:
            with regenerar_lock:
                regenerar["en"] = 0.0
            h = calcular_huella()
            if generar():
                armar_indice()
                difundir("cambio", {"t": time.time()})
                fallas = 0
                if h is not None:
                    ultima = h
            else:
                fallas += 1
                if fallas >= REINTENTOS:
                    print(f"Neuromapa no pudo rearmar la página {fallas} veces seguidas; vuelvo a intentar cuando "
                          "cambie otra nota.")
                    fallas = 0
                    if h is not None:
                        ultima = h
            proxima = time.time() + CADA_HUELLA


def finito(texto):
    valor = float(texto)
    return valor if math.isfinite(valor) else None


class Uso:
    def __init__(self):
        self.lock = threading.Lock()
        self.cuentas = {}
        self.desde = None
        self.abiertos = {}
        self.cerrados = deque(maxlen=RECORRIDOS * 5)
        self.episodios = 0
        self.ultimos = deque(maxlen=PREVIOS)
        self.trabajo = deque(maxlen=TRABAJO_TOPE)
        self.orden = 0
        self.rotados = {"leidos": 0, "sinLeer": 0}
        self.consultas = consultas.Medidor(registro.sesiones_de_prueba(EN_VIVO))

    def cuenta(self, ruta):
        clave = str(ruta).replace("\\", "/").lower()
        if not clave.endswith(".md"):
            return None
        return self.cuentas.setdefault(clave, {"leer": 0, "editar": 0, "crear": 0, "buscar": 0, "ultimo": 0,
                                               "shell": 0, "parcial": 0, "falla": 0})

    def anotar(self, ev):
        fase = ev.get("e", "post")
        k = ev.get("k")
        guardado = ev
        if k == "buscar" and "p" in ev:
            guardado = {x: y for x, y in ev.items() if x != "p"}
        self.orden += 1
        self.ultimos.append((self.orden, guardado))
        if fase == "post" and k in ("leer", "editar", "crear", "buscar"):
            self.trabajo.append((self.orden, guardado))
        ruta = ev.get("f")
        if fase == "usuario":
            self.cerrar_episodio((str(ev.get("s") or ""), ""))
            return
        if fase == "falla":
            c = self.cuenta(ruta) if ruta else None
            if c is not None:
                c["falla"] += 1
            return
        if fase != "post":
            return
        fs = ev.get("fs")
        rutas = [str(r) for r in fs[:MAXIMO_FS] if isinstance(r, str)] if isinstance(fs, list) and k in ("leer", "buscar") else []
        if not ruta and not rutas:
            return
        t = numero(ev.get("t"))
        if t and (self.desde is None or t < self.desde):
            self.desde = t
        if ruta:
            c = self.cuenta(ruta)
            if c is not None:
                if k in ("leer", "editar", "crear", "buscar"):
                    c[k] += 1
                c["ultimo"] = max(c["ultimo"], t)
                r = ev.get("r")
                if k == "leer" and isinstance(r, list) and len(r) == 3 and all(numero(x) for x in r[1:]) and r[1] < r[2]:
                    c["parcial"] += 1
                if k in ("leer", "editar", "crear"):
                    self.anotar_recorrido(ev, str(ruta), t)
        for otra in rutas:
            c = self.cuenta(otra)
            if c is None:
                continue
            c[k] += 1
            c["shell"] += 1
            c["ultimo"] = max(c["ultimo"], t)
            if k == "leer":
                self.anotar_recorrido(ev, otra, t)

    def cerrar_episodio(self, clave):
        r = self.abiertos.pop(clave, None)
        if r is not None and len(set(r["rutas"])) >= 3:
            self.cerrados.append(r)

    def anotar_recorrido(self, ev, ruta, t):
        s = str(ev.get("s") or "")
        if not s:
            return
        a = str(ev.get("a") or "")
        clave = (s, a)
        r = self.abiertos.get(clave)
        if r is not None and t - r["t"] > HUECO_EPISODIO:
            self.cerrar_episodio(clave)
            r = None
        if r is None:
            for otra in [x for x, e in self.abiertos.items() if t - e["t"] > HUECO_EPISODIO]:
                self.cerrar_episodio(otra)
            self.episodios += 1
            r = {"s": s, "ep": self.episodios, "a": a, "at": "", "c": "", "t0": t, "t": t, "rutas": []}
            self.abiertos[clave] = r
        if ev.get("c"):
            r["c"] = str(ev["c"])
        if ev.get("at") and not r["at"]:
            r["at"] = str(ev["at"])
        r["t"] = max(r["t"], t)
        if not r["rutas"] or r["rutas"][-1] != ruta:
            r["rutas"].append(ruta)
            if len(r["rutas"]) > 2 * PASOS:
                del r["rutas"][:-PASOS]

    def resumen(self):
        with self.lock:
            todos = list(self.cerrados) + [r for r in self.abiertos.values() if len(set(r["rutas"])) >= 3]
            recorridos = sorted(todos, key=lambda r: r["t"], reverse=True)[:RECORRIDOS]
            datos = {"desde": self.desde, "rutas": self.cuentas, "rotados": self.rotados, "consultas": self.consultas.resumen(),
                     "recorridos": [dict(r, rutas=r["rutas"][-PASOS:]) for r in recorridos]}
            return json.dumps(datos, ensure_ascii=False).encode("utf-8")

    def previos(self):
        limite = time.time() - VENTANA_TRABAJO
        with self.lock:
            juntos = dict(x for x in self.trabajo if numero(x[1].get("t")) >= limite)
            juntos.update(self.ultimos)
            return json.dumps([juntos[i] for i in sorted(juntos)], ensure_ascii=False)


uso = Uso()


def decodificar(linea):
    try:
        ev = json.loads(linea.decode("utf-8"), parse_constant=lambda _: None, parse_float=finito)
        if isinstance(ev, dict) and linea.count(b"[") + linea.count(b"{") > ANIDADO_SOSPECHOSO:
            json.dumps(ev)
    except (ValueError, RecursionError):
        return None
    return ev if isinstance(ev, dict) else None


def rotados_recientes(cuantos=None):
    fechados = []
    for archivo in EN_VIVO.glob("eventos-*.jsonl"):
        try:
            fechados.append((archivo.stat().st_mtime, archivo.name, archivo))
        except OSError:
            continue
    fechados.sort()
    return [archivo for _, _, archivo in fechados[-(cuantos or ROTADOS_AL_ARRANCAR):]]


def nombre_logico(archivo):
    m = RE_ROTADO.match(archivo.name)
    return m.group(1) if m else None


def rotados_todos():
    salida = {}
    for archivo in EN_VIVO.glob("eventos-*.jsonl*"):
        logico = nombre_logico(archivo)
        if logico and (logico not in salida or not archivo.name.endswith(".gz")):
            salida[logico] = archivo
    return salida


def leer_rotado(archivo):
    crudo = archivo.read_bytes()
    return gzip.decompress(crudo) if archivo.name.endswith(".gz") else crudo


def cuando_roto(archivo):
    m = RE_ROTADO.match(archivo.name)
    try:
        return time.mktime(time.strptime(m.group(2) + m.group(3), "%Y%m%d%H%M%S"))
    except (AttributeError, ValueError, OverflowError):
        return archivo.stat().st_mtime


def dia_de(t):
    try:
        return time.strftime("%Y-%m-%d", time.localtime(t)) if t else "sin-fecha"
    except (OverflowError, OSError, ValueError):
        return "sin-fecha"


def resumir_rotado(archivo):
    dias = {}
    eventos = 0
    for linea in leer_rotado(archivo).split(b"\n"):
        ev = decodificar(linea) if linea.strip() else None
        if ev is None:
            continue
        eventos += 1
        dia = dia_de(numero(ev.get("t")))
        cuenta = dias.get(dia)
        if cuenta is None:
            cuenta = dias[dia] = {"eventos": 0, "uso": Uso()}
        cuenta["eventos"] += 1
        try:
            cuenta["uso"].anotar(ev)
        except Exception:
            pass
    return {"eventos": eventos, "dias": {dia: {"eventos": c["eventos"], "desde": c["uso"].desde, "notas": c["uso"].cuentas}
                                         for dia, c in sorted(dias.items())}}


def cargar_resumen():
    datos = leer_objeto_json(EN_VIVO / RESUMEN)
    if datos.get("version") != VERSION_RESUMEN or not isinstance(datos.get("archivos"), dict):
        datos = {"version": VERSION_RESUMEN, "archivos": {}}
    return datos


def comprimir(archivo):
    crudo = archivo.read_bytes()
    destino = archivo.with_name(f"{archivo.name}.gz")
    if not destino.exists():
        escribir_atomico(destino, gzip.compress(crudo, 6))
    try:
        igual = gzip.decompress(destino.read_bytes()) == crudo
    except (OSError, EOFError, gzip.BadGzipFile):
        igual = False
    if igual:
        archivo.unlink()
    return igual


def ordenar_registros(ahora=None):
    if not ordenar_lock.acquire(blocking=False):
        return None
    try:
        resumen = cargar_resumen()
        nuevos = 0
        for logico, archivo in sorted(rotados_todos().items()):
            if logico in resumen["archivos"]:
                continue
            try:
                resumen["archivos"][logico] = resumir_rotado(archivo)
                nuevos += 1
            except (OSError, EOFError, gzip.BadGzipFile):
                continue
        if nuevos:
            escribir_atomico(EN_VIVO / RESUMEN, json.dumps(resumen, ensure_ascii=False, separators=(",", ":")))
        limite = (time.time() if ahora is None else ahora) - DIAS_SIN_COMPRIMIR * 86400
        comprimidos = 0
        for logico, archivo in sorted(rotados_todos().items()):
            if archivo.name.endswith(".gz") or logico not in resumen["archivos"] or cuando_roto(archivo) > limite:
                continue
            try:
                comprimidos += comprimir(archivo)
            except OSError:
                continue
        dias = cerebro.CONFIG["borrar_registros_dias"]
        borrados = 0
        if dias:
            viejo = (time.time() if ahora is None else ahora) - dias * 86400
            for logico, archivo in sorted(rotados_todos().items()):
                if logico not in resumen["archivos"] or cuando_roto(archivo) > viejo:
                    continue
                try:
                    archivo.unlink()
                    borrados += 1
                except OSError:
                    continue
        return {"resumen": resumen, "nuevos": nuevos, "comprimidos": comprimidos, "borrados": borrados}
    finally:
        ordenar_lock.release()


def sumar_resumenes(resumen, leidos):
    ya = {nombre_logico(a) for a in leidos}
    sumados = 0
    with uso.lock:
        for logico, datos in resumen["archivos"].items():
            if logico in ya or not isinstance(datos, dict):
                continue
            sumados += 1
            for dia in (datos.get("dias") or {}).values():
                if not isinstance(dia, dict):
                    continue
                desde = numero(dia.get("desde"))
                if desde and (uso.desde is None or desde < uso.desde):
                    uso.desde = desde
                for clave, c in (dia.get("notas") or {}).items():
                    destino = uso.cuenta(clave)
                    if destino is None or not isinstance(c, dict):
                        continue
                    for campo in CAMPOS_USO:
                        destino[campo] += numero(c.get(campo))
                    destino["ultimo"] = max(destino["ultimo"], numero(c.get("ultimo")))
        total = len(rotados_todos())
        uso.rotados = {"leidos": len(ya), "resumidos": sumados, "sinLeer": max(0, total - len(ya) - sumados)}
    return sumados


def ordenar_en_fondo(leidos=None):
    try:
        hecho = ordenar_registros()
    except Exception as error:
        print(f"No pude ordenar los registros viejos ({detalle(error)}).")
        return
    if hecho and leidos is not None:
        sumar_resumenes(hecho["resumen"], leidos)


def datos_aprendidos():
    import aprender
    actual = indice["actual"]
    if actual is None:
        return None
    return aprender.para_la_pagina(actual.notas)[0]


def aprender_una_vez(aprender):
    if not programa_cambiado.is_set():
        aprender.quizas(EN_VIVO, cada=APRENDER_CADA)
    ruta = EN_VIVO / aprender.ARCHIVO
    firma = ruta.stat().st_mtime_ns if ruta.exists() else None
    if firma != aprendizaje["firma"] and indice["actual"] is not None:
        datos = datos_aprendidos()
        with aprendizaje_lock:
            aprendizaje.update(firma=firma, datos=datos)
        difundir("aprendido", datos)


def aprendiz():
    import aprender
    while True:
        try:
            aprender_una_vez(aprender)
        except Exception as error:
            if not aprendizaje["avisado"]:
                print(f"No pude rearmar lo aprendido ({detalle(error)}).")
                aprendizaje["avisado"] = True
        time.sleep(APRENDER_CADA / 4)


def nota_del_cerebro(ruta):
    if clave_de_nota(ruta) in indice["claves"]:
        return True
    try:
        return cerebro.dentro_de_fuentes(ruta)
    except (TypeError, ValueError):
        return False


def ruta_segura(ruta):
    if not isinstance(ruta, str) or not ruta or len(ruta) > 400:
        return None
    if "://" not in ruta and ruta.lower().endswith(".md") and all(ord(x) >= 32 for x in ruta):
        return ruta if nota_del_cerebro(ruta) else ".md"
    extension = os.path.splitext(ruta.replace("\\", "/").rsplit("/", 1)[-1])[1]
    return extension.lower() if EXTENSION.match(extension) else None


def motivo_seguro(motivo):
    if not isinstance(motivo, list) or len(motivo) != 4 or motivo[0] not in MOTIVOS_PISTA:
        return None
    if not all(type(x) is int and 0 <= x < 10 ** 7 for x in motivo[1:3]):
        return None
    origen = ruta_segura(motivo[3]) if motivo[3] else ""
    return None if origen is None else [motivo[0], motivo[1], motivo[2], origen]


def raiz_segura(carpeta):
    if not isinstance(carpeta, str) or not carpeta:
        return None
    r = re.sub(r"/\.claude/worktrees/[^/]+", "", carpeta.replace("\\", "/"), flags=re.I)
    minusculas = r.lower().rstrip("/")
    for raiz, nombre in RAICES_HISTORIA:
        if minusculas == raiz or minusculas.startswith(f"{raiz}/"):
            return f"{r[0].upper()}:\\{nombre}" if re.match(r"[A-Za-z]:", r) else f"/{nombre}"
    return None


def evento_seguro(ev):
    t = numero(ev.get("t"))
    s = ev.get("s")
    fase = ev.get("e", "post")
    if t <= 0 or not isinstance(s, str) or not NOMBRE_SEGURO.match(s) or fase not in FASES_HISTORIA:
        return None
    k = ev.get("k")
    limpio = {"t": t, "s": s, "e": fase, "k": k if k in TIPOS_HISTORIA else "otro"}
    for campo in ("h", "a", "at"):
        valor = ev.get(campo)
        if isinstance(valor, str) and NOMBRE_SEGURO.match(valor):
            limpio[campo] = valor
    if ev.get("b") in COMANDOS_HISTORIA:
        limpio["b"] = ev["b"]
    if ev.get("o") == "app":
        limpio["o"] = "app"
    if limpio["k"] == "consulta" and ev.get("p") in registro.OPCIONES_CONSULTA:
        limpio["p"] = ev["p"]
    elif fase in ("inicio", "compacta") and ev.get("p") in MOTIVOS_HISTORIA:
        limpio["p"] = ev["p"]
    elif fase == "guarda" and ev.get("p") in ("compact", "fin"):
        limpio["p"] = ev["p"]
    if fase == "guarda" and type(ev.get("n")) is int and 0 < ev["n"] < 10 ** 6:
        limpio["n"] = ev["n"]
    m = ev.get("m")
    if isinstance(m, list) and len(m) == 2 and all(type(x) is int and 0 <= x < 10 ** 7 for x in m):
        limpio["m"] = m
    r = ev.get("r")
    if isinstance(r, list) and len(r) == 3 and all(type(x) is int and 0 <= x < 10 ** 7 for x in r):
        limpio["r"] = r
    x = ev.get("x")
    if fase == "falla" and isinstance(x, list) and len(x) == 2 and all(v in (0, 1) and type(v) is int for v in x):
        limpio["x"] = x
    for campo, tope in (("d", 10 ** 8), ("xc", 2 ** 32), ("bg", 2), ("nr", 2), ("sa", 2)):
        valor = ev.get(campo)
        if type(valor) is int and 0 <= valor < tope:
            limpio[campo] = valor
    f = ruta_segura(ev.get("f"))
    if f:
        limpio["f"] = f
    fs = ev.get("fs")
    if isinstance(fs, list):
        seguras = [x for x in (ruta_segura(r) for r in fs[:MAXIMO_FS]) if x]
        if seguras:
            limpio["fs"] = seguras
        fp = ev.get("fp")
        motivos = [motivo_seguro(m) for m in fp] if fase == "aviso" and isinstance(fp, list) and len(fp) == len(fs) else []
        if motivos and len(seguras) == len(fs) and all(motivos):
            limpio["fp"] = motivos
    c = raiz_segura(ev.get("c"))
    if c:
        limpio["c"] = c
    return limpio


def archivos_historia(desde, hasta):
    fechados = []
    for archivo in EN_VIVO.glob("eventos-*.jsonl"):
        try:
            fechados.append((archivo.stat().st_mtime, archivo.name, archivo))
        except OSError:
            continue
    fechados.sort()
    salida = []
    anterior = 0
    for fechado, _, archivo in fechados:
        if fechado >= desde and anterior <= hasta:
            salida.append(archivo)
        anterior = fechado
    return salida + ([REGISTRO] if anterior <= hasta else [])


def eventos_historia(desde, hasta):
    eventos = []
    for archivo in archivos_historia(desde, hasta):
        try:
            crudo = archivo.read_bytes()
        except OSError:
            continue
        for linea in crudo.split(b"\n"):
            if not linea.strip():
                continue
            previo = T_DE_LINEA.match(linea)
            if previo:
                try:
                    t = float(previo.group(1))
                except ValueError:
                    t = None
                if t is not None and not desde <= t <= hasta:
                    continue
            ev = decodificar(linea)
            if ev is None or not desde <= numero(ev.get("t")) <= hasta:
                continue
            limpio = evento_seguro(ev)
            if limpio is not None:
                eventos.append(limpio)
    eventos.sort(key=lambda x: x["t"])
    return eventos


def resumen_por_minuto(eventos, desde, hasta):
    minutos = {}
    totales = {"eventos": 0, "usuario": 0, "commit": 0, "compila": 0, "editar": 0, "crear": 0, "leer": 0, "buscar": 0,
               "ejecutar": 0, "consulta": 0, "falla": 0, "espera": 0, "compacta": 0, "fin": 0}
    agentes, chats, editadas, leidas = set(), set(), set(), set()
    tocadas = {}
    lineas = [0, 0]
    for ev in eventos:
        clave = int(ev["t"] // 60) * 60
        m = minutos.get(clave)
        if m is None:
            m = minutos[clave] = {"t": clave, "n": 0, "chats": {}}
        m["n"] += 1
        m["chats"][ev["s"]] = m["chats"].get(ev["s"], 0) + 1
        totales["eventos"] += 1
        chats.add(ev["s"])
        if ev.get("a"):
            agentes.add(ev["a"])
        fase, k = ev["e"], ev["k"]
        marcas = []
        if fase in ("usuario", "falla", "espera", "compacta", "fin"):
            marcas.append(fase)
        elif fase == "post":
            if k in totales:
                marcas.append(k)
            if ev.get("b") in ("commit", "compila"):
                marcas.append(ev["b"])
            md = [x for x in [ev.get("f")] + ev.get("fs", []) if x and len(x) > 3 and x.lower().endswith(".md")]
            if k in ("editar", "crear"):
                editadas.update(md[:1])
                md = md[:1]
            elif k == "leer":
                leidas.update(md)
            else:
                md = []
            for ruta in md:
                tocadas[ruta] = tocadas.get(ruta, 0) + 1
            if ev.get("m"):
                lineas[0] += ev["m"][0]
                lineas[1] += ev["m"][1]
        for marca in marcas:
            totales[marca] += 1
            m[marca] = m.get(marca, 0) + 1
    totales.update({"agentes": len(agentes), "chats": sorted(chats), "editadas": sorted(editadas)[:HISTORIA_LISTA],
                    "leidas": sorted(leidas)[:HISTORIA_LISTA], "lineas": lineas,
                    "tocadas": sorted(tocadas.items(), key=lambda x: (-x[1], x[0]))[:HISTORIA_TOCADAS],
                    "primero": eventos[0]["t"] if eventos else None,
                    "ultimo": eventos[-1]["t"] if eventos else None})
    return {"desde": desde, "hasta": hasta, "modo": "minuto", "minutos": [minutos[x] for x in sorted(minutos)],
            "totales": totales}


def historia(desde, hasta, resumida):
    eventos = eventos_historia(desde, hasta)
    if resumida:
        return resumen_por_minuto(eventos, desde, hasta)
    recortado = len(eventos) > HISTORIA_TOPE
    siguiente = None
    if recortado:
        siguiente = eventos[HISTORIA_TOPE]["t"]
        eventos = [x for x in eventos[:HISTORIA_TOPE] if x["t"] < siguiente]
    return {"desde": desde, "hasta": hasta, "eventos": eventos, "recortado": recortado, "siguiente": siguiente,
            "tope": HISTORIA_TOPE}


class Lector:
    def __init__(self):
        self.pos = 0
        self.resto = b""
        self.ino = None
        self.leidos = []

    def procesar(self, trozo, en_vivo, final=False):
        lineas = (self.resto + trozo).split(b"\n")
        self.resto = b"" if final else lineas.pop()
        eventos = [ev for ev in (decodificar(linea) for linea in lineas if linea.strip()) if ev is not None]
        if not eventos:
            return
        with uso.lock:
            for ev in eventos:
                try:
                    uso.anotar(ev)
                except Exception:
                    pass
                try:
                    uso.consultas.anotar(ev)
                except Exception:
                    pass
        if not en_vivo:
            return
        for ev in eventos:
            try:
                difundir("accion", ev)
            except (ValueError, TypeError, RecursionError):
                continue
            if ev.get("e", "post") == "post" and ev.get("k") in ("editar", "crear") and ev.get("f") and dispara(str(ev["f"])):
                pedir_regeneracion()

    def cargar_historial(self):
        permisos.crear(EN_VIVO)
        leidos = rotados_recientes()
        self.leidos = leidos
        uso.rotados = {"leidos": len(leidos), "sinLeer": max(0, len(list(EN_VIVO.glob("eventos-*.jsonl"))) - len(leidos))}
        for archivo in leidos:
            try:
                crudo = archivo.read_bytes()
            except OSError:
                continue
            self.resto = b""
            self.procesar(crudo, False, final=True)
        self.resto = b""
        try:
            estado = os.stat(REGISTRO)
            with open(REGISTRO, "rb") as f:
                crudo = f.read()
        except OSError:
            return
        self.ino = estado.st_ino or None
        self.pos = len(crudo)
        self.procesar(crudo, False)

    def buscar_rotado(self):
        candidatos = sorted(EN_VIVO.glob("eventos-*.jsonl"), reverse=True)
        for archivo in candidatos:
            try:
                estado = os.stat(archivo)
            except OSError:
                continue
            if self.ino is not None and estado.st_ino == self.ino:
                return archivo
            if self.ino is None and estado.st_size >= self.pos:
                return archivo
        return None

    def terminar_rotado(self):
        viejo = self.buscar_rotado()
        if viejo is not None:
            try:
                with open(viejo, "rb") as f:
                    f.seek(self.pos)
                    trozo = f.read()
                self.procesar(trozo, True, final=True)
            except OSError:
                pass
        self.pos, self.resto = 0, b""
        threading.Thread(target=ordenar_en_fondo, daemon=True).start()

    def revisar(self):
        try:
            estado = os.stat(REGISTRO)
        except OSError:
            return
        ino = estado.st_ino or None
        if (ino is not None and self.ino is not None and ino != self.ino) or estado.st_size < self.pos:
            self.terminar_rotado()
        self.ino = ino
        if estado.st_size > self.pos:
            with open(REGISTRO, "rb") as f:
                f.seek(self.pos)
                trozo = f.read(estado.st_size - self.pos)
            self.pos += len(trozo)
            self.procesar(trozo, True)


def seguir_registro(lector):
    while True:
        time.sleep(0.25)
        try:
            lector.revisar()
        except Exception:
            pass


_clave = []


def clave():
    if not _clave:
        try:
            guardada = ARCHIVO_CLAVE.read_text(encoding="utf-8").strip()
        except OSError:
            guardada = ""
        if len(guardada) < 20:
            guardada = secrets.token_urlsafe(24)
            try:
                permisos.crear(EN_VIVO)
                escribir_atomico(ARCHIVO_CLAVE, guardada)
            except OSError:
                pass
        _clave.append(guardada)
    return _clave[0]


def nombre_galleta(puerto):
    return f"{GALLETA}_{puerto}"


def valor_galleta():
    return firmas.firmar(clave(), "galleta")


def nueva_entrada(ahora=None):
    ahora = time.monotonic() if ahora is None else ahora
    numero = secrets.token_urlsafe(18)
    with entradas_lock:
        for viejo in [n for n, vence in entradas.items() if vence <= ahora]:
            del entradas[viejo]
        entradas[numero] = ahora + VIDA_ENTRADA
    return numero


def usar_entrada(numero):
    with entradas_lock:
        vence = entradas.pop(numero, None)
    return vence is not None and time.monotonic() < vence


class Manejador(http.server.SimpleHTTPRequestHandler):
    error_message_format = ('<!doctype html><meta charset="utf-8"><title>Neuromapa</title>'
                            '<p style="font:16px system-ui;margin:40px">%(explain)s</p>')
    error_content_type = "text/html; charset=utf-8"

    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(cerebro.DATOS), **k)

    def send_error(self, code, message=None, explain=None):
        super().send_error(code, None, ERRORES.get(int(code), "No se pudo atender el pedido."))

    def galleta(self):
        try:
            galletas = http.cookies.SimpleCookie(self.headers.get("Cookie") or "")
        except http.cookies.CookieError:
            return ""
        nombre = nombre_galleta(self.server.server_address[1])
        return galletas[nombre].value if nombre in galletas else ""

    def autorizado(self):
        self.galleta_vieja = False
        firma = self.headers.get(CABECERA_FIRMA)
        if firma:
            return firmas.pedido_valido(clave(), self.path, firma)
        dada = self.headers.get(CABECERA_CLAVE)
        if dada:
            return hmac.compare_digest(dada.encode("utf-8"), clave().encode("utf-8"))
        galleta = self.galleta().encode("utf-8")
        self.galleta_vieja = bool(galleta) and hmac.compare_digest(galleta, clave().encode("utf-8"))
        return bool(galleta) and (self.galleta_vieja or hmac.compare_digest(galleta, valor_galleta().encode("utf-8")))

    def poner_galleta(self):
        galleta = nombre_galleta(self.server.server_address[1])
        self.send_header("Set-Cookie", f"{galleta}={valor_galleta()}; Path=/; Max-Age={DURACION_GALLETA}; HttpOnly; "
                                       "SameSite=Strict")

    def entrar(self):
        parametros = urllib.parse.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
        dada = (parametros.get("clave") or [""])[0]
        numero = (parametros.get("entrada") or [""])[0]
        if not (dada or numero) or self.camino() not in ("/", "/cerebro.html"):
            return False
        if dada:
            if not hmac.compare_digest(dada.encode("utf-8"), clave().encode("utf-8")):
                return False
        elif not usar_entrada(numero) and not self.autorizado():
            return False
        self.send_response(302)
        self.poner_galleta()
        self.send_header("Location", self.pagina_con_opciones())
        self.end_headers()
        return True

    def pagina_con_opciones(self):
        consulta = self.path.split("?", 1)[1].split("#", 1)[0] if "?" in self.path else ""
        opciones = [o for o in consulta.split("&")
                    if RE_OPCION_PAGINA.fullmatch(o) and o.split("=", 1)[0] not in ("clave", "entrada")]
        return "/cerebro.html" + ("?" + "&".join(opciones) if opciones else "")

    def dar_entrada(self):
        firma = self.headers.get(CABECERA_FIRMA)
        if not firma or not firmas.pedido_valido(clave(), self.path, firma):
            self.sin_clave()
            return
        self.enviar_json(json.dumps({"entrada": nueva_entrada()}).encode("utf-8"))

    def sin_clave(self):
        self.send_response(403)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(SIN_CLAVE)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(SIN_CLAVE)

    def log_message(self, formato, *args):
        pass

    def end_headers(self):
        nonce = getattr(self, "nonce", None)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy",
                         POLITICA.format(scripts=f"'nonce-{nonce}' 'strict-dynamic'" if nonce else "'none'"))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def enviar_json(self, cuerpo, estado=200):
        self.send_response(estado)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def host_valido(self):
        puerto = self.server.server_address[1]
        host = (self.headers.get("Host") or "").strip().lower()
        return host in (f"127.0.0.1:{puerto}", f"localhost:{puerto}")

    def camino(self):
        return self.path.split("?", 1)[0].split("#", 1)[0]

    def do_HEAD(self):
        if not self.host_valido():
            self.send_error(403)
            return
        if not self.autorizado():
            self.sin_clave()
            return
        if self.camino() in ESTATICOS:
            self.enviar_pagina(cuerpo=False)
            return
        self.send_error(404)

    def enviar_pagina(self, cuerpo=True):
        try:
            html = (cerebro.DATOS / "cerebro.html").read_bytes()
        except OSError:
            self.send_error(404)
            return
        self.nonce = secrets.token_urlsafe(18)
        html = RE_ETIQUETA_SCRIPT.sub(f'<script nonce="{self.nonce}">'.encode("ascii"), html)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            if getattr(self, "galleta_vieja", False):
                self.poner_galleta()
            self.end_headers()
        finally:
            self.nonce = None
        if cuerpo:
            self.wfile.write(html)

    def do_GET(self):
        if not self.host_valido():
            self.send_error(403)
            return
        if self.entrar():
            return
        camino = self.camino()
        if camino == "/hola":
            self.hola()
            return
        if camino == "/apagar":
            self.apagar()
            return
        if camino == "/entrada":
            self.dar_entrada()
            return
        if not self.autorizado():
            self.sin_clave()
            return
        if camino == "/":
            self.send_response(302)
            self.send_header("Location", self.pagina_con_opciones())
            self.end_headers()
            return
        if camino == "/uso.json":
            self.enviar_json(uso.resumen())
            return
        if camino == "/eventos":
            self.eventos()
            return
        if camino in ("/buscar", "/sobre"):
            self.buscar(camino)
            return
        if camino == "/historia":
            self.historia()
            return
        if camino in ESTATICOS:
            self.enviar_pagina()
            return
        self.send_error(404)

    def hola(self):
        parametros = urllib.parse.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
        desafio = (parametros.get("n") or [""])[0]
        if not firmas.RE_NUMERO.fullmatch(desafio):
            self.send_error(400)
            return
        self.enviar_json(json.dumps({"firma": firmas.del_servidor(clave(), desafio)}).encode("utf-8"))

    def apagar(self):
        firma = self.headers.get(CABECERA_FIRMA)
        if not firma or not firmas.pedido_valido(clave(), self.path, firma):
            self.sin_clave()
            return
        self.enviar_json(b'{"apagando": true}')
        print("Otro Neuromapa sobre estos mismos datos pidió el lugar: me apago para que arranque él.", flush=True)
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def buscar(self, camino):
        parametros = urllib.parse.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")

        def parametro(nombre):
            return (parametros.get(nombre) or [""])[0]

        consulta = parametro("q")[:LARGO_CONSULTA]
        actual = indice["actual"]
        if actual is None:
            self.enviar_json(json.dumps({"listo": False, "consulta": consulta, "resultados": []}).encode("utf-8"), 503)
            return
        grupos = [g for g in parametro("grupos").split(",") if g] or None
        if parametro("alcance") == "foco":
            grupos = list(buscador.ALCANCE)
        try:
            if camino == "/sobre":
                import aprender
                sin = parametro("sin") == "aprendido"
                memoria = aprender.contexto(parametro("cwd")[:LARGO_CWD] or None, parametro("sesion")[:8], sin_aprendido=sin)
                datos = actual.sobre(consulta, grupos, memoria=memoria)
                if sin and (memoria is None or memoria.aprendido is None):
                    datos["sinAprendido"] = True
            else:
                try:
                    cuantos = int(parametro("n") or RESULTADOS)
                except ValueError:
                    cuantos = RESULTADOS
                datos = actual.buscar(consulta, max(1, min(MAXIMO_RESULTADOS, cuantos)), grupos)
        except Exception as error:
            cuerpo = {"listo": True, "error": type(error).__name__, "consulta": consulta}
            self.enviar_json(json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"), 500)
            return
        datos["listo"] = True
        datos["armado"] = indice["armado"]
        datos["secciones"] = len(actual.secciones)
        self.enviar_json(json.dumps(datos, ensure_ascii=False).encode("utf-8"))

    def historia(self):
        parametros = urllib.parse.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")

        def momento(nombre):
            try:
                return finito((parametros.get(nombre) or [""])[0])
            except ValueError:
                return None

        ahora = time.time()
        hasta = momento("hasta")
        hasta = ahora if hasta is None else min(hasta, ahora + 60)
        desde = momento("desde")
        desde = max(hasta - HISTORIA_DIA if desde is None else desde, hasta - HISTORIA_MAXIMA)
        if desde >= hasta:
            self.enviar_json(json.dumps({"error": "desde tiene que ser anterior a hasta"}).encode("utf-8"), 400)
            return
        try:
            datos = historia(desde, hasta, (parametros.get("modo") or [""])[0] == "minuto")
        except Exception as error:
            self.enviar_json(json.dumps({"error": type(error).__name__}).encode("utf-8"), 500)
            return
        self.enviar_json(json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    def list_directory(self, path):
        self.send_error(404)
        return None

    def eventos(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = queue.Queue(maxsize=500)
        with clientes_lock:
            clientes.append(q)
        try:
            try:
                recientes = uso.previos()
            except (ValueError, TypeError, RecursionError):
                recientes = "[]"
            previos = f"event: previos\ndata: {recientes}\n\n"
            with aprendizaje_lock:
                hay, aprendido = aprendizaje["firma"] is not None, aprendizaje["datos"]
            if hay:
                previos += f"event: aprendido\ndata: {json.dumps(aprendido, ensure_ascii=False)}\n\n"
            self.wfile.write(previos.encode("utf-8"))
            self.wfile.flush()
            while True:
                try:
                    mensaje = q.get(timeout=15)
                except queue.Empty:
                    mensaje = b": latido\n\n"
                self.wfile.write(mensaje)
                self.wfile.flush()
        except (ConnectionError, OSError):
            pass
        finally:
            self.close_connection = True
            with clientes_lock:
                if q in clientes:
                    clientes.remove(q)


class Servidor(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            return
        print(f"Neuromapa: falló un pedido de {client_address[0]} (sigue andando). El detalle, en inglés:", file=sys.stderr)
        traceback.print_exc()


def texto_uso():
    nombre = "neuromapa abrir" if sys.argv[0] == "neuromapa abrir" else "servidor.py"
    return f"Uso: {nombre} [--sin-navegador] [--puerto N] [--demo] [--reiniciar]"


def texto_ayuda():
    return "\n".join([texto_uso(), "Arma la página y abre el mapa en vivo en el navegador, con la clave puesta.", "",
                      "  --demo           el mapa de las notas inventadas de demo/, en vez de las tuyas",
                      "  --reiniciar      apaga el mapa que estaba prendido y arranca uno nuevo (después de actualizar "
                      "o de cambiar el config.json)",
                      "  --sin-navegador  no abre el navegador: dice la dirección y dónde está la clave",
                      f"  --puerto N       usa ese puerto (si no, el primero libre entre {PUERTOS[0]} y {PUERTOS[-1]})"])


def opciones_raras():
    argumentos = sys.argv[1:]
    return [a for i, a in enumerate(argumentos) if a not in OPCIONES and not (i and argumentos[i - 1] == "--puerto")]


def puertos_pedidos():
    if "--puerto" in sys.argv:
        i = sys.argv.index("--puerto")
        try:
            return [int(sys.argv[i + 1])]
        except (IndexError, ValueError):
            print(texto_uso())
            return []
    return list(PUERTOS)


def pedir_entrada(puerto):
    camino = "/entrada"
    conexion = http.client.HTTPConnection("127.0.0.1", puerto, timeout=3)
    try:
        conexion.request("GET", camino, headers={"Host": f"127.0.0.1:{puerto}",
                                                 CABECERA_FIRMA: firmas.del_pedido(clave(), camino)})
        respuesta = conexion.getresponse()
        datos = json.loads(respuesta.read().decode("utf-8")) if respuesta.status == 200 else {}
    except (OSError, ValueError, http.client.HTTPException):
        return None
    finally:
        conexion.close()
    numero = datos.get("entrada") if isinstance(datos, dict) else None
    return numero if isinstance(numero, str) and numero else None


def direccion_para_abrir(puerto, propia=False):
    numero = nueva_entrada() if propia else pedir_entrada(puerto)
    if not numero:
        return direccion_con_clave(puerto)
    return f"http://127.0.0.1:{puerto}/cerebro.html?entrada={numero}"


def direccion_con_clave(puerto):
    return f"http://127.0.0.1:{puerto}/cerebro.html?clave={clave()}"


def a_la_vista(puerto):
    return f"http://127.0.0.1:{puerto}/cerebro.html (la clave está en {ARCHIVO_CLAVE})"


def abrir_navegador(direccion):
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        guardadas = (os.dup(1), os.dup(2))
    except OSError:
        return webbrowser.open(direccion)
    nulo = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(nulo, 1)
        os.dup2(nulo, 2)
        return webbrowser.open(direccion)
    finally:
        os.dup2(guardadas[0], 1)
        os.dup2(guardadas[1], 2)
        for descriptor in (*guardadas, nulo):
            os.close(descriptor)


def aviso_navegador(abierto, solo):
    if abierto:
        return ("Lo mandé a abrir en el navegador con la clave puesta. Si no aparece, entrá a la dirección de arriba "
                "agregándole ?clave= y la clave de ese archivo.")
    cuidado = "no la pegues en la charla" if solo else "no la compartas"
    antes = "Para entrar" if abierto is None else "No pude abrir el navegador"
    return f"{antes}: entrá a la dirección de arriba agregándole ?clave= y la clave de ese archivo ({cuidado})."


def ya_prendido():
    anotado = leer_objeto_json(EN_VIVO / "servidor.json")
    try:
        puerto = int(anotado["puerto"])
    except (KeyError, TypeError, ValueError):
        return None
    if not configuracion.donde.proceso_vivo(anotado.get("pid")):
        return None
    desafio = firmas.numero()
    conexion = http.client.HTTPConnection("127.0.0.1", puerto, timeout=3)
    try:
        conexion.request("GET", f"/hola?n={desafio}", headers={"Host": f"127.0.0.1:{puerto}"})
        respuesta = conexion.getresponse()
        datos = json.loads(respuesta.read().decode("utf-8")) if respuesta.status == 200 else {}
        if isinstance(datos, dict) and firmas.servidor_valido(clave(), desafio, datos.get("firma")):
            return puerto
    except (OSError, ValueError, http.client.HTTPException):
        pass
    finally:
        conexion.close()
    return None


def pedir_apagado(puerto, espera=ESPERA_APAGADO):
    pid = leer_objeto_json(EN_VIVO / "servidor.json").get("pid")
    camino = "/apagar"
    conexion = http.client.HTTPConnection("127.0.0.1", puerto, timeout=3)
    try:
        conexion.request("GET", camino, headers={"Host": f"127.0.0.1:{puerto}",
                                                 CABECERA_FIRMA: firmas.del_pedido(clave(), camino)})
        respuesta = conexion.getresponse()
        respuesta.read()
        if respuesta.status != 200:
            return False
    except (OSError, http.client.HTTPException):
        return False
    finally:
        conexion.close()
    limite = time.monotonic() + espera
    while time.monotonic() < limite:
        if not configuracion.donde.proceso_vivo(pid) and puerto_libre(puerto):
            return True
        time.sleep(0.1)
    return puerto_libre(puerto)


def esperar_al_otro(ruta, espera=ESPERA_ARRANQUE):
    limite = time.monotonic() + espera
    while time.monotonic() < limite:
        puerto = ya_prendido()
        if puerto:
            return puerto, None
        candado = tomar_candado(ruta)
        if candado is not None:
            return None, candado
        time.sleep(0.3)
    return None, None


def puerto_libre(puerto):
    with socket.socket() as prueba:
        if Servidor.allow_reuse_address:
            prueba.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            prueba.bind(("127.0.0.1", puerto))
            return True
        except OSError:
            return False


def borrar_anotado():
    ruta = EN_VIVO / "servidor.json"
    if leer_objeto_json(ruta).get("pid") == os.getpid():
        try:
            ruta.unlink()
        except OSError:
            pass


def apagar_sin_pestanas(servidor, espera=APAGAR_SIN_PESTANAS, cada=15):
    vacio_desde = time.monotonic()
    while True:
        time.sleep(cada)
        with clientes_lock:
            hay = bool(clientes)
        if hay:
            vacio_desde = None
        elif vacio_desde is None:
            vacio_desde = time.monotonic()
        elif time.monotonic() - vacio_desde >= espera:
            print("Neuromapa se apagó: no había ninguna pestaña abierta.")
            servidor.shutdown()
            return


def main():
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:]:
        print(texto_ayuda())
        return 0
    raras = opciones_raras()
    if raras:
        print(f'No conozco {", ".join(raras)}. {texto_uso()}')
        return 2
    abrir = "--sin-navegador" not in sys.argv
    solo = "--apagar-solo" in sys.argv
    puertos = puertos_pedidos()
    if not puertos:
        return 1
    try:
        permisos.crear(EN_VIVO)
    except OSError:
        pass
    ruta_candado = EN_VIVO / CANDADO_ARRANQUE
    candado = tomar_candado(ruta_candado)
    ocupado = candado is None and hay_candados() and EN_VIVO.is_dir()
    if ocupado:
        anterior, candado = esperar_al_otro(ruta_candado)
        if anterior is None and candado is None:
            print("Otro Neuromapa está arrancando sobre estos mismos datos y no terminó de arrancar: esperá unos segundos "
                  "y volvé a abrirlo.")
            return 1
    else:
        anterior = ya_prendido()
    candados = [candado]
    try:
        return arrancar(anterior, candados, ruta_candado, puertos, abrir, solo)
    finally:
        for tomado in candados:
            soltar_candado(tomado)


def arrancar(anterior, candados, ruta_candado, puertos, abrir, solo):
    reiniciar = "--reiniciar" in sys.argv
    if solo and anterior and not reiniciar:
        print(f"Neuromapa ya estaba prendido: {a_la_vista(anterior)}")
        print(aviso_navegador(abrir_navegador(direccion_para_abrir(anterior)) if abrir else None, solo))
        return 0
    if anterior:
        if not pedir_apagado(anterior):
            print(f"Hay otro Neuromapa prendido sobre estos mismos datos (puerto {anterior}) y no se apagó: cerrá su ventana "
                  "y volvé a abrir este. Dos a la vez se pisan lo aprendido.")
            return 1
        if candados[0] is None and hay_candados() and EN_VIVO.is_dir():
            candados[0] = tomar_candado(ruta_candado, ESPERA_APAGADO)
            if candados[0] is None:
                print("El otro Neuromapa no terminó de apagarse: cerrá su ventana y volvé a abrir este.")
                return 1
        if reiniciar:
            print("Apagué el mapa que estaba prendido y arranco uno nuevo, con la versión y la configuración de ahora.",
                  flush=True)
        else:
            print("Había otro Neuromapa prendido sobre estos datos: lo apagué y arranco en su lugar.", flush=True)
        if len(puertos) > 1:
            puertos = [anterior] + [p for p in puertos if p != anterior]
    elif configuracion.donde.proceso_vivo(leer_objeto_json(EN_VIVO / "servidor.json").get("pid")):
        print("Aviso: hay otro proceso anotado como Neuromapa sobre estos datos que no respondió (puede ser una versión "
              "vieja). Si es otra ventana de Neuromapa, cerrala: dos a la vez se pisan lo aprendido.", flush=True)
    huella = calcular_huella()
    if not generar():
        if sys.stdin and sys.stdin.isatty():
            input("Apretá Enter para cerrar.")
        return 1
    servidor = None
    falla = None
    for puerto in puertos:
        try:
            servidor = Servidor(("127.0.0.1", puerto), Manejador)
            break
        except OSError as error:
            falla = error
    if servidor is None:
        cual = f"el puerto {puertos[0]}" if len(puertos) == 1 else f"ningún puerto entre el {puertos[0]} y el {puertos[-1]}"
        print(f"No pude abrir {cual}. El sistema dijo: {falla.strerror or falla}")
        return 1
    lector = Lector()
    lector.cargar_historial()
    threading.Thread(target=ordenar_en_fondo, args=(lector.leidos,), daemon=True).start()
    threading.Thread(target=seguir_registro, args=(lector,), daemon=True).start()
    threading.Thread(target=regenerador, args=(huella,), daemon=True).start()
    threading.Thread(target=aprendiz, daemon=True).start()
    try:
        escribir_atomico(EN_VIVO / "servidor.json", json.dumps({"puerto": servidor.server_address[1], "pid": os.getpid()}))
    except OSError:
        pass
    direccion = direccion_para_abrir(servidor.server_address[1], propia=True)
    demo = " (demo)" if configuracion.archivo() == configuracion.DEMO else ""
    print(f"Neuromapa en vivo{demo}: {a_la_vista(servidor.server_address[1])}", flush=True)
    if solo:
        threading.Thread(target=apagar_sin_pestanas, args=(servidor,), daemon=True).start()
    print(aviso_navegador(abrir_navegador(direccion) if abrir else None, solo))
    if solo:
        print(f"Se apaga solo {APAGAR_SIN_PESTANAS // 60} minutos después de cerrar la última pestaña.", flush=True)
    else:
        print("Cerrá esta ventana para apagarlo.", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        borrar_anotado()
    return 0


if __name__ == "__main__":
    sys.exit(main())
