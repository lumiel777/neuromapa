import argparse
import contextlib
import copy
import gzip
import http.client
import http.server
import importlib
import io
import json
import os
import pickle
import queue
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import tokenize
import traceback
import types
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(CARPETA))
from archivos import plantilla_entera

SECRETO = "SECRETO-HUMO"
SESION = "humo0001-prueba"
resultados = []
salteadas = []
PARTES = []
AISLADOS = ("nucleo", "configuracion", "medico", "buscador", "parecidas", "entidades", "mapa", "hook_evento",
            "servidor", "consultas", "aprender")


def repartir():
    for modulo in PARTES:
        for nombre in AISLADOS:
            setattr(modulo, nombre, globals()[nombre])


def probar(nombre, condicion, detalle=""):
    resultados.append(bool(condicion))
    cola = "" if condicion or detalle == "" else f" → {str(detalle)[:300]}"
    print(f'  [{"ok" if condicion else "NO"}] {nombre}{cola}')


def saltear(texto):
    salteadas.append(texto)
    print(f"  [--] {texto}")


def seccion(titulo):
    print(f"\n{titulo}")


def correr(argumentos, espera=60, **entorno):
    return subprocess.run([sys.executable, *argumentos], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=espera, env=dict(os.environ, PYTHONIOENCODING="utf-8", **entorno))


def cerebro_en(copia, *opciones):
    r = correr([str(CARPETA / "cerebro.py"), *opciones], espera=300, CEREBRO_CONFIG=str(copia / "config.json"))
    return r.returncode, r.stdout + r.stderr


def correr_hook(nombre, entrada, espera=60, **entorno):
    return subprocess.run([sys.executable, "-I", "-S", str(CARPETA / nombre)], input=entrada, capture_output=True,
                          timeout=espera, env=dict(os.environ, **entorno))


def frontmatter(nombre, descripcion, tipo):
    return (f"---\nname: {nombre}\ndescription: {descripcion}\nmetadata:\n  node_type: memory\n  type: {tipo}"
            "\n---\n\n")


def login_cs():
    lineas = ["using System;", "", "namespace Demo", "{", "    public class Login", "    {",
              "        public bool ValidarClave(string clave)", "        {",
              "            return clave != null && clave.Trim().Length >= 8;", "        }", ""]
    for i in range(1, 8):
        lineas += [f"        public int Paso{i}()", "        {", f"            return {i};", "        }"]
    return "\n".join(lineas + ["    }", "}", ""])


