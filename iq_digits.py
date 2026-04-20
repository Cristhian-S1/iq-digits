"""
IQ Digits solver — Problema de Satisfacción de Restricciones (CSP)
resuelto con OR-Tools CP-SAT y NumPy.

Representación del tablero
--------------------------
Nodos en una rejilla 5 filas x 6 columnas.
- Arista horizontal  H(r,c): (r,c)-(r,c+1)   r in [0,4], c in [0,4]  -> 5x5 = 25
- Arista vertical    V(r,c): (r,c)-(r+1,c)   r in [0,3], c in [0,5]  -> 4x6 = 24
Total: 49 aristas.  Cada pieza ocupa un subconjunto disjunto de aristas.
"""

from __future__ import annotations
import numpy as np
from ortools.sat.python import cp_model

# ---------------------------------------------------------------------------
# 1.  Definicion de las piezas (dígitos 0..9) como conjuntos de aristas
# ---------------------------------------------------------------------------
#
# Cada dígito se define en una caja local de 2 columnas x 3 filas (3x2 celdas).
# Aristas horizontales locales:  ('H', r, c)  r in [0..2], c in [0..1]
# Aristas verticales   locales:  ('V', r, c)  r in [0..1], c in [0..2]
#
# El '0' es la excepción: ocupa sólo una celda (1x1) -> mitad del tamaño.

DIGIT_SEGMENTS = {
    0: [('H', 0, 0), ('H', 1, 0), ('V', 0, 0), ('V', 0, 1)],               # celda 1x1
    1: [('V', 0, 1), ('V', 1, 1)],                                          # b,c
    2: [('H', 0, 0), ('V', 0, 1), ('H', 1, 0), ('V', 1, 0), ('H', 2, 0)],   # a,b,g,e,d
    3: [('H', 0, 0), ('V', 0, 1), ('H', 1, 0), ('V', 1, 1), ('H', 2, 0)],   # a,b,g,c,d
    4: [('V', 0, 0), ('H', 1, 0), ('V', 0, 1), ('V', 1, 1)],                # f,g,b,c
    5: [('H', 0, 0), ('V', 0, 0), ('H', 1, 0), ('V', 1, 1), ('H', 2, 0)],   # a,f,g,c,d
    6: [('H', 0, 0), ('V', 0, 0), ('H', 1, 0), ('V', 1, 0), ('V', 1, 1), ('H', 2, 0)],
    7: [('H', 0, 0), ('V', 0, 1), ('V', 1, 1)],                             # a,b,c
    8: [('H', 0, 0), ('V', 0, 0), ('V', 0, 1), ('H', 1, 0),
        ('V', 1, 0), ('V', 1, 1), ('H', 2, 0)],
    9: [('H', 0, 0), ('V', 0, 0), ('V', 0, 1), ('H', 1, 0),
        ('V', 1, 1), ('H', 2, 0)],
}

# Dimensiones del tablero (en aristas)
H_ROWS, H_COLS = 5, 5
V_ROWS, V_COLS = 4, 6
NODES_R, NODES_C = 5, 6

# ---------------------------------------------------------------------------
# 2.  Utilidades numpy: transformar una pieza en matriz y generar orientaciones
# ---------------------------------------------------------------------------

def segments_to_arrays(segs):
    """Convierte una lista de aristas locales en dos matrices booleanas
    (horizontales y verticales) alineadas a una misma rejilla de nodos."""
    hs = [(r, c) for t, r, c in segs if t == 'H']
    vs = [(r, c) for t, r, c in segs if t == 'V']
    all_pts = hs + vs
    # Dimensiones de la caja de nodos necesaria
    if not all_pts:
        return np.zeros((1, 1), bool), np.zeros((1, 1), bool)
    max_hr = max((r for r, _ in hs), default=-1)
    max_hc = max((c for _, c in hs), default=-1)
    max_vr = max((r for r, _ in vs), default=-1)
    max_vc = max((c for _, c in vs), default=-1)
    # nodos: filas = max(max_hr, max_vr+1) + 1 ; cols = max(max_hc+1, max_vc) + 1
    node_rows = max(max_hr, max_vr + 1) + 1
    node_cols = max(max_hc + 1, max_vc) + 1
    H = np.zeros((node_rows, node_cols - 1), bool)       # H(r,c): r in rows, c in cols-1
    V = np.zeros((node_rows - 1, node_cols), bool)       # V(r,c)
    for r, c in hs:
        H[r, c] = True
    for r, c in vs:
        V[r, c] = True
    return H, V


