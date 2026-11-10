from humo.base import *


def revisar_partir_en_varias(t):
    seccion("Partir sola en tantas partes como haga falta, en una sola pasada")
    import datetime
    medico_mod = importlib.import_module("medico")
    tope = medico_mod.TOKENS_READ * medico_mod.BYTES_POR_TOKEN
    mundo = t / "partir-en-varias"
    memoria = mundo / "memoria"
    memoria.mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    real = datetime.date.today()
    enorme = memoria / "enorme.md"
    enorme.write_text(frontmatter("enorme", "Cómo se cuida cada planta del vivero, todo junto", "project")
                      + "# Cuidados\n\nUna sección por planta.\n\n"
                      + "".join(f"## Planta {k}\n\n" + "palabra " * 500 + "\n\n" for k in range(36)),
                      encoding="utf-8", newline="\n")
    diario = memoria / "diario.md"
    diario.write_text(frontmatter("diario", "Diario del vivero, un día por entrada", "project")
                      + "# Diario\n\nLo nuevo va abajo.\n\n"
                      + "".join(f"## {(real - datetime.timedelta(days=d)).isoformat()} — día {d}\n\n- **Qué:** "
                                + "palabra " * 450 + "\n- **Listo.**\n\n" for d in range(45, 5, -1)),
                      encoding="utf-8", newline="\n")
    (memoria / "MEMORY.md").write_text("# Memoria\n\n- [Cuidados](enorme.md) — una sección por planta\n"
                                       "- [Diario](diario.md) — un día por entrada\n", encoding="utf-8", newline="\n")
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "partir_sola": True, "fuentes": [
        {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]],
         "memoria": True, "foco": True}]}, ensure_ascii=False), encoding="utf-8", newline="\n")
    viejo = time.time() - 3600
    for nota in (enorme, diario):
        os.utime(nota, (viejo, viejo))

    def renglones():
        return sorted(r for p in memoria.glob("*.md") for r in p.read_text(encoding="utf-8").split("\n") if r.strip())

    todos = renglones()
    antes = {"enorme": len(enorme.read_bytes()) / tope, "diario": len(diario.read_bytes()) / tope}
    _, que_haria = cerebro_en(mundo, "--por-partir")
    codigo, salida = cerebro_en(mundo, "--partir-llenas")
    partes = sorted(memoria.glob("enorme*.md"))
    secciones = {p.name: [k for k in range(36) if f"## Planta {k}\n" in p.read_text(encoding="utf-8")] for p in partes}
    probar("--por-partir avisa que la parte nueva seguiría pasada del tope y que la misma pasada la volvería a partir",
           "enorme-parte-2.md seguiría pasada del tope, así que la misma pasada la volvería a partir" in que_haria,
           que_haria[-600:])
    probar("una nota sin fechas que triplica el tope se parte en una sola pasada en tantas partes como hagan falta, todas "
           "por debajo del 85 % de una lectura, cada sección entera y en orden",
           codigo == 0 and antes["enorme"] > 2.5 and len(partes) >= 4
           and all(len(p.read_bytes()) < 0.85 * tope for p in partes)
           and sorted(k for ks in secciones.values() for k in ks) == list(range(36))
           and (memoria / "enorme-parte-3.md").exists(), (salida[-500:], {p.name: len(p.read_bytes()) for p in partes}))
    historias = sorted(memoria.glob("diario-historia-*.md"))
    probar("un registro con fechas que triplica el tope pasa lo viejo a varias notas de historia en la misma pasada, ninguna "
           "más llena que lo que acepta una historia, y la nota queda por debajo del 85 %",
           antes["diario"] > 2.5 and len(historias) >= 3
           and all(len(h.read_bytes()) < 0.85 * tope for h in historias)
           and len(diario.read_bytes()) < 0.85 * tope and "día 45\n" in historias[0].read_text(encoding="utf-8"),
           (salida[-500:], {h.name: len(h.read_bytes()) for h in historias}, len(diario.read_bytes())))
    agregados = [r for r in renglones() if r not in todos]
    probar("en todo eso no se pierde ni un renglón, y cada partida queda en el registro de partidas",
           not [r for r in todos if r not in renglones()] and len(agregados) < 60
           and salida.count("Partió sola") >= len(partes) - 1 + len(historias),
           (len(agregados), salida.count("Partió sola")))


def revisar_renglon_gigante(t):
    seccion("Una memoria con un renglón más grande que una lectura no se parte en bucle")
    mundo = t / "renglon-gigante"
    memoria = mundo / "memoria"
    memoria.mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    gigante = "**Ronda grande:** " + "; ".join(f"hecho {k} (`{k:07x}`) con algo de texto" for k in range(1800))
    ronda = memoria / "ronda.md"
    ronda.write_text(frontmatter("ronda", "Lo que se hizo en la ronda grande, todo junto", "project")
                     + "# Ronda\n\n" + "".join(f"Antes {k}: " + "palabra " * 60 + "\n\n" for k in range(8))
                     + gigante + "\n\n" + "".join(f"- Cola {k}: " + "palabra " * 40 + "\n" for k in range(25)),
                     encoding="utf-8", newline="\n")
    (memoria / "MEMORY.md").write_text("# Memoria\n\n- [Ronda](ronda.md) — la ronda grande\n", encoding="utf-8",
                                       newline="\n")
    (mundo / "config.json").write_text(json.dumps({"usuario": "Ana", "partir_sola": True, "fuentes": [
        {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]],
         "memoria": True, "foco": True}]}, ensure_ascii=False), encoding="utf-8", newline="\n")

    def envejecer():
        viejo = time.time() - 3600
        for nota in memoria.glob("*.md"):
            os.utime(nota, (viejo, viejo))

    def con_texto():
        return sorted(r for p in memoria.glob("ronda*.md") for r in p.read_text(encoding="utf-8").split("\n") if r.strip())

    envejecer()
    todos = con_texto()
    codigo, salida = cerebro_en(mundo, "--partir-llenas")
    partes = sorted(memoria.glob("ronda*.md"))
    vacias = [p.name for p in partes if not [r for r in p.read_text(encoding="utf-8").split("\n")[7:]
                                             if r.strip() and not r.startswith(("# ", "Sigue de ", "Sigue en ", "- Sigue en "))]]
    probar("no deja partes vacías ni crea una tras otra: corta por donde puede y para",
           codigo == 0 and len(partes) <= 3 and not vacias
           and sum(gigante in p.read_text(encoding="utf-8") for p in partes) == 1, (salida[-600:], [p.name for p in partes], vacias))
    probar("dice que el renglón gigante hay que pasarlo a ítems a mano, y no se pierde ni un renglón",
           "un solo renglón de" in salida and not [r for r in todos if r not in con_texto()], salida[-600:])
    envejecer()
    codigo, otra = cerebro_en(mundo, "--partir-llenas")
    probar("volver a correrla no crea ninguna parte nueva", codigo == 0 and sorted(memoria.glob("ronda*.md")) == partes,
           (otra[-400:], [p.name for p in sorted(memoria.glob("ronda*.md"))]))


