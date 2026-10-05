import glob
import os

from archivos import escribir_atomico

CODIGO = os.path.dirname(os.path.abspath(__file__))
PLUGIN = "neuromapa"
APUNTE = "donde.txt"
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259
if os.name != "nt":
    os.umask(0o077)


def proceso_vivo(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel = ctypes.windll.kernel32
        manija = kernel.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not manija:
            return False
        try:
            codigo = ctypes.c_ulong()
            return bool(kernel.GetExitCodeProcess(manija, ctypes.byref(codigo))) and codigo.value == STILL_ACTIVE
        finally:
            kernel.CloseHandle(manija)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def carpeta_de_claude():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def del_plugin():
    propia = os.environ.get("CLAUDE_PLUGIN_OPTION_CARPETA_DATOS", "").strip()
    if propia:
        return os.path.abspath(os.path.expanduser(propia))
    datos = os.environ.get("CLAUDE_PLUGIN_DATA", "").strip()
    return os.path.abspath(datos) if datos else ""


def apuntada():
    apuntes = glob.glob(os.path.join(carpeta_de_claude(), "plugins", "data", f"{PLUGIN}*", APUNTE))
    for archivo in sorted(apuntes, key=lambda a: -os.path.getmtime(a)):
        try:
            with open(archivo, encoding="utf-8") as f:
                carpeta = f.read().strip()
        except OSError:
            continue
        if carpeta and os.path.isdir(carpeta):
            return carpeta
    return ""


def config():
    elegida = os.environ.get("CEREBRO_CONFIG", "").strip()
    if elegida:
        return os.path.abspath(os.path.join(CODIGO, os.path.expanduser(elegida))), True
    carpeta = del_plugin()
    if carpeta:
        return os.path.join(carpeta, "config.json"), False
    propia = os.path.join(CODIGO, "config.json")
    if os.path.isfile(propia):
        return propia, False
    carpeta = apuntada()
    return (os.path.join(carpeta, "config.json") if carpeta else propia), False


def apuntar(carpeta):
    datos = os.environ.get("CLAUDE_PLUGIN_DATA", "").strip()
    if not datos:
        return False
    os.makedirs(datos, exist_ok=True)
    escribir_atomico(os.path.join(datos, APUNTE), f"{os.path.abspath(carpeta)}\n")
    return True