def rotate90(H, V):
    """Rota 90° en sentido horario el par (H, V).
    Bajo rotación horaria, una arista horizontal se convierte en vertical y viceversa.
    Si tenemos nodos (nr, nc), tras rotar tendremos nodos (nc, nr)."""
    # H shape: (nr, nc-1)  ; V shape: (nr-1, nc)
    nr = H.shape[0]
    nc = H.shape[1] + 1
    # Nueva forma: nr' = nc, nc' = nr
    # H_new shape: (nc, nr-1), V_new shape: (nc-1, nr)
    # Mapeo: nodo (r,c) -> (c, nr-1-r)
    H_new = np.zeros((nc, nr - 1), bool)
    V_new = np.zeros((nc - 1, nr), bool)
    # Aristas verticales originales -> horizontales nuevas
    for r in range(V.shape[0]):
        for c in range(V.shape[1]):
            if V[r, c]:
                # nodos (r,c)-(r+1,c) -> (c, nr-1-r)-(c, nr-1-(r+1)) = (c, nr-1-r)-(c, nr-2-r)
                # Es una arista horizontal nueva entre col (nr-2-r) y (nr-1-r) en fila c
                H_new[c, nr - 2 - r] = True
    # Aristas horizontales originales -> verticales nuevas
    for r in range(H.shape[0]):
        for c in range(H.shape[1]):
            if H[r, c]:
                # nodos (r,c)-(r,c+1) -> (c, nr-1-r)-(c+1, nr-1-r)
                V_new[c, nr - 1 - r] = True
    return H_new, V_new


def mirror_h(H, V):
    """Refleja horizontalmente (espejo sobre eje vertical)."""
    H_new = H[:, ::-1].copy()
    V_new = V[:, ::-1].copy()
    return H_new, V_new


def canonical(H, V):
    """Clave canónica para detectar orientaciones duplicadas."""
    return (H.shape, V.shape, H.tobytes(), V.tobytes())


def all_orientations(H, V):
    """Devuelve todas las orientaciones únicas: 4 rotaciones x 2 espejos."""
    seen, out = set(), []
    cur = (H, V)
    for _ in range(4):
        for variant in (cur, mirror_h(*cur)):
            key = canonical(*variant)
            if key not in seen:
                seen.add(key)
                out.append(variant)
        cur = rotate90(*cur)
    return out


# ---------------------------------------------------------------------------
# 3.  Enumeracion de todas las colocaciones válidas de cada pieza
# ---------------------------------------------------------------------------

def enumerate_placements(digit):
    """Para un dígito, devuelve lista de colocaciones. Cada colocación es
    un frozenset de aristas globales (claves ('H',r,c) o ('V',r,c))."""
    H0, V0 = segments_to_arrays(DIGIT_SEGMENTS[digit])
    placements = []
    seen_global = set()
    for H, V in all_orientations(H0, V0):
        hr, hc = H.shape     # H: nodos_filas x (nodos_cols-1)
        vr, vc = V.shape     # V: (nodos_filas-1) x nodos_cols
        node_rows, node_cols = hr, vc
        # Offset (dr, dc) del nodo superior-izq de la pieza dentro del tablero
        for dr in range(NODES_R - node_rows + 1):
            for dc in range(NODES_C - node_cols + 1):
                edges = set()
                ok = True
                # Aristas horizontales locales -> globales
                rs, cs = np.nonzero(H)
                for r, c in zip(rs, cs):
                    gr, gc = r + dr, c + dc
                    if not (0 <= gr < H_ROWS and 0 <= gc < H_COLS):
                        ok = False; break
                    edges.add(('H', int(gr), int(gc)))
                if not ok:
                    continue
                rs, cs = np.nonzero(V)
                for r, c in zip(rs, cs):
                    gr, gc = r + dr, c + dc
                    if not (0 <= gr < V_ROWS and 0 <= gc < V_COLS):
                        ok = False; break
                    edges.add(('V', int(gr), int(gc)))
                if not ok:
                    continue
                key = frozenset(edges)
                if key in seen_global:
                    continue
                seen_global.add(key)
                placements.append(key)
    return placements


