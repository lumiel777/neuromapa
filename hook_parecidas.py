import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)
import hooks_comun

UMBRAL = 0.25
CUANTAS = 3
LARGO_MAXIMO = 200000


def real(ruta):
    return os.path.normcase(os.path.realpath(str(ruta)))


def aviso(datos):
    if datos.get("hook_event_name") != "PostToolUse" or datos.get("tool_name") != "Write":
        return None
    entrada = datos.get("tool_input")
    respuesta = datos.get("tool_response")
    if not isinstance(entrada, dict) or not isinstance(respuesta, dict) or respuesta.get("type") != "create":
        return None
    ruta = entrada.get("file_path")
    if not isinstance(ruta, str) or not ruta.lower().endswith(".md") or os.path.basename(ruta).lower() == "memory.md":
        return None
    import cerebro as nucleo
    carpetas = {real(raiz[0]) for fuente in nucleo.FUENTES if fuente.get("memoria") for raiz in fuente["raices"]}
    propia = real(ruta)
    if os.path.dirname(propia) not in carpetas or not os.path.isfile(propia) or os.path.getsize(propia) > LARGO_MAXIMO:
        return None
    texto, _ = nucleo.leer_texto(nucleo.Path(ruta))
    if not texto or not texto.strip():
        return None
    import parecidas
    from textos import decimal
    otras = [d for d in parecidas.documentos_de_memoria(nucleo.desde_disco()) if real(d["ruta"]) != propia]
    resultado = parecidas.comparar(texto.replace("\r\n", "\n"), otras, CUANTAS)
    lista = [r for r in resultado["resultados"] if r["puntaje"] >= UMBRAL]
    if not lista:
        return None
    partes = []
    for r in lista:
        comparten = ", ".join(r["comparten"][:5])
        detalle = f"; comparten: {comparten}" if comparten else ""
        partes.append(f'{os.path.basename(r["ruta"])} ({decimal(r["puntaje"], 2)}{detalle})')
    nueva = os.path.basename(ruta)
    return (f'Neuromapa: la memoria nueva {nueva} se parece a {" y a ".join(partes)}. '
            "Revisá si es lo mismo: si lo es, sumalo a la que ya existe en vez de tener dos.")


def main():
    try:
        datos = hooks_comun.entrada()
        hooks_comun.contexto("PostToolUse", (lambda: aviso(datos),))
    except Exception:
        hooks_comun.fallo()


if __name__ == "__main__":
    main()
    sys.exit(0)
