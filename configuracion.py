import difflib
import json
import os
import re
import sys
from pathlib import Path

import donde
import permisos

CARPETA = Path(__file__).resolve().parent
PROPIA = CARPETA / "config.json"
DEMO = CARPETA / "demo" / "config.json"
BORRAR_REGISTROS_DIAS = 90
TOPE_DORMIR = 20
TOPE_COMPARAR = 0.5
TOPE_INDICE_KB = 25
PARTIR_SOLA = {"desde": 85, "hasta": 50, "dias_frescos": 3}
LOBULOS = ("prefrontal", "frontal", "parietal", "occipital", "temporal", "cerebelo", "tronco")
PODAR = ["node_modules", ".git", ".next", "dist", "bin", "obj", ".claude", "__pycache__", ".venv", "venv", ".obsidian",
         ".trash"]
EXCLUIR_FRAGMENTOS = ["\\.claude\\worktrees", "node_modules", "\\.git\\", "\\.next\\", "\\dist\\", "\\bin\\", "\\obj\\",
                      "__pycache__"]
SI_O_NO_FUENTE = ("memoria", "foco", "historico", "registro", "planes_vigentes", "anclas_resumidas", "huerfanas")
CLAVES = {
    "arriba": ("usuario", "fuentes", "proyectos", "lobulos", "alias_rutas", "podar", "podar_si_contiene",
               "excluir_fragmentos", "excluir_claude_bajo", "carpetas_pesadas", "prefijos_tabla", "handoffs", "freno",
               "dormir_con_claude", "partir_sola", "indice_meta_kb", "borrar_registros_dias", "aprender",
               "ordenar_con_preguntas", "comparar_aprendido", "sensibles"),
    "fuente": ("id", "nombre", "color", "raices", "patron", "excluir", "proyecto", "peso_busqueda", "prioridad", "lobulo",
               "ancla") + SI_O_NO_FUENTE,
    "raiz": ("ruta", "recursivo", "alias"),
    "proyecto": ("raiz", "alias", "marca", "pistas", "extensiones", "codigo", "remite_a", "prefijo_carpeta", "nombre",
                 "color", "marca_seccion", "aparte"),
    "codigo": ("ruta", "marca"),
    "handoffs": ("prefijo", "nombre", "lados"),
    "lado": ("id", "nombre", "palabras"),
    "freno": ("tokens_de_agentes_por_hora", "workflow_siempre"),
    "dormir_con_claude": ("tope_usd_por_dia", "modelo"),
    "pesada": ("contiene", "bajar_solo"),
}


class ConfigInvalida(ValueError):
    def __init__(self, mensaje, falta=False):
        super().__init__(mensaje)
        self.falta = falta


def archivo():
    if "--demo" in sys.argv[1:]:
        return DEMO
    return Path(donde.config()[0])


def entorno(ruta=None):
    ruta = Path(ruta) if ruta else archivo()
    variables = dict(os.environ)
    if ruta.is_file() or ruta in (PROPIA, DEMO):
        variables["CEREBRO_CONFIG"] = str(ruta)
    else:
        variables.pop("CEREBRO_CONFIG", None)
        variables["CLAUDE_PLUGIN_OPTION_CARPETA_DATOS"] = str(ruta.parent)
    return variables


def resolver(ruta, base):
    camino = Path(os.path.expandvars(os.path.expanduser(str(ruta))))
    return str(camino if camino.is_absolute() else base / camino)


def lista(valor, campo):
    if valor is None:
        return []
    if not isinstance(valor, list):
        raise ConfigInvalida(f"{campo} tiene que ser una lista, entre corchetes: [ … ]")
    return valor


def textos(valor, campo, minusculas=False):
    if valor is None:
        return []
    if not isinstance(valor, list) or not all(isinstance(x, str) for x in valor):
        raise ConfigInvalida(f"{campo} tiene que ser una lista de textos")
    return [x.lower() for x in valor] if minusculas else list(valor)


