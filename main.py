#!/usr/bin/env python3
"""
IQ Digits — Menú interactivo
Taller 2 — Representación del Conocimiento y Razonamiento
"""

from logic import (
    parse_positions,
    print_stats,
    solve_iq_digits,
    verify_solution,
    display_solution,
    ROWS,
    COLS,
)


def mostrar_menu() -> None:
    print("\n╔══════════════════════════════════════════╗")
    print("║         IQ Digits — Solucionador         ║")
    print("╠══════════════════════════════════════════╣")
    print("║  1. Modo Puzle (sin piezas fijas)        ║")
    print("║  2. Modo Puzle (con piezas fijas)        ║")
    print("║  3. Modo Restricción (suma de vecinos)   ║")
    print("║  4. Modo Restricción + piezas fijas      ║")
    print("║  5. Ver estadísticas del puzzle          ║")
    print("║  0. Salir                                ║")
    print("╚══════════════════════════════════════════╝")
    print("  Opción: ", end="")


def pedir_posiciones(prompt: str) -> dict | None:
    """Solicita posiciones al usuario con validación y reintento."""
    print(f"\n  {prompt}")
    print("  Formato: fila,columna:valor  (separados por espacios)")
    print(f"  Rangos : fila ∈ [0,{ROWS-1}]  columna ∈ [0,{COLS-1}]  valor ∈ [0,9]")
    print("  Ejemplo: 0,0:5 0,2:3 1,4:7")
    print("  (Enter para omitir): ", end="")

    while True:
        raw = input()
        try:
            return parse_positions(raw)
        except (ValueError, AttributeError) as e:
            print(f"  Error: {e}")
            print("  Ingrese de nuevo (o Enter para omitir): ", end="")


def resolver_y_mostrar(fixed_positions: dict | None,
                       sum_constraints: dict | None) -> None:
    """Llama al solver, verifica y muestra el resultado."""
    print_stats()

    if fixed_positions:
        print(f"\n  Piezas fijas        : {fixed_positions}")
    if sum_constraints:
        print(f"  Restricciones suma  : {sum_constraints}")

    print("\n  Resolviendo con CP-SAT...\n")
    solution = solve_iq_digits(fixed_positions, sum_constraints)

    if solution is None:
        print("  No se encontró solución para las restricciones dadas.")
        return

    ok, msg = verify_solution(solution, fixed_positions, sum_constraints)
    if not ok:
        print(f"  ERROR en verificación: {msg}")
        return

    display_solution(solution, fixed_positions, sum_constraints)
    print(f"\n  Verificación: {msg}\n")


def modo_puzle_libre() -> None:
    print("\n  Modo Puzle — sin restricciones (solución libre)")
    resolver_y_mostrar(None, None)


def modo_puzle_fijo() -> None:
    print("\n  Modo Puzle — con piezas fijas")
    fixed = pedir_posiciones("Ingrese las posiciones fijas:")
    if fixed is None:
        print("  No se ingresaron posiciones. Ejecutando en modo libre.")
    resolver_y_mostrar(fixed, None)


def modo_restriccion() -> None:
    print("\n  Modo Restricción — suma de vecinos ortogonales")
    sums = pedir_posiciones("Ingrese las restricciones de suma (valor = suma objetivo):")
    if sums is None:
        print("  No se ingresaron restricciones. Volviendo al menú.")
        return
    resolver_y_mostrar(None, sums)


def modo_restriccion_fijo() -> None:
    print("\n  Modo Restricción + piezas fijas")
    sums = pedir_posiciones("Ingrese las restricciones de suma (valor = suma objetivo):")
    if sums is None:
        print("  No se ingresaron restricciones de suma. Volviendo al menú.")
        return
    fixed = pedir_posiciones("Ingrese las posiciones fijas (opcional):")
    resolver_y_mostrar(fixed, sums)


def main() -> None:
    OPCIONES = {
        "1": modo_puzle_libre,
        "2": modo_puzle_fijo,
        "3": modo_restriccion,
        "4": modo_restriccion_fijo,
        "5": print_stats,
    }

    while True:
        mostrar_menu()
        opcion = input().strip()

        if opcion == "0":
            print("\n  ¡Hasta luego!\n")
            break
        elif opcion in OPCIONES:
            OPCIONES[opcion]()
        else:
            print("  Opción no válida. Ingrese un número del 0 al 5.")


if __name__ == "__main__":
    main()
