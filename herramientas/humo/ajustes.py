from humo.base import *


def revisar_config_rota(t):
    rota = t / "config-rota"
    rota.mkdir()
    (rota / "config.json").write_text('{"fuentes": [ {"id": "x", ', encoding="utf-8")
    try:
        configuracion.cargar(rota / "config.json")
        mensaje = ""
    except configuracion.ConfigInvalida as error:
        mensaje = str(error)
    comando = correr([str(CARPETA / "neuromapa.py"), "--salud"], CEREBRO_CONFIG=str(rota / "config.json"))
    probar("con un config.json roto, el error dice en castellano dónde se rompe, y neuromapa lo muestra sin traza y sale "
           "con 1 (antes, 30 renglones en inglés)",
           "no es un JSON válido" in mensaje and "renglón 1" in mensaje and comando.returncode == 1
           and "no pudo leer su configuración" in comando.stderr and "Traceback" not in comando.stderr + comando.stdout,
           (mensaje, comando.returncode, comando.stderr[-300:]))
    pedido = json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "¿cómo anda la memoria del proyecto de prueba?",
                         "cwd": str(t), "session_id": "rota0001-x"}).encode("utf-8")
    avisos = [correr_hook("hook_servir.py", pedido, CEREBRO_CONFIG=str(rota / "config.json")).stdout for _ in range(2)]
    probar("y el hook de cada pedido se lo dice a Claude una vez por chat (antes callaba: sin pistas ni avisos, sin saber "
           "por qué)", b"no puede leer su configuraci" in avisos[0] and not avisos[1], avisos)


def revisar_nombre_raro(t):
    raros = t / "nombres-raros"
    (raros / "memoria").mkdir(parents=True)
    (raros / "en-vivo").mkdir()
    (raros / "memoria" / "MEMORY.md").write_text("# Memoria\n\n- [Nota rara](nota-10²3.md) — una nota con un dos chiquito\n",
                                                 encoding="utf-8", newline="\n")
    (raros / "memoria" / "nota-10²3.md").write_text(frontmatter("nota-rara", "Una nota con un dos chiquito", "project")
                                                    + "El tope de los baneos es de 876000 horas.\n",
                                                    encoding="utf-8", newline="\n")
    config = {"usuario": "Ana", "fuentes": [{"id": "memoria", "nombre": "Memoria", "color": "#E64980",
                                             "raices": [[str(raros / "memoria"), False, ""]], "memoria": True, "foco": True}]}
    (raros / "config.json").write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8", newline="\n")
    salidas = [cerebro_en(raros, *opciones) for opciones in (["--salida", str(raros / "c.html"), "--json", str(raros / "c.json")],
                                                             ["--salud"], ["--sobre", "tope de los baneos"])]
    probar("una nota con «²» en el nombre no apaga el mapa, --salud ni --sobre (antes se caían los tres: «²» parece un "
           "dígito, pero int() no lo lee)",
           all(codigo == 0 and "Traceback" not in salida for codigo, salida in salidas) and "nota-10²3.md" in salidas[2][1],
           [(codigo, salida[-200:]) for codigo, salida in salidas])
    import firmas
    try:
        rechazada = firmas.pedido_valido("clave", "/x", "²:abc") is False
    except ValueError:
        rechazada = False
    probar("una firma de pedido con «²» en la hora se rechaza sin romper el servidor", rechazada)


