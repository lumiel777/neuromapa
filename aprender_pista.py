import math
import time

import registro
from archivos import es_sensible, leer_objeto_json
from registro import numero

from aprender_comun import (APOYO, ARCHIVO, A_MANO, COLA, FUERZA_CODIGO, FUERZA_MINIMA, MEDIA_RECIENTE, MINIMO_PROYECTO,
                            MOSTRADAS_MINIMAS, PARTES_CORTO, PARTE_PROYECTO, PESO_GENERAL, PESO_RECIENTE, PREMIO_PISTA,
                            RECIENTE, TOQUES, VERSION, clave, en_vivo, es_de_codigo, es_nota, nombre, prendido,
                            proyecto_de, pruebas, raices, raiz_de, rutas_de, util)
from aprender_memoria import Memoria


class Lazos:
    def __init__(self, lazos, veces):
        self.lazos = lazos
        self.veces = veces

    def fuerza(self, a, b):
        w = self.lazos.get(a, {}).get(b, 0.0)
        if not w:
            return 0.0
        juntas = min(1.0, w / math.sqrt(max(self.veces.get(a, 0.0), w) * max(self.veces.get(b, 0.0), w)))
        return juntas * w / (w + APOYO)

    def vecinos(self, a, filtro=None, apoyo=APOYO):
        salida = [(self.fuerza(a, b), b) for b, w in self.lazos.get(a, {}).items()
                  if w >= apoyo and (filtro is None or filtro(b))]
        return sorted((x for x in salida if x[0] > 0), key=lambda x: (-x[0], x[1]))

    def pares(self, apoyo=APOYO):
        vistos = set()
        salida = []
        for a, vecinos in self.lazos.items():
            for b, w in vecinos.items():
                if w >= apoyo and (b, a) not in vistos:
                    vistos.add((a, b))
                    salida.append((self.fuerza(a, b), a, b))
        return sorted(salida, key=lambda x: (-x[0], x[1], x[2]))


class Aprendido(Lazos):
    def __init__(self, datos=None, memoria=None):
        memoria = memoria if memoria is not None else Memoria(datos)
        super().__init__(memoria.lazos, memoria.veces)
        self.viejo = Lazos(memoria.viejo_lazos, memoria.viejo_veces)
        self.charlas = memoria.charlas
        self.pistas = memoria.pistas
        self.codigo = memoria.codigo
        self.rutas = memoria.rutas
        self.dias = memoria.dias
        self.hecho = memoria.hecho
        self.proyectos = memoria.proyectos
        self._delicados = {}

    def delicado(self, c):
        if c not in self._delicados:
            self._delicados[c] = es_sensible(self.rutas.get(c, c))
        return self._delicados[c]

    def pares(self, apoyo=APOYO):
        return [x for x in super().pares(apoyo) if not self.delicado(x[1]) and not self.delicado(x[2])]

    @classmethod
    def de_memoria(cls, memoria):
        return cls(memoria=memoria)

    def tasa_general(self):
        if not hasattr(self, "_tasa"):
            mostradas = sum(par[0] for par in self.pistas.values())
            self._tasa = None if mostradas < MOSTRADAS_MINIMAS else sum(par[1] for par in self.pistas.values()) / mostradas
        return self._tasa

    def parte(self, chat, donde):
        cuenta = self.proyectos.get(chat, {})
        total = sum(cuenta.values())
        return cuenta.get(donde, 0.0) / total if total >= MINIMO_PROYECTO else 1.0

    def vecinos(self, a, filtro=None, apoyo=APOYO, respaldo=True, minimo=0.0):
        if self.delicado(a):
            return []

        def limpio(b):
            return not self.delicado(b) and (filtro is None or filtro(b))

        propios = [x for x in super().vecinos(a, limpio, apoyo) if x[0] >= minimo]
        if propios or not respaldo:
            return propios
        return [x for x in self.viejo.vecinos(a, limpio, apoyo) if x[0] >= minimo]

    def visible(self, c):
        ruta = self.rutas.get(c, c)
        partes = ruta.replace("\\", "/").rstrip("/").split("/")
        return "/".join(partes[-2:]) if len(partes) > 1 else ruta

    def corto(self, c):
        if getattr(self, "_por_nombre", None) is None:
            self._por_nombre = {}
            for x in self.rutas:
                self._por_nombre.setdefault(nombre(x), []).append(x.split("/"))
        partes = self.rutas.get(c, c).replace("\\", "/").rstrip("/").split("/")
        mias = c.split("/")
        otras = [x for x in self._por_nombre.get(nombre(c), ()) if x != mias]
        k = 1
        while k < min(len(partes), PARTES_CORTO) and any(x[-k:] == mias[-k:] for x in otras):
            k += 1
        return "/".join(partes[-k:])


