"""IQ Digits Solver — OR-Tools CP-SAT + NumPy
Tablero: 4×5 celdas  ->  25 aristas H (5×5) + 24 aristas V (4×6) = 49 aristas
10 dígitos (0-9), el '0' es cuadrado 1×1 (4 aristas); el resto 7 segmentos
Total de segmentos: 4+2+5+5+4+5+6+3+7+6 = 47  (quedan 2 aristas libres)
Cada dígito tiene 4 orientaciones (rotaciones 0°, 90°, 180°, 270°), sin reflejos."""
import numpy as np
from ortools.sat.python import cp_model

DIGITOS_DICCIONARIO = {
    0: np.array([[0,1,0],[1,0,1],[0,1,0]]),                                       # cuadrado 1x1
    1: np.array([[0,0,0],[0,0,1],[0,0,0],[0,0,1],[0,0,0]]),                       # b,c
    2: np.array([[0,1,0],[0,0,1],[0,1,0],[1,0,0],[0,1,0]]),                       # a,b,g,e,d
    3: np.array([[0,1,0],[0,0,1],[0,1,0],[0,0,1],[0,1,0]]),                       # a,b,g,c,d
    4: np.array([[0,0,0],[1,0,1],[0,1,0],[0,0,1],[0,0,0]]),                       # f,b,g,c
    5: np.array([[0,1,0],[1,0,0],[0,1,0],[0,0,1],[0,1,0]]),                       # a,f,g,c,d
    6: np.array([[0,1,0],[1,0,0],[0,1,0],[1,0,1],[0,1,0]]),                       # a,f,g,e,c,d
    7: np.array([[0,1,0],[0,0,1],[0,0,0],[0,0,1],[0,0,0]]),                       # a,b,c
    8: np.array([[0,1,0],[1,0,1],[0,1,0],[1,0,1],[0,1,0]]),                       # todos
    9: np.array([[0,1,0],[1,0,1],[0,1,0],[0,0,1],[0,1,0]]),                       # a,f,b,g,c,d
}
FILAS_MATRIZ, COLUMNAS_MATRIZ = 9, 11
TOTAL_HORIZONTALES, TOTAL_VERTICALES = 25, 24
TOTAL = TOTAL_HORIZONTALES + TOTAL_VERTICALES

