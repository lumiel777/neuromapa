import re
import time

import configuracion
import registro
from registro import numero

EN_VIVO = configuracion.actual()["datos"] / "en-vivo"
REGISTRO = EN_VIVO / "eventos.jsonl"
VENTANA_ACIERTO = 1800
MAXIMO_FS = 5
CUENTAS_PISTA = ("sugeridas", "sugeridas_ap", "seguidas", "seguidas_ap", "codigo", "codigo_ap", "codigo_visto",
                 "codigo_ap_visto")
DIA = 86400
MARCAS = (b'"k":"consulta"', b'"b":"cerebro"', b'"e":"usuario"', b'"k":"leer"', b'"e":"aviso"', b'"e":"recuerda"')
RE_WORKTREE = re.compile(r"/\.claude/worktrees/[^/]+")
ALIAS_RUTAS = configuracion.actual()["alias_rutas"]


def clave(ruta):
    r = str(ruta).replace("\\", "/").lower()
    for desde, hacia in ALIAS_RUTAS:
        if r.startswith(desde):
            r = hacia + r[len(desde):]
            break
    return RE_WORKTREE.sub("", r)


def nombre_de(ruta):
    return str(ruta).replace("\\", "/").rsplit("/", 1)[-1].split(":", 1)[0].lower()


def rutas_de(valor):
    if not isinstance(valor, list):
        return []
    return [r for r in valor[:MAXIMO_FS] if isinstance(r, str) and r.lower().endswith(".md")]


