import calendar
import json
import time

import configuracion
import registro

from aprender_comun import HERRAMIENTAS_CHARLA, PREFIJO_CHARLA, lineas_de, registros
from aprender_memoria import Memoria


def hora_de_charla(sello):
    try:
        return calendar.timegm(time.strptime(str(sello)[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError, OverflowError):
        return 0


def texto_de_pedido(contenido):
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list) and contenido and all(isinstance(c, dict) for c in contenido) \
            and not any(c.get("type") == "tool_result" for c in contenido):
        return next((str(c.get("text") or "") for c in contenido if c.get("type") == "text"), "")
    return ""


def eventos_de_charla(d):
    t = hora_de_charla(d.get("timestamp"))
    sesion = str(d.get("sessionId") or "")[:8]
    if not t or not sesion:
        return []
    s = PREFIJO_CHARLA + sesion
    a = str(d.get("agentId") or "")[:40] if d.get("isSidechain") else ""
    cwd = str(d.get("cwd") or "")
    mensaje = d.get("message") if isinstance(d.get("message"), dict) else {}
    contenido = mensaje.get("content")
    if d.get("type") == "user":
        pedido = texto_de_pedido(contenido).lstrip()
        import hooks_comun
        if a or not pedido or pedido.startswith(("<command-", "<local-command-", "/")) or hooks_comun.del_sistema(pedido):
            return []
        return [{"t": t, "s": s, "e": "usuario", "k": "usuario", "c": cwd}]
    if d.get("type") != "assistant" or not isinstance(contenido, list):
        return []
    salida = []
    for c in contenido:
        if not isinstance(c, dict) or c.get("type") != "tool_use" or not isinstance(c.get("input"), dict):
            continue
        entrada = c["input"]
        nombre_herramienta = c.get("name")
        if nombre_herramienta in HERRAMIENTAS_CHARLA:
            ruta = entrada.get("file_path") or entrada.get("notebook_path")
            if isinstance(ruta, str) and ruta:
                salida.append({"t": t, "s": s, "a": a, "e": "post", "k": HERRAMIENTAS_CHARLA[nombre_herramienta], "f": ruta,
                               "c": cwd, "_id": c.get("id")})
        elif nombre_herramienta in ("Bash", "PowerShell"):
            import hook_evento
            clase, rutas = hook_evento.notas_de_comando(entrada.get("command"), cwd)
            if clase == "leer" and rutas:
                salida.append({"t": t, "s": s, "a": a, "e": "post", "k": "leer", "fs": rutas, "c": cwd, "_id": c.get("id")})
    return salida


def charlas_de(casa):
    try:
        return sorted((casa / "projects").glob("*/**/*.jsonl"))
    except OSError:
        return []


def inicio_del_registro(carpeta, ahora):
    for archivo in registros(carpeta, 0):
        for linea in lineas_de([archivo]):
            m = registro.T_DE_LINEA.match(linea)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    continue
    return ahora


def importar_charlas(memoria, carpeta, ahora, segundos=None, casa=None):
    estado = memoria.charlas
    if estado["listo"]:
        return 0
    comienzo = time.perf_counter()
    if not estado["hasta"]:
        estado["hasta"] = inicio_del_registro(carpeta, ahora)
    hasta = estado["hasta"]
    viejo = Memoria()
    viejo.lazos, viejo.veces, viejo.rutas = memoria.viejo_lazos, memoria.viejo_veces, memoria.rutas
    viejo.proyectos, viejo.raices, viejo.olvidos = memoria.proyectos, memoria.raices, memoria.olvidos
    viejo.ahora, viejo.contar = memoria.ahora, False
    limite = None if segundos is None else comienzo + segundos
    leidos = 0
    for archivo in charlas_de(casa or configuracion.carpeta_de_claude()):
        llave = str(archivo)
        try:
            largo = archivo.stat().st_size
        except OSError:
            continue
        posicion = estado["posiciones"].get(llave, 0)
        if posicion >= largo and llave in estado["posiciones"]:
            continue
        terminado, posicion, cuantos = leer_charla(viejo, archivo, posicion, hasta, limite, estado)
        leidos += cuantos
        estado["posiciones"][llave] = largo if terminado else posicion
        if not terminado:
            return leidos
        viejo.abiertos.clear()
        viejo.pares.clear()
    estado["listo"] = True
    estado["posiciones"] = {}
    return leidos


def resultados_de_charla(d):
    contenido = (d.get("message") or {}).get("content") if isinstance(d.get("message"), dict) else None
    if d.get("type") != "user" or not isinstance(contenido, list):
        return {}
    return {c["tool_use_id"]: c.get("is_error") is True for c in contenido
            if isinstance(c, dict) and c.get("type") == "tool_result" and isinstance(c.get("tool_use_id"), str)}


def leer_charla(viejo, archivo, posicion, hasta, limite, estado):
    leidos = 0
    espera = {}

    def anotar(ev):
        try:
            viejo.anotar(ev)
        except (TypeError, ValueError, AttributeError, KeyError):
            return
        estado["eventos"] += 1

    try:
        with open(archivo, "rb") as f:
            f.seek(posicion)
            while True:
                if limite is not None and leidos and leidos % 2000 == 0 and time.perf_counter() > limite:
                    return False, f.tell(), leidos
                crudo = f.readline()
                if not crudo:
                    return True, f.tell(), leidos
                leidos += 1
                if b'"tool_use"' not in crudo and b'"type":"user"' not in crudo and b'"tool_result"' not in crudo:
                    continue
                try:
                    d = json.loads(crudo)
                except ValueError:
                    continue
                if not isinstance(d, dict):
                    continue
                if hora_de_charla(d.get("timestamp")) >= hasta:
                    return True, f.tell(), leidos
                for ev in eventos_de_charla(d):
                    pedido = ev.pop("_id", None)
                    if isinstance(pedido, str) and pedido:
                        espera.setdefault(pedido, []).append(ev)
                    else:
                        anotar(ev)
                for pedido, error in resultados_de_charla(d).items():
                    for ev in espera.pop(pedido, ()):
                        if not error:
                            anotar(ev)
    except OSError:
        return True, posicion, leidos
    finally:
        for evs in espera.values():
            for ev in evs:
                anotar(ev)
