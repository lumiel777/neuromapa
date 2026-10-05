import os
import stat

CODIGO = os.path.dirname(os.path.abspath(__file__))
ESCRIBIR = 0x2 | 0x4 | 0x40 | 0x40000 | 0x80000 | 0x10000000 | 0x40000000
LEER = 0x1 | 0x80000000
TODO = 0x1F01FF
HEREDA = 0x1 | 0x2
SISTEMA = "S-1-5-18"
ADMINISTRADORES = "S-1-5-32-544"
CONFIABLES = {SISTEMA, ADMINISTRADORES, "S-1-3-0", "S-1-3-4",
              "S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464"}


def crear(carpeta):
    carpeta = os.path.abspath(str(carpeta))
    if os.path.isdir(carpeta):
        return
    nuevas = [carpeta]
    while os.path.dirname(nuevas[-1]) != nuevas[-1] and not os.path.isdir(os.path.dirname(nuevas[-1])):
        nuevas.append(os.path.dirname(nuevas[-1]))
    os.makedirs(carpeta, exist_ok=True)
    for nueva in reversed(nuevas if os.name != "nt" else nuevas[-1:]):
        cerrar(nueva)


def cerrar(carpeta):
    if os.name != "nt":
        try:
            os.chmod(carpeta, 0o700)
            return True
        except OSError:
            return False
    try:
        return _cerrar_windows(str(carpeta))
    except (OSError, AttributeError, ValueError):
        return False


def ajenos(carpeta, leer=False):
    if os.name != "nt":
        if leer:
            return []
        try:
            s = os.stat(carpeta)
        except OSError:
            return None
        quienes = []
        if hasattr(os, "getuid") and s.st_uid != os.getuid():
            quienes.append("otra cuenta (es la dueña)")
        if s.st_mode & stat.S_IWGRP:
            quienes.append("su grupo")
        if s.st_mode & stat.S_IWOTH:
            quienes.append("cualquier cuenta")
        return quienes
    try:
        return _ajenos_windows(str(carpeta), ESCRIBIR | LEER if leer else ESCRIBIR)
    except (OSError, AttributeError, ValueError):
        return None


def _api():
    import ctypes
    from ctypes import wintypes
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    puntero = ctypes.c_void_p
    advapi.GetNamedSecurityInfoW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, wintypes.DWORD, puntero, puntero,
                                             ctypes.POINTER(puntero), puntero, ctypes.POINTER(puntero)]
    advapi.GetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi.SetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD, puntero, puntero, puntero,
                                             puntero]
    advapi.SetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi.GetAce.argtypes = [puntero, wintypes.DWORD, ctypes.POINTER(puntero)]
    advapi.ConvertSidToStringSidW.argtypes = [puntero, ctypes.POINTER(puntero)]
    advapi.ConvertStringSidToSidW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(puntero)]
    advapi.LookupAccountSidW.argtypes = [wintypes.LPCWSTR, puntero, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
                                         wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, puntero, wintypes.DWORD,
                                           ctypes.POINTER(wintypes.DWORD)]
    advapi.GetLengthSid.argtypes = [puntero]
    advapi.GetLengthSid.restype = wintypes.DWORD
    advapi.InitializeAcl.argtypes = [puntero, wintypes.DWORD, wintypes.DWORD]
    advapi.AddAccessAllowedAceEx.argtypes = [puntero, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, puntero]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.LocalFree.argtypes = [puntero]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    return ctypes, wintypes, advapi, kernel


def _sid_texto(api, sid):
    ctypes, _, advapi, kernel = api
    cadena = ctypes.c_void_p()
    if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(cadena)):
        return ""
    try:
        return ctypes.wstring_at(cadena.value)
    finally:
        kernel.LocalFree(cadena)


def _nombre(api, sid):
    ctypes, wintypes, advapi, _ = api
    nombre = ctypes.create_unicode_buffer(256)
    dominio = ctypes.create_unicode_buffer(256)
    largo_nombre, largo_dominio, uso = wintypes.DWORD(256), wintypes.DWORD(256), wintypes.DWORD()
    if advapi.LookupAccountSidW(None, sid, nombre, ctypes.byref(largo_nombre), dominio, ctypes.byref(largo_dominio),
                                ctypes.byref(uso)):
        return nombre.value
    return ""


def _usuario(api):
    ctypes, wintypes, advapi, kernel = api
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x8, ctypes.byref(token)):
        return ""
    try:
        largo = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(largo))
        datos = ctypes.create_string_buffer(largo.value)
        if not advapi.GetTokenInformation(token, 1, datos, largo, ctypes.byref(largo)):
            return ""
        return _sid_texto(api, ctypes.cast(datos, ctypes.POINTER(ctypes.c_void_p))[0])
    finally:
        kernel.CloseHandle(token)


