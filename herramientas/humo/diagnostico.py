from humo.base import *


def revisar_descartes(t):
    cerebro = nucleo.desde_disco()
    todos = medico.revisar(cerebro, filtrar=False)
    nombre = {n["id"]: Path(n["ruta"]).name for n in cerebro.nodos}
    elegido = next((h for h in todos if h["tono"] in medico.TONOS_DESCARTABLES and h["linea"] and h["nota"]
                    and nombre.get(h["nota"]) == "arreglo-login.md"), None)
    sospechas = {(h["nota"], h["linea"]) for h in todos if h["tono"] in medico.TONOS_DESCARTABLES}
    grave = next((h for h in todos if h["tono"] not in medico.TONOS_DESCARTABLES and h["linea"] and h["nota"]
                  and (h["nota"], h["linea"]) not in sospechas), None)
    probar("hay un «para revisar» y un aviso concreto para probar los descartes", elegido is not None and grave is not None,
           sorted({(h["regla"], h["tono"]) for h in todos}))
    if elegido is None or grave is None:
        return
    original = medico.DESCARTADOS
    medico.DESCARTADOS = t / "descartados-prueba.json"

    def correr(funcion, *argumentos):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = funcion(*argumentos)
        return codigo, salida.getvalue()

    def mismo(h):
        return lambda x: (x["regla"], x["nota"], x["linea"]) == (h["regla"], h["nota"], h["linea"])
    try:
        lugar = medico.donde_esta(cerebro, elegido)
        marca = (elegido["linea"], buscador.primera_oracion(elegido["texto"]), elegido["regla"])
        antes = buscador.avisos_del_medico(cerebro).get(elegido["nota"], [])
        codigo, dicho = correr(medico.main_descartar_aviso, lugar, "ya lo revisé")
        guardado = json.loads(medico.DESCARTADOS.read_text(encoding="utf-8"))["descartados"]
        renglon = Path(cerebro.por_id[elegido["nota"]]["ruta"]).read_text(encoding="utf-8").split("\n")[elegido["linea"] - 1]
        probar("--descartar-aviso RUTA:LÍNEA guarda la regla, la nota y una huella del renglón (nunca el texto de la nota)",
               codigo == 0 and "Descartado" in dicho and len(guardado) == 1 and len(guardado[0]["huella"]) == 16
               and guardado[0]["motivo"] == "ya lo revisé"
               and renglon.strip()[:20] not in medico.DESCARTADOS.read_text(encoding="utf-8"),
               (codigo, dicho, guardado))
        de_nuevo = nucleo.desde_disco()
        filtrados = medico.revisar(de_nuevo)
        lineas = medico.informe(de_nuevo, filtrados, 0)
        probar("el aviso descartado ya no sale en el médico (ni en la página, que sale de ahí) y --salud dice cuántos hay "
               "callados",
               not any(map(mismo(elegido), filtrados)) and any(map(mismo(elegido), de_nuevo.descartados))
               and any("Descartados a mano" in x for x in lineas), [x for x in lineas if "Descartad" in x])
        if elegido["regla"] in buscador.AVISOS_MEDICO:
            marcas = buscador.avisos_del_medico(de_nuevo).get(elegido["nota"], [])
            probar("la pista tampoco lo marca con ⚠ (los otros avisos del mismo renglón siguen)",
                   marca in antes and marca not in marcas and len(marcas) == len(antes) - 1, (antes, marcas))
        otro = [dict(guardado[0], huella="0" * 16)]
        probar("si el renglón cambia (otra huella), el aviso vuelve a salir",
               any(map(mismo(elegido), medico.separar_descartados(de_nuevo, todos, otro)[0])))

        def mudado(nombre_nota):
            return [dict(guardado[0], ruta=str(Path(guardado[0]["ruta"]).with_name(nombre_nota)))]

        def callado_desde(nombre_nota):
            return not any(map(mismo(elegido), medico.separar_descartados(de_nuevo, todos, mudado(nombre_nota))[0]))
        probar("si la nota se partió y el renglón pasó a otra de la misma familia (la original, sus «parte N» y sus "
               "historias, como las arma la pasada), el descarte lo sigue callando; en otra nota, no",
               callado_desde("arreglo-login-parte-2.md") and callado_desde("arreglo-login-parte-2-historia-1.md")
               and not callado_desde("arreglo-login-viejo.md") and not callado_desde("otro-arreglo-login.md"))
        medico.guardar_descartados(mudado("arreglo-login-historia-1.md"))
        codigo, mudanza = correr(medico.main_descartados)
        medico.guardar_descartados(guardado)
        probar("y --descartados dice que sigue callado y a qué nota pasó el renglón",
               codigo == 0 and f'callado; el renglón pasó a arreglo-login.md:{elegido["linea"]}' in mudanza, mudanza)
        codigo, dicho = correr(medico.main_descartar_aviso, medico.donde_esta(cerebro, grave))
        probar("solo se descartan los «para revisar»: un aviso concreto (ruta, enlace, commit) no",
               codigo == 2 and "solo se descartan" in dicho and len(medico.cargar_descartados()) == 1, dicho)
        codigo, dicho = correr(medico.main_descartados)
        probar("--descartados lo lista con su motivo y dice que sigue callado",
               codigo == 0 and "callado" in dicho and "ya lo revisé" in dicho, dicho)
        codigo, dicho = correr(medico.main_recuperar_aviso, lugar)
        probar("--recuperar-aviso lo hace volver", codigo == 0 and medico.cargar_descartados() == []
               and any(map(mismo(elegido), medico.revisar(nucleo.desde_disco()))), dicho)
    finally:
        medico.DESCARTADOS.unlink(missing_ok=True)
        medico.DESCARTADOS = original


