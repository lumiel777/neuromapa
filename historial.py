import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import cerebro as nucleo
import configuracion
import permisos
from archivos import es_sensible, escribir_atomico, leer_objeto_json
from textos import cantidad

CARPETA = Path(nucleo.DATOS) / "historial"
ESTADO = CARPETA / "estado.json"
EXCLUIR = "*\n!*.md\n!*/\n"
ESPERA = 4.0
PRESUPUESTO = 6.0
CANDADO_VIEJO = 600
MINIMO_BUSCADO = 3
TOPE_VERSIONES_BUSCADAS = 100
TOPE_CAMBIOS = 15
TOPE_HALLAZGOS = 20
_limite = [None]
TOPE_RENGLONES = 3
LARGO_RENGLON = 200
NOMBRES_CAMBIO = {"M": ("cambiada", "cambiadas"), "A": ("nueva", "nuevas"), "D": ("borrada", "borradas")}


def carpetas():
    vistas = {}
    for fuente in nucleo.FUENTES:
        if not fuente.get("memoria"):
            continue
        for raiz, _, _ in fuente["raices"]:
            real = os.path.realpath(raiz)
            if os.path.isdir(real):
                vistas.setdefault(os.path.normcase(real), real)
    return list(vistas.values())


def repo_de(carpeta):
    nombre = re.sub(r"[^\w.-]+", "-", Path(carpeta).parent.name or "memoria")
    huella = hashlib.sha1(os.path.normcase(carpeta).encode("utf-8")).hexdigest()[:8]
    return CARPETA / f"{nombre}-{huella}.git"


def hay_git():
    return shutil.which("git") is not None


