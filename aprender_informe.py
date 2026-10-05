import time

import configuracion
from archivos import leer_objeto_json
from registro import numero
from textos import cantidad

from aprender_comun import (APOYO, ARCHIVO, ARISTAS_MAPA, CAMPOS_DIA, DIAS, FUERZA_MAPA, MOSTRAR, MOSTRAR_DETALLE,
                            VERSION, VIDA_MEDIA, clave, decimal, dia_de, en_vivo, es_nota, prendido)
from aprender_pista import cargar

COMPARAR_MINIMO = 30


def resumen_dias(dias, cuantos, hoy=None):
    hoy = time.time() if hoy is None else hoy
    limite = dia_de(hoy - (cuantos - 1) * 86400)
    suma = dict.fromkeys(CAMPOS_DIA, 0)
    for fecha, cuenta in dias.items():
        if fecha >= limite:
            for k in suma:
                suma[k] += numero(cuenta.get(k))
    return suma


def linea_charlas(aprendido):
    estado = aprendido.charlas
    if not estado["eventos"]:
        return ""
    fecha = time.strftime("%d/%m", time.localtime(estado["hasta"])) if estado["hasta"] else "el registro"
    sigue = "" if estado["listo"] else " (todavía leyendo)"
    return (f'De tus charlas guardadas de antes del {fecha} sacó {estado["eventos"]} lecturas y ediciones{sigue}: '
            f'se usan solo de respaldo, cuando de una nota todavía no aprendió nada nuevo.')


def de_cada(parte, total):
    return f"{parte} de {total} ({round(100 * parte / total)} %)" if total else "—"


def linea_separada(suma):
    if not (suma["codigo_ap"] or suma["notas_ap"]):
        return ""
    return (f'¿Sirve lo aprendido? En las pistas, el código aprendido se abrió después {de_cada(suma["codigo_ap_visto"], suma["codigo_ap"])} '
            f'y el que nombran las notas {de_cada(suma["codigo_visto"], suma["codigo"])}; la nota aprendida se leyó '
            f'{de_cada(suma["seguidas_ap"], suma["notas_ap"])} y las demás '
            f'{de_cada(suma["seguidas"] - suma["seguidas_ap"], suma["notas"] - suma["notas_ap"])}.')


def linea_comparacion(dias, hoy=None):
    activos = sorted(f for f, c in dias.items() if numero(c.get("pistas_sa")))
    if not activos:
        return ""
    suma = resumen_dias({f: c for f, c in dias.items() if f >= activos[0]}, DIAS, hoy)
    sin = suma["pistas_sa"]
    if not sin:
        return ""

    def lado(pistas, utiles, seguidas, notas):
        return f"sirvieron {de_cada(utiles, pistas)} pistas y se leyó {de_cada(seguidas, notas)} de las notas recomendadas"

    con = lado(suma["pistas"] - sin, suma["utiles"] - suma["utiles_sa"], suma["seguidas"] - suma["seguidas_sa"],
               suma["notas"] - suma["notas_sa"])
    sin_lo = lado(sin, suma["utiles_sa"], suma["seguidas_sa"], suma["notas_sa"])
    texto = (f"Comparación (algunos pedidos van sin lo aprendido; una pista sirvió si Claude leyó una nota o abrió un archivo "
             f"de ella): con lo aprendido, {con}; sin lo aprendido, {sin_lo}.")
    if sin < COMPARAR_MINIMO:
        texto += (f" Todavía son pocas para sacar una conclusión: {cantidad(sin, 'pista', 'pistas')} sin lo aprendido, "
                  f"hacen falta {COMPARAR_MINIMO}.")
    return texto