def raiz_de(valor, campo, base):
    if isinstance(valor, str):
        valor = [valor, False, ""]
    elif isinstance(valor, dict):
        valor = [valor.get("ruta"), valor.get("recursivo", False), valor.get("alias", "")]
    if not isinstance(valor, list) or len(valor) != 3 or not isinstance(valor[0], str) or not valor[0]:
        raise ConfigInvalida(f"{campo} tiene que ser una ruta, o [ruta, recursivo, alias]")
    if not isinstance(valor[1], bool):
        raise ConfigInvalida(f"en {campo}, recursivo va true o false, sin comillas")
    return resolver(valor[0], base), valor[1], str(valor[2] or "")


def sin_alias_repetido(raices):
    reservados = {alias for _, _, alias in raices}
    tomados = set()
    salida = []
    for ruta, recursivo, alias in raices:
        if alias in tomados:
            nombre = Path(ruta).name or "raiz"
            alias, n = nombre, 2
            while alias in tomados or alias in reservados:
                alias, n = f"{nombre}-{n}", n + 1
        tomados.add(alias)
        salida.append((ruta, recursivo, alias))
    return salida


def fuentes_de(datos, base):
    salida = []
    vistos = set()
    for i, fuente in enumerate(lista(datos.get("fuentes"), "fuentes")):
        campo = f"fuentes[{i}]"
        if not isinstance(fuente, dict) or not isinstance(fuente.get("id"), str) or not fuente["id"]:
            raise ConfigInvalida(f"{campo} necesita un id")
        if fuente["id"] in vistos:
            raise ConfigInvalida(f'el id «{fuente["id"]}» está repetido en fuentes')
        vistos.add(fuente["id"])
        for clave in SI_O_NO_FUENTE:
            if clave in fuente and not isinstance(fuente[clave], bool):
                raise ConfigInvalida(f"{campo}.{clave} tiene que ser true o false, sin comillas")
        for clave in ("patron", "proyecto"):
            if fuente.get(clave) is not None and not isinstance(fuente[clave], str):
                raise ConfigInvalida(f"{campo}.{clave} tiene que ser un texto, entre comillas")
        armada = dict(fuente)
        armada["nombre"] = str(fuente.get("nombre") or fuente["id"])
        armada["color"] = str(fuente.get("color") or "#868E96")
        armada["raices"] = sin_alias_repetido([raiz_de(r, f"{campo}.raices", base)
                                               for r in lista(fuente.get("raices"), f"{campo}.raices")])
        if fuente.get("memoria"):
            armada["proyecto"] = resolver(fuente["proyecto"], base) if fuente.get("proyecto") else ""
        if "excluir" in fuente:
            armada["excluir"] = textos(fuente["excluir"], f"{campo}.excluir")
        for clave, tipos in (("peso_busqueda", (int, float)), ("prioridad", (int,))):
            if clave in fuente and (isinstance(fuente[clave], bool) or not isinstance(fuente[clave], tipos)):
                raise ConfigInvalida(f"{campo}.{clave} tiene que ser un número")
        if "peso_busqueda" in fuente and fuente["peso_busqueda"] <= 0:
            raise ConfigInvalida(f"{campo}.peso_busqueda tiene que ser mayor que 0 (1 es el peso de fábrica)")
        if "lobulo" in fuente and fuente["lobulo"] not in LOBULOS:
            raise ConfigInvalida(f'{campo}.lobulo tiene que ser uno de: {", ".join(LOBULOS)}')
        ancla = fuente.get("ancla")
        if ancla is not None and not (isinstance(ancla, list) and len(ancla) in (3, 4) and
                                      all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in ancla)):
            raise ConfigInvalida(f"{campo}.ancla tiene que ser [x, y, radio] o [x, y, radio, achatado]")
        salida.append(armada)
    return salida


def expresion(valor, campo):
    if not isinstance(valor, str):
        raise ConfigInvalida(f"{campo} tiene que ser un texto con una expresión regular")
    try:
        return re.compile(valor)
    except re.error as error:
        donde_falla = f" (se rompe en el carácter {error.pos + 1})" if error.pos is not None else ""
        raise ConfigInvalida(f"{campo} no es una expresión regular válida{donde_falla}") from error


