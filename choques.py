import datetime
import re
import time
from pathlib import PureWindowsPath

import consultas
import registro
from textos import cantidad, sin_control

VENTANA = registro.VENTANA_CHOQUE
DIA = 86400
MARCAS = (b'"k":"editar"', b'"k":"crear"')
TOPE_SALUD = 3
RE_WORKTREE = re.compile(r"[\\/]\.claude[\\/]worktrees[\\/][^\\/]+[\\/]?$", re.I)


def actor_de(ev):
    return str(ev.get("s") or ""), str(ev.get("a") or "")


def ediciones_de(lineas, desde):
    salida = []
    for ev in registro.eventos(lineas, desde, MARCAS):
        if ev.get("e", "post") != "post" or ev.get("k") not in ("editar", "crear"):
            continue
        t = registro.numero(ev.get("t"))
        rutas = [ev["f"]] if isinstance(ev.get("f"), str) else consultas.rutas_de(ev.get("fs"))
        for ruta in rutas:
            salida.append({"t": t, "actor": actor_de(ev), "tipo": str(ev.get("at") or ""), "c": str(ev.get("c") or ""),
                           "ruta": ruta, "clave": consultas.clave(ruta)})
    return salida


def del_registro(desde):
    return ediciones_de(registro.lineas_desde(consultas.EN_VIVO, desde), desde)


def hallar(ediciones, ventana=VENTANA):
    por_archivo = {}
    for e in sorted(ediciones, key=lambda e: e["t"]):
        por_archivo.setdefault(e["clave"], []).append(e)
    choques = []
    for lista in por_archivo.values():
        tandas = [[lista[0]]]
        for e in lista[1:]:
            if e["t"] - tandas[-1][-1]["t"] <= ventana:
                tandas[-1].append(e)
            else:
                tandas.append([e])
        for tanda in tandas:
            actores = {}
            for e in tanda:
                datos = actores.setdefault(e["actor"], {"s": e["actor"][0], "a": e["actor"][1], "tipo": e["tipo"], "c": e["c"],
                                                       "veces": 0, "desde": e["t"], "hasta": e["t"]})
                datos["veces"] += 1
                datos["hasta"] = e["t"]
            if len(actores) > 1:
                choques.append({"ruta": tanda[-1]["ruta"], "desde": tanda[0]["t"], "hasta": tanda[-1]["t"],
                                "actores": sorted(actores.values(), key=lambda x: x["desde"])})
    return sorted(choques, key=lambda c: -c["hasta"])


def nombre_archivo(ruta):
    return PureWindowsPath(ruta).name or ruta


def quien(actor):
    carpeta = RE_WORKTREE.sub("", actor["c"]) if actor["c"] else ""
    proyecto = PureWindowsPath(carpeta).name if carpeta else ""
    chat = "chat" + (" de " + proyecto if proyecto else "") + (" (" + actor["s"] + ")" if actor["s"] else "")
    if actor["a"]:
        return "un agente" + (" " + actor["tipo"] if actor["tipo"] else "") + " del " + chat
    return f"el {chat}"


def hora(t):
    return datetime.datetime.fromtimestamp(t).strftime("%H:%M")


def tramo(desde, hasta):
    return hora(desde) + (" a " + hora(hasta) if hora(hasta) != hora(desde) else "")


def fecha(t):
    d = datetime.datetime.fromtimestamp(t)
    return f'{d.day}/{d.month} {d.strftime("%H:%M")}'


def linea_salud(ahora=None):
    ahora = time.time() if ahora is None else ahora
    choques = hallar(del_registro(ahora - DIA))
    if not choques:
        return "Choques entre chats (últimas 24 h): ninguno."
    partes = []
    for c in choques[:TOPE_SALUD]:
        actores = " y ".join(quien(a) for a in c["actores"])
        partes.append(f'{nombre_archivo(c["ruta"])} ({actores}, {tramo(c["desde"], c["hasta"])})')
    resto = len(choques) - len(partes)
    mas = f" y {resto} más" if resto else ""
    import configuracion
    return (f'Choques entre chats (últimas 24 h): {cuantas_veces(choques)}: {"; ".join(partes)}{mas}. '
            f"Detalle: {configuracion.comando()} --choques.")


def cuantas_veces(choques):
    return (cantidad(len(choques), "vez", "veces") + " dos chats o agentes editaron el mismo archivo con menos de "
            f"{VENTANA // 60} min entre uno y otro")


def texto(choques, horas):
    periodo = "última hora" if horas == 1 else f"últimas {horas} h"
    if not choques:
        return [f"Choques entre chats ({periodo}): ninguno. Un choque es cuando dos chats o agentes editan "
                f"el mismo archivo con menos de {VENTANA // 60} min entre uno y otro."]
    lineas = [f"Choques entre chats ({periodo}): {cuantas_veces(choques)}. "
              "Si siguen abiertos, que cada uno relea el archivo antes de volver a tocarlo."]
    for c in choques:
        lineas.append("")
        hasta = f' a {hora(c["hasta"])}' if hora(c["hasta"]) != hora(c["desde"]) else ""
        lineas.append(f'{nombre_archivo(c["ruta"])} · {fecha(c["desde"])}{hasta}')
        lineas.append(f'  {c["ruta"]}')
        for a in c["actores"]:
            ediciones = cantidad(a["veces"], "edición", "ediciones")
            lineas.append(f'  {quien(a)}: {ediciones} ({tramo(a["desde"], a["hasta"])})')
    return lineas


def main(horas=24):
    horas = max(1, min(24 * 30, int(horas)))
    for linea in texto(hallar(del_registro(time.time() - horas * 3600)), horas):
        print(sin_control(linea))
    return 0
