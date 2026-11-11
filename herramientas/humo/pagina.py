from humo.base import *


def generar_pagina(t):
    seccion("Página (cerebro.py arma el cerebro inventado)")
    viejo = sys.argv
    sys.argv = ["cerebro.py", "--json", str(t / "cerebro.json"), "--plantilla", str(CARPETA / "plantilla.html")]
    salida = io.StringIO()
    try:
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(salida):
            codigo = nucleo.main()
    except Exception as error:
        codigo = f"{type(error).__name__}: {error}"
    finally:
        sys.argv = viejo
    probar("cerebro.py termina bien", codigo == 0, f"{codigo}\n{salida.getvalue()[-800:]}")
    html = (t / "cerebro.html").read_text(encoding="utf-8") if (t / "cerebro.html").exists() else ""
    probar("sin --salida, la página queda junto al config y lleva los datos, no el marcador",
           "window.CEREBRO = " in html and nucleo.MARCADOR not in html)
    try:
        datos = json.loads((t / "cerebro.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        datos = {"error": str(error)}
    return datos, html


def revisar_cerebro(datos):
    seccion("Cerebro (notas, grupos y conexiones)")
    nombres = sorted(Path(n["ruta"]).name for n in datos.get("nodos", []))
    esperadas = sorted(["MEMORY.md", "perfil-ana.md", "regla-sin-comentarios.md", "arreglo-login.md",
                        "arreglo-login-bis.md", "suelta.md", "CLAUDE.md", "PLAN-DEMO.md"])
    probar("junta las 8 notas inventadas, ni una más", nombres == esperadas, nombres)
    grupos = {g["id"]: g["cantidad"] for g in datos.get("grupos", [])}
    probar("6 en la memoria, 1 CLAUDE.md y 1 plan", grupos == {"memoria": 6, "instrucciones": 1, "cerebro-ideas": 1}, grupos)
    de_proyecto = {g["id"]: g["cantidad"] for g in datos.get("gruposDeProyecto", [])}
    sueltos = [n["id"] for n in datos.get("nodos", []) if n.get("proyecto") not in de_proyecto]
    probar("la página también lleva las notas agrupadas por proyecto: cada nota tiene el suyo, las cuentas cierran y hay un "
           "grupo para las que no son de ninguno",
           len(de_proyecto) > 1 and not sueltos and sum(de_proyecto.values()) == len(datos.get("nodos", []))
           and all(g.get("nombre") and re.fullmatch(r"#[0-9A-Fa-f]{6}", g.get("color") or "")
                   for g in datos.get("gruposDeProyecto", [])), (de_proyecto, sueltos))
    por_id = {n["id"]: Path(n["ruta"]).name for n in datos.get("nodos", [])}
    aristas = {(por_id.get(a["de"]), por_id.get(a["a"]), a["clase"]) for a in datos.get("aristas", [])}
    indice = {a for de, a, clase in aristas if de == "MEMORY.md" and clase == "indice"}
    probar("el índice apunta a sus 4 notas",
           indice == {"perfil-ana.md", "regla-sin-comentarios.md", "arreglo-login.md", "arreglo-login-bis.md"}, indice)
    probar("el enlace [[regla-sin-comentarios]] es una conexión wiki",
           ("arreglo-login.md", "regla-sin-comentarios.md", "wiki") in aristas, sorted(aristas, key=str))
    rotos = json.dumps(datos.get("salud", {}).get("rotos", []), ensure_ascii=False)
    probar("marca el enlace roto [[nota-que-no-existe]]", "nota-que-no-existe" in rotos, rotos)
    tipo_de = {n["id"]: n["tipo"] for n in datos.get("nodos", [])}
    solos = [por_id.get(i) for i in datos.get("salud", {}).get("huerfanos", []) if tipo_de.get(i) in ("indice", "instrucciones")]
    probar("un MEMORY.md o un CLAUDE.md nunca cuenta como nota huérfana (Claude Code los carga solo)", not solos, solos)
    renglon = "los 32 png en `d:\\demo\\diseno\\iconos\\botones\\piezas\\` y `leeme-piezas.md`"
    probar("un nombre repetido se desempata por la carpeta que nombra el mismo renglón",
           nucleo.carpeta_nombrada("d:\\demo\\diseno\\iconos\\botones", renglon)
           and not nucleo.carpeta_nombrada("d:\\demo\\diseno\\fondos\\bosque", renglon)
           and not nucleo.carpeta_nombrada("d:\\demo\\iconos\\botones", renglon.replace("\\iconos\\", "\\otrosiconos\\"))
           and not nucleo.carpeta_nombrada("d:\\demo", renglon))

    class Repetido:
        salientes, fuertes, handoff_por_numero, slugs_mencionables = {}, {}, {}, {}
        avisos, posiciones = [], []

        def recorrer_ruta(self, texto, inicio, nombre):
            return (inicio, {"x", "y"}, None) if nombre == "claude.md" else None

        def mismo_lugar(self, origen, candidatos):
            return []

        def desempatar(self, *args):
            return None

        def agregar(self, *args):
            pass

        def ambiguo(self, de, mencion, candidatos, posicion=None):
            self.avisos.append(mencion)
            self.posiciones.append(posicion)

    repetido = Repetido()
    nucleo.Cerebro.analizar_menciones(repetido, "m1", ["Leé el CLAUDE.md antes. Un CLAUDE.md o cada `CLAUDE.md` sirve; "
                                                       "your CLAUDE.md; los CLAUDE.md; va a CLAUDE.md; pilos CLAUDE.md."])
    probar("un nombre repetido dicho en general («un CLAUDE.md», «cada CLAUDE.md», «your CLAUDE.md») no es una mención "
           "ambigua; «el CLAUDE.md» o «a CLAUDE.md» sí (antes marcaba «un CLAUDE.md o un MEMORY.md» y no tenía arreglo)",
           repetido.avisos == ["CLAUDE.md", "CLAUDE.md", "CLAUDE.md"], repetido.avisos)
    repetido.avisos, repetido.posiciones = [], []
    cuerpo = "# A\n\nUn CLAUDE.md sirve.\nLeé el CLAUDE.md.\n"
    nucleo.Cerebro.analizar_menciones(repetido, "a", [cuerpo, "el CLAUDE.md"])
    en_su_renglon = types.SimpleNamespace(
        ambiguos=[{"de": "a", "mencion": "CLAUDE.md", "candidatos": ["x", "y"], "posicion": repetido.posiciones[0]}],
        por_id={"a": {"id": "a", "ruta": "/notas/a.md", "_cuerpo": cuerpo}, "x": {"ruta": "/x/CLAUDE.md"},
                "y": {"ruta": "/y/CLAUDE.md"}})
    probar("--salud marca la mención ambigua en su renglón, no en el primero donde aparece el nombre (antes, si el nombre "
           "salía antes dicho en general o dentro de una ruta de afuera, apuntaba a ese renglón, que estaba bien)",
           repetido.posiciones == [cuerpo.index("el CLAUDE") + 3, None]
           and [h["linea"] for h in medico.regla_ambiguas(en_su_renglon)] == [4], repetido.posiciones)
    cabeza = "---\nname: a\ndescription: \"ver D:\\\\x\\\\CLAUDE.md y el CLAUDE.md\"\n---\n"
    cuerpo_b = "# A\n\nCada CLAUDE.md sirve.\nLeé el CLAUDE.md.\n"
    en_la_descripcion = types.SimpleNamespace(
        ambiguos=[{"de": "a", "mencion": "CLAUDE.md", "candidatos": ["x", "y"]}],
        por_id={"a": {"id": "a", "ruta": "/notas/a.md", "_cuerpo": cuerpo_b, "_cabeza": cabeza,
                      "_desfase": cabeza.count("\n")}, "x": {"ruta": "/x/CLAUDE.md"}, "y": {"ruta": "/y/CLAUDE.md"}})
    probar("una mención ambigua en la descripción de la nota sale en el renglón de la descripción, no en el primero "
           "del cuerpo que nombra lo mismo, y salta la ruta completa de ese renglón (antes mandaba a corregir un renglón "
           "que estaba bien)",
           [h["linea"] for h in medico.regla_ambiguas(en_la_descripcion)] == [3],
           [h["linea"] for h in medico.regla_ambiguas(en_la_descripcion)])
    probar("la página recibe del config el usuario, los proyectos y el lóbulo de cada grupo",
           datos.get("usuario") == "Ana" and [p["alias"] for p in datos.get("proyectos", [])] == ["demo"]
           and {g["id"]: g.get("lobulo") for g in datos.get("grupos", [])}.get("memoria") == "temporal",
           {k: datos.get(k) for k in ("usuario", "proyectos")})


def revisar_mapa(t):
    seccion("Mapa de código (--mapa)")
    for archivo, esperados in (("muestra.js", {"sumar", "restar", "Caja"}), ("muestra.py", {"uno", "Dos"})):
        armado = mapa.armar(t / archivo)
        nombres = {b.nombre for b in armado[1]} if armado else set()
        probar(f'{archivo}: encuentra {", ".join(sorted(esperados))}', esperados <= nombres, nombres)


def buscar_chrome():
    for nombre in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    for ruta in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if os.path.isfile(ruta):
            return ruta
    return None


def abrir_en_chrome(chrome, pagina, extra=""):
    perfil = tempfile.mkdtemp(prefix="cerebro-humo-chrome-")
    try:
        r = subprocess.run([chrome, "--headless=new", "--disable-gpu", f"--user-data-dir={perfil}", "--no-first-run",
                            "--no-default-browser-check", "--use-mock-keychain", "--password-store=basic",
                            "--virtual-time-budget=6000", "--dump-dom", pagina.as_uri() + extra], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=180)
        if "<body" in r.stdout:
            return r.stdout
        motivo = f"Chrome salió con {r.returncode} sin la página: {r.stderr[-200:]}"
    except subprocess.TimeoutExpired as error:
        motivo = f"Chrome no terminó en {error.timeout:g} s"
    except (OSError, subprocess.SubprocessError) as error:
        motivo = f"no pude abrir Chrome: {str(error)[:200]}"
    finally:
        shutil.rmtree(perfil, ignore_errors=True)
    limpio = re.sub(r'["<>]', "'", motivo)
    return f"<html data-errores=\"{limpio}\"></html>"


def revisar_pagina_abierta(t, datos, html):
    seccion("La página abierta (escapes, arranque y modo anónimo en Chrome sin ventana)")
    peligroso = {"titulo": "nota con </script><img src=x onerror=alert(1)> adentro, <!-- y <script>"}
    js = nucleo.a_javascript(peligroso)
    probar("los datos que van adentro de la página no pueden cerrar el <script> (una nota con </script> la cortaba)",
           "</" not in js and "<script" not in js.lower() and "<!--" not in js and json.loads(js) == peligroso, js)
    chrome = buscar_chrome()
    if not html or chrome is None:
        saltear("sin Chrome (o sin página), salteado: no se abrió la página en un navegador")
        return
    atrapa = ("<script>addEventListener('error', e => { const r = document.documentElement; "
              "r.dataset.errores = (r.dataset.errores || '') + (e.message || 'error') + ' | '; });</script>\n")
    pagina = t / "pagina-abierta.html"
    pagina.write_text(html.replace("<script>", atrapa + "<script>", 1), encoding="utf-8", newline="\n")
    plantilla = plantilla_entera(CARPETA / "plantilla.html")
    nombres = [g.get("nombre") for g in datos.get("grupos", []) if g.get("nombre") and g.get("nombre") not in plantilla]

    def visible(dom):
        return re.sub(r"<(script|style)\b.*?</\1>", "", dom, flags=re.S)

    normal = abrir_en_chrome(chrome, pagina)
    anonima = abrir_en_chrome(chrome, pagina, "?anonimo")
    errores = [m for dom in (normal, anonima) for m in re.findall(r'data-errores="([^"]*)"', dom)]
    colgado = next((m for m in errores if m.startswith("Chrome no terminó")), None)
    if colgado and os.environ.get("CI"):
        saltear(f"en esta máquina de pruebas, {colgado}: salteado abrir la página en un navegador (en Linux y en una PC "
                "común abre en segundos)")
        return
    probar("la página arranca en un navegador sin ningún error de JavaScript (node --check solo mira la escritura)",
           "<body" in normal and not errores, errores or normal[:200])
    a_la_vista = [n for n in nombres if n in visible(normal)]
    en_anonimo = [n for n in nombres if n in visible(anonima)]
    probar("en modo anónimo la página no muestra los nombres reales de los grupos (en el modo normal sí se ven)",
           bool(a_la_vista) and not en_anonimo, (a_la_vista, en_anonimo))
    de_proyecto = [g.get("nombre") for g in datos.get("gruposDeProyecto", []) if g.get("nombre")]
    por_proyecto = abrir_en_chrome(chrome, pagina, "?color=proyectos")

    def puesto(dom):
        return re.findall(r'<button[^>]*data-color="(\w+)"[^>]*aria-pressed="true"', dom)

    def a_la_vista_en(dom):
        m = re.search(r'id="filtro-proyectos"[^>]*>(.*?)</section>', dom, flags=re.S)
        return m.group(1) if m else ""

    import html as html_modulo

    def rotulos(dom):
        return [html_modulo.unescape(r) for r in re.findall(r'<span class="filtro-nombre">([^<]*)</span>', a_la_vista_en(dom))]

    probar("la página lista los proyectos para prenderlos y apagarlos, arranca coloreada por grupos y con ?color=proyectos "
           "por proyecto, sin errores; en modo anónimo los proyectos también salen con nombres genéricos",
           len(de_proyecto) > 1 and all(n in a_la_vista_en(normal) for n in de_proyecto) and puesto(normal) == ["grupos"]
           and puesto(por_proyecto) == ["proyectos"] and not re.findall(r'data-errores="([^"]*)"', por_proyecto)
           and len(rotulos(anonima)) == len(de_proyecto) and all(re.fullmatch(r"Proyecto [A-Z]", r) for r in rotulos(anonima))
           and sorted(rotulos(normal)) == sorted(de_proyecto),
           (de_proyecto, puesto(normal), puesto(por_proyecto), rotulos(normal), rotulos(anonima)))
    ids = [n["id"] for n in datos.get("nodos", []) if n.get("id") is not None][:2]
    ahora = time.time()
    con_tablero = dict(datos, aprender=True, aprendido={"semana": {"pistas": 12, "utiles": 5, "seguidas": 7, "notas": 30}},
                       arreglados=[{"t": ahora - 60, "id": ids[0], "tipo": "huerfana"},
                                   {"t": ahora - 120, "id": ids[1], "tipo": "medico-rutaVieja"},
                                   {"t": ahora, "id": "no-existe", "tipo": "roto"}])
    tablero = t / "pagina-tablero.html"
    with contextlib.redirect_stdout(io.StringIO()):
        nucleo.escribir_pagina(con_tablero, CARPETA / "plantilla.html", tablero)
    tablero.write_text(tablero.read_text(encoding="utf-8").replace("<script>", atrapa + "<script>", 1), encoding="utf-8",
                       newline="\n")
    dom = abrir_en_chrome(chrome, tablero)

    def bloque_ahorro(dom):
        m = re.search(r'(<section[^>]*id="bloque-ahorro"[^>]*>)(.*?)</section>', dom, flags=re.S)
        return (m.group(1), html_modulo.unescape(m.group(2))) if m else ("", "")

    cabeza, cuerpo = bloque_ahorro(dom)
    cifras = re.findall(r'class="salud-num">([\d.]+)<', cuerpo)
    probar("el tablero «Lo que hizo por vos» muestra las pistas, las que sirvieron, las notas leídas y los problemas "
           "arreglados de notas que siguen en el mapa, con el nombre del problema; sin datos no aparece",
           cabeza and "hidden" not in cabeza and cifras == ["12", "5", "7", "2"] and "Huérfana" in cuerpo
           and "Ruta que ya no existe" in cuerpo and not re.findall(r'data-errores="([^"]*)"', dom)
           and "hidden" in bloque_ahorro(normal)[0],
           (cabeza, cifras, cuerpo[:300], re.findall(r'data-errores="([^"]*)"', dom), bloque_ahorro(normal)[0]))


def revisar_js(t, html):
    seccion("JavaScript de la página (node --check)")
    if shutil.which("node") is None:
        saltear("sin node en el PATH, salteado")
        return
    bloques = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
    carpeta = t / "js"
    carpeta.mkdir(exist_ok=True)
    fallas = []
    for i, codigo in enumerate(bloques, 1):
        ruta = carpeta / f"bloque{i}.js"
        ruta.write_text(codigo, encoding="utf-8", newline="\n")
        r = subprocess.run(["node", "--check", str(ruta)], capture_output=True, text=True, timeout=120)
        if r.returncode:
            fallas.append(f"{ruta.name}: {r.stderr[:300]}")
    probar(f"{len(bloques)} bloques <script>, con los datos adentro, pasan node --check", bloques and not fallas, fallas)
    lineas = [m.group(0) for m in re.finditer(r"(?m)^\s*const (?:ESCAPES|esc) = .*$", html)][:2]
    escapar = carpeta / "esc.js"
    escapar.write_text("\n".join(lineas) + "\nconsole.log(esc('<img src=x onerror=\"a\"> & \\'b\\''));\n", encoding="utf-8",
                       newline="\n")
    r = subprocess.run(["node", str(escapar)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    probar("la página escapa el HTML de títulos y textos (una nota con <img onerror> no entra como HTML)",
           r.stdout.strip() == "&lt;img src=x onerror=&quot;a&quot;&gt; &amp; &#39;b&#39;", (r.stdout, r.stderr[:200]))
    pedazo = re.search(r"const aprende = .*?(?=\n\s*function unir\()", html, re.S)
    eventos = [{"s": "aaaa1111", "a": "agente1", "k": "leer", "f": "a/uno.md", "t": 1000},
               {"s": "aaaa1111", "a": "agente1", "k": "leer", "f": "a/dos.md", "t": 1005},
               {"s": "aaaa1111", "a": "agente1", "k": "editar", "f": "a/tres.py", "t": 1010},
               {"s": "bbbb2222", "k": "editar", "f": "b/tres.py", "t": 1020},
               {"s": "cccc3333", "k": "leer", "f": "c/cuatro.md", "t": 1020 + 3600}]
    prueba = carpeta / "aprende.js"
    prueba.write_text("const DATOS = {}; const uniones = [];\n"
                      "function rutasLeidas(ev) { return ev.fs || []; }\n"
                      "function clave(r) { return String(r).toLowerCase(); }\n"
                      "function unir(r, otras) { uniones.push([r, otras.length]); }\n"
                      + (pedazo.group(0) if pedazo else "") + "\n"
                      + f"const eventos = {json.dumps(eventos)};\n"
                      "eventos.slice(0, -1).forEach(aprenderDe); const antes = aprende.ventanas.size;\n"
                      "aprenderDe(eventos[eventos.length - 1]);\n"
                      "console.log(JSON.stringify({antes, despues: aprende.ventanas.size, uniones}));\n",
                      encoding="utf-8", newline="\n")
    r = subprocess.run(["node", str(prueba)], capture_output=True, text=True, timeout=120)
    try:
        salida = json.loads(r.stdout)
    except ValueError:
        salida = r.stdout + r.stderr[:300]
    probar("en vivo, la página une cada archivo con los anteriores del mismo pedido (de un agente, nota con nota no), y "
           "borra las ventanas de los chats y agentes que llevan más de 30 minutos quietos",
           salida == {"antes": 2, "despues": 1, "uniones": [["a/tres.py", 2]]}, salida)
    pedazo = re.search(r"const CAMPOS_TEXTO = .*?\n    function eventoSano\(ev\) \{.*?\n    \}\n", html, re.S)
    prueba = carpeta / "evento_sano.js"
    prueba.write_text((pedazo.group(0) if pedazo else "") + "\n"
                      "const raro = eventoSano({ t: 'x', s: 5, e: {}, p: { a: 1 }, f: 'a/uno.md', fs: [1, 'a/dos.md', null], "
                      "fc: 'x', m: 'zz', r: [1, 10, 10], x: [1, 'b'], n: 'mucho', id: 7 });\n"
                      "const ahora = Date.now() / 1000;\n"
                      "console.log(JSON.stringify({ t: Math.abs(raro.t - ahora) < 5, resto: Object.keys(raro).filter(k => k !== 't')"
                      ".sort().map(k => [k, raro[k]]), nulo: eventoSano(null), lista: eventoSano([1, 2]) }));\n",
                      encoding="utf-8", newline="\n")
    r = subprocess.run(["node", str(prueba)], capture_output=True, text=True, timeout=120)
    try:
        salida = json.loads(r.stdout)
    except ValueError:
        salida = r.stdout + r.stderr[:300]
    probar("en vivo, un evento con campos de otro tipo (sesión numérica, rutas que no son texto, cifras rotas) llega "
           "limpio a la página y no traba el panel ni «Repetir el día»",
           salida == {"t": True, "resto": [["f", "a/uno.md"], ["fs", ["a/dos.md"]], ["r", [1, 10, 10]]], "nulo": None,
                      "lista": None}, salida)
    probar("en modo anónimo se ocultan «Salud», «Lo que aprendió» y «Lo que hizo por vos», que muestran los nombres "
           "reales de las notas",
           "body.anonimo #bloque-salud, body.anonimo #bloque-aprendido, body.anonimo #bloque-ahorro" in html)
    motivos = re.search(r"const MOTIVO_PISTA = \{.*?\n    \};\n", html, re.S)
    funciones = re.search(r"    function pistaDe\(ev\) \{.*?(?=\n    const opcionConsulta)", html, re.S)
    sano = re.search(r"const CAMPOS_TEXTO = .*?\n    function eventoSano\(ev\) \{.*?\n    \}\n", html, re.S)
    prueba = carpeta / "pista.js"
    prueba.write_text("const COLOR = { consulta: '#e879f9' }; const presenta = { anonimo: false }; const vivo = {};\n"
                      "const hace = t => 'hace un rato'; const clave = r => r; const tituloVisto = n => n.titulo;\n"
                      "const a = { titulo: 'Nota A', texto: '# Título\\n\\n## Estado (4/10)\\nuno\\ndos\\n## Otra\\ntres\\ncuatro\\n',"
                      " desfase: 4 };\n"
                      "const indice = { titulo: 'MEMORY' };\n"
                      "const porRuta = new Map([['m/a.md', a], ['m/MEMORY.md', indice]]);\n"
                      + "".join(m.group(0) + "\n" for m in (motivos, funciones, sano) if m)
                      + "const ev = { e: 'aviso', t: 1, fs: ['m/a.md', 'm/x.py', 'm/MEMORY.md'],\n"
                      "             fp: [['p', 8, 9, ''], ['p', 0, 0, ''], ['i', 2, 3, 'm/MEMORY.md']] };\n"
                      "const lista = pistaDe(ev);\n"
                      "recordarPista(ev);\n"
                      "const normal = razonPista(lista[0], true);\n"
                      "presenta.anonimo = true; const anonima = razonPista(lista[0], true); presenta.anonimo = false;\n"
                      "const corrido = { e: 'aviso', t: 2, fs: ['m/a.md'], fp: [['p', 1, 2, ''], ['a', 1, 2, '']] };\n"
                      "console.log(JSON.stringify({ cuantas: lista.length, normal, anonima, indice: razonPista(lista[1], false),\n"
                      "  resumen: resumenPista(ev), panel: vivo.porQuePista(a), sinMotivo: resumenPista(corrido),\n"
                      "  sano: 'fp' in eventoSano({ t: 1, fp: [['p', 1, 2, '']] }), roto: 'fp' in eventoSano({ t: 1, fp: [['p', 'x', 2, '']] }) }));\n",
                      encoding="utf-8", newline="\n")
    r = subprocess.run(["node", str(prueba)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    try:
        salida = json.loads(r.stdout)
    except ValueError:
        salida = r.stdout + r.stderr[:300]
    probar("la página dice por qué eligió la pista cada nota (por tus palabras con el tramo y su sección, la nombra un "
           "índice, aprendida), alineado con sus rutas; en modo anónimo sin la sección; y lo recuerda para el panel",
           salida == {"cuantas": 2, "normal": "por tus palabras (renglones 8-9, «Estado (4/10)»)",
                      "anonima": "por tus palabras (renglones 8-9)", "indice": "la nombra MEMORY",
                      "resumen": "1 por palabras · 1 por índice",
                      "panel": "La pista la eligió hace un rato: por tus palabras (renglones 8-9, «Estado (4/10)»).",
                      "sinMotivo": "", "sano": True, "roto": False}, salida)
    clases = re.search(r"const ORDEN_CLASES = \[(.*?)\];", html)
    clases = set(re.findall(r"'(\w+)'", clases.group(1))) if clases else set()
    sin_pulso = {}
    for tabla in ("PRIORIDAD", "BASE_MS", "PESO_RAFAGA"):
        cuerpo = re.search(rf"const {tabla} = \{{(.*?)\}};", html)
        sin_pulso[tabla] = sorted(clases - set(re.findall(r"(\w+):", cuerpo.group(1) if cuerpo else "")))
    probar("cada clase de conexión tiene su orden, duración y peso de pulso (sin duración, un pulso por un camino "
           "aprendido no terminaba nunca y la página no volvía a quedarse quieta)",
           len(clases) >= 12 and not any(sin_pulso.values()), sin_pulso)
    fundir = re.search(r"  const nivelUso = .*?\n  const usoDe = .*?;\n", html, re.S)
    prueba = carpeta / "mielina.js"
    prueba.write_text("const estado = { clasesOn: new Set(['mencion', 'wiki', 'aprendida']) };\n"
                      + (fundir.group(0) if fundir else "") + "\n"
                      "const nodo = () => ({ salientes: [], entrantes: [] });\n"
                      "const a = nodo(), b = nodo(), c = nodo();\n"
                      "const unir = (de, al, clase, peso) => { const l = { source: de, target: al, clase, _visible: true,\n"
                      "  datos: peso === undefined ? null : { peso } }; de.salientes.push(l); al.entrantes.push(l); return l; };\n"
                      "const m = unir(a, b, 'mencion'), ap = unir(b, a, 'aprendida', 0.45), sola = unir(a, c, 'aprendida', 0.2),\n"
                      "  w = unir(b, c, 'wiki');\n"
                      "fundirAprendidas([m, ap, sola, w]);\n"
                      "const r = { m: m._mielina, w: w._mielina, sobre: ap._sobre && ap._sobre.length === 1 && ap._sobre[0] === m,\n"
                      "  sola: sola._sobre, tapada: tapada(ap), libre: tapada(sola), usoM: usoDe(m), usoSola: usoDe(sola),\n"
                      "  niveles: [0, 0.2, 0.35, 0.45, 0.6, 0.9].map(nivelUso) };\n"
                      "m._visible = false; r.sinDebajo = tapada(ap);\n"
                      "estado.clasesOn.delete('aprendida'); r.apagada = usoDe(m);\n"
                      "console.log(JSON.stringify(r));\n", encoding="utf-8", newline="\n")
    r = subprocess.run(["node", str(prueba)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    try:
        salida = json.loads(r.stdout)
    except ValueError:
        salida = r.stdout + r.stderr[:300]
    probar("un camino aprendido entre notas que ya estaban conectadas engrosa esa conexión en vez de dibujar otra (y "
           "vuelve a verse punteado si la de abajo se oculta); con «Aprendida» apagada no engrosa nada",
           salida == {"m": 0.45, "w": 0, "sobre": True, "sola": None, "tapada": True, "libre": False, "usoM": 0.45,
                      "usoSola": 0.2, "niveles": [0, 1, 2, 2, 3, 3], "sinDebajo": False, "apagada": 0}, salida)
    caminos = re.search(r"  const llaveCamino = .*?\n    return \{ nacen: nacen\.length, suben: suben\.length, "
                        r"seVan: seVan\.length \};\n  \}\n", html, re.S)
    prueba = carpeta / "caminos.js"
    prueba.write_text("const estado = { clasesOn: new Set(['wiki', 'aprendida']) };\n"
                      "const anim = { efectos: [] }; const colores = { acento: '#a' }; const colorDe = n => '#n';\n"
                      "let dibujos = 0;\n"
                      "const gestoPosible = () => true, introCorriendo = () => false, programarCuadro = () => {};\n"
                      "const pedirDibujo = () => { dibujos++; }, recalcularAristasBusqueda = () => {}, actualizarContador = () => {};\n"
                      "const recalcularVisibles = () => aristas.forEach(l => { l._visible = true; });\n"
                      "const $ = () => null; const document = { querySelectorAll: () => [] };\n"
                      "const nodo = id => ({ id, salientes: [], entrantes: [] });\n"
                      "const A = nodo('a'), B = nodo('b'), C = nodo('c'), D = nodo('d');\n"
                      "const porId = new Map([A, B, C, D].map(n => [n.id, n]));\n"
                      "const aristas = [];\n"
                      "const unir = (x, y, clase, peso) => { const l = { source: x, target: y, clase, texto: '', _visible: true,\n"
                      "  datos: peso === undefined ? null : { peso } }; aristas.push(l); x.salientes.push(l); y.entrantes.push(l); return l; };\n"
                      + (fundir.group(0) if fundir else "") + (caminos.group(0) if caminos else "") + "\n"
                      "const w = unir(A, B, 'wiki'), ab = unir(A, B, 'aprendida', 0.3), cd = unir(C, D, 'aprendida', 0.25),\n"
                      "  ac = unir(A, C, 'aprendida', 0.3);\n"
                      "fundirAprendidas(aristas);\n"
                      "const r0 = actualizarCaminos([['a', 'b', 0.3], ['c', 'd', 0.25], ['a', 'c', 0.3], ['c', 'b', 0.3]]);\n"
                      "const e0 = anim.efectos.length;\n"
                      "const r1 = actualizarCaminos([['b', 'a', 0.45], ['a', 'c', 0.5], ['c', 'b', 0.3], ['b', 'd', 0.3], ['x', 'a', 1],\n"
                      "  ['b', 'd', 'nada']]);\n"
                      "const bd = aristas.find(l => l.source === B && l.target === D);\n"
                      "console.log(JSON.stringify({ r0, e0, r1, efectos: anim.efectos.map(e => e.tipo).sort(), bd: bd && bd.datos.peso,\n"
                      "  aprendidas: aristas.filter(l => l.clase === 'aprendida').length, cdFuera: !C.salientes.includes(cd) && !D.entrantes.includes(cd),\n"
                      "  mielina: w._mielina, texto: ab.texto, potenciaSobre: anim.efectos.some(e => e.tipo === 'potencia' && e.l === w),\n"
                      "  nada: actualizarCaminos(null), igual: actualizarCaminos(aristas.filter(l => l.clase === 'aprendida')\n"
                      "    .map(l => [l.source.id, l.target.id, l.datos.peso])), dibujos }));\n", encoding="utf-8", newline="\n")
    r = subprocess.run(["node", str(prueba)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    try:
        salida = json.loads(r.stdout)
    except ValueError:
        salida = r.stdout + r.stderr[:300]
    probar("en vivo, cuando cambia lo aprendido la página pone al día los caminos sin recargar: nacen los nuevos, se "
           "engrosan los que suben de nivel (sobre la conexión de abajo si ya había) y se apagan los olvidados; la primera "
           "vez solo se pone al día, sin animar, y lo que llega roto se ignora",
           "actualizarCaminos(DATOS.aprendido.caminos)" in html
           and salida == {"r0": {"nacen": 1, "suben": 0, "seVan": 0}, "e0": 0, "r1": {"nacen": 1, "suben": 2, "seVan": 1},
                          "efectos": ["apaga", "brote", "potencia", "potencia"], "bd": 0.3, "aprendidas": 4, "cdFuera": True,
                          "mielina": 0.45, "texto": "se usan juntas en el trabajo (fuerza 0,45)", "potenciaSobre": True,
                          "nada": None, "igual": {"nacen": 0, "suben": 0, "seVan": 0}, "dibujos": 2}, salida)
    rio = re.search(r"    const RIO_VENTANA = .*?\n      return \{ t0, vistos, carriles \};\n    \}\n", html, re.S)
    prueba = carpeta / "rio.js"
    prueba.write_text("const $ = () => null;\n" + (rio.group(0) if rio else "") + "\n"
                      "const ahora = Date.now() / 1000;\n"
                      "const ev = (s, dt, extra) => Object.assign({ s, t: ahora + dt, e: 'post', k: 'leer' }, extra || {});\n"
                      "[ev('a', -2000), ev('afuera', -640), ev('a', -30, { e: 'pre' }), ev('a', -30, { repite: true }),\n"
                      " { t: ahora, e: 'post' }, ev('c1', -500), ev('c1', -490), ev('c2', -400), ev('c3', -300), ev('c4', -200),\n"
                      " ev('c5', -100), ev('c6', -50), ev('c3', -20)].forEach(x => anotarRio(x, false));\n"
                      "const r = carrilesRio(rio.eventos, ahora);\n"
                      "console.log(JSON.stringify({ guardados: rio.eventos.length, vistos: r.vistos.length, carriles: r.carriles,\n"
                      "  vacio: carrilesRio([], ahora).carriles }));\n", encoding="utf-8", newline="\n")
    r = subprocess.run(["node", str(prueba)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    try:
        salida = json.loads(r.stdout)
    except ValueError:
        salida = r.stdout + r.stderr[:300]
    probar("el río del tiempo muestra los últimos 10 minutos: un carril por chat (los 5 que se movieron más recién, en el "
           "orden en que aparecieron), sin lo que empieza (pre), sin la repetición del día y sin lo que no tiene chat; "
           "lo escucha en vivo y al abrir, y se esconde en pantallas chicas y en el modo cine",
           salida == {"guardados": 9, "vistos": 8, "carriles": ["c2", "c3", "c4", "c5", "c6"], "vacio": []}
           and "anotarRio(ev, true)" in html and "lista.forEach(ev => anotarRio(ev, false))" in html
           and ".contador, .eeg, .rio { display: none; }" in html and "body.cine .rio" in html, salida)
    tipos = set(re.findall(r"tipo: '(\w+)'", html))
    inicio = html.find("  const DIBUJO_EFECTO = {")
    dibujos = set(re.findall(r"DIBUJO_EFECTO\.(\w+) = ", html))
    dibujos |= set(re.findall(r"(?m)^    (\w+)\(e, p", html[inicio:html.find("\n  };\n", inicio)])) if inicio >= 0 else set()
    probar("cada animación que lanza la página tiene con qué dibujarse (si no, el cuadro entero se corta con un error)",
           len(tipos) >= 15 and tipos <= dibujos, sorted(tipos - dibujos))
    pedazo = re.search(r"(?m)^  function textoDelLobulo\(l\) \{.*?\n  \}\n", html, re.S)
    prueba = carpeta / "lobulos.js"
    prueba.write_text((pedazo.group(0) if pedazo else "") + "\n"
                      "const l = nombre => ({ anatomico: 'Frontal', nombre });\n"
                      "console.log(JSON.stringify(['Frontal · Ideas y planes', 'Frontal', 'Mis ideas']"
                      ".map(n => textoDelLobulo(l(n)))));\n", encoding="utf-8", newline="\n")
    r = subprocess.run(["node", str(prueba)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    try:
        salida = json.loads(r.stdout)
    except ValueError:
        salida = r.stdout + r.stderr[:300]
    probar("cada zona del dibujo lleva un solo nombre, el del lóbulo («FRONTAL»), y debajo sus grupos; lo que dice el "
           "config.json de ese lóbulo va en la ayuda, venga con «Frontal · …» adelante o no (antes salían dos nombres "
           "distintos encimados)",
           salida == ["Ideas y planes", "", "Mis ideas"] and "l.anatomico = l.nombre;" in html
           and "const texto = l.anatomico.toUpperCase();" in html
           and "item(punto(g ? g.color : 'var(--texto-3)'), l.anatomico, publico('texto', l, textoDelLobulo(l)), '')" in html,
           salida)