def revisar_memoria_llena(t):
    seccion("Una memoria que pasa el tope durante el día")
    dormir = importlib.import_module("dormir")
    mundo = t / "memoria-llena"
    memoria = mundo / "memoria"
    memoria.mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    llena, chica = memoria / "bitacora-llena.md", memoria / "chica.md"
    entradas = "".join(f"## {d}/{m}/2026\n\n" + "Se regó el cantero del fondo y se anotó cómo quedó la tierra. " * 30
                       + "\n\n" for m in (7, 8) for d in range(1, 29))
    llena.write_text(frontmatter("bitacora-llena", "Lo que se hizo cada día en el vivero", "project") + "# Bitácora\n\n"
                     + entradas, encoding="utf-8", newline="\n")
    chica.write_text(frontmatter("chica", "Una nota chica del vivero", "project") + "Poco texto.\n", encoding="utf-8",
                     newline="\n")
    (memoria / "MEMORY.md").write_text("# Memoria\n\n- [Bitácora](bitacora-llena.md) — lo de cada día\n"
                                       "- [Chica](chica.md) — poco\n", encoding="utf-8", newline="\n")

    def configurar(**mas):
        (mundo / "config.json").write_text(json.dumps(dict({"usuario": "Ana", "fuentes": [
            {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]],
             "memoria": True, "foco": True}]}, **mas), ensure_ascii=False), encoding="utf-8", newline="\n")

    def editar(nota):
        entrada = {"hook_event_name": "PostToolUse", "tool_name": "Edit", "session_id": "llena001-x", "cwd": str(mundo),
                   "tool_input": {"file_path": str(nota), "old_string": "Poco", "new_string": "Poco"}}
        return correr_hook("hook_choques.py", json.dumps(entrada).encode("utf-8"), CEREBRO_CONFIG=str(mundo / "config.json"))

    marca = mundo / "en-vivo" / "memoria-llena.txt"

    def desde():
        return marca.read_text(encoding="utf-8").strip() if marca.exists() else None

    configurar()
    editar(llena)
    sin_partir_sola = marca.exists()
    configurar(partir_sola=True)
    editar(chica)
    por_la_chica = marca.exists()
    respuesta = editar(llena)
    primera = desde()
    editar(llena)
    ahora = time.time()
    probar("al editar una memoria que quedó por arriba del tope de un Read, el hook deja una marca (una sola, con la hora "
           "de la primera vez), sin decirle nada al chat; una nota chica o «partir_sola» apagado, no",
           not sin_partir_sola and not por_la_chica and respuesta.returncode == 0 and not respuesta.stdout.strip()
           and primera is not None and desde() == primera, (sin_partir_sola, por_la_chica, primera, respuesta.stdout[:300]))
    probar("con esa marca, el primer pedido que llega pasados 10 minutos larga la partición de fondo (antes esperaba a la "
           "pasada del día siguiente, hasta 20 horas); antes de los 10 minutos, no",
           not dormir.falta_partir(str(mundo), ahora + 60) and dormir.falta_partir(str(mundo), ahora + 601), desde())
    viejo = time.time() - 3600
    os.utime(llena, (viejo, viejo))
    codigo, salida = cerebro_en(mundo, "--partir-llenas")
    probar("esa partición la parte como la pasada (a una nota de historia) y saca la marca, así no se vuelve a largar",
           codigo == 0 and "Partió sola bitacora-llena.md" in salida and (memoria / "bitacora-llena-historia-1.md").exists()
           and not marca.exists() and not dormir.falta_partir(str(mundo), time.time() + 3600), salida[-500:])