# ---------------------------------------------------------------------------
# 4.  Modelo CP-SAT
# ---------------------------------------------------------------------------

def solve(fixed=None, hints=None, cell_hints=None, cover_all=False, verbose=True):
    """
    fixed       : dict {digit: frozenset(edges)}  colocaciones obligatorias (Paso 1).
    hints       : list [(node_r, node_c, value)]  pistas en nodos. El valor es
                  la suma de los dígitos cuyas piezas tocan ese nodo.
    cell_hints  : list [(cell_r, cell_c, value)]  pistas en centros de celda.
                  El valor es la suma de los dígitos cuyas piezas ocupan alguna
                  de las 4 aristas del contorno de esa celda.
    cover_all   : si True, cada arista debe estar cubierta.
    """
    fixed = fixed or {}
    hints = hints or []
    cell_hints = cell_hints or []
    model = cp_model.CpModel()

    # Enumerar placements por dígito
    all_placements = {d: enumerate_placements(d) for d in range(10)}

    # Forzar colocaciones fijas: filtrar la lista al único placement válido
    for d, edges in fixed.items():
        cand = [p for p in all_placements[d] if p == edges]
        if not cand:
            raise ValueError(f"Colocación fija inválida para el dígito {d}")
        all_placements[d] = cand

    # Variables: x[d][i] = 1 si el dígito d se coloca con la orientación i
    x = {d: [model.NewBoolVar(f"x_{d}_{i}") for i in range(len(ps))]
         for d, ps in all_placements.items()}

    # Cada dígito se coloca exactamente una vez
    for d in range(10):
        model.AddExactlyOne(x[d])

    # No solapamiento: para cada arista, suma de placements que la usan <= 1
    edge_users = {}     # edge -> list of (BoolVar, digit)
    for d, ps in all_placements.items():
        for i, edges in enumerate(ps):
            for e in edges:
                edge_users.setdefault(e, []).append((x[d][i], d))

    for e, users in edge_users.items():
        if cover_all:
            model.AddExactlyOne([v for v, _ in users])
        else:
            model.AddAtMostOne([v for v, _ in users])

    # ---- Restricciones de suma (Modo Restricción) ----
    def incident_edges_node(nr, nc):
        res = []
        if 0 <= nr < NODES_R and 0 <= nc - 1 < H_COLS:
            res.append(('H', nr, nc - 1))
        if 0 <= nr < NODES_R and 0 <= nc < H_COLS:
            res.append(('H', nr, nc))
        if 0 <= nr - 1 < V_ROWS and 0 <= nc < V_COLS:
            res.append(('V', nr - 1, nc))
        if 0 <= nr < V_ROWS and 0 <= nc < V_COLS:
            res.append(('V', nr, nc))
        return res

    def contour_edges_cell(cr, cc):
        # Celda (cr, cc) ocupa los nodos (cr,cc), (cr,cc+1), (cr+1,cc), (cr+1,cc+1)
        return [('H', cr, cc), ('H', cr + 1, cc),
                ('V', cr, cc), ('V', cr, cc + 1)]

    def add_sum_constraint(inc_edges, S, tag):
        used = []
        for d in range(10):
            u = model.NewBoolVar(f"used_{d}_{tag}")
            matching = [x[d][i] for i, edges in enumerate(all_placements[d])
                        if any(e in edges for e in inc_edges)]
            if matching:
                model.AddMaxEquality(u, matching)
            else:
                model.Add(u == 0)
            used.append(u)
        model.Add(sum(d * used[d] for d in range(10)) == S)

    for nr, nc, S in hints:
        add_sum_constraint(incident_edges_node(nr, nc), S, f"n{nr}_{nc}")
    for cr, cc, S in cell_hints:
        add_sum_constraint(contour_edges_cell(cr, cc), S, f"c{cr}_{cc}")

    # Resolver
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if verbose:
            print("Sin solución.")
        return None

    # Extraer solución
    result = {}
    for d in range(10):
        for i, var in enumerate(x[d]):
            if solver.Value(var) == 1:
                result[d] = all_placements[d][i]
                break
    if verbose:
        render(result, hints=hints, cell_hints=cell_hints)
    return result


