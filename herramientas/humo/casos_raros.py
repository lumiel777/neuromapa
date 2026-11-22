import builtins

from humo.base import *


def revisar_acentos(t):
    seccion("Acentos guardados de dos formas (NFC y NFD)")
    import unicodedata
    mundo = t / "acentos"
    boveda = mundo / "boveda"
    (boveda / ".obsidian").mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    nfd = lambda s: unicodedata.normalize("NFD", s)
    (boveda / (nfd("Café") + ".md")).write_text("# Café\n\nDe la mañana.\n", encoding="utf-8")
    (boveda / "Canción.md").write_text("# Canción\n\nDel vivero.\n", encoding="utf-8")
    (boveda / "Origen.md").write_text("# Origen\n\nVer [[Café]] y [[" + nfd("Canción") + "]].\n", encoding="utf-8")
    (boveda / "Otra.md").write_text("# Otra\n\nVer [la del café](Caf%C3%A9.md).\n", encoding="utf-8")
    (boveda / "Mencion.md").write_text("# Mención\n\nLo cuenta " + nfd("Canción.md") + ", pegado desde una Mac.\n",
                                       encoding="utf-8")
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "boveda", "nombre": "Bóveda", "color": "#228BE6", "raices": [[str(boveda), True, ""]]}]},
        ensure_ascii=False), encoding="utf-8")
    codigo, salida = cerebro_en(mundo, "--salida", str(mundo / "mapa.html"), "--json", str(mundo / "mapa.json"))
    datos = json.loads((mundo / "mapa.json").read_text(encoding="utf-8")) if codigo == 0 else {}
    nombre = {n["id"]: unicodedata.normalize("NFC", Path(n["ruta"]).name) for n in datos.get("nodos", [])}
    destinos = sorted((nombre.get(a["de"]), a["clase"], nombre.get(a["a"])) for a in datos.get("aristas", [])
                      if nombre.get(a["de"]) in ("Origen.md", "Otra.md") and a["clase"] in ("wiki", "enlace"))
    rotos = [r.get("destino") for r in datos.get("salud", {}).get("rotos", [])]
    probar("un nombre con acento escrito de otra forma Unicode (el archivo descompuesto, como lo dejan las Mac, y el "
           "enlace compuesto, o al revés) lleva a su nota, como en Obsidian, también en un enlace Markdown",
           destinos == [("Origen.md", "wiki", "Café.md"), ("Origen.md", "wiki", "Canción.md"),
                        ("Otra.md", "enlace", "Café.md")] and not rotos, (destinos, rotos, salida[-300:]))
    menciones = sorted(nombre.get(a["a"]) for a in datos.get("aristas", [])
                       if nombre.get(a["de"]) == "Mencion.md" and a["clase"] == "mencion")
    ids = [n["id"] for n in datos.get("nodos", [])]
    probar("una mención escrita descompuesta (texto pegado desde una Mac) también lleva a su nota, y el nombre de cada "
           "nota en el mapa sale compuesto (si no, la misma memoria en Mac y en Windows perdía lo aprendido)",
           menciones == ["Canción.md"] and ids and all(i == unicodedata.normalize("NFC", i) for i in ids), (menciones, ids))


def revisar_detalles_de_lectura(t):
    seccion("Detalles de lectura (títulos con #, encabezados largos, rutas en otra unidad)")
    import ordenar
    titulos = [nucleo.RE_ENCABEZADO.match(x).group(2) for x in ("## Clases de C#", "### Plan ##", "## F# y C#  #")]
    probar("un título que termina en C# o F# conserva el #, y el cierre «##» con espacio antes se saca (antes «Clases de "
           "C#» quedaba «Clases de C»)", titulos == ["Clases de C#", "Plan", "F# y C#"], titulos)
    largo = "---\n" + "Estado: hecho\n" * (nucleo.TOPE_FRONTMATTER + 5) + "---\n\nEl cuerpo.\n"
    datos, cuerpo = nucleo.separar_frontmatter(largo)
    probar("un documento que empieza con una raya --- y tiene otra mucho más abajo no pierde ese tramo como si fuera el "
           "encabezado (el encabezado tiene que cerrar en 200 renglones)", datos == {} and cuerpo == largo
           and ordenar.fin_de_cabeza(largo.split("\n")) == 0, (datos, len(cuerpo)))
    casos = {"````\n```\n# Adentro uno\n```\n````\n# Afuera uno": ["Afuera uno"],
             "```python``` en un renglón\n# Afuera dos": ["Afuera dos"],
             "~~~\n```\n# Adentro tres\n~~~\n# Afuera tres": ["Afuera tres"],
             "```\n# Adentro cuatro\n``` y sigue\n# Adentro cinco\n```\n# Afuera seis": ["Afuera seis"]}
    vistos = {texto: [s["titulo"] for s in nucleo.seccionar(texto) if s["titulo"]] for texto in casos}
    tramos = nucleo.tramos_de_codigo("````\n```\nadentro\n```\n````\nafuera [[x]]")
    probar("un bloque de código cierra solo con el mismo carácter, igual de largo o más y sin nada después, y "
           "«```código```» en un renglón no abre un bloque (antes cualquier ``` abría o cerraba, y un título o un enlace "
           "quedaban del lado equivocado); el médico, la pista, --partir y --pendientes usan la misma regla",
           vistos == casos and len(tramos) == 1 and not nucleo.en_codigo(tramos, 30), (vistos, tramos))
    try:
        relativa = ordenar.ruta_relativa(Path("D:/notas/b.md"), Path("C:/x")) if os.name == "nt" else "D:/notas/b.md"
    except ValueError as error:
        relativa = str(error)
    probar("--partir con el destino en otra unidad no revienta: el enlace va con la ruta entera",
           relativa == "D:/notas/b.md", relativa)


