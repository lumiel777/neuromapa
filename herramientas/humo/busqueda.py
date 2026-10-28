from humo.base import *


def revisar_indice_guardado(t):
    ruta = buscador.ruta_del_indice()
    if ruta.exists():
        ruta.unlink()
    primero = buscador.desde_disco()
    guardado = ruta.exists()
    segundo = buscador.desde_disco()
    nota = t / "memoria" / "arreglo-login.md"
    original = nota.read_bytes()
    try:
        nota.write_bytes(original + b"\npalabraguardadaunica\n")
        tercero = buscador.desde_disco()
    finally:
        nota.write_bytes(original)
    probar("el índice se guarda en en-vivo, se reusa mientras nada cambie y se rehace si cambia una nota",
           guardado and segundo.notas == primero.notas and not primero.buscar("palabraguardadaunica")["resultados"]
           and bool(tercero.buscar("palabraguardadaunica")["resultados"]), (guardado, ruta))
    llamadas = []
    rearmar = buscador.rearmar_de_fondo
    buscador.rearmar_de_fondo = lambda r: llamadas.append(r) or True
    try:
        buscador.desde_disco()
        fresco = buscador.desde_disco(esperar=False)
        sin_cambios = len(llamadas)
        nota.write_bytes(original + b"\notrapalabraunica\n")
        rapido = buscador.desde_disco(esperar=False)
        esperado = buscador.desde_disco()
    finally:
        nota.write_bytes(original)
        buscador.rearmar_de_fondo = rearmar
    probar("sin servidor, si cambió una nota, el hook da la pista con el índice anterior y lo rearma de fondo (antes "
           "esperaba ~2,6 s); la consola espera el nuevo",
           sin_cambios == 0 and len(llamadas) == 1 and isinstance(fresco, buscador.Indice)
           and not rapido.buscar("otrapalabraunica")["resultados"]
           and bool(esperado.buscar("otrapalabraunica")["resultados"]), (sin_cambios, len(llamadas)))
    buscador.desde_disco()
    probar("el índice reusado busca igual que el recién armado",
           segundo.segundos == primero.segundos and segundo.vecinos == primero.vecinos
           and segundo.avisos == primero.avisos and segundo.del_indice == primero.del_indice
           and segundo.buscar("login")["resultados"] == primero.buscar("login")["resultados"]
           and segundo.sobre("fase 0", None)["leerPrimero"] == primero.sobre("fase 0", None)["leerPrimero"])
    import hook_servir
    llamadas = []
    rearmar, espera = buscador.rearmar_de_fondo, getattr(buscador, "ESPERA_INDICE", 6.0)
    limite = getattr(hook_servir, "LIMITE_INDICE", 8.0)
    buscador.rearmar_de_fondo = lambda r: llamadas.append(r) or True
    buscador.ESPERA_INDICE = 0.3
    hook_servir.LIMITE_INDICE = 0.0
    try:
        cabeza, cuerpo = ruta.read_text(encoding="utf-8").split("\n", 1)
        datos = json.loads(cabeza)
        datos["hecho"] -= 2 * 86400
        ruta.write_text(json.dumps(datos) + "\n" + cuerpo, encoding="utf-8")
        nota.write_bytes(original + b"\nviejapalabraunica\n")
        de_dias = buscador.desde_disco(esperar=False)
        con_el_viejo = len(llamadas)
        ruta.unlink()
        comienzo = time.monotonic()
        sin_indice = buscador.desde_disco(esperar=False)
        tardo = time.monotonic() - comienzo
        pista = hook_servir.contexto("¿cómo se arregló la validación de la clave del login?", str(t), servidor=False)
    finally:
        nota.write_bytes(original)
        buscador.rearmar_de_fondo, buscador.ESPERA_INDICE, hook_servir.LIMITE_INDICE = rearmar, espera, limite
    probar("sin servidor, el hook usa el índice guardado aunque tenga días y lo rearma de fondo (antes, pasadas 24 h, lo "
           "armaba entero mientras Claude esperaba)",
           isinstance(de_dias, buscador.Indice) and not de_dias.buscar("viejapalabraunica")["resultados"]
           and con_el_viejo == 1, (type(de_dias).__name__, con_el_viejo))
    marca = ruta.parent / buscador.REARMANDO
    lanzados = []
    lanzar = subprocess.Popen
    subprocess.Popen = lambda *a, **k: lanzados.append(a)
    try:
        con_marca = []
        for adelanto in (0.05, 3600):
            marca.write_text("1\n", encoding="utf-8")
            os.utime(marca, (time.time() + adelanto,) * 2)
            con_marca.append(buscador.rearmar_de_fondo(ruta))
    finally:
        subprocess.Popen = lanzar
        marca.unlink(missing_ok=True)
    probar("una marca de rearmado apenas en el futuro (en Windows, el reloj de Python 3.10 va a saltos de ~15 ms) cuenta "
           "como recién puesta y no rearma dos veces; una de una hora en el futuro (reloj atrasado) no traba",
           con_marca == [False, True] and len(lanzados) == 1, (con_marca, len(lanzados)))
    probar("si no hay índice que sirva (la primera vez o después de actualizar), el hook lo manda a armar de fondo y "
           "sigue sin pista, en vez de armarlo adentro (con memorias grandes chocaba con el tope de 10 s y el índice no "
           "se guardaba nunca)", sin_indice is None and tardo < 3 and pista is None and len(llamadas) >= 2,
           (type(sin_indice).__name__, round(tardo, 2), len(llamadas)))
    buscador.desde_disco()
    marca = t / "el-pickle-corrio"

    class Trampa:
        def __reduce__(self):
            return open, (str(marca), "w")

    viejo = ruta.parent / buscador.INDICE_VIEJO
    viejo.write_bytes(pickle.dumps(Trampa()))
    buscador.desde_disco()
    ruta.unlink()
    buscador.desde_disco()
    probar("un índice viejo en pickle plantado en en-vivo no se carga nunca y se borra al rearmar",
           not marca.exists() and not viejo.exists(), (marca.exists(), viejo.exists()))
    ruta.write_bytes(b"basura")
    probar("un índice guardado roto no rompe nada: se rearma", isinstance(buscador.desde_disco(), buscador.Indice))
    revisar_indice_que_no_se_encoge(t, ruta)


