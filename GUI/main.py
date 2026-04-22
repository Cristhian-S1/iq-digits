"""Punto de entrada: despacha opciones del menú al comando correspondiente."""

from __future__ import annotations
import sys

from api.routes import app
from cli.menu import (
    cmd_solve_fixed,
    cmd_solve_cell_hints,
    cmd_solve_combined,
    cmd_show_board,
    cmd_start_server,
)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5050
        print(f"IQ Digits API server en http://localhost:{port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        return

    while True:
        print("\n=== IQ Digits Solver (CP-SAT) ===")
        print("  1) Resolver con piezas fijas")
        print("  2) Resolver con pistas por celda")
        print("  3) Resolver combinando fijas + pistas por celda")
        print("  4) Mostrar tablero (referencia de posiciones)")
        print("  5) Iniciar servidor web (API REST)")
        print("  0) Salir")
        op = input("Opción: ").strip()

        if op == '0':
            break
        elif op == '1':
            cmd_solve_fixed()
        elif op == '2':
            cmd_solve_cell_hints()
        elif op == '3':
            cmd_solve_combined()
        elif op == '4':
            cmd_show_board()
        elif op == '5':
            cmd_start_server(app)
        else:
            print("Opción inválida.")


if __name__ == '__main__':
    main()