def texto(aprendido, dias, ruta, hoy=None):
    if aprendido is None or not aprendido.veces:
        de_charlas = len(aprendido.viejo.pares()) if aprendido is not None else 0
        if de_charlas:
            return [f"Del registro todavía no aprendió nada (hace falta usar Claude Code con el hook prendido; las "
                    f"corridas de prueba no cuentan), pero ya leyó las charlas guardadas de antes: "
                    f"{cantidad(de_charlas, 'par', 'pares')} de archivos que se usaron juntos, que la pista usa de respaldo."]
        return ["Todavía no aprendió nada: hace falta usar Claude Code con el hook prendido (las corridas de prueba no "
                "cuentan)."]
    suma = resumen_dias(aprendido.dias, dias, hoy)
    lineas = [f"Lo aprendido de tu uso (olvida a la mitad cada {VIDA_MEDIA // 86400} días; las corridas de prueba no "
              "cuentan).",
              f'Últimos {dias} días: {cantidad(suma["pedidos"], "pedido", "pedidos")}, '
              f'{cantidad(suma["toques"], "archivo abierto o editado", "archivos abiertos o editados")}, '
              f'{cantidad(suma["pistas"], "pista", "pistas")} con '
              f'{cantidad(suma["seguidas"], "nota leída", "notas leídas")} después.']
    separado = linea_separada(suma)
    if separado:
        lineas.append(separado)
    comparacion = linea_comparacion(aprendido.dias, hoy)
    if comparacion:
        lineas.append(comparacion)
    charlas = linea_charlas(aprendido)
    if charlas:
        lineas.append(charlas)
    pares = aprendido.pares()
    if pares:
        lineas.append("Se usan juntos (más fuerte primero):")
        lineas += [f"  {decimal(f)}  {aprendido.visible(a)} ↔ {aprendido.visible(b)}" for f, a, b in pares[:MOSTRAR]]
    notas = sorted((c for c in aprendido.veces if es_nota(c)), key=lambda c: -aprendido.veces[c])
    codigo = [(n, aprendido.vecinos(n, lambda b: not es_nota(b), respaldo=False)[:3]) for n in notas]
    codigo = [(n, v) for n, v in codigo if v][:MOSTRAR]
    if codigo:
        lineas.append("Código que se abre con cada nota (lo suma «Para comprobar» aunque la nota no lo nombre):")
        lineas += [f'  {aprendido.visible(n)} → {", ".join(aprendido.visible(b) for _, b in v)}' for n, v in codigo]
    pistas = sorted(((par[1] / par[0], par[0], c) for c, par in aprendido.pistas.items()
                     if par[0] >= 1 and not aprendido.delicado(c)), key=lambda x: (-x[0], -x[1], x[2]))
    if pistas:
        lineas.append("Notas recomendadas y cuántas veces se leyeron después (de cada 10):")
        lineas += [f"  {round(10 * r)}  {aprendido.visible(c)}" for r, _, c in pistas[:MOSTRAR]]
    lineas.append(f"Se guarda en {ruta}. Para apagarlo: «\"aprender\": false» en config.json.")
    return lineas


def para_la_pagina(nodos, hoy=None):
    if not prendido():
        return None, []
    aprendido = cargar()
    if aprendido is None or not aprendido.veces:
        return None, []
    por_clave = {clave(n["ruta"]): n["id"] for n in nodos if n.get("ruta")}
    pares = aprendido.pares()
    aristas = []
    for f, a, b in pares:
        if len(aristas) >= ARISTAS_MAPA or f < FUERZA_MAPA:
            break
        if a in por_clave and b in por_clave and por_clave[a] != por_clave[b]:
            aristas.append({"de": por_clave[a], "a": por_clave[b], "clase": "aprendida", "peso": round(f, 2),
                            "texto": f"se usan juntas en el trabajo (fuerza {decimal(f)})"})

    def lugar(c):
        return {"texto": aprendido.visible(c), "id": por_clave.get(c)}

    notas = sorted((c for c in aprendido.veces if es_nota(c)), key=lambda c: -aprendido.veces[c])
    codigo = [(n, aprendido.vecinos(n, lambda b: not es_nota(b), respaldo=False)[:3]) for n in notas]
    pistas = sorted(((par[1] / par[0], par[0], c) for c, par in aprendido.pistas.items()
                     if par[0] >= 1 and not aprendido.delicado(c)), key=lambda x: (-x[0], -x[1], x[2]))
    semana = resumen_dias(aprendido.dias, 7, hoy)
    return {"semana": semana, "separado": linea_separada(semana), "charlas": linea_charlas(aprendido),
            "vidaMedia": VIDA_MEDIA // 86400, "hecho": aprendido.hecho,
            "pares": [dict(fuerza=round(f, 2), a=lugar(a), b=lugar(b)) for f, a, b in pares[:MOSTRAR]],
            "codigo": [dict(nota=lugar(n), codigo=[aprendido.visible(b) for _, b in v]) for n, v in codigo if v][:MOSTRAR],
            "pistas": [dict(nota=lugar(c), veces=round(veces, 1), leida=round(r, 2)) for r, veces, c in pistas[:MOSTRAR]],
            "aristas": len(aristas), "caminos": [[x["de"], x["a"], x["peso"]] for x in aristas]}, aristas