def revisar_indice_que_no_se_encoge(t, ruta):
    memoria, apartada = t / "memoria", t / "memoria-apartada"
    buscador.desde_disco()
    completo = ruta.read_bytes()
    total = json.loads(completo.split(b"\n", 1)[0])["notas"]

    def guardadas():
        return json.loads(ruta.read_bytes().split(b"\n", 1)[0])["notas"]

    def envejecer(segundos):
        cabeza, cuerpo = ruta.read_text(encoding="utf-8").split("\n", 1)
        datos = json.loads(cabeza)
        datos["hecho"] -= segundos
        ruta.write_text(json.dumps(datos) + "\n" + cuerpo, encoding="utf-8")

    memoria.rename(apartada)
    try:
        sin_memoria = buscador.desde_disco()
        intacto = ruta.read_bytes() == completo
        envejecer(buscador.AGUANTE_ENCOGIDO + 60)
        buscador.desde_disco()
        tras_el_aguante = guardadas()
    finally:
        apartada.rename(memoria)
    probar("si la carpeta de la memoria no responde un rato (un junction caído), el índice guardado no pierde sus notas: "
           "esa vez contesta con lo que pudo leer, sin guardarlo; pasada media hora del último índice bueno, se acepta",
           intacto and len(sin_memoria.notas) < total and tras_el_aguante < total, (intacto, total, tras_el_aguante))
    buscador.desde_disco()
    suelta = memoria / "suelta.md"
    original = suelta.read_bytes()
    suelta.unlink()
    try:
        buscador.desde_disco()
        sin_la_borrada = guardadas()
    finally:
        suelta.write_bytes(original)
    buscador.desde_disco()
    probar("una nota borrada de verdad (su carpeta se lee bien) sale del índice guardado enseguida",
           sin_la_borrada == total - 1 and guardadas() == total, (sin_la_borrada, total))


def revisar_archivo_en_la_pista():
    falso = buscador.Indice.__new__(buscador.Indice)
    falso.del_indice = {}
    falso.notas = [{"tipo": "project", "titulo": "Historia 1 (archivo)"}] + [
        {"tipo": "project", "titulo": f"Vigente {i}"} for i in range(1, 5)] + [
        {"tipo": "project", "titulo": "Historia 2 (Archivo)"}]

    def primeras(orden):
        return falso.primeras_para_leer(orden, {n: [] for n in orden}, None)[0]

    probar("una nota de archivo («(archivo)» en el título del índice) entra a «leer primero» solo si está entre las dos "
           "mejores o si sobra lugar, y como mucho una por pista (antes ocupaban hasta la mitad)",
           primeras([0, 1, 2, 3, 4]) == [0, 1, 2, 3] and primeras([1, 2, 0, 5, 3, 4]) == [1, 2, 3, 4]
           and primeras([1, 0, 5]) == [1, 0] and primeras([1, 2, 0]) == [1, 2, 0],
           (primeras([0, 1, 2, 3, 4]), primeras([1, 2, 0, 5, 3, 4]), primeras([1, 0, 5]), primeras([1, 2, 0])))
    try:
        examen = importlib.import_module("examen")
    except ImportError:
        saltear("el examen de la pista: herramientas/examen.py no va en la copia pública, salteado")
    else:
        probar("el examen de la pista reconoce la nota justa aunque el dato se haya mudado a su «-parte-N» (desde que "
               "la memoria se parte sola lo contaba como falla, y el examen se iba poniendo viejo solo); una "
               "«-historia-N», no",
               examen.es_justa("C:/m/loader-propio-parte-2.md", ["loader-propio.md"])
               and examen.es_justa("C:/m/Loader-Propio.md", ["loader-propio.md"])
               and not examen.es_justa("C:/m/loader-propio-historia-1.md", ["loader-propio.md"])
               and not examen.es_justa("C:/m/otro.md", ["loader-propio.md"]))
    elige = buscador.Indice.__new__(buscador.Indice)
    elige.notas = [{"tipo": "project", "ruta": "C:/m/primera.md", "id": "a"},
                   {"tipo": "project", "ruta": "C:/m/archivo.md", "id": "b"}]
    tablas = {0: [(5.0, 10, 10, "débil 1"), (4.0, 20, 20, "débil 2")], 1: [(30.0, 7, 8, "la que calza")]}
    elige.decisiones_de = lambda n, mapa, rareza: tablas[n]
    elegidas = [d["texto"] for d in elige.decisiones({0: 10.0, 1: 5.0}, {}, [])]
    probar("entre las decisiones de las primeras notas gana la que mejor calza con el pedido, aunque su nota no sea la "
           "primera (antes, la primera nota ponía dos y la otra no entraba)", elegidas == ["la que calza", "débil 1"],
           elegidas)
    con_lista = buscador.Indice.__new__(buscador.Indice)
    con_lista.notas = [{"secciones": [0]}]
    con_lista.secciones = [(0, 0, 1, "- El jardinero cobra 10 pesos la hora (eligió Ana)\n- La poda mensual se hace el "
                                      "primer sábado\n- Los premios los decidió Ana\n\n- La poda diaria es a las 9, lo "
                                      "decidió Ana\n")]

    def coinciden(renglon, mapa):
        donde = renglon.lower().find("poda")
        return ({0}, (donde, donde + 4)) if donde >= 0 else (set(), None)

    con_lista.coincidencias = coinciden
    halladas = [d[3] for d in con_lista.decisiones_de(0, {}, [1.0])]
    probar("una «decisión» de la pista es la de ese mismo ítem de la lista y que nombra lo pedido: a «la poda mensual» ya "
           "no le pega «el jardinero cobra… (eligió Ana)» del ítem de arriba (era el 25 % de las decisiones servidas)",
           len(halladas) == 1 and "poda diaria" in halladas[0], halladas)
    comun = {"grupo": "memoria", "ruta": "C:/m/arreglos.md", "titulo": "Arreglos", "tipo": "project"}
    vivo = dict(comun, ruta="C:/m/changelog.md", titulo="Changelog")
    viejo = dict(comun, ruta="C:/m/arreglos-historia-1.md", titulo="Arreglos, historia 1 (archivo)")
    pesos = [buscador.peso_de_tipo(n, {}) for n in (comun, vivo, viejo)]
    probar("un changelog vivo pesa como cualquier nota (guarda lo de hoy) y una nota de archivo pesa un poco menos, no "
           "un tercio (ahí terminan los arreglos de hace semanas cuando un registro se parte)",
           pesos[0] == pesos[1] and 0.8 <= pesos[2] < pesos[0], pesos)
    nodo = {"grupo": "memoria", "ruta": "C:/m/cronica.md", "titulo": "Crónica de agosto (archivo)"}
    probar("una sola regla de «histórico» para el médico y el buscador: fuente histórica, changelog o «(archivo)»",
           nucleo.es_historica(nodo) and nucleo.es_historica(dict(nodo, titulo="x", ruta="C:/m/changelog-2.md"))
           and not nucleo.es_historica(dict(nodo, titulo="Cómo guardar un archivo")))
    sin_marca = dict(nodo, titulo="Crónica, parte 2")
    probar("una nota de archivo se reconoce también por su descripción («(archivo) …» o «ARCHIVO …», como las partes "
           "viejas de un changelog), pero no por nombrar un archivo",
           nucleo.es_archivo(dict(sin_marca, descripcion="(archivo) Crónica del 3/10; lo vigente va en otra"))
           and nucleo.es_archivo(dict(sin_marca, descripcion="ARCHIVO del changelog, WEB-002 a WEB-016"))
           and nucleo.es_archivo(dict(sin_marca, descripcion="(Archived) old notes"))
           and not nucleo.es_archivo(dict(sin_marca, descripcion="Archivo de configuración: qué carpetas leer"))
           and not nucleo.es_archivo(dict(sin_marca, descripcion="Guarda cada cambio en el archivo (archivo) de abajo"))
           and not nucleo.es_archivo(sin_marca))


