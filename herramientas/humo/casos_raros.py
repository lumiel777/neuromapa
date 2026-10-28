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


def revisar_rutas_de_red(t):
    seccion("Rutas de red en las notas (\\\\servidor\\… o //servidor/…)")
    tocadas = []
    original = os.path.exists

    def espia(ruta, *a, **k):
        if str(ruta).replace("/", "\\").startswith("\\\\"):
            tocadas.append(str(ruta))
            return False
        return original(ruta, *a, **k)

    os.path.exists = espia
    try:
        armar_cerebro(t)
        resueltas = [medico.resolver_ruta(r, [str(t)], espia)
                     for r in ("\\\\red.invalid\\c\\x.md", "//red.invalid/c/x.md")]
    finally:
        os.path.exists = original
    probar("una ruta de red escrita en una nota no hace que Windows se conecte a ese servidor (podía filtrar la sesión)",
           not tocadas and all(r == (None, False, False) for r in resueltas), (tocadas[:3], resueltas))
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