def revisar_enlace_con_ruta_completa(t):
    seccion("Un enlace con la ruta completa a una nota del mapa")
    mundo = t / "ruta-completa"
    notas = mundo / "notas"
    (notas / "sub").mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    destino = notas / "sub" / "Destino.md"
    destino.write_text("# Destino\n", encoding="utf-8")
    (notas / "Origen.md").write_text(f"# Origen\n\nVer [el destino]({destino.as_posix()}).\n", encoding="utf-8")
    (notas / "Otra nota.md").write_text("# Otra nota\n", encoding="utf-8")
    (notas / "Referencias.md").write_text(
        "# Referencias\n\nVer [el destino][d], [Otra][] y [la que falta][Falta].\n\n```\n[en código][d]\n```\n\n"
        "[d]: sub/Destino.md\n[otra]: <Otra nota.md>\n[falta]: no-existe.md\n[sin usar]: tampoco-existe.md\n",
        encoding="utf-8")
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "notas", "nombre": "Notas", "color": "#228BE6", "raices": [[str(notas), True, ""]]}]},
        ensure_ascii=False), encoding="utf-8")
    codigo, salida = cerebro_en(mundo, "--salida", str(mundo / "mapa.html"), "--json", str(mundo / "mapa.json"))
    datos = json.loads((mundo / "mapa.json").read_text(encoding="utf-8")) if codigo == 0 else {}
    nombre = {n["id"]: Path(n["ruta"]).name for n in datos.get("nodos", [])}
    enlaces = sorted((nombre.get(a["de"]), nombre.get(a["a"])) for a in datos.get("aristas", []) if a["clase"] == "enlace")
    probar("un enlace con la ruta completa de una nota del mapa la conecta también en Linux y Mac (antes solo dejaba de "
           "salir roto; en Windows, con la unidad, ya conectaba)", ("Origen.md", "Destino.md") in enlaces,
           (enlaces, salida[-300:]))
    rotos = sorted(r.get("destino") for r in datos.get("salud", {}).get("rotos", []))
    de_referencias = sorted(b for a, b in enlaces if a == "Referencias.md")
    probar("los enlaces de referencia ([texto][d], [Otra][] con [d]: nota.md abajo, sin importar mayúsculas) conectan, "
           "el que lleva a una nota que no existe sale roto, y ni el de un bloque de código ni una definición sin usar "
           "cuentan", de_referencias == ["Destino.md", "Otra nota.md"] and rotos == ["no-existe.md"],
           (de_referencias, rotos))


def revisar_tiempo_relativo(t):
    seccion("Fechas relativas («ayer», «mañana») en notas viejas")
    nota = t / "memoria" / "con-fechas-relativas.md"
    nota.write_text(frontmatter("con-fechas-relativas", "Nota vieja con fechas relativas para la prueba", "project")
                    + "Para mañana: rehacer los arreglos.\n\nLeí un error viejo como si fuera de\nayer.\n\n"
                    + "El texto de la app dice `vuelve\nmañana` y está bien.\n\nEl 20/11 quedó para mañana.\n\n"
                    + "Una mañana de lluvia.\n\nMostraba tomorrow's forecast.\n", encoding="utf-8")
    viejo = time.time() - 3 * 86400
    os.utime(nota, (viejo, viejo))
    try:
        cerebro = armar_cerebro(t)
        avisos = [h for h in medico.regla_tiempo_relativo(cerebro) if cerebro.por_id[h["nota"]]["ruta"] == str(nota)]
    finally:
        nota.unlink()
    probar("en una nota de hace días, «para mañana» sin fecha queda para revisar; «como si fuera de ayer», un texto "
           "entre comillas invertidas, un renglón con fecha, «una mañana» y «tomorrow's» no",
           [h["linea"] for h in avisos] == [9]
           and "«mañana»" in avisos[0]["texto"].lower(), avisos)


def revisar_simbolos(t):
    seccion("Funciones y clases como entidades (--entidad Clase.Metodo)")
    import simbolos
    usa = t / "proyecto" / "codigo" / "Usa.cs"
    usa.write_text("namespace Demo\n{\n    public class Caja\n    {\n        public bool Cobrar(Login login)\n        {\n"
                   "            if (Login.ValidarClave(\"x\")) { return true; }\n            return login.ValidarClave(\"y\");\n"
                   "        }\n    }\n}\n", encoding="utf-8")
    try:
        cerebro = armar_cerebro(t)
        lineas = simbolos.texto_simbolo(cerebro, "ValidarClave") or []
        ninguna = simbolos.texto_simbolo(cerebro, "NoExisteEnNingunLado")
    finally:
        usa.unlink()
    texto = "\n".join(lineas)
    probar("--entidad con una función dice dónde está (archivo y renglones), quién la llama de forma segura "
           "(Login.ValidarClave desde Caja.Cobrar), aparte las probables desde otra variable, y qué notas la nombran",
           "Login.cs:7-" in texto and "Login.ValidarClave" in texto and "lo seguro: 1 llamada" in texto
           and "en Caja.Cobrar" in texto and "Probables" in texto and "arreglo-login.md" in texto and ninguna is None,
           texto[-900:])
    probar("una consulta con forma de archivo, commit o tabla no se toma por una función",
           not simbolos.es_simbolo("riego.py ya") and simbolos.es_simbolo("GameClient.Send") == ("GameClient", "Send")
           and simbolos.es_simbolo("Clase::Metodo()") == ("Clase", "Metodo") and not simbolos.es_simbolo("if"))


def revisar_gemelas(t):
    seccion("Dos notas que solo cambian en mayúsculas (Linux)")
    mundo = t / "gemelas"
    boveda = mundo / "notas"
    boveda.mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    (boveda / "Plan.md").write_text("# Plan grande\n", encoding="utf-8")
    (boveda / "plan.md").write_text("# plan chico\n", encoding="utf-8")
    if len(list(boveda.iterdir())) < 2:
        saltear("dos notas que solo cambian en mayúsculas: este disco no las distingue, salteado")
        return
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "notas", "nombre": "Notas", "color": "#228BE6", "raices": [[str(boveda), True, ""]]}]},
        ensure_ascii=False), encoding="utf-8")
    codigo, salida = cerebro_en(mundo, "--salud")
    probar("de dos notas que solo cambian en mayúsculas, --salud dice cuál quedó afuera (antes se salteaba callada)",
           codigo in (0, 1) and "solo cambia en mayúsculas" in salida, salida[-400:])


