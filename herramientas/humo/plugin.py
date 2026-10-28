from humo.base import *


def buscar_sh():
    sh = shutil.which("sh")
    if sh:
        return sh
    git = shutil.which("git")
    for relativa in ("../bin/sh.exe", "../usr/bin/sh.exe"):
        candidato = Path(git).parent / relativa if git else None
        if candidato and candidato.is_file():
            return str(candidato.resolve())
    return None


def ruta_sh(ruta):
    ruta = str(ruta)
    if os.name == "nt" and len(ruta) > 1 and ruta[1] == ":":
        return "/" + ruta[0].lower() + ruta[2:].replace("\\", "/")
    return ruta


RE_OPCION = re.compile(r"(?<![\w-])--[a-z][\w-]*")
RE_DESPUES_DEL_COMANDO = re.compile(r"(?:(?<![\w/:-])neuromapa(?= )|cerebro\.py|\{comando\}|\{cmd\}|comando\(\)\})"
                                    r"([^`\"'\n]*)")
RE_SKILL_CON_OPCIONES = re.compile(r"/neuromapa:(\w+)([^`\n]*)")
RE_HOOK_CON_OPCIONES = re.compile(r"(hook_\w+\.py)([^`\"'\n]*)")
RE_OPCION_SUELTA = re.compile(r"`(--[a-z][\w-]*)[^`]*`")
RE_OTRO_PROGRAMA = re.compile(r"\b(?:claude|git|gh|pip|uv|node|npx|python -m)\s+(?:-p\b|plugin|--|\w)", re.I)
OPCIONES_DE_CLAUDE_CODE = {"--keep-data"}


def revisar_opciones_nombradas(t):
    seccion("Las opciones que nombran las skills, la documentación y los avisos existen")
    consola = set(RE_OPCION.findall(correr([str(CARPETA / "cerebro.py"), "--help"]).stdout))
    abrir = set(servidor.OPCIONES)
    hooks = {o for archivo in CARPETA.glob("hook_*.py")
             for o in re.findall(r'"(--[a-z][\w-]*)" in sys\.argv', archivo.read_text(encoding="utf-8"))}
    publico = CARPETA / "publico" if (CARPETA / "publico").is_dir() else CARPETA
    documentos = sorted(list((CARPETA / "skills").glob("*/SKILL.md"))
                        + [p for p in publico.glob("*.md") if p.name != "CHANGELOG.md"]
                        + list((publico / "docs").glob("*.md")) + list((CARPETA / "wiki").glob("*.md")))
    nombradas, faltan = set(), {}

    def anotar(opcion, validas, lugar):
        nombradas.add(opcion)
        if opcion not in validas | OPCIONES_DE_CLAUDE_CODE:
            faltan.setdefault(opcion, lugar)

    for archivo in documentos + sorted(CARPETA.glob("*.py")):
        for n, renglon in enumerate(archivo.read_text(encoding="utf-8").split("\n"), 1):
            lugar = f"{archivo.name}:{n}"
            for m in RE_SKILL_CON_OPCIONES.finditer(renglon):
                for opcion in RE_OPCION.findall(m.group(2)):
                    anotar(opcion, abrir if m.group(1) == "abrir" else consola, lugar)
            for m in RE_HOOK_CON_OPCIONES.finditer(renglon):
                for opcion in RE_OPCION.findall(m.group(2)):
                    anotar(opcion, hooks, lugar)
            for m in RE_DESPUES_DEL_COMANDO.finditer(renglon):
                for opcion in RE_OPCION.findall(m.group(1)):
                    anotar(opcion, abrir if m.group(1).lstrip().startswith("abrir") else consola, lugar)
            if archivo.suffix == ".md" and not RE_OTRO_PROGRAMA.search(renglon):
                for m in RE_OPCION_SUELTA.finditer(renglon):
                    anotar(m.group(1), consola | abrir | hooks, lugar)
    probar("cada --opción que las skills, el README, las guías, la wiki y los avisos le dicen a Claude que corra existe en "
           "--help de la consola, en «neuromapa abrir» o en el hook que la nombra (si se renombra una, Claude recibía una "
           "orden que falla); y la búsqueda encontró de verdad qué revisar",
           not faltan and len(consola) >= 30 and len(documentos) >= 8 and len(nombradas) >= 30,
           (faltan, len(consola), len(documentos), len(nombradas)))