def revisar_pasajes(cerebro):
    relleno = [f"Párrafo {i} sobre temas varios del proyecto, con palabras comunes que no dicen nada del asunto " * 3
               for i in range(14)]
    larga = {"titulo": "Registro", "nivel": 2, "linea": 10, "texto": "## Registro\n" + "\n\n".join(relleno)}
    partes = buscador.pasajes_de(larga)
    probar("una sección larga se corta en pasajes por párrafos, sin perder ni repetir texto, y cada uno sabe su renglón",
           len(partes) >= 2 and "\n".join(p["texto"] for p in partes) == larga["texto"]
           and all(larga["texto"].split("\n")[p["linea"] - 10] == p["texto"].split("\n")[0] for p in partes)
           and [p["nivel"] for p in partes[:2]] == [2, 2.5] and all(p["titulo"] == "Registro" for p in partes),
           [(p["linea"], len(p["texto"]), p["nivel"]) for p in partes])
    corta = dict(larga, texto="## Registro\nuna línea")
    cerco = dict(larga, texto="## Código\n```\n" + "\n\n".join(relleno) + "\n```\nfin")
    probar("una sección corta queda entera, y un bloque de código no se corta por la mitad",
           buscador.pasajes_de(corta) == [corta] and len(buscador.pasajes_de(cerco)) == 1)
    hecho = "La cerradura violeta del cofre lleva una bisagra torcida que nadie anotó en otro lado."
    cuerpo = "\n\n".join(relleno[:10] + [hecho] + relleno[10:])
    grande = [p * 3 for p in relleno[:6]]
    repetida = "\n\n".join([grande[0], "cerradura violeta bisagra", grande[1], grande[2], "cerradura violeta bisagra",
                            grande[3], grande[4], "cerradura violeta bisagra", grande[5]])
    partes = buscador.pasajes_de({"titulo": "", "nivel": 0, "linea": 0, "texto": repetida})
    con_titulos = "\n".join(f"## Parte {k}\n{p['texto']}" for k, p in enumerate(partes))
    nodos = [{"id": "prueba:larga", "ruta": "C:/m/registro-largo.md", "titulo": "Registro largo", "tipo": "project",
              "grupo": "memoria", "_cuerpo": cuerpo},
             {"id": "prueba:sin", "ruta": "C:/m/sin-titulos.md", "titulo": "Notas sueltas", "tipo": "project",
              "grupo": "memoria", "_cuerpo": repetida},
             {"id": "prueba:con", "ruta": "C:/m/con-titulos.md", "titulo": "Notas sueltas", "tipo": "project",
              "grupo": "memoria", "_cuerpo": con_titulos}]
    copia = copy.copy(cerebro)
    copia.nodos = list(cerebro.nodos) + nodos
    indice = buscador.Indice(copia)
    palabras, _, final, secciones_de, _, _, _ = indice.puntuar("cerradura violeta bisagra")
    numero = {indice.notas[n]["id"]: n for n in range(len(indice.notas))}
    mejor = secciones_de[numero["prueba:larga"]][0][1]
    probar("en una nota larga sin títulos, el dato escondido en el medio puntúa por su pasaje: el mejor es el del dato",
           hecho in indice.secciones[mejor][3] and indice.secciones[mejor][2] > 1, indice.secciones[mejor][2])
    probar("los pasajes de una misma sección no se suman entre sí como si fueran secciones distintas (si no, una nota "
           "larga le gana siempre a una corta y específica)",
           len(partes) >= 2 and final[numero["prueba:sin"]] < 0.9 * final[numero["prueba:con"]],
           (len(partes), final[numero["prueba:sin"]], final[numero["prueba:con"]]))