def revisar_enlace_afuera(t):
    seccion("Un enlace a una nota que existe fuera del mapa")
    mundo = t / "afuera"
    boveda = mundo / "boveda"
    (boveda / ".obsidian").mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    (mundo / "otra").mkdir()
    (mundo / "otra" / "de-otro.md").write_text("# De otro programa\n", encoding="utf-8")
    existe, falta = (mundo / "otra" / "de-otro.md").as_posix(), (mundo / "otra" / "no-esta.md").as_posix()
    (boveda / "Origen.md").write_text(f"# Origen\n\n- [la de otro](<{existe}>)\n- [la que no está](<{falta}>)\n",
                                      encoding="utf-8")
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "boveda", "nombre": "Bóveda", "color": "#228BE6", "raices": [[str(boveda), True, ""]]}]},
        ensure_ascii=False), encoding="utf-8")
    codigo, salida = cerebro_en(mundo, "--salida", str(mundo / "mapa.html"), "--json", str(mundo / "mapa.json"))
    datos = json.loads((mundo / "mapa.json").read_text(encoding="utf-8")) if codigo == 0 else {}
    rotos = [Path(r.get("destino", "")).name for r in datos.get("salud", {}).get("rotos", [])]
    probar("un enlace a una nota que existe pero queda fuera de las carpetas del mapa (por ejemplo, las notas de otro "
           "programa) no es un enlace roto; uno a una que no existe, sí (antes marcaba los dos)",
           rotos == ["no-esta.md"], (rotos, salida[-300:]))


def revisar_invariancia(t):
    seccion("La misma memoria en otra carpeta o en CRLF")
    mundos = {"corta": t / "inv-a", "larga": t / "otra carpeta con espacios y eñes áé" / "inv-b", "crlf": t / "inv-c"}
    for nombre, mundo in mundos.items():
        mundo.mkdir(parents=True)
        armar_carpeta(mundo)
        escribir_config(mundo)
        login = mundo / "memoria" / "arreglo-login.md"
        login.write_text(login.read_text(encoding="utf-8").replace(str(mundo / "proyecto" / "docs" / "plan-viejo.md"),
                                                                   "proyecto/docs/plan-viejo.md"),
                         encoding="utf-8", newline="\n")
        if nombre == "crlf":
            for archivo in mundo.rglob("*"):
                if archivo.is_file() and archivo.suffix in (".md", ".cs", ".js", ".py"):
                    archivo.write_bytes(archivo.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))

    def normal(texto, mundo):
        for forma in (str(mundo), str(mundo).replace("\\", "/"), str(mundo).replace("\\", "\\\\")):
            texto = texto.replace(forma, "<RAIZ>")
        return re.sub(r"\d+(,\d+)? m?s\b", "N s", texto.replace("\\", "/"))

    ordenes = (("--salud", "--todo"), ("--sobre", "clave del login con espacios"), ("--buscar", "validación de la clave"),
               ("--pendientes",))
    salidas = {(nombre, orden): cerebro_en(mundo, *orden) for nombre, mundo in mundos.items() for orden in ordenes}
    distintas = [(nombre, orden[0]) for orden in ordenes for nombre in ("larga", "crlf")
                 if (salidas[(nombre, orden)][0], normal(salidas[(nombre, orden)][1], mundos[nombre]))
                 != (salidas[("corta", orden)][0], normal(salidas[("corta", orden)][1], mundos["corta"]))]
    contestaron = all(c == 0 for c, _ in salidas.values()) and "notas revisadas" in salidas[("corta", ordenes[0])][1] \
        and "arreglo-login.md" in salidas[("corta", ordenes[1])][1]
    probar("la misma memoria da el mismo médico, la misma búsqueda, el mismo «sobre» y los mismos pendientes en una "
           "carpeta con espacios y eñes en la ruta, y con todos sus archivos en CRLF (la clase del error de Mac y Linux, "
           "que dependía del largo de la ruta)", contestaron and not distintas,
           (distintas, [s[1][-200:] for s in salidas.values() if s[0]][:2]))


def revisar_codificaciones(t):
    seccion("Notas guardadas en UTF-16 o con un byte roto")
    mundo = t / "codificaciones"
    memoria = mundo / "memoria"
    memoria.mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    (memoria / "MEMORY.md").write_text("# Memoria\n\n- [Riego](riego-utf16.md) — el riego\n- [Poda](poda-rota.md) — la poda\n"
                                       "- [Año viejo](viejo-cp1252.md) — una nota vieja\n", encoding="utf-8", newline="\n")
    (memoria / "riego-utf16.md").write_text(frontmatter("riego-utf16", "Cuándo se riega el invernadero", "project")
                                            + "El riego del invernadero arranca a las 06:15.\n", encoding="utf-16")
    (memoria / "poda-rota.md").write_bytes(
        (frontmatter("poda-rota", "La poda de los limoneros", "project") + "La poda de los limoneros se hace en invierno, "
         "después de la cosecha.\nLa configuración de la tijera va con eñe y con tildes.\n").encode("utf-8") + b"Fin \xe9.\n")
    (memoria / "viejo-cp1252.md").write_bytes((frontmatter("viejo-cp1252", "Una nota vieja del vivero", "project")
                                               + "El año nuevo se festeja en el galpón.\n").encode("cp1252"))
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]], "memoria": True,
         "foco": True}]}), encoding="utf-8")
    codigo, salud = cerebro_en(mundo, "--salud", "--todo")
    _, buscado = cerebro_en(mundo, "--buscar", "configuración de la tijera")
    _, riego = cerebro_en(mundo, "--sobre", "riego del invernadero")
    renglones = salud.splitlines()
    de_cada = {nombre: [r for r in renglones if nombre in r] for nombre in ("riego-utf16.md", "poda-rota.md", "viejo-cp1252.md")}
    probar("una nota en UTF-16 (el Bloc de notas con «Unicode», o > en PowerShell 5.1) se lee bien y --salud avisa que no "
           "está en UTF-8; antes entraba como basura y el médico decía, en falso, que no tenía frontmatter",
           codigo == 0 and any(r.startswith("AVISO") and "está guardada en UTF-16" in r for r in de_cada["riego-utf16.md"])
           and not any("frontmatter" in r for r in de_cada["riego-utf16.md"]) and "riego-utf16.md" in riego,
           (de_cada["riego-utf16.md"], riego[-300:]))
    probar("una nota en UTF-8 con un solo byte roto se lee como UTF-8 (las tildes quedan bien y la búsqueda la encuentra) y "
           "--salud dice cuántas letras rotas tiene y en qué renglón; una nota vieja en cp1252 se sigue leyendo sin aviso",
           any(r.startswith("AVISO") and "tiene 1 letra rota" in r and "renglón 11" in r for r in de_cada["poda-rota.md"])
           and "poda-rota.md" in buscado and not any("AVISO" in r and "UTF" in r for r in de_cada["viejo-cp1252.md"]),
           (de_cada, buscado[-300:]))


