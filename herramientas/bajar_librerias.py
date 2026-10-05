import base64
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent
PLANTILLA = CARPETA / "plantilla.html"
VENDOR = CARPETA / "vendor"
RE_LIBRERIA = re.compile(r"const (URL_\w+) = '(https://[^']+)';")
RE_INTEGRIDAD = re.compile(r"\[(URL_\w+)\]: '(sha384-[A-Za-z0-9+/=]+)'")


def main():
    html = PLANTILLA.read_text(encoding="utf-8-sig")
    huellas = dict(RE_INTEGRIDAD.findall(html))
    librerias = RE_LIBRERIA.findall(html)
    if not librerias:
        print("No encontré en plantilla.html qué bibliotecas usa.")
        return 1
    VENDOR.mkdir(exist_ok=True)
    fallas = 0
    for nombre, url in librerias:
        try:
            with urllib.request.urlopen(url, timeout=30) as respuesta:
                datos = respuesta.read()
        except OSError as error:
            print(f"No pude bajar {url}: {error}")
            fallas += 1
            continue
        huella = f'sha384-{base64.b64encode(hashlib.sha384(datos).digest()).decode("ascii")}'
        if huella != huellas.get(nombre):
            print(f"La huella de {url} no es la que espera la página: no la guardo.")
            fallas += 1
            continue
        destino = VENDOR / url.rsplit("/", 1)[-1]
        destino.write_bytes(datos)
        print(f"Guardada {destino} ({len(datos) / 1024:.0f} KB), con la huella verificada.")
    if fallas:
        return 1
    print("Listo: la próxima vez que se arme la página lleva las bibliotecas adentro y el mapa anda sin internet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