def cola_de(archivo, largo):
    try:
        with open(archivo, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - largo))
            return f.read()
    except OSError:
        return b""


def cola_del_registro(carpeta, ahora):
    crudo = cola_de(carpeta / "eventos.jsonl", COLA)
    if len(crudo) < COLA:
        rotados = []
        for archivo in carpeta.glob("eventos-*.jsonl"):
            try:
                fecha = archivo.stat().st_mtime
            except OSError:
                continue
            if ahora - fecha <= RECIENTE:
                rotados.append((fecha, archivo))
        if rotados:
            crudo = cola_de(max(rotados)[1], COLA - len(crudo)) + b"\n" + crudo
    return crudo


def eventos_recientes(carpeta, ahora):
    crudo = cola_del_registro(carpeta, ahora)
    return list(registro.eventos(crudo.split(b"\n"), ahora - RECIENTE)) if crudo else []


def compactada(eventos, sesion):
    return max((numero(ev.get("t")) for ev in eventos if ev.get("e") == "compacta" and ev.get("s") == sesion), default=0.0)


def leidas_por(eventos, sesion):
    sesion = str(sesion or "")[:8]
    if not sesion:
        return {}
    desde = compactada(eventos, sesion)
    salida = {}
    for ev in eventos:
        if ev.get("s") != sesion or ev.get("e", "post") != "post" or ev.get("k") not in ("leer", "crear") \
                or numero(ev.get("t")) <= desde:
            continue
        r = ev.get("r")
        parcial = isinstance(r, list) and len(r) == 3 and all(type(x) is int for x in r) and 0 < r[1] < r[2]
        tramo = (r[0], r[0] + r[1] - 1) if parcial else None
        for ruta in rutas_de(ev):
            c = clave(ruta)
            if es_nota(c):
                salida.setdefault(c, []).append(tramo)
    return salida


def servidas_por(eventos, sesion):
    sesion = str(sesion or "")[:8]
    if not sesion:
        return set()
    desde = compactada(eventos, sesion)
    salida = set()
    for ev in eventos:
        if ev.get("s") == sesion and ev.get("e") == "aviso" and numero(ev.get("t")) > desde:
            for campo in ("fs", "na"):
                lista = ev.get(campo)
                salida.update(clave(r) for r in (lista if isinstance(lista, list) else ()) if isinstance(r, str))
    return salida


def recientes(carpeta, cwd, lista, ahora=None, sesion="", eventos=None):
    ahora = time.time() if ahora is None else ahora
    eventos = eventos_recientes(carpeta, ahora) if eventos is None else eventos
    if not eventos:
        return {}
    raiz = raiz_de(clave(cwd), lista)
    de_prueba = pruebas(carpeta)
    sesion = str(sesion or "")[:8]
    comprimida = compactada(eventos, sesion)
    salida = {}
    for ev in eventos:
        t = numero(ev.get("t"))
        if ev.get("z") or str(ev.get("s") or "") in de_prueba or ev.get("e", "post") != "post" \
                or ev.get("k") not in TOQUES or raiz_de(clave(ev.get("c") or ""), lista) != raiz:
            continue
        if sesion and ev.get("s") == sesion and t > comprimida and ahora - t <= A_MANO:
            continue
        peso = 0.5 ** (max(0.0, ahora - t) / MEDIA_RECIENTE)
        for ruta in rutas_de(ev):
            c = clave(ruta)
            if util(c) and peso > salida.get(c, 0.0):
                salida[c] = peso
    return salida


