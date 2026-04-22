"""Punto de entrada: menú CLI e inicio del servidor web."""

from __future__ import annotations
import sys

from solver.core import solve
from solver.placements import enumerate_placements
from api.routes import app


def _read_int(prompt, lo=None, hi=None):
    while True:
        try:
            v = int(input(prompt).strip())
            if lo is not None and v < lo:
                continue
            if hi is not None and v > hi:
                continue
            return v
        except ValueError:
            pass


def _input_hints(prompt_label):
    hints = []
    print(f"Pistas por {prompt_label} (fila col valor). Línea vacía para terminar.")
    while True:
        s = input("  > ").strip()
        if not s:
            break
        try:
            a, b, v = map(int, s.split())
            hints.append((a, b, v))
        except ValueError:
            print("    Formato inválido. Usa: fila col valor")
    return hints


def _input_fixed():
    fixed = {}
    print("Fijar piezas. Línea vacía para terminar.")
    while True:
        s = input("  Dígito a fijar (0-9) o ENTER: ").strip()
        if not s:
            break
        try:
            d = int(s)
            if not 0 <= d <= 9:
                continue
        except ValueError:
            continue
        places = enumerate_placements(d)
        print(f"    {len(places)} colocaciones disponibles para el dígito {d}.")
        idx = _read_int("    Índice (0..N-1): ", 0, len(places) - 1)
        fixed[d] = places[idx]
    return fixed


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5050
        print(f"🚀 IQ Digits API server en http://localhost:{port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        return

    while True:
        print("\n=== IQ Digits Solver (CP-SAT) ===")
        print(" 1) Resolver reto por defecto (sin pistas)")
        print(" 2) Resolver con piezas fijas")
        print(" 3) Resolver con pistas por nodo")
        print(" 4) Resolver con pistas por celda")
        print(" 5) Resolver combinando fijas + pistas")
        print(" 6) Mostrar colocaciones por dígito (cantidad)")
        print(" 7) Mostrar primeras colocaciones de un dígito")
        print(" 8) Iniciar servidor web (API REST)")
        print(" 0) Salir")
        op = input("Opción: ").strip()
        if op == '0':
            break
        elif op == '1':
            solve(cover_all=False)
        elif op == '2':
            solve(fixed=_input_fixed(), cover_all=False)
        elif op == '3':
            solve(hints=_input_hints("nodo"), cover_all=False)
        elif op == '4':
            solve(cell_hints=_input_hints("celda"), cover_all=False)
        elif op == '5':
            f = _input_fixed()
            hn = _input_hints("nodo")
            hc = _input_hints("celda")
            solve(fixed=f, hints=hn, cell_hints=hc, cover_all=False)
        elif op == '6':
            for d in range(10):
                print(f"  dígito {d}: {len(enumerate_placements(d))} colocaciones")
        elif op == '7':
            d = _read_int("  Dígito: ", 0, 9)
            k = _read_int("  ¿Cuántas mostrar? ", 1, 20)
            for i, pl in enumerate(enumerate_placements(d)[:k]):
                print(f"  [{i}] {sorted(pl)}")
        elif op == '8':
            use_custom = input("¿Puerto personalizado? (s/n): ").strip().lower() == 's'
            port = _read_int("Puerto (default 5050): ", 1024, 65535) if use_custom else 5050
            print(f"🚀 Servidor en http://localhost:{port}")
            app.run(host='0.0.0.0', port=port, debug=False)
        else:
            print("Opción inválida.")


if __name__ == '__main__':
    main()
