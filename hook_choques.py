import os
import re
import sys
import time
from collections import Counter

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)
import hooks_comun

TOPE_LECTURA = 2 * 1024 * 1024
TOPE_CHAT = 8 * 1024 * 1024
ROTADO_RECIENTE = 3 * 86400
HERRAMIENTAS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
FUERZA_RECUERDO = 0.25
RE_TROZO = re.compile(r"\w[\w.,/:-]*\w|\w")
RE_FECHA_HORA = re.compile(r"\d{1,2}/\d{1,2}(?:/\d{2,4})?|\d{1,2}:\d{2}(?::\d{2})?|\d{4}-\d{2}-\d{2}(?:t[\d:.]+z?)?")
PALABRAS_ANTES = 2
LARGO_NUMERO = 3
VENTANA = 80
LARGO_FRASE = 8
TOPE_FRASES = 6
TOPE_HALLADOS = 3
ESPERA_INDICE = 1.5


def cola(ruta, tope=TOPE_LECTURA):
    with open(ruta, "rb") as f:
        f.seek(0, os.SEEK_END)
        largo = f.tell()
        f.seek(max(0, largo - tope))
        lineas = f.read().split(b"\n")
    return lineas[1:] if largo > tope else lineas


def lineas_del_chat(registro, sesion, ahora=None):
    ahora = time.time() if ahora is None else ahora
    marca = f'"s":"{sesion}"'.encode("utf-8")
    rotados = []
    for archivo in registro.parent.glob("eventos-*.jsonl"):
        try:
            rotados.append((archivo.stat().st_mtime, archivo))
        except OSError:
            continue
    ultimo = max(rotados, default=None)
    salida = []
    for archivo in ([ultimo[1]] if ultimo and ahora - ultimo[0] < ROTADO_RECIENTE else []) + [registro]:
        try:
            salida += [x for x in cola(archivo, TOPE_CHAT) if marca in x]
        except OSError:
            continue
    return salida


