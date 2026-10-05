# Cómo colaborar

Gracias por querer sumar. Neuromapa es chico a propósito: Python estándar y una página HTML. Estas son las reglas
de la casa y el porqué de cada una. (Contributions in English are welcome too.)

## Antes de cambiar algo

- Para algo más que un arreglo chico, abrí primero un issue y contá qué querés hacer.
- Leé [docs/como-funciona.md](docs/como-funciona.md): las piezas, los hooks, el registro en vivo y la configuración.

## Probar

```
python3 herramientas/prueba_humo.py
```

(En Windows, `py -3 herramientas/prueba_humo.py`.) Arma notas inventadas en una carpeta temporal y revisa todo (el hook, el médico, el buscador, el servidor, la demo,
los lanzadores con Git Bash y con PowerShell) sin tocar tus notas. Tiene que dar todo bien antes de mandar un
cambio. Las mismas pruebas corren en GitHub con Windows, Linux y Mac, en Python 3.10 y 3.13.

Para ver el mapa con notas inventadas: `sh bin/neuromapa abrir --demo`, o `bin\neuromapa.cmd abrir --demo` en Windows
(ver [demo/LEEME.md](demo/LEEME.md)).

## Las reglas y por qué

- **Solo la biblioteca estándar de Python 3.10 o más nuevo.** Nada que instalar: es una herramienta que corre en
  cada paso de Claude Code y tiene que andar en cualquier PC. d3 y marked van en `vendor/`, sin cambios.
- **Los nombres van en castellano**, igual que los mensajes. Mezclar idiomas en un mismo archivo confunde más que
  cualquiera de los dos.
- **Casi sin comentarios en el código.** El código tiene que decir qué hace con buenos nombres; el porqué de cada
  cambio va en el mensaje del commit, que es donde se busca la historia. Un comentario vale cuando algo sería
  imposible de entender sin él (por ejemplo, un truco del sistema operativo).
- **Finales de línea LF**, salvo los `.cmd` y `.bat`, que van CRLF y solo ASCII: con LF o con tildes, `cmd` los lee
  mal en una consola UTF-8. `.editorconfig` y `.gitattributes` ya lo dicen.
- **Los hooks nunca guardan texto.** El registro en vivo guarda rutas, tipos de herramienta y cantidades; nunca
  mensajes, comandos, búsquedas ni direcciones web completas. Cualquier campo nuevo pasa por esa vara, y la prueba de
  humo lo revisa con un texto secreto.
- **Los hooks no rompen Claude Code.** Ante cualquier error terminan con 0 y sin imprimir nada que no sea su JSON.
  Para ver esos errores mientras probás, `NEUROMAPA_DEPURAR=1` los muestra en la salida de errores.

## Commits y pull requests

- Un commit por cambio. El mensaje dice qué estaba mal y por qué el cambio lo arregla, y cómo lo probaste.
- Si el cambio arregla un error, sumá una prueba a `herramientas/prueba_humo.py` que falle sin el arreglo.

## Sacar una versión

- Subí `version` en `.claude-plugin/plugin.json`, que es el único lugar donde está (`neuromapa --version` lo lee de
  ahí), y anotá los cambios en `CHANGELOG.md` bajo ese número. Claude Code usa ese número para saber si hay algo
  nuevo: si no sube, `claude plugin update` puede decir que ya está al día y no traer los cambios.
- `claude plugin tag` crea la etiqueta `neuromapa--v<versión>` y revisa antes que el manifiesto y el marketplace
  coincidan.
- Para un problema de seguridad, no abras un issue: mirá [SECURITY.md](SECURITY.md).
