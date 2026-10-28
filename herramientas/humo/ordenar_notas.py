from humo.base import *


def revisar_ordenar(t):
    seccion("Ordenar una nota larga (--partir)")
    ordenar = importlib.import_module("ordenar")
    carpeta = t / "ordenar"
    carpeta.mkdir()
    datos = t / "ordenar-datos"

    def escribir(ruta, texto):
        ruta.write_text(texto, encoding="utf-8", newline="\n")

    def salida_de(*argumentos):
        texto = io.StringIO()
        with contextlib.redirect_stdout(texto):
            codigo = ordenar.main_partir(*argumentos)
        return codigo, texto.getvalue()

    def con_texto(ruta):
        return [r for r in ruta.read_text(encoding="utf-8").split("\n") if r.strip()]

    cuerpo = ("# Bitácora del vivero\n\nLo nuevo va arriba.\n\n## Octubre\n\n- **3/10, bomba:** se cambió el relé.\n"
              "  Segunda línea del mismo ítem.\n\n  Párrafo adentro del ítem.\n- **2/10, sensor:** se calibró.\n\n"
              "```\n# esto es código, no un título\n- esto tampoco es un ítem\n```\n\nCierre de octubre, fuera de la lista.\n\n"
              "---\n\n## Septiembre\n\n- **28/9, riego:** arranca a las 06:15.\n- **27/9, luz:** se cambió el tubo.\n")
    bitacora = carpeta / "bitacora.md"
    indice = carpeta / "MEMORY.md"
    escribir(bitacora, frontmatter("bitacora", "Registro de arreglos del vivero, una entrada por arreglo", "project") + cuerpo)
    escribir(indice, "# Memoria\n\n- [Bitácora del vivero](bitacora.md) — registro de arreglos\n- [Otra](otra.md) — otra cosa\n")
    original = bitacora.read_bytes()
    piezas = ordenar.piezas_de(ordenar.renglones_de(original.decode("utf-8")))
    clases = [p["clase"] for p in piezas]
    probar("una nota se corta en piezas por títulos e ítems: el encabezado no es pieza, lo que sigue a un ítem con sangría "
           "va con él, lo de adentro de un bloque de código no corta, y un párrafo suelto después de la lista es otra pieza",
           clases == ["titulo", "titulo", "item", "item", "parrafo", "regla", "titulo", "item", "item"]
           and "Párrafo adentro" in "".join(ordenar.renglones_de(original.decode("utf-8"))[piezas[2]["desde"]:piezas[2]["hasta"]])
           and piezas[1]["fin_seccion"] == 6 and piezas[6]["fin_seccion"] == 9, clases)
    lista = "\n".join(ordenar.lista_de(bitacora))
    probar("la lista de piezas dice cuánto pesa la nota, si entra en un Read y qué piezas arman cada sección",
           "Entra en un Read" in lista and "9 piezas" in lista and "(sección entera: 7-9)" in lista, lista)
    plan, error = ordenar.planear(bitacora, "7-9", memoria=True, indice=indice)
    probar("el plan no toca nada: las notas y el índice siguen iguales y la nota nueva no existe",
           error is None and bitacora.read_bytes() == original and not (carpeta / "bitacora-historia-1.md").exists()
           and "bitacora-historia-1" in plan["rastro"], error)
    respaldo, dicho, error = ordenar.aplicar(plan, datos)
    nueva = carpeta / "bitacora-historia-1.md"
    cabeza, resto = nucleo.separar_frontmatter(nueva.read_text(encoding="utf-8")) if nueva.exists() else ({}, "")
    antes = [r for r in original.decode("utf-8").split("\n") if r.strip()]
    ahora = [r for r in con_texto(bitacora) if r != plan["rastro"]]
    movido = [r for r in resto.split("Lo vigente está en [[bitacora]].", 1)[-1].split("\n") if r.strip()]
    probar("al confirmar, lo viejo pasa a una nota nueva «…-historia-1» y no se pierde ni se repite un renglón: lo que "
           "queda más lo que se fue es la nota de antes",
           error is None and sorted(ahora + movido) == sorted(antes) and len(movido) == 3
           and "- **28/9, riego:** arranca a las 06:15." in movido and plan["rastro"] in con_texto(bitacora),
           (error, movido, [r for r in antes if r not in ahora + movido]))
    probar("la nota nueva nace como memoria de archivo: mismo tipo, su name es el del archivo, la description empieza con "
           "«(archivo)», el título lo dice y apunta a la vigente",
           nucleo.dato(cabeza, "name") == "bitacora-historia-1" and nucleo.dato(cabeza, "type", True) == "project"
           and nucleo.dato(cabeza, "description").startswith("(archivo) ")
           and nucleo.es_archivo({"titulo": "", "descripcion": nucleo.dato(cabeza, "description")})
           and resto.lstrip("\n").startswith("# Bitácora del vivero, historia 1 (archivo)\n\nLo vigente está en [[bitacora]]."),
           (cabeza, resto[:120]))
    armada = "".join(ordenar.cabeza_para(
        ["---\n", "name: vieja\n", "description: >\n", "  texto largo\n", "  en dos renglones\n", "metadata:\n",
         "  type: feedback\n", "  originSessionId: abc\n", "  modified: 2026-01-01\n", "---\n"], "nueva", 'Dice "hola"', "\n"))
    probar("el encabezado de la nota nueva copia el tipo, cambia el name y la description (aunque la vieja ocupara varios "
           "renglones o la nueva lleve comillas) y no arrastra la fecha ni la sesión de la otra nota",
           armada == '---\nname: nueva\ndescription: "Dice \\"hola\\""\nmetadata:\n  type: feedback\n---\n'
           and nucleo.dato(nucleo.separar_frontmatter(armada + "\nx\n")[0], "description") == 'Dice "hola"', armada)
    renglones_indice = indice.read_text(encoding="utf-8").split("\n")
    probar("el índice gana un renglón para la nota nueva justo debajo del de la vigente, con «(archivo)» en el título",
           renglones_indice[3].startswith("- [Bitácora del vivero, historia 1 (archivo)](bitacora-historia-1.md) — ")
           and renglones_indice[4].startswith("- [Otra]") and "índice" in dicho, renglones_indice)
    copias = sorted(p.name for p in respaldo.iterdir()) if respaldo else []
    probar("antes de cambiar nada guarda una copia de la nota y del índice como estaban",
           copias == ["1-bitacora.md", "2-MEMORY.md"] and (respaldo / "1-bitacora.md").read_bytes() == original, copias)
    plan2, _ = ordenar.planear(bitacora, "3-4", descripcion="Arreglos de octubre", memoria=True, indice=indice)
    viejo = bitacora.read_bytes()
    escribir(bitacora, viejo.decode("utf-8") + "\nUn renglón que agregó otro chat.\n")
    otro, _ = ordenar.planear(bitacora, "3-4", descripcion="Arreglos de octubre", memoria=True, indice=indice)
    _, _, error = ordenar.aplicar(plan2, datos)
    probar("si la nota cambió después de armar el plan, el código de confirmación ya no es el mismo y el plan viejo no se "
           "aplica: no crea la nota nueva ni toca la vigente",
           otro["huella"] != plan2["huella"] and error and "cambió" in error
           and not (carpeta / "bitacora-historia-2.md").exists() and b"otro chat" in bitacora.read_bytes(), error)
    _, _, error = ordenar.aplicar(otro, datos)
    segunda = carpeta / "bitacora-historia-2.md"
    probar("mover ítems sueltos deja un ítem en su lugar que dice a dónde fueron (el renglón en blanco que los separaba de "
           "lo que sigue no se va con ellos), y la description que se pasa queda con «(archivo)» adelante",
           error is None and "- Lo que seguía acá (2 piezas) pasó a [[bitacora-historia-2]]." in con_texto(bitacora)
           and "[[bitacora-historia-2]].\n\n```\n" in bitacora.read_text(encoding="utf-8")
           and 'description: "(archivo) Arreglos de octubre"' in segunda.read_text(encoding="utf-8")
           and "Párrafo adentro del ítem." in segunda.read_text(encoding="utf-8")
           and "Párrafo adentro del ítem." not in bitacora.read_text(encoding="utf-8"), error)
    juntas, dicho = ordenar.cambio_de_indice(
        "- [Bitácora](bitacora.md) — vigente\n- Bitácora, historias (archivo): [1](bitacora-historia-1.md) septiembre; "
        "[2](bitacora-historia-2.md) octubre\n", "bitacora.md", "bitacora-historia-3.md", "Bitácora, historia 3 (archivo)",
        "noviembre", 3)
    probar("si el índice ya junta las partes viejas en un renglón «(archivo)», la nueva se suma a ese renglón",
           juntas is not None and juntas.split("\n")[1].endswith("octubre; [3](bitacora-historia-3.md) noviembre")
           and juntas.count("\n") == 2, (juntas, dicho))
    plano = carpeta / "plano.md"
    acumulado = carpeta / "acumulado.md"
    escribir(plano, "# Pendientes\n\n- uno\n- dos\n- tres\n- cuatro\n")
    acumulado.write_bytes(b"\xef\xbb\xbf# Acumulado\r\n\r\nLo de antes.\r\n")
    plan3, error = ordenar.planear(plano, "2,4", destino="acumulado", titulo="Agregado")
    _, _, error = ordenar.aplicar(plan3, datos) if plan3 else (None, None, error)
    junto = acumulado.read_bytes()
    probar("pasar piezas salteadas a una nota que ya existe las agrega al final, en orden, bajo el título pedido, y respeta "
           "el BOM y los finales de renglón de esa nota; en una nota común el rastro es un enlace de Markdown",
           error is None and junto.startswith(b"\xef\xbb\xbf") and junto.count(b"\n") == junto.count(b"\r\n")
           and junto.decode("utf-8").replace("\r\n", "\n").endswith("Lo de antes.\n\n## Agregado\n\n- uno\n\n- tres\n")
           and plano.read_text(encoding="utf-8") == "# Pendientes\n\n- Lo que seguía acá (2 piezas) pasó a "
           "[acumulado.md](acumulado.md).\n- dos\n- cuatro\n", (error, junto, plano.read_text(encoding="utf-8")))
    intacto = plano.read_bytes()
    plan4, _ = ordenar.planear(plano, "3")
    real = ordenar.escribir_atomico

    def falla_en_la_vigente(ruta, contenido):
        if Path(ruta).name == "plano.md":
            raise PermissionError("plano.md sigue tomado por otro programa")
        return real(ruta, contenido)

    ordenar.escribir_atomico = falla_en_la_vigente
    try:
        _, _, error = ordenar.aplicar(plan4, datos)
    finally:
        ordenar.escribir_atomico = real
    probar("si falla a mitad de camino, deshace lo que alcanzó a escribir: la nota nueva no queda y la vigente sigue igual",
           error and "como estaba" in error and not (carpeta / "plano-historia-1.md").exists()
           and plano.read_bytes() == intacto, error)

    def corte_en_la_vigente(ruta, contenido):
        if Path(ruta).name == "plano.md":
            raise KeyboardInterrupt
        return real(ruta, contenido)

    ordenar.escribir_atomico = corte_en_la_vigente
    cortado = False
    try:
        ordenar.aplicar(plan4, datos)
    except KeyboardInterrupt:
        cortado = True
    finally:
        ordenar.escribir_atomico = real
    probar("un Ctrl+C a mitad de camino también deshace lo escrito, y después corta (antes la nota nueva quedaba escrita "
           "y la vigente sin recortar)", cortado and not (carpeta / "plano-historia-1.md").exists()
           and plano.read_bytes() == intacto, cortado)
    plan5, _ = ordenar.planear(bitacora, "5", memoria=True, indice=indice)
    vigente = bitacora.read_bytes()

    def otro_chat_toca_el_indice(ruta, contenido):
        real(ruta, contenido)
        if Path(ruta).name == "bitacora.md":
            with open(indice, "a", encoding="utf-8", newline="\n") as f:
                f.write("- [Nueva](nueva.md) — la anotó otro chat\n")

    ordenar.escribir_atomico = otro_chat_toca_el_indice
    try:
        _, _, error = ordenar.aplicar(plan5, datos)
    finally:
        ordenar.escribir_atomico = real
    probar("si otro chat cambia el índice justo en el medio, no lo pisa: deshace las dos notas y el renglón del otro chat "
           "queda",
           error and "índice" in error and not (carpeta / "bitacora-historia-3.md").exists()
           and bitacora.read_bytes() == vigente and "la anotó otro chat" in indice.read_text(encoding="utf-8")
           and "historia-3" not in indice.read_text(encoding="utf-8"), error)
    latin = carpeta / "latin.md"
    latin.write_bytes("# Años\n\n- uno\n- dos\n".encode("latin-1"))
    rechazos = [ordenar.planear(plano, "1-4")[1], ordenar.planear(plano, "9")[1], ordenar.planear(plano, "dos")[1],
                ordenar.planear(carpeta / ".env.md", "1")[1], ordenar.planear(latin, "2")[1],
                ordenar.planear(plano, "2", destino="plano.md")[1]]
    probar("no se lleva la nota entera, ni piezas que no existen, ni toca un archivo con nombre de clave, uno que no está "
           "en UTF-8 o un destino que es la misma nota",
           all(rechazos) and "entera" in rechazos[0] and "no hay pieza" in rechazos[1] and "clave" in rechazos[3]
           and "UTF-8" in rechazos[4] and "misma" in rechazos[5], rechazos)
    codigo, texto = salida_de(str(plano))
    probar("--partir con una nota sola lista las piezas y no cambia nada",
           codigo == 0 and "4 piezas" in texto and "--mover" in texto and plano.read_bytes() == intacto, texto)
    codigo, texto = salida_de(str(plano), "3", "", "", "", "")
    clave = re.search(r"--confirmar ([0-9a-f]{8})", texto)
    probar("con --mover muestra el plan (qué se va, a dónde, cómo queda cada nota) y el código para confirmarlo, todavía "
           "sin cambiar nada",
           codigo == 0 and clave and "todavía no cambié nada" in texto and "plano-historia-1.md, nueva" in texto
           and plano.read_bytes() == intacto, texto)
    codigo, texto = salida_de(str(plano), "3", "", "", "", "00000000")
    probar("con un código de confirmación que no es el del plan no hace nada y lo dice",
           codigo == 2 and "no es la de este plan" in texto and plano.read_bytes() == intacto, texto)
    codigo, texto = salida_de(str(plano), "3", "", "", "", clave.group(1) if clave else "")
    guardados = sorted((nucleo.DATOS / ordenar.RESPALDOS).glob("*-partir*/1-plano.md"))
    probar("con el código del plan hace el cambio, deja la copia de antes en la carpeta de datos y sugiere correr el médico",
           codigo == 0 and "Hecho" in texto and (carpeta / "plano-historia-1.md").exists()
           and len(guardados) == 1 and guardados[0].read_bytes() == intacto and "--salud" in texto, texto)
    contexto, error = ordenar.resolver("perfil-ana")
    _, es_indice = ordenar.resolver(str(t / "memoria" / "MEMORY.md"))
    probar("una memoria se puede pedir por su nombre: sabe que es memoria y cuál es su índice; el índice mismo no se parte",
           error is None and contexto["memoria"] and os.path.samefile(contexto["indice"], t / "memoria" / "MEMORY.md")
           and es_indice and "índice" in es_indice, (error, es_indice))


