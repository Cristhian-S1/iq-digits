"""Comandos CLI: cada función ejecuta el flujo completo de su opción."""

from __future__ import annotations

from core.core import solve, render
from core.placements import enumerate_placements
from core.pieces import NODES_R, NODES_C, V_ROWS

# ── helpers privados ──────────────────────────────────────────────────────────

def _read_int(prompt, lo=None, hi=None):
    while True:
        try:
            v = int(input(prompt).strip())
            if lo is not None and v < lo:
                print(f"    Valor mínimo: {lo}")
                continue
            if hi is not None and v > hi:
                print(f"    Valor máximo: {hi}")
                continue
            return v
        except ValueError:
            pass

def _placement_anchor(pl):
    rows = [r for t, r, c in pl] + [r + 1 for t, r, c in pl if t == 'V']
    cols = [c for t, r, c in pl] + [c + 1 for t, r, c in pl if t == 'H']
    return min(rows), min(cols)


def _render_placement_mini(pl):
    rows_used = [r for t, r, c in pl] + [r + 1 for t, r, c in pl if t == 'V']
    cols_used = [c for t, r, c in pl] + [c + 1 for t, r, c in pl if t == 'H']
    min_r, max_r = min(rows_used), max(rows_used)
    min_c, max_c = min(cols_used), max(cols_used)
    nr = max_r - min_r + 1
    nc = max_c - min_c + 1
    W = nc * 4 - 3
    Hh = nr * 2 - 1
    grid = [[' '] * W for _ in range(Hh)]
    for r in range(nr):
        for c in range(nc):
            grid[r * 2][c * 4] = '·'
    for t, r, c in pl:
        lr, lc = r - min_r, c - min_c
        if t == 'H':
            for k in range(1, 4):
                grid[lr * 2][lc * 4 + k] = '─'
        else:
            grid[lr * 2 + 1][lc * 4] = '│'
    return '\n'.join(''.join(row) for row in grid)


def _collect_board_layout():
    sep = "=" * 62
    print(f"\n{sep}")
    print("  REFERENCIA DEL TABLERO IQ DIGITS")
    print(sep)

    print("\n  NODOS (fila, col) — para posición de dígitos:\n")
    hdr = "         "
    for c in range(NODES_C):
        hdr += f"  c={c}  "
    print(hdr)
    for r in range(NODES_R):
        row_str = f"  f={r}   "
        for c in range(NODES_C):
            row_str += f"({r},{c})"
            if c < NODES_C - 1:
                row_str += "──"
        print(row_str)
        if r < V_ROWS:
            v_str = "         "
            for _ in range(NODES_C):
                v_str += "  │   "
            print(v_str)

    print(f"\n  CELDAS [fila, col] — para pistas por celda (filas 0-{NODES_R-2}, cols 0-{NODES_C-2}):\n")
    cell_hdr = "         "
    for c in range(NODES_C - 1):
        cell_hdr += f"  c={c}  "
    print(cell_hdr)
    for r in range(NODES_R - 1):
        cell_row = f"  f={r}   "
        for c in range(NODES_C - 1):
            cell_row += f"[{r},{c}]  "
        print(cell_row)

    print(f"\n  Al colocar un dígito usa la posición del nodo SUPERIOR-IZQUIERDO.")
    print(sep)


def _collect_fixed():
    fixed = {}
    _collect_board_layout()
    print("\n  Fijar dígitos en el tablero. ENTER para terminar.")

    while True:
        print()
        if fixed:
            print("  Estado actual:")
            render(fixed)
            print()

        s = input("  Dígito a fijar (0-9) o ENTER para terminar: ").strip()
        if not s:
            break
        try:
            d = int(s)
            if not 0 <= d <= 9:
                print("  Dígito fuera de rango (0-9).")
                continue
        except ValueError:
            print("  Entrada inválida.")
            continue

        all_pl = enumerate_placements(d)
        print(f"\n  El dígito {d} tiene {len(all_pl)} colocaciones posibles en el tablero.")
        print(f"  Introduce la posición del nodo SUPERIOR-IZQUIERDO del dígito:")
        dr = _read_int(f"    Fila   (0-{NODES_R - 1}): ", 0, NODES_R - 1)
        dc = _read_int(f"    Columna (0-{NODES_C - 1}): ", 0, NODES_C - 1)

        matches = [(i, pl) for i, pl in enumerate(all_pl)
                   if _placement_anchor(pl) == (dr, dc)]

        if not matches:
            print(f"\n  No hay colocaciones del dígito {d} con nodo superior-izquierdo en ({dr},{dc}).")
            print("  Prueba otra posición.")
            continue

        if len(matches) == 1:
            fixed[d] = matches[0][1]
            print(f"  Única orientación posible. Dígito {d} fijado en ({dr},{dc}).")
        else:
            print(f"\n  {len(matches)} orientaciones posibles en ({dr},{dc}):\n")
            for j, (_, pl) in enumerate(matches):
                print(f"    [{j + 1}]")
                for line in _render_placement_mini(pl).split('\n'):
                    print(f"      {line}")
                print()
            choice = _read_int(f"  Elige orientación (1-{len(matches)}): ", 1, len(matches))
            fixed[d] = matches[choice - 1][1]
            print(f"  Dígito {d} fijado en ({dr},{dc}), orientación {choice}.")

    return fixed


def _collect_cell_hints():
    _collect_board_layout()
    hints = []
    print("\n  Pistas de suma por CELDA.")
    print("  La suma de los dígitos que bordean esa celda = valor dado.")
    print(f"  Formato: fila col suma   (ej: '1 2 10'). Línea vacía para terminar.")
    while True:
        s = input("  > ").strip()
        if not s:
            break
        try:
            a, b, v = map(int, s.split())
        except ValueError:
            print("  Formato inválido. Usa: fila col suma")
            continue
        if not (0 <= a < NODES_R - 1 and 0 <= b < NODES_C - 1):
            print(f"  Celda inválida. Filas 0-{NODES_R - 2}, columnas 0-{NODES_C - 2}.")
            continue
        hints.append((a, b, v))
        print(f"  Pista añadida: celda ({a},{b}) = {v}")
    return hints


# ── comandos públicos (flujo completo) ────────────────────────────────────────

def cmd_solve_fixed():
    fixed = _collect_fixed()
    print("depuracion",fixed)
    solve(fixed=fixed, cover_all=False)


def cmd_solve_cell_hints():
    cell_hints = _collect_cell_hints()
    solve(cell_hints=cell_hints, cover_all=False)


def cmd_solve_combined():
    fixed = _collect_fixed()
    cell_hints = _collect_cell_hints()
    solve(fixed=fixed, cell_hints=cell_hints, cover_all=False)

def cmd_show_board():
    _collect_board_layout()
