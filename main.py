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

def indice_arista(fila, columna):
    """Posición (fila, columna) de la grilla unificada -> índice lineal de arista."""
    return (fila//2)*5 + columna//2 if fila % 2 == 0 else TOTAL_HORIZONTALES + (fila//2)*6 + columna//2

def construir_colocaciones():
    """digito -> list[(orientacion, fila, columna, aristas_tupla)]."""
    return {digito: [(orientacion, fila, columna,
                      tuple(indice_arista(fila+desplaz_fila, columna+desplaz_columna)
                            for desplaz_fila, desplaz_columna in zip(*np.where(plantilla == 1))))
                     for orientacion, plantilla in enumerate([np.rot90(DIGITOS_DICCIONARIO[digito], k) for k in range(4)])
                     for fila in range(0, FILAS_MATRIZ - plantilla.shape[0] + 1, 2)
                     for columna in range(0, COLUMNAS_MATRIZ - plantilla.shape[1] + 1, 2)]
            for digito in range(10)}

# ─── Solver ────────────────────────────────────────────────────────────────────
def solver(piezas_fijas=None, restricciones_celda=None):
    piezas_fijas, restricciones_celda = piezas_fijas or [], restricciones_celda or []
    COLOCACIONES = construir_colocaciones()
    modelo = cp_model.CpModel()

    # variables_decision[digito][indice] = 1 si se usa esa colocación del dígito
    variables_decision = {digito: [modelo.NewBoolVar(f'x{digito}_{indice}')
                                   for indice in range(len(COLOCACIONES[digito]))]
                          for digito in range(10)}
    for digito in range(10): modelo.AddExactlyOne(variables_decision[digito])

    # Cobertura por arista + no-solapamiento
    cobertura_aristas = [[] for _ in range(TOTAL)]
    for digito in range(10):
        for indice, (_, _, _, aristas_pieza) in enumerate(COLOCACIONES[digito]):
            for arista in aristas_pieza:
                cobertura_aristas[arista].append((digito, variables_decision[digito][indice]))
    for cobertura_arista in cobertura_aristas:
        if cobertura_arista: modelo.Add(sum(var_bool for _, var_bool in cobertura_arista) <= 1)

    # Piezas fijas
    for digito, orientacion, fila, columna in piezas_fijas:
        indice_colocacion = next((i for i, (orient_p, fila_p, col_p, _) in enumerate(COLOCACIONES[digito])
                                  if (orient_p, fila_p, col_p) == (orientacion, fila, columna)), None)
        if indice_colocacion is not None: modelo.Add(variables_decision[digito][indice_colocacion] == 1)
        else: print(f"  ⚠ Sin placement válido: dígito={digito}, disp={orientacion}, pos=({fila//2},{columna//2})")

    # Pistas por celda con etiquetas de grupo:
    #   0     -> arista vacía
    #   1..4  -> etiqueta de grupo. Misma etiqueta = mismo dígito; etiquetas distintas = dígitos distintos.
    #   suma  -> suma de los dígitos (uno por grupo).
    for fila_celda, columna_celda, suma_objetivo, *etiquetas in restricciones_celda:
        aristas_celda = [TOTAL_HORIZONTALES + fila_celda*6 + columna_celda,           # izq
                         TOTAL_HORIZONTALES + fila_celda*6 + columna_celda + 1,       # der
                         fila_celda*5 + columna_celda,                                # arr
                         (fila_celda+1)*5 + columna_celda]                            # aba
        grupos = {}
        for arista, etiqueta in zip(aristas_celda, etiquetas):
            modelo.Add(sum(var_bool for _, var_bool in cobertura_aristas[arista]) == (1 if etiqueta else 0))
            if etiqueta: grupos.setdefault(etiqueta, []).append(arista)
        digitos_grupos = []
        for aristas_grupo in grupos.values():
            digito_grupo = modelo.NewIntVar(0, 9, f'dg_{fila_celda}_{columna_celda}_{len(digitos_grupos)}')
            for arista in aristas_grupo:
                modelo.Add(digito_grupo == sum(d * var_bool for d, var_bool in cobertura_aristas[arista]))
            digitos_grupos.append(digito_grupo)
        if len(digitos_grupos) > 1: modelo.AddAllDifferent(digitos_grupos)
        modelo.Add(sum(digitos_grupos) == suma_objetivo)

    solucionador = cp_model.CpSolver()
    solucionador.parameters.num_search_workers = 8
    if solucionador.Solve(modelo) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        mostrar_solucion(solucionador, variables_decision, COLOCACIONES)
    else:
        print("\n❌ No hay solución para esta configuración.")

# ─── Visualización ─────────────────────────────────────────────────────────────
def mostrar_solucion(solucionador, variables_decision, colocaciones):
    aristas_visuales = ['·'] * TOTAL
    for digito in range(10):
        for indice, (_, _, _, aristas_pieza) in enumerate(colocaciones[digito]):
            if solucionador.Value(variables_decision[digito][indice]):
                for arista in aristas_pieza: aristas_visuales[arista] = str(digito)
    tablero_visual = np.full((FILAS_MATRIZ, COLUMNAS_MATRIZ), ' ', dtype='<U2')
    tablero_visual[::2, ::2] = '+'
    tablero_visual[::2, 1::2] = np.array(aristas_visuales[:TOTAL_HORIZONTALES]).reshape(5, 5)
    tablero_visual[1::2, ::2] = np.array(aristas_visuales[TOTAL_HORIZONTALES:]).reshape(4, 6)
    print("\n═══ Tablero (· = arista vacía) ═══")
    print('\n'.join(' '.join(fila_visual) for fila_visual in tablero_visual))

# ─── Matrices de referencia ────────────────────────────────────────────────────
def mostrar_matrices():
    print("Matriz de ARISTAS (corner superior-izquierdo de la pieza):")
    print(f"      c=0    c=1    c=2    c=3    c=4    c=5")
    for fila in range(5):
        print(f"f={fila}  " + "".join(f"({fila},{columna})──" for columna in range(6)))
        if fila < 4: print(f"       │      │      │      │      │      │")
    print("\nMatriz de CELDAS (para pistas de suma):")
    print(f"      c=0    c=1    c=2    c=3    c=4")
    for fila in range(4):
        print(f"f={fila}  " + "".join(f"[{fila},{columna}]  " for columna in range(5)))
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
    lista_piezas = []
    print("\n── Piezas fijas (Enter vacío para terminar) ──")
    while (entrada := input("Dígito (0-9): ").strip()):
        digito = int(entrada)
        orientacion = int(input("  Disposición (0-3): "))
        fila, columna = map(int, input("  Fila columna: ").split())
        lista_piezas.append((digito, orientacion, 2*fila, 2*columna))
    return lista_piezas

def ingresar_pistas_celda():
    lista_pistas = []
    print("\n── Pistas por celda (Enter vacío para terminar) ──")
    print("    Formato: fila columna suma izq der arr aba   (0=vacía, 1..4=etiqueta de grupo)")
    while (entrada := input("Pista: ").strip()):
        lista_pistas.append(tuple(map(int, entrada.split())))
    return lista_pistas

# ─── Main ──────────────────────────────────────────────────────────────────────
while True:
    print("\n" + "═"*45 + "\n         IQ Digits — Solver CP-SAT\n" + "═"*45)
    mostrar_matrices()
    solver(piezas_fijas=ingresar_piezas_fijas(), restricciones_celda=ingresar_pistas_celda())