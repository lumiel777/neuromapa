from humo.base import *


def evento_de(datos):
    return hook_evento.armar(dict({"session_id": SESION, "cwd": "C:\\demo"}, **datos))


def revisar_hook(t):
    seccion("Hook (qué anota y qué nunca guarda)")
    anidado = ("[" * 200000 + "]" * 200000).encode("ascii")
    rotos = [(nombre, entrada[:12], r.returncode, r.stderr[-80:])
             for nombre in ("hook_inicio.py", "hook_cerebro.py", "hook_servir.py", "hook_choques.py", "hook_parecidas.py",
                            "hook_freno.py", "hook_guardar.py")
             for entrada in (anidado, b"no es json", b"")
             for r in [correr_hook(nombre, entrada, CEREBRO_CONFIG=str(t / "config.json"))]
             if r.returncode or r.stderr or b'"deny"' in r.stdout or b'"block"' in r.stdout]
    probar("una entrada absurda (JSON con 200.000 niveles), una que no es JSON o una vacía no rompen ningún hook: salen "
           "con 0, sin traza y sin frenar nada", not rotos, rotos)
    import textos
    probar("una ruta o una carpeta con caracteres de control no se guarda, y --choques limpia lo que imprime; lo que se "
           "cita de una nota (la pista, --sobre, el médico) tampoco los lleva (antes un título con un código de color de "
           "la consola o un pitido le llegaba así a Claude)",
           hook_evento.ruta_guardable("C:/a\x00b\x1b[31m.md") == "" and hook_evento.ruta_guardable("C:/a b.md") == "C:/a b.md"
           and "c" not in hook_evento.armar({"hook_event_name": "PostToolUse", "tool_name": "Read", "cwd": "C:/x\x1b[2J"})
           and textos.sin_control("a\x1b[31mb\x00") == "a?[31mb?" and textos.citar("Riego\x1b[31m\x07 «ya»") == "«Riego?[31m? ‹ya›»"
           and textos.recortar("a\x07b\u2028c", 80) == "a?b c")
    recomendada = f'Para leer primero:\n  {t / "memoria" / "perfil-ana.md"}:10-22\n'
    casos = [
        ("un comando de Bash", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                "tool_input": {"command": f"curl -H 'Authorization: Bearer {SECRETO}' "
                                                          f"https://example.com/api?token={SECRETO}"},
                                "tool_response": {"stdout": f"respuesta {SECRETO}", "stderr": ""}}),
        ("un mensaje del usuario", {"hook_event_name": "UserPromptSubmit", "prompt": f"mi clave es {SECRETO}"}),
        ("un patrón de Grep", {"hook_event_name": "PostToolUse", "tool_name": "Grep",
                               "tool_input": {"pattern": SECRETO, "path": str(t)}}),
        ("una consulta de ToolSearch", {"hook_event_name": "PostToolUse", "tool_name": "ToolSearch",
                                        "tool_input": {"query": SECRETO}}),
        ("una web", {"hook_event_name": "PostToolUse", "tool_name": "WebFetch",
                     "tool_input": {"url": f"https://example.com/{SECRETO}?clave={SECRETO}",
                                    "prompt": f"resumí {SECRETO}"}}),
        ("una edición", {"hook_event_name": "PostToolUse", "tool_name": "Edit",
                         "tool_input": {"file_path": str(t / "memoria" / "perfil-ana.md"), "old_string": SECRETO,
                                        "new_string": f"{SECRETO}\notra"}}),
        ("un archivo nuevo", {"hook_event_name": "PostToolUse", "tool_name": "Write",
                              "tool_input": {"file_path": str(t / "nuevo.md"), "content": SECRETO}}),
        ("una consulta al cerebro", {"hook_event_name": "PostToolUse", "tool_name": "PowerShell",
                                     "tool_input": {"command": f"python cerebro.py --sobre \"tema {SECRETO}\""},
                                     "tool_response": {"stdout": recomendada}}),
        ("una herramienta MCP con una dirección en file_path",
         {"hook_event_name": "PostToolUse", "tool_name": "mcp__otro__subir",
          "tool_input": {"file_path": f"https://ejemplo.invalid/subir?token={SECRETO}"}}),
        ("un motivo de compactación inventado", {"hook_event_name": "PreCompact", "trigger": f"{SECRETO} algo"}),
        ("una regla por carpeta cargada", {"hook_event_name": "InstructionsLoaded", "load_reason": "path_glob_match",
                                           "file_path": str(t / ".claude" / "rules" / "semillas.md"),
                                           "globs": [f"datos/{SECRETO}/**"], "memory_type": f"Project {SECRETO}",
                                           "trigger_file_path": str(t / "datos" / f"{SECRETO}.txt")}),
        ("un nombre de herramienta enorme", {"hook_event_name": "PostToolUse", "tool_name": f'mcp__otro__{"a" * 3000}'}),
        ("una consulta desde el plugin", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                          "tool_input": {"command": f"neuromapa --sobre \"tema {SECRETO}\""},
                                          "tool_response": {"stdout": recomendada}}),
        ("una consulta por el lanzador", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                          "tool_input": {"command": "sh \"C:/x/plugin/bin/neuromapa\" --salud"}}),
        ("un comando en una carpeta llamada Neuromapa", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                                         "tool_input": {"command": "cd D:/Neuromapa && ls"}}),
        ("una consulta del gasto", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                    "tool_input": {"command": "neuromapa --gasto 3"}}),
        ("un echo con una palabra terminada en .md", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                                      "tool_input": {"command": f"echo 'mi nota {SECRETO}.md'"}}),
        ("un mensaje de commit que nombra un .md", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                                    "tool_input": {"command": f"git commit -m \"arreglo en {SECRETO}.md\""}}),
        ("el cuerpo de un heredoc", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                     "tool_input": {"command": f"cat <<'EOF' > notas/nueva.md\nlinea con {SECRETO}.md\nEOF"}}),
        ("un here-string de PowerShell", {"hook_event_name": "PostToolUse", "tool_name": "PowerShell",
                                          "tool_input": {"command": f"git commit -m @'\nmensaje {SECRETO}.md\n'@"}}),
        ("una dirección sin esquema con IP", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                              "tool_input": {"command": f"ls 10.0.0.5/{SECRETO}/notas.md"}}),
        ("un pedido de red a un nombre sin punto", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                                    "tool_input": {"command": f"curl intranet/{SECRETO}/notas.md"}}),
        ("un pedido de red de PowerShell", {"hook_event_name": "PostToolUse", "tool_name": "PowerShell",
                                            "tool_input": {"command": f"Invoke-WebRequest localhost:8080/{SECRETO}.md"}}),
        ("una palabra suelta terminada en .md que no es un archivo",
         {"hook_event_name": "PostToolUse", "tool_name": "Bash",
          "tool_input": {"command": f"gh issue create --title {SECRETO}.md"}}),
        ("una herramienta MCP con texto libre en file_path",
         {"hook_event_name": "PostToolUse", "tool_name": "mcp__otro__traducir",
          "tool_input": {"file_path": f"{SECRETO} traducime esto, mi pin es 4455"}}),
        ("un commit cuyo mensaje parece una ruta absoluta", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                                             "tool_input": {"command": f"git commit -m \"/docs/{SECRETO}.md\""}}),
        ("una ruta de red como argumento", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                            "tool_input": {"command": f"node f.js //evil.invalid/{SECRETO}/token.md"}}),
        ("una sesión, un agente y un tipo de agente con texto raro",
         {"hook_event_name": "PostToolUse", "tool_name": "Read", "session_id": f"<{SECRETO}>",
          "agent_id": f"a b {SECRETO}", "agent_type": f"tipo\n{SECRETO}"}),
        ("un comando que falló", {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
                                  "tool_input": {"command": f"python x.py {SECRETO}"},
                                  "error": f"Exit code 2\nTraceback {SECRETO}", "duration_ms": 1234}),
        ("un comando de fondo sin resultados", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                                "tool_input": {"command": f"grep -rn {SECRETO} src", "run_in_background": True},
                                                "tool_response": {"stdout": "", "backgroundTaskId": "b1",
                                                                  "returnCodeInterpretation": "No matches found"},
                                                "duration_ms": 4321}),
    ]
    eventos = {}
    for nombre, datos in casos:
        evento = evento_de(datos)
        eventos[nombre] = evento
        probar(f"no guarda el texto de {nombre}", SECRETO not in json.dumps(evento, ensure_ascii=False), evento)
    tocados = []
    original_isfile = os.path.isfile
    os.path.isfile = lambda ruta: tocados.append(str(ruta)) or original_isfile(ruta)
    try:
        for comando, cwd in (("cd //evil.invalid/compartida && cat notas.md", "C:\\demo"),
                             ("Set-Location \\\\evil.invalid\\compartida; Get-Content notas.md", "C:\\demo"),
                             ("cat notas.md", "\\\\evil.invalid\\compartida")):
            hook_evento.notas_de_comando(comando, cwd)
    finally:
        os.path.isfile = original_isfile
    probar("una carpeta de red en un comando no hace que el hook se conecte a ese servidor (lo hacía antes de que el "
           "usuario aprobara el comando, y Windows le ofrece la sesión)",
           not [r for r in tocados if r.replace("/", "\\").startswith("\\\\")], tocados)
    real = t / "memoria" / "perfil-ana.md"
    probar("una nota que existe, nombrada con su ruta absoluta en un comando, se sigue anotando",
           hook_evento.notas_de_comando(f'cat "{real}"', None)[1] == [str(real)],
           hook_evento.notas_de_comando(f'cat "{real}"', None))
    probar("del mensaje del usuario guarda solo el largo",
           eventos["un mensaje del usuario"].get("n") == len(f"mi clave es {SECRETO}"), eventos["un mensaje del usuario"])
    probar("de la web guarda solo el dominio", eventos["una web"].get("p") == "example.com", eventos["una web"])
    cargada = {k: v for k, v in eventos["una regla por carpeta cargada"].items() if k != "t"}
    probar("de una regla por carpeta que Claude Code cargó guarda solo cuál es (ni su texto, ni el patrón, ni el archivo que "
           "la disparó); las instrucciones que se cargan por otro motivo, como al empezar, no se anotan",
           cargada == {"s": SESION[:8], "e": "regla", "h": "", "k": "regla", "c": "C:\\demo",
                       "f": str(t / ".claude" / "rules" / "semillas.md")}
           and hook_evento.se_anota({"hook_event_name": "InstructionsLoaded", "load_reason": "path_glob_match"})
           and not hook_evento.se_anota({"hook_event_name": "InstructionsLoaded", "load_reason": "session_start"})
           and not hook_evento.se_anota({"hook_event_name": "InstructionsLoaded"})
           and hook_evento.se_anota({"tool_name": "Read"}) and hook_evento.se_anota({"hook_event_name": "Stop"})
           and not hook_evento.se_anota({"hook_event_name": "Inventado"}), cargada)
    probar("de la edición guarda solo cuántas líneas", eventos["una edición"].get("m") == [2, 1], eventos["una edición"])
    fallido, fondo = eventos["un comando que falló"], eventos["un comando de fondo sin resultados"]
    probar("de un comando guarda su familia, cuánto tardó, con qué código salió, si fue de fondo y si no encontró nada "
           "(números y sí/no; nunca el comando, su salida ni el texto del error)",
           fallido.get("b") == "python" and fallido.get("xc") == 2 and fallido.get("d") == 1234
           and fondo.get("b") == "busca" and fondo.get("bg") == 1 and fondo.get("nr") == 1 and fondo.get("d") == 4321,
           (fallido, fondo))
    esperadas = {"cd D:/x && python a.py": "python", "cat a.txt | head -5": "lee", "grep -n hola f.txt": "busca",
                 "ls -la": "lista", "Get-ChildItem C:/x": "lista", "npm install": "node", "VAR=1 node x.js": "node",
                 "curl https://example.com": "red", "rm -rf build": "archivos", "sed -n 1,5p f.txt": "lee",
                 "sed -i s/a/b/ f.txt": "archivos", "./correr.sh": "script", "powershell -File x.ps1": "script",
                 "tasklist": "sistema", "echo hola": "otro", "git commit -m x": "commit", "git status": "git",
                 "dotnet build": "compila", "": "otro"}
    familias = {c: hook_evento.clase_comando(c) for c in esperadas}
    probar("cada comando cae en su familia por el primer programa (saltea cd y asignaciones; commit, compila, prueba, "
           "git, base y cerebro siguen primero)", familias == esperadas,
           {c: (f, esperadas[c]) for c, f in familias.items() if f != esperadas[c]})
    gasto_consultado = eventos["una consulta del gasto"]
    probar("--gasto también cuenta como consulta (una sola lista de opciones para el hook, el medidor y la página)",
           gasto_consultado.get("k") == "consulta" and gasto_consultado.get("p") == "gasto", gasto_consultado)
    heredoc = eventos["el cuerpo de un heredoc"]
    probar("de un comando con texto adentro guarda solo el archivo que toca (el destino del heredoc)",
           [os.path.basename(r) for r in heredoc.get("fs") or []] == ["nueva.md"], heredoc)
    de_red = [eventos[n] for n in ("una dirección sin esquema con IP", "un pedido de red a un nombre sin punto",
                                   "un pedido de red de PowerShell", "una palabra suelta terminada en .md que no es un archivo")]
    raros = eventos["una sesión, un agente y un tipo de agente con texto raro"]
    probar("no toma como ruta una dirección con IP o localhost, nada de un comando de red, ni una palabra suelta que no "
           "es un archivo; la sesión, el agente y su tipo con texto raro quedan vacíos",
           not any(e.get("f") or e.get("fs") for e in de_red) and not raros.get("s") and "a" not in raros
           and "at" not in raros, (de_red, raros))
    existe = t / "proyecto" / "LEEME-humo.md"
    existe.write_text("x", encoding="utf-8")
    suelta = hook_evento.armar({"hook_event_name": "PostToolUse", "tool_name": "Bash", "session_id": SESION,
                                "cwd": str(t / "proyecto"), "tool_input": {"command": "python armar.py LEEME-humo.md"}})
    existe.unlink()
    probar("una palabra suelta que sí es un archivo de la carpeta se sigue anotando",
           [os.path.basename(r) for r in suelta.get("fs") or [suelta.get("f", "")] if r] == ["LEEME-humo.md"], suelta)
    mcp = eventos["una herramienta MCP con una dirección en file_path"]
    probar("una dirección web que llega como ruta no se guarda, un motivo desconocido queda «otro» y el nombre de la "
           "herramienta tiene tope",
           "f" not in mcp and eventos["un motivo de compactación inventado"].get("p") == "otro"
           and len(eventos["un nombre de herramienta enorme"].get("h", "")) <= 120,
           (mcp, eventos["un motivo de compactación inventado"], len(eventos["un nombre de herramienta enorme"].get("h", ""))))
    consulta = eventos["una consulta al cerebro"]
    probar("la consulta al cerebro queda con el nombre de la opción",
           consulta.get("k") == "consulta" and consulta.get("p") == "sobre", consulta)
    probar("y con la nota que el cerebro recomendó",
           any(str(r).endswith("perfil-ana.md") for r in consulta.get("fs") or []), consulta)
    plugin, lanzador, carpeta = (eventos["una consulta desde el plugin"], eventos["una consulta por el lanzador"],
                                 eventos["un comando en una carpeta llamada Neuromapa"])
    probar("en el plugin, «neuromapa --sobre» y el lanzador también cuentan como consultas; una carpeta llamada así, no",
           plugin.get("k") == "consulta" and plugin.get("p") == "sobre"
           and any(str(r).endswith("perfil-ana.md") for r in plugin.get("fs") or [])
           and lanzador.get("k") == "consulta" and lanzador.get("p") == "salud" and carpeta.get("k") != "consulta",
           (plugin, lanzador, carpeta))

    registro = Path(hook_evento.REGISTRO)
    lectura = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Read", "session_id": SESION,
                          "cwd": str(t), "tool_input": {"file_path": str(t / "memoria" / "arreglo-login.md")},
                          "tool_response": {"type": "text", "file": {"startLine": 1, "numLines": 9, "totalLines": 9}}})
    del_sistema = [json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": SESION, "cwd": str(t), "prompt": p})
                   for p in ("<task-notification>\n<status>completed</status>\n</task-notification>",
                             'Another Claude session sent a message:\n<agent-message from="a1">\nlisto\n</agent-message>')]
    pedido = json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": SESION, "cwd": str(t), "prompt": "hola"})
    salida = io.StringIO()
    for entrada in (pedido, lectura, "no es json", "{}", *del_sistema):
        viejo = sys.stdin
        sys.stdin = io.TextIOWrapper(io.BytesIO(entrada.encode("utf-8")), encoding="utf-8")
        try:
            with contextlib.redirect_stdout(salida):
                hook_evento.main()
        finally:
            sys.stdin = viejo
    crudo = registro.read_bytes() if registro.exists() else b""
    lineas = [linea for linea in crudo.split(b"\r\n") if linea]
    probar("main() escribe una línea para un mensaje y otra para una lectura, y nada con basura, vacío, un aviso de "
           "tarea o el informe de un agente (no son mensajes del usuario)",
           len(lineas) == 2 and json.loads(lineas[0]).get("e") == "usuario", crudo[:300])
    probar("cada línea termina en CRLF, como el registro real", crudo.endswith(b"\r\n") and crudo.count(b"\n") == len(lineas))
    ultimo = json.loads(lineas[-1]) if lineas else {}
    probar("la lectura queda con su nota y su tramo",
           ultimo.get("k") == "leer" and str(ultimo.get("f", "")).endswith("arreglo-login.md")
           and ultimo.get("r") == [1, 9, 9], ultimo)
    probar("main() no imprime nada (lo impreso entra al contexto de Claude)", salida.getvalue() == "", salida.getvalue())
    os.environ["NEUROMAPA_PRUEBA"] = "1"
    try:
        de_prueba = evento_de({"hook_event_name": "UserPromptSubmit", "prompt": "hola"})
    finally:
        del os.environ["NEUROMAPA_PRUEBA"]
    probar("con NEUROMAPA_PRUEBA=1 (las corridas de medir) cada evento queda marcado como prueba; sin eso, no",
           de_prueba.get("z") == 1 and "z" not in evento_de({"hook_event_name": "UserPromptSubmit", "prompt": "hola"}),
           de_prueba)
    pista = hook_evento.aviso(SESION, str(t), [str(t / "memoria" / "arreglo-login.md"), f"https://x.invalid/{SECRETO}"],
                              ["login.py"])
    probar("la pista del hook guarda solo las rutas de las notas y los nombres del código (nunca una dirección web)",
           pista.get("e") == "aviso" and pista.get("fc") == ["login.py"] and SECRETO not in json.dumps(pista)
           and [os.path.basename(r) for r in pista.get("fs", ())] == ["arreglo-login.md"], pista)
    indice_md = str(t / "memoria" / "MEMORY.md")
    con_motivos = hook_evento.aviso(SESION, str(t), [str(t / "memoria" / "arreglo-login.md"), f"https://x.invalid/{SECRETO}",
                                                     indice_md], [],
                                    motivos=[("p", 10, 14, ""), ("i", 1, 2, f"https://x.invalid/{SECRETO}"),
                                             ("zz", -3, "x", indice_md)])
    probar("la pista guarda por qué eligió cada nota (palabras, índice o aprendida, el tramo y la nota de origen), "
           "alineado con sus rutas y solo con códigos, números y rutas",
           con_motivos.get("fp") == [["p", 10, 14, ""], ["p", 0, 0, indice_md]] and len(con_motivos.get("fs", ())) == 2
           and SECRETO not in json.dumps(con_motivos), con_motivos.get("fp"))
    marcado = hook_evento.aviso(SESION, str(t), [str(t / "memoria" / "arreglo-login.md")], [], sin_aprendido=True)
    probar("un pedido del modo de comparación queda marcado en el aviso («sa»: 1) y los demás no",
           marcado.get("sa") == 1 and "sa" not in con_motivos, marcado)

    r = correr_hook("hook_cerebro.py", b"no es json", espera=30)
    probar("hook_cerebro.py con basura sale con 0 y sin imprimir nada",
           r.returncode == 0 and not r.stdout and not r.stderr, (r.returncode, r.stdout[:200], r.stderr[:200]))
    paso_roto = ("import sys; sys.path.insert(0, sys.argv[1]); import hooks_comun; "
                 "hooks_comun.contexto('PostToolUse', (lambda: 1 / 0, lambda: 'sigue'))")
    callado, depurado = [subprocess.run([sys.executable, "-c", paso_roto, str(CARPETA)], capture_output=True, text=True,
                                        timeout=30, env=dict(os.environ, NEUROMAPA_DEPURAR=valor))
                         for valor in ("", "1")]
    probar("si un paso de un hook falla, los demás siguen; el error se ve solo con NEUROMAPA_DEPURAR=1",
           "sigue" in callado.stdout and not callado.stderr
           and "ZeroDivisionError" in depurado.stderr and "sigue" in depurado.stdout,
           (callado.stdout[-120:], callado.stderr[-120:], depurado.stderr[-120:]))
    import hooks_comun
    fallas = t / "fallas-humo"
    fallas.mkdir()
    for _ in range(2):
        try:
            buscador.idf_de(f"{SECRETO} texto", 1)
        except TypeError:
            hooks_comun.anotar_falla(sys.exc_info(), carpeta=str(fallas))
    try:
        raise ValueError(SECRETO)
    except ValueError:
        hooks_comun.anotar_falla(sys.exc_info(), ahora=time.time() - 8 * 86400, carpeta=str(fallas))
    linea = hooks_comun.linea_salud(carpeta=str(fallas))
    crudo = (fallas / hooks_comun.FALLAS).read_text(encoding="utf-8")
    probar("cada falla de un hook queda contada en en-vivo/fallas.json (solo dónde y de qué tipo, nunca el mensaje) y "
           "--salud la muestra; lo de hace más de 7 días se olvida (antes no quedaban en ningún lado)",
           "TypeError en buscador.py:" in linea and "2 veces" in linea and "ValueError" not in linea
           and SECRETO not in crudo and hooks_comun.linea_salud(carpeta=str(t / "claude-vacia")) == "", (linea, crudo))


