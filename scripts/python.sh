#!/bin/sh
avisar=0
consola=0
if [ "${1:-}" = "--avisar" ]; then
    avisar=1
    shift
elif [ "${1:-}" = "--consola" ]; then
    consola=1
    shift
fi
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
guardado="${CLAUDE_PLUGIN_DATA:-}/python.txt"
correr() {
    ruta="$1"
    shift
    case "${ruta##*/}" in
        py|py.exe) exec "$ruta" -3 "$@" ;;
    esac
    exec "$ruta" "$@"
}
if [ "$avisar" = 0 ] && [ -n "${CLAUDE_PLUGIN_DATA:-}" ] && [ -f "$guardado" ]; then
    read -r ruta < "$guardado"
    case "$ruta" in
        /*/python3|/*/python|/*/py|/*/python3.exe|/*/python.exe|/*/py.exe) [ -x "$ruta" ] && correr "$ruta" "$@" ;;
    esac
fi
version() {
    "$@" -c "import sys; print(sys.version_info >= (3, 10))" 2>/dev/null
}
viejo=""
for nombre in ${NEUROMAPA_PYTHONS:-python3 python py}; do
    ruta=$(command -v "$nombre" 2>/dev/null) || continue
    if [ "$nombre" = py ]; then
        respuesta=$(version "$ruta" -3)
    else
        respuesta=$(version "$ruta")
    fi
    case "$respuesta" in
        True*) ;;
        False*) viejo="$nombre"; continue ;;
        *) continue ;;
    esac
    if [ -n "${CLAUDE_PLUGIN_DATA:-}" ]; then
        mkdir -p "$CLAUDE_PLUGIN_DATA" 2>/dev/null && printf '%s\n' "$ruta" > "$guardado" 2>/dev/null
    fi
    correr "$ruta" "$@"
done
if [ -n "$viejo" ]; then
    falta="el que encontré ($viejo) es más viejo"
else
    falta="no lo encontré (probé python3, python y py)"
fi
if [ "$avisar" = 1 ]; then
    printf '{"systemMessage": "Neuromapa necesita Python 3.10 o más nuevo y %s. Instalalo desde https://www.python.org/downloads/ y abrí Claude Code de nuevo. Mientras tanto, sus hooks no hacen nada."}\n' "$falta"
fi
if [ "$consola" = 1 ]; then
    printf 'Neuromapa necesita Python 3.10 o superior y %s: https://www.python.org/downloads/\n' "$falta" >&2
    exit 1
fi
exit 0