class Medidor:
    def __init__(self, pruebas=frozenset()):
        self.pruebas = pruebas
        self.visto = False
        self.total = 0
        self.por_opcion = {}
        self.de_agentes = 0
        self.recomendadas = 0
        self.leidas = 0
        self.pedidos = 0
        self.con_consulta = 0
        self.desde = None
        self.ultima = None
        self.pendientes = {}
        self.pedido = {}
        self.avisos = 0
        self.pistas = dict.fromkeys(CUENTAS_PISTA, 0)
        self.de_avisos = {}
        self.recordadas = 0
        self.recordadas_leidas = 0
        self.de_recuerdos = {}

    def anotar(self, ev):
        if registro.de_prueba(ev, self.pruebas):
            return
        fase = ev.get("e", "post")
        s = str(ev.get("s") or "")
        a = str(ev.get("a") or "")
        t = numero(ev.get("t"))
        if fase == "aviso":
            self.aviso(ev, s, t)
            return
        if fase == "recuerda":
            self.recuerdo(ev, s, t)
            return
        if fase == "usuario":
            if s:
                self.pedido[s] = False
                if self.visto:
                    self.pedidos += 1
            return
        if fase != "post":
            return
        k = ev.get("k")
        if k == "consulta" or ev.get("b") == "cerebro":
            if not self.visto and s in self.pedido:
                self.pedidos += 1
            self.visto = True
        if k in ("leer", "editar", "crear"):
            self.seguir_aviso(ev, s, t, k)
        if k == "leer" and not a:
            self.seguir_recuerdo(ev, s, t)
        if k == "consulta":
            self.consulta(ev, s, a, t)
        elif k == "leer":
            self.lectura(ev, s, a, t)

    def consulta(self, ev, s, a, t):
        opcion = ev.get("p") if ev.get("p") in registro.OPCIONES_CONSULTA else "otra"
        self.total += 1
        self.por_opcion[opcion] = self.por_opcion.get(opcion, 0) + 1
        if t:
            self.desde = t if self.desde is None else min(self.desde, t)
            self.ultima = t if self.ultima is None else max(self.ultima, t)
        if a:
            self.de_agentes += 1
        elif self.pedido.get(s) is False:
            self.pedido[s] = True
            self.con_consulta += 1
        rutas = rutas_de(ev.get("fs"))
        if not rutas:
            return
        pendientes = self.pendientes.setdefault((s, a), {})
        for c in [c for c, t0 in pendientes.items() if t - t0 > VENTANA_ACIERTO]:
            del pendientes[c]
        for ruta in rutas:
            c = clave(ruta)
            if c not in pendientes:
                self.recomendadas += 1
            pendientes[c] = t

    def aviso(self, ev, s, t):
        if not s:
            return
        self.avisos += 1
        if t:
            self.desde = t if self.desde is None else min(self.desde, t)
            self.ultima = t if self.ultima is None else max(self.ultima, t)
        pendientes = self.de_avisos.setdefault(s, {})
        for c in [c for c, (t0, _) in pendientes.items() if t - t0 > VENTANA_ACIERTO]:
            del pendientes[c]
        aprendidas = {clave(r) for r in rutas_de(ev.get("na"))}
        for ruta in rutas_de(ev.get("fs")):
            c = clave(ruta)
            if ("nota", c) not in pendientes:
                self.pistas["sugeridas"] += 1
                self.pistas["sugeridas_ap"] += c in aprendidas
                pendientes[("nota", c)] = (t, c in aprendidas)
        for campo, aprendido in (("fc", False), ("ca", True)):
            valor = ev.get(campo)
            for ruta in valor[:MAXIMO_FS] if isinstance(valor, list) else []:
                if not isinstance(ruta, str):
                    continue
                llave = ("ruta", clave(ruta)) if aprendido else ("codigo", nombre_de(ruta))
                if llave not in pendientes:
                    self.pistas["codigo_ap" if aprendido else "codigo"] += 1
                    pendientes[llave] = (t, aprendido)

    def seguir_aviso(self, ev, s, t, k):
        pendientes = self.de_avisos.get(s)
        if not pendientes:
            return
        rutas = [ev["f"]] if isinstance(ev.get("f"), str) else []
        rutas += [r for r in (ev.get("fs") or [])[:MAXIMO_FS] if isinstance(r, str)] if isinstance(ev.get("fs"), list) else []
        for ruta in rutas:
            llaves = [("codigo", nombre_de(ruta)), ("ruta", clave(ruta))] + ([("nota", clave(ruta))] if k == "leer" else [])
            for llave in llaves:
                previo = pendientes.pop(llave, None)
                if previo is None or t - previo[0] > VENTANA_ACIERTO:
                    continue
                if llave[0] == "nota":
                    self.pistas["seguidas_ap" if previo[1] else "seguidas"] += 1
                else:
                    self.pistas["codigo_ap_visto" if previo[1] else "codigo_visto"] += 1

    def recuerdo(self, ev, s, t):
        if not s:
            return
        pendientes = self.de_recuerdos.setdefault(s, {})
        for ruta in rutas_de(ev.get("fs")):
            c = clave(ruta)
            if c not in pendientes:
                self.recordadas += 1
            pendientes[c] = t

    def seguir_recuerdo(self, ev, s, t):
        pendientes = self.de_recuerdos.get(s)
        if not pendientes:
            return
        rutas = ([ev["f"]] if isinstance(ev.get("f"), str) else []) + rutas_de(ev.get("fs"))
        for ruta in rutas:
            t0 = pendientes.pop(clave(ruta), None)
            if t0 is not None and t - t0 <= VENTANA_ACIERTO:
                self.recordadas_leidas += 1

    def lectura(self, ev, s, a, t):
        rutas = rutas_de(ev.get("fs"))
        if isinstance(ev.get("f"), str):
            rutas.insert(0, ev["f"])
        pendientes = self.pendientes.get((s, a))
        if not pendientes:
            return
        for ruta in rutas:
            t0 = pendientes.pop(clave(ruta), None)
            if t0 is not None and t - t0 <= VENTANA_ACIERTO:
                self.leidas += 1
        if not pendientes:
            del self.pendientes[(s, a)]

    def resumen(self):
        return {"visto": self.visto, "total": self.total, "porOpcion": dict(self.por_opcion), "deAgentes": self.de_agentes,
                "recomendadas": self.recomendadas, "leidas": self.leidas, "pedidos": self.pedidos,
                "conConsulta": self.con_consulta, "desde": self.desde, "ultima": self.ultima, "avisos": self.avisos,
                "recordadas": self.recordadas, "recordadasLeidas": self.recordadas_leidas, **self.pistas}