def codigo_de(valor, campo, base):
    salida = []
    for i, raiz in enumerate(lista(valor, campo)):
        if isinstance(raiz, str):
            raiz = {"ruta": raiz}
        if not isinstance(raiz, dict) or not isinstance(raiz.get("ruta"), str) or not raiz["ruta"]:
            raise ConfigInvalida(f"{campo}[{i}] necesita una ruta")
        marca = expresion(raiz["marca"], f"{campo}[{i}].marca") if raiz.get("marca") else None
        salida.append({"ruta": resolver(raiz["ruta"], base), "marca": marca})
    return salida


def proyectos_de(datos, base):
    salida = []
    for i, proyecto in enumerate(lista(datos.get("proyectos"), "proyectos")):
        campo = f"proyectos[{i}]"
        if not isinstance(proyecto, dict) or not isinstance(proyecto.get("raiz"), str) or not proyecto["raiz"]:
            raise ConfigInvalida(f"{campo} necesita una raiz")
        raiz = resolver(proyecto["raiz"], base)
        alias = str(proyecto.get("alias") or Path(raiz).name)
        marca = expresion(proyecto.get("marca") or f"(?<!\\w){re.escape(alias)}(?!\\w)", f"{campo}.marca")
        pistas = textos(proyecto.get("pistas"), f"{campo}.pistas", True) or [alias.lower()]
        armado = {"raiz": raiz, "alias": alias, "marca": marca, "pistas": pistas,
                  "extensiones": textos(proyecto.get("extensiones"), f"{campo}.extensiones", True),
                  "codigo": codigo_de(proyecto.get("codigo"), f"{campo}.codigo", base)}
        for clave in ("remite_a", "prefijo_carpeta", "nombre", "color"):
            if proyecto.get(clave) is not None:
                if not isinstance(proyecto[clave], str) or not proyecto[clave]:
                    raise ConfigInvalida(f"{campo}.{clave} tiene que ser un texto")
                armado[clave] = proyecto[clave]
        if proyecto.get("marca_seccion"):
            armado["marca_seccion"] = expresion(proyecto["marca_seccion"], f"{campo}.marca_seccion")
        if proyecto.get("aparte") is not None:
            if not isinstance(proyecto["aparte"], bool):
                raise ConfigInvalida(f"{campo}.aparte tiene que ser true o false")
            armado["aparte"] = proyecto["aparte"]
        salida.append(armado)
    alias = {p["alias"] for p in salida}
    for p in salida:
        if p.get("remite_a") and p["remite_a"] not in alias:
            raise ConfigInvalida(f'el proyecto «{p["alias"]}» remite a «{p["remite_a"]}», que no está en proyectos')
    return salida


def pesadas_de(datos):
    salida = []
    for i, pesada in enumerate(lista(datos.get("carpetas_pesadas"), "carpetas_pesadas")):
        campo = f"carpetas_pesadas[{i}]"
        bajar = pesada.get("bajar_solo") if isinstance(pesada, dict) else None
        if not isinstance(pesada, dict) or not isinstance(pesada.get("contiene"), str) or not isinstance(bajar, dict):
            raise ConfigInvalida(f"{campo} necesita «contiene» y «bajar_solo»")
        salida.append({"contiene": pesada["contiene"].lower(), "bajar_solo": {str(k).lower(): str(v) for k, v in bajar.items()}})
    return salida


def alias_de(datos, base):
    salida = []
    for i, par in enumerate(lista(datos.get("alias_rutas"), "alias_rutas")):
        if not isinstance(par, list) or len(par) != 2 or not all(isinstance(x, str) and x for x in par):
            raise ConfigInvalida(f"alias_rutas[{i}] tiene que ser [ruta que se ve, ruta real]")
        desde, hacia = (resolver(x, base).replace("\\", "/").lower().rstrip("/") + "/" for x in par)
        salida.append((desde, hacia))
    return salida


def rotulos_de(datos):
    rotulos = datos.get("lobulos") or {}
    if not isinstance(rotulos, dict) or not all(k in LOBULOS and isinstance(v, str) for k, v in rotulos.items()):
        raise ConfigInvalida(f'lobulos tiene que ser {{lóbulo: rótulo}}, con lóbulos de: {", ".join(LOBULOS)}')
    return dict(rotulos)


