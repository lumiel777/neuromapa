import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import configuracion
import donde
from textos import cantidad, miles

HOOKS = ("hook_cerebro", "hook_servir", "hook_choques", "hook_parecidas", "hook_guardar", "hook_freno")
RE_SCRIPT = re.compile(r"([^\s\"']*hook_\w+\.py)")
RE_PY_ENTRE_COMILLAS = re.compile(r"[\"']([^\"'\n]+?\.py)[\"']")
RE_PYTHON = re.compile(r"^\s*\"?([^\"\s]+\.exe)\"?", re.I)
QUIETO = 24 * 3600
DIAS_PISTA = 7
ETIQUETA = {"bien": "  bien   ", "ojo": "  ojo    ", "falta": "  FALTA  ", "dato": "  ·      "}


def hace(segundos):
    if segundos < 90:
        return "hace un momento"
    if segundos < 5400:
        return f"hace {round(segundos / 60)} minutos"
    if segundos < 172800:
        return f"hace {round(segundos / 3600)} horas"
    return f"hace {round(segundos / 86400)} días"


def revisar_python():
    v = sys.version_info
    texto = f"Python {v.major}.{v.minor}.{v.micro} ({sys.executable})"
    if v < (3, 10):
        return [("falta", f"{texto}: hace falta 3.10 o más nuevo, de python.org.")]
    return [("bien", texto)]


def revisar_config():
    ruta, elegida = str(configuracion.archivo()), donde.config()[1]
    try:
        config = configuracion.actual()
    except configuracion.ConfigInvalida as error:
        return None, [("falta", f"La configuración ({ruta}) tiene un error: {error}. Arreglá ese archivo, o borralo "
                                "para volver a la de fábrica.")]
    origen = "elegida con CEREBRO_CONFIG" if elegida else "la de fábrica" if not os.path.isfile(ruta) else ruta
    return config, [("bien", f"Configuración: {origen}; la carpeta de datos es {config['datos']}.")]


def revisar_notas(config):
    import cerebro as nucleo
    total, de_memoria, vacias = 0, 0, []
    for fuente in nucleo.FUENTES:
        cuantas = sum(len(nucleo.listar(raiz, recursivo, False)) for raiz, recursivo, _ in fuente["raices"])
        total += cuantas
        if fuente.get("memoria"):
            de_memoria += cuantas
        if not cuantas:
            vacias.append(fuente.get("nombre") or fuente["id"])
    lineas = []
    if not total:
        lineas.append(("falta", "No encontré ninguna nota: ¿Claude Code ya guardó alguna memoria? Si usás otras carpetas, "
                                "van en «fuentes» del config.json."))
    elif not de_memoria:
        lineas.append(("ojo", f"Encontré {miles(total)} notas, pero ninguna en la memoria de Claude Code: la pista y el "
                              "médico de la memoria no tienen con qué trabajar todavía."))
    else:
        lineas.append(("bien", f"Notas: {miles(total)} en {cantidad(len(nucleo.FUENTES), 'fuente', 'fuentes')} "
                               f"({miles(de_memoria)} de la memoria de Claude Code)."))
    if vacias:
        lineas.append(("ojo", f"Sin ninguna nota: {', '.join(vacias)}. Si la carpeta se movió, corregila en el config.json."))
    return lineas


def comandos_de(ajustes):
    return [str(h.get("command", "")) for grupos in (ajustes.get("hooks") or {}).values() if isinstance(grupos, list)
            for g in grupos if isinstance(g, dict) for h in g.get("hooks", ()) if isinstance(h, dict)]