def revisar_raices_sin_alias(t):
    seccion("Dos carpetas de una fuente sin alias")
    mundo = t / "sin-alias"
    for carpeta, nombre in (("uno", "README.md"), ("dos", "README.md"), ("tres/b", "c.md"), ("cuatro", "c.md")):
        (mundo / carpeta).mkdir(parents=True)
        (mundo / carpeta / nombre).write_text(f"# Lo de {carpeta}\n\nUna nota de {carpeta}.\n", encoding="utf-8")
    (mundo / "en-vivo").mkdir()
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "docs", "nombre": "Documentos", "raices": [[str(mundo / "uno"), False, ""], [str(mundo / "dos"), False, ""]]},
        {"id": "otra", "nombre": "Otra", "raices": [[str(mundo / "tres"), True, "a"], [str(mundo / "cuatro"), False, "a/b"]]}]}),
        encoding="utf-8")
    codigo, salida = cerebro_en(mundo, "--salida", str(mundo / "mapa.html"), "--json", str(mundo / "mapa.json"))
    datos = json.loads((mundo / "mapa.json").read_text(encoding="utf-8")) if codigo == 0 else {}
    ids = sorted(n["id"] for n in datos.get("nodos", []) if n["id"].startswith("docs:"))
    raices = configuracion.armar({"fuentes": [{"id": "x", "raices": [["a/notas", False, ""], ["b/notas", False, ""],
                                                                    ["c", False, "notas"]]}]}, t)["fuentes"][0]["raices"]
    probar("dos carpetas de una fuente sin alias, con un archivo que se llama igual (dos README.md, o el MEMORY.md de dos "
           "memorias), se ven las dos en el mapa: la segunda toma de alias el nombre de su carpeta, sin pisar uno ya "
           "puesto (antes la segunda desaparecía sin aviso)",
           ids == ["docs:README.md", "docs:dos/README.md"] and [r[2] for r in raices] == ["", "notas-2", "notas"],
           (codigo, ids, raices, salida[-300:]))
    _, salud = cerebro_en(mundo, "--salud")
    renglon = next((r for r in salud.splitlines() if "mismo nombre" in r), "")
    probar("si dos notas igual terminan con el mismo nombre en el mapa, --salud avisa cuál quedó afuera y qué hacer",
           renglon.startswith("AVISO") and str(mundo / "cuatro" / "c.md") in renglon and "alias" in renglon,
           renglon or salud[-400:])


def revisar_carpeta_sin_permiso(t):
    seccion("Una carpeta sin permiso de lectura")
    if os.name != "nt" and getattr(os, "geteuid", lambda: 1)() == 0:
        saltear("carpeta sin permiso: como root se lee todo, salteado")
        return
    mundo = t / "sin-permiso"
    abierta, cerrada, honda = mundo / "abierta", mundo / "cerrada", mundo / "honda"
    for carpeta in (abierta, cerrada, honda / "adentro"):
        carpeta.mkdir(parents=True)
        (carpeta / "nota.md").write_text("# Nota\n\nEl riego del vivero.\n", encoding="utf-8")
    (mundo / "en-vivo").mkdir()
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "abierta", "raices": [[str(abierta), False, ""]]}, {"id": "cerrada", "raices": [[str(cerrada), False, ""]]},
        {"id": "honda", "raices": [[str(honda), True, ""]]}]}), encoding="utf-8")
    cerradas = (cerrada, honda / "adentro")

    def permiso(carpeta, cerrar):
        if os.name == "nt":
            subprocess.run(["icacls", str(carpeta)] + (["/deny", "*S-1-1-0:(RD)"] if cerrar else ["/remove:d", "*S-1-1-0"]),
                           capture_output=True, timeout=60)
        else:
            os.chmod(carpeta, 0 if cerrar else 0o700)

    for carpeta in cerradas:
        permiso(carpeta, True)
    try:
        codigo, salud = cerebro_en(mundo, "--salud")
    finally:
        for carpeta in cerradas:
            permiso(carpeta, False)
    renglones = [r for r in salud.splitlines() if r.startswith("AVISO   No pude entrar")]
    probar("una carpeta sin permiso de lectura no tumba el mapa (antes, --salud salía con un error de Python en inglés sin "
           "revisar nada) ni se saltea callada adentro de una recursiva: --salud nombra cada una y sigue con lo demás",
           codigo == 0 and "Traceback" not in salud and len(renglones) == 2
           and any(f"a {cerrada} (" in r for r in renglones) and any(f"a {honda / 'adentro'} (" in r for r in renglones)
           and all("no tengo permiso" in r for r in renglones), (codigo, renglones, salud[-500:]))


def revisar_fecha_rara(t):
    seccion("Una nota con una fecha de archivo rara")
    import datetime
    mundo = t / "fecha-rara"
    notas = mundo / "notas"
    notas.mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    for nombre in ("vieja", "lejana", "normal"):
        (notas / f"{nombre}.md").write_text(f"# La {nombre}\n\nEl riego del vivero.\n", encoding="utf-8")
    for nombre, fecha in (("vieja", (1960, 1, 1)), ("lejana", (3001, 6, 1))):
        cuando = (datetime.datetime(*fecha) - datetime.datetime(1970, 1, 1)).total_seconds()
        os.utime(notas / f"{nombre}.md", (cuando, cuando))
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "notas", "raices": [[str(notas), False, ""]]}]}), encoding="utf-8")
    codigo, salud = cerebro_en(mundo, "--salud")
    armado, _ = cerebro_en(mundo, "--salida", str(mundo / "mapa.html"), "--json", str(mundo / "mapa.json"))
    datos = json.loads((mundo / "mapa.json").read_text(encoding="utf-8")) if armado == 0 else {}
    avisadas = sorted(Path(r.split(" tiene una fecha")[0][8:]).name for r in salud.splitlines()
                      if r.startswith("AVISO") and "fecha de archivo que no se puede leer" in r)
    probar("una nota con la fecha de archivo de antes de 1970 o del año 3001 (de un .zip o de un disco con la fecha mal) no "
           "tumba --salud ni el armado del mapa (antes, «OSError: Invalid argument» sin revisar nada); en Windows, "
           "donde esas fechas no se pueden leer, --salud las nombra",
           codigo == 0 and armado == 0 and "Traceback" not in salud and len(datos.get("nodos", [])) == 3
           and (avisadas == ["lejana.md", "vieja.md"] if os.name == "nt" else True), (codigo, armado, avisadas, salud[-400:]))