def revisar_fichas(cerebro, t):
    seccion("Fichas de las notas con Claude (--fichas)")
    import fichas
    ruta = t / "fichas-prueba.json"
    llamadas = []

    def falso(texto, tope):
        numeros = [int(x) for x in re.findall(r"^=== NOTA (\d+):", texto, re.M)]
        llamadas.append((len(numeros), tope))
        return {"gasto": 0.02, "respuesta": {"fichas": [
            {"nota": i, "tema": f"tema {i}", "claves": ["multicliente", "otra"], "preguntas": ["¿qué es?"]}
            for i in numeros] + [{"nota": 999, "tema": "x", "claves": ["y"], "preguntas": []},
                                  {"nota": 1, "tema": "", "claves": [], "preguntas": []}]}}

    try:
        r = fichas.armar(cerebro, 5.0, llamar_a=falso, ruta=ruta, avisar=lambda x: None)
        guardadas = fichas.leer(ruta)
        con_texto = [n for n in cerebro.nodos if (n.get("_cuerpo") or "").strip()]
        probar("--fichas arma una ficha por nota (varias notas por llamada), con la huella de su texto, y descarta las "
               "respuestas que no corresponden a ninguna nota o vienen vacías",
               r["hechas"] == len(con_texto) == len(guardadas["fichas"]) and r["faltan"] == 0
               and all(len(f["huella"]) == 16 for f in guardadas["fichas"].values())
               and sum(n for n, _ in llamadas) == len(con_texto) and len(llamadas) < len(con_texto),
               (r, len(con_texto), llamadas[:3]))
        llamadas.clear()
        r = fichas.armar(cerebro, 5.0, llamar_a=falso, ruta=ruta, avisar=lambda x: None)
        probar("una segunda pasada no llama a Claude si ninguna nota cambió", r["hechas"] == 0 and not llamadas, r)
        nodo = con_texto[0]
        cambiado = copy.copy(cerebro)
        cambiado.nodos = [dict(n, _cuerpo=n["_cuerpo"] + "\nun renglón nuevo") if n is nodo else n for n in cerebro.nodos]
        r = fichas.armar(cambiado, 5.0, llamar_a=falso, ruta=ruta, avisar=lambda x: None)
        probar("si una nota cambia, se rehace solo su ficha", r["hechas"] == 1 and llamadas == [(1, llamadas[0][1])], r)
        llamadas.clear()
        ruta.unlink()
        r = fichas.armar(cerebro, 0.05, llamar_a=falso, ruta=ruta, avisar=lambda x: None)
        probar("sin margen para terminar una tanda, no llama (así el tope no se pasa)", not llamadas and r["hechas"] == 0, r)

        def con_tope(texto, tope):
            llamadas.append(tope)
            return {"tope": True, "gasto": tope}
        por_lote = fichas.NOTAS_POR_LOTE
        fichas.NOTAS_POR_LOTE = 2
        try:
            r = fichas.armar(cerebro, 5.0, llamar_a=con_tope, ruta=ruta, avisar=lambda x: None)
        finally:
            fichas.NOTAS_POR_LOTE = por_lote
        probar("si una tanda llega a su tope de gasto, la pasada se corta ahí y el gasto queda anotado",
               len(llamadas) == 1 and llamadas[0] <= fichas.TOPE_POR_LLAMADA and r["errores"]
               and fichas.leer(ruta)["gastado"] == round(llamadas[0], 4), (r, llamadas))
        ruta.write_text('{"fichas": {"a": 3, "b": {"huella": 5}}, "gastado": "mucho"}', encoding="utf-8")
        probar("un fichas.json con datos raros se lee vacío, sin caerse",
               fichas.leer(ruta) == {"fichas": {}, "gastado": 0.0}, fichas.leer(ruta))
        sin = buscador.Indice(cerebro)
        fichas.guardar({"fichas": {nodo["ruta"]: {"huella": "x" * 16, "tema": "tema", "claves": ["multicliente"],
                                                  "preguntas": []}}, "gastado": 0}, fichas.ARCHIVO)
        con = buscador.Indice(cerebro)
        ruta_de = {Path(x["ruta"]).name for x in con.sobre("multicliente", None)["leerPrimero"]}
        probar("con la ficha, una palabra que la nota no usa (pero su ficha sí) la encuentra, y el corrector no la "
               "cambia por otra parecida",
               Path(nodo["ruta"]).name in ruta_de and not sin.sobre("multicliente", None)["leerPrimero"]
               and con.corregir("multicliente")[0] is None, (ruta_de, sin.corregir("multicliente")))
        probar("la pista decide si el pedido tiene que ver con las notas sin contar las fichas (con ellas, una paella o una "
               "fórmula de Excel recibían pista)", con.sobre("multicliente", None)["relevancia"] == 0,
               con.sobre("multicliente", None)["relevancia"])
        propia = next(m.group(0) for m in re.finditer(r"[^\W\d_]{7,}", nodo["_cuerpo"]))
        fichas.guardar({"fichas": {nodo["ruta"]: {"huella": "x" * 16, "tema": "tema", "claves": [propia, propia, propia],
                                                  "preguntas": []}}, "gastado": 0}, fichas.ARCHIVO)
        _, _, final, _, _, _, sin_ficha = buscador.Indice(cerebro).puntuar(propia)
        numero = next(n for n, x in enumerate(buscador.Indice(cerebro).notas) if x["ruta"] == nodo["ruta"])
        probar("una nota que ya coincide por su texto se ordena igual que sin ficha (sumarla desordenaba los pedidos "
               "reales)", numero in final and final[numero] == sin_ficha[numero], (propia, final.get(numero)))
        pregunta = f"¿dónde quedó {propia}?"
        fichas.guardar({"fichas": {nodo["ruta"]: {"huella": "x" * 16, "tema": "tema", "claves": ["otra"],
                                                  "preguntas": [pregunta]}}, "gastado": 0}, fichas.ARCHIVO)
        indice = buscador.Indice(cerebro)
        _, _, ordenado, _, _, _, decide = indice.puntuar(propia, preguntas=True)
        _, _, sin_ordenar, _, _, _, decide_sin = indice.puntuar(propia)
        probar("las preguntas de la ficha suben en el orden a la nota que ya coincide por su texto; el puntaje con que la "
               "pista decide si aparece no cambia (con las preguntas adentro, 4 pedidos ajenos de 86 recibían pista)",
               ordenado[numero] > sin_ordenar[numero] == decide[numero] and decide == decide_sin
               and set(ordenado) == set(sin_ordenar), (ordenado.get(numero), sin_ordenar.get(numero)))
        en_sobre = next((x["puntaje"] for g in indice.sobre(propia, None)["grupos"] for x in g["notas"]
                         if x["ruta"] == nodo["ruta"]), None)
        en_buscar = next((x["puntaje"] for x in indice.buscar(propia, 500, None)["resultados"]
                          if x["ruta"] == nodo["ruta"]), None)
        probar("--sobre y la pista ordenan con las preguntas; --buscar sigue como estaba",
               en_sobre == round(ordenado[numero], 2) > en_buscar == round(sin_ordenar[numero], 2), (en_sobre, en_buscar))
        r = indice.sobre(propia, None)
        probar("sin cambio de orden entre las notas que se miran, las palabras juntas para decidir son las mismas",
               r["juntasSinPreguntas"] == r["juntas"], (r["juntasSinPreguntas"], r["juntas"]))
        fichas.ARCHIVO.unlink(missing_ok=True)
        for clave, encabezado in (("preguntas", {"preguntas": pregunta}), ("questions", {"metadata": {"questions": pregunta}})):
            escrita = copy.copy(cerebro)
            escrita.nodos = [dict(n, _frontmatter={**n.get("_frontmatter", {}), **encabezado}) if n is nodo else n
                             for n in cerebro.nodos]
            _, _, ordenado, _, _, _, decide = buscador.Indice(escrita).puntuar(propia, preguntas=True)
            probar(f"una línea «{clave}:» en el encabezado de la nota ordena igual que las preguntas de una ficha (sin "
                   "pagar nada: la escribe el chat al guardar)", ordenado[numero] > decide[numero], ordenado.get(numero))
        escrita = copy.copy(cerebro)
        escrita.nodos = [dict(n, _frontmatter={**n.get("_frontmatter", {}), "preguntas": "¿cómo anda el multipregunta?"})
                         if n is nodo else n for n in cerebro.nodos]
        solo_pregunta = buscador.Indice(escrita)
        r = solo_pregunta.sobre("multipregunta", None)
        probar("una palabra que solo está en las preguntas no trae la nota ni da relevancia (ordenan, no suman notas), y "
               "el corrector no la cambia por otra parecida",
               not r["leerPrimero"] and r["relevancia"] == 0 and solo_pregunta.corregir("multipregunta")[0] is None,
               (r["leerPrimero"], r["relevancia"]))
        apagado = nucleo.CONFIG.get("ordenar_con_preguntas", True)
        nucleo.CONFIG["ordenar_con_preguntas"] = False
        try:
            escrita.nodos = [dict(n, _frontmatter={**n.get("_frontmatter", {}), "preguntas": pregunta}) if n is nodo else n
                             for n in cerebro.nodos]
            _, _, ordenado, _, _, _, decide = buscador.Indice(escrita).puntuar(propia, preguntas=True)
        finally:
            nucleo.CONFIG["ordenar_con_preguntas"] = apagado
        probar("con «ordenar_con_preguntas» en false en el config.json, las preguntas no cuentan",
               ordenado[numero] == decide[numero], (ordenado.get(numero), decide.get(numero)))
        dos = copy.copy(cerebro)
        dos.nodos = list(cerebro.nodos) + [
            {"id": "prueba:junta", "ruta": "C:/m/junta.md", "titulo": "Apunte uno", "tipo": "project", "grupo": "memoria",
             "_cuerpo": "El trompolino lleva fresquibilis nuevo.\n"},
            {"id": "prueba:suelta", "ruta": "C:/m/suelta.md", "titulo": "Apunte dos", "tipo": "project", "grupo": "memoria",
             "_cuerpo": "Apunte sobre el trompolino viejo.\n",
             "_frontmatter": {"preguntas": "¿qué fresquibilis lleva el trompolino? ¿trompolino con fresquibilis? ¿y la "
                                           "gargamela?"}}]
        indice_dos = buscador.Indice(dos)
        suelta = next(n for n, x in enumerate(indice_dos.notas) if x["id"] == "prueba:suelta")
        _, _, entera, _, _, _, _ = indice_dos.puntuar("trompolino gargamela", preguntas=True)
        _, _, cortada, _, _, _, _ = indice_dos.puntuar("trompolino gargamel", preguntas=True)
        _, _, ajena, _, _, _, _ = indice_dos.puntuar("trompolino zurubio", preguntas=True)
        probar("las palabras de las preguntas entran al vocabulario: cuentan aunque el pedido las escriba cortadas",
               entera[suelta] > cortada[suelta] > ajena[suelta], (entera.get(suelta), cortada.get(suelta), ajena.get(suelta)))
        revisar, peso = buscador.NOTAS_A_REVISAR, buscador.PESO_PREGUNTAS
        buscador.NOTAS_A_REVISAR, buscador.PESO_PREGUNTAS = 1, 5.0
        try:
            r = indice_dos.sobre("trompolino fresquibilis", None)
            buscador.PESO_PREGUNTAS = 1e-9
            _, _, ordenado, _, _, _, decide = indice_dos.puntuar("trompolino fresquibilis", preguntas=True)
        finally:
            buscador.NOTAS_A_REVISAR, buscador.PESO_PREGUNTAS = revisar, peso
        probar("si las preguntas ponen arriba una nota que no junta las palabras, la pista igual se decide con la que las "
               "juntaba antes de ordenar",
               (r["juntas"], r["juntasSinPreguntas"]) == (1, 2) and r["relevancia"] > 0, (r["juntas"], r["juntasSinPreguntas"]))
        probar("una pregunta que nombra otra palabra del pedido cuenta como que la nota también la cubre (en el banco, sin "
               "esto se encontraba una nota menos)",
               ordenado[suelta] > 1.2 * decide[suelta], (ordenado.get(suelta), decide.get(suelta)))
    finally:
        ruta.unlink(missing_ok=True)
        fichas.ARCHIVO.unlink(missing_ok=True)


