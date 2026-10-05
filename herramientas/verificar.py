import os
import re
import shutil
import subprocess
import sys
import tempfile

CARPETA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANTILLA = os.path.join(CARPETA, "plantilla.html")


def es_comentario(linea):
    return bool(re.match(r"\s*//", linea)) or ("/*" in linea and "__CEREBRO__" not in linea)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    with open(PLANTILLA, encoding="utf-8") as f:
        texto = f.read()
    principal = max(re.findall(r"<script>(.*?)</script>", texto, re.S), key=len)
    with tempfile.TemporaryDirectory() as temporal:
        ruta = os.path.join(temporal, "principal.js")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(principal)
        node = shutil.which("node")
        if node is None:
            print("No encontré node: salteo la revisión de sintaxis del JavaScript (se instala desde https://nodejs.org).")
        else:
            r = subprocess.run([node, "--check", ruta], capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                print(f"Error de sintaxis en el JavaScript:\n{r.stderr}")
                return 1
            print("JavaScript: sintaxis bien.")
        comentarios = [n for n, linea in enumerate(principal.splitlines(), 1) if es_comentario(linea)]
        if comentarios:
            print(f'Aviso: hay comentarios en el JavaScript (líneas del bloque): {", ".join(map(str, comentarios[:10]))}')
        armado = subprocess.run([sys.executable, os.path.join(CARPETA, "cerebro.py"), "--salida",
                                 os.path.join(temporal, "cerebro.html")], capture_output=True, text=True, cwd=CARPETA,
                                encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        if armado.returncode != 0:
            print(f"Error al armar la página:\n{armado.stdout}{armado.stderr}")
            return 1
    print("La página se arma bien (en una carpeta temporal; la tuya no se tocó).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