def _ajenos_windows(carpeta, permisos=ESCRIBIR):
    api = _api()
    ctypes, _, advapi, kernel = api
    lista = ctypes.c_void_p()
    descriptor = ctypes.c_void_p()
    if advapi.GetNamedSecurityInfoW(carpeta, 1, 0x4, None, None, ctypes.byref(lista), None, ctypes.byref(descriptor)):
        return None
    try:
        if not lista.value:
            return ["cualquier cuenta"]
        propios = CONFIABLES | {_usuario(api)}
        quienes = []
        for i in range(ctypes.cast(lista, ctypes.POINTER(ctypes.c_ushort))[2]):
            entrada = ctypes.c_void_p()
            if not advapi.GetAce(lista, i, ctypes.byref(entrada)):
                continue
            tipo = ctypes.cast(entrada, ctypes.POINTER(ctypes.c_ubyte))[0]
            mascara = ctypes.cast(ctypes.c_void_p(entrada.value + 4), ctypes.POINTER(ctypes.c_uint32))[0]
            if tipo != 0 or not mascara & permisos:
                continue
            sid = ctypes.c_void_p(entrada.value + 8)
            texto = _sid_texto(api, sid)
            if texto and texto not in propios:
                quien = _nombre(api, sid) or texto
                if quien not in quienes:
                    quienes.append(quien)
        return quienes
    finally:
        kernel.LocalFree(descriptor)


def _cerrar_windows(carpeta):
    api = _api()
    ctypes, _, advapi, kernel = api
    usuario = _usuario(api)
    if not usuario:
        return False
    sids = []
    try:
        for texto in (usuario, SISTEMA, ADMINISTRADORES):
            sid = ctypes.c_void_p()
            if not advapi.ConvertStringSidToSidW(texto, ctypes.byref(sid)):
                return False
            sids.append(sid)
        largo = 8 + sum(8 + advapi.GetLengthSid(s) for s in sids)
        lista = ctypes.create_string_buffer(largo)
        if not advapi.InitializeAcl(lista, largo, 2):
            return False
        for sid in sids:
            if not advapi.AddAccessAllowedAceEx(lista, 2, HEREDA, TODO, sid):
                return False
        return advapi.SetNamedSecurityInfoW(carpeta, 1, 0x4 | 0x80000000, None, None, lista, None) == 0
    finally:
        for sid in sids:
            kernel.LocalFree(sid)


def comando(carpeta):
    if os.name != "nt":
        return f'chmod 700 "{carpeta}"'
    try:
        usuario = _usuario(_api())
    except (OSError, AttributeError, ValueError):
        usuario = ""
    return (f'icacls "{carpeta}" /inheritance:r /grant:r "*{usuario or "TU-SID"}:(OI)(CI)F" '
            f'"*{SISTEMA}:(OI)(CI)F" "*{ADMINISTRADORES}:(OI)(CI)F"')


def abiertas(carpetas, leer=False):
    salida = []
    for nombre, carpeta in carpetas:
        quienes = ajenos(carpeta, leer) if carpeta and os.path.isdir(carpeta) else None
        if quienes:
            salida.append((nombre, os.path.abspath(carpeta), quienes))
    return salida


def raices(halladas):
    juntas = {}
    for nombre, carpeta, quienes in halladas:
        clave = os.path.normcase(carpeta)
        if clave in juntas:
            juntas[clave][0].append(nombre)
        else:
            juntas[clave] = ([nombre], carpeta, quienes)
    return [j for c, j in juntas.items() if not any(c.startswith(o + os.sep) for o in juntas if o != c)]


def nombrar(halladas):
    return "; ".join(f'{carpeta} ({" y ".join(nombres)}: {", ".join(quienes)})'
                     for nombres, carpeta, quienes in raices(halladas))


def linea_salud(datos=None, codigo=CODIGO):
    if datos is None:
        import configuracion
        datos = configuracion.actual()["datos"]
    de_datos = (("carpeta de datos", str(datos)), ("en-vivo", os.path.join(str(datos), "en-vivo")))
    escriben = abiertas(de_datos + (("carpeta del código", str(codigo)),))
    vistas = {os.path.normcase(carpeta) for _, carpeta, _ in escriben}
    leen = [h for h in abiertas(de_datos, leer=True) if os.path.normcase(h[1]) not in vistas]
    if not escriben and not leen:
        return ""
    frases = []
    if escriben:
        del_codigo = any(nombre == "carpeta del código" for nombre, _, _ in escriben)
        efecto = "lo que Neuromapa le pasa a Claude" + (" o el código que corren los hooks" if del_codigo else "")
        frases.append(f"Otras cuentas de esta PC pueden escribir en {nombrar(escriben)}: podrían cambiar {efecto}.")
    if leen:
        frases.append(f"Otras cuentas de esta PC pueden leer {nombrar(leen)}: ahí están la página con el texto de todas "
                      "las notas y la clave del servidor.")
    arreglo = " y ".join(comando(carpeta) for _, carpeta, _ in raices(escriben + leen))
    return f'AVISO   {" ".join(frases)} Para que quede solo tuya: {arreglo}'