def handoffs_de(datos):
    valor = datos.get("handoffs")
    if valor is None:
        return None
    if not isinstance(valor, dict) or not isinstance(valor.get("prefijo"), str) or not valor["prefijo"].strip():
        raise ConfigInvalida("handoffs necesita un «prefijo», el principio del nombre de sus archivos")
    lados = []
    for i, lado in enumerate(lista(valor.get("lados"), "handoffs.lados")):
        campo = f"handoffs.lados[{i}]"
        if not isinstance(lado, dict) or not isinstance(lado.get("id"), str) or not lado["id"]:
            raise ConfigInvalida(f"{campo} necesita un id")
        lados.append({"id": lado["id"], "nombre": str(lado.get("nombre") or lado["id"]),
                      "palabras": textos(lado.get("palabras"), f"{campo}.palabras", True) or [lado["id"].lower()]})
    return {"prefijo": valor["prefijo"].strip(), "nombre": str(valor.get("nombre") or "Handoffs"), "lados": lados}


def freno_de(datos):
    valor = datos.get("freno")
    if valor is None:
        return None
    tope = valor.get("tokens_de_agentes_por_hora") if isinstance(valor, dict) else None
    if isinstance(tope, bool) or not isinstance(tope, int) or tope <= 0:
        raise ConfigInvalida("freno necesita «tokens_de_agentes_por_hora», un número entero mayor que cero")
    siempre = valor.get("workflow_siempre", False)
    if not isinstance(siempre, bool):
        raise ConfigInvalida("en freno, «workflow_siempre» va true o false")
    return {"tokens_de_agentes_por_hora": tope, "workflow_siempre": siempre}


def dormir_con_claude_de(datos):
    valor = datos.get("dormir_con_claude")
    if valor is None or valor is False:
        return None
    tope = valor.get("tope_usd_por_dia") if isinstance(valor, dict) else None
    if isinstance(tope, bool) or not isinstance(tope, (int, float)) or not 0 < tope <= TOPE_DORMIR:
        raise ConfigInvalida(f"dormir_con_claude necesita «tope_usd_por_dia», un número mayor que cero y hasta {TOPE_DORMIR}")
    modelo = valor.get("modelo", "sonnet")
    if not isinstance(modelo, str) or not re.fullmatch(r"[\w.\-\[\]]{2,60}", modelo):
        raise ConfigInvalida("en dormir_con_claude, «modelo» tiene que ser el nombre de un modelo, como sonnet")
    return {"tope_usd_por_dia": float(tope), "modelo": modelo}


def comparar_aprendido_de(datos):
    valor = datos.get("comparar_aprendido", 0)
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not 0 <= valor <= TOPE_COMPARAR:
        raise ConfigInvalida(f"comparar_aprendido tiene que ser la parte de los pedidos que van sin lo aprendido, de 0 a "
                             f"{TOPE_COMPARAR} (0,2 es uno de cada cinco; 0 lo apaga)")
    return float(valor)


def dias_de_registro(datos):
    dias = datos.get("borrar_registros_dias", BORRAR_REGISTROS_DIAS)
    if isinstance(dias, bool) or not isinstance(dias, int) or dias < 0:
        raise ConfigInvalida("borrar_registros_dias tiene que ser un número entero de días (0: no borrar nunca)")
    return dias


def partir_sola_de(datos):
    valor = datos.get("partir_sola")
    if valor is None or valor is False:
        return None
    opciones = dict(PARTIR_SOLA)
    if valor is not True:
        if not isinstance(valor, dict) or set(valor) - set(PARTIR_SOLA):
            raise ConfigInvalida(f'partir_sola va true, false o un objeto con {", ".join(PARTIR_SOLA)}')
        opciones.update(valor)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in opciones.values()) \
            or not 10 <= opciones["hasta"] < opciones["desde"] <= 100 or opciones["dias_frescos"] < 0:
        raise ConfigInvalida("en partir_sola, «desde» y «hasta» son porcentajes del tope de una lectura (hasta menor que "
                             "desde, como 85 y 50) y «dias_frescos», cuántos días de entradas nuevas no se tocan")
    return opciones


