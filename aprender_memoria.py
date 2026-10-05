import zlib

from registro import numero

from aprender_comun import (CAMPOS_DIA, DESPUES_DE_PISTA, DIAS, HUECO, MINIMO, MISMO_PEDIDO, OLVIDOS, PARES, PESO_PISTA,
                            PESO_PROPIO, PISTAS_ABIERTAS, RE_WORKTREE, SEGUIR, TOQUES, VECINOS, VENTANA, VERSION,
                            VIDA_MEDIA, VISTOS, clave, dia_de, es_de_codigo, es_nota, es_numero, nombre, numeros,
                            proyecto_de, raices, rutas_de, tabla, textos, util)


def abierto_valido(v):
    pares = v.get("pares", []) if isinstance(v, dict) else None
    return isinstance(v, dict) and es_numero(v.get("t")) and textos(v.get("ventana", [])) and textos(v.get("vistos", [])) \
        and isinstance(pares, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in pares)


def charlas_validas(valor):
    valor = tabla(valor)
    posiciones = {k: x for k, x in tabla(valor.get("posiciones")).items()
                  if isinstance(x, int) and not isinstance(x, bool) and x >= 0}
    return {"hasta": numero(valor.get("hasta")), "listo": valor.get("listo") is True, "posiciones": posiciones,
            "eventos": int(numero(valor.get("eventos")))}


def huella_par(a, b):
    return zlib.crc32("\t".join(sorted((a, b))).encode("utf-8"))


def par_olvidado(a, b):
    return "\t".join(sorted((a, b)))


def olvidos_validos(valor):
    valor = tabla(valor)
    return {"archivos": veces_validas(valor.get("archivos")), "pares": veces_validas(valor.get("pares"))}


def pendiente_valido(v):
    return isinstance(v, dict) and es_numero(v.get("t")) \
        and all(textos(v.get(k)) for k in ("notas", "codigo", "leidas", "vistos", "despues")) \
        and all(textos(v.get(k, [])) for k in ("notas_ap", "codigo_ap", "vistos_ap"))


def lazos_validos(valor):
    return {a: {b: float(w) for b, w in v.items() if es_numero(w)} for a, v in tabla(valor).items() if isinstance(v, dict)}


def veces_validas(valor):
    return {c: float(w) for c, w in tabla(valor).items() if es_numero(w)}


def podar_lazos(lazos, veces):
    for a in list(lazos):
        vecinos = {b: w for b, w in lazos[a].items() if w >= MINIMO}
        if len(vecinos) > VECINOS:
            vecinos = dict(sorted(vecinos.items(), key=lambda x: -x[1])[:VECINOS])
        if vecinos:
            lazos[a] = vecinos
        else:
            del lazos[a]
    return {c: w for c, w in veces.items() if w >= MINIMO or c in lazos}


def redondear(lazos, veces):
    return ({a: {b: round(w, 4) for b, w in v.items()} for a, v in lazos.items()},
            {c: round(w, 4) for c, w in veces.items()})


