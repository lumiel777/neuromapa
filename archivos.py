import json
import os
import re
import tempfile
import time
from pathlib import Path

try:
    import msvcrt
except ImportError:
    msvcrt = None
try:
    import fcntl
except ImportError:
    fcntl = None

ESPERA_REEMPLAZO = 2.0
HOLGURA_RELOJ = 2.0
MARCA_PAGINA = "/*__PAGINA__*/\n"
CARPETAS_SENSIBLES = (".ssh", ".aws", ".gnupg", ".kube", ".docker", ".azure", "gcloud", ".password-store")
EXTENSIONES_SENSIBLES = ("pem", "key", "pfx", "p12", "ppk", "kdbx", "jks", "keystore", "tfstate", "tfstate.backup",
                         "tfvars", "ovpn")
NOMBRES_SENSIBLES = ("secrets.json", "secret.json", "credentials.json", ".credentials.json", ".npmrc", ".netrc", "_netrc",
                     ".pypirc", ".git-credentials", ".htpasswd", "token.json", "tokens.json", "clave.txt", ".pgpass",
                     "wp-config.php", "secrets.yaml", "secrets.yml")
NOMBRES_GENERICOS = ("credentials", "cookies", "login data", "web data")
EXT_CODIGO = ("cs", "py", "js", "jsx", "mjs", "cjs", "ts", "tsx", "java", "kt", "go", "rs", "php", "swift", "c", "h", "cc",
              "cpp", "hpp", "ps1", "psm1", "sh", "bat", "cmd", "sql", "prisma")
_CARPETAS = "|".join(map(re.escape, CARPETAS_SENSIBLES))
_EXTENSIONES = "|".join(map(re.escape, EXTENSIONES_SENSIBLES))
_NOMBRES = "|".join(map(re.escape, NOMBRES_SENSIBLES))
_GENERICOS = "|".join(map(re.escape, NOMBRES_GENERICOS))
_PATRONES = r"id_(?:rsa|dsa|ecdsa|ed25519)[^\\/\s'\"]*|client_secret[^\\/\s'\"]*\.json|gh[\\/]hosts\.ya?ml"
RE_SENSIBLE = re.compile(rf"(?:^|[\\/])(?:{_CARPETAS})(?:[\\/]|$)|(?:^|[\\/])\.env(?:\.[^\\/]*)?$|\.(?:{_EXTENSIONES})$"
                         rf"|(?:^|[\\/])(?:{_PATRONES}|{_NOMBRES}|{_GENERICOS})$", re.I)
RE_SENSIBLE_EN_TEXTO = re.compile(rf"(?:^|[\\/\s'\"*=:(])\.env(?![\w-])|(?:^|[\\/\s'\"*=:(])\.env\."
                                  rf"|\.(?:{_EXTENSIONES})(?![\w-])|(?:^|[\\/])(?:{_CARPETAS})(?:[\\/]|$)"
                                  rf"|{_PATRONES}|(?<![\w.\-])(?:{_NOMBRES})(?![\w.\-])|[\\/](?:{_GENERICOS})(?![\w.\-])",
                                  re.I)
_propios = []


def propios():
    if not _propios:
        try:
            import configuracion
            nombres = tuple(configuracion.actual().get("sensibles") or ())
        except Exception:
            nombres = ()
        partes = "|".join(map(re.escape, nombres))
        _propios.append((re.compile(rf"(?:^|[\\/])(?:{partes})(?:[\\/]|$)", re.I) if nombres else None,
                         re.compile(rf"(?<![\w.\-])(?:{partes})(?![\w.\-])", re.I) if nombres else None))
    return _propios[0]


def es_sensible(ruta):
    texto = str(ruta).rstrip("\\/")
    if RE_SENSIBLE.search(texto):
        return True
    propio = propios()[0]
    return bool(propio and propio.search(texto))


def menciona_sensible(texto):
    if RE_SENSIBLE_EN_TEXTO.search(texto):
        return True
    propio = propios()[1]
    return bool(propio and propio.search(texto))


