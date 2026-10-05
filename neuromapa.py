import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    import configuracion
    try:
        return correr(sys.argv[1:])
    except configuracion.ConfigInvalida as error:
        consejo = ("Si la variable CEREBRO_CONFIG apunta ahí, corregila o sacala." if error.falta
                   else "Arreglá ese archivo o borralo para volver a la de fábrica.")
        print(f"Neuromapa no pudo leer su configuración: {error}. {consejo}", file=sys.stderr)
        return 1


def correr(argumentos):
    if argumentos[:1] == ["abrir"]:
        sys.argv = ["neuromapa abrir", "--apagar-solo"] + argumentos[1:]
        import servidor
        return servidor.main()
    sys.argv = ["neuromapa"] + argumentos
    import cerebro
    return cerebro.main(epilogo="Para ver el mapa en el navegador: neuromapa abrir (con --demo, el de las notas inventadas).")


if __name__ == "__main__":
    sys.exit(main())