def revisar_orden_pista(cerebro, t):
    seccion("Orden de la pista (lo aprendido, CLAUDE.md de otras carpetas y notas de otro proyecto)")
    import aprender
    indice = buscador.Indice(cerebro)
    consulta = "validación clave login renglones"

    def puntajes(memoria):
        r = indice.sobre(consulta, None, memoria=memoria)
        return {Path(n["ruta"]).name: n["puntaje"] for g in r["grupos"] for n in g["notas"]}

    def contexto(**cambios):
        c = aprender.contexto(str(t / "proyecto"))
        c.factor = lambda ruta: 1.0
        c.arriba_del_chat = lambda ruta: True
        c.proyecto = None
        for clave, valor in cambios.items():
            setattr(c, clave, valor)
        return c

    base = puntajes(contexto())
    leida = puntajes(contexto(factor=lambda ruta: 4.0 if ruta.endswith("arreglo-login-bis.md") else 1.0))
    ajena = puntajes(contexto(arriba_del_chat=lambda ruta: False))
    separados = buscador.separados
    buscador.separados = lambda lista: (lambda a, b: True)
    try:
        lejos = puntajes(contexto(proyecto="c:/otro-proyecto"))
    finally:
        buscador.separados = separados
    bis, instrucciones = "arreglo-login-bis.md", "CLAUDE.md"
    probar("lo aprendido sube en la pista las notas que se suelen leer para eso",
           base.get(bis) and leida.get(bis, 0) > 3 * base[bis], (base.get(bis), leida.get(bis)))
    probar("un CLAUDE.md de otra carpeta (que no está arriba de la charla) pierde su ventaja de instrucciones",
           base.get(instrucciones) and ajena.get(instrucciones, 0) < base[instrucciones] * 0.9,
           (base.get(instrucciones), ajena.get(instrucciones)))
    probar("las notas de otro proyecto bajan en la pista (la memoria se comparte entre proyectos)",
           base.get(instrucciones) and lejos.get(instrucciones, 0) < base[instrucciones] * 0.75,
           (base.get(instrucciones), lejos.get(instrucciones)))