def del_registro(desde):
    medidor = Medidor(registro.sesiones_de_prueba(EN_VIVO))
    crudos = []
    for archivo in registro.archivos_desde(EN_VIVO, desde):
        try:
            crudos.append(archivo.read_bytes())
        except OSError:
            continue
    if not any(b'"cerebro"' in crudo or b'"e":"aviso"' in crudo or b'"e":"recuerda"' in crudo for crudo in crudos):
        return medidor
    for ev in registro.eventos((linea for crudo in crudos for linea in crudo.split(b"\n")), desde, MARCAS):
        medidor.anotar(ev)
    return medidor


def porcentaje(parte, total):
    return f"{round(100 * parte / total)} %" if total else "—"


def linea_pistas(r):
    if not r["avisos"]:
        return ""
    avisos = "1 aviso" if r["avisos"] == 1 else f'{r["avisos"]} avisos'
    sugeridas = r["sugeridas"]
    seguidas = r["seguidas"] + r["seguidas_ap"]
    partes = [f' Pistas del hook (últimas 24 h): {avisos}; de las {sugeridas} notas que recomendó se leyeron después '
              f'{seguidas} ({porcentaje(seguidas, sugeridas)})']
    if r["sugeridas_ap"]:
        partes.append(f'las que sumó lo aprendido, {r["seguidas_ap"]} de {r["sugeridas_ap"]}')
    if r["codigo"] or r["codigo_ap"]:
        partes.append(f'del código para comprobar se abrió {r["codigo_visto"]} de {r["codigo"]} '
                      f'({porcentaje(r["codigo_visto"], r["codigo"])})')
    if r["codigo_ap"]:
        partes.append(f'y del aprendido {r["codigo_ap_visto"]} de {r["codigo_ap"]} '
                      f'({porcentaje(r["codigo_ap_visto"], r["codigo_ap"])})')
    return "; ".join(partes) + "."


def linea_recuerdos(r):
    if not r["recordadas"]:
        return ""
    notas = "1 nota" if r["recordadas"] == 1 else f'{r["recordadas"]} notas'
    return (f' Al editar código (últimas 24 h) le recordó {notas} que suelen ir con ese archivo; se leyeron después '
            f'{r["recordadasLeidas"]} ({porcentaje(r["recordadasLeidas"], r["recordadas"])}).')


def linea_salud(ahora=None):
    ahora = time.time() if ahora is None else ahora
    r = del_registro(ahora - DIA).resumen()
    return linea_consultas(r) + linea_pistas(r) + linea_recuerdos(r)


def linea_consultas(r):
    if not r["visto"] and not r["avisos"] and not r["recordadas"]:
        return "Consultas a Neuromapa (últimas 24 h): sin registro; el hook no anotó nada en ese tiempo."
    if not r["total"]:
        return "Consultas a Neuromapa (últimas 24 h): ninguna."
    opciones = ", ".join(f"--{o} {n}" for o, n in sorted(r["porOpcion"].items(), key=lambda x: (-x[1], x[0])))
    partes = [f'Consultas a Neuromapa (últimas 24 h): {r["total"]} ({opciones})']
    if r["deAgentes"]:
        partes.append(f'{r["deAgentes"]} de agentes')
    if r["pedidos"]:
        partes.append(f'pedidos en que el chat consultó: {r["conConsulta"]} de {r["pedidos"]}')
    if r["recomendadas"]:
        partes.append(f'de las {r["recomendadas"]} notas recomendadas se leyeron después {r["leidas"]} '
                      f'({porcentaje(r["leidas"], r["recomendadas"])})')
    return f'{"; ".join(partes)}.'