def revisar_hooks(casa=None):
    casa = casa or donde.carpeta_de_claude()
    try:
        with open(os.path.join(casa, "settings.json"), encoding="utf-8") as f:
            ajustes = json.load(f)
        if not isinstance(ajustes, dict):
            ajustes = {}
    except (OSError, ValueError):
        ajustes = {}
    comandos = [c for c in comandos_de(ajustes) if "hook_" in c and "CLAUDE_PLUGIN_ROOT" not in c]
    plugin = bool(os.environ.get("CLAUDE_PLUGIN_ROOT")) or any(
        str(nombre).startswith("neuromapa@") and prendido for nombre, prendido in (ajustes.get("enabledPlugins") or {}).items())
    puestos = sorted({h for h in HOOKS for c in comandos if f"{h}.py" in c})
    lineas = []
    if plugin and comandos:
        lineas.append(("falta", "Está instalado dos veces: como plugin y con hooks a mano en settings.json. Todo se anota y "
                                "se sirve dos veces. Dejá uno: desinstalá el plugin o sacá esos hooks de settings.json."))
    elif plugin:
        lineas.append(("bien", "Hooks: los pone el plugin."))
    elif comandos:
        faltan = [h for h in HOOKS if h not in puestos]
        lineas.append(("bien" if not faltan else "ojo",
                       f"Hooks puestos a mano en settings.json: {len(puestos)} de {len(HOOKS)}"
                       + (f" (faltan {', '.join(f + '.py' for f in faltan)})." if faltan else ".")))
    else:
        lineas.append(("falta", "No encontré los hooks: ni el plugin prendido ni hooks a mano en settings.json. Sin ellos "
                                "no hay registro ni pista. Instalalo con «claude plugin install neuromapa@neuromapa» y "
                                "reiniciá Claude Code."))
    rotos = sorted({m for c in comandos for m in RE_SCRIPT.findall(c) if os.path.isabs(m) and not os.path.isfile(m)})
    pythons = sorted({m.group(1) for c in comandos for m in [RE_PYTHON.match(c)] if m and os.path.isabs(m.group(1))
                      and not os.path.isfile(m.group(1))})
    if rotos:
        lineas.append(("falta", f"Hooks que apuntan a archivos que ya no están: {', '.join(rotos[:3])}"
                                + (" y más" if len(rotos) > 3 else "") + ". ¿Se movió la carpeta? Corregí las rutas en "
                                "settings.json."))
    if pythons:
        lineas.append(("falta", f"Hooks que llaman a un Python que ya no está: {', '.join(pythons)}. Corregí la ruta en "
                                "settings.json."))
    return lineas


def eventos_desde(en_vivo, desde, marcas=()):
    import registro
    return registro.eventos(registro.lineas_desde(Path(en_vivo), desde), desde, marcas)


def revisar_registro(datos, ahora=None):
    import registro
    ahora = time.time() if ahora is None else ahora
    en_vivo = Path(datos) / "en-vivo"
    ultimo = max((registro.numero(ev.get("t")) for ev in eventos_desde(en_vivo, ahora - QUIETO * 7)), default=0)
    if not ultimo:
        return [("falta", "El registro no anotó nada en la última semana: los hooks no están corriendo. Reiniciá Claude "
                          "Code después de instalar; si sigue, mirá «Aparece un hook error» en la wiki.")]
    lineas = [("bien" if ahora - ultimo < QUIETO else "ojo",
               f"El registro anota: lo último, {hace(ahora - ultimo)}."
               + ("" if ahora - ultimo < QUIETO else " Si estuviste usando Claude Code, los hooks no están corriendo."))]
    pistas = sum(1 for _ in eventos_desde(en_vivo, ahora - DIAS_PISTA * 86400, (b'"e":"aviso"', b'"e": "aviso"')))
    if pistas:
        lineas.append(("bien", f"La pista: Claude la recibió {cantidad(pistas, 'vez', 'veces')} en {DIAS_PISTA} días."))
    else:
        lineas.append(("ojo", f"La pista no se dio ninguna vez en {DIAS_PISTA} días. Con el plugin viene apagada: se "
                              "prende con «/plugin configure neuromapa@neuromapa» (contexto automático)."))
    return lineas


def revisar_mapa(datos):
    import hook_servir
    anotado = hook_servir.servidor_vivo(str(datos))
    pagina = Path(datos) / "cerebro.html"
    if anotado:
        return [("bien", f"El mapa está abierto en http://127.0.0.1:{anotado.get('puerto')}.")]
    if pagina.is_file():
        return [("dato", f"El mapa está cerrado (es normal: se abre con «neuromapa abrir» o /neuromapa:abrir); se armó "
                         f"por última vez {hace(time.time() - pagina.stat().st_mtime)}.")]
    return [("dato", "El mapa todavía no se armó nunca: se abre con «neuromapa abrir» o /neuromapa:abrir.")]