# ---------------------------------------------------------------------------
# 5.  Renderizado ASCII de la solución
# ---------------------------------------------------------------------------

def render(result, hints=None, cell_hints=None):
    """Imprime el tablero de forma legible. Cada arista se marca con el dígito
    que la ocupa (o '-' / '|' si está libre)."""
    em = {}
    for d, edges in result.items():
        for e in edges:
            em[e] = d
    W = NODES_C * 4 - 3
    Hh = NODES_R * 2 - 1
    grid = np.full((Hh, W), ' ', dtype='<U1')
    for r in range(NODES_R):
        for c in range(NODES_C):
            grid[r * 2, c * 4] = '·'
    for r in range(H_ROWS):
        for c in range(H_COLS):
            d = em.get(('H', r, c))
            ch = str(d) if d is not None else '─'
            for k in range(1, 4):
                grid[r * 2, c * 4 + k] = ch
    for r in range(V_ROWS):
        for c in range(V_COLS):
            d = em.get(('V', r, c))
            ch = str(d) if d is not None else '│'
            grid[r * 2 + 1, c * 4] = ch
    # Pistas por nodo: sobrescribir el '·' con el valor (si es un solo dígito)
    if hints:
        for nr, nc, val in hints:
            s = str(val)
            if len(s) == 1:
                grid[nr * 2, nc * 4] = s
    # Pistas por celda: mostrar en la posición central (fila impar, col impar)
    if cell_hints:
        for cr, cc, val in cell_hints:
            s = str(val)
            # Centro de la celda (cr,cc) en el render: fila cr*2+1, col cc*4+2
            if len(s) == 1:
                grid[cr * 2 + 1, cc * 4 + 2] = s
    print('\n'.join(''.join(row) for row in grid))
    print()
    for d, edges in sorted(result.items()):
        print(f"  dígito {d} ({len(edges)} aristas): {sorted(edges)}")


# ---------------------------------------------------------------------------
# 6.  Retos predefinidos
# ---------------------------------------------------------------------------

DEFAULT_CHALLENGE = {
    # Sin piezas fijas, sin pistas: busca cualquier configuración donde los 10
    # dígitos quepan sin solaparse (47 aristas ocupadas, 2 libres del total de 49).
    'fixed': {},
    'hints': [],
    'cover_all': False,
}


# ---------------------------------------------------------------------------
# 7.  main() con menú while-True
# ---------------------------------------------------------------------------

def _read_int(prompt, lo=None, hi=None):
    while True:
        try:
            v = int(input(prompt).strip())
            if lo is not None and v < lo: continue
            if hi is not None and v > hi: continue
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
    """Permite fijar una pieza indicando dígito, orientación (idx) y desplazamiento.
    Lo más práctico: listar placements del dígito y que el usuario elija índice."""
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
    while True:
        print("\n=== IQ Digits Solver (CP-SAT) ===")
        print(" 1) Resolver reto por defecto (sin pistas)")
        print(" 2) Resolver con piezas fijas")
        print(" 3) Resolver con pistas por nodo")
        print(" 4) Resolver con pistas por celda")
        print(" 5) Resolver combinando fijas + pistas")
        print(" 6) Mostrar colocaciones por dígito (cantidad)")
        print(" 7) Mostrar primeras colocaciones de un dígito")
        print(" 0) Salir")
        op = input("Opción: ").strip()
        if op == '0':
            break
        elif op == '1':
            solve(**DEFAULT_CHALLENGE)
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
        else:
            print("Opción inválida.")


if __name__ == '__main__':
    main()