def revisar_librerias(t):
    seccion("Bibliotecas locales (vendor: d3 y marked adentro de la página, sin internet)")
    import base64
    import hashlib
    vendor = t / "vendor"
    vendor.mkdir(exist_ok=True)
    codigo = b"window.equis = 1;"
    huella = f'sha384-{base64.b64encode(hashlib.sha384(codigo).digest()).decode("ascii")}'
    html = f"const URL_X = 'https://ejemplo.invalid/equis.min.js';\n[URL_X]: '{huella}',\n"
    (vendor / "equis.min.js").write_bytes(codigo)
    probar("con la copia local y la huella justa, la mete en la página",
           "window.equis = 1;" in nucleo.librerias_locales(html, vendor))
    (vendor / "equis.min.js").write_bytes(b"window.equis = 2;")
    with contextlib.redirect_stderr(io.StringIO()) as aviso:
        adentro_mal = nucleo.librerias_locales(html, vendor)
    probar("si la copia no coincide con la huella, no la usa y avisa", adentro_mal == "" and "huella" in aviso.getvalue(),
           aviso.getvalue()[:200])
    probar("sin copia local, la página sigue igual (baja de internet)", nucleo.librerias_locales(html, t / "no-hay") == "")
    plantilla = plantilla_entera(CARPETA / "plantilla.html")
    reales = nucleo.librerias_locales(plantilla, CARPETA / "vendor")
    archivos = sorted(p.name for p in (CARPETA / "vendor").glob("*.js"))
    licencias = (CARPETA / "vendor" / "LICENCIAS.md").read_text(encoding="utf-8")
    orden = [reales.find(f"https://d3js.org/{m}/") for m in ("d3-dispatch", "d3-selection", "d3-transition", "d3-zoom")]
    probar("el programa trae en vendor/ los 11 módulos de d3 que usa la página y marked, con la huella que espera la "
           "página, en el orden de sus dependencias, cada uno de menos de 256 KiB y con su licencia (el mapa anda sin "
           "internet; antes, el d3 entero pesaba 273 KiB)",
           reales.count("<script") == 12 and min(orden) >= 0 and orden == sorted(orden)
           and all((CARPETA / "vendor" / n).stat().st_size < 256 * 1024 for n in archivos)
           and all(n.split(".")[0] in licencias for n in archivos), (reales.count("<script"), orden, archivos))