def revisar_tope_indice(t):
    def con(lineas, largo):
        ruta = t / f"MEMORY-{lineas}-{largo}.md"
        ruta.write_bytes((("x" * (largo - 1)) + "\n").encode() * lineas)
        nodo = {"id": "i", "tipo": "indice", "ruta": str(ruta), "lineas": lineas, "bytes": ruta.stat().st_size}
        falso = types.SimpleNamespace(nodos=[nodo], listados_por_indice={}, indice_roto=[], rotos=[], sin_indice=[],
                                      por_enlace={}, por_id={"i": nodo})
        h = medico.regla_indice(falso)[0]
        return h["tono"], h["linea"], h["texto"]

    hoy = con(99, 152)
    probar("el índice de hoy (99 líneas, 15 KB) entra entero y el médico dice los dos topes",
           hoy[0] == "info" and "99 de 200 líneas y 15,0 de 25 KB" in hoy[2], hoy)
    probar("con pocas líneas pero 20 KB avisa que se acerca al tope (antes solo miraba las líneas)",
           con(100, 200)[0] == "aviso", con(100, 200))
    largas = con(100, 300)
    probar("con 100 líneas de 300 letras (30 KB) es grave y dice desde qué línea Claude no lo ve (la 84: el tope de 25 KB "
           "corta antes que el de 200 líneas)",
           largas[:2] == ("peligro", 84) and "desde la línea 84" in largas[2] and "lo que llegue antes" in largas[2], largas)
    cortas = con(250, 10)
    probar("con 250 líneas cortas sigue cortando en la 201", cortas[:2] == ("peligro", 201), cortas)
    probar("si se pasan los dos topes, manda el que corta primero (125 líneas de 200 bytes llenan justo los 25 KB)",
           con(250, 200)[:2] == ("peligro", 126), con(250, 200))
    sin_meta = con(99, 176)
    nucleo.CONFIG["indice_meta_kb"] = 17
    try:
        pasada = con(99, 176)
        nucleo.CONFIG["indice_meta_kb"] = 18
        debajo = con(99, 176)
    finally:
        del nucleo.CONFIG["indice_meta_kb"]
    probar("con «indice_meta_kb» en config.json el médico avisa al pasar esa meta (17,4 KB con meta de 17) y, debajo, la "
           "nombra; sin la meta, todo igual que antes",
           sin_meta[0] == "info" and sin_meta[2].endswith("Entra entero.") and pasada[0] == "aviso"
           and "Pasó la meta de 17 KB" in pasada[2] and debajo[0] == "info" and "la meta es 18 KB" in debajo[2],
           (sin_meta, pasada, debajo))
    errores = []
    for valor in (40, "17", True, 0):
        try:
            configuracion.armar({"indice_meta_kb": valor}, t)
        except configuracion.ConfigInvalida as error:
            errores.append(str(error))
    probar("«indice_meta_kb» va un número de KB de más de 0 hasta el tope de 25; si no, la configuración dice qué poner",
           len(errores) == 4 and all("indice_meta_kb" in e for e in errores)
           and configuracion.armar({"indice_meta_kb": 17.5}, t)["indice_meta_kb"] == 17.5
           and configuracion.armar({}, t)["indice_meta_kb"] is None, errores)

    def indice_con(renglones, bytes_del_indice=3000):
        nodo = {"id": "i", "tipo": "indice", "ruta": str(t / "MEMORY-largos.md"), "lineas": len(renglones) + 2,
                "bytes": bytes_del_indice, "_cuerpo": "\n".join(renglones), "_desfase": 2}
        falso = types.SimpleNamespace(nodos=[nodo], listados_por_indice={}, indice_roto=[], rotos=[], sin_indice=[],
                                      por_enlace={}, por_id={"i": nodo})
        return medico.regla_indice(falso)

    def entrada(nota, letras):
        principio = f"- [{nota}]({nota}.md) — "
        return principio + "x" * (letras - len(principio))

    varias = "- Historias (archivo): [1](a-historia-1.md) uno; [2](a-historia-2.md) " + "y" * 300
    renglones = ["# Memoria", "", entrada("corta", 120), entrada("justa", medico.LARGO_RENGLON_INDICE),
                 entrada("larga", 300), varias, "Un párrafo suelto, que no es una entrada: " + "z" * 300,
                 entrada("enorme", 471), entrada("pasada", 221), entrada("cuarta", 250)]
    holgado = indice_con(renglones)
    de_largos = [(h["linea"], h["tono"], h["texto"].split(". ")[0]) for h in holgado if h["regla"] == "ganchoLargo"]
    arreglo = next(h["arreglo"] for h in holgado if h["regla"] == "ganchoLargo")
    apretado = indice_con(renglones, 20000)[0]
    probar("un renglón del índice de más de 220 letras que apunta a una sola nota es un aviso (así llega a los chats como "
           "problema nuevo, aunque se haya escrito con un script), con su línea, la nota de ese renglón y cuántas letras "
           "tiene; no el que junta varias notas, ni un párrafo suelto, ni el que llega justo a 220",
           de_largos == [(10, "aviso", "Este renglón del índice, el de enorme.md, tiene 471 letras"),
                         (7, "aviso", "Este renglón del índice, el de larga.md, tiene 300 letras"),
                         (12, "aviso", "Este renglón del índice, el de cuarta.md, tiene 250 letras"),
                         (11, "aviso", "Este renglón del índice, el de pasada.md, tiene 221 letras")]
           and "hasta unas 200 letras" in arreglo and holgado[0]["regla"] == "presupuestoIndice"
           and holgado[0]["tono"] == "info" and "más largos" not in holgado[0]["arreglo"], (de_largos, arreglo))
    import problemas
    nodo = {"id": "i", "ruta": str(t / "MEMORY-largos.md"), "grupo": "memoria", "titulo": "Memoria"}
    nuevos = [p for p in problemas.listar({"nodos": [nodo], "salud": {"medico": holgado}}, {"memoria": ""}, [])
              if p["clave"].startswith("medico-ganchoLargo|")]
    probar("cada renglón largo del índice es un problema nuevo distinto para el aviso a los chats (cada uno nombra su "
           "nota): si ya había uno largo, el que aparece después también se avisa",
           len(nuevos) == 4 and len({p["clave"] for p in nuevos}) == 4 and all(p["linea"] for p in nuevos),
           [p["clave"] for p in nuevos])
    probar("cuando el índice se acerca al tope, el aviso nombra los tres renglones más largos (hay cuatro), del más largo "
           "al más corto", apretado["tono"] == "aviso"
           and apretado["arreglo"].endswith("Los renglones más largos: el 10 (471 letras), el 7 (300 letras), el 12 (250 "
                                            "letras)."), apretado)
    probar("un índice sin renglones largos no suma nada", [h["regla"] for h in indice_con(renglones[:4], 20000)]
           == ["presupuestoIndice"] and "más largos" not in indice_con(renglones[:4], 20000)[0]["arreglo"],
           indice_con(renglones[:4], 20000))

    def nota(nombre, titulo, fuente="memoria", carpeta="memoria", tipo="project"):
        return {"id": f"{carpeta}/{nombre}", "ruta": str(t / carpeta / f"{nombre}.md"), "titulo": titulo, "tipo": tipo,
                "bytes": 20480, "descripcion": "", "_fuente": fuente}

    notas = [nota("visor", "Visor"), nota("visor-parte-2", "Visor, parte 2"), nota("visor-parte-3", "Visor, parte 3"),
             nota("visor-historia-1", "Visor, historia 1 (archivo)"), nota("riego", "Riego"),
             nota("riego-parte-2", "Riego, parte 2"), nota("solo-parte-2", "Suelta, parte 2"),
             nota("solo-parte-3", "Suelta, parte 3"), nota("solo-parte-4", "Suelta, parte 4"),
             nota("doc", "Doc", fuente="docs", carpeta="docs"),
             nota("doc-parte-2", "Doc 2", fuente="docs", carpeta="docs"),
             nota("doc-parte-3", "Doc 3", fuente="docs", carpeta="docs"),
             nota("otra-parte-2", "Otra, parte 2", carpeta="otra"), nota("otra-parte-3", "Otra, parte 3", carpeta="otra"),
             nota("otra", "Otra", carpeta="otra2")]
    falso = types.SimpleNamespace(nodos=notas, fuente_de={n["id"]: {"memoria": n["_fuente"] == "memoria"} for n in notas})
    partes = [(h["nota"], h["tono"], h["linea"]) for h in getattr(medico, "regla_partes", lambda c: [])(falso)]
    texto = next((h["texto"] for h in getattr(medico, "regla_partes", lambda c: [])(falso) if h["nota"] == "memoria/visor"),
                 "")
    probar("una memoria que ya va en tres partes o más queda «para revisar» en su primera nota (lo vigente queda "
           "repartido), aunque falte la primera; no cuentan las historias, ni una de dos partes, ni la documentación, "
           "ni una nota con el mismo nombre en otra carpeta",
           partes == [("memoria/visor", "revisar", 1), ("memoria/solo-parte-2", "revisar", 1)]
           and "ya va en 3 partes (60,0 KB" in texto and "visor-parte-3.md" in texto, (partes, texto))