class Contexto:
    def __init__(self, aprendido, cercanos=None, proyecto=None, lista=(), leidas=None, cwd="", servidas=None):
        self.aprendido = aprendido
        self.recientes = cercanos or {}
        self.proyecto = proyecto
        self.lista = list(lista)
        self.leidas = leidas or {}
        self.cwd = clave(cwd).rstrip("/") if cwd else ""
        self.servidas = servidas or set()

    def ya_servida(self, ruta):
        return clave(ruta) in self.servidas

    def arriba_del_chat(self, ruta):
        carpeta = clave(ruta).rsplit("/", 1)[0]
        return not self.cwd or self.cwd == carpeta or self.cwd.startswith(carpeta + "/")

    def ya_leido(self, ruta, desde, hasta):
        return any(t is None or (t[0] <= desde and hasta <= t[1]) for t in self.leidas.get(clave(ruta), ()))

    def de_aca(self, c):
        return es_de_codigo(c) and (self.proyecto is None or
                                    self.aprendido.parte(self.proyecto, proyecto_de(c, self.lista)) >= PARTE_PROYECTO)

    def factor(self, ruta):
        c = clave(ruta)
        f = 1.0
        par = self.aprendido.pistas.get(c) if self.aprendido else None
        general = self.aprendido.tasa_general() if self.aprendido else None
        if par and par[0] >= MOSTRADAS_MINIMAS and general is not None and general < 1:
            tasa = (par[1] + PESO_GENERAL * general) / (par[0] + PESO_GENERAL)
            if tasa > general:
                f *= 1 + PREMIO_PISTA * min(1.0, (tasa - general) / (1 - general))
        return f * (1 + PESO_RECIENTE * self.recientes.get(c, 0.0))

    def junto_con(self, ruta, valida):
        if not self.aprendido:
            return []
        return self.aprendido.vecinos(clave(ruta), lambda b: es_nota(b) and valida(b), minimo=FUERZA_MINIMA)

    def codigo_de_nota(self, ruta):
        if not self.aprendido:
            return {}
        salida = {}
        for f, b in self.aprendido.vecinos(clave(ruta), es_de_codigo):
            salida[nombre(b)] = max(f, salida.get(nombre(b), 0.0))
        return salida

    def codigo_con(self, rutas):
        if not self.aprendido:
            return []
        suma = {}
        for ruta in rutas:
            for f, b in self.aprendido.vecinos(clave(ruta), self.de_aca, minimo=FUERZA_CODIGO):
                previo = suma.get(b, (0.0, ruta))
                suma[b] = (previo[0] + f, previo[1] if previo[0] >= f else ruta)
        return sorted(((f, b, self.aprendido.rutas.get(b, b), semilla) for b, (f, semilla) in suma.items()),
                      key=lambda x: (-x[0], x[1]))


def contexto(cwd=None, sesion="", sin_aprendido=False):
    if not prendido():
        return None
    try:
        carpeta = en_vivo()
        aprendido = None if sin_aprendido else cargar(carpeta)
        lista = raices()
        eventos = eventos_recientes(carpeta, time.time()) if cwd or sesion else []
        cercanos = recientes(carpeta, cwd, lista, sesion=sesion, eventos=eventos) if cwd else {}
        leidas = leidas_por(eventos, sesion)
        servidas = servidas_por(eventos, sesion)
    except Exception:
        return None
    return Contexto(aprendido, cercanos, proyecto_de(clave(cwd), lista) if cwd else None, lista, leidas, cwd or "",
                    servidas)


_cache = {}


def cargar(carpeta=None):
    carpeta = carpeta or en_vivo()
    ruta = carpeta / ARCHIVO
    try:
        firma = ruta.stat().st_mtime_ns
    except OSError:
        return None
    guardado = _cache.get(str(ruta))
    if guardado and guardado[0] == firma:
        return guardado[1]
    datos = leer_objeto_json(ruta)
    try:
        aprendido = Aprendido(datos) if datos.get("version") == VERSION else None
    except (TypeError, ValueError, AttributeError):
        aprendido = None
    _cache[str(ruta)] = (firma, aprendido)
    return aprendido