def revisar_candado_posix(t):
    seccion("Candado del hook en Mac y Linux (fcntl de mentira: acá no hay fcntl)")

    class FcntlFalso:
        LOCK_EX, LOCK_NB, LOCK_UN = 2, 4, 8

        def __init__(self):
            self.ocupado = False
            self.llamadas = []

        def flock(self, fd, modo):
            self.llamadas.append(modo)
            if modo & self.LOCK_EX:
                if self.ocupado:
                    raise OSError("ocupado")
                self.ocupado = True
            elif modo == self.LOCK_UN:
                self.ocupado = False

    falso = FcntlFalso()
    import archivos
    antes = (archivos.msvcrt, archivos.fcntl, hook_evento.ESPERA_CANDADO)
    archivos.msvcrt, archivos.fcntl, hook_evento.ESPERA_CANDADO = None, falso, 0.05
    try:
        primero = hook_evento.tomar_candado()
        segundo = hook_evento.tomar_candado()
        hook_evento.soltar_candado(primero)
        tercero = hook_evento.tomar_candado()
        hook_evento.soltar_candado(tercero)
    finally:
        archivos.msvcrt, archivos.fcntl, hook_evento.ESPERA_CANDADO = antes
    probar("toma el candado con flock, lo niega si está ocupado y lo suelta",
           primero is not None and segundo is None and tercero is not None and not falso.ocupado
           and falso.llamadas[0] == falso.LOCK_EX | falso.LOCK_NB and falso.LOCK_UN in falso.llamadas, falso.llamadas)
    registro = Path(hook_evento.REGISTRO)
    archivos.msvcrt, archivos.fcntl, hook_evento.ESPERA_CANDADO = None, falso, 0.05
    try:
        ocupado = hook_evento.tomar_candado()
        previo = registro.read_bytes() if registro.exists() else b""
        try:
            hook_evento.escribir(b'{"t":1}\r\n')
            descartado = False
        except hook_evento.CandadoOcupado:
            descartado = True
        despues = registro.read_bytes() if registro.exists() else b""
        hook_evento.soltar_candado(ocupado)
    finally:
        archivos.msvcrt, archivos.fcntl, hook_evento.ESPERA_CANDADO = antes
    probar("si el candado sigue ocupado, el evento no se escribe sin él ni se rota (así se perdía el 21 %): se descarta "
           "y queda anotado como falla", descartado and despues == previo, (descartado, len(previo), len(despues)))
    guardado = registro.read_bytes() if registro.exists() else b""
    try:
        registro.write_bytes(guardado + b'{"t":1,"s":"cortado","e":"po')
        hook_evento.escribir(b'{"t":2,"s":"sigue001","e":"post"}\r\n')
        cola = registro.read_bytes()[len(guardado):].split(b"\r\n")
    finally:
        registro.write_bytes(guardado)
    probar("si el renglón anterior quedó cortado (disco lleno, hook cortado por tiempo), el evento siguiente empieza en un "
           "renglón nuevo y no se pierde", cola[1] == b'{"t":2,"s":"sigue001","e":"post"}', cola)