def git(carpeta, *argumentos, binario=False):
    orden = ["git", f"--git-dir={repo_de(carpeta)}", f"--work-tree={carpeta}", "-c", "core.autocrlf=false",
             "-c", "core.quotepath=false", "-c", "user.name=Neuromapa", "-c", "user.email=neuromapa@localhost",
             "-c", "commit.gpgsign=false", "-c", f"core.hooksPath={repo_de(carpeta) / 'sin-hooks'}", *argumentos]
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    espera = ESPERA if _limite[0] is None else min(ESPERA, _limite[0] - time.monotonic())
    if espera <= 0:
        return None
    try:
        proceso = subprocess.run(orden, cwd=carpeta, env=entorno, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 timeout=espera, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return None
    if proceso.returncode != 0:
        return None
    return proceso.stdout if binario else proceso.stdout.decode("utf-8", "replace")


def firma(carpeta):
    partes = []
    for raiz, subcarpetas, archivos in os.walk(carpeta):
        subcarpetas[:] = [s for s in subcarpetas if not s.startswith(".") and not es_sensible(os.path.join(raiz, s))]
        for nombre in archivos:
            ruta = os.path.join(raiz, nombre)
            if not nombre.lower().endswith(".md") or es_sensible(ruta):
                continue
            try:
                estado = os.stat(ruta)
            except OSError:
                continue
            partes.append(f"{os.path.relpath(ruta, carpeta)}|{estado.st_size}|{estado.st_mtime_ns}")
    return hashlib.sha1("\n".join(sorted(partes)).encode("utf-8")).hexdigest()


def candado_libre(repo):
    candado = repo / "index.lock"
    try:
        if time.time() - candado.stat().st_mtime < CANDADO_VIEJO:
            return False
        candado.unlink()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def fuera_del_historial(carpeta, relativa):
    return es_sensible(os.path.join(carpeta, relativa)) or any(p.startswith(".") for p in Path(relativa).parts[:-1])


def resumen(cambios):
    partes = []
    for letra, (uno, varios) in NOMBRES_CAMBIO.items():
        nombres = [Path(ruta).name for estado, ruta in cambios if estado == letra]
        if nombres:
            partes.append(f"{cantidad(len(nombres), uno, varios)}: {', '.join(nombres)}")
    return "; ".join(partes) or "sin cambios"


def guardar_carpeta(carpeta):
    repo = repo_de(carpeta)
    nuevo = not (repo / "HEAD").is_file()
    if nuevo:
        permisos.crear(repo.parent)
        if git(carpeta, "init", "-q") is None:
            return False
        (repo / "info").mkdir(exist_ok=True)
        (repo / "info" / "exclude").write_text(EXCLUIR, encoding="utf-8")
    if not candado_libre(repo) or git(carpeta, "add", "-A", ".") is None:
        return False
    seguidas = (git(carpeta, "ls-files") or "").splitlines()
    sacar = [r for r in seguidas if fuera_del_historial(carpeta, r)]
    if sacar and git(carpeta, "rm", "--cached", "-q", "--", *sacar) is None:
        return False
    salida = git(carpeta, "diff", "--cached", "--name-status", "--no-renames")
    if salida is None:
        return False
    cambios = [tuple(linea.split("\t", 1)) for linea in salida.splitlines() if "\t" in linea]
    if not cambios:
        return True
    mensaje = (f"primera versión: {cantidad(len(cambios), 'nota', 'notas')}" if nuevo else resumen(cambios))
    return git(carpeta, "commit", "-q", "-m", mensaje) is not None


def guardar():
    if not hay_git():
        return False
    estado = leer_objeto_json(ESTADO)
    cambio = False
    _limite[0] = time.monotonic() + PRESUPUESTO
    try:
        for carpeta in carpetas():
            clave = repo_de(carpeta).name
            actual = firma(carpeta)
            if estado.get(clave) == actual:
                continue
            if guardar_carpeta(carpeta):
                estado[clave] = actual
                cambio = True
    finally:
        _limite[0] = None
    if cambio:
        escribir_atomico(ESTADO, json.dumps(estado, ensure_ascii=False, indent=1) + "\n")
    return cambio


def fecha(segundos):
    d = datetime.datetime.fromtimestamp(int(segundos))
    return f"{d.day}/{d.month} a las {d:%H:%M}"


def versiones(carpeta):
    if not (repo_de(carpeta) / "HEAD").is_file():
        return []
    salida = git(carpeta, "log", "--format=%ct")
    return [int(t) for t in salida.split()] if salida else []


def linea_salud():
    lista = carpetas()
    if not lista:
        return None
    if not hay_git():
        return ("Historial de la memoria: apagado, porque no encontré git. Con git instalado, cada cambio de la memoria "
                "queda guardado y nada de lo que se borre se pierde.")
    guardar()
    tiempos = [t for carpeta in lista for t in versiones(carpeta)]
    if not tiempos:
        return "Historial de la memoria: todavía sin versiones (se guarda al terminar cada respuesta de Claude)."
    return (f"Historial de la memoria: {cantidad(len(tiempos), 'versión', 'versiones')} desde el {fecha(min(tiempos))}, "
            f"la última el {fecha(max(tiempos))}. Para buscar algo que se borró: {configuracion.comando()} "
            f'--historial "texto".')


def registro(carpeta, *argumentos):
    salida = git(carpeta, "log", "--format=@%h %ct %P", "--raw", "--numstat", "--no-renames", *argumentos) or ""
    commits = []
    for linea in salida.splitlines():
        if linea.startswith("@"):
            corto, tiempo, *padres = linea[1:].split(" ")
            commits.append({"hash": corto, "t": int(tiempo), "primera": not any(padres), "estado": {}, "numeros": {}})
        elif linea.startswith(":") and "\t" in linea and commits:
            meta, ruta = linea.split("\t", 1)
            commits[-1]["estado"][ruta] = meta.split()[-1]
        elif linea.count("\t") >= 2 and commits:
            mas, menos, ruta = linea.split("\t", 2)
            commits[-1]["numeros"][ruta] = (mas, menos)
    return commits


def describir(commit):
    if commit["primera"]:
        return f"primera versión: {cantidad(len(commit['estado']), 'nota', 'notas')}"
    partes = []
    for ruta, letra in commit["estado"].items():
        mas, menos = commit["numeros"].get(ruta, ("-", "-"))
        nombre = Path(ruta).name
        if letra == "A":
            partes.append(f"nueva {nombre}")
        elif letra == "D":
            partes.append(f"borró {nombre}")
        else:
            partes.append(f"{nombre} (+{mas} −{menos})")
    return ", ".join(partes)


def main_cambios():
    lista = carpetas()
    if not lista:
        print("No hay carpetas de memoria en la configuración.")
        return 0
    if not hay_git():
        print(linea_salud())
        return 1
    guardar()
    for carpeta in lista:
        commits = registro(carpeta, "-n", str(TOPE_CAMBIOS))
        total = len(versiones(carpeta))
        if not commits:
            print(f"Historial de {carpeta}: todavía sin versiones.")
            continue
        print(f"Historial de {carpeta}: {cantidad(total, 'versión', 'versiones')}. Los últimos cambios:")
        for commit in commits:
            print(f"  {fecha(commit['t'])}  {describir(commit)}")
    print(f'Para buscar algo que se borró: {configuracion.comando()} --historial "texto".')
    return 0


def contenido(carpeta, version, ruta):
    datos = git(carpeta, "show", f"{version}:{ruta}", binario=True)
    return datos.decode("utf-8", "replace").replace("\r\n", "\n") if datos is not None else ""


def renglones_con(texto, buscado):
    bajo = buscado.lower()
    salida = []
    for numero, renglon in enumerate(texto.split("\n"), 1):
        if bajo in renglon.lower():
            recorte = renglon.strip()
            salida.append(f"{numero}: {recorte[:LARGO_RENGLON]}{'…' if len(recorte) > LARGO_RENGLON else ''}")
    return salida


def cuantas(texto, buscado):
    return texto.lower().count(buscado.lower())


def hallazgos(carpeta, buscado):
    salida = []
    for commit in reversed(registro(carpeta, f"-S{buscado}", "-i", "-n", str(TOPE_VERSIONES_BUSCADAS))):
        for ruta in commit["estado"]:
            despues = contenido(carpeta, commit["hash"], ruta)
            antes = "" if commit["primera"] else contenido(carpeta, commit["hash"] + "^", ruta)
            n_antes, n_despues = cuantas(antes, buscado), cuantas(despues, buscado)
            if n_antes == n_despues:
                continue
            if commit["primera"]:
                que = f"ya estaba en {Path(ruta).name} (primera versión)"
            elif n_despues == 0:
                que = f"se borró de {Path(ruta).name}"
            elif n_antes == 0:
                que = f"apareció en {Path(ruta).name}"
            else:
                que = f"en {Path(ruta).name} pasó de {n_antes} a {n_despues} veces"
            borrado = n_despues < n_antes
            salida.append({"t": commit["t"], "que": que, "hash": commit["hash"], "ruta": ruta, "borrado": borrado,
                           "renglones": renglones_con(antes, buscado)[:TOPE_RENGLONES] if borrado else []})
    return salida


def hoy_esta(carpeta, buscado):
    nombres = []
    for raiz, subcarpetas, archivos in os.walk(carpeta):
        subcarpetas[:] = [s for s in subcarpetas if not s.startswith(".")]
        for nombre in sorted(archivos):
            if not nombre.lower().endswith(".md"):
                continue
            try:
                texto = Path(raiz, nombre).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if cuantas(texto, buscado):
                nombres.append(nombre)
    return nombres


def main_buscar(buscado):
    buscado = buscado.strip()
    if len(buscado) < MINIMO_BUSCADO:
        print(f'Falta el texto, de {MINIMO_BUSCADO} letras o más: --historial "texto".')
        return 2
    lista = carpetas()
    if not lista or not hay_git():
        print(linea_salud() or "No hay carpetas de memoria en la configuración.")
        return 1
    guardar()
    encontrado = False
    for carpeta in lista:
        todos = hallazgos(carpeta, buscado)
        hoy = hoy_esta(carpeta, buscado)
        if not todos and not hoy:
            continue
        encontrado = True
        print(f"«{buscado}» en el historial de {carpeta}:")
        for h in todos[-TOPE_HALLAZGOS:]:
            print(f"  {fecha(h['t'])}  {h['que']}" + (". Lo que decía:" if h["renglones"] else ""))
            for renglon in h["renglones"]:
                print(f"      {renglon}")
            if h["borrado"]:
                print(f'      Versión entera de antes: git --git-dir="{repo_de(carpeta)}" show {h["hash"]}^:"{h["ruta"]}"')
        if len(todos) > TOPE_HALLAZGOS:
            print(f"  … y {len(todos) - TOPE_HALLAZGOS} cambios más antiguos.")
        print(f"  Hoy está en: {', '.join(hoy)}." if hoy else "  Hoy no está en ninguna nota.")
    if not encontrado:
        print(f"«{buscado}» no aparece en la memoria de hoy ni en su historial.")
    return 0


def main(argumento):
    return main_buscar(argumento) if argumento else main_cambios()
