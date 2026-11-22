import re
import unicodedata

RE_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
RE_WIKI = re.compile(r"\[\[(?![^\[\]\n]*(?:\{\{|<%))([^\[\]\n|#]{1,150})(#[^\[\]\n|]*)?(\|[^\[\]\n]*)?\]\]")
RE_WIKI_VISTO = re.compile(r"!?" + RE_WIKI.pattern)
RE_CERCO = re.compile(r"[ \t]*(`{3,}|~{3,})(.*)")
RE_ORDEN_PARA_IA = re.compile(
    r"<\s*/?\s*(?:[A-Za-z][\w.]*[-_:][\w.:-]*|(?:system|user|assistant|human|instructions?|tools?|functions?|invoke"
    r"|parameter|prompt|context|documents?|results?|output|thinking|command-\w+)\b)[^<>\n]{0,200}>"
    r"|<\|[^|<>\n]{0,40}\|>|<<\s*/?\s*SYS\s*>>|\[\s*/?\s*INST\s*\]", re.I)
TAPADO = "[tapado]"
TOPE_FRONTMATTER = 200
CLAVES = [re.compile(p, re.S) for p in (
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)",
    r"(?<![\w-])(?:sk|pk|rk)-(?:[A-Za-z]+-)?[A-Za-z0-9_-]{16,}",
    r"(?<![\w-])(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{16,}",
    r"(?<![\w-])re_[A-Za-z0-9_]{16,}",
    r"(?<![\w-])gh[pousr]_[A-Za-z0-9]{20,}",
    r"(?<![\w-])github_pat_[A-Za-z0-9_]{20,}",
    r"(?<![\w-])AKIA[0-9A-Z]{16}(?![\w-])",
    r"(?<![\w-])xox[baprs]-[A-Za-z0-9-]{10,}",
    r"(?<![\w-])eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}",
    r"(?<![\w-])(?=[\w-]*[0-9])(?=[\w-]*[A-Z])(?=[\w-]*[a-z])[A-Za-z0-9_-]{32,}={0,2}(?![\w-])",
)]


def tapar_claves(texto, propios=()):
    for secreto in propios:
        texto = texto.replace(secreto, TAPADO)
    for patron in CLAVES:
        texto = patron.sub(TAPADO, texto)
    return texto


def sin_control(texto):
    return RE_CONTROL.sub("?", str(texto))


class Cercos:
    def __init__(self):
        self.marca = ""

    def paso(self, linea):
        m = RE_CERCO.match(linea)
        if self.marca:
            if m and m.group(1)[0] == self.marca[0] and len(m.group(1)) >= len(self.marca) and not m.group(2).strip():
                self.marca = ""
                return "cierra"
            return "dentro"
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            self.marca = m.group(1)
            return "abre"
        return ""


def tapar_cercos(texto):
    cercos = Cercos()
    return "\n".join(re.sub(r"[^\n]", " ", linea) if cercos.paso(linea) else linea for linea in texto.split("\n"))


def sin_ordenes_para_ia(texto):
    return RE_ORDEN_PARA_IA.sub(lambda m: "‹" + m.group(0)[1:-1] + "›", str(texto))


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
    limpio = sin_ordenes_para_ia(sin_control(" ".join(str(texto).split()))).replace("«", "‹").replace("»", "›")
    if largo and len(limpio) > largo:
        limpio = limpio[:largo - 1].rstrip() + "…"
    return "«" + limpio + "»"