def minutos(segundos):
    n = int(segundos // 60)
    return "menos de un minuto" if n < 1 else "1 minuto" if n == 1 else f"{n} minutos"


def aviso(datos, ahora=None):
    if datos.get("hook_event_name") != "PostToolUse" or datos.get("tool_name") not in HERRAMIENTAS:
        return None
    entrada = datos.get("tool_input")
    if not isinstance(entrada, dict):
        return None
    ruta = entrada.get("file_path") or entrada.get("notebook_path")
    if not isinstance(ruta, str) or not ruta:
        return None
    import choques
    import consultas
    agente = hooks_comun.nombre_seguro(datos.get("agent_id")) or hooks_comun.nombre_seguro(datos.get("agent_type"))
    propio = (str(datos.get("session_id") or "")[:8], agente)
    if not propio[0]:
        return None
    ahora = time.time() if ahora is None else ahora
    try:
        lineas = cola(consultas.REGISTRO)
    except OSError:
        return None
    clave = consultas.clave(ruta)
    ultimos = {}
    for e in choques.ediciones_de(lineas, ahora - choques.VENTANA):
        if e["clave"] == clave and e["actor"] != propio:
            ultimos[e["actor"]] = e
    if not ultimos:
        return None
    partes = [choques.quien({"s": e["actor"][0], "a": e["actor"][1], "tipo": e["tipo"], "c": e["c"]}) + " hace "
              + minutos(max(0, ahora - e["t"])) for e in sorted(ultimos.values(), key=lambda e: -e["t"])]
    return ("Neuromapa: " + choques.nombre_archivo(ruta) + " también lo editó " + " y ".join(partes)
            + ". Si trabajan a la vez, releé el archivo antes de seguir y fijate que los cambios no se pisen.")


def texto_nuevo(herramienta, entrada):
    if herramienta == "Write":
        return entrada.get("content"), ""
    if herramienta == "Edit":
        return entrada.get("new_string"), entrada.get("old_string")
    cambios = [c for c in entrada.get("edits") or [] if isinstance(c, dict)]
    return ("\n".join(str(c.get("new_string") or "") for c in cambios),
            "\n".join(str(c.get("old_string") or "") for c in cambios))


def aviso_rutas(datos):
    herramienta = datos.get("tool_name")
    entrada = datos.get("tool_input")
    if datos.get("hook_event_name") != "PostToolUse" or herramienta not in ("Edit", "Write", "MultiEdit") \
            or not isinstance(entrada, dict):
        return None
    ruta = entrada.get("file_path")
    if not isinstance(ruta, str) or not ruta.lower().endswith(".md"):
        return None
    nuevo, viejo = texto_nuevo(herramienta, entrada)
    if not isinstance(nuevo, str) or not nuevo.strip():
        return None
    import cerebro as nucleo
    if not nucleo.dentro_de_fuentes(ruta):
        return None
    import medico
    antes = viejo if isinstance(viejo, str) else ""
    rotas = medico.rutas_rotas(ruta, nuevo, antes)
    enlaces = medico.enlaces_rotos(ruta, nuevo, antes)
    if not rotas and not enlaces:
        return None
    import choques
    partes = []
    if rotas:
        partes.append(("una ruta que no existe: " if len(rotas) == 1 else "rutas que no existen: ") + lista(rotas))
    if enlaces:
        partes.append(("un enlace a una nota que no existe: " if len(enlaces) == 1 else "enlaces a notas que no existen: ")
                      + lista(enlaces))
    consejos = []
    if rotas:
        consejos.append("Si la ruta se movió, poné la nueva; si es a propósito (se borró o todavía no existe), decilo en el "
                        "mismo renglón para que el médico no la marque.")
    if enlaces:
        consejos.append("El enlace corregilo o sacalo: el médico lo marca aunque el renglón lo explique.")
    return f'Neuromapa: en {choques.nombre_archivo(ruta)} acabás de escribir {" y ".join(partes)}. ' + " ".join(consejos)


def lista(cosas):
    return ", ".join(cosas[:3]) + (f" y {len(cosas) - 3} más" if len(cosas) > 3 else "")


def plano(texto):
    return " ".join(RE_TROZO.findall(texto.lower()))


def es_dato(trozo):
    return any(c.isdigit() for c in trozo) and not RE_FECHA_HORA.fullmatch(trozo)


def datos_sacados(viejo, nuevo):
    trozos_nuevos = RE_TROZO.findall(nuevo.lower())
    quedan = Counter(t for t in trozos_nuevos if es_dato(t))
    siguen = {(trozos_nuevos[i], trozos_nuevos[i + 1]): trozos_nuevos[i + 2] for i in range(len(trozos_nuevos) - 2)}
    frases = []
    for m in RE_TROZO.finditer(viejo.lower()):
        dato = m.group(0)
        if not es_dato(dato):
            continue
        if quedan[dato] > 0:
            quedan[dato] -= 1
            continue
        antes = RE_TROZO.findall(viejo[max(0, m.start() - VENTANA):m.start()].lower())
        antes = (antes[1:] if m.start() > VENTANA else antes)[-PALABRAS_ANTES:]
        despues = []
        if dato.isdigit() and len(dato) < LARGO_NUMERO:
            despues = RE_TROZO.findall(viejo[m.end():m.end() + VENTANA].lower())[:1]
            if not despues:
                continue
        frase = " ".join(antes + [dato] + despues)
        reemplazo = siguen.get(tuple(antes))
        if len(antes) == PALABRAS_ANTES and any(p.isalpha() and len(p) > 2 for p in antes) and len(frase) >= LARGO_FRASE \
                and reemplazo is not None and reemplazo != dato and any(c.isdigit() for c in reemplazo) \
                and frase not in frases:
            frases.append(frase)
    return frases[:TOPE_FRASES]


def renglones_con(ruta, frases):
    try:
        with open(ruta, encoding="utf-8", errors="replace") as archivo:
            texto = archivo.read(TOPE_LECTURA)
    except OSError:
        return []
    salida, vistas = [], set()
    for i, renglon in enumerate(texto.split("\n"), 1):
        entero = f" {plano(renglon)} "
        cual = next((f for f in frases if f not in vistas and f" {f} " in entero), None)
        if cual:
            vistas.add(cual)
            salida.append((i, cual))
    return salida


def aviso_dato_viejo(datos):
    herramienta = datos.get("tool_name")
    entrada = datos.get("tool_input")
    if datos.get("hook_event_name") != "PostToolUse" or herramienta not in ("Edit", "MultiEdit") \
            or not isinstance(entrada, dict) or datos.get("agent_id") or not hooks_comun.contexto_automatico():
        return None
    ruta = entrada.get("file_path")
    if not isinstance(ruta, str) or not ruta.lower().endswith(".md"):
        return None
    nuevo, viejo = texto_nuevo(herramienta, entrada)
    if not isinstance(viejo, str) or not isinstance(nuevo, str):
        return None
    frases = datos_sacados(viejo, nuevo)
    if not frases:
        return None
    import cerebro as nucleo
    if not nucleo.dentro_de_fuentes(ruta):
        return None
    import buscador
    indice = buscador.desde_disco(esperar=False, hasta=time.monotonic() + ESPERA_INDICE)
    if indice is None:
        return None
    propia = os.path.normcase(os.path.realpath(ruta))
    candidatas = {}
    for n, _, _, texto in indice.secciones:
        nota = indice.notas[n]
        if nota["ruta"] in candidatas or os.path.normcase(os.path.realpath(nota["ruta"])) == propia \
                or nucleo.es_historica(nota):
            continue
        entero = f" {plano(texto)} "
        if any(f" {f} " in entero for f in frases):
            candidatas[nota["ruta"]] = None
    hallados = []
    for otra in candidatas:
        for linea, cual in renglones_con(otra, frases):
            hallados.append((otra, linea, cual))
        if len(hallados) >= TOPE_HALLADOS:
            break
    if not hallados:
        return None
    import choques
    lugares = "; ".join(f"{r}:{linea} («{f}»)" for r, linea, f in hallados[:TOPE_HALLADOS])
    return (f"Neuromapa: en {choques.nombre_archivo(ruta)} acabás de cambiar un dato que otras notas todavía dicen igual "
            f"que antes: {lugares}. Si es el mismo dato, actualizalo ahí también; si esas cuentan otra cosa (o lo de antes "
            "sigue siendo cierto allá), no hace falta tocarlas.")


def recordados(eventos, desde):
    import aprender
    from registro import numero
    return {aprender.clave(ev["f"]) for ev in eventos
            if ev.get("e") == "recuerda" and isinstance(ev.get("f"), str) and numero(ev.get("t")) > desde}


def aviso_nota(datos):
    if datos.get("hook_event_name") != "PostToolUse" or datos.get("tool_name") not in HERRAMIENTAS \
            or datos.get("agent_id") or datos.get("agent_type"):
        return None
    entrada = datos.get("tool_input")
    sesion = str(datos.get("session_id") or "")[:8]
    if not isinstance(entrada, dict) or not hooks_comun.nombre_seguro(sesion):
        return None
    ruta = entrada.get("file_path") or entrada.get("notebook_path")
    if not isinstance(ruta, str) or not ruta or not hooks_comun.contexto_automatico():
        return None
    from archivos import EXT_CODIGO
    if os.path.splitext(ruta)[1][1:].lower() not in EXT_CODIGO:
        return None
    import aprender
    c = aprender.clave(ruta)
    if not aprender.util(c) or not aprender.prendido():
        return None
    aprendido = aprender.cargar()
    candidatas = aprendido.vecinos(c, aprender.es_nota, minimo=FUERZA_RECUERDO) if aprendido else []
    if not candidatas:
        return None
    import consultas
    import hook_evento
    import registro
    if not hook_evento.ruta_guardable(ruta):
        return None
    eventos = list(registro.eventos(lineas_del_chat(consultas.REGISTRO, sesion), 0))
    if {c, aprender.clave(hook_evento.corto(ruta, 300))} & recordados(eventos, aprender.compactada(eventos, sesion)):
        return None
    leidas = aprender.leidas_por([ev for ev in eventos if not ev.get("a")], sesion)
    cwd = datos.get("cwd") if isinstance(datos.get("cwd"), str) else ""
    import configuracion
    cargadas = hooks_comun.ya_cargadas(cwd, configuracion.carpeta_de_claude())
    for _, b in candidatas:
        nota = aprendido.rutas.get(b, b)
        if os.path.normcase(nota) in cargadas or os.path.normcase(os.path.realpath(nota)) in cargadas \
                or not os.path.isfile(nota):
            continue
        if b in leidas:
            return None
        hook_evento.escribir_evento(hook_evento.recuerdo(sesion, cwd, ruta, [nota]))
        import choques
        return (f"Neuromapa: cuando se edita {choques.nombre_archivo(ruta)} se suele leer también {nota} (lo aprendió "
                "del uso) y en esta charla todavía no la leíste. Si el cambio toca lo que cuenta esa nota, leela antes "
                "de seguir: puede tener una decisión o una trampa de este archivo.")
    return None


def main():
    try:
        datos = hooks_comun.entrada()
        hooks_comun.contexto("PostToolUse", (lambda: aviso(datos), lambda: aviso_rutas(datos), lambda: aviso_nota(datos),
                                             lambda: aviso_dato_viejo(datos)))
    except Exception:
        hooks_comun.fallo()


if __name__ == "__main__":
    main()
    sys.exit(0)
