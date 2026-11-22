import os
import signal
import subprocess
import sys

WINDOWS = sys.platform == "win32"
ESPERA_CORTE = 5


def cortar(proceso):
    if WINDOWS:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proceso.pid)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=ESPERA_CORTE,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        try:
            os.killpg(proceso.pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        proceso.kill()
    except OSError:
        pass


def lanzar_de_fondo(argumentos):
    opciones = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if WINDOWS:
        opciones["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        opciones["start_new_session"] = True
    return subprocess.Popen(argumentos, **opciones)


def correr(orden, timeout, input=None, capture_output=False, **opciones):
    if capture_output:
        opciones["stdout"] = opciones["stderr"] = subprocess.PIPE
    if input is not None:
        opciones["stdin"] = subprocess.PIPE
    if WINDOWS:
        opciones.setdefault("creationflags", getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        opciones.setdefault("start_new_session", True)
    with subprocess.Popen(orden, **opciones) as proceso:
        try:
            salida, error = proceso.communicate(input, timeout=timeout)
        except subprocess.TimeoutExpired:
            cortar(proceso)
            try:
                proceso.communicate(timeout=ESPERA_CORTE)
            except subprocess.TimeoutExpired:
                pass
            raise subprocess.TimeoutExpired(orden, timeout) from None
    return subprocess.CompletedProcess(orden, proceso.returncode, salida, error)