def revisar_medico(cerebro, con_git):
    seccion("Médico (--salud)")
    revisar_descartes(nucleo.DATOS)
    revisar_tope_indice(nucleo.DATOS)
    hallazgos = medico.revisar(cerebro)
    nombre = {n["id"]: Path(n["ruta"]).name for n in cerebro.nodos}

    def hay(regla, nota, texto=""):
        return any(h["regla"] == regla and nombre.get(h["nota"]) == nota and texto in h["texto"] for h in hallazgos)

    resumen = sorted({(h["regla"], nombre.get(h["nota"])) for h in hallazgos}, key=str)
    probar("la memoria que no está en el índice (suelta.md)", hay("sinIndice", "suelta.md"), resumen)
    probar("la ruta que ya no existe (plan-viejo.md)", hay("rutaVieja", "arreglo-login.md", "plan-viejo.md"), resumen)
    probar("el enlace [[…]] a una nota que no existe (antes solo salía en la página)",
           hay("enlaceRoto", "arreglo-login.md", "nota-que-no-existe"), resumen)
    probar("el ancla corrida: Login.cs:30 cuando ValidarClave está en la 7",
           hay("anclaCorrida", "arreglo-login.md", "la 7"), resumen)
    codigo_real, anclas_reales = medico.CODIGO, getattr(cerebro, "anclas", None)
    medico.CODIGO = []
    try:
        sin_codigo = [h for h in medico.regla_anclas(cerebro) if h["regla"] == "anclas"]
    finally:
        medico.CODIGO, cerebro.anclas = codigo_real, anclas_reales
    probar("sin proyectos con «codigo», el médico dice que las anclas se saltearon por eso (no que el renglón nombra otro "
           "proyecto) y cómo sumarlo", len(sin_codigo) == 1 and "dice dónde está su código" in sin_codigo[0]["texto"]
           and "más de un proyecto" not in sin_codigo[0]["texto"] and "«codigo»" in sin_codigo[0]["arreglo"], sin_codigo)
    probar("la cifra vieja del CLAUDE.md (dice 99 renglones)", hay("hecho", "CLAUDE.md", "99"), resumen)
    probar("las dos memorias que cuentan lo mismo", any(h["regla"] == "memoriasParecidas" for h in hallazgos), resumen)
    if con_git:
        probar("el commit que no existe (de4dbe7)", hay("commitInexistente", "arreglo-login.md", "de4dbe7"), resumen)
        probar("un commit con «no» adelante («no `abc1234`») no se marca como inexistente",
               not hay("commitInexistente", "arreglo-login.md", "abc1234"), resumen)
        solo_propio = medico.regla_commits(cerebro, [str(nucleo.CARPETA)])
        probar("sin proyectos con git en la configuración no marca commits como inexistentes (el repo del propio programa no "
               "cuenta), y dice por qué; con proyectos cargados no pide sumarlos, pide revisar su raíz",
               [h["regla"] for h in solo_propio] == ["commits"] and "Ningún proyecto" in solo_propio[0]["texto"]
               and "«raiz»" in solo_propio[0]["arreglo"], solo_propio)
    else:
        saltear("el commit que no existe: sin git en el PATH, salteado")
    citados = [v for v, _, _ in medico.extraer_commits("El md5 `ab12cd34ef` y la huella `9f8e7d6c5b`. El commit `de4dbe7`"
                                                        " (md5 `ab12cd34ef`) y el hash del commit `ab12cd3`.")]
    probar("una huella de archivo («md5 `…`», «huella `…`») no cuenta como commit; «commit» al lado, sí",
           citados == ["de4dbe7", "ab12cd3"], citados)
    probar("una huella cortada con «…» se reconoce para las otras notas",
           medico.huellas_de("motor servido (md5 `4649a21d…`)") == {"4649a21d"}, medico.huellas_de("md5 `4649a21d…`"))
    en_lista = medico.huellas_de("SHA OK (motor `0a1b2c3d`, lanzador `4e5f6a7b`,\n  y guardia `5a6b7c8d`)")
    probar("en una lista de huellas («SHA OK (motor `…`, lanzador `…`)») cuentan todas, también si la lista sigue en el "
           "renglón de abajo; una oración nueva, la palabra «commit» u otra cosa entre comillas invertidas la cortan",
           en_lista == {"0a1b2c3d", "4e5f6a7b", "5a6b7c8d"}
           and medico.huellas_de("md5 `ab12cd34ef`. Arreglado en `de4dbe7`") == {"ab12cd34ef"}
           and medico.huellas_de("md5 `ab12cd34ef`, commit `de4dbe7`") == {"ab12cd34ef"}
           and medico.huellas_de("md5 `ab12cd34ef` (`sha.txt`), y `de4dbe7`") == {"ab12cd34ef"}, en_lista)
    exe = "- **Exe:** `C:/x/app.exe`, SHA-256\n  `2CCD4440FD5F…` (`sha256.txt` al lado). El de antes `938a4c6f` sigue ahí."
    con_commit = "El md5 cambió; el commit del arreglo es `de4dbe7`"
    otro_item = "- huella `ab12cd34ef` del exe\n- arreglo `de4dbe7`"
    probar("un código suelto con una huella nombrada un poco antes, en el mismo párrafo o ítem, parece una huella; con "
           "«commit» en el medio, en otro ítem o sin nada que hable de huellas, no",
           medico.huella_cerca(exe, exe.index("`938a4c6f`"))
           and not medico.huella_cerca(con_commit, con_commit.index("`de4dbe7`"))
           and not medico.huella_cerca(otro_item, otro_item.index("`de4dbe7`"))
           and not medico.huella_cerca("Se arregló en `de4dbe7`", 14))
    if con_git:
        base = next(n for n in cerebro.nodos if nombre.get(n["id"]) == "arreglo-login.md")
        cuerpo = ("Bajó con SHA OK (motor `0a1b2c3d`, lanzador `4e5f6a7b`). El exe tiene la huella `99aa88bb…`. El de antes "
                  "`77cc66dd` sigue guardado.\n\nSe arregló en `5d4c3b2a`.")
        con_huellas = types.SimpleNamespace(nodos=[dict(base, _cuerpo=cuerpo)])
        marcados = {(h["regla"], h["tono"], v) for h in medico.regla_commits(con_huellas)
                    for v in ("0a1b2c3d", "4e5f6a7b", "77cc66dd", "5d4c3b2a") if v in h["texto"]}
        probar("el médico no marca como commit las huellas de una lista; la que tiene una huella nombrada cerca queda «para "
               "revisar» como huella probable, y un commit que no existe sigue siendo un aviso",
               marcados == {("huellaProbable", "revisar", "77cc66dd"), ("commitInexistente", "aviso", "5d4c3b2a")}, marcados)
    suelta = next(n for n in cerebro.nodos if nombre.get(n["id"]) == "suelta.md")
    carpeta = Path(suelta["ruta"]).parent

    def de_memoria(archivo, descripcion="Lo que se hizo con el login en la primera semana del proyecto"):
        return dict(suelta, id=archivo, ruta=str(carpeta / archivo), titulo="Una nota", descripcion=descripcion)

    indice_falso = {"id": "i", "tipo": "indice", "ruta": str(carpeta / "MEMORY.md"),
                    "_cuerpo": "- Login, historias (archivo): [1](login-viejo.md) y [2](login-marcada.md)\n"
                               "- [Vigente](vigente.md) — lo de antes quedó en el (archivo) de [otra](login-otra.md)\n"}
    notas = [de_memoria("login-viejo.md"), de_memoria("login-marcada.md", "(archivo) Lo de antes del login"),
             de_memoria("vigente.md"), de_memoria("login-otra.md"), de_memoria("login-historia-3.md"),
             de_memoria("la-historia.md"), de_memoria("formato-del-archivo.md")]
    falso = types.SimpleNamespace(nodos=[indice_falso] + notas, ganchos={}, por_id={n["id"]: n for n in notas},
                                  fuente_de={n["id"]: {"memoria": True} for n in [indice_falso] + notas},
                                  por_ruta={nucleo.normalizar(n["ruta"]): n["id"] for n in notas})
    sin_marca = {h["nota"]: h for h in medico.regla_frontmatter(falso) if h["regla"] == "archivoSinMarca"}
    probar("una memoria que parece de archivo y no lo dice queda «para revisar»: la que el índice lista en un renglón "
           "«(archivo)» con varias notas y la que se llama «…-historia-3»; no la que ya lo dice, ni una vigente cuyo renglón "
           "nombra un archivo, ni «la-historia» o «formato-del-archivo»",
           set(sin_marca) == {"login-viejo.md", "login-historia-3.md"}
           and all(h["tono"] == "revisar" for h in sin_marca.values())
           and "MEMORY.md la lista" in sin_marca["login-viejo.md"]["texto"]
           and "por cómo se llama" in sin_marca["login-historia-3.md"]["texto"], sorted(sin_marca))
    codigo = medico.Codigo()

    def datos_de(texto, ext):
        lineas = texto.split("\n")
        return {"texto": texto, "lineas": lineas, "total": len(lineas), "compacto": None, "ext": ext}

    py = datos_de("def larga(x):\n" + "".join(f"    y = x + {i}\n" for i in range(40))
                  + "    return y\n\n\ndef otra():\n    return 1\n", "py")
    js = datos_de("function larga(x) {\n" + "".join(f"  let y = x + {i};\n" for i in range(40))
                  + "  return y;\n}\n\nfunction otra() {\n  return 1;\n}\n", "js")
    adentro_afuera = [codigo.declarada_arriba(d, ("palabra", "larga"), n) for d in (py, js) for n in (35, 46)]
    probar("en Python y JavaScript, una línea adentro de una función larga es de esa función, y afuera no",
           adentro_afuera == [True, False, True, False], adentro_afuera)
    graves = [h for h in hallazgos if h["tono"] == "peligro"]
    probar("ningún hallazgo grave inesperado", not graves, graves)
    texto = "\n".join(medico.informe(cerebro, hallazgos, 30, 0.1))
    probar("el informe sale en texto", texto.startswith("Médico de la memoria:"), texto[:200])
    notas_falsas = {i: {"id": i, "ruta": f"/notas/{i}.md"} for i in ("a", "b")}
    falso = types.SimpleNamespace(nodos=list(notas_falsas.values()), por_id=notas_falsas)

    def suelto(nota, regla, linea):
        return {"nota": nota, "regla": regla, "linea": linea, "tono": "revisar", "texto": f"Cita x.cs:{linea}.",
                "arreglo": "Poner la línea nueva."}

    varios = [suelto("a", "anclaCorrida", n) for n in (3, 9, 12, 20, 31, 40)] + [suelto("b", "anclaCorrida", 5),
                                                                                 suelto("a", "rutaVieja", 7)]
    corto, todo = medico.informe(falso, varios, 30), medico.informe(falso, varios, 0)
    probar("--salud junta en un renglón los del mismo tipo en una misma nota, con cuántos y en qué renglones; --todo "
           "los sigue mostrando uno por uno, como antes",
           sum("REVISAR /notas/a.md — 6 anclas corridas (renglones 3, 9, 12, 20 y 2 más). El primero: Cita x.cs:3" in x
               for x in corto) == 1
           and any(x.startswith("REVISAR /notas/a.md:7 — ") for x in corto) and any("--salud --todo los muestra" in x for x in corto)
           and [x for x in todo if x.startswith("REVISAR")][0] == "REVISAR /notas/a.md:3 — Cita x.cs:3. → Poner la línea nueva."
           and sum(x.startswith("REVISAR") for x in todo) == 8 and not any("--todo los muestra" in x for x in todo),
           (corto, todo))
    filas = medico.filas_juntas(varios, {"b": 10.0})
    listos = {(nucleo.normalizar("/notas/a.md"), 3): 4, (nucleo.normalizar("/notas/a.md"), 9): 5,
              (nucleo.normalizar("/notas/b.md"), 5): 7}
    juntos, solo = medico.texto_fila(falso, filas[1], listos), medico.texto_fila(falso, filas[0], listos)
    probar("primero van las notas que la pista más usa, y cada renglón dice qué arreglos de la pasada de cada noche ya "
           "están listos para aplicar con --aplicar",
           filas[0][0]["nota"] == "b" and "2 tienen el arreglo listo" in juntos and juntos.endswith("--aplicar 4,5 (lo decide "
                                                                                                     f"{medico.QUIEN}).")
           and "Arreglo listo de la pasada de cada noche:" in solo and "--aplicar 7 " in solo, (filas, juntos, solo))
    cortado = medico.informe(falso, varios, 3)
    probar("si no entran todos, el «… y N más» cuenta los hallazgos que quedaron afuera, no los renglones",
           any(x.startswith("… y 2 más: 1 anclaCorrida, 1 rutaVieja.") for x in cortado), cortado)
    con_ambiguas = types.SimpleNamespace(
        ambiguos=[{"de": "a", "mencion": "progreso.md", "candidatos": ["p1", "p2"]},
                  {"de": "a", "mencion": "FICHA.md", "candidatos": ["f1"]}],
        por_id={"a": {"id": "a", "ruta": "/notas/a.md", "_cuerpo": "# A\n\nAnotá en progreso.md.\nY la FICHA.md.\n"},
                "p1": {"ruta": "/uno/progreso.md"}, "p2": {"ruta": "/dos/progreso.md"}, "f1": {"ruta": "/tres/FICHA.md"}})
    ambiguas = medico.regla_ambiguas(con_ambiguas)
    con_ambigua_del_medico = {"nodos": [{"id": "a", "ruta": "/notas/a.md", "grupo": "g"}], "salud": {
        "ambiguos": [{"de": "a", "mencion": "progreso.md", "candidatos": ["p1", "p2"]}],
        "medico": [dict(ambiguas[0], nota="a")]}}
    import problemas
    tipos = [p["clave"].split("|")[0] for p in problemas.listar(con_ambigua_del_medico, {}, [])]
    probar("--salud también muestra las menciones ambiguas como aviso, con su renglón y los candidatos (antes solo salían "
           "en el mapa y en el aviso a los chats: la consola decía 8 avisos y el mapa 22), sin contarlas dos veces en el "
           "aviso a los chats ni en la página",
           [(h["regla"], h["tono"], h["linea"]) for h in ambiguas] == [("ambigua", "aviso", 3), ("ambigua", "aviso", 4)]
           and "/uno/progreso.md" in ambiguas[0]["texto"] and "/dos/progreso.md" in ambiguas[0]["texto"]
           and "2 notas" in ambiguas[0]["texto"] and "otra carpeta (/tres/FICHA.md)" in ambiguas[1]["texto"]
           and tipos == ["ambigua"]
           and "'enlaceRoto', 'ambigua']" in plantilla_entera(CARPETA / "plantilla.html"), (ambiguas, tipos))
    import buscador
    uno = medico.informe(types.SimpleNamespace(nodos=[{}]), [])[0]
    busqueda = buscador.texto_buscar(types.SimpleNamespace(segundos=0.1),
                                     {"ms": 1, "total": 1, "resultados": [{}], "consulta": "x", "terminos": []})[0]
    probar("con una sola, los textos van en singular («1 nota revisada», «1 nota con algo, la mejor»), no «1 notas»",
           "1 nota revisada" in uno and "1 nota con algo, la mejor" in busqueda and "1 notas" not in uno + busqueda,
           (uno, busqueda))
    con_aparte = medico.informe(types.SimpleNamespace(nodos=[{}]), [], avisos_aparte=1)
    probar("el primer renglón de --salud cuenta también los avisos de afuera de las notas (permisos, fallas de los "
           "hooks, notas que no pudo leer), y entonces no dice «No encontré nada» a secas",
           "1 aviso," in con_aparte[0] and con_aparte[1:] == ["En las notas no encontré nada."], con_aparte)


