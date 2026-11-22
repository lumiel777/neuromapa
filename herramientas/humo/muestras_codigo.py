MUESTRAS = {
    "Tienda.java": """package juego;

@Entity
public class Tienda<T extends Item> implements Vende {
    private final Map<String, Integer> precios = new HashMap<>() {{ put("a", 1); }};

    @Override
    public synchronized <R> List<R> vender(T item, int cantidad) throws Exception {
        Runnable r = () -> { System.out.println("{"); };
        var anonimo = new Comparator<T>() {
            public int compare(T a, T b) { return 0; }
        };
        return List.of();
    }

    default void abrir() {
    }

    static {
        System.out.println("bloque estático");
    }

    record Pedido(int id) {
        Pedido {
        }
    }

    enum Estado { ABIERTA, CERRADA }

    public @interface Marca {
    }
}
""",
    "tienda.ts": """import { z } from "zod";

export interface Item { id: number; nombre: string }
type Mapa = { [clave: string]: number };
enum Estado { Abierta, Cerrada }

export class Tienda<T extends Item> {
  private precios = new Map<string, number>();
  constructor(private nombre: string) {}
  async vender(item: T, cantidad = 1): Promise<{ ok: boolean }> {
    const limpio = item.nombre.replace(/[{}`]/g, "");
    return { ok: limpio.length > 0 };
  }
  get total(): number {
    return this.precios.size;
  }
}

export function Boton({ texto, alClic }: { texto: string; alClic: () => void }) {
  return <button onClick={() => alClic()}>{texto} {"}"}</button>;
}

export const sumar = (a: number, b = 2): number => {
  return a + b;
};

const lista = [1, 2].map((x) => {
  return x * 2;
});

export default async function Pagina(): Promise<JSX.Element> {
  const plantilla = `hola ${"{"} mundo`;
  return <div>{plantilla}</div>;
}
""",
    "Tienda.kt": """package juego

data class Item(val id: Int, val nombre: String)

sealed class Resultado {
    object Bien : Resultado()
}

class Tienda(private val nombre: String) : Vende {
    private val precios = mutableMapOf<String, Int>()

    init {
        println("abrió ${nombre}")
    }

    override fun vender(item: Item, cantidad: Int = 1): Resultado {
        precios.forEach { (k, v) -> println("$k=$v {") }
        if (cantidad > 0) {
            return Resultado.Bien
        }
        return Resultado.Bien
    }

    fun doble(x: Int) = x * 2

    companion object {
        fun crear(): Tienda {
            return Tienda(\"\"\"una { tienda\"\"\")
        }
    }
}

fun <T> List<T>.primero(): T {
    return this[0]
}

interface Vende {
    fun vender(item: Item, cantidad: Int): Resultado
}
""",
    "tienda.go": """package tienda

import "fmt"

type Item struct {
	ID     int
	Nombre string `json:"nombre{"`
}

type Vende interface {
	Vender(item Item) error
}

type Tienda struct {
	precios map[string]int
}

func Nueva(nombre string) *Tienda {
	return &Tienda{precios: map[string]int{}}
}

func (t *Tienda) Vender(item Item) error {
	if item.ID == 0 {
		return fmt.Errorf("sin id: %s {", item.Nombre)
	}
	go func() {
		fmt.Println("vendido")
	}()
	for k, v := range t.precios {
		fmt.Println(k, v)
	}
	return nil
}

func (Tienda) Nombre() string { return "tienda" }

func Mayor[T int | float64](a, b T) T {
	if a > b {
		return a
	}
	return b
}
""",
    "tienda.rs": """use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct Item {
    pub id: u32,
}

pub enum Estado {
    Abierta,
    Cerrada { desde: u64 },
}

pub trait Vende {
    fn vender(&mut self, item: Item) -> Result<(), String>;
}

pub struct Tienda<'a> {
    nombre: &'a str,
    precios: HashMap<String, u32>,
}

impl<'a> Tienda<'a> {
    pub fn nueva(nombre: &'a str) -> Self {
        let texto = r#"un { raro "#;
        let c = '{';
        Tienda { nombre, precios: HashMap::new() }
    }
}

impl<'a> Vende for Tienda<'a> {
    fn vender(&mut self, item: Item) -> Result<(), String> {
        match item.id {
            0 => { return Err("sin id {".into()); }
            _ => {}
        }
        let doble = |x: u32| { x * 2 };
        Ok(())
    }
}

mod pruebas {
    fn prueba_vender() {
        assert!(true);
    }
}
""",
    "tienda.php": """<?php
namespace Juego;

interface Vende {
    public function vender(Item $item): bool;
}

trait ConPrecio {
    public function precio(): int { return 1; }
}

final class Tienda implements Vende {
    use ConPrecio;

    public function __construct(private string $nombre) {
        $texto = "una { llave";
        $otro = 'otra } llave';
        # un comentario con {
    }

    public function vender(Item $item): bool {
        $nota = <<<EOT
        texto con { llaves }
        EOT;
        $anonima = function ($x) { return $x; };
        $clase = new class { public function hola() { return 1; } };
        return true;
    }

    public static function &crear(): self {
        return new self("x");
    }
}

function ayudante(array $a): int {
    return count($a);
}

enum Estado: string {
    case Abierta = 'a';
}
""",
}