def revisar_escritura_segura(t):
    seccion("Escribir una nota sin perderla ni romper sus enlaces")
    import archivos
    carpeta = t / "escritura-segura"
    carpeta.mkdir()
    real, duro = carpeta / "real.md", carpeta / "duro.md"
    real.write_text("lo viejo\n", encoding="utf-8")
    os.link(real, duro)
    forzados = []
    fsync = archivos.os.fsync
    archivos.os.fsync = lambda fd: forzados.append(fd) or fsync(fd)
    try:
        archivos.escribir_atomico(duro, "lo nuevo\n")
    finally:
        archivos.os.fsync = fsync
    probar("escribir en una nota que es un enlace duro de otra cambia las dos (antes se separaban y la otra quedaba con lo "
           "viejo), y lo escrito se fuerza al disco antes de dar el cambio por hecho",
           real.read_text(encoding="utf-8") == "lo nuevo\n" and os.stat(real).st_nlink == 2 and len(forzados) == 1,
           (real.read_text(encoding="utf-8"), os.stat(real).st_nlink, forzados))
    destino, enlace = carpeta / "destino.md", carpeta / "enlace.md"
    destino.write_text("lo viejo\n", encoding="utf-8")
    try:
        os.symlink(destino, enlace)
    except (OSError, NotImplementedError):
        saltear("escribir en un enlace simbólico: esta PC no deja crearlos sin permiso, salteado")
        return
    archivos.escribir_atomico(enlace, "lo nuevo\n")
    probar("escribir en un enlace simbólico escribe en su destino y el enlace sigue siendo un enlace (antes quedaba un "
           "archivo común y el destino con lo viejo)",
           enlace.is_symlink() and destino.read_text(encoding="utf-8") == "lo nuevo\n",
           (enlace.is_symlink(), destino.read_text(encoding="utf-8")))


def revisar_tope_de_procesos(t):
    seccion("El tope de tiempo de git y de los otros programas que se llaman")
    import ast
    import donde
    carpeta = t / "tope-de-procesos"
    carpeta.mkdir()
    lanzador, pid = carpeta / "lanzador.py", carpeta / "nieto.pid"
    lanzador.write_text("import subprocess, sys, time\n"
                        "nieto = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
                        "open(sys.argv[1], 'w').write(str(nieto.pid))\n"
                        "time.sleep(30)\n", encoding="utf-8")
    cortado, segundos = None, None
    comienzo = time.perf_counter()
    try:
        procesos = importlib.import_module("procesos")
        procesos.correr([sys.executable, str(lanzador), str(pid)], timeout=1.5, capture_output=True)
    except subprocess.TimeoutExpired:
        cortado = True
    except ImportError:
        cortado = False
    segundos = time.perf_counter() - comienzo
    time.sleep(0.3)
    vivo = pid.is_file() and donde.proceso_vivo(int(pid.read_text() or 0))
    probar("un programa que arranca otro (como el git.exe de Git\\cmd, que es un lanzador) se corta a tiempo y no deja "
           "vivo al que arrancó (antes, en Windows, el tope de 4 s esperaba hasta que el otro terminara)",
           cortado and segundos < 10 and not vivo, (cortado, round(segundos, 1), vivo))
    sueltos = []
    for ruta in sorted(CARPETA.glob("*.py")):
        if ruta.name == "procesos.py":
            continue
        for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
            if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute) and nodo.func.attr == "run"
                    and isinstance(nodo.func.value, ast.Name) and nodo.func.value.id == "subprocess"
                    and any(k.arg == "timeout" for k in nodo.keywords)):
                sueltos.append(f"{ruta.name}:{nodo.lineno}")
    probar("ningún módulo del programa llama a otro programa con tope sin pasar por procesos.correr (git del médico y "
           "del historial, la pasada con Claude y el armado del servidor)", not sueltos, sueltos)


def revisar_copias_de_conflicto(t):
    seccion("Copias de conflicto que deja la sincronización")
    mundo = t / "conflictos"
    memoria, boveda = mundo / "memoria", mundo / "boveda"
    (boveda / ".obsidian").mkdir(parents=True)
    memoria.mkdir()
    (mundo / "en-vivo").mkdir()

    def escribir(ruta, texto):
        ruta.write_text(texto, encoding="utf-8", newline="\n")
    tareas = frontmatter("tareas", "Lo que hay que hacer en el vivero esta semana", "project") + "# Tareas\n\nRegar los canteros.\n"
    escribir(memoria / "MEMORY.md", "# Memoria\n\n- [Tareas](tareas.md) — lo que hay que hacer en el vivero\n"
             "- [Riego](riego.md) — cómo se riega\n")
    escribir(memoria / "tareas.md", tareas)
    escribir(memoria / "tareas (Conflicted copy PC-Ana 202610181234).md", tareas.replace("los canteros", "todo"))
    escribir(memoria / "riego.md", frontmatter("riego", "Cómo se riega el vivero y cada cuánto", "project")
             + "# Riego\n\nAntes de regar, ver [[tareas]].\n")
    escribir(boveda / "Notas.md", "# Notas\n\nDel vivero.\n")
    escribir(boveda / "Notas.sync-conflict-20261018-123456-ABCDEFG.md", "# Notas\n\nDel vivero, otra versión.\n")
    escribir(boveda / "Plan (Ana's conflicted copy 2026-10-18).md", "# Plan\n\nSin la original al lado.\n")
    escribir(mundo / "config.json", json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]], "memoria": True,
         "foco": True},
        {"id": "boveda", "nombre": "Bóveda", "color": "#228BE6", "raices": [[str(boveda), True, ""]]}]},
        ensure_ascii=False))
    codigo, salida = cerebro_en(mundo, "--salida", str(mundo / "mapa.html"), "--json", str(mundo / "mapa.json"))
    datos = json.loads((mundo / "mapa.json").read_text(encoding="utf-8")) if codigo == 0 else {}
    nombre = {n["id"]: Path(n["ruta"]).name for n in datos.get("nodos", [])}
    destinos = [nombre.get(a["a"]) for a in datos.get("aristas", []) if a["clase"] == "wiki" and nombre.get(a["de"]) == "riego.md"]
    probar("en la memoria, [[tareas]] lleva a tareas.md aunque su copia de conflicto (con el mismo name:) aparezca antes: "
           "manda el nombre del archivo, como en Obsidian", destinos == ["tareas.md"], (destinos, salida[-300:]))
    salud = cerebro_en(mundo, "--salud", "--todo")[1]
    copias = sorted(r.split(" — ")[0].split("\\")[-1].split("/")[-1] for r in salud.splitlines() if "copia de conflicto" in r)
    probar("el médico avisa cada copia de conflicto que tiene al lado su nota original (Obsidian Sync, Dropbox, "
           "Syncthing) y dice cuál es la buena; una que no tiene original no",
           copias == ["Notas.sync-conflict-20261018-123456-ABCDEFG.md", "tareas (Conflicted copy PC-Ana 202610181234).md"]
           and all(r.startswith("AVISO ") for r in salud.splitlines() if "copia de conflicto" in r)
           and "Juntar en tareas.md" in salud, (copias, salud[-900:]))