def revisar_resuelto(t):
    seccion("Problemas anotados que un commit posterior pudo resolver")
    repo = t / "resuelto"
    repo.mkdir()
    if not crear_repo(repo):
        saltear("sin git en el PATH, salteado")
        return
    ahora = int(time.time())

    def commit(mensaje, dias, archivo, contenido):
        (repo / archivo).write_text(contenido, encoding="utf-8")
        fecha = f"{ahora - dias * 86400} +0000"
        entorno = dict(os.environ, GIT_AUTHOR_DATE=fecha, GIT_COMMITTER_DATE=fecha)
        for pasos in (["add", "--", archivo],
                      ["-c", "user.name=prueba", "-c", "user.email=prueba@example.invalid", "commit", "-q", "-m", mensaje]):
            subprocess.run(["git", "-C", str(repo)] + pasos, check=True, capture_output=True, timeout=30, env=entorno)

    notas = ("# Notas\n\nEl botón de recompensas no aparece en la ventana del cofre dorado.\n\n"
             "El botón de ordenar no aparece en la ventana de la mochila.\n\n"
             "La brújula no aparece en el mapa del parque.\n- ✅ Arreglado el 1/1.\n")
    commit("Mochila: el boton de ordenar ya aparece en la ventana de la mochila", 4, "mochila.py", "x = 1\n")
    commit("notas", 3, "NOTAS.md", notas)
    commit("Cofre dorado: el boton de recompensas vuelve a aparecer en la ventana del cofre", 2, "cofre.py", "x = 2\n")
    commit("Brujula: vuelve a aparecer en el mapa del parque", 1, "brujula.py", "x = 3\n")
    nodo = {"id": "n1", "ruta": str(repo / "NOTAS.md"), "grupo": "docs", "tipo": "documento", "_cuerpo": notas,
            "_desfase": 0}
    puntaje = medico.PUNTAJE_RESUELTO
    medico.PUNTAJE_RESUELTO = 3.0
    try:
        hallados = medico.regla_resuelto(type("Cerebro", (), {"nodos": [nodo]})(), [str(repo)])
    finally:
        medico.PUNTAJE_RESUELTO = puntaje
    lineas = {h["linea"]: h["texto"] for h in hallados}
    probar("avisa que puede estar resuelto si un commit posterior nombra lo mismo (el cofre dorado), y no si el commit es "
           "anterior a la nota (la mochila) ni si la nota ya dice ✅ (la brújula)",
           list(lineas) == [3] and "Cofre dorado" in lineas[3] and "Puede que ya esté resuelto" in lineas[3], hallados)
    import hook_servir
    sospecha = {"leerPrimero": [{"ruta": str(repo / "NOTAS.md"), "linea": 1, "fin": 5, "seccion": "", "avisos": [
        {"linea": 3, "texto": buscador.primera_oracion(lineas.get(3, ""))},
        {"linea": 4, "texto": "Cita a.cs:1 por «x», que ya no está cerca de esa línea."}]}]}
    servido = hook_servir.armar(sospecha)
    probar("la sospecha del médico («puede que ya esté resuelto») le llega a Claude como sospecha y no con el rótulo "
           "«dato viejo» de lo comprobado (antes la skill decía que el médico lo había comprobado)",
           "⚠ puede que ya esté resuelto en la línea 3: el commit" in servido
           and "⚠ dato viejo en la línea 4: Cita" in servido and "dato viejo en la línea 3" not in servido, servido)
    nota_espacio = {"_cuerpo": "La lista está en (`Web Server\\Program.cs:91`) y en Api Server/Program.cs:12.\n"}
    anclas = [a for grupo in medico.anclas_de_nodo(nota_espacio).values() for a in grupo]
    codigo = medico.Codigo()
    codigo.indices["X"] = {"program.cs": ["D:\\p\\Web Server\\Program.cs", "D:\\p\\Api Server\\Program.cs"]}
    resueltas = [codigo.resolver("X", a["carpeta"], a["nombre"], a["ext"], "", "nota.md", a["antes"]) for a in anclas]
    probar("una ancla con una carpeta con espacios (Web Server\\Program.cs) encuentra su archivo entre varios del mismo "
           "nombre (antes tomaba «Server\\» y la salteaba)",
           resueltas == [["D:\\p\\Web Server\\Program.cs"], ["D:\\p\\Api Server\\Program.cs"]], (anclas, resueltas))
    codigo.indices["MAC"] = {"cartera.py": ["/u/p/app/web/cartera.py", "/u/p/app/models/cartera.py"]}
    con_barras = codigo.resolver("MAC", "app/models", "cartera", "py", "", "/n.md")
    probar("en Mac y Linux, una ancla con carpeta (app/models/cartera.py) encuentra su archivo entre varios del mismo "
           "nombre (antes comparaba la carpeta con barras invertidas contra rutas con «/» y no hallaba ninguno; issue #1)",
           con_barras == ["/u/p/app/models/cartera.py"], con_barras)
    codigo.indices["WEB"] = {"pagina.ts": ["D:\\w\\src\\pagina.ts"]}
    del_servidor = medico.archivos_del_ancla(codigo, "WEB", anclas[0], "", "nota.md", {"WEB": "X"})
    probar("si una nota de un proyecto cita un archivo de otro al que remite (la web al servidor), lo busca también ahí",
           del_servidor == ["D:\\p\\Web Server\\Program.cs"]
           and medico.archivos_del_ancla(codigo, "WEB", anclas[0], "", "nota.md", {}) == [], del_servidor)
    frases = medico.problemas_de({"_cuerpo": "El formulario no comprueba la edad.\nLas tiene al revés.\nLos manda cruzados.\n"
                                             "Las da sin pedir permiso.\nAnda bien.", "_desfase": 0})
    item = medico.problemas_de({"_cuerpo": "- El registro no comprueba la edad:\n  - el de los socios\n  - el de los invitados\n"
                                           "- Otra cosa aparte\n", "_desfase": 0})
    probar("«ya resuelto» reconoce más formas de anotar un problema (no comprueba, al revés, cruzados, sin pedir) y, en "
           "un ítem de lista, mira también sus sub-ítems (antes, un solo renglón: se perdía el arreglo de los registros)",
           [p["linea"] for p in frases] == [1, 2, 3, 4] and len(item) == 1 and "socios" in item[0]["contexto"]
           and "invitados" in item[0]["contexto"] and "Otra cosa" not in item[0]["contexto"], (frases, item))
    marcado = medico.problemas_de({"_cuerpo": "- El bastón venía al revés:\n  - uno\n  - dos\n  - tres\n  - cuatro\n"
                                              "  - ✅ se publicaron\n\n- El escudo:\n  - la hebilla no funciona\n  - a\n"
                                              "  - b\n  - c\n  - d\n  - ✅ el casco quedó bien\n", "_desfase": 0})
    probar("«ya resuelto» ve el «✅» en los sub-ítems de su mismo ítem aunque quede lejos, pero no el de un ítem hermano "
           "(antes avisaba los bastones publicados, con la marca 10 renglones más abajo)",
           [p["linea"] for p in marcado] == [9], marcado)
    propias = medico.palabras_utiles("Los tulipanes y las orquídeas salen cruzados en la ventana del vivero")
    mensaje = ("Vivero: los turnos se reparten bien.\n\nLo de los tulipanes y orquideas cruzados en el paquete queda sin "
               "tocar: no hay prueba de qué espera el cliente.")
    probar("«ya resuelto» no cuenta un commit que dice que justo eso queda sin tocar, ni uno que no toca el código que "
           "nombra el renglón (eran 3 de los 5 falsos)",
           medico.deja_sin_tocar(mensaje, propias)
           and not medico.deja_sin_tocar(mensaje, medico.palabras_utiles("El informe mensual no carga"))
           and medico.codigo_nombrado("ver `Pedidos\\Flags.cs:28-88` y PerfilSocio.cs:40") == {"flags.cs", "perfilsocio.cs"})
    sin_git = t / "no-es-un-repo"
    sin_git.mkdir()
    mudo = medico.regla_resuelto(type("Cerebro", (), {"nodos": [nodo]})(), [str(sin_git)])
    probar("si git no responde, «ya resuelto» lo dice en vez de quedar vacío como si no hubiera nada",
           len(mudo) == 1 and mudo[0]["tono"] == "info" and "git no respondió" in mudo[0]["texto"], mudo)
    renglones = medico.problemas_de({"_cuerpo": "La app no se traba al abrir la ventana.\nEl mapa no se ve en el parque.",
                                     "_desfase": 0})
    probar("«no se traba» describe algo que anda bien; «no se ve», un problema",
           [p["linea"] for p in renglones] == [2], renglones)
    describen = medico.problemas_de({"_cuerpo": "\n\n".join([
        "- Lo que revisa el riego (cada falla deja un aviso en el registro): agua y hora.",
        "- Lee el sensor: más de 1.000 falla y corta.",
        "- Si el pedido del sensor falla al abrir, reintenta solo.",
        "- Los avisos de prueba no llegan al celular, a propósito.",
        "- 2026-09-26: subido el riego nuevo; el reloj venía roto, ahora marca bien.",
        "- El formato del sensor no guarda qué maceta es de cuál.",
        "- Los nombres en el código están cruzados, pero es solo el nombre de la constante.",
        "- **Problema:** si el sensor falla, el riego queda prendido toda la noche.",
        "| R4 | Si falla leer `macetas.txt`, la lista queda vacía hasta reiniciar |",
        "- El riego no anda los domingos.",
        "- La falla del riego sigue: no carga la hora."]), "_desfase": 0})
    probar("«ya resuelto» no toma como problema el renglón que describe cómo es algo: «cada falla», «más de 1.000 falla», "
           "«si … falla», «a propósito», «pero es solo», «venía roto» y «el formato no guarda» (8 de los 12 de la "
           "auditoría 4 eran así); sí el que lo dice con todas las letras, el rotulado como problema de una auditoría y "
           "el que tiene otra queja además de la falla",
           [p["linea"] for p in describen] == [15, 17, 19, 21], [(p["linea"], p["renglon"]) for p in describen])