def notas(t):
    viejo = str(t / "proyecto" / "docs" / "plan-viejo.md")
    return {
        "memoria/MEMORY.md": (
            "# Memoria del proyecto demo\n\n## Personas\n"
            "- [Perfil de Ana](perfil-ana.md) — quién es Ana y cómo prefiere las explicaciones\n\n## Reglas\n"
            "- [Sin comentarios](regla-sin-comentarios.md) — el código va limpio y el porqué va al commit\n\n"
            "## Arreglos\n"
            "- [Arreglo del login](arreglo-login.md) — la validación de la clave fallaba con espacios\n"
            "- [Arreglo del login, otra vez](arreglo-login-bis.md) — el mismo arreglo, contado de nuevo\n"
            "- [En otra máquina](//red.invalid/compartida/remota.md) — una ruta de red escrita en el índice\n"),
        "memoria/perfil-ana.md": frontmatter(
            "perfil-ana", "Quién es Ana, la dueña del proyecto demo, y cómo prefiere que le expliquen", "user")
            + "Ana es la dueña del proyecto demo. Prefiere explicaciones cortas, con el archivo y la línea.\n",
        "memoria/regla-sin-comentarios.md": frontmatter(
            "regla-sin-comentarios", "El código del proyecto demo va sin comentarios; el porqué va al mensaje de commit",
            "feedback")
            + "El código del proyecto demo va limpio, sin notas al margen. El porqué de cada cambio va al commit.\n\n"
            + "**Why:** Ana lo pidió para leer el código más rápido.\n\n"
            + "**How to apply:** antes de guardar, revisar lo nuevo.\n",
        "memoria/arreglo-login.md": frontmatter(
            "arreglo-login", "La validación de la clave del login fallaba con espacios al final; se recortan antes",
            "project")
            + "La validación de la clave fallaba cuando la clave traía espacios al final. Se arregló recortando los "
            + "espacios antes de comparar, en `Login.cs:30` (`ValidarClave`), commit `de4dbe7` (no `abc1234`, que se "
            + "descartó). Sigue la regla "
            + "[[regla-sin-comentarios]]. Ver también [[nota-que-no-existe]].\n\n"
            + "El plan de antes estaba en `" + viejo + "`.\n\n"
            + "Probado con claves con y sin espacios al final.\n",
        "memoria/arreglo-login-bis.md": frontmatter(
            "arreglo-login-bis", "La validación de la clave del login fallaba con espacios al final; se recortan",
            "project")
            + "La validación de la clave fallaba cuando la clave traía espacios al final. Se arregló recortando los "
            + "espacios antes de comparar la clave. Sigue la regla [[regla-sin-comentarios]].\n\n"
            + "Probado con claves con y sin espacios al final.\n",
        "memoria/suelta.md": frontmatter(
            "suelta", "Idea suelta para el proyecto demo: un tope de intentos para frenar a quien adivina", "project")
            + "Una idea para más adelante: un tope de intentos, para frenar a quien adivina.\n",
        "proyecto/CLAUDE.md": (
            "# Proyecto demo\n\nInstrucciones para Claude en el proyecto demo.\n\n"
            "- El archivo de login tiene 99 renglones.\n- Leé primero la memoria.\n"),
        "proyecto/codigo/Login.cs": login_cs(),
        "ideas/PLAN-DEMO.md": (
            "# Plan demo\n\n## Fases\n\n### Fase 0: preparar la casa\n\nOrdenar lo que hay antes de sumar cosas.\n\n"
            "### Fase 1: que ande en otra PC\n\nSacar las rutas fijas a un archivo de configuración.\n"),
        "muestra.js": ("function sumar(a, b) {\n  return a + b;\n}\n\nconst restar = (a, b) => a - b;\n\n"
                       "class Caja {\n  abrir() {\n    return true;\n  }\n}\n"),
        "muestra.py": "def uno():\n    return 1\n\n\nclass Dos:\n    def tres(self):\n        return 3\n",
        "sugerencias.json": "[]\n",
    }