def indice_meta_de(datos):
    valor = datos.get("indice_meta_kb")
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not 0 < valor <= TOPE_INDICE_KB:
        raise ConfigInvalida(f"indice_meta_kb es la meta del índice de la memoria en KB: el médico avisa cuando la pasa "
                             f"(un número de más de 0 hasta {TOPE_INDICE_KB}, el tope que Claude lee al arrancar)")
    return valor


def aprender_de(datos):
    valor = datos.get("aprender", True)
    if not isinstance(valor, bool):
        raise ConfigInvalida("aprender va true o false")
    return valor


def ordenar_con_preguntas_de(datos):
    valor = datos.get("ordenar_con_preguntas", True)
    if not isinstance(valor, bool):
        raise ConfigInvalida("ordenar_con_preguntas va true o false")
    return valor


def claves_desconocidas(datos):
    avisos = []

    def revisar(objeto, clase, campo):
        if not isinstance(objeto, dict):
            return
        for clave in objeto:
            if clave in CLAVES[clase] or clave.startswith(("_", "$", "//")):
                continue
            parecida = difflib.get_close_matches(clave, CLAVES[clase], 1, 0.6)
            avisos.append(f"{campo} tiene «{clave}», que Neuromapa no conoce"
                          + (f" (¿quisiste decir «{parecida[0]}»?)" if parecida else "") + ": no hace nada.")

    revisar(datos, "arriba", "la configuración")
    for i, fuente in enumerate(datos.get("fuentes") or []):
        nombre = f"fuentes[{i}] («{fuente.get('id')}»)"
        revisar(fuente, "fuente", nombre)
        for j, raiz in enumerate(fuente.get("raices") or []):
            revisar(raiz, "raiz", f"{nombre}.raices[{j}]")
    for i, proyecto in enumerate(datos.get("proyectos") or []):
        nombre = f"proyectos[{i}] («{proyecto.get('alias') or proyecto.get('raiz')}»)"
        revisar(proyecto, "proyecto", nombre)
        for j, raiz in enumerate(proyecto.get("codigo") or []):
            revisar(raiz, "codigo", f"{nombre}.codigo[{j}]")
    for clave in ("handoffs", "freno", "dormir_con_claude"):
        revisar(datos.get(clave), clave, clave)
    for i, lado in enumerate((datos.get("handoffs") or {}).get("lados") or []):
        revisar(lado, "lado", f"handoffs.lados[{i}]")
    for i, pesada in enumerate(datos.get("carpetas_pesadas") or []):
        revisar(pesada, "pesada", f"carpetas_pesadas[{i}]")
    return avisos


def armar(datos, base):
    if not isinstance(datos, dict):
        raise ConfigInvalida("la configuración tiene que ser un objeto JSON")
    if not isinstance(datos.get("usuario", ""), str):
        raise ConfigInvalida("usuario tiene que ser un texto")
    armada = {
        "datos": Path(base),
        "usuario": datos.get("usuario", ""),
        "lobulos": rotulos_de(datos),
        "alias_rutas": alias_de(datos, base),
        "fuentes": fuentes_de(datos, base),
        "proyectos": proyectos_de(datos, base),
        "podar": textos(datos.get("podar", PODAR), "podar", True),
        "podar_si_contiene": textos(datos.get("podar_si_contiene"), "podar_si_contiene", True),
        "excluir_fragmentos": [f.replace("/", "\\") for f in
                               textos(datos.get("excluir_fragmentos", EXCLUIR_FRAGMENTOS), "excluir_fragmentos", True)],
        "excluir_claude_bajo": [resolver(r, base) for r in textos(datos.get("excluir_claude_bajo"), "excluir_claude_bajo")],
        "carpetas_pesadas": pesadas_de(datos),
        "prefijos_tabla": textos(datos.get("prefijos_tabla"), "prefijos_tabla", True),
        "handoffs": handoffs_de(datos),
        "freno": freno_de(datos),
        "dormir_con_claude": dormir_con_claude_de(datos),
        "partir_sola": partir_sola_de(datos),
        "indice_meta_kb": indice_meta_de(datos),
        "borrar_registros_dias": dias_de_registro(datos),
        "aprender": aprender_de(datos),
        "ordenar_con_preguntas": ordenar_con_preguntas_de(datos),
        "comparar_aprendido": comparar_aprendido_de(datos),
        "sensibles": textos(datos.get("sensibles"), "sensibles", True),
    }
    armada["avisos"] = claves_desconocidas(datos)
    return armada