def revisar_bytes_al_reescribir(t):
    seccion("Renombrar y partir respetan el BOM y los finales de renglón de cada nota")
    bom = b"\xef\xbb\xbf"
    mundo = t / "bytes"
    memoria = mundo / "memoria"
    memoria.mkdir(parents=True)
    (mundo / "en-vivo").mkdir()

    def crlf(texto):
        return texto.replace("\n", "\r\n").encode("utf-8")

    archivos = {
        "MEMORY.md": bom + crlf("# Memoria\n\n- [Riego](riego.md) — el riego del vivero, día por día\n"
                                "- [Poda](poda.md) — la poda de los limoneros\n- [Otra](otra.md) — otra cosa\n"),
        "riego.md": bom + crlf(frontmatter("riego", "El riego del vivero, día por día", "project") + "# Riego\n\n"
                               + "Un día por sección.\n\n" + "".join(f"## Día {k}\n\n- regado {k}\n\n" for k in range(1, 7))),
        "poda.md": crlf(frontmatter("poda", "La poda de los limoneros", "project") + "# Poda\n\nVer [[riego]] y riego.md.\n"),
        "otra.md": (frontmatter("otra", "Otra cosa del vivero", "project") + "# Otra\n\nVer [[riego]].\n").encode("utf-8"),
    }
    for nombre, datos in archivos.items():
        (memoria / nombre).write_bytes(datos)
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]],
         "memoria": True, "foco": True}]}, ensure_ascii=False), encoding="utf-8")

    def forma(datos):
        fines = "crlf" if datos.count(b"\r\n") == datos.count(b"\n") > 0 else "lf" if b"\r\n" not in datos else "mezcla"
        return datos.startswith(bom), fines

    def confirmar(*orden):
        clave = re.search(r"--confirmar ([0-9a-f]{8})", cerebro_en(mundo, *orden)[1])
        return cerebro_en(mundo, *orden, "--confirmar", clave.group(1) if clave else "")[0]

    def respaldos_iguales(paso, originales):
        copias = [p for p in (mundo / "respaldos").glob(f"*-{paso}/*") if p.is_file()]
        return bool(copias) and all(p.read_bytes() == originales.get(p.name.split("-", 1)[1]) for p in copias)

    antes = {p.name: p.read_bytes() for p in memoria.iterdir()}
    renombrada = confirmar("--renombrar", "riego", "regar")
    tras_renombrar = {p.name: p.read_bytes() for p in memoria.iterdir()}
    partida = confirmar("--partir", "regar.md", "--mover", "3-5")
    despues = {p.name: p.read_bytes() for p in memoria.iterdir()}
    formas = {nombre: forma(datos) for nombre, datos in despues.items()}
    esperadas = {"MEMORY.md": (True, "crlf"), "regar.md": (True, "crlf"), "regar-historia-1.md": (True, "crlf"),
                 "poda.md": (False, "crlf"), "otra.md": (False, "lf")}
    probar("--renombrar y --partir dejan cada nota como estaba: con BOM la que tenía, CRLF la que era CRLF y LF la que "
           "era LF, y la nota nueva igual que la que se partió; las copias de respaldo son los bytes de antes, uno por uno",
           renombrada == 0 and partida == 0 and formas == esperadas and respaldos_iguales("renombrar", antes)
           and respaldos_iguales("partir", tras_renombrar), formas)


