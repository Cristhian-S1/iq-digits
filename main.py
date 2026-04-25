"""
IQ Digits Solver — OR-Tools CP-SAT + NumPy
Tablero: 4×5 celdas  ->  25 aristas H (5×5) + 24 aristas V (4×6) = 49 aristas
10 dígitos (0-9), el '0' es cuadrado 1×1 (4 aristas); el resto 7 segmentos
Total de segmentos: 4+2+5+5+4+5+6+3+7+6 = 47  (quedan 2 aristas libres)
"""
import numpy as np
from ortools.sat.python import cp_model

# ─── Plantillas en grilla unificada ───────────────────────────────────────────
# (par, impar) = arista H; (impar, par) = arista V; (par, par) = esquina
D = {
    0: np.array([[0,1,0],[1,0,1],[0,1,0]]),                                       # cuadrado 1x1
    1: np.array([[0,0,0],[0,0,1],[0,0,0],[0,0,1],[0,0,0]]),                      # b,c
    2: np.array([[0,1,0],[0,0,1],[0,1,0],[1,0,0],[0,1,0]]),                      # a,b,g,e,d
    3: np.array([[0,1,0],[0,0,1],[0,1,0],[0,0,1],[0,1,0]]),                      # a,b,g,c,d
    4: np.array([[0,0,0],[1,0,1],[0,1,0],[0,0,1],[0,0,0]]),                      # f,b,g,c
    5: np.array([[0,1,0],[1,0,0],[0,1,0],[0,0,1],[0,1,0]]),                      # a,f,g,c,d
    6: np.array([[0,1,0],[1,0,0],[0,1,0],[1,0,1],[0,1,0]]),                      # a,f,g,e,c,d
    7: np.array([[0,1,0],[0,0,1],[0,0,0],[0,0,1],[0,0,0]]),                      # a,b,c
    8: np.array([[0,1,0],[1,0,1],[0,1,0],[1,0,1],[0,1,0]]),                      # todos
    9: np.array([[0,1,0],[1,0,1],[0,1,0],[0,0,1],[0,1,0]]),                      # a,f,b,g,c,d
}

GR, GC = 9, 11     # grilla unificada (2*4+1, 2*5+1)
HN, VN = 25, 24    # aristas horizontales y verticales
TOTAL  = HN + VN