def linea_salud(hoy=None):
    if not prendido():
        return "Aprendizaje: apagado («aprender»: false en config.json)."
    aprendido = cargar()
    if aprendido is None or not aprendido.veces:
        guardado = leer_objeto_json(en_vivo() / ARCHIVO)
        if guardado and guardado.get("version") != VERSION:
            return ("Aprendizaje: aprendido.json es de otra versión (lo sigue escribiendo un mapa abierto con el código "
                    "anterior): reinicialo (con el plugin, /neuromapa:abrir --reiniciar) y se rearma solo en un minuto.")
        return ("Aprendizaje: todavía sin datos (se rearma solo: cada minuto con el mapa abierto y, si no, al terminar "
                "una respuesta, cada 10 minutos como mucho).")
    suma = resumen_dias(aprendido.dias, 7, hoy)
    linea = (f'Aprendizaje (últimos 7 días): {cantidad(suma["pedidos"], "pedido", "pedidos")}, '
             f'{cantidad(len(aprendido.pares()), "par", "pares")} de archivos que se usan juntos; de las notas que '
             f'recomendó, se leyeron después {suma["seguidas"]}.')
    return " ".join(x for x in (linea, linea_separada(suma), linea_comparacion(aprendido.dias, hoy)) if x)


def conocidas(aprendido):
    todas = set(aprendido.lazos) | set(aprendido.veces) | set(aprendido.viejo.lazos) | set(aprendido.viejo.veces) \
        | set(aprendido.pistas)
    return {c for c in todas if not aprendido.delicado(c)}


def buscar_claves(aprendido, buscado):
    c = clave(str(buscado).strip().strip("\"'")).rstrip("/")
    todas = conocidas(aprendido)
    if not c or c in todas:
        return [c] if c else []
    sufijo = "/" + c.lstrip("/")
    return sorted(x for x in todas if x.endswith(sufijo))


def elegir(aprendido, buscado):
    claves = buscar_claves(aprendido, buscado)
    if len(claves) == 1:
        return claves[0], []
    if not claves:
        return None, [f"No aprendió nada de «{buscado}». Probá con el nombre del archivo o su ruta, como salen en "
                      f"{configuracion.comando()} --aprendido."]
    return None, ([f"Hay {len(claves)} archivos que terminan en «{buscado}»; decí cuál con más de la ruta:"]
                  + [f"  {aprendido.rutas.get(c, c)}" for c in claves[:MOSTRAR_DETALLE]]
                  + ([f"  y {len(claves) - MOSTRAR_DETALLE} más"] if len(claves) > MOSTRAR_DETALLE else []))


def detalle(aprendido, c):
    ruta = aprendido.rutas.get(c, c)
    lineas = [f"Lo aprendido de {ruta} (olvida a la mitad cada {VIDA_MEDIA // 86400} días):"]
    propios = aprendido.vecinos(c, respaldo=False)
    if propios:
        lineas.append("Se usa junto con (más fuerte primero):")
        lineas += [f"  {decimal(f)}  {aprendido.corto(b)}" for f, b in propios[:MOSTRAR_DETALLE]]
        if len(propios) > MOSTRAR_DETALLE:
            lineas.append(f"  y {len(propios) - MOSTRAR_DETALLE} más")
    else:
        lineas.append("Del registro todavía no aprendió con qué se usa.")
    flojas = sum(1 for w in aprendido.lazos.get(c, {}).values() if w < APOYO)
    if flojas:
        lineas.append(f"Además tiene {cantidad(flojas, 'unión floja', 'uniones flojas')}: todavía no cuenta"
                      f"{'' if flojas == 1 else 'n'} (hace falta usarlos juntos algunas veces más).")
    viejos = aprendido.viejo.vecinos(c)
    if viejos:
        lineas.append("De las charlas guardadas de antes (solo de respaldo, si del registro no aprendió nada):")
        lineas += [f"  {decimal(f)}  {aprendido.corto(b)}" for f, b in viejos[:MOSTRAR_DETALLE]]
    par = aprendido.pistas.get(c)
    if par and par[0] >= 1:
        lineas.append(f"Cuando la pista la recomendó, se leyó después {round(10 * par[1] / par[0])} de cada 10 veces.")
    lineas.append(f'Para olvidarlo: {configuracion.comando()} --olvidar "{ruta}"; para olvidar solo una unión, con las '
                  "dos rutas (o el final de cada una, como sale arriba).")
    return lineas