def revisar_rutas_temporales(t):
    seccion("Rutas de una carpeta temporal que ya no existen")
    mundo = t / "rutas-temporales"
    memoria = mundo / "memoria"
    memoria.mkdir(parents=True)
    sesion = Path(tempfile.gettempdir()) / "claude" / "D--Vivero" / "0a1b2c3d-sesion-vieja" / "scratchpad" / "auditoria"
    sistema = Path(tempfile.gettempdir()) / "vivero-copia-vieja"
    (memoria / "auditoria.md").write_text(
        frontmatter("auditoria", "Auditoría del riego del vivero", "project") + "# Auditoría\n\n"
        + f"- El informe de eficiencia quedó en `{sesion / 'eficiencia.md'}`.\n\n"
        + f"- El de experiencia quedó en `{sesion / 'experiencia.md'}` (era temporal).\n\n"
        + f"- La copia de los sensores quedó en `{sistema / 'sensores.md'}`.\n\n"
        + f"- El plan del riego está en `{memoria / 'plan-viejo.md'}`.\n\n"
        + f"- Las notas sueltas de hoy están en `{mundo / 'suelta' / 'notas.md'}`.\n", encoding="utf-8", newline="\n")
    (memoria / "MEMORY.md").write_text("# Memoria\n\n- [Auditoría](auditoria.md) — del riego\n", encoding="utf-8",
                                       newline="\n")
    (mundo / "suelta").mkdir()
    (mundo / "suelta" / "notas.md").write_text("# Notas sueltas\n", encoding="utf-8")
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "fuentes": [
        {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]],
         "memoria": True, "foco": True}]}, ensure_ascii=False), encoding="utf-8", newline="\n")
    salud = cerebro_en(mundo, "--salud", "--todo")[1]

    def del_renglon(nombre):
        return next((r for r in salud.splitlines() if nombre in r and "que no existe" in r), "")
    sesion_vieja, del_sistema = del_renglon("eficiencia.md"), del_renglon("sensores.md")
    probar("una ruta que ya no existe en la carpeta temporal de una sesión de Claude o del sistema queda «para revisar» "
           "(así no llega a los chats como problema y se puede descartar), dice que esa carpeta se borra sola y cómo "
           "callarla; si el renglón ya dice que era temporal, no avisa",
           sesion_vieja.startswith("REVISAR ") and "carpeta temporal de una sesión de Claude" in sesion_vieja
           and "que era temporal" in sesion_vieja and del_sistema.startswith("REVISAR ")
           and "carpeta temporal del sistema" in del_sistema and not del_renglon("experiencia.md"),
           (sesion_vieja, del_sistema, salud[-900:]))
    probar("una ruta que falta en una carpeta de la configuración sigue siendo un aviso, aunque esa carpeta esté dentro "
           "de la temporal; y a una que existe en la temporal no le propone sumarla a las fuentes",
           del_renglon("plan-viejo.md").startswith("AVISO ")
           and not [r for r in salud.splitlines() if "notas.md" in r and "fuentes" in r], salud[-900:])
    import medico
    texto = ("- La copia quedó en `/x/a.md`.\n\n- Lo de las rutas temporales se borró.\n"
             "- Y la de `/x/b.md`, que\n  se borró ayer.\n- Otra: `/x/c.md`.\n| fila | se movió |\n")
    tramos = [medico.alrededor(texto, texto.index(f"/x/{n}.md"), 80) for n in "abc"]
    probar("lo que dice el ítem siguiente de la lista, otro párrafo o una fila de tabla no calla el aviso de una ruta "
           "(«se borró», «temporal»), y lo que sigue en el mismo ítem, aunque pase al renglón de abajo, sí (en Linux y "
           "Mac, con rutas cortas, el ítem de abajo entraba en las 80 letras y callaba el aviso)",
           "temporal" not in tramos[0] and "se borró ayer" in tramos[1] and "se movió" not in tramos[2], tramos)


NOTA_CON_RED = ("Enlaces: [a](//red.invalid/c/a.md), [b](\\\\red.invalid\\c\\b.md), [[//red.invalid/c/w]], "
                "[d](%2F%2Fred.invalid%2Fc%2Fd.md), [e](<//red.invalid/c/e.md>), [f](\\\\?\\UNC\\red.invalid\\c\\f.md).\n\n"
                "Código: `\\\\red.invalid\\c\\x.cs:10`, `//red.invalid/c/y.py:3`, \\\\red.invalid\\c\\z.md y "
                "`\\\\?\\UNC\\red.invalid\\c\\q.md`.\n")