def armar_carpeta(t):
    for relativa, texto in notas(t).items():
        ruta = t / relativa
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto, encoding="utf-8", newline="\n")
    hechos = {"hechos": [{
        "nota": "instrucciones:demo/CLAUDE.md",
        "que": "renglones de Login.cs",
        "patron": "archivo de login tiene (\\d+) renglones",
        "como_contar": {"tipo": "lineas", "archivo": "proyecto/codigo/Login.cs"},
    }]}
    (t / "hechos.json").write_text(json.dumps(hechos, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    (t / "en-vivo").mkdir(exist_ok=True)


def crear_repo(carpeta):
    pasos = (["init", "-q"], ["-c", "user.name=prueba", "-c", "user.email=prueba@example.invalid",
                              "commit", "-q", "--allow-empty", "-m", "primera"])
    try:
        for pasos_git in pasos:
            subprocess.run(["git", "-C", str(carpeta)] + pasos_git, check=True, capture_output=True, timeout=30)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def escribir_config(t):
    config = {
        "usuario": "Ana",
        "fuentes": [
            {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(t / "memoria"), False, ""]],
             "memoria": True, "proyecto": str(t / "proyecto"), "foco": True, "prioridad": 0, "lobulo": "temporal"},
            {"id": "instrucciones", "nombre": "Instrucciones (CLAUDE.md)", "color": "#F59F00",
             "raices": [[str(t / "proyecto"), False, "demo"]], "patron": "CLAUDE.md", "foco": True, "prioridad": 1,
             "lobulo": "prefrontal"},
            {"id": "cerebro-ideas", "nombre": "Cerebro · Decisiones", "color": "#51CF66",
             "raices": [[str(t / "ideas"), False, ""]], "registro": True, "foco": True, "lobulo": "prefrontal"},
        ],
        "proyectos": [{"raiz": str(t / "proyecto"), "alias": "demo", "marca": r"(?i)proyecto\s+demo",
                       "codigo": [str(t / "proyecto")]}],
        "alias_rutas": [[str(t / "memoria-por-junction"), str(t / "memoria")]],
    }
    ruta = t / "config.json"
    ruta.write_text(json.dumps(config, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    return ruta


def aislar(t):
    for nombre in [k for k in os.environ if k.startswith("CLAUDE_PLUGIN_") or k == "CLAUDE_ENV_FILE"]:
        del os.environ[nombre]
    os.environ["CEREBRO_CONFIG"] = str(escribir_config(t))
    (t / "claude-vacia").mkdir()
    os.environ["CLAUDE_CONFIG_DIR"] = str(t / "claude-vacia")
    global nucleo, configuracion, medico, buscador, parecidas, entidades, mapa, hook_evento, servidor, consultas, aprender
    import configuracion
    import aprender
    import cerebro as nucleo
    nucleo.CARPETA = t
    nucleo._listados.clear()
    import medico
    import buscador
    import parecidas
    import entidades
    import mapa
    import hook_evento
    import consultas
    import servidor
    repartir()


def adentro(t, *rutas):
    base = nucleo.normalizar(str(t))
    return all(nucleo.normalizar(str(r)).startswith(base) for r in rutas)


def revisar_aislamiento(t):
    seccion("Aislamiento (nada apunta a las carpetas reales)")
    rutas = {
        "la configuración (CEREBRO_CONFIG)": configuracion.archivo(),
        "cerebro.DATOS (la página, sugerencias.json y hechos.json)": nucleo.DATOS,
        "medico.CACHE_COMMITS": medico.CACHE_COMMITS,
        "medico.CACHE_FECHAS_ANCLAS": medico.CACHE_FECHAS_ANCLAS,
        "medico.HECHOS": medico.HECHOS,
        "medico.regla_hechos (ruta por defecto)": medico.regla_hechos.__defaults__[0],
        "parecidas.CACHE": parecidas.CACHE,
        "parecidas.Cache (ruta por defecto)": parecidas.Cache.__init__.__defaults__[0],
        "hook_evento.REGISTRO": hook_evento.REGISTRO,
        "hook_evento.CANDADO": hook_evento.CANDADO,
        "servidor.EN_VIVO": servidor.EN_VIVO,
        "servidor: el resumen de los registros": servidor.EN_VIVO / servidor.RESUMEN,
        "servidor: el sugerencias.json que vigila": next(e for e in servidor.EXTRAS if e.name == "sugerencias.json"),
        "servidor: el hechos.json que vigila": next(e for e in servidor.EXTRAS if e.name == "hechos.json"),
        "servidor.ARCHIVO_CLAVE": servidor.ARCHIVO_CLAVE,
        "consultas.REGISTRO": consultas.REGISTRO,
        "buscador: el índice guardado": buscador.ruta_del_indice(),
        "aprender: la lista de sesiones de prueba": aprender.en_vivo() / aprender.PRUEBAS,
        "dormir: las propuestas": importlib.import_module("dormir").ruta(nucleo.DATOS),
        "historial: la carpeta de las versiones de la memoria": importlib.import_module("historial").CARPETA,
        "dormir: lo que ya revisó Claude": importlib.import_module("dormir").ruta(nucleo.DATOS,
                                                                                 importlib.import_module("dormir").MEMO),
    }
    for nombre, ruta in rutas.items():
        probar(f"{nombre} queda en la carpeta de prueba", adentro(t, ruta), ruta)
    raices = [r for f in nucleo.FUENTES for r, _, _ in f["raices"]] + [c["ruta"] for p in medico.CODIGO for c in p["codigo"]]
    probar("FUENTES y el código a revisar quedan en la carpeta de prueba", adentro(t, *raices), raices)
    return adentro(t, *rutas.values(), *raices)


def armar_cerebro(t):
    nucleo._listados.clear()
    cerebro = nucleo.Cerebro()
    cerebro.recolectar()
    cerebro.analizar(t / "sugerencias.json")
    return cerebro


def borrar_carpeta(carpeta):
    def destrabar(funcion, ruta, _):
        try:
            os.chmod(ruta, stat.S_IWRITE | stat.S_IREAD)
            funcion(ruta)
        except OSError:
            pass

    if sys.version_info >= (3, 12):
        shutil.rmtree(carpeta, onexc=destrabar)
    else:
        shutil.rmtree(carpeta, onerror=destrabar)
    return not os.path.exists(carpeta)