class Memoria:
    def __init__(self, datos=None):
        crudo = datos if isinstance(datos, dict) else {}
        datos = crudo if crudo.get("version") == VERSION else {}
        self.olvidos = olvidos_validos(crudo.get("olvidos"))
        self.hecho = numero(datos.get("hecho"))
        self.hasta = numero(datos.get("hasta"))
        self.lazos = lazos_validos(datos.get("lazos"))
        self.veces = veces_validas(datos.get("veces"))
        viejo = tabla(datos.get("viejo"))
        self.viejo_lazos = lazos_validos(viejo.get("lazos"))
        self.viejo_veces = veces_validas(viejo.get("veces"))
        self.pistas = {c: list(v) for c, v in tabla(datos.get("pistas")).items() if numeros(v, 2)}
        self.codigo = {c: list(v) for c, v in tabla(datos.get("codigo")).items() if numeros(v, 2)}
        self.rutas = {c: RE_WORKTREE.sub("", r, count=1) for c, r in tabla(datos.get("rutas")).items() if isinstance(r, str)}
        self.abiertos = {k: v for k, v in tabla(datos.get("abiertos")).items() if abierto_valido(v)}
        self.pendientes = {}
        for k, v in tabla(datos.get("pendientes")).items():
            validas = [x for x in (v if isinstance(v, list) else [v]) if pendiente_valido(x)][-PISTAS_ABIERTAS:]
            if validas:
                self.pendientes[k] = validas
        self.dias = {k: {campo: int(numero(v.get(campo))) for campo in CAMPOS_DIA}
                     for k, v in tabla(datos.get("dias")).items() if isinstance(v, dict)}
        self.pares = {k: set(v.get("pares", [])) for k, v in self.abiertos.items()}
        self.charlas = charlas_validas(datos.get("charlas"))
        self.proyectos = lazos_validos(datos.get("proyectos"))
        self.raices = None
        self.contar = True
        self.ahora = self.hecho

    def envejecer(self, ahora):
        if self.hecho and ahora > self.hecho:
            f = 0.5 ** ((ahora - self.hecho) / VIDA_MEDIA)
            for lazos, veces in ((self.lazos, self.veces), (self.viejo_lazos, self.viejo_veces)):
                for vecinos in lazos.values():
                    for b in vecinos:
                        vecinos[b] *= f
                for c in veces:
                    veces[c] *= f
            for par in list(self.pistas.values()) + list(self.codigo.values()):
                par[0] *= f
                par[1] *= f
            for cuenta in self.proyectos.values():
                for p in cuenta:
                    cuenta[p] *= f
        self.ahora = ahora

    def peso(self, t):
        return 0.5 ** (max(0.0, self.ahora - t) / VIDA_MEDIA)

    def dia(self, t):
        return self.dias.setdefault(dia_de(t), dict.fromkeys(CAMPOS_DIA, 0))

    def olvidado(self, t, a, b=None):
        archivos = self.olvidos["archivos"]
        if archivos and (archivos.get(a, -1.0) >= t or (b is not None and archivos.get(b, -1.0) >= t)):
            return True
        pares = self.olvidos["pares"]
        return b is not None and bool(pares) and pares.get(par_olvidado(a, b), -1.0) >= t

    def sumar(self, a, b, w, t=None):
        if a == b or (t is not None and self.olvidado(t, a, b)):
            return
        for x, y in ((a, b), (b, a)):
            vecinos = self.lazos.setdefault(x, {})
            vecinos[y] = vecinos.get(y, 0.0) + w

    def olvidar_archivo(self, c, ahora):
        quitados = []
        for lazos, veces in ((self.lazos, self.veces), (self.viejo_lazos, self.viejo_veces)):
            vecinos = lazos.pop(c, {})
            for b in vecinos:
                otros = lazos.get(b)
                if otros is not None:
                    otros.pop(c, None)
                    if not otros:
                        del lazos[b]
            veces.pop(c, None)
            quitados.append(len(vecinos))
        self.pistas.pop(c, None)
        self.rutas.pop(c, None)
        for abierto in self.abiertos.values():
            abierto["ventana"] = [x for x in abierto.get("ventana", ()) if x != c]
        self.olvidos["archivos"][c] = ahora
        return quitados

    def olvidar_par(self, a, b, ahora):
        quitados = []
        for lazos in (self.lazos, self.viejo_lazos):
            hubo = False
            for x, y in ((a, b), (b, a)):
                vecinos = lazos.get(x)
                if vecinos is not None and vecinos.pop(y, None) is not None:
                    hubo = True
                    if not vecinos:
                        del lazos[x]
            quitados.append(int(hubo))
        self.olvidos["pares"][par_olvidado(a, b)] = ahora
        return quitados

    def anotar(self, ev, de_prueba=frozenset()):
        t = numero(ev.get("t"))
        s = str(ev.get("s") or "")
        if not t or not s or ev.get("z") or s in de_prueba:
            return
        fase = ev.get("e", "post")
        a = str(ev.get("a") or "")
        if fase in ("usuario", "aviso") and not a:
            self.empezar(s, t)
        if fase == "aviso" or (fase == "post" and ev.get("k") == "consulta" and ev.get("p") == "sobre"):
            self.pista(s, t, ev)
            return
        if fase != "post" or ev.get("k") not in TOQUES:
            return
        for ruta in rutas_de(ev):
            self.tocar(s, a, t, ruta, str(ev.get("c") or ""))

    def empezar(self, s, t):
        previo = self.abiertos.get(f"{s}|")
        if previo and 0 <= t - numero(previo.get("inicio")) <= MISMO_PEDIDO:
            return
        self.abiertos[f"{s}|"] = {"t": t, "inicio": t, "ventana": [], "vistos": []}
        self.pares[f"{s}|"] = set()
        if self.contar:
            self.dia(t)["pedidos"] += 1

    def tocar(self, s, a, t, ruta, cwd=""):
        c = clave(ruta)
        if not util(c) or self.olvidado(t, c):
            return
        self.rutas[c] = RE_WORKTREE.sub("", ruta, count=1)
        p = self.peso(t)
        k = f"{s}|{a}"
        abierto = self.abiertos.get(k)
        if abierto is None or t - numero(abierto.get("t")) > HUECO:
            abierto = self.abiertos[k] = {"t": t, "inicio": t, "ventana": [], "vistos": []}
            self.pares[k] = set()
        pares = self.pares.setdefault(k, set())
        ventana = [x for x in abierto.get("ventana", ()) if isinstance(x, str)]
        nota_de_agente = bool(a) and es_nota(c)
        if c in ventana:
            ventana.remove(c)
        else:
            for otra in ventana:
                if nota_de_agente and es_nota(otra):
                    continue
                huella = huella_par(c, otra)
                if huella in pares:
                    continue
                if len(pares) < PARES:
                    pares.add(huella)
                self.sumar(c, otra, p * (PESO_PROPIO if self.sugerido(s, t, c, otra) else 1.0), t)
        abierto["ventana"] = (ventana + [c])[-VENTANA:]
        vistos = abierto.get("vistos") if isinstance(abierto.get("vistos"), list) else []
        if c not in vistos:
            if not nota_de_agente:
                self.veces[c] = self.veces.get(c, 0.0) + p
            abierto["vistos"] = (vistos + [c])[-VISTOS:]
            if es_de_codigo(c):
                self.contar_proyecto(cwd, c, p)
        abierto["t"] = t
        if self.contar:
            self.dia(t)["toques"] += 1
        self.seguir(s, t, c)

    def sugerido(self, s, t, a, b):
        for pendiente in self.pendientes.get(s, ()):
            if t - numero(pendiente.get("t")) > SEGUIR:
                continue
            propios = set(pendiente.get("codigo_ap", ())) | set(pendiente.get("notas_ap", ()))
            notas = pendiente.get("notas", ())
            if (a in propios and b in notas) or (b in propios and a in notas):
                return True
        return False

    def contar_proyecto(self, cwd, c, p):
        if self.raices is None:
            try:
                self.raices = raices()
            except Exception:
                self.raices = []
        cuenta = self.proyectos.setdefault(proyecto_de(clave(cwd), self.raices), {})
        donde = proyecto_de(c, self.raices)
        cuenta[donde] = cuenta.get(donde, 0.0) + p

    def pista(self, s, t, ev):
        def lista(campo):
            return [r for r in ev[campo][:5] if isinstance(r, str)] if isinstance(ev.get(campo), list) else []

        codigo_ap = list(dict.fromkeys(clave(r) for r in lista("ca")))
        codigo = list(dict.fromkeys(nombre(clave(r)) for r in lista("fc")))
        notas_ap = [clave(r) for r in lista("na")]
        notas = []
        for ruta in lista("fs"):
            c = clave(ruta)
            if util(c) and c not in notas:
                notas.append(c)
                self.rutas.setdefault(c, RE_WORKTREE.sub("", ruta, count=1))
        if not notas and not codigo and not codigo_ap:
            return
        abiertas = self.pendientes.setdefault(s, [])
        sin = 1 if ev.get("sa") == 1 else 0
        abiertas.append({"t": t, "notas": notas, "codigo": codigo, "leidas": [], "vistos": [], "despues": [],
                         "notas_ap": [c for c in notas_ap if c in notas], "codigo_ap": codigo_ap, "vistos_ap": [], "sa": sin})
        while len(abiertas) > PISTAS_ABIERTAS:
            self.cerrar_pista(abiertas.pop(0))
        self.dia(t)["pistas"] += 1
        self.dia(t)["pistas_sa"] += sin

    def seguir(self, s, t, c):
        abiertas = self.pendientes.get(s)
        if not abiertas:
            return
        for pendiente in list(abiertas):
            if t - numero(pendiente.get("t")) > SEGUIR:
                abiertas.remove(pendiente)
                self.cerrar_pista(pendiente)
                continue
            if c in pendiente["notas"]:
                if c not in pendiente["leidas"]:
                    pendiente["leidas"].append(c)
                continue
            if nombre(c) in pendiente["codigo"] and nombre(c) not in pendiente["vistos"]:
                pendiente["vistos"].append(nombre(c))
            if c in pendiente.get("codigo_ap", ()) and c not in pendiente.setdefault("vistos_ap", []):
                pendiente["vistos_ap"].append(c)
            if c not in pendiente["despues"] and c not in pendiente.get("codigo_ap", ()) \
                    and len(pendiente["despues"]) < DESPUES_DE_PISTA:
                pendiente["despues"].append(c)
        if not abiertas:
            del self.pendientes[s]

    def cerrar_pista(self, pendiente):
        try:
            t = numero(pendiente.get("t"))
            p = self.peso(t)
            for c in pendiente["notas"]:
                if self.olvidado(t, c):
                    continue
                par = self.pistas.setdefault(c, [0.0, 0.0])
                par[0] += p
                par[1] += p if c in pendiente["leidas"] else 0.0
            for n in pendiente["codigo"]:
                par = self.codigo.setdefault(n, [0.0, 0.0])
                par[0] += p
                par[1] += p if n in pendiente["vistos"] else 0.0
            if pendiente["notas"] and pendiente["despues"] and not self.olvidado(t, pendiente["notas"][0]):
                primera = pendiente["notas"][0]
                self.veces[primera] = self.veces.get(primera, 0.0) + PESO_PISTA * p
                for c in pendiente["despues"]:
                    self.sumar(primera, c, PESO_PISTA * p, t)
            notas_ap = set(pendiente.get("notas_ap", ()))
            codigo_ap = set(pendiente.get("codigo_ap", ()))
            dia = self.dia(numero(pendiente.get("t")))
            dia["seguidas"] += len(pendiente["leidas"])
            dia["notas"] += len(pendiente["notas"])
            dia["notas_ap"] += len(notas_ap)
            dia["seguidas_ap"] += len(notas_ap & set(pendiente["leidas"]))
            dia["codigo"] += len(set(pendiente["codigo"]))
            dia["codigo_visto"] += len(set(pendiente["vistos"]))
            dia["codigo_ap"] += len(codigo_ap)
            dia["codigo_ap_visto"] += len(codigo_ap & set(pendiente.get("vistos_ap", ())))
            util = 1 if pendiente["leidas"] or pendiente["vistos"] or pendiente.get("vistos_ap") else 0
            dia["utiles"] += util
            if pendiente.get("sa"):
                dia["utiles_sa"] += util
                dia["notas_sa"] += len(pendiente["notas"])
                dia["seguidas_sa"] += len(pendiente["leidas"])
                dia["codigo_sa"] += len(set(pendiente["codigo"]))
                dia["codigo_visto_sa"] += len(set(pendiente["vistos"]))
        except (KeyError, TypeError, AttributeError):
            pass

    def cerrar(self, hasta):
        for s, abiertas in list(self.pendientes.items()):
            for pendiente in list(abiertas):
                if hasta - numero(pendiente.get("t")) > SEGUIR:
                    abiertas.remove(pendiente)
                    self.cerrar_pista(pendiente)
            if not abiertas:
                del self.pendientes[s]
        for k, abierto in list(self.abiertos.items()):
            if hasta - numero(abierto.get("t")) > HUECO:
                del self.abiertos[k]
                self.pares.pop(k, None)

    def podar(self):
        self.veces = podar_lazos(self.lazos, self.veces)
        self.viejo_veces = podar_lazos(self.viejo_lazos, self.viejo_veces)
        self.pistas = {c: par for c, par in self.pistas.items() if par[0] >= MINIMO}
        self.codigo = {c: par for c, par in self.codigo.items() if par[0] >= MINIMO}
        self.proyectos = {chat: cuenta for chat, cuenta in
                          ((chat, {p: w for p, w in cuenta.items() if w >= MINIMO}) for chat, cuenta in self.proyectos.items())
                          if cuenta}
        vivos = set(self.lazos) | set(self.veces) | set(self.pistas) | set(self.viejo_lazos) | set(self.viejo_veces)
        self.rutas = {c: r for c, r in self.rutas.items() if c in vivos}
        self.dias = dict(sorted(self.dias.items())[-DIAS:])

    def abiertas(self):
        return sum(len(v) for v in self.pendientes.values()) + len(self.abiertos)

    def datos(self):
        lazos, veces = redondear(self.lazos, self.veces)
        viejo_lazos, viejo_veces = redondear(self.viejo_lazos, self.viejo_veces)
        return {"version": VERSION, "hecho": round(self.hecho, 3), "hasta": round(self.hasta, 3),
                "lazos": lazos, "veces": veces, "viejo": {"lazos": viejo_lazos, "veces": viejo_veces},
                "pistas": {c: [round(x, 4) for x in par] for c, par in self.pistas.items()},
                "codigo": {c: [round(x, 4) for x in par] for c, par in self.codigo.items()},
                "rutas": self.rutas, "pendientes": self.pendientes, "dias": self.dias, "charlas": self.charlas,
                "proyectos": {chat: {p: round(w, 4) for p, w in cuenta.items()} for chat, cuenta in self.proyectos.items()},
                "abiertos": {k: dict(v, pares=sorted(self.pares.get(k, ()))) for k, v in self.abiertos.items()},
                "olvidos": {tipo: {c: round(t, 3) for c, t in sorted(cuales.items(), key=lambda x: -x[1])[:OLVIDOS]}
                            for tipo, cuales in self.olvidos.items()}}
