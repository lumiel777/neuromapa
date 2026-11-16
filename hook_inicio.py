import json
import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)
import hooks_comun

BIENVENIDA = "bienvenida.txt"
TEXTO_BIENVENIDA = ("Neuromapa quedó instalado. Para ver tu memoria como un cerebro en vivo: /neuromapa:abrir (con notas "
                    "inventadas: /neuromapa:abrir --demo). Para revisar tus notas: /neuromapa:salud.")
DOBLE = "doble-avisado.txt"
TEXTO_DOBLE = ("Neuromapa está instalado dos veces: como plugin y con sus hooks a mano en settings.json, así que todo se "
               "anota y se sirve dos veces. Dejá uno: desinstalá el plugin o sacá esos hooks de settings.json.")


def una_vez(carpeta, nombre):
    try:
        with open(os.path.join(carpeta, nombre), "x", encoding="utf-8", newline="\n") as f:
            f.write("1\n")
    except OSError:
        return False
    return True


def main():
    try:
        hooks_comun.entrada()
        import donde
        carpeta = os.path.dirname(donde.config()[0])
        if not donde.apuntar(carpeta):
            return
        destino = os.environ.get("CLAUDE_ENV_FILE", "").strip()
        if destino:
            # Una sola vez por archivo: Claude Code mete este archivo en cada comando de Bash, y repetida en cada
            # arranque o compactación la línea lo hacía crecer hasta pasar el tope de ~8 KB de Git Bash en Windows.
            linea = "export CLAUDE_PLUGIN_OPTION_CARPETA_DATOS='" + carpeta.replace("'", "'\\''") + "'\n"
            try:
                with open(destino, encoding="utf-8") as f:
                    ya_esta = linea in f.read()
            except OSError:
                ya_esta = False
            if not ya_esta:
                with open(destino, "a", encoding="utf-8", newline="\n") as f:
                    f.write(linea)
        mensajes = []
        if una_vez(carpeta, BIENVENIDA):
            mensajes.append(TEXTO_BIENVENIDA)
        if hooks_comun.instalado_dos_veces() and una_vez(carpeta, DOBLE):
            mensajes.append(TEXTO_DOBLE)
        if mensajes:
            print(json.dumps({"systemMessage": " ".join(mensajes)}))
    except Exception:
        hooks_comun.fallo()


if __name__ == "__main__":
    main()
    sys.exit(0)