def revisar_permisos(t):
    seccion("Permisos de las carpetas (que otra cuenta de la PC no pueda escribir ni leer los datos)")
    import permisos

    def abrir(carpeta):
        if os.name == "nt":
            subprocess.run(["icacls", str(carpeta), "/grant", "*S-1-5-11:(OI)(CI)M"], capture_output=True, timeout=60)
        else:
            os.chmod(carpeta, 0o777)

    abierta = t / "permisos-abierta"
    abierta.mkdir()
    abrir(abierta)
    adentro = abierta / "datos" / "en-vivo"
    permisos.crear(adentro)
    (adentro / "clave.txt").write_text("x", encoding="utf-8")
    probar("ve cuando otra cuenta puede escribir en una carpeta",
           bool(permisos.ajenos(abierta)), permisos.ajenos(abierta))
    probar("lo que crea Neuromapa nace cerrado aunque la carpeta de arriba esté abierta (y lo de adentro hereda)",
           permisos.ajenos(abierta / "datos") == [] and permisos.ajenos(adentro) == []
           and (os.name != "nt" or permisos.ajenos(adentro / "clave.txt") == []),
           (permisos.ajenos(abierta / "datos"), permisos.ajenos(adentro)))
    cerrada = t / "permisos-cerrada"
    permisos.crear(cerrada)
    linea = permisos.linea_salud(abierta, cerrada)
    probar("--salud avisa la carpeta abierta una vez, con el comando para cerrarla, y calla si todo está cerrado",
           linea.startswith("AVISO") and linea.count(str(abierta)) == 2 and "en-vivo" not in linea
           and "hooks" not in linea and ("icacls" in linea if os.name == "nt" else "chmod 700" in linea)
           and permisos.linea_salud(cerrada, cerrada) == "", linea)
    probar("si también el código está abierto, lo dice", "hooks" in permisos.linea_salud(cerrada, abierta))
    permisos.cerrar(abierta)
    probar("cerrar deja la carpeta solo para la cuenta propia", permisos.ajenos(abierta) == [], permisos.ajenos(abierta))
    if os.name == "nt":
        legible = t / "permisos-legible"
        legible.mkdir()
        subprocess.run(["icacls", str(legible), "/grant", "*S-1-5-32-545:(OI)(CI)RX"], capture_output=True, timeout=60)
        linea = permisos.linea_salud(legible, cerrada)
        probar("--salud avisa también si otras cuentas pueden leer la carpeta de datos (la página con todas las notas y la "
               "clave), aunque no puedan escribir (antes callaba)",
               permisos.ajenos(legible) == [] and bool(permisos.ajenos(legible, leer=True))
               and linea.startswith("AVISO") and "pueden leer" in linea and "escribir" not in linea
               and linea.count(str(legible)) == 2 and "icacls" in linea, linea)
        permisos.cerrar(legible)
        probar("y calla cuando se cierra", permisos.linea_salud(legible, cerrada) == "",
               permisos.linea_salud(legible, cerrada))


