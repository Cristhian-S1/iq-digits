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
DIGITOS_DICCIONARIO = {
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

FILAS_MATRIZ, COLUMNAS_MATRIZ = 9, 11     # grilla unificada (2*4+1, 2*5+1)
TOTAL_HORIZONTALES, TOTAL_VERTICALES = 25, 24    # aristas horizontales y verticales
TOTAL  = TOTAL_HORIZONTALES + TOTAL_VERTICALES

def indice_arista(i, j):
    """Posición (i,j) de la grilla unificada -> índice lineal de arista."""
    return (i//2)*5 + j//2 if i % 2 == 0 else TOTAL_HORIZONTALES + (i//2)*6 + j//2

def calcular_orientaciones(posicion_pieza):
    """8 orientaciones: 4 rotaciones × 2 reflejos (0-3 sin flip, 4-7 con flip)."""
    return [np.rot90(np.fliplr(posicion_pieza) if numero_orientacion >= 4 else posicion_pieza, numero_orientacion % 4) for numero_orientacion in range(8)]

def construir_colocaciones():
    """digit -> list[(orient_idx, grid_r, grid_c, edges_tuple)]."""
    colocaciones = {}
    for digito in range(10):
        #acumula todas las colocaciones válidas de un dígito antes de asignarlas al diccionario
        colocaciones_por_digito = []
        for numero_orientacion, plantilla in enumerate(calcular_orientaciones(DIGITOS_DICCIONARIO[digito])):
            alto_plantilla, ancho_plantilla = plantilla.shape
            filas_segmentos_activos, columnas_segmentos_activos = np.where(plantilla == 1)                                             # posiciones de segmentos
            for fila_esquina_superior in range(0, FILAS_MATRIZ - alto_plantilla + 1, 2):                                     # solo anclas en esquinas
                for columna_esquina_superior in range(0, COLUMNAS_MATRIZ - ancho_plantilla + 1, 2):
                    colocaciones_por_digito.append((numero_orientacion, fila_esquina_superior, columna_esquina_superior,
                                tuple(indice_arista(fila_esquina_superior+desplazamiento_fila, columna_esquina_superior+desplazamiento_columna) for desplazamiento_fila, desplazamiento_columna in zip(filas_segmentos_activos, columnas_segmentos_activos))))
        colocaciones[digito] = colocaciones_por_digito
    return colocaciones

# ─── Solver ────────────────────────────────────────────────────────────────────
def solver(piezas_fijas=None, restricciones_celda=None):
    piezas_fijas, restricciones_celda = piezas_fijas or [], restricciones_celda or []
    COLOCACIONES = construir_colocaciones()
    modelo = cp_model.CpModel()

    # Variables: variables_decision[digito][indice_colocacion] = 1 si se usa la indice_colocacion-ésima colocación del dígito digito
    variables_decision = {digito: [modelo.NewBoolVar(f'variables_decision{digito}_{indice_colocacion}') for indice_colocacion in range(len(COLOCACIONES[digito]))] for digito in range(10)}

    # Cada dígito aparece exactamente una vez
    for digito in range(10):
        modelo.AddExactlyOne(variables_decision[digito])

    # Cobertura por arista
    cobertura_aristas = [[] for _ in range(TOTAL)]
    for digito in range(10):
        for indice_colocacion, (_, _, _, edges) in enumerate(COLOCACIONES[digito]):
            for indice_arista in edges:
                cobertura_aristas[indice_arista].append((digito, variables_decision[digito][indice_colocacion]))

    # No-solapamiento + valor por arista (0 si vacía; también 0 si es el dígito 0)
    valores_aristas = []
    for indice_arista in range(TOTAL):
        variable_valor_arista = modelo.NewIntVar(0, 9, f'variable_valor_arista{indice_arista}')
        if cobertura_aristas[indice_arista]:
            modelo.Add(sum(variable_booleana for _, variable_booleana in cobertura_aristas[indice_arista]) <= 1)
            modelo.Add(variable_valor_arista == sum(digito * variable_booleana for digito, variable_booleana in cobertura_aristas[indice_arista]))
        else:
            modelo.Add(variable_valor_arista == 0)
        valores_aristas.append(variable_valor_arista)

    # Piezas fijas
    for digito, orientacion, fila_esquina_superior, columna_esquina_superior in piezas_fijas:
        encontrado = False
        for indice_colocacion, (numero_orientacion, fila_colocacion, columna_colocacion, _) in enumerate(COLOCACIONES[digito]):
            if numero_orientacion == orientacion and fila_colocacion == fila_esquina_superior and columna_colocacion == columna_esquina_superior:
                modelo.Add(variables_decision[digito][indice_colocacion] == 1); encontrado = True; break
        if not encontrado:
            print(f"  ⚠ Sin placement válido: dígito={digito}, disp={orientacion}, pos=({fila_esquina_superior//2},{columna_esquina_superior//2})")

    # Pistas por celda: suma de las 4 aristas vecinas == target
    for fila_pista, columna_pista, objetivo in restricciones_celda:
        arista_superior = fila_pista*5 + columna_pista
        arista_inferior = (fila_pista+1)*5 + columna_pista
        arista_izquierda = TOTAL_HORIZONTALES + fila_pista*6 + columna_pista
        arista_derecha = TOTAL_HORIZONTALES + fila_pista*6 + (columna_pista+1)
        modelo.Add(valores_aristas[arista_superior] + valores_aristas[arista_inferior] + valores_aristas[arista_izquierda] + valores_aristas[arista_derecha] == objetivo)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 8
    estado = solver.Solve(modelo)
    if estado in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        mostrar_solucion(solver, variables_decision, COLOCACIONES)
    else:
        print("\n❌ No hay solución para esta configuración.")
# ─── Visualización ─────────────────────────────────────────────────────────────
def mostrar_solucion(solver, x, P):
    matriz_horizontales = np.full((5, 5), -1, dtype=int)
    matriz_verticales = np.full((4, 6), -1, dtype=int)
    for digito in range(10):
        for indice_colocacion, (_, _, _, edges) in enumerate(P[digito]):
            if solver.Value(x[digito][indice_colocacion]):
                for indice_arista_resuelta in edges:
                    if indice_arista_resuelta < TOTAL_HORIZONTALES: matriz_horizontales[indice_arista_resuelta//5, indice_arista_resuelta%5] = digito
                    else:      matriz_verticales[(indice_arista_resuelta-TOTAL_HORIZONTALES)//6, (indice_arista_resuelta-TOTAL_HORIZONTALES)%6] = digito
    print("\n═══ Aristas horizontales (5×5)  -1 = vacía ═══")
    print(matriz_horizontales)
    print("\n═══ Aristas verticales (4×6)    -1 = vacía ═══")
    print(matriz_verticales)
    print("\n═══ Tablero (· = arista vacía) ═══")
    tablero_visual = np.full((FILAS_MATRIZ, COLUMNAS_MATRIZ), ' ', dtype='<U2')
    tablero_visual[::2, ::2]   = '+'
    tablero_visual[::2, 1::2]  = np.where(matriz_horizontales >= 0, matriz_horizontales.astype(str), '·')
    tablero_visual[1::2, ::2]  = np.where(matriz_verticales >= 0, matriz_verticales.astype(str), '·')
    print('\n'.join(' '.join(fila_visual) for fila_visual in tablero_visual))

def mostrar_matrices():
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
def ingresar_piezas_fijas():
    lista_piezas = []
    print("\n── Piezas fijas (Enter vacío para terminar) ──")
    while True:
        entrada = input("Dígito (0-9): ").strip()
        if not entrada: break
        digito = int(entrada)
        orientacion = int(input("  Disposición (0-7): "))
        fila_esquina_superior, columna_esquina_superior = map(int, input("  Fila columna: ").split())
        lista_piezas.append((digito, orientacion, 2*fila_esquina_superior, 2*columna_esquina_superior))
    return lista_piezas

def ingresar_pistas_celda():
    lista_pistas = []
    print("\n── Pistas por celda (Enter vacío para terminar) ──")
    while True:
        entrada = input("Fila columna suma: ").strip()
        if not entrada: break
        fila_pista, columna_pista, objetivo = map(int, entrada.split())
        lista_pistas.append((fila_pista, columna_pista, objetivo))
    return lista_pistas

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
    opcion = input("Opción: ").strip()
    if opcion == '5': break
    if   opcion == '4': mostrar_matrices()
    elif opcion == '1': mostrar_matrices(); solver(piezas_fijas=ingresar_piezas_fijas())
    elif opcion == '2': mostrar_matrices(); solver(restricciones_celda=ingresar_pistas_celda())
    elif opcion == '3':
        mostrar_matrices()
        lista_piezas = ingresar_piezas_fijas(); lista_pistas = ingresar_pistas_celda()
        solver(piezas_fijas=lista_piezas, restricciones_celda=lista_pistas)
    else: print("Opción inválida.")