import os
import sys
import time

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)
import hooks_comun

UMBRAL = 5
PAUSA = 15 * 60
SIN_TRABAJO = ("md", "txt")
TEXTO_COMPACTADA = ("Neuromapa: esta charla se acaba de compactar y el resumen de arriba es lo único que queda de lo que se "
                    "habló antes. Lo que ese resumen cuenta como decidido, aprendido o pendiente y todavía no está escrito en "
                    "la memoria (o en los documentos del proyecto) se pierde en la próxima compactación o al cerrar la charla. "
                    "Antes de seguir conviene pasarlo a la memoria, en la nota que ya cubre cada tema en vez de crear otra; si "
                    "ya está todo escrito, no hace falta nada.")


def extension(ruta):
    return os.path.splitext(ruta)[1][1:].lower()


def cuentas(eventos, sesion, es_nota):
    from registro import numero
    propios = [ev for ev in eventos if ev.get("s") == sesion]
    nota = max((numero(ev.get("t")) for ev in propios if ev.get("e") == "post" and ev.get("k") in ("editar", "crear")
                and isinstance(ev.get("f"), str) and es_nota(ev["f"])), default=0.0)
    avisado = max((numero(ev.get("t")) for ev in propios if ev.get("e") == "guarda"), default=0.0)
    desde = max(nota, avisado)
    import consultas
    archivos = {consultas.clave(ev["f"]) for ev in propios
                if ev.get("e") == "post" and ev.get("k") in ("editar", "crear") and isinstance(ev.get("f"), str)
                and extension(ev["f"]) not in SIN_TRABAJO and numero(ev.get("t")) > desde}
    commits = sum(1 for ev in propios if ev.get("e") == "post" and ev.get("b") == "commit" and numero(ev.get("t")) > desde)
    return len(archivos), commits, nota > 0, avisado


def es_nota(ruta):
    if extension(ruta) != "md":
        return False
    import cerebro as nucleo
    import consultas
    return nucleo.dentro_de_fuentes(ruta) or nucleo.dentro_de_fuentes(consultas.clave(ruta))


def texto_fin(archivos, commits, escribio):
    from textos import cantidad
    hecho = "se cambió 1 archivo" if archivos == 1 else "se cambiaron " + cantidad(archivos, "archivo", "archivos")
    if commits:
        hecho += " y se hizo 1 commit" if commits == 1 else " y se hicieron " + cantidad(commits, "commit", "commits")
    antes = (f"Neuromapa: desde la última vez que esta charla escribió en la memoria {hecho}." if escribio else
             f"Neuromapa: en esta charla {hecho} y todavía no se escribió nada en la memoria.")
    return (antes + " Si salió una decisión, un porqué, un número o un paso que convenga recordar dentro de unas semanas, "
            "este es el momento de anotarlo en la nota que ya cubre ese tema. Si no hay nada nuevo que valga la pena "
            "guardar, no hace falta hacer nada.")


def anotar(sesion, cwd, motivo, archivos=0):
    import hook_evento
    hook_evento.escribir_evento(hook_evento.recordatorio(sesion, cwd, motivo, archivos))


def aviso_compactada(datos):
    if datos.get("hook_event_name") != "SessionStart" or datos.get("source") != "compact" \
            or not hooks_comun.contexto_automatico():
        return None
    sesion = str(datos.get("session_id") or "")[:8]
    if hooks_comun.nombre_seguro(sesion):
        anotar(sesion, datos.get("cwd"), "compact")
    return TEXTO_COMPACTADA


def aviso_fin(datos, ahora=None):
    if datos.get("hook_event_name") != "Stop" or not hooks_comun.contexto_automatico():
        return None
    sesion = str(datos.get("session_id") or "")[:8]
    if not hooks_comun.nombre_seguro(sesion):
        return None
    import consultas
    import registro
    from hook_choques import lineas_del_chat
    ahora = time.time() if ahora is None else ahora
    eventos = list(registro.eventos(lineas_del_chat(consultas.REGISTRO, sesion, ahora), 0))
    archivos, commits, escribio, avisado = cuentas(eventos, sesion, es_nota)
    if ahora - avisado < PAUSA or not (archivos >= UMBRAL or (commits and archivos)):
        return None
    anotar(sesion, datos.get("cwd"), "fin", archivos)
    return texto_fin(archivos, commits, escribio)


def guardar_historial():
    try:
        import historial
        historial.guardar()
    except Exception:
        hooks_comun.fallo()


def main():
    try:
        datos = hooks_comun.entrada()
        evento = datos.get("hook_event_name")
        if evento in ("SessionStart", "Stop"):
            guardar_historial()
        if evento == "SessionStart":
            hooks_comun.contexto("SessionStart", (lambda: aviso_compactada(datos),))
        elif evento == "Stop":
            hooks_comun.contexto("Stop", (lambda: aviso_fin(datos),))
    except Exception:
        hooks_comun.fallo()


if __name__ == "__main__":
    main()
    sys.exit(0)