def e_idx(i, j):
    """Posición (i,j) de la grilla unificada -> índice lineal de arista."""
    return (i//2)*5 + j//2 if i % 2 == 0 else HN + (i//2)*6 + j//2

def orientations(m):
    """8 orientaciones: 4 rotaciones × 2 reflejos (0-3 sin flip, 4-7 con flip)."""
    return [np.rot90(np.fliplr(m) if i >= 4 else m, i % 4) for i in range(8)]

def build_placements():
    """digit -> list[(orient_idx, grid_r, grid_c, edges_tuple)]."""
    res = {}
    for d in range(10):
        lst = []
        for oi, m in enumerate(orientations(D[d])):
            h, w = m.shape
            ys, xs = np.where(m == 1)                                             # posiciones de segmentos
            for r in range(0, GR - h + 1, 2):                                     # solo anclas en esquinas
                for c in range(0, GC - w + 1, 2):
                    lst.append((oi, r, c,
                                tuple(e_idx(r+y, c+x) for y, x in zip(ys, xs))))
        res[d] = lst
    return res

# ─── Solver ────────────────────────────────────────────────────────────────────
def solve(fixed=None, hints=None):
    fixed, hints = fixed or [], hints or []
    P = build_placements()
    m = cp_model.CpModel()

    # Variables: x[d][i] = 1 si se usa la i-ésima colocación del dígito d
    x = {d: [m.NewBoolVar(f'x{d}_{i}') for i in range(len(P[d]))] for d in range(10)}

    # Cada dígito aparece exactamente una vez
    for d in range(10):
        m.AddExactlyOne(x[d])

    # Cobertura por arista
    covers = [[] for _ in range(TOTAL)]
    for d in range(10):
        for i, (_, _, _, edges) in enumerate(P[d]):
            for e in edges:
                covers[e].append((d, x[d][i]))

    # No-solapamiento + valor por arista (0 si vacía; también 0 si es el dígito 0)
    val = []
    for e in range(TOTAL):
        v = m.NewIntVar(0, 9, f'v{e}')
        if covers[e]:
            m.Add(sum(b for _, b in covers[e]) <= 1)
            m.Add(v == sum(d * b for d, b in covers[e]))
        else:
            m.Add(v == 0)
        val.append(v)

    # Piezas fijas
    for d, o, r, c in fixed:
        hit = False
        for i, (oi, rr, cc, _) in enumerate(P[d]):
            if oi == o and rr == r and cc == c:
                m.Add(x[d][i] == 1); hit = True; break
        if not hit:
            print(f"  ⚠ Sin placement válido: dígito={d}, disp={o}, pos=({r//2},{c//2})")

    # Pistas por celda: suma de las 4 aristas vecinas == target
    for hr, hc, tgt in hints:
        top = hr*5 + hc
        bot = (hr+1)*5 + hc
        lft = HN + hr*6 + hc
        rgt = HN + hr*6 + (hc+1)
        m.Add(val[top] + val[bot] + val[lft] + val[rgt] == tgt)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 8
    status = solver.Solve(m)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        display_solution(solver, x, P)
    else:
        print("\n❌ No hay solución para esta configuración.")

# ─── Visualización ─────────────────────────────────────────────────────────────
def display_solution(solver, x, P):
    H = np.full((5, 5), -1, dtype=int)
    V = np.full((4, 6), -1, dtype=int)
    for d in range(10):
        for i, (_, _, _, edges) in enumerate(P[d]):
            if solver.Value(x[d][i]):
                for e in edges:
                    if e < HN: H[e//5, e%5] = d
                    else:      V[(e-HN)//6, (e-HN)%6] = d
    print("\n═══ Aristas horizontales (5×5)  -1 = vacía ═══")
    print(H)
    print("\n═══ Aristas verticales (4×6)    -1 = vacía ═══")
    print(V)
    print("\n═══ Tablero (· = arista vacía) ═══")
    g = np.full((GR, GC), ' ', dtype='<U2')
    g[::2, ::2]   = '+'
    g[::2, 1::2]  = np.where(H >= 0, H.astype(str), '·')
    g[1::2, ::2]  = np.where(V >= 0, V.astype(str), '·')
    print('\n'.join(' '.join(row) for row in g))

def show_reference():
    print("""
Matriz de ARISTAS (ingresá fila f y columna c del corner superior-izquierdo de la pieza):
         c=0    c=1    c=2    c=3    c=4    c=5
  f=0   (0,0)──(0,1)──(0,2)──(0,3)──(0,4)──(0,5)
           │     │     │     │     │     │
  f=1   (1,0)──(1,1)──(1,2)──(1,3)──(1,4)──(1,5)
           │     │     │     │     │     │
  f=2   (2,0)──(2,1)──(2,2)──(2,3)──(2,4)──(2,5)
           │     │     │     │     │     │
  f=3   (3,0)──(3,1)──(3,2)──(3,3)──(3,4)──(3,5)
           │     │     │     │     │     │
  f=4   (4,0)──(4,1)──(4,2)──(4,3)──(4,4)──(4,5)

Matriz de CELDAS (para pistas de suma):
         c=0    c=1    c=2    c=3    c=4
  f=0   [0,0]  [0,1]  [0,2]  [0,3]  [0,4]
  f=1   [1,0]  [1,1]  [1,2]  [1,3]  [1,4]
  f=2   [2,0]  [2,1]  [2,2]  [2,3]  [2,4]
  f=3   [3,0]  [3,1]  [3,2]  [3,3]  [3,4]

Disposiciones (4 rotaciones × 2 reflejos):
  0 = original            4 = reflejo + original
  1 = rot 90° CCW         5 = reflejo + rot 90°
  2 = rot 180°            6 = reflejo + rot 180°
  3 = rot 270° CCW        7 = reflejo + rot 270°
""")

# ─── Entrada de usuario ────────────────────────────────────────────────────────
def input_fixed():
    fx = []
    print("\n── Piezas fijas (Enter vacío para terminar) ──")
    while True:
        s = input("Dígito (0-9): ").strip()
        if not s: break
        d = int(s)
        o = int(input("  Disposición (0-7): "))
        r, c = map(int, input("  Fila columna: ").split())
        fx.append((d, o, 2*r, 2*c))
    return fx

def input_hints():
    hs = []
    print("\n── Pistas por celda (Enter vacío para terminar) ──")
    while True:
        s = input("Fila columna suma: ").strip()
        if not s: break
        a, b, t = map(int, s.split())
        hs.append((a, b, t))
    return hs

# ─── Main ──────────────────────────────────────────────────────────────────────
while True:
    print("\n" + "═"*45)
    print("         IQ Digits — Solver CP-SAT")
    print("═"*45)
    print("1) Resolver con piezas fijas")
    print("2) Resolver con pistas por celda")
    print("3) Resolver combinando fijas + pistas")
    print("4) Mostrar tablero (referencia de posiciones)")
    print("5) Salir")
    opt = input("Opción: ").strip()
    if opt == '5': break
    if   opt == '4': show_reference()
    elif opt == '1': show_reference(); solve(fixed=input_fixed())
    elif opt == '2': show_reference(); solve(hints=input_hints())
    elif opt == '3':
        show_reference()
        fx = input_fixed(); hs = input_hints()
        solve(fixed=fx, hints=hs)
    else: print("Opción inválida.")