def revisar_anclas_movidas(t):
    seccion("Anclas sin nombre que el código movió (git diff desde la fecha del renglón)")
    probar("el mapeo de líneas sigue inserciones, borrados y cambios; un renglón editado en el lugar (el mismo número de "
           "renglones antes y después, pocos) sigue en su posición",
           [medico.mapear_linea(n, [[5, 0, 6, 3]]) for n in (4, 6)] == [4, 9]
           and [medico.mapear_linea(n, [[10, 2, 9, 0]]) for n in (12, 10)] == [10, None]
           and [medico.mapear_linea(n, [[3, 1, 3, 2]]) for n in (3, 4)] == [None, 5]
           and [medico.mapear_linea(n, [[5, 0, 6, 3], [20, 1, 23, 1]]) for n in (20, 21)] == [23, 24]
           and medico.mapear_linea(11, [[10, 5, 10, 5]]) is None)
    diff = ("diff --git a/Web Server/x.cs b/Web Server/x.cs\nindex 1..2 100644\n--- a/Web Server/x.cs\t\n"
            "+++ b/Web Server/x.cs\t\n@@ -5,0 +6,3 @@ algo\n+a\n+++ b\n+c\ndiff --git a/n.cs b/n.cs\nnew file mode 100644\n"
            "--- /dev/null\n+++ b/n.cs\n@@ -0,0 +1,2 @@\n+x\n+y\n")
    probar("lee el diff con carpetas con espacios (git les agrega un tabulador) y descarta los archivos nuevos",
           medico.hunks_de_diff(diff) == {"Web Server/x.cs": [[5, 0, 6, 3]], "n.cs": None}, medico.hunks_de_diff(diff))
    if shutil.which("git") is None:
        saltear("sin git en el PATH, salteado")
        return
    repo = t / "repo-movido"
    repo.mkdir()
    base = 1767268800

    def commit(cuando, mensaje, **archivos):
        for nombre, texto in archivos.items():
            (repo / nombre).write_text(texto, encoding="utf-8", newline="\n")
        fecha = f"{cuando} +0000"
        entorno = dict(os.environ, GIT_AUTHOR_DATE=fecha, GIT_COMMITTER_DATE=fecha)
        for pasos in (["add", "-A"], ["-c", "user.name=prueba", "-c", "user.email=prueba@example.invalid", "commit", "-q",
                                      "-m", mensaje]):
            subprocess.run(["git", "-C", str(repo)] + pasos, check=True, capture_output=True, timeout=30, env=entorno)

    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, capture_output=True, timeout=30)
    lineas = "".join(f"linea {i}\n" for i in range(1, 61))
    commit(base, "codigo", **{"Mov.cs": lineas})
    commit(base + 86400, "nota", **{"vieja.md": "Ver `Mov.cs:10`.\n", "editada.md": "Ver `Mov.cs:10`.\n"})
    commit(base + 4 * 86400, "mueve", **{"Mov.cs": "".join(f"nueva {i}\n" for i in range(20)) + lineas})
    commit(base + 5 * 86400, "retoca la nota", **{"editada.md": "Ver `Mov.cs:10`, con una palabra más.\n"})
    commit(base + 8 * 86400, "nota con el arbol sin commitear", **{"apurada.md": "Ver `Mov.cs:50`.\n"})
    commit(base + 8 * 86400 + 7200, "commit del arbol", **{"Mov.cs": "".join(f"otra {i}\n" for i in range(20))
                                                          + "".join(f"nueva {i}\n" for i in range(20)) + lineas})
    candidatas = [{"_nota_ruta": str(repo / "vieja.md"), "linea": 1, "archivo": str(repo / "Mov.cs"), "desde": 10},
                  {"_nota_ruta": str(repo / "apurada.md"), "linea": 1, "archivo": str(repo / "Mov.cs"), "desde": 50}]
    movidas = medico.anclas_movidas(candidatas, [str(repo)], t / "anclas-git-humo.json")
    probar("un ancla sin nombre que el código movió desde que se escribió el renglón sale con su línea nueva; una escrita "
           "mirando cambios sin commitear (commiteados al rato) no se marca, porque las dos cuentas no coinciden",
           [(Path(c["_nota_ruta"]).name, nueva) for c, nueva, _ in movidas] == [("vieja.md", 50)],
           [(Path(c["_nota_ruta"]).name, nueva) for c, nueva, _ in movidas])
    editada = [{"_nota_ruta": str(repo / "editada.md"), "linea": 1, "archivo": str(repo / "Mov.cs"), "desde": 10,
                "cita": "Mov.cs:10"}]
    retocada = medico.anclas_movidas(editada, [str(repo)], t / "anclas-git-humo.json", t / "anclas-fechas-humo.json")
    probar("si el renglón se retocó después de escribir el ancla (la cita ya estaba antes de ese commit), la fecha de git "
           "no es la del ancla: sale sin número (antes proponía la 30, contando solo lo que se movió después del retoque)",
           [(nueva, d["opciones"], d["corrimiento"], d["motivo"]) for _, nueva, d in retocada] == [(None, [], 20, "retocado")],
           [(nueva, d) for _, nueva, d in retocada])
    revisar_anclas_de_la_memoria(t, repo, base, commit)
    muchos = [f"carpeta-con-un-nombre-bastante-largo/archivo-de-codigo-con-nombre-largo-{n:04}.cs" for n in range(600)]
    (repo / "carpeta-con-un-nombre-bastante-largo").mkdir()
    commit(base + 10 * 86400, "muchos", **{nombre: "x\n" for nombre in muchos},
           **{"Señal.cs": lineas, "senal.md": "Ver `Señal.cs:3`.\n"})
    commit(base + 12 * 86400, "cambia la señal", **{"Señal.cs": "arriba\n" + lineas})
    por_archivo = medico.commits_por_archivo(str(repo), muchos) or {}
    historia = medico.historia_anclas([{"_nota_ruta": str(repo / "senal.md"), "linea": 1, "archivo": str(repo / "Señal.cs")}],
                                      [str(repo)])
    probar("la historia de las anclas le pide a git cientos de archivos de una vez (antes pasaba el tope de la línea de "
           "comandos de Windows y no traía ninguno) y encuentra los que tienen tildes o eñes en el nombre",
           len(por_archivo) == 600 and len(historia[0].get("cambiosDespues", [])) == 1,
           (len(por_archivo), historia[0].get("cambiosDespues")))