def revisar_renombrar(t):
    seccion("Cambiarle el nombre a una nota (--renombrar)")
    ordenar = importlib.import_module("ordenar")
    mundo = t / "renombrar"
    memoria, docs = mundo / "memoria", mundo / "docs"
    memoria.mkdir(parents=True)
    docs.mkdir()
    (mundo / "en-vivo").mkdir()

    def escribir(ruta, texto):
        ruta.write_text(texto, encoding="utf-8", newline="\n")

    def leer(ruta):
        return ruta.read_text(encoding="utf-8")

    escribir(memoria / "MEMORY.md", "# Memoria\n\n- [Registro de riego](registro-riego.md) — una entrada por arreglo del riego\n"
             "- [Bomba](bomba-nueva.md) — la bomba que se cambió en marzo\n"
             "- [Registro de riego, historia 1 (archivo)](registro-riego-historia-1.md) — lo viejo del registro\n")
    escribir(memoria / "registro-riego.md",
             frontmatter("registro-riego", "Registro de los arreglos del riego del vivero, una entrada por arreglo", "project")
             + "# Registro de riego\n\nLo viejo está en [[registro-riego-historia-1]]. Este registro (registro-riego) se llena "
               "solo. La bomba, en [[bomba-nueva]].\n")
    cuerpo_bomba = ("# Bomba\n\nVer [[{n}]] y [[{n}|el registro]], también [[{n}#Marzo]].\n"
                    "El detalle está en [el registro]({n}.md#marzo) y en [otra forma](<./{n}.md>).\n"
                    "Anotado en `{n}.md:12` y en {n} a secas.\n"
                    "No tocar: registro-riego-historia-1, [[registro-riego-historia-1]], otro-registro-riego.md ni "
                    "carpeta-ajena/registro-riego.md.\n")
    cabeza_bomba = frontmatter("bomba-nueva", "La bomba nueva del vivero: cuándo se cambió y qué caudal da", "project")
    escribir(memoria / "bomba-nueva.md", cabeza_bomba + cuerpo_bomba.replace("{n}", "registro-riego"))
    escribir(memoria / "registro-riego-historia-1.md",
             frontmatter("registro-riego-historia-1", "(archivo) Lo viejo del riego; lo vigente está en registro-riego", "project")
             + "# Registro de riego, historia 1 (archivo)\n\nLo vigente está en [[registro-riego]].\n")
    plan_docs = "# Plan del vivero\n\nLa memoria `registro-riego.md` tiene los arreglos; ver ../memoria/registro-riego.md.\n"
    escribir(docs / "PLAN.md", plan_docs)
    escribir(mundo / "config.json", json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]], "memoria": True,
         "foco": True},
        {"id": "docs", "nombre": "Docs", "color": "#888888", "raices": [[str(docs), False, ""]], "foco": True}]},
        ensure_ascii=False))
    vieja, nueva = memoria / "registro-riego.md", memoria / "riego-registro.md"
    escribir(mundo / "descartados.json", json.dumps({"descartados": [
        {"regla": "yaResuelto", "ruta": str(vieja), "linea": 9, "huella": "0000000000000000", "motivo": str(vieja),
         "fecha": "2026-01-01"}]}, ensure_ascii=False, indent=1))
    escribir(mundo / "sugerencias.json", json.dumps([
        {"de": str(vieja).replace("\\", "/"), "a": str(memoria / "bomba-nueva.md"), "clase": "sugerida",
         "motivo": "van juntas"}], ensure_ascii=False, indent=1))

    def grafo(nombre):
        codigo, salida = cerebro_en(mundo, "--salida", str(mundo / f"{nombre}.html"), "--json", str(mundo / f"{nombre}.json"))
        if codigo:
            return codigo, salida
        datos = json.loads(leer(mundo / f"{nombre}.json"))
        de_quien = {n["id"]: Path(n["ruta"]).name.replace("riego-registro.md", "registro-riego.md") for n in datos["nodos"]}
        return 0, sorted((a["clase"], de_quien[a["de"]], de_quien[a["a"]]) for a in datos["aristas"]
                         if a["clase"] in ("wiki", "indice", "enlace", "mencion") and de_quien[a["de"]] != "PLAN.md")

    antes = {p: p.read_bytes() for p in list(memoria.iterdir()) + [docs / "PLAN.md", mundo / "descartados.json",
                                                                   mundo / "sugerencias.json"]}
    _, grafo_antes = grafo("antes")
    codigo, plan = cerebro_en(mundo, "--renombrar", "registro-riego", "riego-registro")
    clave = re.search(r"--confirmar ([0-9a-f]{8})", plan)
    probar("--renombrar muestra el plan sin tocar nada: cuántas referencias cambia y en qué notas, los datos propios que "
           "nombran la nota y lo que queda afuera de la memoria, con su renglón",
           codigo == 0 and clave and all(p.read_bytes() == b for p, b in antes.items()) and not nueva.exists()
           and "todavía no cambié nada" in plan and "bomba-nueva.md (7)" in plan and "MEMORY.md (1)" in plan
           and "descartados.json (1)" in plan and "sugerencias.json (1)" in plan
           and "No toco 2 referencias fuera de la memoria" in plan and "PLAN.md:3" in plan, plan)
    codigo, salida = cerebro_en(mundo, "--renombrar", "registro-riego", "riego-registro", "--confirmar", "00000000")
    probar("con un código que no es el del plan no cambia nada",
           codigo == 2 and all(p.read_bytes() == b for p, b in antes.items()) and not nueva.exists(), salida)
    codigo, salida = cerebro_en(mundo, "--renombrar", "registro-riego", "riego-registro", "--confirmar",
                                clave.group(1) if clave else "")
    propia = leer(nueva) if nueva.exists() else ""
    probar("con el código del plan el archivo cambia de nombre, su encabezado dice el nombre nuevo y lo que la nota dice de "
           "sí misma también; sus enlaces a otras notas quedan como estaban",
           codigo == 0 and "Hecho" in salida and not vieja.exists() and "\nname: riego-registro\n" in propia
           and "Este registro (riego-registro) se llena solo" in propia and "[[registro-riego-historia-1]]" in propia, salida)
    probar("en las otras memorias cambia cada forma de nombrarla ([[…]] con alias o sección, enlaces de Markdown con ancla "
           "o entre < >, el nombre del archivo con su renglón y el nombre a secas) y nada más: ni la nota de historia, ni un "
           "archivo que solo se le parece, ni uno igual que está en otra carpeta",
           leer(memoria / "bomba-nueva.md") == cabeza_bomba + cuerpo_bomba.replace("{n}", "riego-registro"),
           leer(memoria / "bomba-nueva.md"))
    historia = leer(memoria / "registro-riego-historia-1.md")
    probar("la nota de historia conserva su nombre y pasa a apuntar a la vigente con el nombre nuevo, también en su "
           "description; el índice cambia solo el enlace de la nota",
           "name: registro-riego-historia-1\n" in historia and "lo vigente está en riego-registro\n" in historia
           and "Lo vigente está en [[riego-registro]]." in historia
           and "- [Registro de riego](riego-registro.md) — una entrada" in leer(memoria / "MEMORY.md")
           and "(registro-riego-historia-1.md) — lo viejo" in leer(memoria / "MEMORY.md"), historia)
    descartes = json.loads(leer(mundo / "descartados.json"))["descartados"][0]
    sugerida = json.loads(leer(mundo / "sugerencias.json"))[0]
    probar("los datos propios que guardaban la ruta de la nota (avisos descartados, conexiones sugeridas) la siguen: cambia "
           "solo ese campo, con las barras que tenía, y no un texto que la nombre",
           descartes["ruta"] == str(nueva) and descartes["motivo"] == str(vieja)
           and sugerida["de"] == str(nueva).replace("\\", "/") and sugerida["a"] == str(memoria / "bomba-nueva.md"),
           (descartes, sugerida))
    copias = sorted(p.name.split("-", 1)[1] for p in (mundo / "respaldos").glob("*-renombrar/*")) \
        if (mundo / "respaldos").is_dir() else []
    probar("lo de afuera de la memoria no se toca, y de todo lo que cambió queda una copia de antes",
           (docs / "PLAN.md").read_bytes() == plan_docs.encode("utf-8")
           and copias == sorted(["MEMORY.md", "registro-riego.md", "bomba-nueva.md", "registro-riego-historia-1.md",
                                 "descartados.json", "sugerencias.json"]), copias)
    codigo, grafo_despues = grafo("despues")
    _, salud = cerebro_en(mundo, "--salud", "--todo")
    probar("después del cambio el mapa une las memorias igual que antes (los mismos enlaces, uno por uno) y el médico no "
           "encuentra ningún enlace roto en la memoria",
           codigo == 0 and grafo_antes and grafo_despues == grafo_antes
           and not [r for r in salud.splitlines() if str(memoria) in r.split(" — ")[0]
                    and ("no lleva a ninguna nota" in r or "que no existe" in r)], (grafo_antes, grafo_despues, salud))
    rechazos = [cerebro_en(mundo, "--renombrar", "riego-registro", nombre)[1]
                for nombre in ("bomba-nueva", "sub/carpeta", "riego-registro", ".oculta")]
    rechazos.append(cerebro_en(mundo, "--renombrar", str(memoria / "MEMORY.md"), "indice")[1])
    probar("no acepta un nombre que ya usa otra nota, uno con carpeta, el mismo nombre, uno que empieza con punto, ni "
           "cambiarle el nombre al índice",
           "ya hay una nota" in rechazos[0] and "sin carpeta" in rechazos[1] and "ya se llama así" in rechazos[2]
           and "sin carpeta" in rechazos[3] and "índice" in rechazos[4] and nueva.exists(), rechazos)
    intacto = {p: p.read_bytes() for p in memoria.iterdir()}
    tomado = correr(["-c", "import sys, os; sys.path.insert(0, sys.argv[1]); import ordenar, cerebro\n"
                           "real = os.remove\n"
                           "def falla(ruta):\n"
                           "    if os.path.basename(str(ruta)) == 'riego-registro.md':\n"
                           "        raise PermissionError('tomado por otro programa')\n"
                           "    return real(ruta)\n"
                           "contexto, error = ordenar.resolver('riego-registro')\n"
                           "plan, error = ordenar.planear_nombre(contexto, 'otro-nombre', cerebro.DATOS)\n"
                           "ordenar.os.remove = falla\n"
                           "print(ordenar.aplicar_nombre(plan, cerebro.DATOS)[1])\n", str(CARPETA)],
                    CEREBRO_CONFIG=str(mundo / "config.json"))
    probar("si el archivo viejo no se puede borrar (otro programa lo tiene tomado), deshace todo: ninguna nota queda con "
           "el nombre nuevo a medias",
           "como estaba" in tomado.stdout and not (memoria / "otro-nombre.md").exists()
           and all(p.read_bytes() == b for p, b in intacto.items()), tomado.stdout + tomado.stderr)
    cortado = correr(["-c", "import sys, os; sys.path.insert(0, sys.argv[1]); import ordenar, cerebro\n"
                            "real = ordenar.escribir_atomico\n"
                            "orden = []\n"
                            "def corte(ruta, contenido):\n"
                            "    orden.append(os.path.basename(str(ruta)))\n"
                            "    if len(orden) == 2:\n"
                            "        raise KeyboardInterrupt\n"
                            "    return real(ruta, contenido)\n"
                            "contexto, error = ordenar.resolver('riego-registro')\n"
                            "plan, error = ordenar.planear_nombre(contexto, 'otro-nombre', cerebro.DATOS)\n"
                            "ordenar.escribir_atomico = corte\n"
                            "try:\n"
                            "    ordenar.aplicar_nombre(plan, cerebro.DATOS)\n"
                            "except KeyboardInterrupt:\n"
                            "    print('cortado', orden[0])\n", str(CARPETA)],
                     CEREBRO_CONFIG=str(mundo / "config.json"))
    probar("--renombrar crea primero la nota con el nombre nuevo y recién después cambia los enlaces (así nunca apuntan a "
           "una nota que todavía no existe), y un Ctrl+C a mitad de camino deshace todo",
           "cortado otro-nombre.md" in cortado.stdout and not (memoria / "otro-nombre.md").exists()
           and all(p.read_bytes() == b for p, b in intacto.items()), cortado.stdout + cortado.stderr)
    viejo_plan = correr(["-c", "import sys; sys.path.insert(0, sys.argv[1]); import ordenar, cerebro\n"
                               "contexto, error = ordenar.resolver('riego-registro')\n"
                               "plan, error = ordenar.planear_nombre(contexto, 'otro-nombre', cerebro.DATOS)\n"
                               "open(sys.argv[2], 'a', encoding='utf-8', newline='\\n').write('Lo anotó otro chat.\\n')\n"
                               "print(ordenar.aplicar_nombre(plan, cerebro.DATOS)[1])\n", str(CARPETA),
                        str(memoria / "bomba-nueva.md")], CEREBRO_CONFIG=str(mundo / "config.json"))
    probar("si otro chat cambia una de las notas entre el plan y el cambio, no aplica el plan viejo: nada cambia de nombre "
           "y lo que escribió el otro chat queda",
           "cambió" in viejo_plan.stdout and "como estaba" in viejo_plan.stdout and nueva.exists()
           and not (memoria / "otro-nombre.md").exists() and leer(memoria / "bomba-nueva.md").endswith("Lo anotó otro chat.\n")
           and "[[riego-registro]]" in leer(memoria / "bomba-nueva.md"), viejo_plan.stdout + viejo_plan.stderr)
    def renombrar(viejo, nuevo_nombre):
        _, texto = cerebro_en(mundo, "--renombrar", viejo, nuevo_nombre)
        codigo_plan = re.search(r"--confirmar ([0-9a-f]{8})", texto)
        return cerebro_en(mundo, "--renombrar", viejo, nuevo_nombre, "--confirmar", codigo_plan.group(1) if codigo_plan else "")

    escribir(memoria / "vivero.md", frontmatter("vivero", "Datos fijos del vivero: dónde queda y cuánto mide", "project")
             + "# Vivero\n\nEl vivero mide 40 metros.\n")
    escribir(memoria / "medidas.md", frontmatter("medidas", "Las medidas del vivero y de cada cantero, en metros", "project")
             + "# Medidas\n\nVer [[vivero]]. El vivero tiene dos naves.\n")
    codigo, salida = renombrar("vivero", "invernadero")
    probar("una nota de nombre corto, sin guion, también cambia su name y los [[enlaces]] que le apuntan; la palabra suelta "
           "en el texto no se toca, porque el mapa tampoco la toma por una mención",
           codigo == 0 and "\nname: invernadero\n" in leer(memoria / "invernadero.md")
           and "El vivero mide 40 metros." in leer(memoria / "invernadero.md")
           and leer(memoria / "medidas.md").endswith("Ver [[invernadero]]. El vivero tiene dos naves.\n")
           and "medidas del vivero" in leer(memoria / "medidas.md"), salida)
    escribir(docs / "Plan viejo.md", "# Plan viejo\n\nLo que se pensó en enero.\n")
    escribir(docs / "INDICE.md", "# Documentos\n\n[el plan](Plan%20viejo.md#enero) y [otra forma](<Plan viejo.md>).\n")
    codigo, salida = renombrar("Plan viejo", "Plan nuevo")
    probar("una nota común con espacios en el nombre: cambian los enlaces de Markdown que le apuntan desde su mismo grupo, "
           "con los espacios codificados o entre < > como estaban",
           codigo == 0 and (docs / "Plan nuevo.md").exists() and not (docs / "Plan viejo.md").exists()
           and leer(docs / "INDICE.md").endswith("[el plan](Plan%20nuevo.md#enero) y [otra forma](<Plan nuevo.md>).\n"),
           salida + leer(docs / "INDICE.md"))
    probar("el lugar del nombre dentro de un enlace se halla aunque lleve carpeta, ancla, < > o espacios codificados",
           [ordenar.lugar_del_nombre(c) for c in ("nota.md", "../m/nota.md#x", "<./mi nota.md>", "a%20b.md?v=1")]
           == [(0, 7), (5, 12), (3, 13), (0, 8)])
    escribir(memoria / "launcher-nuevo.md", frontmatter("launcher-nuevo", "El launcher nuevo del vivero: cómo se arma",
                                                        "project") + "# Launcher nuevo\n\nSe arma solo.\n")
    con_rutas = ("# Publicar\n\nVer launcher-nuevo para el detalle; también `launcher-nuevo`.\n"
                 "El código está en `D:\\launcher-nuevo\\src`, el guion en launcher-nuevo\\armar.py y en ver/launcher-nuevo.py.\n"
                 "```\ngit checkout launcher-nuevo\ncd D:\\launcher-nuevo\n```\n")
    escribir(memoria / "publicar.md", frontmatter("publicar", "Cómo se publica cada versión del vivero", "project") + con_rutas)
    _, plan_rutas = cerebro_en(mundo, "--renombrar", "launcher-nuevo", "launcher-viejo")
    codigo, salida = renombrar("launcher-nuevo", "launcher-viejo")
    publicar = leer(memoria / "publicar.md")
    probar("--renombrar cambia el nombre de la nota en el texto y solo entre comillas invertidas, pero no una carpeta, un "
           "archivo ni un comando que se llaman igual (D:\\launcher-nuevo\\src, git checkout launcher-nuevo): esos los "
           "muestra en el plan, con su renglón, para cambiarlos a mano",
           codigo == 0 and "Ver launcher-viejo para el detalle; también `launcher-viejo`." in publicar
           and "`D:\\launcher-nuevo\\src`" in publicar and "launcher-nuevo\\armar.py" in publicar
           and "ver/launcher-nuevo.py" in publicar and "git checkout launcher-nuevo\ncd D:\\launcher-nuevo\n" in publicar
           and "No toco 5 menciones del nombre que están en una ruta" in plan_rutas and "publicar.md:12" in plan_rutas
           and "publicar.md:15" in plan_rutas,
           (plan_rutas, publicar))
    escribir(memoria / "duplicada-a.md", frontmatter("mismo-nombre", "Una nota que comparte el name con otra", "project")
             + "# A\n\nUna.\n")
    escribir(memoria / "duplicada-b.md", frontmatter("mismo-nombre", "La otra nota que comparte el name", "project")
             + "# B\n\nOtra.\n")
    dos_ordenes = correr(["-c", "import json, sys; sys.path.insert(0, sys.argv[1]); import ordenar, cerebro\n"
                                "contexto, error = ordenar.resolver('duplicada-a')\n"
                                "c = contexto['cerebro']\n"
                                "ids = sorted(c.slugs_mencionables['mismo-nombre'])\n"
                                "salida = []\n"
                                "for orden in (ids, ids[::-1]):\n"
                                "    c.slugs_mencionables['mismo-nombre'] = orden\n"
                                "    plan, error = ordenar.planear_nombre(contexto, 'otra-cosa', cerebro.DATOS)\n"
                                "    salida.append([plan['huella'], sorted(x['ruta'].name for x in plan['cambios'])])\n"
                                "print(json.dumps(salida))\n", str(CARPETA)], CEREBRO_CONFIG=str(mundo / "config.json"))
    try:
        planes = json.loads(dos_ordenes.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        planes = []
    probar("si dos notas comparten el name, --renombrar da el mismo plan en cualquier orden y nunca le cambia el name a "
           "la otra nota (antes dependía del orden al azar de Python)",
           len(planes) == 2 and planes[0] == planes[1] and "duplicada-b.md" not in planes[0][1],
           (planes, dos_ordenes.stderr[-400:]))


def revisar_obsidian(t):
    seccion("Una bóveda de Obsidian como fuente")
    mundo = t / "obsidian"
    memoria, boveda = mundo / "memoria", mundo / "boveda"
    for carpeta in (memoria, boveda / "Proyectos" / "Vivero", boveda / "Archivo" / "Vivero", boveda / "Archivo" / "Notas",
                    boveda / "Notas", boveda / "Sueltas", mundo / "en-vivo"):
        carpeta.mkdir(parents=True)

    def escribir(ruta, texto):
        ruta.write_text(texto, encoding="utf-8", newline="\n")

    escribir(memoria / "MEMORY.md", "# Memoria\n\n- [Riego](riego.md) — cómo se riega el vivero\n"
             "- [Riego, historia 1 (archivo)](riego-historia-1.md) — lo viejo del riego\n")
    escribir(memoria / "riego-historia-1.md",
             frontmatter("riego-historia-1", "(archivo) Lo viejo del riego; lo vigente está en riego", "project")
             + "# Riego, historia 1 (archivo)\n\nAntes se regaba con [[bomba-vieja]].\n")
    escribir(memoria / "riego.md", frontmatter("riego", "Cómo se riega el vivero y cada cuánto", "project")
             + "# Riego\n\nVer la bóveda. El turno de cosecha se anota como `[[cosecha-anual]]`.\n")
    escribir(memoria / "cosecha-anual.md", "---\nname: cosecha-anual\ndescription: Cuándo se cosecha cada cantero del vivero\n"
             "tags: [cosecha, vivero]\nmetadata:\n  node_type: memory\n  type: project\n---\n\n# Cosecha\n\nEn marzo. "
             "#nota-suelta\n")
    escribir(boveda / "Sueltas" / "Con propiedades.md", '---\naliases:\n  - IA\n  - "Inteligencia artificial"\ntags:\n'
             '  - proyecto/vivero\n  - "#urgente"\nrelated:\n  - "[[Notas/Diario]]"\n---\n\n# Máquinas que piensan\n\n'
             "Una nota con #riego en el texto, y `#no-es-etiqueta` en código.\n")
    escribir(boveda / "Sueltas" / "Sintaxis.md", "# Cómo se enlaza\n\nSe escribe `[[Carpeta/Nota]]` o `[texto](otra.md)`.\n\n"
             "```\n[[Sueltas/Idea]]\n[[Tampoco existe]]\n```\n\nY acá sí: [[Notas/Diario]].\n")
    escribir(boveda / "Inicio.md", "# Inicio\n\n- [[Proyectos/Vivero/Plan|el plan]]\n- [[Archivo/Vivero/Plan]]\n"
             "- [[Vivero/Plan]]\n- [[../boveda/Sueltas/Idea]]\n- [[Sueltas/Idea#Para qué]] y [[Idea#^abc123]]\n"
             "- [[Notas/Diario]], y lo de Sueltas/No existe ya no está\n- [[Sueltas/No existe]]\n"
             "- ![[foto.png]], [[Sueltas/informe.pdf|el informe]] y ![[Sueltas/Idea]]\n- [[Versión 1.5]]\n"
             "- [[Proyectos/Vivero/Tareas|las tareas]]\n")
    (boveda / "foto.png").write_bytes(b"\x89PNG\r\n")
    for carpeta in (boveda / ".trash", boveda / ".obsidian" / "plugins" / "tema"):
        carpeta.mkdir(parents=True)
    escribir(boveda / ".trash" / "Borrada.md", "# Borrada\n\nIba con [[Sueltas/Idea]] y [[Ya no existe]].\n")
    for carpeta in (boveda / ".stversions" / "Proyectos", boveda / ".plantillas-ocultas"):
        carpeta.mkdir(parents=True)
    escribir(boveda / ".stversions" / "Proyectos" / "Tareas~20261018-120000.md", "# Tareas\n\nRegar.\n")
    escribir(boveda / ".plantillas-ocultas" / "Oculta.md", "# Oculta\n\nVer [[{{date}}]].\n")
    escribir(boveda / "Sueltas" / "Reunión.md", "# Reunión\n\nAyer: [[{{date:YYYY-MM-DD}}]]. Creada el "
             "[[<% tp.date.now(\"YYYY-MM-DD\") %>]], de [[{{title}}|la plantilla]].\n")
    escribir(boveda / ".obsidian" / "plugins" / "tema" / "README.md", "# Tema\n\nUn plugin.\n")
    escribir(boveda / ".obsidian" / "app.json", json.dumps({"userIgnoreFilters": ["Plantillas/", "/borrador/"]}))
    (boveda / "Plantillas").mkdir()
    escribir(boveda / "Plantillas" / "Diaria.md", "# {{title}}\n\nVer [[{{date}}]].\n")
    escribir(boveda / "Dibujo.excalidraw.md", "---\nexcalidraw-plugin: parsed\n---\n# Text Elements\nHola ^a1\n\n%%\n"
             "# Drawing\n```json\n{\"type\": \"excalidraw\"}\n```\n%%\n")
    escribir(boveda / "Sueltas" / "borrador-idea.md", "# Borrador\n\nA medio escribir.\n")
    escribir(boveda / "Sueltas" / "Ocultas.md", "# Lo que Obsidian no muestra\n\n[[Plantillas/Diaria]], [[Diaria]], "
             "![[Dibujo.excalidraw]], [el dibujo](../Dibujo.excalidraw.md) y [[borrador-idea]].\n")
    escribir(boveda / "Proyectos" / "Vivero" / "Plan.md", "# Plan vigente\n\nLas tareas, en [[./Tareas]].\n")
    escribir(boveda / "Proyectos" / "Vivero" / "Tareas.md", "# Tareas\n\nRegar.\n")
    escribir(boveda / "Archivo" / "Vivero" / "Plan.md", "# Plan viejo\n\nLo del año pasado.\n")
    escribir(boveda / "Notas" / "Diario.md", "# Diario\n\nHoy.\n")
    escribir(boveda / "Archivo" / "Notas" / "Diario.md", "# Diario viejo\n\nAyer.\n")
    escribir(boveda / "Sueltas" / "Idea.md", '---\nrelated: "[[Proyectos/Vivero/Plan]]"\n---\n\n# Idea\n\n## Para qué\n\n'
             "Una idea suelta. ^abc123\n")
    escribir(boveda / "Guia.md", "# Guía\n\nLa de la raíz.\n")
    escribir(boveda / "Notas" / "Guia.md", "# Guía de notas\n\nOtra con el mismo nombre.\n")
    escribir(boveda / "Notas" / "Lista.md", "# Lista\n\nVer [[Guia]].\n")
    escribir(boveda / "Sueltas" / "Otra.md", "# Otra\n\nTambién [[Guia]].\n")
    (boveda / "Markdown").mkdir()
    escribir(boveda / "Markdown" / "Origen.md", "# Enlaces Markdown\n\n[corto](Tareas.md), [desde la raíz]"
             "(Proyectos/Vivero/Tareas.md), [con barra](/Proyectos/Vivero/Tareas.md), [sin extensión]"
             "(../Proyectos/Vivero/Tareas), [con espacios](Con%20propiedades.md) y [roto](No%20existe.md).\n")
    escribir(mundo / "config.json", json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]], "memoria": True,
         "foco": True},
        {"id": "boveda", "nombre": "Bóveda", "color": "#228BE6", "raices": [[str(boveda), True, ""]]}],
        "podar": ["node_modules"]}, ensure_ascii=False))
    codigo, salida = cerebro_en(mundo, "--salida", str(mundo / "mapa.html"), "--json", str(mundo / "mapa.json"))
    datos = json.loads((mundo / "mapa.json").read_text(encoding="utf-8")) if codigo == 0 else {}
    relativa = {n["id"]: os.path.relpath(n["ruta"], boveda).replace("\\", "/") for n in datos.get("nodos", [])}
    wiki = sorted((relativa[a["de"]], relativa[a["a"]]) for a in datos.get("aristas", []) if a["clase"] == "wiki")
    salud = datos.get("salud", {})
    probar("en una bóveda no entra nada de una carpeta con punto, como en Obsidian: ni .obsidian, ni la papelera .trash "
           "(una nota borrada no vuelve como viva), ni las versiones viejas de .stversions, aunque el config.json tenga "
           "un «podar» propio sin ellas",
           datos and not [r for r in relativa.values() if any(p.startswith(".") and p != ".." for p in r.split("/"))],
           sorted(relativa.values()))
    con_punto = t / ".config-falsa" / "boveda-adentro"
    (con_punto / ".obsidian").mkdir(parents=True)
    (con_punto / ".stversions").mkdir()
    probar("lo que está arriba de la raíz de la bóveda no cuenta: una bóveda adentro de una carpeta con punto (como la "
           "memoria bajo ~/.claude) sigue entrando, y adentro de ella, sus carpetas con punto no",
           not nucleo.es_oculta(con_punto / "Nota.md") and nucleo.es_oculta(con_punto / ".stversions" / "Nota~1.md"))
    enlaces_md = sorted({relativa[a["a"]] for a in datos.get("aristas", [])
                         if a["clase"] == "enlace" and relativa.get(a["de"]) == "Markdown/Origen.md"})
    rotos_md = sorted(r.get("destino") for r in salud.get("rotos", []) if relativa.get(r.get("de")) == "Markdown/Origen.md")
    probar("en una bóveda, los enlaces Markdown llevan a su nota como en Obsidian (con «Usar [[Wikilinks]]» apagado): el "
           "nombre solo, la ruta desde la raíz con o sin / adelante, sin .md y con espacios codificados; solo el que no "
           "existe sale roto", enlaces_md == ["Proyectos/Vivero/Tareas.md", "Sueltas/Con propiedades.md"]
           and rotos_md == ["No%20existe.md"], (enlaces_md, salud.get("rotos")))
    con_obsidian = {relativa[n["id"]]: n.get("obsidian") for n in datos.get("nodos", [])}
    probar("cada nota de la bóveda sabe en qué bóveda está y su ruta adentro, para el botón «Abrir en Obsidian»; las "
           "que no están en una bóveda, no",
           con_obsidian.get("Proyectos/Vivero/Plan.md") == {"boveda": "boveda", "archivo": "Proyectos/Vivero/Plan.md"}
           and "../memoria/riego.md" in con_obsidian and con_obsidian["../memoria/riego.md"] is None, con_obsidian)
    etiquetas = {relativa[n["id"]]: n.get("etiquetas") for n in datos.get("nodos", [])}
    probar("las etiquetas salen de la lista del encabezado (como la guarda Obsidian, o entre corchetes) y, solo en una "
           "bóveda, de los #tema del texto, sin lo que está en código; en una memoria, un #algo suelto no es etiqueta",
           etiquetas.get("Sueltas/Con propiedades.md") == ["proyecto/vivero", "urgente", "riego"]
           and etiquetas.get("../memoria/cosecha-anual.md") == ["cosecha", "vivero"] and etiquetas.get("Inicio.md") is None,
           etiquetas)
    propiedades = nucleo.separar_frontmatter(
        '---\naliases:\n  - IA\ntags:\n  - tema-a\nnotas relacionadas:\n  - "[[Carpeta/B]]"\n  - otra cosa\n'
        '"fecha de inicio": 2026-10-01\n---\n\nTexto\n')[0]
    cortada = nucleo.separar_frontmatter('---\ntags:\n  - tema-a\n¿esto qué es?\n  - suelta\n---\n\nTexto\n')[0]
    probar("una propiedad con espacios en el nombre (Obsidian lo permite) o entre comillas se lee aparte: sus valores ya "
           "no se pegan a las etiquetas o los alias de arriba; y un renglón que no se entiende corta la lista",
           propiedades.get("tags") == ["tema-a"] and propiedades.get("aliases") == ["IA"]
           and propiedades.get("notas relacionadas") == ["[[Carpeta/B]]", "otra cosa"]
           and propiedades.get("fecha de inicio") == "2026-10-01" and cortada.get("tags") == ["tema-a"],
           (propiedades, cortada))
    _, por_alias = cerebro_en(mundo, "--sobre", "inteligencia artificial", "--todo")
    _, por_etiqueta = cerebro_en(mundo, "--sobre", "urgente", "--todo")
    primera = [s.split("Para leer primero:")[-1].strip().splitlines()[:1] for s in (por_alias, por_etiqueta)]
    probar("la búsqueda encuentra una nota por su alias y por su etiqueta, aunque su texto no los diga",
           all(p and "Con propiedades.md" in p[0] for p in primera), (primera, por_alias[-300:]))
    probar("lo que la bóveda excluye en Obsidian («Archivos excluidos»: una carpeta o una expresión entre barras) y los "
           "dibujos de Excalidraw no entran como notas",
           datos and "Sueltas/Ocultas.md" in relativa.values()
           and not {"Plantillas/Diaria.md", "Dibujo.excalidraw.md", "Sueltas/borrador-idea.md"} & set(relativa.values()),
           sorted(relativa.values()))
    probar("los [[enlaces]] con carpeta, como los escribe Obsidian, llevan a su nota: desde la raíz de la bóveda, relativos "
           "(./ y ../), con título o bloque, y también los del encabezado",
           wiki == [("Inicio.md", "Archivo/Vivero/Plan.md"), ("Inicio.md", "Notas/Diario.md"),
                    ("Inicio.md", "Proyectos/Vivero/Plan.md"), ("Inicio.md", "Proyectos/Vivero/Tareas.md"),
                    ("Inicio.md", "Sueltas/Idea.md"), ("Notas/Lista.md", "Guia.md"),
                    ("Proyectos/Vivero/Plan.md", "Proyectos/Vivero/Tareas.md"),
                    ("Sueltas/Con propiedades.md", "Notas/Diario.md"), ("Sueltas/Idea.md", "Proyectos/Vivero/Plan.md"),
                    ("Sueltas/Otra.md", "Guia.md"), ("Sueltas/Sintaxis.md", "Notas/Diario.md")],
           (codigo, wiki, salida[-300:]))
    probar("con dos notas del mismo nombre, un [[enlace]] por el nombre lleva a la de la raíz de la bóveda desde cualquier "
           "carpeta, como en Obsidian (antes ganaba la de la misma carpeta, o quedaba ambiguo)",
           ("Notas/Lista.md", "Guia.md") in wiki and ("Sueltas/Otra.md", "Guia.md") in wiki, wiki)
    menciones = sorted((relativa[a["de"]], relativa[a["a"]]) for a in datos.get("aristas", []) if a["clase"] == "mencion")
    probar("un [[enlace]] o un enlace de Markdown dentro de código (entre comillas invertidas o en un bloque) no cuenta como "
           "enlace, como en Obsidian; si nombra una memoria, cuenta como mención, igual que su nombre suelto",
           ("../memoria/riego.md", "../memoria/cosecha-anual.md") in menciones
           and not [w for w in wiki if w[0] == "../memoria/riego.md"], (menciones, wiki))
    ambiguos = [(relativa[x["de"]], x["mencion"], sorted(relativa[c] for c in x["candidatos"]))
                for x in salud.get("ambiguos", [])]
    probar("si la ruta del enlace calza con dos notas, queda como ambiguo y no como roto; si una está en la raíz de la "
           "bóveda, gana esa, como en Obsidian",
           ambiguos == [("Inicio.md", "[[Vivero/Plan]]", ["Archivo/Vivero/Plan.md", "Proyectos/Vivero/Plan.md"])],
           ambiguos)
    rotos = sorted((relativa[x["de"]], x["destino"]) for x in salud.get("rotos", []))
    probar("un adjunto (una foto, un PDF) no es una nota y no cuenta como enlace roto; roto queda el enlace a una nota que "
           "no existe, aunque su nombre lleve un punto; el de una nota de archivo no se marca, ni el que lleva a algo que la "
           "bóveda excluye (en Obsidian anda), ni el que es sintaxis de plantilla ([[{{date}}]], [[<% tp.… %>]])",
           rotos == [("Inicio.md", "Sueltas/No existe"), ("Inicio.md", "Versión 1.5"),
                     ("Markdown/Origen.md", "No%20existe.md")], rotos)
    hook = correr(["-c", "import sys; sys.path.insert(0, sys.argv[1]); import medico\n"
                         "print(medico.enlaces_rotos(sys.argv[2], open(sys.argv[2], encoding='utf-8').read()))\n",
                   str(CARPETA), str(boveda / "Sueltas" / "Sintaxis.md")], CEREBRO_CONFIG=str(mundo / "config.json"))
    probar("el aviso del hook al editar tampoco toma por roto un enlace que está dentro de código",
           hook.returncode == 0 and hook.stdout.strip() == "[]", hook.stdout + hook.stderr[-300:])
    excluidas = correr(["-c", "import sys, json, pathlib; sys.path.insert(0, sys.argv[1]); import cerebro\n"
                              "b = pathlib.Path(sys.argv[2])\n"
                              "app = b / '.obsidian' / 'app.json'\n"
                              "texto = app.read_text(encoding='utf-8')\n"
                              "dichas = [cerebro.fuente_de_ruta(str(b / 'Plantillas' / 'Diaria.md')),\n"
                              "          cerebro.fuente_de_ruta(str(b / 'Dibujo.excalidraw.md')),\n"
                              "          (cerebro.fuente_de_ruta(str(b / 'Inicio.md')) or {}).get('id')]\n"
                              "antes = cerebro.huella()\n"
                              "app.write_text(texto.replace('Plantillas/', 'Plantillas/viejas/'), encoding='utf-8')\n"
                              "despues = cerebro.huella()\n"
                              "app.write_text(texto, encoding='utf-8')\n"
                              "print(json.dumps(dichas + [antes != despues]))\n", str(CARPETA), str(boveda)],
                       CEREBRO_CONFIG=str(mundo / "config.json"))
    probar("para el hook, lo que la bóveda excluye tampoco es una nota; y si cambia la lista de excluidos de Obsidian, el "
           "mapa se entera y se rearma",
           excluidas.stdout.strip() == json.dumps([None, None, "boveda", True]), excluidas.stdout + excluidas.stderr[-300:])
    _, medico_dice = cerebro_en(mundo, "--salud", "--todo")
    probar("el médico ubica cada enlace roto en su renglón, aunque el mismo texto aparezca antes en la nota",
           "Inicio.md:9 — Enlaza a «Sueltas/No existe»" in medico_dice
           and "Inicio.md:11 — Enlaza a «Versión 1.5»" in medico_dice, medico_dice[-600:])
    _, plan = cerebro_en(mundo, "--renombrar", "Tareas", "Pendientes")
    clave = re.search(r"--confirmar ([0-9a-f]{8})", plan)
    codigo, hecho = cerebro_en(mundo, "--renombrar", "Tareas", "Pendientes", "--confirmar", clave.group(1) if clave else "")
    inicio = (boveda / "Inicio.md").read_text(encoding="utf-8")
    plan_vivero = (boveda / "Proyectos" / "Vivero" / "Plan.md").read_text(encoding="utf-8")
    probar("--renombrar cambia solo el nombre dentro de un [[enlace]] con carpeta o relativo, y la carpeta queda",
           codigo == 0 and (boveda / "Proyectos" / "Vivero" / "Pendientes.md").exists()
           and "- [[Proyectos/Vivero/Pendientes|las tareas]]\n" in inicio and "[[./Pendientes]]" in plan_vivero,
           plan + hecho + inicio + plan_vivero)
    origen_md = (boveda / "Markdown" / "Origen.md").read_text(encoding="utf-8")
    probar("--renombrar también cambia los enlaces Markdown que Obsidian escribe en una bóveda (el nombre solo, desde la "
           "raíz y sin .md), y el que no lleva .md sigue sin llevarlo",
           "[corto](Pendientes.md), [desde la raíz](Proyectos/Vivero/Pendientes.md), [con barra](/Proyectos/Vivero/"
           "Pendientes.md), [sin extensión](../Proyectos/Vivero/Pendientes)," in origen_md, origen_md)
    _, rechazo = cerebro_en(mundo, "--renombrar", "Inicio", "Diario")
    probar("en una bóveda, --renombrar no acepta un nombre que ya usa otra nota en otra carpeta (los [[Diario]] quedarían "
           "ambiguos, sin aviso)", "ya hay una nota que se llama Diario" in rechazo and (boveda / "Inicio.md").exists()
           and not (boveda / "Diario.md").exists(), rechazo)
    config = json.loads((mundo / "config.json").read_text(encoding="utf-8"))
    huerfanas_antes = [r for r in medico_dice.splitlines() if "Ninguna nota la nombra" in r or "no se alcanzan" in r]
    sueltas_antes = [i for i in salud.get("huerfanos", []) if i.startswith("boveda:")]
    config["fuentes"][1]["huerfanas"] = False
    escribir(mundo / "config.json", json.dumps(config, ensure_ascii=False))
    _, medico_sin = cerebro_en(mundo, "--salud", "--todo")
    codigo, _ = cerebro_en(mundo, "--salida", str(mundo / "sin.html"), "--json", str(mundo / "sin.json"))
    sin = json.loads((mundo / "sin.json").read_text(encoding="utf-8")) if codigo == 0 else {}
    probar('con "huerfanas": false en una fuente, sus notas no dan el aviso de huérfana (el del médico ni el de Salud) ni '
           "cuentan en «no se alcanzan»; sin la opción, como siempre",
           len(huerfanas_antes) >= 3 and sueltas_antes and sin and not sin["salud"]["huerfanos"]
           and not [r for r in medico_sin.splitlines() if "Ninguna nota la nombra" in r or "no se alcanzan" in r],
           (huerfanas_antes, sueltas_antes, medico_sin[-400:]))
    config["fuentes"][1]["historico"] = True
    escribir(mundo / "config.json", json.dumps(config, ensure_ascii=False))
    _, medico_historico = cerebro_en(mundo, "--salud", "--todo")
    codigo, _ = cerebro_en(mundo, "--salida", str(mundo / "historico.html"), "--json", str(mundo / "historico.json"))
    historico = json.loads((mundo / "historico.json").read_text(encoding="utf-8")) if codigo == 0 else {}
    probar("una fuente historico no da avisos de enlaces rotos, como dice Cómo funciona: ni el médico ni Salud",
           "Enlaza a «Sueltas/No existe»" in medico_dice and historico and not historico["salud"]["rotos"]
           and "Enlaza a" not in medico_historico, medico_historico[-400:])
    config["fuentes"][1]["huerfanas"] = "no"
    escribir(mundo / "config.json", json.dumps(config, ensure_ascii=False))
    _, rota = cerebro_en(mundo, "--salud")
    probar('"huerfanas" con algo que no es true o false es un error de configuración que dice qué arreglar',
           "fuentes[1].huerfanas tiene que ser true o false" in rota, rota[-300:])
    config["fuentes"][1].pop("huerfanas", None)
    escribir(mundo / "config.json", json.dumps(config, ensure_ascii=False))
    (memoria / ".obsidian").mkdir()
    try:
        codigo, _ = cerebro_en(mundo, "--salida", str(mundo / "memoria-boveda.html"), "--json",
                               str(mundo / "memoria-boveda.json"))
        en_boveda = json.loads((mundo / "memoria-boveda.json").read_text(encoding="utf-8")) if codigo == 0 else {}
    finally:
        shutil.rmtree(memoria / ".obsidian", ignore_errors=True)
    cosecha = next((n for n in en_boveda.get("nodos", []) if n["ruta"].endswith("cosecha-anual.md")), {})
    probar("con la memoria abierta como bóveda (lo que recomienda la guía), un #algo suelto en su texto sigue sin ser "
           "etiqueta (en la memoria suelen ser colores o anclas); las de tags: sí",
           cosecha.get("obsidian") and cosecha.get("etiquetas") == ["cosecha", "vivero"], cosecha)
    if shutil.which("node") is None:
        saltear("sin node en el PATH: la página con enlaces de Obsidian, salteada")
        return
    plantilla = plantilla_entera(CARPETA / "plantilla.html")
    piezas = [re.search(r"(?m)^\s*const normRuta = .*$", plantilla), re.search(r"(?m)^\s*const RE_ADJUNTO = .*$", plantilla),
              re.search(r"  function resolverPuntos\(p\) \{.*?\n  \}\n", plantilla, re.S),
              re.search(r"  function rutaAbsoluta\(href, n\) \{.*?\n  \}\n", plantilla, re.S),
              re.search(r"(?m)^\s*const decodificar = .*$", plantilla),
              re.search(r"  function conMdSiFalta\(href\) \{.*?\n  \}\n", plantilla, re.S),
              re.search(r"  function resolverPorCola\(href, n\) \{.*?\n  \}\n", plantilla, re.S),
              re.search(r"  function enlaceObsidian\(n\) \{.*?\n  \}\n", plantilla, re.S),
              re.search(r"  function resolverWikiConCarpeta\(s, desde\) \{.*?\n  function ajustarEnlaces", plantilla, re.S)]
    nodos = [{"id": relativa[n["id"]], "ruta": n["ruta"], "slug": n["slug"], "archivo": Path(n["ruta"]).name}
             for n in datos.get("nodos", [])]
    aristas = [{"de": relativa[a["de"]], "a": relativa[a["a"]], "clase": a["clase"]} for a in datos.get("aristas", [])]
    prueba = mundo / "wiki.js"
    escribir(prueba, "".join((p.group(0) if p else "") + "\n" for p in piezas).replace("function ajustarEnlaces", "")
             + f"const nodos = {json.dumps(nodos)};\nconst aristas = {json.dumps(aristas)};\n"
             "const porId = new Map(nodos.map(n => [n.id, n]));\nnodos.forEach(n => { n.salientes = []; });\n"
             "aristas.forEach(a => porId.get(a.de).salientes.push({ clase: a.clase, target: porId.get(a.a) }));\n"
             "const porRuta = new Map(nodos.map(n => [normRuta(n.ruta), n]));\n"
             "const ver = (slug, de) => { const r = resolverWiki(slug, porId.get(de)); return r ? r.id : null; };\n"
             "console.log(JSON.stringify([ver('Proyectos/Vivero/Plan', 'Inicio.md'), ver('Archivo/Vivero/Plan', 'Inicio.md'),"
             " ver('Vivero/Plan', 'Inicio.md'), ver('../boveda/Sueltas/Idea', 'Inicio.md'), ver('Notas/Diario', 'Inicio.md'),"
             " ver('./Tareas', 'Proyectos/Vivero/Plan.md'), ver('Sueltas/No existe', 'Inicio.md'),"
             " ['foto.png', 'Sueltas/informe.pdf', 'board.canvas', 'Versión 1.5', 'Nota.md'].map(x => RE_ADJUNTO.test(x)),"
             " enlaceObsidian({ ruta: '/home/ana/Mi bóveda/Proyectos/Vivero/Plan.md',"
             " obsidian: { boveda: 'Mi bóveda', archivo: 'Proyectos/Vivero/Plan.md' } }),"
             " enlaceObsidian({ obsidian: null }),"
             " [conMdSiFalta('../Proyectos/Vivero/Tareas#Regar'), conMdSiFalta('foto.png'), conMdSiFalta('Nota.md'),"
             " (resolverPorCola('/Proyectos/Vivero/Tareas.md', porId.get('Inicio.md')) || {}).id]]));\n")
    r = subprocess.run(["node", str(prueba)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    filtro = re.search(r"  const SIN_ETIQUETA = '';.*?\n  const clavesEtiquetas = .*?;\n", plantilla, re.S)
    visible = re.search(r"  function etiquetaVisible\(n\) \{.*?\n  \}\n", plantilla, re.S)
    prueba_filtro = mundo / "etiquetas.js"
    escribir(prueba_filtro, "const nodos = [{ id: 'a', etiquetas: ['Riego', 'urgente'] }, { id: 'b', etiquetas: ['riego'] }, "
             "{ id: 'c', etiquetas: [] }];\n" + (filtro.group(0) if filtro else "") + (visible.group(0) if visible else "")
             + "const estado = { etiquetasOn: new Set(clavesEtiquetas()) };\n"
             "const ver = () => nodos.filter(etiquetaVisible).map(n => n.id).join('');\nconst salida = [ver()];\n"
             "estado.etiquetasOn = new Set(['urgente']); salida.push(ver());\n"
             "estado.etiquetasOn = new Set([SIN_ETIQUETA]); salida.push(ver());\n"
             "salida.push(ETIQUETAS.map(e => e.nombre + ':' + e.cantidad).join(','));\nconsole.log(JSON.stringify(salida));\n")
    r_filtro = subprocess.run(["node", str(prueba_filtro)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    probar("el filtro de etiquetas del mapa: con todas marcadas se ve todo; con una, solo sus notas; «Sin etiqueta», las "
           "que no tienen; y la misma etiqueta con otras mayúsculas cuenta una vez",
           r_filtro.stdout.strip() == json.dumps(["abc", "a", "c", "Riego:2,urgente:1"], separators=(",", ":")),
           r_filtro.stdout + r_filtro.stderr[:300])
    probar("la página del mapa lleva los mismos [[enlaces]] con carpeta a la misma nota, no elige cuando son ambiguos, "
           "reconoce los adjuntos como Python, arma el enlace de «Abrir en Obsidian» con la ruta completa de la nota, "
           "como pide su ayuda para que Obsidian elija la bóveda (con / y espacios codificados; antes iba por el nombre "
           "de la bóveda, y todas las memorias se llaman «memory»), y encuentra los enlaces Markdown sin .md o con / "
           "adelante",
           r.stdout.strip() == json.dumps(["Proyectos/Vivero/Plan.md", "Archivo/Vivero/Plan.md", None, "Sueltas/Idea.md",
                                           "Notas/Diario.md", "Proyectos/Vivero/Tareas.md", None,
                                           [True, True, True, False, False],
                                           "obsidian://open?path=%2Fhome%2Fana%2FMi%20b%C3%B3veda%2FProyectos%2FVivero"
                                           "%2FPlan.md", "",
                                           ["../Proyectos/Vivero/Tareas.md#Regar", None, None,
                                            "Proyectos/Vivero/Tareas.md"]],
                                          separators=(",", ":"), ensure_ascii=False),
           r.stdout + r.stderr[:300])
    import ordenar
    import pendientes
    import recetas
    import reglas
    import textos
    texto = "Ver [[Sueltas/Idea#Para qué|la idea]], ![[foto.png]] y [[Notas/Diario]]"
    vistos = [nucleo.limpiar_md(texto), ordenar.limpiar(texto), pendientes.limpio(texto)]
    propios = [m.__name__ for m in (nucleo, ordenar, pendientes, recetas, reglas)
               if getattr(m, "sin_wiki", None) is not getattr(textos, "sin_wiki", False)]
    probar("el resumen de una nota muestra el alias de [[destino|alias]] y saca el «!» de los incrustados, como la "
           "página, en el mapa, al partir y en los pendientes (antes mostraba el destino), con una sola regla para todos; "
           "las recetas y las reglas nombran el destino",
           vistos == ["Ver la idea, foto.png y Notas/Diario"] * 3 and not propios
           and nucleo.RE_WIKI is textos.RE_WIKI
           and textos.sin_wiki(texto, "`{destino}`") == "Ver `Sueltas/Idea`, `foto.png` y `Notas/Diario`",
           (vistos, propios))
    con_plantillas, sin_carpeta = mundo / "boveda-plantillas", mundo / "boveda-sin-carpeta"
    for carpeta in (con_plantillas / ".obsidian" / "plugins" / "templater-obsidian", con_plantillas / "Modelos",
                    con_plantillas / "Templater" / "Sub", con_plantillas / "Notas",
                    sin_carpeta / ".obsidian" / "plugins" / "templater-obsidian"):
        carpeta.mkdir(parents=True, exist_ok=True)
    escribir(con_plantillas / ".obsidian" / "templates.json", json.dumps({"folder": "Modelos", "dateFormat": "YYYY-MM-DD"}))
    escribir(con_plantillas / ".obsidian" / "plugins" / "templater-obsidian" / "data.json",
             json.dumps({"templates_folder": "/Templater/"}))
    escribir(sin_carpeta / ".obsidian" / "templates.json", json.dumps({"folder": ""}))
    escribir(sin_carpeta / ".obsidian" / "plugins" / "templater-obsidian" / "data.json", json.dumps({"templates_folder": "/"}))
    casos = {"Modelos/Semanal.md": True, "Templater/Sub/Reunion.md": True, "Notas/Modelos de avión.md": False,
             "Modelos.md": False, "Notas/Diario.md": False}
    nucleo._bovedas.clear()
    vistas = {n: nucleo.es_oculta(str(con_plantillas / n)) for n in casos}
    sueltas = [nucleo.es_oculta(str(sin_carpeta / n)) for n in ("Nota.md", "Sub/Otra.md")]
    escribir(boveda / ".obsidian" / "templates.json", json.dumps({"folder": "Plantillas"}))
    cambio = correr(["-c", "import sys, pathlib; sys.path.insert(0, sys.argv[1]); import cerebro\n"
                           "opciones = pathlib.Path(sys.argv[2]) / '.obsidian' / 'templates.json'\n"
                           "antes = cerebro.huella()\n"
                           "opciones.write_text('{\"folder\": \"Modelos\"}', encoding='utf-8')\n"
                           "print(antes != cerebro.huella())\n", str(CARPETA), str(boveda)],
                    CEREBRO_CONFIG=str(mundo / "config.json"))
    probar("la carpeta de plantillas de Obsidian (la de sus opciones, en .obsidian/templates.json) y la de Templater no "
           "entran como notas, aunque no estén en «Archivos excluidos» (antes daban enlaces rotos con {{date}} y títulos "
           "basura); una carpeta vacía o «/» no deja nada afuera, y si se cambia la carpeta el mapa se rearma",
           vistas == casos and sueltas == [False, False] and cambio.stdout.strip() == "True",
           (vistas, sueltas, cambio.stdout + cambio.stderr[-300:]))


def revisar_indice_juntado(t):
    seccion("Renglones del índice que nombran varias notas")
    mundo = t / "indice-juntado"
    memoria = mundo / "memoria"
    memoria.mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    (memoria / "MEMORY.md").write_text(
        "# Memoria\n\n- [Vivero](vivero.md) — cómo se riega el vivero; sigue en la [parte 2](vivero-parte-2.md)\n"
        "- Vivero, historias (archivo): [1](vivero-historia-1.md) enero; [2](<vivero-historia-2.md>) febrero; "
        "[9](vivero-historia-9.md) marzo\n"
        "* Ver también [la huerta](huerta.md) y [la web](https://ejemplo.invalid/guia.md)\n\n"
        "Un párrafo suelto que nombra [la poda](poda.md) no es un renglón de lista.\n", encoding="utf-8", newline="\n")
    notas = {"vivero": "Cómo se riega el vivero en verano y en invierno", "vivero-parte-2": "La segunda parte del riego del vivero",
             "vivero-historia-1": "(archivo) Lo de enero en el vivero, día por día",
             "vivero-historia-2": "(archivo) Lo de febrero en el vivero, día por día",
             "huerta": "La huerta del fondo y lo que se planta en cada cantero", "poda": "Cuándo se podan los frutales del vivero"}
    for nombre, descripcion in notas.items():
        (memoria / f"{nombre}.md").write_text(frontmatter(nombre, descripcion, "project") + f"# Nota {nombre}\n\nTexto.\n",
                                              encoding="utf-8", newline="\n")
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]],
         "memoria": True, "foco": True}]}, ensure_ascii=False), encoding="utf-8", newline="\n")
    codigo, salida = cerebro_en(mundo, "--salida", str(mundo / "c.html"), "--json", str(mundo / "c.json"))
    try:
        datos = json.loads((mundo / "c.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        datos = {"error": str(error)}
    por_id = {n["id"]: Path(n["ruta"]).name for n in datos.get("nodos", [])}
    del_indice = {por_id.get(a["a"]) for a in datos.get("aristas", [])
                  if por_id.get(a["de"]) == "MEMORY.md" and a["clase"] == "indice"}
    salud = datos.get("salud", {})
    sin_indice = [por_id.get(i) for i in salud.get("sinIndice", [])]
    probar("todo enlace a una nota en un renglón de lista del índice cuenta como listado (el primero, los que siguen y los "
           "de un renglón que no arranca con un enlace); el de un párrafo suelto no",
           codigo == 0 and del_indice == {"vivero.md", "vivero-parte-2.md", "vivero-historia-1.md", "vivero-historia-2.md",
                                          "huerta.md"} and sin_indice == ["poda.md"], (salida[-300:], del_indice, sin_indice))
    rotos = [x.get("destino") for x in salud.get("indiceRoto", [])]
    titulos = {Path(n["ruta"]).name: n["titulo"] for n in datos.get("nodos", [])}
    probar("un enlace de más que apunta a una nota que no existe sale como índice roto (y una dirección de internet no), y "
           "solo el primer enlace del renglón le pone el título a su nota",
           rotos == ["vivero-historia-9.md"] and titulos.get("vivero.md") == "Vivero"
           and titulos.get("vivero-historia-1.md") == "Nota vivero-historia-1"
           and titulos.get("vivero-parte-2.md") == "Nota vivero-parte-2", (rotos, titulos))
    _, medico_dice = cerebro_en(mundo, "--salud", "--todo")
    probar("el médico cuenta las cinco entradas, avisa de la que el índice no lista, no dice que a las otras «se llega por "
           "otra nota» y no les pide gancho a los enlaces de más",
           "5 entradas" in medico_dice and medico_dice.count("que MEMORY.md no lista") == 1
           and "poda.md — Es una memoria que MEMORY.md no lista" in medico_dice and "se llega por" not in medico_dice
           and "no dice cuándo abrirla" not in medico_dice and "vivero-historia-9.md" in medico_dice, medico_dice[-900:])
    ordenar = importlib.import_module("ordenar")
    dormir = importlib.import_module("dormir")
    suelto = ("# Memoria\r\n\r\n- [Guía](guia.md) — suelo, riego y poda\r\n"
              "- [Guía, historia 2 (archivo)](guia-historia-2.md) — lo de febrero; con sus fechas\r\n"
              "- [Otra](otra.md) — otra cosa\r\n- [Guía, historia 1 (archivo)](<guia-historia-1.md>) — lo de enero\r\n"
              "- [Lo viejo de la otra](otra-historia-1.md) — escrito a mano\r\n"
              "- Poda, historias (archivo): [1](poda-historia-1.md) 2024\r\n"
              "- [Poda, historia 2 (archivo)](poda-historia-2.md)\r\n"
              "- [Guía, historia 10 (archivo)](guia-historia-10.md) — lo de octubre\r\n\r\nUn párrafo (archivo) que nombra "
              "la [historia 3](guia-historia-3.md) no es un renglón de lista.\r\n")
    junto, cambios = ordenar.juntar_historias(suelto)
    probar("juntar las historias de cada nota en un renglón: van por número, cada una con su gancho entero, en el lugar "
           "de la primera; la que ya tenía renglón «(archivo)» recibe las sueltas, y no toca un renglón escrito a mano "
           "que está solo, ni un párrafo, ni los fines de línea",
           junto == ("# Memoria\r\n\r\n- [Guía](guia.md) — suelo, riego y poda\r\n"
                     "- Guía, historias (archivo): [1](<guia-historia-1.md>) lo de enero; [2](guia-historia-2.md) lo de "
                     "febrero; con sus fechas; [10](guia-historia-10.md) lo de octubre\r\n"
                     "- [Otra](otra.md) — otra cosa\r\n- [Lo viejo de la otra](otra-historia-1.md) — escrito a mano\r\n"
                     "- Poda, historias (archivo): [1](poda-historia-1.md) 2024; [2](poda-historia-2.md)\r\n\r\nUn párrafo "
                     "(archivo) que nombra la [historia 3](guia-historia-3.md) no es un renglón de lista.\r\n")
           and [(c["familia"], c["juntadas"], c["renglon"]) for c in cambios] == [("guia", 3, 4), ("poda", 2, 7)],
           (junto, cambios))
    probar("si no hay dos renglones de la misma nota para juntar, o ya están juntos, devuelve el índice igual",
           ordenar.juntar_historias(junto) == (junto, [])
           and ordenar.juntar_historias("- [Guía, historia 1 (archivo)](guia-historia-1.md) — enero\n- [A](a.md) — b\n")[1] == [])
    con_titulo = ordenar.juntar_historias(
        "- [Visor](visor.md) — el visor vigente\n"
        "- [Visor: pedidos 1 a 6, con el 3 que Ana rechazó](visor-historia-1.md) — archivo de abril\n"
        "- [Visor, historia 2 (archivo)](visor-historia-2.md) — las 10 propuestas del 5/10\n")[0]
    partido = ("- [Poda, historia 1 (archivo)](poda-historia-1.md) — lo de enero, que sigue\n  en el renglón de abajo\n"
               "- [Poda, historia 2 (archivo)](poda-historia-2.md) — lo de febrero\n")
    probar("al juntar, lo que dice el título de una historia además de «historia N (archivo)» pasa al pedazo (antes se "
           "tiraba), y un renglón que sigue en el de abajo no se junta (antes ese pedazo quedaba colgado de la última)",
           con_titulo == "- [Visor](visor.md) — el visor vigente\n- Visor, historias (archivo): [1](visor-historia-1.md) "
           "pedidos 1 a 6, con el 3 que Ana rechazó — archivo de abril; [2](visor-historia-2.md) las 10 propuestas del "
           "5/10\n" and ordenar.juntar_historias(partido) == (partido, []), (con_titulo, ordenar.juntar_historias(partido)))
    mundo = t / "indice-solo"
    memoria = mundo / "memoria"
    memoria.mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    indice = memoria / "MEMORY.md"
    antes = ("# Memoria\n\n- [Guía](guia.md) — suelo, riego y poda del vivero\n"
             "- [Guía, historia 2 (archivo)](guia-historia-2.md) — lo de febrero, con sus fechas\n"
             "- [Poda](poda.md) — cuándo se poda cada frutal\n"
             "- [Guía, historia 1 (archivo)](guia-historia-1.md) — lo de enero, con sus fechas\n"
             "- [Poda, historia 1 (archivo)](poda-historia-1.md) — lo del año pasado\n")
    indice.write_text(antes, encoding="utf-8", newline="\n")
    for nombre, descripcion in (("guia", "Suelo, riego y poda del vivero, lo vigente"),
                                ("guia-historia-1", "(archivo) Guía: lo de enero, día por día"),
                                ("guia-historia-2", "(archivo) Guía: lo de febrero, día por día"),
                                ("poda", "Cuándo se poda cada frutal del vivero"),
                                ("poda-historia-1", "(archivo) Poda: lo del año pasado, mes por mes")):
        (memoria / f"{nombre}.md").write_text(frontmatter(nombre, descripcion, "project") + f"# Nota {nombre}\n\nTexto.\n",
                                              encoding="utf-8", newline="\n")

    def configurar(**mas):
        (mundo / "config.json").write_text(json.dumps(dict({"usuario": "Ana", "fuentes": [
            {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]],
             "memoria": True, "foco": True}]}, **mas), ensure_ascii=False), encoding="utf-8", newline="\n")

    viejo = time.time() - 3600
    os.utime(indice, (viejo, viejo))
    configurar()
    codigo, salida = cerebro_en(mundo, "--dormir")
    _, que_haria = cerebro_en(mundo, "--por-partir")
    probar("apagado de fábrica, la pasada de cada día no toca el índice, y --por-partir dice qué juntaría",
           codigo == 0 and indice.read_text(encoding="utf-8") == antes and not (mundo / "respaldos").exists()
           and "En el índice MEMORY.md, las historias de 1 nota quedarían en un renglón por nota (1 renglón menos)"
           in que_haria and "Con «partir_sola» prendido" in que_haria, (salida[-300:], que_haria))
    configurar(partir_sola=True)
    os.utime(indice, None)
    codigo, salida = cerebro_en(mundo, "--dormir")
    probar("prendido, no toca un índice que se guardó hace menos de diez minutos (otro chat puede estar escribiéndolo) y "
           "dice por qué",
           codigo == 0 and indice.read_text(encoding="utf-8") == antes
           and "No ordenó sola el índice MEMORY.md: se guardó hace menos de 10 minutos" in salida, salida[-400:])
    os.utime(indice, (viejo, viejo))
    codigo, salida = cerebro_en(mundo, "--dormir")
    despues = indice.read_text(encoding="utf-8")
    copias = list((mundo / "respaldos").glob("*-juntar-indice/1-MEMORY.md"))
    try:
        registro = (mundo / "respaldos" / "partidas.log").read_text(encoding="utf-8")
    except OSError:
        registro = ""
    probar("prendido y con el índice quieto, la pasada de cada día junta en un renglón las historias de una misma nota: un "
           "renglón menos, los ganchos enteros, copia de antes en respaldos y un renglón en el registro",
           codigo == 0 and despues == antes.replace(
               "- [Guía, historia 2 (archivo)](guia-historia-2.md) — lo de febrero, con sus fechas\n",
               "- Guía, historias (archivo): [1](guia-historia-1.md) lo de enero, con sus fechas; [2](guia-historia-2.md) "
               "lo de febrero, con sus fechas\n").replace(
               "- [Guía, historia 1 (archivo)](guia-historia-1.md) — lo de enero, con sus fechas\n", "")
           and "Ordenó sola el índice MEMORY.md: las historias de 1 nota quedaron en un renglón por nota (1 renglón menos)"
           in salida and len(copias) == 1 and copias[0].read_text(encoding="utf-8") == antes
           and "MEMORY.md (el índice): las historias de 1 nota quedaron" in registro, (salida[-400:], despues, registro))
    aviso = dormir.aviso_partidas(str(mundo), "chat0001") or ""
    _, salud = cerebro_en(mundo, "--salud", "--todo")
    probar("a cada chat le avisa una sola vez que ordenó el índice y que lo relea antes de editarlo, y el médico sigue "
           "contando las cinco notas como listadas",
           "ordenó sola el índice" in aviso and "MEMORY.md: las historias de 1 nota" in aviso and "releelo" in aviso
           and "partió sola" not in aviso and dormir.aviso_partidas(str(mundo), "chat0001") is None
           and "5 entradas" in salud and "no lista" not in salud, (aviso, salud[:500]))
    os.utime(indice, (viejo, viejo))
    codigo, salida = cerebro_en(mundo, "--dormir")
    probar("la pasada siguiente no lo vuelve a tocar: ya no hay nada que juntar",
           codigo == 0 and indice.read_text(encoding="utf-8") == despues
           and len(list((mundo / "respaldos").glob("*-juntar-indice*"))) == 1, salida[-400:])