def revisar_buscador(cerebro, t):
    seccion("Buscador (--sobre y --buscar)")
    revisar_archivo_en_la_pista()
    revisar_pasajes(cerebro)
    revisar_indice_guardado(t)
    indice = buscador.Indice(cerebro)
    r = indice.sobre("fase 0", None)
    primero = r["leerPrimero"][0] if r["leerPrimero"] else {}
    renglon = ""
    if primero:
        renglon = Path(primero["ruta"]).read_text(encoding="utf-8").split("\n")[primero["linea"] - 1]
    probar("«fase 0» manda primero al plan, a su título", Path(primero.get("ruta", "")).name == "PLAN-DEMO.md"
           and renglon.startswith("### Fase 0"), (primero, renglon))
    if primero:
        plan = primero["ruta"]
        eventos = [{"t": 100, "s": "aaaa1111", "e": "post", "k": "leer", "f": plan, "r": [1, 400, 400]},
                   {"t": 110, "s": "aaaa1111", "e": "post", "k": "leer", "f": "C:/m/larga.md", "r": [1, 5, 100]},
                   {"t": 120, "s": "bbbb2222", "e": "post", "k": "leer", "f": "C:/m/otra.md"}]
        leidas = aprender.leidas_por(eventos, "aaaa1111")
        contexto = aprender.Contexto(None, leidas=leidas)
        tras_compactar = aprender.leidas_por(eventos + [{"t": 130, "s": "aaaa1111", "e": "compacta"}], "aaaa1111")
        probar("lo que el mismo chat ya leyó (entera, o el tramo justo si fue parcial) cuenta como leído; lo de otro chat o "
               "de antes de compactar, no",
               contexto.ya_leido(plan, 40, 60) and contexto.ya_leido("C:/m/larga.md", 2, 4)
               and not contexto.ya_leido("C:/m/larga.md", 50, 60) and not contexto.ya_leido("C:/m/otra.md", 1, 2)
               and not tras_compactar, (leidas, tras_compactar))
        chat = aprender.Contexto(None, cwd="D:/a/b")
        probar("el ×1,6 de las instrucciones vale solo para el CLAUDE.md de la carpeta del chat o de una de arriba (antes "
               "el de otro proyecto subía en todos los chats)",
               chat.arriba_del_chat("D:/a/CLAUDE.md") and chat.arriba_del_chat("D:\\a\\b\\CLAUDE.md")
               and not chat.arriba_del_chat("D:/c/CLAUDE.md") and not chat.arriba_del_chat("D:/a/bc/CLAUDE.md")
               and aprender.Contexto(None).arriba_del_chat("D:/c/CLAUDE.md"))
        sin_lo_leido = indice.sobre("fase 0", None, memoria=contexto)["leerPrimero"]
        probar("la pista no vuelve a recomendar una nota que el chat ya leyó (antes era 13 de 45 lugares)",
               plan not in [p["ruta"] for p in sin_lo_leido], [p["ruta"] for p in sin_lo_leido])
        avisos = [{"t": 100, "s": "aaaa1111", "e": "aviso", "fs": [plan]},
                  {"t": 105, "s": "aaaa1111", "e": "aviso", "na": ["C:/m/aprendida.md"]},
                  {"t": 110, "s": "bbbb2222", "e": "aviso", "fs": ["C:/m/otra.md"]}]
        servidas = aprender.servidas_por(avisos, "aaaa1111")
        tras_compactar = aprender.servidas_por(avisos + [{"t": 120, "s": "aaaa1111", "e": "compacta"}], "aaaa1111")
        import hook_servir
        ya_dada = indice.sobre("fase 0", None, memoria=aprender.Contexto(None, servidas=servidas))
        renglones = hook_servir.armar(ya_dada).splitlines()
        donde = next((i for i, r in enumerate(renglones) if Path(plan).name in r), None)
        probar("si la pista ya le dio una nota a este chat (desde que compactó), la vuelve a nombrar en un renglón, sin "
               "volver a citar su texto (era el 36 % de lo servido); lo de otro chat o de antes de compactar no cuenta",
               servidas == {aprender.clave(plan), aprender.clave("C:/m/aprendida.md")} and not tras_compactar
               and donde is not None and not (donde + 1 < len(renglones) and renglones[donde + 1].startswith("      :")),
               (servidas, renglones))
    r = indice.sobre("ana comentarios validarclave fases", None)
    probar("palabras que ningún renglón junta: avisa y trae notas igual",
           r["aproximado"] is True and bool(r["grupos"]) and bool(r["leerPrimero"]), {k: r[k] for k in ("juntas", "notas")})
    r = indice.sobre("de la que", None)
    probar("una consulta sin palabras no inventa resultados", not r["grupos"] and not r["leerPrimero"])
    r = indice.buscar("login", 8, None)
    primera = Path(r["resultados"][0]["ruta"]).name if r["resultados"] else ""
    probar("«login» trae primero un arreglo del login", primera in ("arreglo-login.md", "arreglo-login-bis.md"), primera)
    r = indice.buscar("valdiacion", 8, None)
    probar("perdona una errata («valdiacion»)", (r.get("corregida") or "").startswith("validacion"), r.get("corregida"))
    indice.corregir = lambda consulta: ("logan", {"login": ["logan"]}, {"login": 1})
    try:
        dudosa = indice.buscar("login", 8, None)
    finally:
        del indice.corregir
    primera = Path(dudosa["resultados"][0]["ruta"]).name if dudosa["resultados"] else ""
    probar("si una palabra bien escrita parece errata de otra más común, busca las dos formas (antes la reemplazaba: "
           "pegaba → pegada, place → palace)", primera in ("arreglo-login.md", "arreglo-login-bis.md"), primera)
    con_avisos = buscador.Indice(cerebro, buscador.avisos_del_medico(cerebro))
    texto = "\n".join(buscador.texto_sobre(con_avisos.sobre("ValidarClave login", None)))
    probar("--sobre avisa el dato viejo que el médico conoce (Login.cs:30 corrida a la 7)",
           "⚠ dato viejo" in texto and "Login.cs:30" in texto and "la 7" in texto, texto[-500:])
    tema = "validación de la clave del login"
    leer = con_avisos.sobre(tema, None)["leerPrimero"]
    if len(leer) >= 2:
        n = con_avisos.numero_de[leer[0]["id"]]
        guardados = con_avisos.avisos.get(n)

        def con_aviso(regla):
            con_avisos.avisos[n] = sorted(set(guardados or []) | {(leer[0]["linea"], "Nombra plan-viejo.md, que ya no existe.",
                                                                   regla)})
            return [p["id"] for p in con_avisos.sobre(tema, None)["leerPrimero"]], \
                con_avisos.sobre(tema, None)["leerPrimero"]
        try:
            bajada, lista = con_aviso("rutaVieja")
            dudosas = [con_aviso(r)[0] for r in ("yaResuelto", "anclaCorrida")]
        finally:
            if guardados is None:
                con_avisos.avisos.pop(n, None)
            else:
                con_avisos.avisos[n] = guardados
        viejas = [p["id"] for p in lista if p.get("viejo")]
        limpias = [p["id"] for p in lista if not p.get("viejo")]
        probar("una nota cuyo tramo tiene un dato viejo comprobado (ruta que ya no existe, cifra o commit) baja detrás de "
               "las limpias en «leer primero», sin desaparecer y con su ⚠ (Kage); por «puede que ya esté resuelto» o una "
               "línea corrida, no",
               leer[0]["id"] in viejas and bajada == limpias + viejas and bajada[0] != leer[0]["id"]
               and lista[bajada.index(leer[0]["id"])]["avisos"] and all(d[0] == leer[0]["id"] for d in dudosas),
               (bajada, viejas, dudosas))
    else:
        saltear("bajar la nota con datos viejos: la prueba necesita dos notas en «leer primero»")
    comprobar = [c["archivo"] for c in con_avisos.sobre("ValidarClave login", None)["comprobar"]]
    probar("«Para comprobar» usa la línea que el médico ya corrigió (Login.cs:7), no la vieja de la nota",
           any(c.startswith("Login.cs:7") for c in comprobar) and not any(c == "Login.cs:30" for c in comprobar),
           comprobar)
    pares = {"forecasts": "forecast", "forecasting": "forecast", "entries": "entry", "retried": "retry", "fixes": "fix",
             "fixed": "fix", "stopping": "stop", "cached": "cach", "cache": "cach", "servidores": "servidor",
             "notas": "nota", "clientes": "client", "status": "status", "class": "class"}
    mal = {p: buscador.forma_base(p) for p, b in pares.items() if buscador.forma_base(p) != b}
    probar("plurales y verbos en inglés y en español van a la misma forma base", not mal, mal)
    probar("las palabras vacías del inglés no cuentan",
           buscador.terminos("How do I roll back a deployed release?") == ["roll", "back", "deployed", "release"],
           buscador.terminos("How do I roll back a deployed release?"))
    probar("«planes» también busca «plan» (antes se perdía la palabra sin la s)", "plan" in indice.expandir("planes"),
           sorted(indice.expandir("planes")))


