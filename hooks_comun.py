import contextlib
import io
import json
import os
import re
import sys

RE_DEL_SISTEMA = re.compile(r"(?:[^\n<]{0,80}\n)?<(?:task-notification|agent-message|ci-monitor-event)\b")
CODIGO = os.path.dirname(os.path.abspath(__file__))
FALLAS = "fallas.json"
DIAS_FALLAS = 7
MOSTRAR_FALLAS = 3
RE_NOMBRE = re.compile(r"[\w.:\-]{1,40}\Z")


def nombre_seguro(valor):
    valor = str(valor or "")
    return valor if RE_NOMBRE.match(valor) else ""


def del_sistema(texto):
    return bool(RE_DEL_SISTEMA.match(texto or ""))


def depurando():
    return os.environ.get("NEUROMAPA_DEPURAR", "").strip() not in ("", "0")


def de_prueba():
    return os.environ.get("NEUROMAPA_PRUEBA", "").strip() not in ("", "0")


def contexto_automatico():
    if not os.environ.get("CLAUDE_PLUGIN_DATA", "").strip():
        return True
    return os.environ.get("CLAUDE_PLUGIN_OPTION_SERVIR_CONTEXTO", "").strip().lower() in ("true", "1", "si", "sí", "yes")


def ya_cargadas(cwd, casa):
    if not cwd:
        return frozenset()
    import problemas
    salida = {os.path.normcase(os.path.realpath(os.path.join(str(casa), "CLAUDE.md")))}
    carpeta = os.path.abspath(cwd)
    while True:
        for relativa in ("CLAUDE.md", "CLAUDE.local.md", os.path.join(".claude", "CLAUDE.md")):
            salida.add(os.path.normcase(os.path.realpath(os.path.join(carpeta, relativa))))
        if os.path.dirname(carpeta) == carpeta:
            break
        carpeta = os.path.dirname(carpeta)
    memoria = problemas.memoria_del_chat(cwd, casa)
    if memoria:
        salida.add(os.path.normcase(os.path.join(memoria, "MEMORY.md")))
    return frozenset(salida)


def entrada():
    try:
        datos = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    except (OSError, ValueError, RecursionError):
        return {}
    return datos if isinstance(datos, dict) else {}


def fallo():
    if depurando():
        import traceback
        traceback.print_exc(file=sys.stderr)
    try:
        anotar_falla(sys.exc_info())
    except Exception:
        pass


def lugar_de(rastro):
    lugar = ""
    while rastro is not None:
        archivo = rastro.tb_frame.f_code.co_filename
        if os.path.dirname(os.path.abspath(archivo)) == CODIGO:
            lugar = f"{os.path.basename(archivo)}:{rastro.tb_lineno}"
        rastro = rastro.tb_next
    return lugar


def carpeta_en_vivo():
    import donde
    return os.path.join(os.path.dirname(donde.config()[0]), "en-vivo")


def anotar_falla(info, ahora=None, carpeta=None):
    import time
    from archivos import escribir_atomico, leer_objeto_json
    tipo, _, rastro = info
    if tipo is None:
        return
    carpeta = carpeta or carpeta_en_vivo()
    if not os.path.isdir(carpeta):
        return
    ahora = time.time() if ahora is None else ahora
    ruta = os.path.join(carpeta, FALLAS)
    datos = {k: v for k, v in leer_objeto_json(ruta).items()
             if isinstance(v, dict) and isinstance(v.get("ultima"), (int, float)) and ahora - v["ultima"] < DIAS_FALLAS * 86400}
    clave = f"{os.path.basename(sys.argv[0] or '?')}|{tipo.__name__}|{lugar_de(rastro)}"
    previa = datos.get(clave, {})
    veces = previa.get("veces") if isinstance(previa.get("veces"), int) else 0
    datos[clave] = {"veces": veces + 1, "ultima": ahora}
    escribir_atomico(ruta, json.dumps(datos, ensure_ascii=False))


def linea_salud(ahora=None, carpeta=None):
    import time
    from archivos import leer_objeto_json
    if carpeta is None:
        import configuracion
        carpeta = os.path.join(str(configuracion.actual()["datos"]), "en-vivo")
    ahora = time.time() if ahora is None else ahora
    fallas = sorted(((v["veces"], v["ultima"], k) for k, v in leer_objeto_json(os.path.join(carpeta, FALLAS)).items()
                     if isinstance(v, dict) and isinstance(v.get("veces"), int) and isinstance(v.get("ultima"), (int, float))
                     and ahora - v["ultima"] < DIAS_FALLAS * 86400), reverse=True)
    if not fallas:
        return ""
    partes = []
    for veces, ultima, clave in fallas[:MOSTRAR_FALLAS]:
        donde_fallo, tipo, lugar = (clave.split("|") + ["", ""])[:3]
        momento = time.localtime(ultima)
        cuando = f"{momento.tm_mday}/{momento.tm_mon} {time.strftime('%H:%M', momento)}"
        en = f" en {lugar}" if lugar else ""
        partes.append(f'{donde_fallo}: {tipo}{en} ({veces} {"vez" if veces == 1 else "veces"}, la última el {cuando})')
    resto = f" y {len(fallas) - MOSTRAR_FALLAS} más" if len(fallas) > MOSTRAR_FALLAS else ""
    return (f'AVISO   Fallas de los hooks y del armado (últimos {DIAS_FALLAS} días): {"; ".join(partes)}{resto}. '
            "Se tragan para no cortar a Claude; para ver el error entero, correr con NEUROMAPA_DEPURAR=1.")


def instalado_dos_veces(casa=None):
    import donde
    try:
        with open(os.path.join(casa or donde.carpeta_de_claude(), "settings.json"), encoding="utf-8") as f:
            ajustes = json.load(f)
        comandos = [str(h.get("command", "")) for grupos in (ajustes.get("hooks") or {}).values() for g in grupos
                    for h in g.get("hooks", ()) if isinstance(h, dict)]
        a_mano = any("hook_cerebro.py" in c and "CLAUDE_PLUGIN_ROOT" not in c for c in comandos)
        plugin = bool(os.environ.get("CLAUDE_PLUGIN_ROOT")) or any(
            str(nombre).startswith("neuromapa@") and prendido for nombre, prendido in (ajustes.get("enabledPlugins") or {}).items())
    except (OSError, ValueError, AttributeError, TypeError):
        return False
    return a_mano and plugin


def linea_doble():
    if not instalado_dos_veces():
        return ""
    return ("AVISO   Neuromapa está instalado dos veces: como plugin y con sus hooks a mano en settings.json. Todo se "
            "anota y se sirve dos veces (dos pistas en cada pedido). Dejá uno: desinstalá el plugin o sacá de "
            "settings.json los hooks de hook_cerebro.py, hook_servir.py y los demás.")


def responder(salida):
    sys.stdout.write(json.dumps(salida, ensure_ascii=True))
    sys.stdout.flush()


def callado(paso):
    with contextlib.redirect_stdout(io.StringIO()):
        if depurando():
            return paso()
        with contextlib.redirect_stderr(io.StringIO()):
            return paso()


def contexto(evento, pasos, separador="\n"):
    partes = []
    for paso in pasos:
        try:
            partes.append(callado(paso))
        except Exception:
            fallo()
    texto = separador.join(p for p in partes if p)
    if texto:
        responder({"hookSpecificOutput": {"hookEventName": evento, "additionalContext": texto}})