def revisar_git():
    if shutil.which("git"):
        return [("bien", "git: está (lo usan el historial de la memoria y el médico para las citas al código).")]
    return [("ojo", "No encontré git: el historial de la memoria y la revisión de citas al código no andan. Se instala "
                    "de git-scm.com.")]


def revisar_permisos(datos):
    import permisos
    linea = permisos.linea_salud(datos)
    if not linea:
        return [("bien", "Permisos: la carpeta de datos es solo de tu cuenta.")]
    return [("falta" if linea.startswith("GRAVE") else "ojo", linea.split(None, 1)[1] if " " in linea else linea)]


def rutas_py_perdidas(texto):
    import archivos
    salida = []
    for crudo in RE_PY_ENTRE_COMILLAS.findall(texto):
        ruta = crudo.replace("\\\\", "\\")
        if os.path.isabs(ruta) and not archivos.es_de_red(ruta) and not os.path.isfile(ruta) and ruta not in salida:
            salida.append(ruta)
    return salida


def revisar_codex(casa=None):
    casa = Path(casa) if casa else Path.home() / ".codex"
    if not casa.is_dir():
        return []
    try:
        toml = (casa / "config.toml").read_text(encoding="utf-8", errors="replace")
        inicio = toml.find("[mcp_servers.neuromapa]")
        conector = inicio >= 0
        fin = toml.find("\n[", inicio + 1) if conector else -1
        seccion = toml[inicio:fin if fin >= 0 else len(toml)] if conector else ""
    except OSError:
        conector, seccion = False, ""
    try:
        texto = (casa / "hooks.json").read_text(encoding="utf-8", errors="replace")
        pista = "hook_servir.py" in texto and "--codex" in texto
    except OSError:
        texto, pista = "", False
    perdidas = rutas_py_perdidas(seccion) + (rutas_py_perdidas(texto) if pista else [])
    if perdidas:
        return [("ojo", f"Codex: apunta a {perdidas[0]}, que ya no existe (¿se movió Neuromapa?): el "
                        f"{'conector' if perdidas[0] in rutas_py_perdidas(seccion) else 'hook'} no anda. Volvé a "
                        "registrarlo con la ruta nueva (ver «Codex» en cómo funciona).")]
    if conector and pista:
        return [("bien", "Codex: el conector y la pista están puestos.")]
    if conector or pista:
        return [("dato", f"Codex: {'el conector' if conector else 'la pista'} está puesto; "
                         f"{'la pista' if conector else 'el conector'} no (ver «Codex» en cómo funciona).")]
    return [("dato", "Codex está instalado, pero Neuromapa no: es opcional (ver «Codex» en cómo funciona).")]


def revisar():
    lineas = revisar_python()
    config, de_config = revisar_config()
    lineas += de_config
    if config is None:
        return lineas
    lineas += revisar_notas(config)
    lineas += revisar_hooks()
    lineas += revisar_registro(config["datos"])
    lineas += revisar_mapa(config["datos"])
    lineas += revisar_git()
    lineas += revisar_permisos(config["datos"])
    lineas += revisar_codex()
    return lineas


def main():
    for salida in (sys.stdout, sys.stderr):
        try:
            salida.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        version = json.loads((Path(donde.CODIGO) / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError, TypeError):
        version = "sin versión"
    print(f"Neuromapa {version} · revisión de la instalación")
    lineas = revisar()
    for tono, texto in lineas:
        print(f"{ETIQUETA[tono]}{texto}")
    faltan = sum(1 for tono, _ in lineas if tono == "falta")
    ojos = sum(1 for tono, _ in lineas if tono == "ojo")
    if faltan:
        print(f"Hay {cantidad(faltan, 'cosa', 'cosas')} que arreglar (las «FALTA»).")
    elif ojos:
        print(f"Anda, con {cantidad(ojos, 'cosa', 'cosas')} para mirar (las «ojo»).")
    else:
        print("Todo bien.")
    return 1 if faltan else 0
