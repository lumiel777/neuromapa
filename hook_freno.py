import os
import sys
import time
from pathlib import Path

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)
import hooks_comun

HERRAMIENTAS = ("Agent", "Task", "Workflow")


def aviso(datos, ahora=None):
    if datos.get("hook_event_name") != "PreToolUse" or datos.get("tool_name") not in HERRAMIENTAS:
        return None
    import configuracion
    freno = configuracion.actual().get("freno")
    ruta = datos.get("transcript_path")
    if not freno:
        return None
    if freno.get("workflow_siempre") and datos.get("tool_name") == "Workflow":
        return ("Neuromapa: este chat quiere lanzar un workflow (varios agentes a la vez), y tu regla es que no se usan "
                "salvo que los pidas. ¿Lanzarlo igual?")
    if not isinstance(ruta, str) or not ruta:
        return None
    import gasto
    ahora = time.time() if ahora is None else ahora
    desde = ahora - gasto.HORA
    principal = Path(ruta)
    usado = 0
    for archivo in sorted((principal.parent / principal.stem / "subagents").glob("**/*.jsonl")):
        if archivo.name == gasto.JOURNAL:
            continue
        try:
            if archivo.stat().st_mtime < desde:
                continue
        except OSError:
            continue
        usado += gasto.total(gasto.uso_de(archivo, desde))
    tope = freno["tokens_de_agentes_por_hora"]
    if usado < tope:
        return None
    que = "el workflow" if datos.get("tool_name") == "Workflow" else "otro agente"
    return ("Neuromapa: los agentes de este chat ya usaron " + gasto.cifra(usado) + " tokens en la última hora y tu tope "
            "es " + gasto.cifra(tope) + ". ¿Lanzar igual " + que + "?")


def main():
    try:
        texto = aviso(hooks_comun.entrada())
        if texto:
            hooks_comun.responder({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                          "permissionDecisionReason": texto}})
    except Exception:
        hooks_comun.fallo()


if __name__ == "__main__":
    main()
    sys.exit(0)
