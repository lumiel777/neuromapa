import datetime
import json
import re
import time
from pathlib import Path

import configuracion
import consultas
import registro
from textos import cantidad, decimal

HORA = 3600
QUIETO = 180
ABANDONADO = 2 * HORA
CAMPOS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
MARCA_USO = b'"usage"'
JOURNAL = "journal.jsonl"


def epoca(texto):
    try:
        return datetime.datetime.fromisoformat(str(texto).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def vacio():
    return {c: 0 for c in CAMPOS}


def total(uso):
    return sum(uso.values())


def uso_de(archivo, desde):
    por_pedido = {}
    try:
        with open(archivo, "rb") as f:
            for linea in f:
                if MARCA_USO not in linea:
                    continue
                try:
                    d = json.loads(linea)
                except ValueError:
                    continue
                mensaje = d.get("message") if isinstance(d, dict) else None
                uso = mensaje.get("usage") if isinstance(mensaje, dict) else None
                t = epoca(d.get("timestamp"))
                if not isinstance(uso, dict) or t is None or t < desde:
                    continue
                pedido = d.get("requestId") or mensaje.get("id") or d.get("uuid") or len(por_pedido)
                por_pedido[pedido] = {c: registro.numero(uso.get(c)) for c in CAMPOS}
    except OSError:
        return vacio()
    suma = vacio()
    for uso in por_pedido.values():
        for c in CAMPOS:
            suma[c] += int(uso[c])
    return suma


def transcripciones(desde, casa=None):
    base = Path(casa or configuracion.carpeta_de_claude()) / "projects"
    for patron in ("*/*.jsonl", "*/*/subagents/**/*.jsonl"):
        for archivo in base.glob(patron):
            if archivo.name == JOURNAL:
                continue
            try:
                if archivo.stat().st_mtime >= desde:
                    yield archivo
            except OSError:
                continue


def nombre_proyecto(carpeta):
    carpeta = re.sub(r"--claude-worktrees-.*$", "", carpeta, flags=re.I)
    for p in configuracion.actual()["proyectos"]:
        if re.sub(r"[^A-Za-z0-9]", "-", p["raiz"]).lower() == carpeta.lower():
            return p["alias"]
    return carpeta.rsplit("--", 1)[-1] or carpeta


def gasto(desde, casa=None):
    sesiones = {}
    base = Path(casa or configuracion.carpeta_de_claude()) / "projects"
    for archivo in transcripciones(desde, casa):
        partes = archivo.relative_to(base).parts
        de_agente = len(partes) >= 4 and partes[2] == "subagents"
        carpeta = partes[0]
        sesion = partes[1] if de_agente else archivo.stem
        uso = uso_de(archivo, desde)
        if not total(uso):
            continue
        d = sesiones.setdefault(sesion, {"sesion": sesion, "proyecto": nombre_proyecto(carpeta), "chat": vacio(),
                                         "agentes": vacio(), "con_agentes": 0})
        destino = d["agentes"] if de_agente else d["chat"]
        for c in CAMPOS:
            destino[c] += uso[c]
        d["con_agentes"] += 1 if de_agente else 0
    return sorted(sesiones.values(), key=lambda d: -(total(d["chat"]) + total(d["agentes"])))


def agentes_quietos(ahora, ventana=2 * HORA):
    agentes = {}
    desde = ahora - ventana
    for ev in registro.eventos(registro.lineas_desde(consultas.EN_VIVO, desde), desde, (b'"a":',)):
        if not ev.get("a"):
            continue
        clave = (str(ev.get("s") or ""), str(ev["a"]))
        d = agentes.setdefault(clave, {"eventos": 0, "fin": False, "ultimo": 0, "tipo": str(ev.get("at") or ""),
                                       "c": str(ev.get("c") or "")})
        d["eventos"] += 1
        d["ultimo"] = max(d["ultimo"], registro.numero(ev.get("t")))
        d["fin"] = d["fin"] or ev.get("e") == "sub-fin"
    return sorted(({"s": s, "a": a, **d} for (s, a), d in agentes.items()
                   if not d["fin"] and d["eventos"] >= 2 and QUIETO <= ahora - d["ultimo"] <= ABANDONADO),
                  key=lambda d: -d["ultimo"])


def cifra(n):
    if n >= 999_500:
        return f"{decimal(n / 1_000_000)} M"
    if n >= 1000:
        miles = round(n / 1000)
        return "mil" if miles == 1 else f"{miles} mil"
    return str(n)


def linea_salud(ahora=None, casa=None):
    ahora = time.time() if ahora is None else ahora
    sesiones = gasto(ahora - HORA, casa)
    quietos = agentes_quietos(ahora)
    if not sesiones and not quietos:
        return "Gasto (última hora): ningún chat usó tokens."
    todo = sum(total(d["chat"]) + total(d["agentes"]) for d in sesiones)
    cache = sum(d["chat"]["cache_read_input_tokens"] + d["agentes"]["cache_read_input_tokens"] for d in sesiones)
    partes = [f"Gasto (última hora): {cifra(todo)} tokens en " + cantidad(len(sesiones), "chat", "chats")
              + (f" ({cifra(cache)} leídos de la caché, que cuestan un décimo)" if cache else "")]
    if sesiones:
        mayor = sesiones[0]
        de_agentes = total(mayor["agentes"])
        partes.append(f'el que más, el de {mayor["proyecto"]} ({mayor["sesion"][:8]}): '
                      + cifra(total(mayor["chat"]) + de_agentes)
                      + (f", {cifra(de_agentes)} de agentes" if de_agentes else ""))
    if quietos:
        partes.append(cantidad(len(quietos), "agente quieto", "agentes quietos")
                      + f" hace más de {QUIETO // 60} min sin terminar")
    return f'{"; ".join(partes)}. Detalle: {configuracion.comando()} --gasto.'


def texto(sesiones, quietos, horas):
    periodo = "la última hora" if horas == 1 else f"las últimas {horas} h"
    lineas = [f"Gasto de {periodo} (tokens de las transcripciones de Claude Code; cada respuesta se cuenta una vez):"]
    if not sesiones:
        lineas.append("  ningún chat usó tokens.")
    for d in sesiones:
        chat, agentes = d["chat"], d["agentes"]
        linea = f'  {d["proyecto"]} ({d["sesion"][:8]}): {cifra(total(chat) + total(agentes))}'
        if d["con_agentes"]:
            linea += f" · agentes: {cifra(total(agentes))} en " + cantidad(d["con_agentes"], "transcripción", "transcripciones")
        lineas.append(linea)
        suma = {c: chat[c] + agentes[c] for c in CAMPOS}
        lineas.append(f'      nuevos {cifra(suma["input_tokens"])}'
                      f' · escritos en caché {cifra(suma["cache_creation_input_tokens"])}'
                      f' · leídos de caché {cifra(suma["cache_read_input_tokens"])}'
                      f' · de salida {cifra(suma["output_tokens"])}')
    if quietos:
        lineas.append(f"Agentes quietos hace más de {QUIETO // 60} min sin terminar (pueden estar trabados; "
                      "los que pasan 3 min sin herramientas se reintentan desde cero; los callados hace más de "
                      f"{ABANDONADO // HORA} h ya no se cuentan):")
        ahora = time.time()
        for q in quietos:
            minutos = round((ahora - q["ultimo"]) / 60)
            lineas.append(f'  {q["tipo"] or "agente"} {q["a"][:12]} del chat {q["s"]}: {q["eventos"]} eventos, '
                          f"el último hace {minutos} min")
    return lineas


def main(horas=1):
    horas = max(1, min(24 * 7, int(horas)))
    ahora = time.time()
    for linea in texto(gasto(ahora - horas * HORA), agentes_quietos(ahora, max(2 * HORA, horas * HORA)), horas):
        print(linea)
    return 0