def abrir_para_escribir(destino, binario):
    return open(destino, "wb") if binario else open(destino, "w", encoding="utf-8", newline="")


def escribir_atomico(ruta, contenido):
    ruta = Path(ruta)
    if ruta.is_symlink():
        ruta = Path(os.path.realpath(ruta))
    binario = isinstance(contenido, bytes)
    try:
        enlazado = ruta.stat().st_nlink > 1
    except OSError:
        enlazado = False
    if enlazado:
        with abrir_para_escribir(ruta, binario) as archivo:
            archivo.write(contenido)
            archivo.flush()
            os.fsync(archivo.fileno())
        return
    fd, temporal = tempfile.mkstemp(dir=ruta.parent, prefix=f".{ruta.name}.", suffix=".tmp")
    try:
        with abrir_para_escribir(fd, binario) as archivo:
            archivo.write(contenido)
            archivo.flush()
            os.fsync(archivo.fileno())
        limite = time.monotonic() + ESPERA_REEMPLAZO
        while True:
            try:
                os.replace(temporal, ruta)
                return
            except PermissionError as error:
                if time.monotonic() >= limite:
                    raise PermissionError(f"{ruta.name} sigue tomado por otro programa: quedó como estaba") from error
                time.sleep(0.02)
    finally:
        if os.path.exists(temporal):
            try:
                os.remove(temporal)
            except OSError:
                pass


def plantilla_entera(ruta):
    ruta = Path(ruta)
    html = ruta.read_text(encoding="utf-8-sig")
    if MARCA_PAGINA not in html:
        return html
    partes = sorted((ruta.parent / "pagina").glob("*.js"))
    if not partes:
        raise FileNotFoundError(f"la plantilla {ruta} pide el JavaScript de pagina/, y esa carpeta no está a su lado")
    return html.replace(MARCA_PAGINA, "".join(p.read_text(encoding="utf-8") for p in partes), 1)


def tomar_candado(ruta, espera=0.0):
    if msvcrt is None and fcntl is None:
        return None
    try:
        fd = os.open(ruta, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError:
        return None
    limite = time.monotonic() + espera
    while True:
        try:
            if msvcrt is not None:
                os.lseek(fd, 0, 0)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError:
            if time.monotonic() >= limite:
                os.close(fd)
                return None
            time.sleep(0.002)


def soltar_candado(fd):
    if fd is None:
        return
    try:
        if msvcrt is not None:
            os.lseek(fd, 0, 0)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        os.close(fd)
    except OSError:
        pass


def hay_candados():
    return msvcrt is not None or fcntl is not None


def reciente(marca, espera, ahora=None):
    ahora = time.time() if ahora is None else ahora
    return -HOLGURA_RELOJ <= ahora - marca < espera


def dentro(ruta, raiz):
    ruta = os.path.normcase(os.path.abspath(ruta)).rstrip("\\/")
    raiz = os.path.normcase(os.path.abspath(raiz)).rstrip("\\/")
    return ruta == raiz or ruta.startswith(raiz + os.sep)


def estado_generado(ruta, esperado, propia):
    try:
        actual = Path(ruta).read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n")
    except OSError:
        return "nueva"
    if actual == esperado:
        return "igual"
    cabeza = actual.split("\n---\n", 1)[0] if actual.startswith("---\n") and "\n---\n" in actual else ""
    return "propia" if propia.search(cabeza) else "ajena"


def leer_objeto_json(ruta):
    try:
        with open(ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def json_roto(ruta):
    try:
        with open(ruta, encoding="utf-8-sig") as archivo:
            json.load(archivo)
    except ValueError as error:
        return str(error)
    except OSError:
        return None
    return None


def apartar_roto(ruta, ahora=None):
    ruta = Path(ruta)
    if json_roto(ruta) is None:
        return None
    destino = ruta.with_name(f"{ruta.stem}.roto-{time.strftime('%Y%m%d-%H%M%S', time.localtime(ahora))}{ruta.suffix}")
    try:
        os.replace(ruta, destino)
    except OSError:
        return None
    return destino