def revisar_datos_rotos(cerebro, t):
    seccion("Archivos de datos rotos")
    import aprender
    import archivos
    descartados = medico.DESCARTADOS
    antes = descartados.read_bytes() if descartados.exists() else None
    roto = b'{"descartados": [{"regla": "yaResuelto", "ruta": "a.md"'
    try:
        descartados.write_bytes(roto)
        descartar = medico.main_descartar_aviso(str(t / "memoria" / "arreglo-login.md") + ":1")
        recuperar = medico.main_recuperar_aviso(str(t / "memoria" / "arreglo-login.md") + ":1")
        intacto = descartados.read_bytes() == roto
        avisos = [h["texto"] for h in medico.regla_datos_rotos(cerebro)]
    finally:
        if antes is None:
            descartados.unlink(missing_ok=True)
        else:
            descartados.write_bytes(antes)
    probar("un descartados.json roto no se pisa: --descartar-aviso y --recuperar-aviso lo dicen y no escriben, y el médico "
           "avisa que los avisos descartados vuelven a salir (antes se reescribía con lo nuevo y se perdían todos)",
           descartar == 2 and recuperar == 2 and intacto and any("descartados.json" in a for a in avisos), (descartar, recuperar,
                                                                                                         intacto, avisos))
    carpeta = t / "aprendido-roto"
    carpeta.mkdir()
    (carpeta / aprender.ARCHIVO).write_bytes(b'{"version": 3, "pares": {')
    apartado = archivos.apartar_roto(carpeta / aprender.ARCHIVO, 1767268800)
    sano = archivos.apartar_roto(carpeta / "no-existe.json") is None
    consolidada = t / "aprendido-roto-consolidar"
    consolidada.mkdir()
    (consolidada / aprender.ARCHIVO).write_bytes(b"{roto")
    aprender.consolidar(consolidada)
    sano = sano and len(list(consolidada.glob("aprendido.roto-*.json"))) == 1
    en_vivo = nucleo.DATOS / "en-vivo"
    en_vivo.mkdir(exist_ok=True)
    plantado = en_vivo / "aprendido.roto-20260101-000000.json"
    plantado.write_bytes(b"{")
    try:
        avisos = [h["texto"] for h in medico.regla_datos_rotos(cerebro)]
    finally:
        plantado.unlink()
    probar("un aprendido.json roto se aparta con la fecha en el nombre (en vez de pisarlo con uno nuevo, que perdía lo que "
           "se mandó olvidar) y el médico avisa dónde quedó",
           apartado is not None and apartado.name.startswith("aprendido.roto-") and apartado.read_bytes().startswith(b'{"version"')
           and not (carpeta / aprender.ARCHIVO).exists() and sano
           and any("aprendido.json estaba roto" in a and str(plantado) in a for a in avisos), (apartado, avisos))