def revisar_dos_consolas(t, sh, base, comandos):
    raiz = t / "raiz con espacio"
    (raiz / "scripts").mkdir(parents=True)
    for nombre in ("python.sh", "python.cmd"):
        shutil.copy2(CARPETA / "scripts" / nombre, raiz / "scripts" / nombre)
    (raiz / "hook_eco.py").write_text("import json, sys\nprint(json.dumps({'leido': sys.stdin.buffer.read().decode('utf-8')}, "
                                      "ensure_ascii=True))\n", encoding="utf-8")
    comando = next(c for c in comandos if "hook_cerebro.py" in c).replace("${CLAUDE_PLUGIN_ROOT}", str(raiz)).replace(
        "hook_cerebro.py", "hook_eco.py")
    pedido = '{"x":"canción"}'
    esperado = [{"leido": pedido}]

    def salidas(r):
        try:
            return [json.loads(renglon) for renglon in r.stdout.decode("utf-8", "replace").splitlines() if renglon.strip()]
        except ValueError:
            return r.stdout

    r = subprocess.run([sh, "-c", comando], input=pedido.encode("utf-8"), capture_output=True, env=dict(base), timeout=60)
    probar("con Git Bash, Linux o Mac, cada hook corre una sola vez y lee el pedido entero", salidas(r) == esperado,
           (salidas(r), r.stderr[-200:]))
    powershell = shutil.which("powershell") if os.name == "nt" else None
    if not powershell:
        saltear("sin PowerShell de Windows: salteo los hooks sin Git Bash")
        return

    def en_powershell(texto, entrada, entorno):
        return subprocess.run([powershell, "-NoProfile", "-NonInteractive", "-Command", texto], input=entrada,
                              capture_output=True, env=entorno, timeout=60)

    r = en_powershell(comando, pedido.encode("utf-8"), dict(base))
    probar("sin Git Bash (PowerShell), cada hook corre una sola vez por el lanzador de Windows y lee el pedido entero",
           salidas(r) == esperado and r.returncode == 0, (salidas(r), r.returncode))
    rara = t / "raiz&rara"
    shutil.copytree(raiz, rara)
    otra = next(c for c in comandos if "hook_cerebro.py" in c).replace("${CLAUDE_PLUGIN_ROOT}", str(rara)).replace(
        "hook_cerebro.py", "hook_eco.py")
    r = en_powershell(otra, pedido.encode("utf-8"), dict(base))
    probar("con PowerShell, una carpeta con «&» en el nombre no rompe el hook (cmd lo tomaba como otro comando)",
           salidas(r) == esperado and r.returncode == 0, (salidas(r), r.stderr[-300:]))
    datos = t / "datos-cmd"
    for _ in range(2):
        r = en_powershell(comando, pedido.encode("utf-8"), dict(base, CLAUDE_PLUGIN_DATA=str(datos)))
    python_txt = datos / "python.txt"
    recordado = python_txt.read_text(encoding="utf-8", errors="replace").strip() if python_txt.is_file() else ""
    probar("el lanzador de Windows recuerda qué Python usar", recordado in ("py", "python") and salidas(r) == esperado,
           (recordado, salidas(r)))
    sistema = os.environ.get("SystemRoot", r"C:\Windows")
    if os.path.isfile(os.path.join(sistema, "py.exe")):
        perdido = t / "datos-cmd-perdido"
        perdido.mkdir()
        (perdido / "python.txt").write_text("python\n", encoding="utf-8")
        solo_py = dict(base, CLAUDE_PLUGIN_DATA=str(perdido),
                       PATH=os.pathsep.join([sistema, os.path.join(sistema, "System32"),
                                             os.path.join(sistema, "System32", "WindowsPowerShell", "v1.0")]))
        r = en_powershell(comando, pedido.encode("utf-8"), solo_py)
        ahora = (perdido / "python.txt").read_text(encoding="utf-8", errors="replace").strip()
        probar("si el Python que recordaba el lanzador de Windows ya no está, busca otro en vez de fallar en cada hook",
               salidas(r) == esperado and r.returncode == 0 and ahora == "py", (salidas(r), r.returncode, ahora))
    else:
        saltear("sin py.exe: salteo la prueba del Python recordado que ya no está (Windows sin Git Bash)")
    sin_python = dict(base, PATH=os.path.join(sistema, "System32") + os.pathsep
                      + os.path.join(sistema, "System32", "WindowsPowerShell", "v1.0"))
    inicio = next(c for c in comandos if "--avisar" in c).replace("${CLAUDE_PLUGIN_ROOT}", str(raiz))
    r = en_powershell(inicio, b"{}", sin_python)
    try:
        aviso = json.loads(r.stdout).get("systemMessage", "")
    except ValueError:
        aviso = ""
    callado = en_powershell(comando, b"{}", sin_python)
    probar("sin Git Bash ni Python, el arranque avisa con el enlace y los demás hooks no hacen nada",
           "python.org" in aviso and "3.10 o más nuevo" in aviso and r.returncode == 0 and callado.returncode == 0
           and callado.stdout == b"", (r.stdout, callado.stdout))
    cmd = os.path.join(sistema, "System32", "cmd.exe")
    lanzador_cmd = str(CARPETA / "bin" / "neuromapa.cmd")

    def en_cmd(*argumentos, entorno, lanzador=lanzador_cmd, carpeta=None):
        return subprocess.run(f'"{cmd}" /d /s /c "{subprocess.list2cmdline([lanzador, *argumentos])}"',
                              capture_output=True, env=entorno, timeout=60, cwd=carpeta, input=b"")

    con = en_cmd("--mapa", str(CARPETA / "donde.py"), entorno=dict(base))
    sin = en_cmd("--salud", entorno=sin_python)
    probar("neuromapa.cmd corre con Python 3.10 o más nuevo, y sin él lo dice y sale con 1",
           con.returncode == 0 and b"donde.py" in con.stdout and sin.returncode == 1 and b"Python 3.10" in sin.stdout,
           (con.returncode, con.stdout[:80], sin.returncode, sin.stdout[:120]))
    mal = en_cmd("--opcion-que-no-existe", entorno=dict(base))
    probar("si el programa falla, neuromapa.cmd sale con su mismo código (antes salía siempre con 0 y Claude no veía el "
           "error)", mal.returncode == 2, (mal.returncode, mal.stderr[:120]))
    trampa = Path(tempfile.mkdtemp(prefix="cerebro-trampa-"))
    marca = trampa / "marca.txt"
    for falso in ("py.bat", "python.bat"):
        (trampa / falso).write_bytes(f'@echo off\r\necho PLANTADO {falso}>>"{marca}"\r\n'.encode("ascii"))
    comun = {k: v for k, v in base.items() if k.lower() != "nodefaultcurrentdirectoryinexepath"}
    version = en_cmd("--version", entorno=comun, carpeta=str(trampa))
    en_cmd("hook_freno.py", entorno=comun, carpeta=str(trampa), lanzador=str(CARPETA / "scripts" / "python.cmd"))
    probar("desde una consola común, neuromapa.cmd y python.cmd no corren un py.bat o python.bat plantado en la carpeta "
           "donde uno está parado (cmd busca ahí primero)", not marca.exists() and b"Neuromapa" in version.stdout,
           (marca.read_text(encoding="ascii", errors="replace") if marca.exists() else "", version.stdout[:80]))
    shutil.rmtree(trampa, ignore_errors=True)