@contextlib.contextmanager
def espia_de_red(tocadas):
    def de_red(ruta):
        try:
            texto = os.fspath(ruta)
        except TypeError:
            return False
        if isinstance(texto, bytes):
            texto = texto.decode(errors="replace")
        return texto.strip().replace("/", "\\").startswith("\\\\")

    def envolver(modulo, nombre, respuesta):
        original = getattr(modulo, nombre)

        def espia(ruta, *a, **k):
            if not de_red(ruta):
                return original(ruta, *a, **k)
            tocadas.append(f"{nombre}({os.fspath(ruta)})")
            if respuesta is OSError:
                raise FileNotFoundError(ruta)
            return respuesta(ruta) if callable(respuesta) else respuesta

        return modulo, nombre, original, espia

    cambios = [envolver(os.path, n, False) for n in ("exists", "isfile", "isdir", "lexists", "islink")]
    cambios += [envolver(os.path, n, 0) for n in ("getmtime", "getsize")]
    cambios += [envolver(os.path, "realpath", os.fspath), envolver(os, "listdir", lambda r: [])]
    cambios += [envolver(m, n, OSError) for m, n in ((os, "stat"), (os, "lstat"), (os, "scandir"), (builtins, "open"))]
    for modulo, nombre, _, espia in cambios:
        setattr(modulo, nombre, espia)
    try:
        yield
    finally:
        for modulo, nombre, original, _ in cambios:
            setattr(modulo, nombre, original)


def revisar_semillas(t):
    seccion("La misma respuesta con cualquier semilla de Python (cada hook arranca con otra)")
    sin_tiempos = lambda texto: re.sub(r"\d+(?:,\d+)? (?:ms|s)\b", "", texto)
    distintas = []
    for opciones in (["--sobre", "validación de la clave del login"], ["--salud", "--todo"],
                     ["--parecidas", "La validación de la clave fallaba con espacios al final"]):
        salidas = {sin_tiempos(correr([str(CARPETA / "cerebro.py"), *opciones], espera=300, PYTHONHASHSEED=s).stdout)
                   for s in ("1", "2", "3")}
        if len(salidas) != 1:
            distintas.append(opciones[0])
    probar("--sobre, --salud y --parecidas dan lo mismo con tres semillas distintas (un empate decidido por el orden "
           "de un set cambiaba la pista de un pedido a otro)", not distintas, distintas)


def revisar_candado_ocupado(t):
    seccion("Un evento con el registro tomado por otro (CandadoOcupado)")
    import archivos
    if not archivos.hay_candados():
        saltear("el candado del registro: este sistema no tiene candados de archivo, salteado")
        return
    registro = Path(hook_evento.REGISTRO)
    antes = registro.read_bytes() if registro.exists() else b""
    evento = lambda n: {"t": round(time.time(), 3), "s": "candado1", "e": "post", "h": "Read", "k": "leer", "n": n}
    tomado = archivos.tomar_candado(hook_evento.CANDADO)
    try:
        perdidos = []
        for n in (1, 2):
            try:
                hook_evento.escribir_evento(evento(n), 0)
            except hook_evento.CandadoOcupado:
                perdidos.append(n)
        en_espera = sorted(os.listdir(hook_evento.PENDIENTES))
        sin_tocar = (registro.read_bytes() if registro.exists() else b"") == antes
    finally:
        archivos.soltar_candado(tomado)
    hook_evento.escribir_evento(evento(3))
    nuevos = [json.loads(r) for r in (registro.read_bytes()[len(antes):]).decode("utf-8").splitlines() if r.strip()]
    quedan = os.listdir(hook_evento.PENDIENTES)
    probar("si otro tiene el registro, el evento queda en en-vivo\\pendientes (antes se perdía) y el siguiente que entra "
           "los suma en orden antes del suyo y los borra",
           not perdidos and len(en_espera) == 2 and all(n.endswith(".jsonl") for n in en_espera) and sin_tocar
           and [e["n"] for e in nuevos] == [1, 2, 3] and not quedan, (perdidos, en_espera, nuevos, quedan))
    tope, hook_evento.TOPE_PENDIENTES = hook_evento.TOPE_PENDIENTES, 1
    tomado = archivos.tomar_candado(hook_evento.CANDADO)
    try:
        hook_evento.escribir_evento(evento(4), 0)
        try:
            hook_evento.escribir_evento(evento(5), 0)
            lleno = False
        except hook_evento.CandadoOcupado:
            lleno = True
    finally:
        archivos.soltar_candado(tomado)
        hook_evento.TOPE_PENDIENTES = tope
    hook_evento.escribir_evento(evento(6))
    probar("si quedaron demasiados pendientes (el candado trabado para siempre), deja de juntarlos y avisa como antes",
           lleno and not os.listdir(hook_evento.PENDIENTES), lleno)


def revisar_procesos_de_fondo(t):
    seccion("Procesos de fondo (rearmar el índice, la pasada de cada noche)")
    import procesos
    marca = t / "de-fondo.txt"
    proceso = procesos.lanzar_de_fondo([sys.executable, "-c", f"open({str(marca)!r}, 'w').write('corrio')"])
    proceso.wait(60)
    con_detached = sorted(p.name for p in CARPETA.glob("*.py") if "DETACHED_PROCESS" in p.read_text(encoding="utf-8"))
    probar("un proceso de fondo corre sin consola visible y nada lo lanza con DETACHED_PROCESS (en Windows 11 con "
           "Terminal, un hijo de un proceso sin consola abría una ventana vacía)",
           marca.is_file() and marca.read_text(encoding="utf-8") == "corrio" and not con_detached, con_detached)