def revisar_partir_sola(t):
    seccion("Partir sola la memoria que está por llenarse (partir_sola)")
    import datetime
    ordenar = importlib.import_module("ordenar")
    dormir = importlib.import_module("dormir")
    hoy = datetime.date(2026, 10, 10)
    fechas = [ordenar.fecha_de(texto, hoy) for texto in (
        "2026-10-08 — el aro salía arriba", "Lo último del 6/10 (master)", "31/12, cierre del año", "Versión 0.8/10 lista",
        "3/4/25: la bomba", "1/13 in US style", "30/2 no existe", "sin fecha")]
    probar("lee la fecha del título de una entrada (2026-10-08, 6/10, 3/4/25): sin año toma el último que no cae en el "
           "futuro, y no confunde un número de versión ni una fecha imposible",
           fechas == [datetime.date(2026, 10, 8), datetime.date(2026, 10, 6), datetime.date(2025, 12, 31), None,
                      datetime.date(2025, 4, 3), datetime.date(2026, 1, 13), None, None], fechas)

    def nota_de(dias, relleno=900, titulo="## {f} — arreglo"):
        partes = ["# Registro\n\nLo nuevo va arriba.\n\n"]
        for d in dias:
            f = (hoy - datetime.timedelta(days=d)).isoformat() if d is not None else "sin fecha"
            partes.append(titulo.replace("{f}", f) + f" {d}\n\n- **Problema:** " + "x" * relleno + "\n- **Arreglo:** listo.\n\n")
        return "".join(partes)

    def eleccion(dias, objetivo=0.5, frescos=3):
        texto = nota_de(dias)
        piezas = ordenar.piezas_de(ordenar.renglones_de(texto))
        elegida = ordenar.elegir_viejas(piezas, len(texto.encode()), len(texto.encode()) * objetivo, hoy, frescos)
        if not elegida:
            return None
        return elegida["entradas"], (hoy - elegida["ultima"]).days, (hoy - elegida["primera"]).days
    probar("de un registro con lo nuevo arriba elige las entradas más viejas, las de abajo, hasta dejar la nota en el "
           "tamaño pedido; con lo nuevo abajo, las de arriba",
           eleccion(list(range(20))) == (11, 9, 19) and eleccion(list(range(19, -1, -1))) == (11, 9, 19),
           (eleccion(list(range(20))), eleccion(list(range(19, -1, -1)))))
    probar("nunca se lleva las entradas de los últimos días ni deja menos de tres, aunque la nota siga grande",
           eleccion(list(range(20)), objetivo=0.01, frescos=12) == (7, 13, 19)
           and eleccion(list(range(20)), objetivo=0.01, frescos=0) == (17, 3, 19),
           (eleccion(list(range(20)), 0.01, 12), eleccion(list(range(20)), 0.01, 0)))
    probar("si no puede saber qué es lo viejo no elige nada: fechas desordenadas, todas del mismo día, menos de cuatro "
           "entradas, o entradas sin fecha",
           eleccion([5, 19, 2, 14, 9, 0, 17, 3, 11, 7]) is None and eleccion([8] * 10) is None
           and eleccion([20, 10, 5]) is None and eleccion([None] * 10) is None)
    mundo = t / "partir-sola"
    memoria = mundo / "memoria"
    memoria.mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    real = datetime.date.today()
    cuerpo = "".join(f"## {(real - datetime.timedelta(days=d)).isoformat()} — arreglo {d}\n\n- **Problema:** "
                     + "palabra " * 130 + "\n- **Arreglo:** listo.\n\n" for d in range(40))
    registro = memoria / "registro.md"
    registro.write_text(frontmatter("registro", "Registro de arreglos del vivero, una entrada por arreglo", "project")
                        + "# Registro\n\nLo nuevo va arriba.\n\n" + cuerpo, encoding="utf-8", newline="\n")
    de_archivo = memoria / "registro-viejo.md"
    de_archivo.write_text(frontmatter("registro-viejo", "(archivo) Lo de antes del registro del vivero, entrada por entrada",
                                      "project") + "# Registro viejo (archivo)\n\n" + cuerpo, encoding="utf-8", newline="\n")
    archivo_antes = de_archivo.read_bytes()
    (memoria / "MEMORY.md").write_text("# Memoria\n\n- [Registro](registro.md) — una entrada por arreglo\n"
                                       "- [Registro viejo (archivo)](registro-viejo.md) — lo de antes\n", encoding="utf-8",
                                       newline="\n")

    def configurar(**mas):
        (mundo / "config.json").write_text(json.dumps(dict({"usuario": "Ana", "fuentes": [
            {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]],
             "memoria": True, "foco": True}]}, **mas), ensure_ascii=False), encoding="utf-8", newline="\n")

    def renglones():
        return sorted(r for p in memoria.glob("*.md") for r in p.read_text(encoding="utf-8").split("\n") if r.strip())

    antes = registro.read_bytes()
    todos = renglones()
    viejo = time.time() - 3600
    os.utime(registro, (viejo, viejo))
    os.utime(de_archivo, (viejo, viejo))
    configurar()
    _, salud = cerebro_en(mundo, "--salud", "--todo")
    codigo, salida = cerebro_en(mundo, "--dormir")
    _, que_haria = cerebro_en(mundo, "--por-partir")
    probar("apagado de fábrica: el médico avisa que la memoria está por llenarse, --por-partir dice qué entradas pasaría, "
           "y la pasada de cada día no toca nada",
           codigo == 0 and registro.read_bytes() == antes and len(list(memoria.glob("*.md"))) == 3
           and "del tope de un Read" in salud and "La pasada de cada día" not in salud
           and "pasarían a registro-historia-1.md" in que_haria and "Con «partir_sola» prendido" in que_haria
           and "registro-viejo" not in que_haria,
           (salida[-300:], que_haria))
    configurar(partir_sola=True)
    os.utime(registro, None)
    codigo, salida = cerebro_en(mundo, "--dormir")
    probar("prendido, no toca una memoria que se guardó hace menos de diez minutos (otro chat puede estar escribiéndola) y "
           "dice por qué",
           codigo == 0 and registro.read_bytes() == antes and "No partió sola registro.md" in salida
           and "menos de 10 minutos" in salida, salida[-400:])
    os.utime(registro, (viejo, viejo))
    codigo, salida = cerebro_en(mundo, "--dormir")
    historia = memoria / "registro-historia-1.md"
    quedo = registro.read_text(encoding="utf-8")
    se_fue = historia.read_text(encoding="utf-8") if historia.exists() else ""
    agregados = [r for r in renglones() if r not in todos]
    probar("prendido, la pasada de cada día pasa las entradas más viejas a una nota de historia: la memoria queda cerca de "
           "la mitad del tope, las de los últimos días no se mueven y no se pierde ni un renglón",
           codigo == 0 and "Partió sola registro.md" in salida and 20000 < len(quedo.encode()) < 26000
           and all(f"arreglo {d}\n" in quedo for d in range(4)) and "arreglo 39\n" in se_fue and "arreglo 39\n" not in quedo
           and not [r for r in todos if r not in renglones()] and len(agregados) < 12, (salida[-300:], len(quedo), agregados))
    cabeza = nucleo.separar_frontmatter(se_fue)[0]
    indice = (memoria / "MEMORY.md").read_text(encoding="utf-8")
    probar("la nota de historia nace como archivo, con las fechas de lo que lleva en su description y en el renglón del "
           "índice, y la vigente dice a dónde fue lo viejo",
           nucleo.dato(cabeza, "description").startswith("(archivo) Registro: ") and " entradas viejas, del " in
           nucleo.dato(cabeza, "description") and "](registro-historia-1.md) — del " in indice
           and "pasó a [[registro-historia-1]]." in quedo, (cabeza, indice))
    aviso = dormir.aviso_partidas(str(mundo), "chat0001")
    probar("a cada chat le avisa una sola vez qué memoria partió, a qué nota fue lo viejo y que la relea antes de editarla",
           aviso and "registro.md" in aviso and "registro-historia-1.md" in aviso and "releela" in aviso
           and dormir.aviso_partidas(str(mundo), "chat0001") is None and dormir.aviso_partidas(str(mundo), "chat0002"),
           aviso)
    pedido = json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "¿cómo quedó el registro de arreglos del vivero?",
                         "cwd": str(mundo), "session_id": "chat0003-x"}).encode("utf-8")
    del_hook = [correr_hook("hook_servir.py", pedido, CEREBRO_CONFIG=str(mundo / "config.json")).stdout for _ in range(2)]
    probar("y el hook de cada pedido se lo pasa a Claude, también una sola vez por chat",
           b"sola 1 memoria" in del_hook[0] and b"registro-historia-1.md" in del_hook[0] and b"releela" in del_hook[0]
           and b"sola 1 memoria" not in del_hook[1], del_hook)
    partida = registro.read_bytes()
    codigo, salida = cerebro_en(mundo, "--dormir")
    probar("la pasada siguiente no la vuelve a partir, porque ya está por debajo del tope; y una nota de archivo no se "
           "parte nunca sola, por grande que sea",
           codigo == 0 and registro.read_bytes() == partida and len(list(memoria.glob("*.md"))) == 4
           and de_archivo.read_bytes() == archivo_antes, salida[-300:])
    def crecer(desde_dia, cuantas):
        texto = registro.read_text(encoding="utf-8")
        mas = "".join(f"## {(real - datetime.timedelta(days=d)).isoformat()} — arreglo {d}\n\n- **Problema:** "
                      + "palabra " * 130 + "\n- **Arreglo:** listo.\n\n" for d in range(desde_dia, desde_dia + cuantas))
        rastro = texto.rindex("Lo que estaba acá")
        registro.write_text(texto[:rastro] + mas + texto[rastro:], encoding="utf-8", newline="\n")
        os.utime(registro, (viejo, viejo))

    configurar(partir_sola={"desde": 85, "hasta": 60})
    crecer(60, 18)
    todos = renglones()
    en_historia = se_fue.count("\n## ")
    codigo, salida = cerebro_en(mundo, "--dormir")
    junta = historia.read_text(encoding="utf-8")
    cabeza = nucleo.separar_frontmatter(junta)[0]
    cuantas = re.search(r": (\d+) entradas viejas, del ", nucleo.dato(cabeza, "description"))
    dia_viejo = real - datetime.timedelta(days=77)
    probar("cuando vuelve a llenarse, lo viejo se suma a la última nota de historia mientras tenga lugar, en vez de crear "
           "otra: no nace una nota nueva ni un renglón más en el índice, y no se pierde ni un renglón",
           codigo == 0 and "Partió sola registro.md" in salida and not (memoria / "registro-historia-2.md").exists()
           and "arreglo 77\n" in junta and "arreglo 39\n" in junta and "\n## Entradas del " in junta
           and not [r for r in todos if r not in renglones() and not r.startswith("description: ")
                    and "](registro-historia-1.md)" not in r]
           and (memoria / "MEMORY.md").read_text(encoding="utf-8").count("\n- ") == indice.count("\n- "), salida[-300:])
    probar("la description de esa nota y su renglón del índice pasan a contar todas las entradas y las fechas de punta a "
           "punta",
           cuantas and int(cuantas.group(1)) > en_historia - 1
           and f"del {dia_viejo.day}/{dia_viejo.month}/{dia_viejo.year} al " in nucleo.dato(cabeza, "description")
           and f"](registro-historia-1.md) — del {dia_viejo.day}/{dia_viejo.month}/{dia_viejo.year} al "
           in (memoria / "MEMORY.md").read_text(encoding="utf-8"), (cabeza, en_historia))
    crecer(100, 20)
    codigo, salida = cerebro_en(mundo, "--dormir")
    probar("y cuando en la última ya no entra, abre una nota de historia nueva",
           codigo == 0 and (memoria / "registro-historia-2.md").exists()
           and "arreglo 119\n" in (memoria / "registro-historia-2.md").read_text(encoding="utf-8")
           and historia.read_text(encoding="utf-8") == junta, salida[-300:])
    listado = (memoria / "MEMORY.md").read_text(encoding="utf-8")
    _, salud = cerebro_en(mundo, "--salud", "--todo")
    probar("esa segunda historia no le suma un renglón al índice: el de la primera pasa a juntar las dos, y el médico las "
           "sigue contando como listadas",
           listado.count("\n- ") == indice.count("\n- ")
           and re.search(r"\n- Registro, historias \(archivo\): \[1\]\(registro-historia-1\.md\) del [^;\n]+; "
                         r"\[2\]\(registro-historia-2\.md\) del [^;\n]+\n", listado)
           and "no lista" not in salud and "4 entradas" in salud, (listado, salud[:600]))
    segunda = memoria / "registro-historia-2.md"

    def con_lugar(descripcion, peso):
        nodo = {"id": "h2", "ruta": str(segunda), "titulo": "Registro, historia 2 (archivo)", "descripcion": descripcion}
        falso = types.SimpleNamespace(por_id={"h2": nodo}, por_ruta={nucleo.normalizar(segunda): "h2"})
        return ordenar.historia_con_lugar(falso, registro, peso)[0] is not None

    sola = "(archivo) Registro: 20 entradas viejas, del 1/7/2026 al 20/7/2026; lo vigente está en registro"
    probar("solo le agrega a una nota de historia que hizo ella misma y mientras entre: a una escrita a mano (con otra "
           "description) no la toca, y si lo nuevo no entra tampoco",
           con_lugar(sola, 1000) and not con_lugar("(archivo) Lo de julio, escrito a mano; lo vigente está en registro", 1000)
           and not con_lugar(sola, 45000) and not con_lugar(sola.replace("1/7/2026", "41/7/2026"), 1000))
    llena = memoria / "bitacora.md"
    llena.write_text(frontmatter("bitacora", "Bitácora del vivero, una entrada por arreglo", "project")
                     + "# Bitácora\n\nLo nuevo va arriba.\n\n" + cuerpo + cuerpo, encoding="utf-8", newline="\n")

    def de_la_llena(frase="no entra en un Read"):
        salud = cerebro_en(mundo, "--salud", "--todo")[1]
        return next((r for r in salud.splitlines() if "bitacora.md" in r and frase in r), salud[-600:])
    con_pasada = de_la_llena()
    dormir.guardar_partidas(str(mundo), time.time(), [], [
        {"nota": str(llena), "lleno": 176, "motivo": "no tiene ni un renglón suelto por donde cortarla"},
        {"nota": str(registro), "lleno": 90, "espera": True, "motivo": "se guardó hace menos de 10 minutos"}])
    trabada = de_la_llena()
    llena.write_text(frontmatter("bitacora", "Bitácora del vivero, una entrada por arreglo", "project")
                     + "# Bitácora\n\nLo nuevo va arriba.\n\n" + cuerpo, encoding="utf-8", newline="\n")
    casi_trabada = de_la_llena("del tope de un Read")
    dormir.guardar_partidas(str(mundo), time.time(), [], [])
    casi_sola = de_la_llena("del tope de un Read")
    configurar()
    llena.write_text(frontmatter("bitacora", "Bitácora del vivero, una entrada por arreglo", "project")
                     + "# Bitácora\n\nLo nuevo va arriba.\n\n" + cuerpo + cuerpo, encoding="utf-8", newline="\n")
    sin_pasada = de_la_llena()
    probar("con «partir_sola» prendido, la memoria que ya no entra en un Read queda «para revisar» (así no llega a los "
           "chats como problema nuevo) y dice que la pasada la parte sola, no que la partan a mano",
           con_pasada.startswith("REVISAR ") and "la pasada de cada día la parte sola" in con_pasada
           and "--partir-llenas" in con_pasada and "lo decide" not in con_pasada
           and '--partir "bitacora.md"' not in con_pasada, con_pasada)
    probar("si la última pasada no la pudo partir, vuelve a ser un aviso con el motivo y el comando para hacerlo a mano (y "
           "la que está casi llena tampoco promete que la parte sola, pero sí cuando la pasada puede); apagado, sigue el "
           "aviso de antes",
           trabada.startswith("AVISO ") and "no la pudo partir sola: no tiene ni un renglón suelto" in trabada
           and '--partir "bitacora.md"' in trabada and casi_trabada.startswith("REVISAR ")
           and "no la pudo partir sola" in casi_trabada and "la parte sola y lo avisa" not in casi_trabada
           and "La pasada de cada día la parte sola y lo avisa" in casi_sola and "no la pudo" not in casi_sola
           and sin_pasada.startswith("AVISO ") and "lo decide Ana" in sin_pasada
           and '--partir "bitacora.md"' in sin_pasada, (trabada, casi_trabada, casi_sola, sin_pasada))
    llena.unlink()
    configurar(partir_sola={"desde": 40, "hasta": 90})
    codigo, salida = cerebro_en(mundo, "--salud")
    probar("un partir_sola mal escrito (hasta mayor que desde) se rechaza con un mensaje claro",
           codigo != 0 and "partir_sola" in salida and "Traceback" not in salida, salida[-300:])


