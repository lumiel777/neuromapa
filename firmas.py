import hashlib
import hmac
import re
import secrets
import time

RE_NUMERO = re.compile(r"[0-9a-f]{32}")
VIGENCIA = 60


def firmar(clave, *partes):
    return hmac.new(clave.encode("utf-8"), "|".join(("neuromapa",) + partes).encode("utf-8"), hashlib.sha256).hexdigest()


def numero():
    return secrets.token_hex(16)


def del_servidor(clave, desafio):
    return firmar(clave, "servidor", desafio)


def servidor_valido(clave, desafio, dada):
    return isinstance(dada, str) and hmac.compare_digest(dada.encode("utf-8"),
                                                         del_servidor(clave, desafio).encode("utf-8"))


def del_pedido(clave, camino, ahora=None):
    t = str(int(time.time() if ahora is None else ahora))
    return f"{t}:{firmar(clave, 'pedido', t, camino)}"


def pedido_valido(clave, camino, dada, ahora=None):
    t, _, firma = (dada or "").partition(":")
    if not t.isdecimal() or abs((time.time() if ahora is None else ahora) - int(t)) > VIGENCIA:
        return False
    return hmac.compare_digest(firma.encode("utf-8"), firmar(clave, "pedido", t, camino).encode("utf-8"))