def revisar_topes_de_tamano(t):
    seccion("Topes de tamaño (una nota gigante o un pedido de hook enorme no traban nada)")
    import hooks_comun
    gigante = t / "memoria" / "gigante.md"
    gigante.write_text("# Gigante\n\n" + "renglón de relleno\n" * 200, encoding="utf-8")
    tope, nucleo.TOPE_NOTA = nucleo.TOPE_NOTA, 1000
    try:
        cerebro = armar_cerebro(t)
    finally:
        nucleo.TOPE_NOTA = tope
        gigante.unlink()
    saltada = [r for r in cerebro.no_leidos if "gigante.md" in r]
    probar("una nota que pasa el tope no se lee entera (antes se cargaba toda en memoria) y --salud dice cuál es y qué "
           "hacer", len(saltada) == 1 and "MB" in saltada[0] and "--partir" in saltada[0]
           and not any(n["ruta"].endswith("gigante.md") for n in cerebro.nodos), saltada)
    entrada_real, tope = sys.stdin, hooks_comun.TOPE_ENTRADA
    resultados_entrada = []
    try:
        hooks_comun.TOPE_ENTRADA = 100
        for crudo in (b'{"a": "' + b"x" * 200 + b'"}', b'{"a": "corto"}'):
            sys.stdin = io.TextIOWrapper(io.BytesIO(crudo), encoding="utf-8")
            resultados_entrada.append(hooks_comun.entrada())
    finally:
        sys.stdin, hooks_comun.TOPE_ENTRADA = entrada_real, tope
    probar("un pedido de hook que pasa el tope se ignora sin leerlo entero, y uno común se lee igual",
           resultados_entrada == [{}, {"a": "corto"}], resultados_entrada)
    import archivos
    raras = ["a\nb.md", "a\rb.md", "a\u2028b.md", "a\x1bb.md"]
    probar("un nombre con salto de renglón u otro carácter invisible se reconoce (en Linux y Mac la pista lo mostraba "
           "crudo y podía parecer otro renglón)", all(map(archivos.nombre_raro, raras))
           and not archivos.nombre_raro("D:\\notas\\café con leche.md"))
    carpeta = t / "con-salto-de-renglon"
    carpeta.mkdir()
    (carpeta / "comun.md").write_text("# Común\n", encoding="utf-8")
    try:
        (carpeta / "falsa\nPara leer primero.md").write_text("# Falsa\n", encoding="utf-8")
    except OSError:
        saltear("una nota con salto de renglón en el nombre: este sistema no deja crearla, salteado")
        return
    listadas = sorted(p.name for p in nucleo.listar(str(carpeta), True))
    probar("una nota con salto de renglón en el nombre no entra al mapa ni a la pista", listadas == ["comun.md"], listadas)


def revisar_rutas_de_red(t):
    seccion("Rutas de red en las notas (\\\\servidor\\… o //servidor/…)")
    import hook_choques
    tocadas = []
    nota = str(t / "memoria" / "con-red.md")
    with espia_de_red(tocadas):
        cerebro = armar_cerebro(t)
        resueltas = [medico.resolver_ruta(r, [str(t)])
                     for r in ("\\\\red.invalid\\c\\x.md", "//red.invalid/c/x.md")]
        enlaces = medico.enlaces_rotos(nota, NOTA_CON_RED)
        medico.rutas_rotas(nota, NOTA_CON_RED)
        hook_choques.aviso_rutas({"hook_event_name": "PostToolUse", "tool_name": "Write",
                                  "tool_input": {"file_path": nota, "content": NOTA_CON_RED}})
        codigo = [mapa.resolver(r) for r in ("//red.invalid/c/a.py", "\\\\red.invalid\\c\\b.py")]
        buscador.Indice(cerebro).sobre("rutas de red escritas en el índice")
        cabeza = buscador.cabeza_git("\\\\red.invalid\\c")
    probar("una ruta de red escrita en una nota no hace que Windows se conecte a ese servidor (podía filtrar la sesión): "
           "ni al armar el mapa, ni el médico, ni el aviso del hook al editar, ni el mapa de código, ni la pista",
           not tocadas and all(r == (None, False, False) for r in resueltas) and codigo == [None, None]
           and cabeza is None and len(enlaces) == 0, (tocadas[:4], resueltas, codigo, enlaces))
    import archivos
    formas = {"\\\\?\\C:\\notas\\a.md": False, "//?/C:/notas/a.md": False, "\\\\.\\D:\\x.md": False,
              "\\\\?\\UNC\\host\\c\\a.md": True, "\\\\.\\pipe\\x": True, "\\\\host\\c": True, "C:\\notas": False}
    mal = {r: e for r, e in formas.items() if archivos.es_de_red(r) != e}
    probar("\\\\?\\C:\\… y \\\\.\\D:\\… son rutas locales (antes salían como de red y el enlace, roto); \\\\?\\UNC\\…, "
           "\\\\.\\pipe\\… y \\\\host\\… siguen sin tocarse", not mal, mal)
    delicadas = t / "raiz-con-delicadas"
    for relativa in ("riego.md", ".env.md", "id_rsa.md", ".ssh/claves.md", "docs/.aws/zonas.md", "docs/sensor.md"):
        (delicadas / relativa).parent.mkdir(parents=True, exist_ok=True)
        (delicadas / relativa).write_text("# Nota\nCONTENIDO_DELICADO hunter2\n", encoding="utf-8")
    recursivas = sorted(p.relative_to(delicadas).as_posix() for p in nucleo.listar(str(delicadas), True))
    sueltas = sorted(p.name for p in nucleo.listar(str(delicadas), False))
    afuera = sorted(Path(r).relative_to(delicadas).as_posix() for r in nucleo.delicadas.values()
                    if Path(r).is_relative_to(delicadas))
    probar("una nota con nombre o carpeta de claves (.env.md, id_rsa.md, .ssh, .aws) no entra al mapa, a la pista ni al "
           "conector (antes entraba con todo su texto), y queda contada para --salud",
           recursivas == ["docs/sensor.md", "riego.md"] and sueltas == ["riego.md"]
           and afuera == [".env.md", ".ssh", "docs/.aws", "id_rsa.md"], (recursivas, sueltas, afuera))
    raiz = t / "raiz-con-enlaces"
    (raiz / "sub").mkdir(parents=True)
    afuera = t / "afuera-secreto.md"
    afuera.write_text("# Secreto\n", encoding="utf-8")
    (raiz / "propia.md").write_text("# Propia\n", encoding="utf-8")
    if os.name == "nt":
        listadas = [p.name for p in nucleo.listar(str(raiz), True)]
        probar("una nota común de la carpeta se lista (enlaces simbólicos y FIFO: se prueban en Linux)",
               listadas == ["propia.md"], listadas)
        return
    os.symlink(afuera, raiz / "enlace.md")
    os.symlink(afuera, raiz / "sub" / "enlace.md")
    os.mkfifo(raiz / "sub" / "fifo.md")
    listadas = sorted(str(p.relative_to(raiz)) for recursivo in (False, True) for p in nucleo.listar(str(raiz), recursivo))
    probar("un enlace simbólico a un archivo de fuera de la carpeta no entra al mapa, y un FIFO no lo cuelga",
           listadas == ["propia.md", "propia.md"], listadas)
