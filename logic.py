"""
IQ Digits — Lógica del solucionador
Taller 2 — Representación del Conocimiento y Razonamiento

=======================================================================
Especificación CSP
=======================================================================

El tablero es una cuadrícula de 2 filas × 5 columnas = 10 posiciones.
Cada posición aloja exactamente un dígito LCD (0-9).

Tablero físico
--------------
  H[i][j] — aristas horizontales : 5 filas × 5 cols = 25 aristas
  V[i][j] — aristas verticales   : 4 filas × 6 cols = 24 aristas
  Total                          : 49 aristas = Σ segmentos de los 10 dígitos

Variables
---------
  board[r][c]   r ∈ {0,1},  c ∈ {0,1,2,3,4}

Dominios
--------
  D(board[r][c]) = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}

Restricciones
-------------
  1. AllDifferent — cada dígito 0-9 aparece exactamente una vez.
  2. (Modo Puzle) Posiciones fijas: board[r][c] = d
  3. (Modo Restricción) Suma de vecinos ortogonales = target[r][c]

=======================================================================
Funciones NumPy utilizadas
=======================================================================
  np.array()      — crear matrices de patrones y resultados
  np.zeros()      — inicializar matrices H y V
  .astype(bool)   — convertir a booleano para máscaras
  .flatten()      — aplanar el array 2-D de variables CP-SAT
  .sum(axis=1)    — contar segmentos activos por dígito
  .tolist()       — convertir a lista Python para CP-SAT

=======================================================================
Métodos CP-SAT utilizados
=======================================================================
  CpModel.new_int_var()       — variable entera con dominio acotado
  CpModel.add_all_different() — restricción AllDifferent global
  CpModel.add()               — restricciones de igualdad lineal
  CpSolver.solve()            — búsqueda CDCL + propagación
  CpSolver.value()            — obtener valor de variable en la solución
  cp_model.OPTIMAL / FEASIBLE — estados de éxito del solver
"""

import numpy as np
from ortools.sat.python import cp_model

# ── Dimensiones del tablero ───────────────────────────────────────────────────
ROWS = 2
COLS = 5

# ── Índices de los 7 segmentos LCD ───────────────────────────────────────────
SEG_TOP, SEG_MID, SEG_BOT, SEG_TL, SEG_TR, SEG_BL, SEG_BR = range(7)

# ── Patrones de segmentos para los dígitos 0–9 ───────────────────────────────
# Columnas: [TOP, MID, BOT, TL, TR, BL, BR]
SEGMENT_PATTERNS = np.array([
    #TOP MID BOT  TL  TR  BL  BR
    [ 1,  0,  1,   1,  1,  1,  1],  # 0
    [ 0,  0,  0,   0,  1,  0,  1],  # 1
    [ 1,  1,  1,   0,  1,  1,  0],  # 2
    [ 1,  1,  1,   0,  1,  0,  1],  # 3
    [ 0,  1,  0,   1,  1,  0,  1],  # 4
    [ 1,  1,  1,   1,  0,  0,  1],  # 5
    [ 1,  1,  1,   1,  0,  1,  1],  # 6
    [ 1,  0,  0,   0,  1,  0,  1],  # 7
    [ 1,  1,  1,   1,  1,  1,  1],  # 8
    [ 1,  1,  1,   1,  1,  0,  1],  # 9
], dtype=np.int8)


# ── Estadísticas con NumPy ────────────────────────────────────────────────────

def segment_stats() -> dict:
    """Calcula estadísticas de segmentos usando operaciones NumPy vectorizadas."""
    S = SEGMENT_PATTERNS
    seg_counts = S.sum(axis=1)
    cooccurrence = S @ S.T  # (10,7) × (7,10) → (10,10)
    return {
        "seg_por_digito"  : {d: int(seg_counts[d]) for d in range(10)},
        "total_segmentos" : int(seg_counts.sum()),
        "aristas_H"       : 5 * 5,
        "aristas_V"       : 4 * 6,
        "total_aristas"   : 5 * 5 + 4 * 6,
        "cooccurrence"    : cooccurrence,
    }


# ── Construcción de las matrices de aristas ───────────────────────────────────

