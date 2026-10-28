import re
import unicodedata

RE_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
RE_WIKI = re.compile(r"\[\[(?![^\[\]\n]*(?:\{\{|<%))([^\[\]\n|#]{1,150})(#[^\[\]\n|]*)?(\|[^\[\]\n]*)?\]\]")
RE_WIKI_VISTO = re.compile(r"!?" + RE_WIKI.pattern)


def sin_control(texto):
    return RE_CONTROL.sub("?", str(texto))


def sin_wiki(texto, molde="{visible}"):
    def cambio(m):
        destino = m.group(1).strip()
        return molde.format(destino=destino, visible=(m.group(3) or "")[1:].strip() or destino)
    return RE_WIKI_VISTO.sub(cambio, texto)


def sin_marcas(texto):
    minusculas = texto.lower()
    if minusculas.isascii():
        return minusculas
    return "".join(c for c in unicodedata.normalize("NFKD", minusculas) if not unicodedata.category(c).startswith("M"))


def decimal(valor, digitos=1):
    return format(valor, f".{digitos}f").replace(".", ",")


def miles(n):
    return format(n, ",").replace(",", ".")


def cantidad(n, singular, plural):
    return f"{miles(n)} {singular if n == 1 else plural}"


def detalle(error):
    texto = f"{type(error).__name__}: {error}" if str(error) else type(error).__name__
    return f"detalle de Python, en inglés: {sin_control(texto)}"


def recortar(texto, largo):
    texto = sin_control(" ".join(str(texto).split()))
    if len(texto) <= largo:
        return texto
    texto = texto[:largo - 1].rstrip() + "…"
    return texto + "»" if texto.count("«") > texto.count("»") else texto


def entre_comillas(texto):
    return "'" + texto.replace("'", "''") + "'"


def citar(texto, largo=None):
    limpio = sin_control(" ".join(str(texto).split())).replace("«", "‹").replace("»", "›")
    if largo and len(limpio) > largo:
        limpio = limpio[:largo - 1].rstrip() + "…"
    return "«" + limpio + "»"