def revisar_exportar(t):
    try:
        import exportar
    except ImportError:
        return
    seccion("Exportar la copia pública (que nunca borre lo que no hizo)")
    ajena = t / "exportar-ajena"
    ajena.mkdir()
    (ajena / "mio.txt").write_text("no me borres", encoding="utf-8")
    vacia = t / "exportar-vacia"
    vacia.mkdir()
    anterior = t / "exportar-anterior"
    (anterior / ".claude-plugin").mkdir(parents=True)
    (anterior / ".claude-plugin" / "plugin.json").write_text('{"name": "neuromapa"}', encoding="utf-8")
    (anterior / "cerebro.py").write_text("", encoding="utf-8")
    prohibidas = [Path(t.anchor), Path.home(), CARPETA.parent, CARPETA, CARPETA / "demo", ajena, ajena / "mio.txt"]
    permitidas = [t / "exportar-nueva", vacia, anterior]
    probar("exportar solo usa una carpeta nueva, vacía o una copia anterior; nunca la raíz, tu usuario, la que contiene "
           "al Cerebro ni una con cosas ajenas (antes vaciaba lo que hubiera)",
           all(exportar.motivo_para_no_usar(p) for p in prohibidas)
           and not any(exportar.motivo_para_no_usar(p) for p in permitidas),
           [str(p) for p in prohibidas if not exportar.motivo_para_no_usar(p)]
           + [str(p) for p in permitidas if exportar.motivo_para_no_usar(p)])
    r = correr([str(CARPETA / "herramientas" / "exportar.py"), "--destino", str(ajena), "--autor", "X", "--repo", "x/y"])
    probar("con una carpeta ajena, exportar frena sin tocar nada", r.returncode == 1 and (ajena / "mio.txt").is_file(),
           r.stdout[-300:])
    copia = t / "exportar-copia"
    r = correr([str(CARPETA / "herramientas" / "exportar.py"), "--destino", str(copia), "--autor", "Prueba", "--repo",
                "prueba/neuromapa"], espera=300)
    raiz = {p.name for p in copia.iterdir()} if copia.is_dir() else set()
    privados = sorted(raiz & {"config.json", "CLAUDE.md", "RETOMAR.md", "RETOMAR-historia.md", "en-vivo", "ideas",
                              "medicion", "hechos.json", "sugerencias.json", "publico"})
    try:
        autor = json.loads((copia / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["author"]["name"]
    except (OSError, ValueError, KeyError, TypeError):
        autor = None
    try:
        misma_pagina = plantilla_entera(copia / "plantilla.html") == plantilla_entera(CARPETA / "plantilla.html")
    except OSError:
        misma_pagina = False
    probar("exportar arma la copia pública sin config.json, en-vivo, ideas, RETOMAR ni el CLAUDE.md privado, con el "
           "autor puesto, sin rastros privados, con la prueba de humo entera (la entrada y sus partes) y con la "
           "página entera (la plantilla y el JavaScript de pagina/)",
           r.returncode == 0 and "Sin rastros privados" in r.stdout and not privados and autor == "Prueba"
           and (copia / "cerebro.py").is_file() and (copia / "demo" / "config.json").is_file()
           and (copia / "herramientas" / "prueba_humo.py").is_file()
           and (copia / "herramientas" / "humo" / "base.py").is_file()
           and (copia / "herramientas" / "humo" / "__init__.py").is_file() and misma_pagina,
           (r.returncode, r.stdout[-300:], privados, autor, misma_pagina))
    rastro = t / "exportar-rastro"
    (rastro / "docs").mkdir(parents=True)
    nombre, carpeta = "Lum" + "iel", "D:\\" + "Cerebro"
    (rastro / "docs" / "nota.md").write_text(f"Lo armó {nombre}, en {carpeta}\n", encoding="utf-8")
    hallados = exportar.barrer(rastro)
    probar("el barrido de la copia pública encuentra un nombre y una ruta de esta PC (y entonces exportar frena)",
           any(nombre in h for h in hallados) and any("Cerebro" in h for h in hallados), hallados)
    fuente = t / "exportar-publico"
    (fuente / "publico" / "docs").mkdir(parents=True)
    for relativa in (".gitignore", "README.md", "docs/guía.md"):
        (fuente / "publico" / relativa).write_text("__pycache__/\n" if relativa == ".gitignore" else "hola\n",
                                                    encoding="utf-8")
    try:
        subprocess.run(["git", "init", "-q", str(fuente)], capture_output=True, timeout=30, check=True)
        subprocess.run(["git", "-C", str(fuente), "add", "publico"], capture_output=True, timeout=30, check=True)
        (fuente / "publico" / "borrador.md").write_text("sin terminar\n", encoding="utf-8")
        (fuente / "publico" / "docs" / "nota.tmp").write_text("", encoding="utf-8")
        (fuente / "publico" / "__pycache__").mkdir()
        (fuente / "publico" / "__pycache__" / "x.pyc").write_bytes(b"")
        vistos = exportar.de_publico(fuente)
    except (OSError, subprocess.SubprocessError, AttributeError) as error:
        vistos = f"no anduvo: {error}"
    probar("de publico/ exportar copia solo lo que está en git: un borrador, un .tmp o un __pycache__ que caigan ahí no "
           "se publican, y un nombre con tilde sale bien (antes copiaba todo lo del disco)",
           vistos == [".gitignore", "README.md", "docs/guía.md"], vistos)
    versionada = t / "exportar-con-git"
    shutil.copytree(anterior, versionada)
    shutil.copy2(CARPETA / "publico" / ".gitignore", versionada / ".gitignore")
    git = ["git", "-C", str(versionada), "-c", "user.name=prueba", "-c", "user.email=prueba@ejemplo.invalid",
           "-c", "commit.gpgsign=false"]
    estados = {}
    try:
        subprocess.run(["git", "init", "-q", str(versionada)], capture_output=True, timeout=30, check=True)
        subprocess.run([*git, "add", "-A"], capture_output=True, timeout=30, check=True)
        subprocess.run([*git, "commit", "-q", "-m", "copia"], capture_output=True, timeout=30, check=True)
        (versionada / "__pycache__").mkdir()
        (versionada / "__pycache__" / "cerebro.pyc").write_bytes(b"")
        estados["limpia"] = exportar.motivo_para_no_usar(versionada)
        (versionada / "hechos.json").write_text("{}", encoding="utf-8")
        estados["con hechos.json"] = exportar.motivo_para_no_usar(versionada)
        (versionada / "hechos.json").unlink()
        (versionada / "PENDIENTE.txt").write_text("sin commit", encoding="utf-8")
        estados["con un archivo nuevo"] = exportar.motivo_para_no_usar(versionada)
        r = correr([str(CARPETA / "herramientas" / "exportar.py"), "--destino", str(versionada), "--autor", "X", "--repo",
                    "x/y"])
        estados["exportar"] = r.returncode == 1 and (versionada / "PENDIENTE.txt").is_file()
    except (OSError, subprocess.SubprocessError) as error:
        estados["git"] = f"no anduvo: {error}"
    probar("exportar no vacía una copia anterior con cosas sin commit, ni con datos que git deja afuera, pero sí una limpia "
           "(antes las borraba sin avisar)",
           estados.get("limpia") == "" and estados.get("con hechos.json") and estados.get("con un archivo nuevo")
           and estados.get("exportar") is True, estados)
    flujo = (CARPETA / "publico" / ".github" / "workflows" / "pruebas.yml").read_text(encoding="utf-8").splitlines()
    pasos = [i for i, linea in enumerate(flujo) if "uses: actions/checkout@" in linea]
    probar("el CI de la copia pública baja el repo sin dejar el token de GitHub guardado en el clon",
           pasos and all(any("persist-credentials: false" in linea for linea in flujo[i + 1:i + 3]) for i in pasos),
           [flujo[i:i + 3] for i in pasos])
    clon = t / "exportar-gitignore"
    clon.mkdir()
    shutil.copy2(CARPETA / "publico" / ".gitignore", clon / ".gitignore")
    privados = ["config.json", "hechos.json", "sugerencias.json", "cerebro.html", "problemas.json", "en-vivo/clave.txt"]
    de_la_demo = ["demo/config.json", "demo/hechos.json", "demo/sugerencias.json"]
    try:
        subprocess.run(["git", "init", "-q", str(clon)], capture_output=True, timeout=30, check=True)
        r = subprocess.run(["git", "-C", str(clon), "check-ignore", *privados, *de_la_demo], capture_output=True, text=True,
                           timeout=30)
        ignorados = set(r.stdout.split())
    except (OSError, subprocess.SubprocessError) as error:
        ignorados = {f"git no anduvo: {error}"}
    probar("en un clon de la copia pública, git deja afuera el config, hechos.json y sugerencias.json de quien lo usa "
           "(antes se subían con un git add), pero no los de la demo", ignorados == set(privados),
           sorted(ignorados ^ set(privados)))


def revisar_chequeo(t):
    seccion("El chequeo de la instalación (neuromapa chequeo)")
    try:
        chequeo = importlib.import_module("chequeo")
    except ImportError:
        probar("existe el chequeo de la instalación", False, "no está chequeo.py")
        return
    carpeta = t / "chequeo"
    (carpeta / "codigo").mkdir(parents=True)
    script = carpeta / "codigo" / "hook_cerebro.py"
    script.write_text("", encoding="utf-8")
    python = sys.executable

    def ajustes(nombre, datos):
        casa = carpeta / nombre
        casa.mkdir()
        (casa / "settings.json").write_text(json.dumps(datos), encoding="utf-8")
        return casa

    def hook(ruta, ejecutable=python):
        return {"hooks": [{"type": "command", "command": f'"{ejecutable}" -I -S "{ruta}"'}]}

    todos = {"hooks": {"PostToolUse": [hook(carpeta / "codigo" / f"{h}.py") for h in chequeo.HOOKS]}}
    for h in chequeo.HOOKS:
        (carpeta / "codigo" / f"{h}.py").write_text("", encoding="utf-8")
    casos = {
        "bien": ajustes("bien", todos),
        "doble": ajustes("doble", dict(todos, enabledPlugins={"neuromapa@neuromapa": True})),
        "plugin": ajustes("plugin", {"enabledPlugins": {"neuromapa@neuromapa": True}}),
        "nada": ajustes("nada", {}),
        "movido": ajustes("movido", {"hooks": {"Stop": [hook(carpeta / "viejo" / "hook_cerebro.py"),
                                                       hook(script, str(carpeta / "Python39" / "python.exe"))]}}),
    }
    tonos = {nombre: [tono for tono, _ in chequeo.revisar_hooks(casa)] for nombre, casa in casos.items()}
    textos = {nombre: " ".join(texto for _, texto in chequeo.revisar_hooks(casa)) for nombre, casa in casos.items()}
    probar("el chequeo dice si los hooks están: todos a mano o por el plugin está bien; a mano y por el plugin a la vez, "
           "o ninguno, falta; y avisa los que apuntan a un archivo o a un Python que ya no están (la carpeta se movió)",
           tonos["bien"] == ["bien"] and tonos["plugin"] == ["bien"] and tonos["doble"] == ["falta"]
           and tonos["nada"] == ["falta"] and tonos["movido"][1:] == ["falta", "falta"]
           and "viejo" in textos["movido"] and "Python39" in textos["movido"] and "faltan" in textos["movido"], tonos)
    vivo = carpeta / "datos" / "en-vivo"
    vivo.mkdir(parents=True)
    ahora = time.time()
    sin_nada = [tono for tono, _ in chequeo.revisar_registro(carpeta / "datos", ahora)]
    (vivo / "eventos.jsonl").write_text(json.dumps({"t": ahora - 120, "s": "aaaa1111", "e": "post"}) + "\n"
                                        + json.dumps({"t": ahora - 60, "s": "aaaa1111", "e": "aviso"}, separators=(",", ":"))
                                        + "\n", encoding="utf-8")
    con_pista = chequeo.revisar_registro(carpeta / "datos", ahora)
    (vivo / "eventos.jsonl").write_text(json.dumps({"t": ahora - 3 * 86400, "s": "aaaa1111", "e": "post"}) + "\n",
                                        encoding="utf-8")
    quieto = chequeo.revisar_registro(carpeta / "datos", ahora)
    probar("el chequeo mira el registro: sin nada en la semana falta (los hooks no corren); con algo reciente está bien y "
           "cuenta las pistas; quieto hace días o sin pistas, lo marca para mirar y dice cómo prender la pista",
           sin_nada == ["falta"] and [x for x, _ in con_pista] == ["bien", "bien"] and "1 vez" in con_pista[1][1]
           and [x for x, _ in quieto] == ["ojo", "ojo"] and "/plugin configure" in quieto[1][1], (sin_nada, con_pista, quieto))
    codex = carpeta / "codex"
    codex.mkdir()
    clave = "sk-" + "a1b2c3d4" * 6
    (codex / "config.toml").write_text(f'api_key = "{clave}"\n\n[mcp_servers.neuromapa]\ncommand = "py"\n', encoding="utf-8")
    (codex / "hooks.json").write_text(json.dumps({"hooks": {"UserPromptSubmit": [hook("x/hook_servir.py --codex")]}}),
                                      encoding="utf-8")
    puesto = chequeo.revisar_codex(codex)
    (codex / "hooks.json").unlink()
    a_medias = chequeo.revisar_codex(codex)
    probar("el chequeo dice si Codex tiene el conector y la pista, sin mostrar nada de su configuración (puede tener claves)",
           puesto[0][0] == "bien" and a_medias[0][0] == "dato" and "conector" in a_medias[0][1]
           and clave not in repr(puesto + a_medias) and chequeo.revisar_codex(carpeta / "sin-codex") == [],
           (puesto, a_medias))
    r = correr([str(CARPETA / "neuromapa.py"), "chequeo"], CEREBRO_CONFIG=str(t / "config.json"))
    probar("«neuromapa chequeo» corre entero con una instalación de prueba y termina con un resumen",
           r.returncode in (0, 1) and "revisión de la instalación" in r.stdout
           and any(f in r.stdout for f in ("Todo bien.", "para mirar", "que arreglar")) and not r.stderr.strip(),
           (r.returncode, r.stdout[-400:], r.stderr[-300:]))


def fstrings_nuevos(texto):
    salida = []
    pila = []
    for tok in tokenize.generate_tokens(io.StringIO(texto).readline):
        if tok.type == tokenize.FSTRING_START:
            comilla = tok.string.lstrip("rRfFbBuU")
            if pila and pila[-1]["comilla"] == comilla[0]:
                salida.append(tok.start[0])
            pila.append({"comilla": comilla[0], "triple": len(comilla) == 3, "linea": tok.start[0]})
        elif tok.type == tokenize.FSTRING_END:
            pila.pop()
        elif pila and tok.type != tokenize.FSTRING_MIDDLE:
            actual = pila[-1]
            if (not actual["triple"] and tok.start[0] != actual["linea"]) or "\\" in tok.string \
                    or (tok.type == tokenize.STRING and actual["comilla"] in tok.string[:4]):
                salida.append(tok.start[0])
    return sorted(set(salida))


def revisar_python_310():
    seccion("Python 3.10 (el plugin promete andar desde esa versión)")
    if not hasattr(tokenize, "FSTRING_START"):
        saltear("con un Python anterior a 3.12 no hace falta: si algo no fuera de 3.10, ni siquiera cargaría")
        return
    malos = []
    for archivo in sorted(CARPETA.rglob("*.py")):
        if {"demo", "medicion", "vendor", "node_modules", ".git", "en-vivo"} & set(archivo.relative_to(CARPETA).parts):
            continue
        malos += [f"{archivo.relative_to(CARPETA)}:{n}" for n in fstrings_nuevos(archivo.read_text(encoding="utf-8"))]
    ejemplos = [fstrings_nuevos('y = f"{x +\n 1}"\n'), fstrings_nuevos('y = f"{x + "b"}"\n'), fstrings_nuevos('y = f"{x!r:>3}"\n')]
    probar("ningún f-string usa lo que recién acepta Python 3.12 (una expresión partida en renglones, la misma comilla "
           "adentro o una barra invertida): con 3.10 o 3.11 el programa no arrancaría",
           not malos and ejemplos == [[2], [1], []], (malos[:5], ejemplos))