def revisar_partir_siempre(t):
    seccion("Partir sola aunque no se sepa qué es lo viejo (entradas de estos días y «parte 2»)")
    import datetime
    ordenar = importlib.import_module("ordenar")
    dormir = importlib.import_module("dormir")
    hoy = datetime.date(2026, 10, 10)

    def viejas(dias, frescos):
        texto = "# Registro\n\nLo nuevo va arriba.\n\n" + "".join(
            f"## {(hoy - datetime.timedelta(days=d)).isoformat()} — arreglo {d}\n\n- **Problema:** " + "x" * 900
            + "\n- **Arreglo:** listo.\n\n" for d in dias)
        elegida = ordenar.elegir_viejas(ordenar.piezas_de(ordenar.renglones_de(texto)), len(texto.encode()), 1, hoy, frescos)
        return elegida and (elegida["entradas"], (hoy - elegida["ultima"]).days, (hoy - elegida["primera"]).days)
    probar("las entradas de estos días quedan protegidas; si no hay otra salida puede llevarse las más viejas de ellas, y "
           "siempre deja las tres últimas",
           viejas(list(range(8)), 30) is None and viejas(list(range(8)), None) == (5, 3, 7),
           (viejas(list(range(8)), 30), viejas(list(range(8)), None)))

    def relleno(cuanto):
        return ("palabra " * 12 + "\n") * (cuanto // 97)

    def corte(texto):
        renglones = ordenar.renglones_de(texto)
        elegido = ordenar.elegir_corte(renglones, ordenar.piezas_de(renglones), 25000, 40000, 2500)
        if not elegido:
            return None, 0
        return ordenar.pelado(renglones[elegido["corte"]]), len("".join(renglones[:elegido["corte"]]).encode())

    por_titulos = "# Guía\n\nPara qué sirve.\n\n" + "".join(f"## Tema {k}\n\n{relleno(3600)}\n" for k in range(12))
    renglon, queda = corte(por_titulos)
    probar("una nota sin fechas se corta en dos por un título, cerca de la mitad del tope de una lectura",
           renglon and renglon.startswith("## Tema ") and 20000 < queda < 30000, (renglon, queda))
    por_niveles = ("# Guía\n\n## A\n\n" + relleno(15000) + "\n## B\n\n" + relleno(300) + "\n### b1\n\n" + relleno(9500)
                   + "\n### b2\n\n" + relleno(5000) + "\n### b3\n\n" + relleno(6000) + "\n## C\n\n" + relleno(9000))
    renglon, queda = corte(por_niveles)
    probar("entre un título de sección y un subtítulo que cae más cerca de la mitad, corta por el de sección (no parte una "
           "sección si puede evitarlo)", renglon == "## B", (renglon, queda))
    por_items = "# Lista\n\nPara qué sirve.\n\n## Todo\n\n" + "".join(
        f"- ítem {k}: " + "palabra " * 90 + "\n" for k in range(60))
    renglon, queda = corte(por_items)
    probar("si no hay títulos por donde cortar, corta entre dos ítems",
           renglon and renglon.startswith("- ítem ") and 22000 < queda < 28000, (renglon, queda))
    por_parrafos = "".join("".join(f"Párrafo {k} renglón {j} " + "palabra " * 11 + "\n" for j in range(45)) + "\n"
                           for k in range(9))
    renglon, queda = corte(por_parrafos)
    probar("y si tampoco hay ítems, entre dos párrafos separados por un renglón en blanco (nunca en medio de un párrafo)",
           renglon and re.match(r"Párrafo \d renglón 0 ", renglon) and 20000 < queda < 30000, (renglon, queda))
    renglon, queda = corte("".join(f"renglón {j} " + "palabra " * 12 + "\n" for j in range(400)))
    probar("como último recurso, una nota que es un solo párrafo larguísimo se corta entre dos renglones, cerca de la mitad",
           renglon and re.match(r"renglón \d+ ", renglon) and 20000 < queda < 30000, (renglon, queda))
    con_cola = corte("".join(f"renglón {j} " + "palabra " * 12 + "\n" for j in range(400)) + "\n## Cola\n\n" + relleno(1500))
    probar("no corta dentro de un bloque de código (ni como último recurso), y no saca una parte de migajas: si el único "
           "título dejaría casi todo donde está, corta entre renglones",
           corte("Introducción.\n\n" + relleno(4000) + "\n```text\n" + por_parrafos + "```\n")[0] == "```text"
           and corte("Introducción.\n\n```text\n" + por_parrafos + "```\n")[0] is None
           and corte("```text\n" + por_parrafos + "```\n")[0] is None
           and re.match(r"renglón \d+ ", con_cola[0] or "") and 20000 < con_cola[1] < 30000,
           (corte("Introducción.\n\n" + relleno(4000) + "\n```text\n" + por_parrafos + "```\n"),
            corte("Introducción.\n\n```text\n" + por_parrafos + "```\n"), corte("```text\n" + por_parrafos + "```\n"),
            con_cola))
    renglon, queda = corte("Introducción.\n\n" + relleno(4000) + "\n## Único\n\n- ítem grande: " + "palabra " * 5500 + "\n")
    probar("no deja un título solo al final de la primera parte: el corte no cae justo debajo de un título",
           renglon == "## Único", (renglon, queda))
    casi_nada = corte("Introducción.\n\n## Único\n\n- ítem grande: " + "palabra " * 5500 + "\n")
    probar("si arriba del único corte no queda casi nada, no corta: la parte nueva sería igual de grande y se volvería a "
           "partir sin fin", casi_nada[0] is None, casi_nada)
    carpeta = t / "tomos"
    carpeta.mkdir()
    guia = carpeta / "guia.md"
    guia.write_text(frontmatter("guia", "Guía del vivero (VIGENTE): suelo, riego y poda", "project")
                    + "# Guía\n\nPara qué sirve.\n\n## Suelo\n\n- Arena y turba.\n\n## Riego\n\nDos veces por semana.\n\n"
                      "### Goteo\n\n- Media hora.\n- Con filtro.\n\n## Poda\n\nEn invierno.\n", encoding="utf-8", newline="\n")
    indice = carpeta / "MEMORY.md"
    indice.write_text("# Memoria\n\n- [Guía del vivero (VIGENTE)](guia.md) — suelo, riego y poda\n"
                      "- Guía, historias (archivo): [1](guia-historia-1.md) 2025; [2](guia-historia-2.md) 2026\n"
                      "- [Otra](otra.md) — otra cosa\n", encoding="utf-8", newline="\n")

    def renglon_de(ruta, texto):
        return next(i for i, r in enumerate(ordenar.renglones_de(ordenar.leer(ruta)[2])) if ordenar.pelado(r) == texto)

    def con_texto(ruta):
        return [r for r in ruta.read_text(encoding="utf-8").split("\n") if r.strip()]

    original = con_texto(guia)
    cuantos = len(ordenar.renglones_de(ordenar.leer(guia)[2]))
    malos = [ordenar.planear(guia, "", memoria=True, corte=k)[0] for k in (
        0, 3, renglon_de(guia, "# Guía"), renglon_de(guia, "## Riego") - 1, cuantos, cuantos + 5)]
    probar("un corte que se llevaría la nota entera, que cae en el encabezado, en un renglón en blanco o fuera de la nota "
           "se rechaza", malos == [None] * 6, malos)
    plan, error = ordenar.planear(guia, "", memoria=True, indice=indice, titulo_nota="Guía del vivero (VIGENTE)",
                                  corte=renglon_de(guia, "## Riego"))
    falla = ordenar.aplicar(plan, str(carpeta))[2] if plan else error
    parte = carpeta / "guia-parte-2.md"
    quedo = guia.read_text(encoding="utf-8")
    se_fue = parte.read_text(encoding="utf-8") if parte.exists() else ""
    cabeza = nucleo.separar_frontmatter(se_fue)[0]
    probar("la segunda mitad pasa a una nota «…-parte-2» que no es archivo: su description dice de qué nota sigue y qué "
           "secciones lleva, y adentro dice que es la misma nota",
           not falla and nucleo.dato(cabeza, "description") == "Parte 2 de «Guía del vivero» (sigue de guia): «Riego»; «Poda»"
           and "# Guía del vivero, parte 2\n" in se_fue and "Sigue de [[guia]]. No es archivo" in se_fue
           and "\n## Riego\n" in se_fue and "\n### Goteo\n" in se_fue and "\n## Poda\n" in se_fue, (falla, cabeza, se_fue[:300]))
    probar("la primera parte termina diciendo dónde sigue y con qué secciones, y entre las dos no se pierde ni un renglón",
           re.search(r"\n\nSigue en \[\[guia-parte-2\]\] \(5 piezas\): «Riego»; «Poda»\n$", quedo)
           and "## Riego" not in quedo and "## Suelo" in quedo
           and not [r for r in original if r not in con_texto(guia) + con_texto(parte)], quedo[-200:])
    listado = indice.read_text(encoding="utf-8").split("\n")
    probar("el índice gana un renglón para la parte 2, debajo de los de esa nota y sin mezclarla con sus historias de archivo",
           listado[4] == "- [Guía del vivero, parte 2](guia-parte-2.md) — sigue de guia: «Riego» y lo que sigue"
           and listado[3].endswith("[2](guia-historia-2.md) 2026") and listado[5].startswith("- [Otra]"), listado)
    plan, error = ordenar.planear(parte, "", memoria=True, indice=indice, titulo_nota="Guía del vivero, parte 2",
                                  corte=renglon_de(parte, "### Goteo"))
    falla = ordenar.aplicar(plan, str(carpeta))[2] if plan else error
    tercera = carpeta / "guia-parte-3.md"
    se_fue = tercera.read_text(encoding="utf-8") if tercera.exists() else ""
    listado = indice.read_text(encoding="utf-8").split("\n")
    probar("si una parte vuelve a llenarse, lo que sale va a «…-parte-3» (no a «…-parte-2-parte-2»), que dice de qué "
           "sección viene lo primero, y su renglón del índice queda debajo del de la parte 2",
           not falla and "# Guía del vivero, parte 3\n" in se_fue
           and "Sigue de [[guia-parte-2]]; lo primero es de la sección «Riego»." in se_fue
           and listado[5].startswith("- [Guía del vivero, parte 3](guia-parte-3.md) — sigue de guia-parte-2: «Goteo»")
           and listado[6].startswith("- [Otra]")
           and not [r for r in original if r not in con_texto(guia) + con_texto(parte) + con_texto(tercera)],
           (falla, se_fue[:300], listado))
    cruzado = ("# Memoria\n\n- [Lanzador](lanzador.md) — la 0.8 se cuenta en [guia](guia.md)\n"
               "- [Guía](guia.md) — suelo, riego y poda\n- [Otra](otra.md) — otra cosa\n")
    con_renglon = (ordenar.cambio_de_indice(cruzado, "guia.md", "guia-historia-1.md", "Guía, historia 1 (archivo)",
                                            "del 1/7/2026 al 5/7/2026", 1)[0] or "").split("\n")
    solo_nombrada = (ordenar.cambio_de_indice(cruzado.replace("- [Guía](guia.md) — suelo, riego y poda\n", ""), "guia.md",
                                              "guia-historia-1.md", "Guía, historia 1 (archivo)", "del 1/7/2026 al 5/7/2026",
                                              1)[0] or "").split("\n")
    probar("el renglón nuevo del índice va debajo del renglón propio de la nota, no debajo de otro que solo la nombra "
           "(así el de una historia cayó en otra sección); si ninguno es el propio, debajo del que la nombra",
           con_renglon[3:5] == ["- [Guía](guia.md) — suelo, riego y poda",
                                "- [Guía, historia 1 (archivo)](guia-historia-1.md) — del 1/7/2026 al 5/7/2026"]
           and solo_nombrada[3:4] == ["- [Guía, historia 1 (archivo)](guia-historia-1.md) — del 1/7/2026 al 5/7/2026"],
           (con_renglon, solo_nombrada))
    con_una = ("# Memoria\n\n- [Guía](guia.md) — suelo, riego y poda\n"
               "- [Guía, historia 1 (archivo)](guia-historia-1.md) — del 1/7/2026 al 5/7/2026\n- [Otra](otra.md) — otra cosa\n")
    las_dos, dicho = ordenar.cambio_de_indice(con_una, "guia.md", "guia-historia-2.md", "Guía, historia 2 (archivo)",
                                              "del 6/7/2026 al 9/7/2026", 2)
    probar("la segunda historia de una nota no le suma un renglón al índice: el de la primera pasa a juntar las dos, con el "
           "gancho de cada una entero",
           las_dos == con_una.replace("- [Guía, historia 1 (archivo)](guia-historia-1.md) — del 1/7/2026 al 5/7/2026\n",
                                      "- Guía, historias (archivo): [1](guia-historia-1.md) del 1/7/2026 al 5/7/2026; "
                                      "[2](guia-historia-2.md) del 6/7/2026 al 9/7/2026\n")
           and "pasa a juntar las historias" in dicho, (las_dos, dicho))
    a_mano = con_una.replace("[Guía, historia 1 (archivo)]", "[Lo viejo de la guía]")
    sin_nombre = ordenar.cambio_de_indice(a_mano, "guia.md", "guia-historia-2.md", "Más cosas viejas", "de julio", 2)[0] or ""
    con_nombre = ordenar.cambio_de_indice(a_mano, "guia.md", "guia-historia-2.md", "Guía, historia 2 (archivo)", "de julio",
                                          2)[0] or ""
    probar("si ni el renglón de la primera ni el título de la nueva dicen de qué nota son historia, no inventa un nombre: "
           "agrega el renglón como antes; con uno de los dos alcanza para juntarlas, y el título escrito a mano queda",
           sin_nombre.count("\n- ") == 4 and "- [Lo viejo de la guía](guia-historia-1.md) — del 1/7/2026" in sin_nombre
           and con_nombre.count("\n- ") == 3 and "- Guía, historias (archivo): [1](guia-historia-1.md) Lo viejo de la guía — "
           "del 1/7/2026 al 5/7/2026; [2](guia-historia-2.md) de julio\n" in con_nombre, (sin_nombre, con_nombre))
    de_otra = ("- [Poda, historia 1 (archivo)](poda-historia-1.md) — lo de 2024\n"
               "- [Poda, historia 2 (archivo)](poda-historia-2.md) — lo de 2025\n")
    solo_la_suya = ordenar.cambio_de_indice(con_una + de_otra, "guia.md", "guia-historia-2.md", "Guía, historia 2 (archivo)",
                                            "de julio", 2)[0] or ""
    probar("al partir una nota solo junta las historias de esa nota: los renglones sueltos de otra quedan como estaban (esos "
           "los junta la pasada de cada día, con su copia y su aviso)",
           solo_la_suya.endswith(de_otra) and "- Guía, historias (archivo): [1](guia-historia-1.md)" in solo_la_suya,
           solo_la_suya)
    pegada = carpeta / "pegada.md"
    pegada.write_text("# Notas\n\nPrimera línea.\nÚltima línea.\n## Final\n\nLo del final.\n", encoding="utf-8", newline="\n")
    lista = carpeta / "lista.md"
    lista.write_text("# Lista\n\n- Uno.\n- Dos.\n- Tres.\n", encoding="utf-8", newline="\n")
    sin_blanco = ordenar.planear(pegada, "", memoria=True, corte=renglon_de(pegada, "## Final"))[0]
    entre_items = ordenar.planear(lista, "", memoria=True, corte=renglon_de(lista, "- Tres."))[0]
    probar("el aviso de dónde sigue queda como párrafo aparte aunque el título cortado viniera pegado al texto, y como "
           "ítem cuando el corte cae entre dos ítems",
           sin_blanco and sin_blanco["bytes_fuente"].decode("utf-8").endswith(
               "Última línea.\n\nSigue en [[pegada-parte-2]] (1 pieza): «Final»\n")
           and entre_items and entre_items["bytes_fuente"].decode("utf-8").endswith(
               "- Dos.\n- Sigue en [[lista-parte-2]] (1 pieza): «Tres.»\n"),
           (sin_blanco and sin_blanco["bytes_fuente"][-120:], entre_items and entre_items["bytes_fuente"][-120:]))
    justa = carpeta / "justa.md"
    justa.write_text("".join(f"renglón {j} " + "palabra " * 12 + "\n" for j in range(400)) + "\nCierre: "
                     + "palabra " * 400 + "\n", encoding="utf-8", newline="\n")
    falso = types.SimpleNamespace(carpeta_de={"j": str(carpeta)}, nodos=[], por_id={}, por_ruta={})
    plan, dicho, error = ordenar.plan_sola(falso, {"id": "j", "ruta": str(justa), "titulo": "Justa"},
                                           justa.stat().st_size / 50000, {"desde": 85, "hasta": 50, "dias_frescos": 3}, hoy)
    probar("si ningún corte alcanza a dejarla holgada, igual hace el que más alivia en vez de no hacer nada",
           plan and dicho.get("tomo") and dicho["primero"].startswith("Cierre: ")
           and len(plan["bytes_fuente"]) > 40000, (dicho, error))
    mundo = t / "partir-siempre"
    memoria = mundo / "memoria"
    memoria.mkdir(parents=True)
    (mundo / "en-vivo").mkdir()
    real = datetime.date.today()

    def paso(dias, k):
        return (f"## {(real - datetime.timedelta(days=dias)).isoformat()} — paso {dias}.{k}\n\n- **Qué:** "
                + "palabra " * 450 + "\n- **Listo.**\n\n")

    frescas = memoria / "frescas.md"
    frescas.write_text(frontmatter("frescas", "Mudanza del vivero, paso a paso", "project")
                       + "# Mudanza\n\nLo nuevo va abajo.\n\n" + paso(40, 0)
                       + "".join(paso(d, k) for d in (2, 1, 0) for k in range(4)), encoding="utf-8", newline="\n")
    sin_fechas = memoria / "sinfechas.md"
    sin_fechas.write_text(frontmatter("sinfechas", "Cómo se cuida cada planta del vivero", "project")
                          + "# Cuidados\n\nUna sección por planta.\n\n"
                          + "".join(f"## Planta {k}\n\n" + "palabra " * 450 + "\n\n" for k in range(12)),
                          encoding="utf-8", newline="\n")
    bloque = memoria / "bloque.md"
    bloque.write_text(frontmatter("bloque", "Inventario del vivero, todo seguido", "project") + "```text\n"
                      + "".join(f"renglón {j} " + "palabra " * 12 + "\n" for j in range(400)) + "```\n",
                      encoding="utf-8", newline="\n")
    (memoria / "MEMORY.md").write_text("# Memoria\n\n- [Mudanza](frescas.md) — paso a paso\n"
                                       "- [Cuidados](sinfechas.md) — una sección por planta\n"
                                       "- [Inventario](bloque.md) — todo seguido\n", encoding="utf-8", newline="\n")

    def configurar(**mas):
        (mundo / "config.json").write_text(json.dumps(dict({"usuario": "Ana", "fuentes": [
            {"id": "memoria", "nombre": "Memoria", "color": "#E64980", "raices": [[str(memoria), False, ""]],
             "memoria": True, "foco": True}]}, **mas), ensure_ascii=False), encoding="utf-8", newline="\n")

    def renglones():
        return sorted(r for p in memoria.glob("*.md") for r in p.read_text(encoding="utf-8").split("\n") if r.strip())

    def del_renglon(salida, nombre):
        return next((r for r in salida.split("\n") if nombre in r), "")

    viejo = time.time() - 3600
    for nota in (frescas, sin_fechas, bloque):
        os.utime(nota, (viejo, viejo))
    todos = renglones()
    configurar()
    codigo, salida = cerebro_en(mundo, "--partir-llenas")
    probar("--partir-llenas con «partir_sola» apagado no toca nada y lo dice",
           codigo == 1 and "apagado" in salida and renglones() == todos and len(list(memoria.glob("*.md"))) == 4, salida)
    configurar(partir_sola=True)
    os.utime(sin_fechas, None)
    codigo, salida = cerebro_en(mundo, "--dormir")
    historia = memoria / "frescas-historia-1.md"
    se_fue = historia.read_text(encoding="utf-8") if historia.exists() else ""
    quedo = frescas.read_text(encoding="utf-8")
    probar("cuando lo viejo no alcanza para aliviar la nota, la pasada se lleva también las entradas más viejas de estos "
           "días a la nota de historia, y deja las últimas",
           codigo == 0 and "Partió sola frescas.md" in salida and "pasaron a frescas-historia-1.md" in salida
           and "paso 40.0\n" in se_fue and "paso 2.3\n" in se_fue and "paso 1.0\n" in se_fue
           and all(f"paso 0.{k}\n" in quedo for k in range(4)) and "paso 2.0\n" not in quedo
           and len(quedo.encode()) < 30000, (salida[-600:], len(quedo)))
    probar("la que se estaba editando no la toca todavía y dice que vuelve a probar en media hora, sin mandar a nadie a "
           "partirla a mano; la que es un solo bloque sí queda para partir a mano, con el porqué",
           "menos de 10 minutos; vuelve a probar en media hora" in del_renglon(salida, "sinfechas.md")
           and "A mano" not in del_renglon(salida, "sinfechas.md") and "un solo bloque" in del_renglon(salida, "bloque.md")
           and "A mano" in del_renglon(salida, "bloque.md") and not (memoria / "sinfechas-parte-2.md").exists(),
           salida[-600:])
    ahora = time.time()
    falso = mundo / "armar.py"
    falso.write_text("import sys\nfrom pathlib import Path\nPath(__file__).with_name('lanzado.txt').write_text(sys.argv[1])\n",
                     encoding="utf-8")
    antes_de_tiempo = dormir.falta_partir(str(mundo), ahora + 60) or dormir.despertar(str(mundo), str(falso), ahora + 60)
    lanzo = dormir.despertar(str(mundo), str(falso), ahora + 1801)
    for _ in range(100):
        if (mundo / "lanzado.txt").exists():
            break
        time.sleep(0.1)
    lanzado = (mundo / "lanzado.txt").read_text(encoding="utf-8") if (mundo / "lanzado.txt").exists() else ""
    probar("pasada media hora, el primer pedido larga de fondo solo la partición (no toda la pasada del día); antes, nada",
           not antes_de_tiempo and lanzo and lanzado == "--partir-llenas", (antes_de_tiempo, lanzo, lanzado))
    os.utime(sin_fechas, (viejo, viejo))
    todos = renglones()
    codigo, salida = cerebro_en(mundo, "--partir-llenas")
    parte = memoria / "sinfechas-parte-2.md"
    se_fue = parte.read_text(encoding="utf-8") if parte.exists() else ""
    quedo = sin_fechas.read_text(encoding="utf-8")
    cabeza = nucleo.separar_frontmatter(se_fue)[0]
    en_parte = [k for k in range(12) if f"## Planta {k}\n" in se_fue]
    agregados = [r for r in renglones() if r not in todos]
    probar("la nota sin fechas se parte sola en dos: la primera mitad queda, la segunda pasa a «sinfechas-parte-2», cada "
           "sección entera en una de las dos, y no se pierde ni un renglón",
           codigo == 0 and "Partió sola sinfechas.md" in salida and 20000 < len(quedo.encode()) < 30000
           and en_parte and en_parte == list(range(en_parte[0], 12))
           and [k for k in range(12) if f"## Planta {k}\n" in quedo] == list(range(en_parte[0]))
           and not [r for r in todos if r not in renglones()] and len(agregados) < 12,
           (salida[-400:], len(quedo), en_parte, agregados))
    probar("esa parte 2 nace como nota común (no archivo), queda en el índice y ya no hay nada esperando para reintentar",
           nucleo.dato(cabeza, "description").startswith("Parte 2 de «Cuidados» (sigue de sinfechas): «Planta ")
           and "](sinfechas-parte-2.md) — sigue de sinfechas: «Planta " in (memoria / "MEMORY.md").read_text(encoding="utf-8")
           and not dormir.falta_partir(str(mundo), time.time() + 1801), cabeza)
    aviso = dormir.aviso_partidas(str(mundo), "chat0001") or ""
    registro = mundo / "respaldos" / "partidas.log"
    anotado = registro.read_text(encoding="utf-8").splitlines() if registro.exists() else []
    _, que_haria = cerebro_en(mundo, "--por-partir")
    _, salud = cerebro_en(mundo, "--salud", "--todo")
    probar("cada partición queda escrita en un registro (fecha, nota, qué pasó a dónde y la copia), --por-partir muestra lo "
           "último, y a cada chat le avisa de las dos",
           len(anotado) == 2 and "frescas.md" in anotado[0] and "pasaron a frescas-historia-1.md" in anotado[0]
           and "sinfechas.md" in anotado[1] and "pasó a sinfechas-parte-2.md, que no es archivo" in anotado[1]
           and all("copia de antes en " in r and re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d  ", r) for r in anotado)
           and "Lo último que partió sola" in que_haria and "sinfechas-parte-2.md" in que_haria
           and "frescas-historia-1.md" in aviso and "sinfechas-parte-2.md" in aviso and "releela" in aviso,
           (anotado, que_haria[-400:], aviso))
    probar("de la casi llena que la pasada no pudo partir, el médico no promete que se parte sola: dice por qué no y cómo "
           "partirla a mano; y no se queja de las notas nuevas",
           "no la pudo partir sola: no tiene ni un renglón suelto" in del_renglon(salud, "bloque.md:1")
           and '--partir "bloque.md"' in del_renglon(salud, "bloque.md:1")
           and "--partir-llenas lo hace ahora" not in del_renglon(salud, "bloque.md:1")
           and "sinfechas-parte-2.md" not in salud and "frescas-historia-1.md" not in salud, salud[-900:])
    partidas = {p.name: p.read_bytes() for p in memoria.glob("*.md")}
    codigo, salida = cerebro_en(mundo, "--partir-llenas")
    probar("volver a correrla no parte nada más: lo que ya quedó por debajo del tope no se toca",
           codigo == 0 and {p.name: p.read_bytes() for p in memoria.glob("*.md")} == partidas
           and len(registro.read_text(encoding="utf-8").splitlines()) == 2, salida[-300:])