def comando():
    partes = [p.lower() for p in CARPETA.parts]
    en_plugin = (os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.basename(sys.argv[0] or "").startswith("neuromapa")
                 or any(partes[i:i + 2] == ["plugins", "cache"] for i in range(len(partes))))
    base = "neuromapa" if en_plugin else "python " + str(CARPETA / "cerebro.py").replace("\\", "/")
    return f"{base} --demo" if archivo() == DEMO else base


def carpeta_de_claude():
    if archivo() == DEMO:
        return DEMO.parent / "claude"
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def alias_de_memoria(carpeta, casa):
    if carpeta.parent == casa / "agent-memory":
        return f"agente-{carpeta.name}"
    return carpeta.parent.name if carpeta.name == "memory" else carpeta.name


def memoria_movida(casa):
    try:
        datos = json.loads((casa / "settings.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    valor = datos.get("autoMemoryDirectory") if isinstance(datos, dict) else None
    if not isinstance(valor, str) or not valor.strip():
        return []
    ruta = Path(os.path.expanduser(valor.strip()))
    if not ruta.is_absolute() or str(ruta).replace("/", "\\").startswith("\\\\") or not ruta.is_dir():
        return []
    if (ruta / "MEMORY.md").is_file():
        return [ruta]
    return sorted(p for p in ruta.iterdir() if p.is_dir() and (p / "MEMORY.md").is_file())


def por_defecto():
    casa = carpeta_de_claude()
    fuentes = []
    memorias = []
    reales = {}
    alias = []
    candidatas = list(sorted((casa / "projects").glob("*/memory"))) + memoria_movida(casa)
    candidatas += sorted(p for p in (casa / "agent-memory").glob("*") if p.is_dir())
    for carpeta in candidatas:
        if not carpeta.is_dir():
            continue
        real = os.path.normcase(os.path.realpath(carpeta))
        if real in reales:
            alias.append([str(carpeta), str(reales[real])])
        else:
            reales[real] = carpeta
            memorias.append(carpeta)
    if memorias:
        fuentes.append({"id": "memoria", "nombre": "Memoria", "color": "#E64980", "memoria": True,
                        "raices": [[str(p), False, alias_de_memoria(p, casa)] for p in memorias]})
    fuentes.append({"id": "instrucciones", "nombre": "Instrucciones (CLAUDE.md)", "color": "#F59F00",
                    "raices": [[str(casa), False, "usuario"]], "patron": "CLAUDE.md"})
    return {"fuentes": fuentes, "alias_rutas": alias}


_actual = {}


def actual():
    ruta = archivo()
    clave = str(ruta)
    if clave not in _actual:
        _actual[clave] = cargar()
    return _actual[clave]


def cargar(ruta=None):
    if ruta:
        ruta, elegida = Path(os.path.abspath(ruta)), True
    else:
        ruta = archivo()
        elegida = ruta == DEMO or donde.config()[1]
    if not ruta.is_file():
        if ruta == PROPIA:
            return armar(por_defecto(), CARPETA)
        if elegida:
            raise ConfigInvalida(f"no encontré {ruta}", falta=True)
        permisos.crear(ruta.parent)
        return armar(por_defecto(), ruta.parent)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as error:
        raise ConfigInvalida(f"{ruta} no es un JSON válido (se rompe en el renglón {error.lineno}, columna {error.colno})"
                             ) from error
    except UnicodeDecodeError as error:
        raise ConfigInvalida(f"{ruta} no está guardado en UTF-8: abrilo con un editor de texto y guardalo eligiendo la "
                             "codificación UTF-8") from error
    except (OSError, ValueError) as error:
        raise ConfigInvalida(f"no pude leer {ruta}: {error}") from error
    if isinstance(datos, dict) and "fuentes" not in datos:
        datos = dict(por_defecto(), **datos)
    try:
        return armar(datos, ruta.parent)
    except ConfigInvalida as error:
        raise ConfigInvalida(f"{ruta}: {error}") from error