def revisar_configuracion(t):
    seccion("Configuración (la que arma sola, los alias y los errores)")
    revisar_config_rota(t)
    revisar_nombre_raro(t)
    casa = t / "casa-claude"
    for nombre in ("C--x-uno", "C--x-dos"):
        (casa / "projects" / nombre / "memory").mkdir(parents=True)
        (casa / "projects" / nombre / "memory" / "MEMORY.md").write_text("# Memoria\n", encoding="utf-8")
    (casa / "CLAUDE.md").write_text("# Instrucciones\n", encoding="utf-8")
    (casa / "agent-memory" / "revisor").mkdir(parents=True)
    (casa / "agent-memory" / "revisor" / "MEMORY.md").write_text("# Memoria del revisor\n", encoding="utf-8")
    movida = t / "memoria-movida"
    movida.mkdir()
    (movida / "MEMORY.md").write_text("# Memoria movida\n", encoding="utf-8")
    (casa / "settings.json").write_text(json.dumps({"autoMemoryDirectory": str(movida)}), encoding="utf-8")
    antes = os.environ.get("CLAUDE_CONFIG_DIR")
    os.environ["CLAUDE_CONFIG_DIR"] = str(casa)
    try:
        armada = configuracion.armar(configuracion.por_defecto(), configuracion.CARPETA)
    finally:
        if antes is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = antes
    memoria = next((f for f in armada["fuentes"] if f["id"] == "memoria"), {})
    alias = sorted(r[2] for r in memoria.get("raices", []))
    probar("sin config.json, encuentra las 2 memorias de la carpeta de Claude, la de un subagente (agent-memory) y la "
           "que se movió con autoMemoryDirectory (antes, esas dos quedaban afuera)",
           alias == ["C--x-dos", "C--x-uno", "agente-revisor", "memoria-movida"], memoria.get("raices"))
    instrucciones = next((f for f in armada["fuentes"] if f["id"] == "instrucciones"), {})
    probar("y lee el CLAUDE.md de esa carpeta", bool(instrucciones.get("raices")) and instrucciones["raices"][0][0] == str(casa),
           instrucciones.get("raices"))
    por_junction = consultas.clave(str(t / "memoria-por-junction" / "perfil-ana.md"))
    probar("una ruta por un junction (alias_rutas) cuenta como la real",
           por_junction == consultas.clave(str(t / "memoria" / "perfil-ana.md")))
    solo_freno = t / "solo-freno" / "config.json"
    solo_freno.parent.mkdir()
    solo_freno.write_text('{"freno": {"tokens_de_agentes_por_hora": 500000}}', encoding="utf-8")
    os.environ["CLAUDE_CONFIG_DIR"] = str(casa)
    try:
        con_freno = configuracion.cargar(solo_freno)
    finally:
        os.environ["CLAUDE_CONFIG_DIR"] = antes
    probar("un config.json que solo suma el freno sigue leyendo las fuentes de fábrica (antes dejaba el mapa con 0 notas)",
           con_freno["freno"] and [f["id"] for f in con_freno["fuentes"]] == [f["id"] for f in armada["fuentes"]],
           [f["id"] for f in con_freno["fuentes"]])
    fragmentos = configuracion.armar({"excluir_fragmentos": ["/Borrador/"]}, t)["excluir_fragmentos"]
    probar("excluir_fragmentos escrito con «/» excluye igual que con «\\» (se compara contra rutas normalizadas)",
           any(f in nucleo.normalizar("C:/notas/borrador/idea.md") for f in fragmentos), fragmentos)
    dormir_claude = configuracion.armar({"dormir_con_claude": {"tope_usd_por_dia": 1}}, t)["dormir_con_claude"]
    probar("dormir con Claude viene apagado y, prendido, lleva el tope por día y el modelo (sonnet si no se dice)",
           configuracion.armar({}, t)["dormir_con_claude"] is None
           and dormir_claude == {"tope_usd_por_dia": 1.0, "modelo": "sonnet"}, dormir_claude)
    probar("el modo de comparación viene apagado (0) y se prende con la parte de los pedidos que van sin lo aprendido",
           configuracion.armar({}, t)["comparar_aprendido"] == 0.0
           and configuracion.armar({"comparar_aprendido": 0.2}, t)["comparar_aprendido"] == 0.2)
    probar("ordenar con las preguntas de las notas viene prendido y se apaga con false",
           configuracion.armar({}, t)["ordenar_con_preguntas"] is True
           and configuracion.armar({"ordenar_con_preguntas": False}, t)["ordenar_con_preguntas"] is False)
    roto = t / "config-roto.json"
    for texto, esperado in (('{"fuentes": [{"nombre": "sin id"}]}', "necesita un id"),
                            ('{"proyectos": [{"raiz": "x", "marca": "(roto"}]}',
                             "no es una expresión regular válida (se rompe en el carácter 1)"),
                            ('{"fuentes": [{"id": "a", "lobulo": "nariz"}]}', "lobulo"),
                            ('{"proyectos": [{"raiz": "x", "remite_a": "nadie"}]}', "remite a"),
                            ('{"dormir_con_claude": {"tope_usd_por_dia": 0}}', "tope_usd_por_dia"),
                            ('{"dormir_con_claude": {"tope_usd_por_dia": 1, "modelo": "a b"}}', "modelo"),
                            ('{"comparar_aprendido": 0.9}', "comparar_aprendido"),
                            ('{"ordenar_con_preguntas": "no"}', "ordenar_con_preguntas va true o false"),
                            ('{"fuentes": [{"id": "a", "memoria": "false"}]}',
                             "fuentes[0].memoria tiene que ser true o false, sin comillas"),
                            ('{"fuentes": [{"id": "a", "foco": "no"}]}', "fuentes[0].foco tiene que ser true o false"),
                            ('{"fuentes": [{"id": "a", "raices": [["notas", "false", ""]]}]}',
                             "recursivo va true o false, sin comillas"),
                            ('{"fuentes": [{"id": "a", "raices": "D:\\\\Notas"}]}', "fuentes[0].raices tiene que ser una lista"),
                            ('{"proyectos": [{"raiz": "x", "codigo": "D:\\\\P\\\\src"}]}',
                             "proyectos[0].codigo tiene que ser una lista"),
                            ('{"fuentes": [{"id": "a", "patron": ["CLAUDE.md"]}]}', "fuentes[0].patron tiene que ser un texto"),
                            ('{"fuentes": [{"id": "a", "peso_busqueda": -5}]}', "peso_busqueda tiene que ser mayor que 0"),
                            ('{"fuentes": {"id": "a"}}', "fuentes tiene que ser una lista"),
                            ("{no es json", "no es un JSON válido")):
        roto.write_text(texto, encoding="utf-8")
        try:
            configuracion.cargar(roto)
            dijo = "no avisó"
        except configuracion.ConfigInvalida as error:
            dijo = str(error)
        probar(f"un config roto dice qué está mal («{esperado}»)", esperado in dijo, dijo)
    for codificacion in ("cp1252", "utf-16"):
        roto.write_bytes('{"usuario": "Begoña"}'.encode(codificacion))
        try:
            configuracion.cargar(roto)
            dijo = "no avisó"
        except configuracion.ConfigInvalida as error:
            dijo = str(error)
        probar(f"un config.json guardado en {codificacion} dice que hay que guardarlo en UTF-8, en castellano (antes, el "
               "error de Python en inglés)", "no está guardado en UTF-8" in dijo and "codec" not in dijo, dijo)
    tipeos = configuracion.armar({"partir_solo": True, "_comentario": "para mí", "fuentes": [
        {"id": "notas", "focus": True, "raices": [{"ruta": "notas", "recursiva": True}]}],
        "proyectos": [{"raiz": "x", "pistass": ["x"]}]}, t).get("avisos")
    de_fabrica = configuracion.armar(configuracion.por_defecto(), t).get("avisos")
    de_la_demo = configuracion.cargar(configuracion.DEMO).get("avisos")
    probar("una clave mal escrita no frena nada pero se avisa, con la más parecida («¿quisiste decir partir_sola?»); las "
           "que empiezan con «_» son comentarios; la de fábrica y la de la demo no avisan nada (antes se ignoraban callado)",
           tipeos is not None and len(tipeos) == 4 and "«partir_solo»" in tipeos[0] and "«partir_sola»" in tipeos[0]
           and "«notas»" in tipeos[1] and "«foco»" in tipeos[1] and "«recursivo»" in tipeos[2] and "«pistas»" in tipeos[3]
           and de_fabrica == [] and de_la_demo == [], (tipeos, de_fabrica, de_la_demo))
    con_tipeo = t / "config-tipeo"
    con_tipeo.mkdir()
    (con_tipeo / "config.json").write_text(json.dumps({"usuario": "Ana", "partir_solo": True, "fuentes": [
        {"id": "memoria", "raices": [[str(t / "nombres-raros" / "memoria"), False, ""]], "memoria": True}]}),
        encoding="utf-8")
    codigo, salud = cerebro_en(con_tipeo, "--salud")
    renglon = next((r for r in salud.splitlines() if "partir_solo" in r), "")
    probar("--salud muestra la clave mal escrita como aviso, con el archivo y la sugerencia",
           codigo == 0 and renglon.startswith("AVISO") and str(con_tipeo / "config.json") in renglon
           and "¿quisiste decir «partir_sola»?" in renglon, (codigo, renglon or salud[-400:]))
    for programa, extra in (("cerebro.py", ["--salud"]), ("servidor.py", ["--sin-navegador", "--puerto", "0"])):
        r = correr([str(CARPETA / programa)] + extra, CEREBRO_CONFIG=str(roto))
        probar(f"{programa} con el config roto sale con un renglón claro, sin traza de Python",
               r.returncode == 1 and "Error en la configuración:" in r.stderr and "Traceback" not in r.stderr,
               (r.returncode, r.stderr[-300:]))
    salidas = {}
    for nombre, argv in (("tipeo", [str(CARPETA / "servidor.py"), "--dmeo", "--sin-navegador", "--puerto", "0"]),
                         ("ayuda", [str(CARPETA / "servidor.py"), "--help"]),
                         ("plugin", [str(CARPETA / "neuromapa.py"), "abrir", "--dmeo", "--sin-navegador", "--puerto", "0"])):
        try:
            r = correr(argv, espera=30)
            salidas[nombre] = (r.returncode, r.stdout + r.stderr)
        except subprocess.TimeoutExpired:
            salidas[nombre] = (None, "se quedó sirviendo")
    ilegible = t / "ilegible"
    (ilegible / "memory").mkdir(parents=True)
    (ilegible / "memory" / "MEMORY.md").write_text("# Memoria\n\n- [Mala](mala.md) — una nota que no se puede leer\n",
                                                   encoding="utf-8")
    (ilegible / "memory" / "mala.md").write_bytes(b"---\nname: mala\n---\n\x81\x8d\x8f\x90\x9d\n")
    (ilegible / "config.json").write_text(json.dumps({"fuentes": [{"id": "memoria", "nombre": "Memoria", "memoria": True,
                                                                   "raices": [["memory", False, ""]]}]}), encoding="utf-8")
    r = correr([str(CARPETA / "cerebro.py"), "--salud"], espera=120, CEREBRO_CONFIG=str(ilegible / "config.json"))
    probar("--salud avisa la nota que no pudo leer, en vez de saltearla en silencio",
           "No pude leer" in r.stdout and "mala.md" in r.stdout, (r.stdout[-300:], r.stderr[-200:]))
    ayuda, falta = [correr([str(CARPETA / "cerebro.py")] + extra) for extra in (["--help"], ["--sobre"])]
    probar("la ayuda y los errores de la consola salen en castellano",
           "uso: " in ayuda.stdout and "muestra esta ayuda" in ayuda.stdout and "le falta el valor" in falta.stderr
           and "usage" not in ayuda.stdout + falta.stderr, (ayuda.stdout[:120], falta.stderr[-120:]))
    abreviada = correr([str(CARPETA / "cerebro.py"), "--dem", "--salud"])
    probar("una opción abreviada («--dem») se rechaza, no se toma como --demo con la configuración real",
           abreviada.returncode == 2 and "--dem" in abreviada.stderr and "Médico" not in abreviada.stdout,
           (abreviada.returncode, abreviada.stdout[:120], abreviada.stderr[-160:]))
    dos_modos = correr([str(CARPETA / "cerebro.py"), "--salud", "--aprobar-hecho", "1"])
    probar("dos modos juntos («--salud --aprobar-hecho 1») se rechazan, en vez de correr uno y callar el otro",
           dos_modos.returncode == 2 and "no va junto" in dos_modos.stderr, (dos_modos.returncode, dos_modos.stderr[-160:]))
    permisos = {s: re.findall(r"^\s+- (\S+\(.*\))$", (CARPETA / "skills" / s / "SKILL.md").read_text(encoding="utf-8"), re.M)
                for s in ("abrir", "salud", "sobre")}
    probar("cada comando del plugin preaprueba solo su propio modo (nunca «neuromapa *», que dejaría escribir donde sea)",
           all(permisos.values()) and all(re.search(r"neuromapa(\.cmd\")?\"? (--)?" + s, p)
                                          for s, lista in permisos.items() for p in lista),
           permisos)

    def arrancar(*extra, espera=60):
        arranque = subprocess.Popen([sys.executable, str(CARPETA / "servidor.py"), "--sin-navegador", "--puerto", "0", *extra],
                                    env=dict(os.environ, PYTHONIOENCODING="utf-8"), stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        reloj = threading.Timer(espera, arranque.kill)
        reloj.start()
        visto = []
        try:
            for renglon in arranque.stdout:
                visto.append(renglon.rstrip())
                if "Traceback" in renglon or "Cerrá esta ventana" in renglon or "Se apaga solo" in renglon:
                    break
        finally:
            reloj.cancel()
            arranque.kill()
            arranque.wait(10)
            (aprender.en_vivo() / aprender.CANDADO).unlink(missing_ok=True)
        return visto

    primero = subprocess.Popen([sys.executable, str(CARPETA / "servidor.py"), "--sin-navegador", "--puerto", "0"],
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"), stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    try:
        for renglon in primero.stdout:
            if "Cerrá esta ventana" in renglon or "Traceback" in renglon:
                break
        threading.Thread(target=primero.wait, daemon=True).start()
        segundo = arrancar()
        try:
            primero.wait(10)
        except subprocess.TimeoutExpired:
            pass
        se_fue = primero.poll() is not None
    finally:
        primero.kill()
        primero.wait(10)
    probar("abrir-cerebro.bat dos veces reinicia: el segundo le pide al primero que se apague y arranca en su lugar "
           "(antes quedaban dos sobre los mismos datos, pisándose lo aprendido)",
           se_fue and any("lo apagué" in v for v in segundo) and any("Neuromapa en vivo" in v for v in segundo),
           (se_fue, segundo[-4:]))
    import archivos
    candado = servidor.EN_VIVO / getattr(servidor, "CANDADO_ARRANQUE", "")
    apurado = subprocess.Popen([sys.executable, str(CARPETA / "servidor.py"), "--sin-navegador", "--puerto", "0"],
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"), stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    try:
        limite = time.monotonic() + (10 if hasattr(servidor, "CANDADO_ARRANQUE") else 0)
        while time.monotonic() < limite:
            prueba = archivos.tomar_candado(candado)
            if prueba is None:
                break
            archivos.soltar_candado(prueba)
            time.sleep(0.05)
        desde = time.monotonic()
        pegado = arrancar(espera=150)
        tardo = round(time.monotonic() - desde, 1)
        try:
            apurado.wait(15)
        except subprocess.TimeoutExpired:
            pass
        reemplazado = apurado.poll() is not None
    finally:
        apurado.kill()
        apurado.wait(10)
    probar("dos arranques casi a la vez dejan uno solo: el segundo espera a que el primero termine de arrancar y lo "
           "reemplaza (antes, con menos de ~4 s de diferencia, quedaban dos y uno no se veía)",
           reemplazado and any("lo apagué" in v for v in pegado) and any("Neuromapa en vivo" in v for v in pegado),
           (reemplazado, f"{tardo} s", pegado[-4:]))
    servidor._clave.clear()
    servidor.ARCHIVO_CLAVE.unlink(missing_ok=True)
    visto = arrancar()
    clave_creada = servidor.ARCHIVO_CLAVE.exists()
    probar("la primera vez, el archivo de la clave que nombra la consola ya existe cuando lo nombra (antes se creaba recién "
           "con el primer pedido, y quien no tenía navegador no lo encontraba)", clave_creada, visto[-4:])
    probar("servidor.py arranca entero como programa (el camino de abrir-cerebro.bat), hasta «en vivo», y nunca imprime "
           "la clave (antes la mostraba en la dirección; si lo arranca Claude queda en la charla)",
           any("Neuromapa en vivo" in v for v in visto) and not any(servidor.clave() in v for v in visto)
           and any("clave.txt" in v for v in visto) and any("Para entrar" in v for v in visto), visto[-6:])
    del_plugin = arrancar("--apagar-solo")
    probar("desde el plugin, la dirección sale sin la clave (queda en la transcripción de la charla) y dice dónde está",
           any("en vivo" in v or "ya estaba" in v for v in del_plugin) and not any(servidor.clave() in v for v in del_plugin)
           and any("clave.txt" in v for v in del_plugin), del_plugin[-4:])
    vivo = subprocess.Popen([sys.executable, str(CARPETA / "servidor.py"), "--sin-navegador", "--puerto", "0", "--apagar-solo"],
                            env=dict(os.environ, PYTHONIOENCODING="utf-8"), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    try:
        for renglon in vivo.stdout:
            if "Se apaga solo" in renglon or "Traceback" in renglon:
                break
        threading.Thread(target=vivo.wait, daemon=True).start()
        reusa = arrancar("--apagar-solo")
        nuevo = arrancar("--apagar-solo", "--reiniciar")
        try:
            vivo.wait(10)
        except subprocess.TimeoutExpired:
            pass
        apagado = vivo.poll() is not None
    finally:
        vivo.kill()
        vivo.wait(10)
    probar("desde el plugin, abrirlo de nuevo reusa el mapa prendido, y con --reiniciar lo apaga y arranca uno nuevo "
           "(después de actualizar o de cambiar el config.json, el que seguía prendido servía lo de antes)",
           any("ya estaba prendido" in v for v in reusa) and apagado and any("Apagué el mapa" in v for v in nuevo)
           and any("en vivo" in v for v in nuevo), (reusa[-2:], apagado, nuevo[-3:]))
    navegador = ("import subprocess, sys, webbrowser; sys.path.insert(0, sys.argv[1]); import servidor; "
                 "webbrowser.open = lambda d: subprocess.call([sys.executable, '-c', 'import sys; print(sys.argv[1]); "
                 "sys.stderr.write(sys.argv[1])', d]) == 1; "
                 "print(servidor.aviso_navegador(servidor.abrir_navegador("
                 "'http://127.0.0.1:1/cerebro.html?clave=SECRETO'), True))")
    r = correr(["-c", navegador, str(CARPETA)])
    probar("si el navegador falla, lo que imprime (con la clave en la dirección) no llega a la consola que lee Claude, y el "
           "aviso dice que no se abrió", "SECRETO" not in r.stdout + r.stderr and "No pude abrir el navegador" in r.stdout,
           (r.stdout[-200:], r.stderr[-200:]))
    probar("una opción mal escrita o --help no arman ni sirven nada (con «--dmeo» antes se servían las notas reales)",
           salidas["tipeo"][0] == 2 and "No conozco --dmeo" in salidas["tipeo"][1] and "en vivo" not in salidas["tipeo"][1]
           and salidas["ayuda"][0] == 0 and "Uso: servidor.py" in salidas["ayuda"][1]
           and salidas["plugin"][0] == 2 and "Uso: neuromapa abrir" in salidas["plugin"][1], salidas)
    plantilla_texto = plantilla_entera(CARPETA / "plantilla.html")
    probar("la página de «falta la clave» dice dónde está la clave, y ella y el mapa vacío mandan a los lanzadores que "
           "andan en todos lados (no a «python servidor.py» ni a abrir-cerebro.bat, que necesitan «python»)",
           b"en-vivo/clave.txt" in servidor.SIN_CLAVE and b"bin/neuromapa abrir" in servidor.SIN_CLAVE
           and b"python servidor.py" not in servidor.SIN_CLAVE and "abrir-cerebro.bat" not in plantilla_texto
           and "bin/neuromapa abrir" in plantilla_texto, servidor.SIN_CLAVE[-200:])
    nombres_pagina = {}
    for bloque, desde, hasta in (("clases", "const CLASES =", "const TIPOS ="), ("tipos", "const TIPOS =", "const TIPOS_MEMORIA")):
        trozo = plantilla_texto.split(desde, 1)[1].split(hasta, 1)[0]
        nombres_pagina[bloque] = dict(re.findall(r"(\w+): \{ nombre: '([^']+)'", trozo))
    probar("la consola nombra las conexiones y los tipos de nota igual que la página («Proyecto», no «project»)",
           nombres_pagina["clases"] == nucleo.NOMBRE_CLASE and set(nucleo.ORDEN_CLASES) == set(nucleo.NOMBRE_CLASE)
           and nombres_pagina["tipos"] == nucleo.NOMBRE_TIPO, nombres_pagina)
    try:
        configuracion.cargar(t / "no-existe" / "config.json")
        dijo = "no avisó"
    except configuracion.ConfigInvalida as error:
        dijo = str(error)
    probar("un config elegido que no existe avisa, en vez de armar el de fábrica", "no encontré" in dijo, dijo)
    r = correr([str(CARPETA / "neuromapa.py"), "--salud"], CEREBRO_CONFIG=str(t / "no-existe" / "config.json"))
    probar("si CEREBRO_CONFIG apunta a un archivo que no existe, la consola dice que la corrijas (no «arreglá ese "
           "archivo o borralo», que no existe)", r.returncode == 1 and "CEREBRO_CONFIG" in r.stderr
           and "Arreglá ese archivo" not in r.stderr, r.stderr[-300:])
    vacia = t / "memoria-vacia"
    (vacia / "notas").mkdir(parents=True)
    (vacia / "config.json").write_text(json.dumps({"fuentes": [{"id": "a", "nombre": "A", "raices": [
        [str(vacia / "notas"), True, ""]]}]}), encoding="utf-8")
    dichos = {modo: correr([str(CARPETA / "cerebro.py"), *extra], espera=120, CEREBRO_CONFIG=str(vacia / "config.json"))
              for modo, extra in (("salud", ["--salud"]), ("buscar", ["--buscar", "riego"]),
                                  ("armar", ["--salida", str(vacia / "c.html"), "--json", str(vacia / "c.json")]))}
    probar("con la memoria vacía, --salud, --buscar y el armado dicen dónde buscaron (antes: «0 notas… No encontré nada»)",
           all(str(vacia / "notas") in r.stdout and "No encontré ninguna nota" in r.stdout for r in dichos.values())
           and "No encontré nada." not in dichos["salud"].stdout,
           {m: r.stdout[-300:] + r.stderr[-200:] for m, r in dichos.items()})
    otra = t / "otra" / "config.json"
    otra.parent.mkdir()
    otra.write_text("{}", encoding="utf-8")
    probar("los datos van a la carpeta del config", configuracion.cargar(otra)["datos"] == otra.parent,
           configuracion.cargar(otra)["datos"])
    import gasto
    viejo = sys.argv
    sys.argv = ["cerebro.py", "--demo"]
    try:
        elegida = configuracion.archivo()
        casa_demo = configuracion.carpeta_de_claude()
        linea_gasto = gasto.linea_salud()
    finally:
        sys.argv = viejo
    probar("--demo elige demo/config.json aunque haya CEREBRO_CONFIG", elegida == configuracion.DEMO, elegida)
    probar("con --demo, el gasto y las lecciones leen la carpeta de Claude inventada de la demo, no la del usuario",
           casa_demo == configuracion.DEMO.parent / "claude" and "ningún chat" in linea_gasto, (casa_demo, linea_gasto))
    codigo = "import sys; sys.path.insert(0, sys.argv[1]); import hook_evento; print(hook_evento.CARPETA)"
    for caso, valor in (("sin CEREBRO_CONFIG", None), ("con un CEREBRO_CONFIG relativo", "config.json")):
        entorno = {k: v for k, v in os.environ.items() if k != "CEREBRO_CONFIG"}
        if valor:
            entorno["CEREBRO_CONFIG"] = valor
        r = subprocess.run([sys.executable, "-c", codigo, str(CARPETA)], env=entorno, capture_output=True, text=True,
                           timeout=30, cwd=str(t))
        probar(f"el hook {caso} anota junto al programa, aunque el chat esté en otra carpeta",
               r.stdout.strip() == str(CARPETA / "en-vivo"),
               r.stdout + r.stderr)


def revisar_handoffs(t):
    seccion("Handoffs (salen de la configuración; sin ella no hay)")
    carpeta = t / "handoffs"
    carpeta.mkdir()
    for numero, cuerpo in ((1, "Escrito el 2026-09-01 desde el chat de la web. Pide revisar el login."),
                           (2, "Escrito el 2026-09-02 desde el chat del srv. Responde al 1: quedó arreglado."),
                           (3, "Escrito el 2026-09-03 desde el chat de la web. Pide sumar un tope de intentos.")):
        (carpeta / f"PASE_{numero}.md").write_text(f"# Pase {numero}\n\n{cuerpo}\n", encoding="utf-8", newline="\n")
    lados = [{"id": "web", "nombre": "la web"}, {"id": "servidor", "nombre": "el servidor", "palabras": ["servidor", "srv"]}]

    def armar(nombre, handoffs):
        config = {"usuario": "Ana", "fuentes": [{"id": "pases", "nombre": "Pases", "raices": [[str(carpeta), False, ""]],
                                                 "patron": "PASE*.md"}]}
        if handoffs:
            config["handoffs"] = handoffs
        ruta = t / f"{nombre}.json"
        ruta.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8", newline="\n")
        datos = t / f"{nombre}-datos.json"
        r = correr([str(CARPETA / "cerebro.py"), "--json", str(datos), "--salida", str(t / f"{nombre}.html")], espera=300,
                   CEREBRO_CONFIG=str(ruta))
        try:
            return json.loads(datos.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"error": r.stdout[-300:] + r.stderr[-300:]}

    con = armar("con-handoffs", {"prefijo": "PASE", "nombre": "Pases entre chats", "lados": lados})
    nodos = {Path(n["ruta"]).name: n for n in con.get("nodos", [])}
    probar("con «handoffs» en el config, los 3 pases son handoffs",
           len(nodos) == 3 and all(n["tipo"] == "handoff" for n in nodos.values()), con.get("error") or sorted(nodos))
    probar("cada uno sabe de qué lado viene (y «srv» cuenta como el servidor)",
           [nodos.get(f"PASE_{i}.md", {}).get("lado") for i in (1, 2, 3)] == ["web", "servidor", "web"],
           [n.get("lado") for n in nodos.values()])
    por_id = {n["id"]: Path(n["ruta"]).name for n in con.get("nodos", [])}
    responde = {(por_id.get(a["de"]), por_id.get(a["a"])) for a in con.get("aristas", []) if a["clase"] == "responde"}
    probar("el 2 responde al 1", responde == {("PASE_2.md", "PASE_1.md")}, responde)
    salud = con.get("salud", {})
    probar("el 3 queda sin respuesta y el 2, sin acuse",
           [por_id.get(h["id"]) for h in salud.get("handoffsAbiertos", [])] == ["PASE_3.md"]
           and [por_id.get(h["id"]) for h in salud.get("respuestasSinAcuse", [])] == ["PASE_2.md"],
           {k: salud.get(k) for k in ("handoffsAbiertos", "respuestasSinAcuse")})
    probar("la página recibe el nombre, el prefijo y los lados",
           con.get("handoffs") == {"nombre": "Pases entre chats", "prefijo": "PASE",
                                   "lados": [{"id": "web", "nombre": "la web"}, {"id": "servidor", "nombre": "el servidor"}]},
           con.get("handoffs"))
    sin = armar("sin-handoffs", None)
    probar("sin «handoffs» en el config, los mismos archivos son documentos comunes",
           len(sin.get("nodos", [])) == 3 and all(n["tipo"] == "doc" for n in sin.get("nodos", []))
           and not any(a["clase"] in ("responde", "cadena") for a in sin.get("aristas", []))
           and sin.get("handoffs") is None and not sin.get("salud", {}).get("handoffsAbiertos"),
           sin.get("error") or [n["tipo"] for n in sin.get("nodos", [])])
    roto = t / "config-handoffs-roto.json"
    roto.write_text('{"handoffs": {"nombre": "sin prefijo"}}', encoding="utf-8")
    try:
        configuracion.cargar(roto)
        dijo = "no avisó"
    except configuracion.ConfigInvalida as error:
        dijo = str(error)
    probar("«handoffs» sin prefijo dice qué falta", "prefijo" in dijo, dijo)