def revisar_anclas_de_la_memoria(t, repo, base, commit):
    historial = importlib.import_module("historial")
    renglon = "Ver `Mov.cs:10` y `:20`, y `otro/Foo.py:3-4`."
    del_nodo = sorted(a["cita"] for grupo in medico.anclas_de_nodo({"_cuerpo": renglon}).values() for a in grupo)
    probar("las citas que se buscan en el historial se arman igual que las anclas de la nota (también las sueltas)",
           sorted(medico.citas_del_renglon(renglon)) == del_nodo == ["Mov.cs:10", "Mov.cs:20", "otro/Foo.py:3-4"],
           (medico.citas_del_renglon(renglon), del_nodo))
    probar("las partes y las historias de una nota son de la misma familia",
           {medico.familia_de_nota(n) for n in ("nota.md", "nota-parte-2.md", "Nota-historia-3-parte-2.md")} == {"nota"})
    memoria = t / "memoria-anclas"
    memoria.mkdir()
    historial.repo_de(str(memoria)).parent.mkdir(parents=True, exist_ok=True)
    orden = ["git", f"--git-dir={historial.repo_de(str(memoria))}", f"--work-tree={memoria}"]
    subprocess.run(orden + ["init", "-q"], check=True, capture_output=True, timeout=30)

    def version(cuando, **notas):
        for nombre, texto in notas.items():
            (memoria / nombre).write_text(texto, encoding="utf-8", newline="\n")
        fecha = f"{cuando} +0000"
        entorno = dict(os.environ, GIT_AUTHOR_DATE=fecha, GIT_COMMITTER_DATE=fecha)
        for pasos in (["add", "-A"], ["-c", "user.name=prueba", "-c", "user.email=prueba@example.invalid", "commit", "-q",
                                      "-m", "versión"]):
            subprocess.run(orden + pasos, check=True, capture_output=True, timeout=30, env=entorno)

    dia = 86400
    version(base + 2 * dia, **{"otra.md": "Nada.\n", "raiz.md": "Ver `Mov.cs:12`.\n"})
    version(base + 2 * dia + dia // 2, **{"nota.md": "Ver `Mov.cs:10`.\n"})
    version(base + 4 * dia + 3600, **{"apurada-mem.md": "Ver `Mov.cs:15`.\n"})
    version(base + 9 * dia, **{"nota.md": "Arriba.\n", "nota-parte-2.md": "Ver `Mov.cs:10`.\n"})

    def candidata(nombre, desde):
        return {"_nota_ruta": str(memoria / nombre), "linea": 1, "archivo": str(repo / "Mov.cs"), "desde": desde,
                "cita": f"Mov.cs:{desde}"}

    candidatas = [candidata("nota-parte-2.md", 10), candidata("raiz.md", 12), candidata("apurada-mem.md", 15)]
    cache = t / "anclas-memoria-humo.json"
    carpetas = historial.carpetas
    historial.carpetas = lambda: [str(memoria)]
    try:
        movidas = medico.anclas_movidas(candidatas, [str(repo)], t / "anclas-git-memoria.json", cache)
        resultado = sorted((Path(c["_nota_ruta"]).name, nueva, d["opciones"], d["corrimiento"], d["motivo"])
                           for c, nueva, d in movidas)
        probar("en la memoria, el ancla se fecha por la primera versión del historial que la trae (aunque después la "
               "nota se haya partido); si el renglón es más viejo que el historial, o si cerca de esa fecha hubo commits "
               "que dejarían la línea en lugares distintos, sale sin número",
               resultado == [("apurada-mem.md", None, [35, 55], 20, ""), ("nota-parte-2.md", 50, [], 40, ""),
                             ("raiz.md", None, [], 40, "historial")], resultado)
        version(base + 9 * dia + 3600, **{"nueva.md": "Ver `Mov.cs:20`.\n"})
        primeras, raiz = medico.primeras_citas(str(memoria), cache)
        guardado = json.loads(cache.read_text(encoding="utf-8")).get(historial.repo_de(str(memoria)).name, {})
        probar("el índice de citas del historial se guarda y se pone al día solo con las versiones nuevas",
               primeras.get("nueva|Mov.cs:20") == base + 9 * dia + 3600 and primeras.get("nota|Mov.cs:10") == base
               + 2 * dia + dia // 2 and raiz == base + 2 * dia and guardado.get("raiz") == raiz
               and "nueva|Mov.cs:20" in guardado.get("primeras", {}), (primeras, raiz))
        version(base + 9 * dia + 7200, **{"rango.md": "Ver `Mov.cs:45-80` y `Mov.cs:30`.\n"})
        actual = (repo / "Mov.cs").read_text(encoding="utf-8").split("\n")
        commit(base + 9 * dia + 9 * 3600, "rellena", **{"Mov.cs": "\n".join([f"arriba {i}" for i in range(20)] + actual[:60]
                                                                 + [f"metida {i}" for i in range(20)] + actual[60:])})
        rango = dict(candidata("rango.md", 45), hasta=80, cita="Mov.cs:45-80")
        sueltas = medico.anclas_movidas([rango, candidata("rango.md", 30)], [str(repo)], t / "anclas-git-memoria.json",
                                        cache)
        probar("un rango que el código cambió por dentro sale con su largo nuevo (las dos puntas, seguidas por separado); "
               "una línea del mismo archivo que solo se corrió, con su número",
               sorted((c["cita"], nueva, d["largo"]) for c, nueva, d in sueltas)
               == [("Mov.cs:30", 50, 0), ("Mov.cs:45-80", 65, 55)],
               [(c["cita"], nueva, d) for c, nueva, d in sueltas])
    finally:
        historial.carpetas = carpetas