def indice_arista(i, j):
    """Posición (i,j) de la grilla unificada -> índice lineal de arista."""
    return (i//2)*5 + j//2 if i % 2 == 0 else TOTAL_HORIZONTALES + (i//2)*6 + j//2

def construir_colocaciones():
    """digit -> list[(orient_idx, grid_r, grid_c, edges_tuple)]."""
    return {d: [(o, r, c, tuple(indice_arista(r+dr, c+dc) for dr, dc in zip(*np.where(p == 1))))
                for o, p in enumerate([np.rot90(DIGITOS_DICCIONARIO[d], k) for k in range(4)])
                for r in range(0, FILAS_MATRIZ - p.shape[0] + 1, 2)
                for c in range(0, COLUMNAS_MATRIZ - p.shape[1] + 1, 2)]
            for d in range(10)}

# ─── Solver ────────────────────────────────────────────────────────────────────
def solver(piezas_fijas=None, restricciones_celda=None):
    piezas_fijas, restricciones_celda = piezas_fijas or [], restricciones_celda or []
    COLOCACIONES = construir_colocaciones()
    modelo = cp_model.CpModel()

    # x[d][i] = 1 si se usa la i-ésima colocación del dígito d
    x = {d: [modelo.NewBoolVar(f'x{d}_{i}') for i in range(len(COLOCACIONES[d]))] for d in range(10)}
    for d in range(10): modelo.AddExactlyOne(x[d])

    # Cobertura por arista + no-solapamiento
    cobertura = [[] for _ in range(TOTAL)]
    for d in range(10):
        for i, (_, _, _, edges) in enumerate(COLOCACIONES[d]):
            for e in edges: cobertura[e].append((d, x[d][i]))
    for ca in cobertura:
        if ca: modelo.Add(sum(vb for _, vb in ca) <= 1)

    # Piezas fijas
    for d, o, fr, cc in piezas_fijas:
        idx = next((i for i, (po, pf, pc, _) in enumerate(COLOCACIONES[d]) if (po, pf, pc) == (o, fr, cc)), None)
        if idx is not None: modelo.Add(x[d][idx] == 1)
        else: print(f"  ⚠ Sin placement válido: dígito={d}, disp={o}, pos=({fr//2},{cc//2})")

    # Pistas por celda con etiquetas de grupo:
    #   0     -> arista vacía
    #   1..4  -> etiqueta de grupo. Misma etiqueta = mismo dígito; etiquetas distintas = dígitos distintos.
    #   suma  -> suma de los dígitos (uno por grupo).
    for fp, cp_, obj, *etqs in restricciones_celda:
        aristas = [TOTAL_HORIZONTALES + fp*6 + cp_, TOTAL_HORIZONTALES + fp*6 + cp_ + 1,   # izq, der
                   fp*5 + cp_, (fp+1)*5 + cp_]                                              # arr, aba
        grupos = {}
        for a, lbl in zip(aristas, etqs):
            modelo.Add(sum(vb for _, vb in cobertura[a]) == (1 if lbl else 0))
            if lbl: grupos.setdefault(lbl, []).append(a)
        digs = []
        for ags in grupos.values():
            dg = modelo.NewIntVar(0, 9, f'dg_{fp}_{cp_}_{len(digs)}')
            for a in ags: modelo.Add(dg == sum(d*vb for d, vb in cobertura[a]))
            digs.append(dg)
        if len(digs) > 1: modelo.AddAllDifferent(digs)
        modelo.Add(sum(digs) == obj)

    s = cp_model.CpSolver()
    s.parameters.num_search_workers = 8
    if s.Solve(modelo) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        mostrar_solucion(s, x, COLOCACIONES)
    else:
        print("\n❌ No hay solución para esta configuración.")

# ─── Visualización ─────────────────────────────────────────────────────────────
def mostrar_solucion(s, x, P):
    aristas = ['·'] * TOTAL
    for d in range(10):
        for i, (_, _, _, edges) in enumerate(P[d]):
            if s.Value(x[d][i]):
                for e in edges: aristas[e] = str(d)
    t = np.full((FILAS_MATRIZ, COLUMNAS_MATRIZ), ' ', dtype='<U2')
    t[::2, ::2] = '+'
    t[::2, 1::2] = np.array(aristas[:TOTAL_HORIZONTALES]).reshape(5, 5)
    t[1::2, ::2] = np.array(aristas[TOTAL_HORIZONTALES:]).reshape(4, 6)
    print("\n═══ Tablero (· = arista vacía) ═══")
    print('\n'.join(' '.join(f) for f in t))

# ─── Matrices de referencia ────────────────────────────────────────────────────
def mostrar_matrices():
    print("Matriz de ARISTAS (corner superior-izquierdo de la pieza):")
    print(f"      c=0    c=1    c=2    c=3    c=4    c=5")
    for i in range(5):
        print(f"f={i}  " + "".join(f"({i},{j})──" for j in range(6)))
        if i < 4: print(f"       │      │      │      │      │      │")
    print("\nMatriz de CELDAS (para pistas de suma):")
    print(f"      c=0    c=1    c=2    c=3    c=4")
    for i in range(4):
        print(f"f={i}  " + "".join(f"[{i},{j}]  " for j in range(5)))
    print("""Formato de pista:  fila columna suma izq der arr aba
    · suma  = suma de los dígitos que tocan la celda (uno por grupo)
    · izq, der, arr, aba ∈ {0,1,2,3,4}:
        0     -> arista vacía
        1..4  -> etiqueta de grupo. Misma etiqueta = MISMO dígito; etiquetas distintas = dígitos DISTINTOS.
    Ejemplos:
        1 1 1 1 con suma 8  -> las 4 aristas por un mismo dígito (8)
        1 2 3 4 con suma 18 -> 4 dígitos distintos
        1 2 2 2             -> izq con un dígito; arr/der/aba con otro distinto que cubre las 3
        1 3 2 3             -> 3 grupos: izq | arr | (der+aba) -> 3 dígitos distintos

    Disposiciones (4 rotaciones):
    0 = original 0°    1 = rot 90° CCW    2 = rot 180°    3 = rot 270° CCW""")

# ─── Entrada de usuario ────────────────────────────────────────────────────────
def ingresar_piezas_fijas():
    lista = []
    print("\n── Piezas fijas (Enter vacío para terminar) ──")
    while (entrada := input("Dígito (0-9): ").strip()):
        d = int(entrada); o = int(input("  Disposición (0-3): "))
        fr, cc = map(int, input("  Fila columna: ").split())
        lista.append((d, o, 2*fr, 2*cc))
    return lista

def ingresar_pistas_celda():
    lista = []
    print("\n── Pistas por celda (Enter vacío para terminar) ──")
    print("    Formato: fila columna suma izq der arr aba   (0=vacía, 1..4=etiqueta de grupo)")
    while (entrada := input("Pista: ").strip()):
        lista.append(tuple(map(int, entrada.split())))
    return lista

# ─── Main ──────────────────────────────────────────────────────────────────────
while True:
    print("\n" + "═"*45 + "\n         IQ Digits — Solver CP-SAT\n" + "═"*45)
    mostrar_matrices()
    solver(piezas_fijas=ingresar_piezas_fijas(), restricciones_celda=ingresar_pistas_celda())