def revisar_conector(t):
    seccion("Conector MCP para la app de escritorio de Claude (solo lectura)")
    import hook_evento
    nota = t / "memoria" / "perfil-ana.md"
    pedidos = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "sobre", "arguments": {"tema": f"perfil de ana {SECRETO}"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "leer_nota", "arguments": {"ruta": str(CARPETA / "cerebro.py")}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "leer_nota", "arguments": {"ruta": str(nota), "desde": 1, "hasta": 3}}},
        {"jsonrpc": "2.0", "id": 6, "method": "otra/cosa"},
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "avisar_charla", "arguments": {}}},
    ]
    registro = Path(hook_evento.REGISTRO)
    antes = registro.stat().st_size if registro.exists() else 0
    r = subprocess.run([sys.executable, "-I", str(CARPETA / "conector_mcp.py")], capture_output=True, timeout=120,
                       input="".join(json.dumps(p) + "\n" for p in pedidos).encode("utf-8"),
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    respuestas = [json.loads(l) for l in r.stdout.decode("utf-8").splitlines() if l.strip()]
    por_id = {x.get("id"): x for x in respuestas}
    texto = lambda i: ((por_id.get(i) or {}).get("result") or {}).get("content", [{}])[0].get("text", "")
    error = lambda i: ((por_id.get(i) or {}).get("result") or {}).get("isError") is True
    herramientas = [h["name"] for h in ((por_id.get(2) or {}).get("result") or {}).get("tools", [])]
    probar("el conector habla MCP: se presenta, lista sus cuatro herramientas, contesta solo lo que tiene id y dice "
           "«método desconocido» a lo que no conoce",
           len(respuestas) == 7 and (por_id.get(1) or {}).get("result", {}).get("protocolVersion") == "2025-06-18"
           and herramientas == ["sobre", "buscar", "leer_nota", "avisar_charla"]
           and (por_id.get(6) or {}).get("error", {}).get("code") == -32601, (respuestas[:2], r.stderr[-300:]))
    probar("«sobre» devuelve la pista avisando que es texto citado, y «leer_nota» lee solo notas del índice (un .py no)",
           not error(3) and "texto citado" in texto(3) and error(4) and not error(5) and "líneas 1 a 3" in texto(5),
           (texto(3)[:200], texto(4)[:120], texto(5)[:200]))
    nuevo = registro.read_bytes()[antes:] if registro.exists() else b""
    if registro.exists():
        with open(registro, "r+b") as f:
            f.truncate(antes)
    probar("cada uso del conector queda en el registro como «Chat de la app» (origen app, opción y rutas), nunca con lo "
           "que se preguntó", b'"o":"app"' in nuevo and b'"p":"sobre"' in nuevo and b'"k":"leer"' in nuevo
           and SECRETO.encode() not in nuevo, nuevo[-400:])
    del_conector = [json.loads(l) for l in nuevo.decode("utf-8", "replace").splitlines() if '"o":"app"' in l]
    aviso_charla = [e for e in del_conector if e.get("e") == "usuario"]
    otras = {e.get("s") for e in del_conector if e.get("e") != "usuario"}
    probar("«avisar_charla» solo marca que hay una charla nueva (un mensaje, sin texto ni notas) y le da su propia marca, "
           "así dos charlas de la app no se ven como una", not error(7) and "texto citado" not in texto(7)
           and len(aviso_charla) == 1 and set(aviso_charla[0]) == {"t", "s", "e", "h", "k", "o"}
           and aviso_charla[0]["s"] not in otras, (texto(7), aviso_charla, otras))
    antes = registro.stat().st_size if registro.exists() else 0
    with open(registro, "ab") as f:
        for herramienta in ("mcp__neuromapa__avisar_charla", "mcp__neuromapa__sobre"):
            f.write(json.dumps({"t": round(time.time(), 3), "s": "cccc1234", "e": "pre", "h": herramienta, "k": "otro"},
                               separators=(",", ":")).encode("utf-8") + b"\r\n")
    marca = registro.stat().st_size
    lineas = [json.dumps(p) for p in (
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "avisar_charla", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "sobre", "arguments": {"tema": "perfil de ana"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "buscar", "arguments": {"consulta": "ana"}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "sobre", "arguments": "no es un objeto"}})]
    lineas.append('[{"jsonrpc":"2.0","id":6,"method":"ping"}]')
    r = subprocess.run([sys.executable, "-I", str(CARPETA / "conector_mcp.py")], capture_output=True, timeout=120,
                       input="".join(x + "\n" for x in lineas).encode("utf-8"), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    respuestas = [json.loads(l) for l in r.stdout.decode("utf-8").splitlines() if l.strip()]
    por_id = {x.get("id"): x for x in respuestas}
    nuevo = registro.read_bytes()[marca:]
    with open(registro, "r+b") as f:
        f.truncate(antes)
    de_app = [json.loads(l) for l in nuevo.decode("utf-8", "replace").splitlines() if '"o":"app"' in l]
    probar("si la llamada vino de Claude Code (su hook anotó «mcp__neuromapa__…» un instante antes), el conector no la "
           "anota como «Chat de la app»: Code ya anota su charla; lo que no vino de Code, sí",
           not any(e.get("e") == "usuario" or e.get("p") == "sobre" for e in de_app)
           and any(e.get("p") == "buscar" for e in de_app), (de_app, r.stderr[-300:]))
    probar("a unos argumentos que no son un objeto les dice eso (no «no conozco la herramienta»), y a un pedido en lote le "
           "contesta con un error en vez de dejarlo esperando",
           "tienen que ser un objeto" in texto_de_respuesta(por_id.get(5))
           and any(x.get("id") is None and (x.get("error") or {}).get("code") == -32600 for x in respuestas), respuestas[-3:])
    antes = registro.stat().st_size if registro.exists() else 0
    with open(registro, "ab") as f:
        f.write(json.dumps({"t": round(time.time(), 3), "s": "cccc1234", "e": "pre", "h": "mcp__neuromapa__sobre",
                            "k": "otro"}, separators=(",", ":")).encode("utf-8") + b"\r\n")
    marca = registro.stat().st_size
    lineas = [json.dumps(p) for p in (
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "clientInfo": {"name": "codex-mcp-client", "version": "0.1"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "avisar_charla", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "sobre", "arguments": {"tema": "perfil de ana"}}})]
    r = subprocess.run([sys.executable, "-I", str(CARPETA / "conector_mcp.py")], capture_output=True, timeout=120,
                       input="".join(x + "\n" for x in lineas).encode("utf-8"), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    respuestas = [json.loads(l) for l in r.stdout.decode("utf-8").splitlines() if l.strip()]
    instrucciones = ((respuestas[0] if respuestas else {}).get("result") or {}).get("instructions", "")
    nuevo = registro.read_bytes()[marca:]
    with open(registro, "r+b") as f:
        f.truncate(antes)
    de_codex = [json.loads(l) for l in nuevo.decode("utf-8", "replace").splitlines() if l.strip()]
    probar("si el que se conecta es Codex (se presenta así al conectarse), sus usos quedan como «Chat de Codex» (origen "
           "codex, con su propia marca de charla) y no como de la app; una marca de Claude Code de ese momento no los "
           "borra, y las instrucciones le hablan a Codex, no de la app de Claude",
           de_codex and all(e.get("o") == "codex" and str(e.get("s", "")).startswith("codex") for e in de_codex)
           and any(e.get("e") == "usuario" for e in de_codex) and any(e.get("p") == "sobre" for e in de_codex)
           and "avisar_charla" in instrucciones and "modo Chat de la app" not in instrucciones,
           (de_codex, instrucciones[:200], r.stderr[-300:]))
    revisar_conector_actualizado()


def revisar_conector_actualizado():
    import archivos
    import conector_mcp
    pedido = {"name": "sobre", "arguments": {"tema": "perfil de ana"}}
    nuevo, medico_viejo, firma = archivos.json_roto, sys.modules.get("medico"), conector_mcp._codigo["firma"]
    del archivos.json_roto
    sys.modules.pop("medico", None)
    try:
        conector_mcp._codigo["firma"] = None
        mezclado = conector_mcp.llamar(pedido)
        sys.modules.pop("medico", None)
        conector_mcp._codigo["firma"] = (("otro.py", 0, 0),)
        aparte = conector_mcp.llamar(pedido)
    finally:
        archivos.json_roto = nuevo
        if medico_viejo is not None:
            sys.modules["medico"] = medico_viejo
        conector_mcp._codigo["firma"] = firma
    texto = lambda r: (r.get("content") or [{}])[0].get("text", "")
    probar("si el código de Neuromapa cambia mientras el conector MCP sigue abierto (una charla larga mientras se "
           "actualiza), lo nuevo y lo viejo ya no se mezclan: el pedido se contesta en un proceso aparte con todo el código "
           "nuevo (antes daba «cannot import name … from archivos» hasta reiniciar la charla)",
           mezclado.get("isError") and "ImportError" in texto(mezclado)
           and not aparte.get("isError") and "perfil-ana" in texto(aparte), (texto(mezclado)[:200], texto(aparte)[:300]))


def texto_de_respuesta(respuesta):
    return ((respuesta or {}).get("result") or {}).get("content", [{}])[0].get("text", "")


def revisar_parecidas_y_entidades(cerebro, t):
    seccion("Parecidas y entidades")
    ruta = t / "memoria" / "arreglo-login.md"
    documentos = parecidas.documentos_de_memoria(cerebro)
    r = parecidas.comparar(ruta.read_text(encoding="utf-8"), documentos, excluir=[str(ruta)])
    primera = Path(r["resultados"][0]["ruta"]).name if r["resultados"] else ""
    probar("un borrador igual a otra memoria da «repetida», con la otra primero",
           r["veredicto"] == "repetida" and primera == "arreglo-login-bis.md", (r["veredicto"], primera))
    salientes, entrantes = {}, {}
    for de, a in cerebro.fuertes:
        salientes.setdefault(de, set()).add(a)
        entrantes.setdefault(a, set()).add(de)
    probar("las tablas de lo que sale y entra de cada nota coinciden con todas las conexiones (el armado las usa para no "
           "recorrer todas las conexiones por cada nota: con 10.000 notas, de 61 a 22 s)",
           getattr(cerebro, "salientes", None) == salientes and getattr(cerebro, "entrantes", None) == entrantes)
    import random
    azar = random.Random(3)
    vs = [{f"p{azar.randrange(30)}": azar.random() for _ in range(azar.randrange(1, 8))} for _ in range(40)]
    completo = sorted((-round(s, 9), i, j) for i in range(40) for j in range(i + 1, 40)
                      for s in [sum(x * vs[j][p] for p, x in vs[i].items() if p in vs[j])] if s >= 0.01)
    rapido = sorted((-round(s, 9), i, j) for s, i, j in parecidas.cosenos(vs, 0.01))
    probar("las parecidas dan los mismos pares que la cuenta completa (ya no arman una tabla de n × n: con 10.000 notas, "
           "--salud bajó de 1.234 a 799 MB)", rapido == completo and len(completo) > 20, (len(rapido), len(completo)))
    carpeta = t / "memoria-partes"

    def hermanas(a, b):
        return parecidas.hermanas(str(carpeta / a), str(carpeta / b))
    probar("«memorias parecidas» reconoce como partes las que arma Neuromapa al partir («-parte-N», «-historia-N», en "
           "cadena) aunque la original no lleve número; dos notas numeradas de series distintas son una serie, no partes",
           hermanas("visor.md", "visor-parte-3.md") == "partes" and hermanas("visor-parte-2-historia-1.md", "visor-parte-4.md")
           == "partes" and hermanas("riego-historia-2.md", "riego-parte-2.md") == "partes"
           and hermanas("lista-5.md", "riego-historia-1.md") == "plantilla"
           and parecidas.hermanas(str(carpeta / "visor.md"), str(t / "otra" / "visor-parte-3.md")) != "partes",
           [hermanas("visor.md", "visor-parte-3.md"), hermanas("riego-historia-2.md", "riego-parte-2.md")])
    nombres = {"v": "visor.md", "v3": "visor-parte-3.md", "v4": "visor-parte-4.md", "vh": "visor-parte-2-historia-1.md",
               "i": "MEMORY.md", "l": "lista.md", "l4": "lista-4.md", "l5": "lista-5.md", "r": "riego.md",
               "rh": "riego-historia-1.md", "s4": "suelta-4.md", "s5": "suelta-5.md"}
    falso = types.SimpleNamespace(
        por_id={k: {"ruta": str(carpeta / n), "tipo": "indice" if k == "i" else "memoria"} for k, n in nombres.items()},
        por_ruta={nucleo.normalizar(carpeta / n): k for k, n in nombres.items()})
    padres = {"vh": {"i", "v4"}, "v3": {"i", "v4"}, "l4": {"i", "l"}, "l5": {"i", "l", "r"}, "rh": {"i", "r"},
              "s4": {"i"}, "s5": {"i"}}

    def de_quien(a, b):
        return parecidas.de_quien_son_partes(falso, a, b, hermanas(nombres[a], nombres[b]), padres)
    probar("y dice de quién son partes con la nota original, no con otra que enlaza a las dos ni con el índice; de dos "
           "notas de una serie, ninguna",
           [de_quien("vh", "v3"), de_quien("l4", "l5"), de_quien("l5", "rh"), de_quien("s4", "s5")]
           == ["visor.md", "lista.md", "", ""],
           [de_quien("vh", "v3"), de_quien("l4", "l5"), de_quien("l5", "rh"), de_quien("s4", "s5")])
    falso.memorias_parecidas = [{"a": "vh", "b": "v3", "puntaje": 0.3, "comparten": ["porton"], "partesDe": "visor.md",
                                 "hermanas": "partes"},
                                {"a": "l5", "b": "rh", "puntaje": 0.3, "comparten": ["web"], "hermanas": "plantilla"},
                                {"a": "s4", "b": "r", "puntaje": 0.3, "comparten": ["riego"]}]
    dichos = [(h["tono"], h["texto"]) for h in medico.regla_memorias_parecidas(falso)]
    probar("el médico no manda a fusionar dos partes ni dos notas numeradas de una serie: solo las que no tienen nada que "
           "ver por el nombre",
           [d[0] for d in dichos] == ["info", "info", "revisar"] and "visor.md" in dichos[0][1]
           and "llevan número" in dichos[1][1], dichos)
    _, hallados, _ = entidades.quien_nombra(cerebro, "Login.cs")
    notas_ = {Path(cerebro.por_id[x[0]]["ruta"]).name for e in hallados for x in e["notas"] if x[0] in cerebro.por_id}
    probar("«Login.cs» lo nombra arreglo-login.md", "arreglo-login.md" in notas_, notas_)
    original = medico.repos_conocidos
    medico.repos_conocidos = lambda: []
    try:
        lineas, _ = entidades.texto_entidad(cerebro, "f00dfee")
    finally:
        medico.repos_conocidos = original
    probar("sin repositorios git, --entidad de un hash dice que no pudo buscarlo, no que no existe",
           any("no pude buscarlo como commit" in linea for linea in lineas)
           and not any("ningún repo conocido" in linea for linea in lineas), lineas)
