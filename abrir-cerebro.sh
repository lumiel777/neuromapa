#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! sh scripts/python.sh --consola servidor.py "$@"; then
    echo
    echo "No se pudo abrir el cerebro. Fijate el mensaje de arriba."
    exit 1
fi