def revisar_plugin(t):
    seccion("Plugin neuromapa (carpeta de datos, arranque, Python y hooks)")
    codigo = t / "codigo-plugin"
    codigo.mkdir()
    for nombre in ("donde.py", "archivos.py"):
        shutil.copy2(CARPETA / nombre, codigo / nombre)
    casa = t / "casa-plugin"
    apuntada = t / "datos-apuntados"
    apuntada.mkdir()
    (casa / "plugins" / "data" / "neuromapa-prueba").mkdir(parents=True)
    (casa / "plugins" / "data" / "neuromapa-prueba" / "donde.txt").write_text(f"{apuntada}\n", encoding="utf-8")
    (casa / "projects" / "C--x-plugin" / "memory").mkdir(parents=True)
    (casa / "projects" / "C--x-plugin" / "memory" / "nota.md").write_text("---\nname: nota\ndescription: una nota\n---\nHola\n",
                                                                          encoding="utf-8")
    quitar = ("CEREBRO_CONFIG", "CLAUDE_PLUGIN_DATA", "CLAUDE_PLUGIN_OPTION_CARPETA_DATOS",
              "CLAUDE_PLUGIN_OPTION_SERVIR_CONTEXTO")
    base = {k: v for k, v in os.environ.items() if k not in quitar}
    base["CLAUDE_CONFIG_DIR"] = str(casa)

    def donde_dice(**extra):
        programa = "import sys; sys.path.insert(0, sys.argv[1]); import donde; print(donde.config()[0])"
        r = subprocess.run([sys.executable, "-I", "-S", "-c", programa, str(codigo)], capture_output=True, text=True,
                           env=dict(base, **extra), timeout=60)
        return r.stdout.strip() or r.stderr.strip()

    elegida = str(t / "elegida.json")
    probar("donde: CEREBRO_CONFIG manda sobre todo",
           donde_dice(CEREBRO_CONFIG=elegida, CLAUDE_PLUGIN_DATA=str(t / "pd")) == elegida)
    probar("donde: la carpeta elegida en el plugin manda sobre la del plugin",
           donde_dice(CLAUDE_PLUGIN_OPTION_CARPETA_DATOS=str(t / "mia"), CLAUDE_PLUGIN_DATA=str(t / "pd"))
           == str(t / "mia" / "config.json"))
    probar("donde: si no, la carpeta de datos del plugin",
           donde_dice(CLAUDE_PLUGIN_DATA=str(t / "pd")) == str(t / "pd" / "config.json"))
    probar("donde: desde la consola, sin variables, sigue el apunte que dejó el arranque",
           donde_dice() == str(apuntada / "config.json"), donde_dice())
    datos_plugin = t / "pd-config"
    programa = ("import sys; sys.path.insert(0, sys.argv[1]); import configuracion; c = configuracion.actual(); "
                "print(c['datos']); print(','.join(f['id'] for f in c['fuentes']))")
    r = subprocess.run([sys.executable, "-I", "-S", "-c", programa, str(CARPETA)], capture_output=True, text=True,
                       env=dict(base, CLAUDE_PLUGIN_DATA=str(datos_plugin)), timeout=60)
    lineas = r.stdout.strip().splitlines()
    probar("sin config.json, el plugin arma su configuración con la memoria de ~/.claude y guarda todo en su carpeta",
           len(lineas) == 2 and lineas[0] == str(datos_plugin) and "memoria" in lineas[1].split(",")
           and datos_plugin.is_dir(),
           (r.stdout[-300:], r.stderr[-300:]))
    datos_inicio = t / "pd-inicio"
    entorno_bash = t / "entorno-bash.sh"
    entorno_bash.write_text("", encoding="utf-8")
    arranques = [subprocess.run([sys.executable, "-I", "-S", str(CARPETA / "hook_inicio.py")], input=b"{}",
                                capture_output=True, timeout=60,
                                env=dict(base, CLAUDE_PLUGIN_DATA=str(datos_inicio), CLAUDE_ENV_FILE=str(entorno_bash)))
                 for _ in range(2)]
    donde_txt = datos_inicio / "donde.txt"
    apunte = donde_txt.read_text(encoding="utf-8").strip() if donde_txt.is_file() else ""
    try:
        primero = json.loads(arranques[0].stdout.decode("utf-8"))
    except ValueError:
        primero = {}
    probar("el arranque deja el apunte y la carpeta para la consola; la primera vez le dice al usuario que quedó "
           "instalado y cómo abrirlo, y después no imprime nada (antes no había ninguna señal de que anduviera)",
           all(r.returncode == 0 for r in arranques) and "quedó instalado" in primero.get("systemMessage", "")
           and "/neuromapa:abrir" in primero.get("systemMessage", "") and arranques[1].stdout == b""
           and apunte == str(datos_inicio)
           and "CLAUDE_PLUGIN_OPTION_CARPETA_DATOS" in entorno_bash.read_text(encoding="utf-8"),
           ([r.stdout for r in arranques], apunte))
    revisar_instalacion_doble(t, base)
    sh = buscar_sh()
    lanzador = str(CARPETA / "scripts" / "python.sh")
    if sh:
        r = subprocess.run([sh, lanzador, "-c", "print(40 + 2)"], capture_output=True, text=True, env=dict(base), timeout=60)
        probar("el lanzador encuentra un Python 3.10 o más nuevo", r.stdout.strip() == "42", (r.stdout, r.stderr[-200:]))
        sin_codificacion = {k: v for k, v in base.items() if k != "PYTHONIOENCODING"}
        r = subprocess.run([sh, lanzador, "-c", "import sys; print('configuraci\\u00f3n'); sys.exit('Cerr\\u00e1 esta ventana')"],
                           capture_output=True, env=sin_codificacion, timeout=60)
        probar("el lanzador hace que Python escriba en UTF-8, también los errores",
               "configuración".encode("utf-8") in r.stdout and "Cerrá".encode("utf-8") in r.stderr,
               (r.stdout[-100:], r.stderr[-100:]))
        sin_python = dict(base, NEUROMAPA_PYTHONS="no-hay-1 no-hay-2")
        r = subprocess.run([sh, lanzador, "--avisar", "-c", "print(1)"], capture_output=True, text=True, env=sin_python,
                           timeout=60)
        try:
            aviso = json.loads(r.stdout).get("systemMessage", "")
        except ValueError:
            aviso = ""
        callado = subprocess.run([sh, lanzador, "-c", "print(1)"], capture_output=True, env=sin_python, timeout=60)
        probar("sin Python, el arranque avisa con el enlace y los demás hooks no hacen nada",
               "python.org" in aviso and r.returncode == 0 and callado.returncode == 0 and callado.stdout == b"",
               (r.stdout, callado.stdout))
        lanzador_bin = str(CARPETA / "bin" / "neuromapa")
        con = subprocess.run([sh, lanzador_bin, "--mapa", str(CARPETA / "donde.py")], capture_output=True, env=dict(base),
                             timeout=60)
        sin = subprocess.run([sh, lanzador_bin, "--salud"], capture_output=True, env=sin_python, timeout=60)
        probar("bin/neuromapa (Mac y Linux) corre con Python 3.10 o más nuevo, y sin él lo dice y sale con 1 "
               "(antes se callaba)",
               con.returncode == 0 and b"donde.py" in con.stdout and sin.returncode == 1 and b"Python 3.10" in sin.stderr
               and b"python.org" in sin.stderr,
               (con.returncode, con.stdout[:80], con.stderr[-200:], sin.returncode, sin.stderr[:120]))
        falsos = t / "python-viejo"
        falsos.mkdir()
        (falsos / "python-viejo").write_text("#!/bin/sh\necho False\n", encoding="utf-8", newline="\n")
        (falsos / "python-tienda").write_text("#!/bin/sh\necho 'Python was not found; run without arguments to install "
                                              "from the Microsoft Store' >&2\nexit 49\n", encoding="utf-8", newline="\n")
        for falso in ("python-viejo", "python-tienda"):
            os.chmod(falsos / falso, 0o755)
        camino = str(falsos) + os.pathsep + base.get("PATH", "")
        viejo = subprocess.run([sh, lanzador, "--consola", "-c", "print(1)"], capture_output=True, timeout=60,
                               env=dict(base, NEUROMAPA_PYTHONS="python-viejo", PATH=camino))
        probar("con un Python más viejo que 3.10, el lanzador dice que el que encontró es viejo (no que no hay)",
               viejo.returncode == 1 and "python-viejo) es más viejo".encode("utf-8") in viejo.stderr,
               (viejo.returncode, viejo.stderr[-200:]))
        tienda = subprocess.run([sh, lanzador, "--consola", "-c", "print(1)"], capture_output=True, timeout=60,
                                env=dict(base, NEUROMAPA_PYTHONS="python-tienda", PATH=camino))
        probar("el «python» de la tienda de Windows (que no es Python) no hace decir «es más viejo», sino que no hay",
               tienda.returncode == 1 and "no lo encontré".encode("utf-8") in tienda.stderr
               and "más viejo".encode("utf-8") not in tienda.stderr, (tienda.returncode, tienda.stderr[-200:]))
        recuerdos = t / "datos-lanzador"
        recuerdos.mkdir()
        python_txt = recuerdos / "python.txt"
        con_datos = dict(base, CLAUDE_PLUGIN_DATA=str(recuerdos))
        vueltas = []
        for anterior in ("/no/existe/python3", "python3"):
            python_txt.write_text(anterior + "\n", encoding="utf-8", newline="\n")
            r = subprocess.run([sh, lanzador, "-c", "print(40 + 2)"], capture_output=True, text=True, env=con_datos,
                               timeout=60)
            nueva = python_txt.read_text(encoding="utf-8").strip()
            vueltas.append((anterior, r.returncode, r.stdout.strip(), nueva))
        probar("si el Python recordado ya no está (o quedó solo su nombre, como antes), el lanzador busca otro y recuerda "
               "su ruta (antes, error 127 en cada hook)",
               all(codigo == 0 and salida == "42" and nueva.startswith("/") and nueva != anterior
                   and nueva.rsplit("/", 1)[-1] in ("python3", "python", "py", "python3.exe", "python.exe", "py.exe")
                   for anterior, codigo, salida, nueva in vueltas), vueltas)
        propio = t / "python-recordado"
        propio.mkdir()
        (propio / "python3").write_text("#!/bin/sh\necho recordado\n", encoding="utf-8", newline="\n")
        os.chmod(propio / "python3", 0o755)
        python_txt.write_text(ruta_sh(propio / "python3") + "\n", encoding="utf-8", newline="\n")
        r = subprocess.run([sh, lanzador, "-c", "print(1)"], capture_output=True, text=True, env=con_datos, timeout=60)
        probar("el lanzador usa la ruta del Python que recordó, sin volver a buscar", r.stdout.strip() == "recordado",
               (r.stdout, r.stderr[-200:]))
    else:
        print("  (sin sh en esta PC: salteo las pruebas del lanzador y de bin/neuromapa)")
    import hook_servir
    antes = {k: os.environ.get(k) for k in ("CLAUDE_PLUGIN_DATA", "CLAUDE_PLUGIN_OPTION_SERVIR_CONTEXTO")}
    try:
        for k in antes:
            os.environ.pop(k, None)
        fuera = hook_servir.prendido()
        os.environ["CLAUDE_PLUGIN_DATA"] = str(t / "pd")
        de_fabrica = hook_servir.prendido()
        os.environ["CLAUDE_PLUGIN_OPTION_SERVIR_CONTEXTO"] = "true"
        elegido = hook_servir.prendido()
    finally:
        for k, v in antes.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    probar("contexto automático: prendido fuera del plugin, apagado de fábrica en el plugin, prendido si se elige",
           fuera and not de_fabrica and elegido, (fuera, de_fabrica, elegido))
    hooks = json.loads((CARPETA / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    comandos = [h["command"] for grupos in hooks["hooks"].values() for g in grupos for h in g["hooks"]]
    nombrados = sorted({m for c in comandos for m in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)", c)})
    faltan = [n for n in nombrados if not (CARPETA / n).is_file()]
    manifiesto = json.loads((CARPETA / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    probar("el manifiesto se llama neuromapa y existe cada archivo que nombran los hooks",
           manifiesto.get("name") == "neuromapa" and not faltan and len(nombrados) >= 7, (nombrados, faltan))
    forma = re.compile(r'/bin/sh "\$\{CLAUDE_PLUGIN_ROOT\}/scripts/python\.sh" ((?:--avisar )?)-I -S '
                       r'"\$\{CLAUDE_PLUGIN_ROOT\}/(hook_\w+\.py)"'
                       r' \\; \. "\$\{CLAUDE_PLUGIN_ROOT\}/scripts/python\.cmd" ((?:--avisar )?)(hook_\w+\.py)')
    probar("cada hook pasa por el lanzador de Python, con el mismo hook para Git Bash y para PowerShell "
           "(a python.cmd, solo el nombre)",
           all((m := forma.fullmatch(c)) and m.group(1) == m.group(3) and m.group(2) == m.group(4) for c in comandos),
           comandos[:1])
    fondo = {m: h.get("async") is True for grupos in hooks["hooks"].values() for g in grupos for h in g["hooks"]
             for m in re.findall(r"(hook_\w+)\.py\"", h["command"])}
    probar("los avisos de choques y parecidas corren de fondo (no hacen esperar a Claude); el freno, el contexto, el "
           "arranque y el recordatorio de guardar esperan (si no, su aviso no le llega a Claude)",
           fondo.get("hook_choques") and fondo.get("hook_parecidas") and not fondo.get("hook_freno")
           and not fondo.get("hook_servir") and not fondo.get("hook_inicio") and fondo.get("hook_guardar") is False, fondo)
    guardar = {evento: [g.get("matcher", "") for g in grupos if any("hook_guardar.py" in h["command"] for h in g["hooks"])]
               for evento, grupos in hooks["hooks"].items()}
    probar("el recordatorio de guardar corre al volver de compactar y al terminar cada respuesta, y en nada más",
           {k: v for k, v in guardar.items() if v} == {"SessionStart": ["compact"], "Stop": [""]}, guardar)
    de_reglas = hooks["hooks"].get("InstructionsLoaded", [])
    probar("el hook de las reglas cargadas corre solo cuando una regla entra por su carpeta (no en cada instrucción que se "
           "carga al empezar un chat)",
           [g.get("matcher") for g in de_reglas] == ["path_glob_match"]
           and all("hook_cerebro.py" in h["command"] and h.get("async") is True for g in de_reglas for h in g["hooks"]),
           de_reglas)
    de_windows = sorted({p for patron in ("*.bat", "*.cmd", "bin/*.cmd", "scripts/*.cmd") for p in CARPETA.glob(patron)})
    con_lf = [p.name for p in de_windows
              if p.read_bytes().count(b"\n") != p.read_bytes().count(b"\r\n") or max(p.read_bytes()) > 127]
    probar("los .cmd y .bat van con finales de línea de Windows y solo ASCII (si no, cmd los lee mal en una consola UTF-8)",
           len(de_windows) >= 3 and not con_lf, (len(de_windows), con_lf))
    if sh:
        revisar_dos_consolas(t, sh, base, comandos)
    r = correr([str(CARPETA / "neuromapa.py"), "--mapa", str(CARPETA / "donde.py")])
    probar("neuromapa.py hace de cerebro.py (con --mapa)",
           r.returncode == 0 and "donde.py" in r.stdout and "apuntar" in r.stdout, (r.stdout[-300:], r.stderr[-300:]))
    r = correr([str(CARPETA / "neuromapa.py"), "--help"])
    probar("neuromapa --help cuenta cómo abrir el mapa (neuromapa abrir)",
           r.returncode == 0 and "neuromapa abrir" in r.stdout, (r.stdout[-300:], r.stderr[-300:]))
    manifiesto = json.loads((CARPETA / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    r = correr([str(CARPETA / "neuromapa.py"), "--version"])
    probar("neuromapa --version dice la versión del manifiesto del plugin (un solo lugar para la versión)",
           r.returncode == 0 and r.stdout.strip() == f'Neuromapa {manifiesto["version"]}', (r.stdout, r.stderr[-200:]))
    raiz_antes = os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
    viejo = sys.argv
    try:
        normal = configuracion.comando()
        os.environ["CLAUDE_PLUGIN_ROOT"] = str(t)
        desde_hook = configuracion.comando()
        os.environ.pop("CLAUDE_PLUGIN_ROOT")
        sys.argv = ["neuromapa"]
        desde_consola = configuracion.comando()
        sys.argv = ["neuromapa", "--demo", "--proponer-hechos"]
        en_demo = configuracion.comando()
    finally:
        sys.argv = viejo
        if raiz_antes is not None:
            os.environ["CLAUDE_PLUGIN_ROOT"] = raiz_antes
    sueltos = [f"{archivo.name}:{n}" for archivo in sorted(CARPETA.glob("*.py"))
               for n, renglon in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1)
               if re.search(r"[\"'][^\"'\n]*\bcerebro\.py --", renglon) or "El cerebro:" in renglon]
    if os.name != "nt":
        archivo_nuevo, carpeta_nueva = t / "permisos.txt", t / "permisos-dir"
        r = subprocess.run([sys.executable, "-c", "import os, sys; sys.path.insert(0, sys.argv[1]); import donde; "
                            "open(sys.argv[2], 'w').write('x'); os.mkdir(sys.argv[3]); "
                            "print(oct(os.stat(sys.argv[2]).st_mode & 0o777), oct(os.stat(sys.argv[3]).st_mode & 0o777))",
                            str(CARPETA), str(archivo_nuevo), str(carpeta_nueva)], capture_output=True, text=True, timeout=30)
        probar("en Mac y Linux, lo que escribe queda solo para el dueño (clave, registro, página con las notas)",
               r.stdout.split() == ["0o600", "0o700"], (r.stdout, r.stderr[-200:]))
    else:
        saltear("permisos de Mac y Linux: en Windows no aplica, salteado")
    probar("los mensajes nombran el comando que existe (neuromapa en el plugin, python …/cerebro.py si no); ninguno escribe "
           "«cerebro.py --» a mano ni «El cerebro:»",
           normal.startswith("python ") and normal.endswith("/cerebro.py") and desde_hook == "neuromapa"
           and desde_consola == "neuromapa" and not sueltos, (normal, desde_hook, desde_consola, sueltos))
    probar("en la demo, los comandos que sugiere llevan --demo (si no, la pista apuntaba a las notas reales)",
           en_demo == "neuromapa --demo", en_demo)


def revisar_instalacion_doble(t, base):
    import hooks_comun
    a_mano = {"hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": "python -I -S C:/x/hook_cerebro.py"}]}]}}
    del_plugin = {"enabledPlugins": {"neuromapa@neuromapa": True}}
    casas = {}
    for nombre, ajustes in (("doble", dict(a_mano, **del_plugin)), ("mano", a_mano), ("plugin", del_plugin), ("rota", None)):
        casa = t / f"claude-{nombre}"
        casa.mkdir()
        (casa / "settings.json").write_text("{rota" if ajustes is None else json.dumps(ajustes), encoding="utf-8")
        casas[nombre] = hooks_comun.instalado_dos_veces(str(casa))
    anterior = os.environ.get("CLAUDE_CONFIG_DIR")
    os.environ["CLAUDE_CONFIG_DIR"] = str(t / "claude-doble")
    try:
        aviso = hooks_comun.linea_doble()
    finally:
        os.environ["CLAUDE_CONFIG_DIR"] = anterior
    arranques = [subprocess.run([sys.executable, "-I", "-S", str(CARPETA / "hook_inicio.py")], input=b"{}",
                                capture_output=True, timeout=60,
                                env=dict(base, CLAUDE_PLUGIN_DATA=str(t / "pd-doble"), CLAUDE_PLUGIN_ROOT=str(CARPETA),
                                         CLAUDE_CONFIG_DIR=str(t / "claude-mano")))
                 for _ in range(2)]
    try:
        mensaje = json.loads(arranques[0].stdout.decode("utf-8")).get("systemMessage", "")
    except ValueError:
        mensaje = ""
    probar("si Neuromapa está como plugin y con sus hooks a mano en settings.json, --salud y el arranque del plugin lo "
           "avisan (una vez), junto con la bienvenida (antes todo se anotaba y se servía dos veces sin aviso)",
           casas == {"doble": True, "mano": False, "plugin": False, "rota": False} and aviso.startswith("AVISO")
           and "dos veces" in mensaje and "quedó instalado" in mensaje and arranques[1].stdout == b"",
           (casas, aviso[:40], mensaje[:80], arranques[1].stdout))
    viejos = (hook_evento.CARPETA, hook_evento.REGISTRO, hook_evento.CANDADO)
    carpeta = t / "registro-doble"
    carpeta.mkdir()
    hook_evento.CARPETA, hook_evento.REGISTRO, hook_evento.CANDADO = (str(carpeta), str(carpeta / "eventos.jsonl"),
                                                                      str(carpeta / "eventos.lock"))
    try:
        evento = {"t": int(time.time()), "s": "doble001", "e": "post", "k": "leer", "id": "toolu00001"}
        for e in (evento, dict(evento, t=evento["t"] + 1), dict(evento, e="pre"), dict(evento, id="toolu00002")):
            hook_evento.escribir_evento(e)
        renglones = (carpeta / "eventos.jsonl").read_text(encoding="utf-8").splitlines()
    finally:
        hook_evento.CARPETA, hook_evento.REGISTRO, hook_evento.CANDADO = viejos
    probar("el registro no anota dos veces el mismo evento (misma charla, id y fase seguidos, como cuando corren el plugin y "
           "los hooks a mano), y sí los que cambian de fase o de id", len(renglones) == 3, renglones)
