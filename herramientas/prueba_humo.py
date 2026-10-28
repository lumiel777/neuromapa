from humo import (base, ajustes, aprendizaje, busqueda, casos_raros, consola, diagnostico, en_vivo, instalacion,
                  ordenar_notas, pagina, partir, pasada, pista, plugin, versiones)
from humo.base import *
from humo.ajustes import *
from humo.aprendizaje import *
from humo.busqueda import *
from humo.casos_raros import *
from humo.consola import *
from humo.diagnostico import *
from humo.en_vivo import *
from humo.instalacion import *
from humo.ordenar_notas import *
from humo.pagina import *
from humo.partir import *
from humo.pasada import *
from humo.pista import *
from humo.plugin import *
from humo.versiones import *

base.PARTES.extend([ajustes, aprendizaje, busqueda, casos_raros, consola, diagnostico, en_vivo, instalacion,
                    ordenar_notas, pagina, partir, pasada, pista, plugin, versiones])


def paso(nombre, funcion, *argumentos):
    try:
        return funcion(*argumentos)
    except Exception:
        print(traceback.format_exc().rstrip())
        probar(f"{nombre} corrió entero", False)
        return None


def main():
    parser = argparse.ArgumentParser(description="Arma un cerebro con notas inventadas y revisa que todo responda.")
    parser.add_argument("--dejar", action="store_true", help="no borra la carpeta de prueba, para mirarla")
    argumentos = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    comienzo = time.perf_counter()
    t = Path(tempfile.mkdtemp(prefix="cerebro-humo-"))
    print(f"Prueba de humo de Neuromapa · carpeta de prueba: {t}")
    try:
        armar_carpeta(t)
        con_git = crear_repo(t / "proyecto")
        aislado = paso("el aislamiento", lambda: aislar(t) or revisar_aislamiento(t))
        if not aislado:
            print("\nFrené acá: algo apunta a las carpetas reales y la prueba podría escribir en ellas.")
        else:
            paso("el hook", revisar_hook, t)
            paso("el candado en Mac y Linux", revisar_candado_posix, t)
            paso("los permisos de las carpetas", revisar_permisos, t)
            paso("exportar", revisar_exportar, t)
            paso("el chequeo de la instalación", revisar_chequeo, t)
            paso("las bibliotecas locales", revisar_librerias, t)
            paso("Python 3.10", revisar_python_310)
            datos, html = paso("la página", generar_pagina, t) or ({}, "")
            paso("el cerebro", revisar_cerebro, datos)
            paso("la configuración", revisar_configuracion, t)
            paso("los handoffs", revisar_handoffs, t)
            cerebro = paso("el armado del cerebro", armar_cerebro, t)
            if cerebro is not None:
                paso("el médico", revisar_medico, cerebro, con_git)
                paso("los problemas ya resueltos", revisar_resuelto, t)
                paso("las anclas movidas", revisar_anclas_movidas, t)
                paso("los archivos de datos rotos", revisar_datos_rotos, cerebro, t)
                paso("el buscador", revisar_buscador, cerebro, t)
                paso("el orden de la pista", revisar_orden_pista, cerebro, t)
                paso("las fichas", revisar_fichas, cerebro, t)
                paso("el conector de la app", revisar_conector, t)
                paso("parecidas y entidades", revisar_parecidas_y_entidades, cerebro, t)
                paso("las rutas de red", revisar_rutas_de_red, t)
                paso("las rutas de una carpeta temporal", revisar_rutas_temporales, t)
                paso("las copias de conflicto", revisar_copias_de_conflicto, t)
                paso("los acentos NFC y NFD", revisar_acentos, t)
                paso("la misma memoria en otra carpeta", revisar_invariancia, t)
                paso("las notas mal guardadas", revisar_codificaciones, t)
                paso("las carpetas sin alias", revisar_raices_sin_alias, t)
                paso("una carpeta sin permiso", revisar_carpeta_sin_permiso, t)
                paso("una fecha de archivo rara", revisar_fecha_rara, t)
                paso("la escritura segura", revisar_escritura_segura, t)
                paso("el tope de tiempo de git", revisar_tope_de_procesos, t)
                paso("dormir", revisar_dormir, t)
                paso("dormir con Claude", revisar_dormir_claude, t)
            paso("el mapa", revisar_mapa, t)
            paso("el JavaScript", revisar_js, t, html)
            paso("la página abierta", revisar_pagina_abierta, t, datos, html)
            paso("los registros", revisar_registros, t)
            paso("el servidor", revisar_servidor, t)
            paso("lo en vivo", revisar_vivo, t)
            paso("la demo", revisar_demo, t)
            paso("la memoria con pruebas", revisar_pruebas, t)
            paso("el hook que sirve el Cerebro", revisar_servir, t)
            paso("una nota que intenta meter órdenes", revisar_pista_hostil, t)
            paso("los problemas arreglados", revisar_arreglados, t)
            paso("el aprendizaje", revisar_aprender, t)
            paso("los choques entre chats", revisar_choques, t)
            paso("el aviso al editar código", revisar_recuerdo, t)
            paso("recordar guardar", revisar_guardar, t)
            paso("historial de la memoria", revisar_historial, t)
            paso("qué dato cambió y cuándo", revisar_vigencia, t)
            paso("ordenar una nota larga", revisar_ordenar, t)
            paso("cambiarle el nombre a una nota", revisar_renombrar, t)
            paso("los bytes al reescribir notas", revisar_bytes_al_reescribir, t)
            paso("una bóveda de Obsidian", revisar_obsidian, t)
            paso("renglones del índice con varias notas", revisar_indice_juntado, t)
            paso("partir sola la memoria casi llena", revisar_partir_sola, t)
            paso("una memoria que se llena durante el día", revisar_memoria_llena, t)
            paso("partir sola aunque no haya nada viejo", revisar_partir_siempre, t)
            paso("partir sola en varias partes", revisar_partir_en_varias, t)
            paso("tablero de pendientes", revisar_pendientes, t)
            paso("reglas por carpeta", revisar_reglas, t)
            paso("recetas que pueden ser skills", revisar_recetas, t)
            paso("buscar en las charlas viejas", revisar_buscar_charlas, t)
            paso("ver y olvidar lo aprendido", revisar_olvidar, t)
            paso("el gasto y el freno de mano", revisar_gasto, t)
            paso("los topes y filtros de respaldo", revisar_respaldos, t)
            paso("las lecciones", revisar_lecciones, t)
            paso("el plugin", revisar_plugin, t)
            paso("las opciones que se nombran", revisar_opciones_nombradas, t)
    finally:
        if argumentos.dejar:
            print(f"\nLa carpeta de prueba queda en {t}")
        elif not borrar_carpeta(t):
            print(f"\nNo pude borrar del todo la carpeta de prueba: {t}")
    bien = sum(resultados)
    segundos = format(time.perf_counter() - comienzo, ".1f").replace(".", ",")
    print(f"\n{bien} de {len(resultados)} pruebas bien ({segundos} s).")
    if salteadas:
        print(f"Sin probar en esta compu ({len(salteadas)}): {'; '.join(salteadas)}.")
    return 0 if resultados and bien == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