ESPERADOS = {
    "Tienda.java": [(4, 32, "clase", "Tienda", ""), (8, 14, "metodo", "vender", "Tienda"),
                    (11, 11, "funcion", "compare", "vender"), (16, 17, "metodo", "abrir", "Tienda"),
                    (23, 26, "clase", "Pedido", "Tienda"), (28, 28, "clase", "Estado", "Tienda"),
                    (30, 31, "clase", "Marca", "Tienda")],
    "tienda.ts": [(3, 3, "clase", "Item", ""), (4, 4, "clase", "Mapa", ""), (5, 5, "clase", "Estado", ""),
                  (7, 17, "clase", "Tienda", ""), (9, 9, "metodo", "constructor", "Tienda"),
                  (10, 13, "metodo", "vender", "Tienda"), (14, 16, "metodo", "total", "Tienda"),
                  (19, 21, "funcion", "Boton", ""), (23, 25, "funcion", "sumar", ""),
                  (31, 34, "funcion", "Pagina", "")],
    "Tienda.kt": [(5, 7, "clase", "Resultado", ""), (9, 31, "clase", "Tienda", ""),
                  (16, 22, "metodo", "vender", "Tienda"), (26, 30, "clase", "Companion", "Tienda"),
                  (27, 29, "metodo", "crear", "Companion"), (33, 35, "funcion", "primero", ""),
                  (37, 39, "clase", "Vende", "")],
    "tienda.go": [(5, 8, "clase", "Item", ""), (10, 12, "clase", "Vende", ""), (14, 16, "clase", "Tienda", ""),
                  (18, 20, "funcion", "Nueva", ""), (22, 33, "metodo", "Tienda.Vender", ""),
                  (35, 35, "metodo", "Tienda.Nombre", ""), (37, 42, "funcion", "Mayor", "")],
    "tienda.rs": [(4, 6, "clase", "Item", ""), (8, 11, "clase", "Estado", ""), (13, 15, "clase", "Vende", ""),
                  (17, 20, "clase", "Tienda", ""), (22, 28, "clase", "Tienda<'a>", ""),
                  (23, 27, "metodo", "nueva", "Tienda<'a>"), (30, 39, "clase", "Vende for Tienda<'a>", ""),
                  (31, 38, "metodo", "vender", "Vende for Tienda<'a>"), (41, 45, "clase", "pruebas", ""),
                  (42, 44, "metodo", "prueba_vender", "pruebas")],
    "tienda.php": [(4, 6, "clase", "Vende", ""), (8, 10, "clase", "ConPrecio", ""),
                   (9, 9, "metodo", "precio", "ConPrecio"), (12, 33, "clase", "Tienda", ""),
                   (15, 19, "metodo", "__construct", "Tienda"), (21, 28, "metodo", "vender", "Tienda"),
                   (26, 26, "funcion", "hola", "vender"), (30, 32, "metodo", "crear", "Tienda"),
                   (35, 37, "funcion", "ayudante", ""), (39, 41, "clase", "Estado", "")],
}