def build_edge_arrays(board: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Construye H (5×5) y V (4×6) a partir de la solución del tablero.

    Cada posición (r, c) tiene sus propios segmentos (no compartidos):
      H[2r   ][c]   ← segmento superior
      H[2r+1 ][c]   ← segmento medio
      H[2r+2 ][c]   ← segmento inferior
      V[2r   ][c]   ← arriba-izquierda
      V[2r   ][c+1] ← arriba-derecha
      V[2r+1 ][c]   ← abajo-izquierda
      V[2r+1 ][c+1] ← abajo-derecha
    """
    H = np.zeros((5, 5), dtype=np.int8)
    V = np.zeros((4, 6), dtype=np.int8)

    for r in range(ROWS):
        for c in range(COLS):
            seg = SEGMENT_PATTERNS[int(board[r, c])]
            H[2*r,     c    ] = seg[SEG_TOP]
            H[2*r + 1, c    ] = seg[SEG_MID]
            H[2*r + 2, c    ] = seg[SEG_BOT]
            V[2*r,     c    ] = seg[SEG_TL]
            V[2*r,     c + 1] = seg[SEG_TR]
            V[2*r + 1, c    ] = seg[SEG_BL]
            V[2*r + 1, c + 1] = seg[SEG_BR]

    return H, V


# ── Verificación ──────────────────────────────────────────────────────────────

def verify_solution(board: np.ndarray,
                    fixed: dict | None = None,
                    sums: dict | None = None) -> tuple[bool, str]:
    """Verifica AllDifferent, posiciones fijas y restricciones de suma."""
    flat = board.flatten().tolist()
    if sorted(flat) != list(range(10)):
        return False, f"Dígitos incorrectos: {flat}"

    if fixed:
        for (r, c), d in fixed.items():
            if int(board[r, c]) != d:
                return False, f"Posición fija incumplida: ({r},{c}) debe ser {d}"

    if sums:
        for (r, c), target in sums.items():
            neighbors = [
                int(board[r + dr, c + dc])
                for dr, dc in ((-1,0),(1,0),(0,-1),(0,1))
                if 0 <= r + dr < ROWS and 0 <= c + dc < COLS
            ]
            if sum(neighbors) != target:
                return False, (f"Suma de vecinos en ({r},{c}): "
                               f"{sum(neighbors)} ≠ {target}")

    return True, "Solución válida"


# ── Solver CP-SAT ─────────────────────────────────────────────────────────────

def solve_iq_digits(
    fixed_positions: dict | None = None,
    sum_constraints: dict | None = None,
) -> np.ndarray | None:
    """
    Resuelve IQ Digits usando CP-SAT de OR-Tools.

    Parámetros
    ----------
    fixed_positions : {(fila, col): dígito}
        Piezas pre-colocadas (Modo Puzle).
    sum_constraints : {(fila, col): suma_objetivo}
        La suma de los dígitos ortogonalmente vecinos debe igualar
        suma_objetivo (Modo Restricción).

    Estrategia de solución
    ----------------------
    CP-SAT aplica propagación de restricciones (arc-consistency)
    combinada con búsqueda CDCL (Conflict-Driven Clause Learning).

    Retorna
    -------
    np.ndarray de forma (2, 5) con la solución, o None si es infactible.
    """
    model  = cp_model.CpModel()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0

    board_vars = np.array([
        [model.new_int_var(0, 9, f"board_{r}_{c}") for c in range(COLS)]
        for r in range(ROWS)
    ])

    # Restricción 1 — AllDifferent
    model.add_all_different(board_vars.flatten().tolist())

    # Restricción 2 — Modo Puzle: posiciones fijas
    if fixed_positions:
        for (r, c), digit in fixed_positions.items():
            model.add(board_vars[r, c] == digit)

    # Restricción 3 — Modo Restricción: suma de vecinos = objetivo
    if sum_constraints:
        for (r, c), target in sum_constraints.items():
            neighbors = [
                board_vars[r + dr, c + dc]
                for dr, dc in ((-1,0),(1,0),(0,-1),(0,1))
                if 0 <= r + dr < ROWS and 0 <= c + dc < COLS
            ]
            model.add(sum(neighbors) == target)

    status = solver.solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return np.array([
            [solver.value(board_vars[r, c]) for c in range(COLS)]
            for r in range(ROWS)
        ])
    return None


# ── Visualización LCD ─────────────────────────────────────────────────────────

def display_solution(board: np.ndarray,
                     fixed: dict | None = None,
                     sums: dict | None = None) -> None:
    """
    Muestra el tablero en representación LCD de 7 segmentos (ASCII art).
    Las posiciones fijas se marcan con [d]; las de suma con (t→d).
    """
    H, V = build_edge_arrays(board)
    fixed = fixed or {}
    sums  = sums  or {}

    sep = "═" * 58
    print(f"\n{sep}")
    print("  IQ Digits — Solución")
    print(sep)

    for r in range(ROWS):
        line = "  "
        for c in range(COLS):
            line += f" {'_' if H[2*r, c] else ' '} "
        print(line)

        line = "  "
        for c in range(COLS):
            left  = "|" if V[2*r,     c    ] else " "
            mid   = "_" if H[2*r + 1, c    ] else " "
            right = "|" if V[2*r,     c + 1] else " "
            line += f"{left}{mid}{right}"
        print(line)

        line = "  "
        for c in range(COLS):
            left  = "|" if V[2*r + 1, c    ] else " "
            bot   = "_" if H[2*r + 2, c    ] else " "
            right = "|" if V[2*r + 1, c + 1] else " "
            line += f"{left}{bot}{right}"
        print(line)

        if r < ROWS - 1:
            print()

    print(f"\n{sep}")
    print("  Disposición numérica del tablero:")

    for r in range(ROWS):
        row_str = f"    Fila {r}: "
        for c in range(COLS):
            d = int(board[r, c])
            if (r, c) in fixed:
                row_str += f"[{d}] "
            elif (r, c) in sums:
                row_str += f"({sums[(r,c)]}→{d}) "
            else:
                row_str += f" {d}  "
        print(row_str)

    print(f"\n  Leyenda:  [d] = posicion fija   (t→d) = restriccion de suma")

    print(f"\n  Matriz H — aristas horizontales (5×5):")
    for i in range(5):
        print(f"    H[{i}] = {H[i].tolist()}")

    print(f"\n  Matriz V — aristas verticales (4×6):")
    for i in range(4):
        print(f"    V[{i}] = {V[i].tolist()}")

    print(sep)


def print_stats() -> None:
    """Imprime estadísticas del puzzle usando NumPy."""
    stats = segment_stats()
    print("\n── Estadísticas del puzzle ──────────────────────────────────")
    print(f"  Aristas horizontales H : 5×5 = {stats['aristas_H']}")
    print(f"  Aristas verticales   V : 4×6 = {stats['aristas_V']}")
    print(f"  Total de aristas       : {stats['total_aristas']}")
    print(f"  Total de segmentos     : {stats['total_segmentos']}")
    print(f"  Segmentos por dígito   : {stats['seg_por_digito']}")
    print("─────────────────────────────────────────────────────────────")


# ── Helpers de entrada ────────────────────────────────────────────────────────

def parse_positions(raw: str) -> dict | None:
    """
    Convierte una cadena de posiciones 'f,c:v f,c:v ...' en {(f, c): v}.
    Retorna None si la cadena está vacía, o lanza ValueError si el formato
    es incorrecto.

    Formato: fila,columna:valor  (separados por espacios)
    Ejemplo: '0,0:5 0,2:3 1,4:7'
    """
    raw = raw.strip()
    if not raw:
        return None
    result = {}
    for token in raw.split():
        pos, val = token.split(":")
        r, c = map(int, pos.split(","))
        if not (0 <= r < ROWS):
            raise ValueError(f"Fila {r} fuera de rango [0, {ROWS-1}]")
        if not (0 <= c < COLS):
            raise ValueError(f"Columna {c} fuera de rango [0, {COLS-1}]")
        v = int(val)
        if not (0 <= v <= 9):
            raise ValueError(f"Valor {v} fuera de rango [0, 9]")
        result[(r, c)] = v
    return result or None
