"""
IQ Digits Solver — OR-Tools CP-SAT + NumPy
Resuelve el puzzle IQ Digits mediante programación de restricciones.

Tablero: 4×5 celdas  ->  25 aristas H (5×5) + 24 aristas V (4×6) = 49 aristas
10 dígitos (0-9), el '0' es cuadrado 1×1 (4 aristas); el resto 7 segmentos
Total de segmentos: 4+2+5+5+4+5+6+3+7+6 = 47  (quedan 2 aristas libres)
Cada dígito tiene 4 orientaciones (rotaciones 0°, 90°, 180°, 270°), sin reflejos.
"""

import numpy as np
from ortools.sat.python import cp_model

# ═══════════════════════════════════════════════════════════════════════════════
# DICCIONARIO DE DÍGITOS — Plantillas de segmentos en grilla 2D
# ═══════════════════════════════════════════════════════════════════════════════
# Cada dígito se representa como una matriz binaria donde 1 = segmento activo.
# El formato mapea directamente a un display de 7 segmentos estandar, adaptado
# al puzzle IQ Digits (cuadrícula de aristas).
#
# Estructura interna de cada matriz:
#   - Las matrices indican qué aristas del dígito deben colocarse
#   - Se aplican rotaciones de 90° antihorario para obtener las 4 orientaciones
#   - La coordenada (0,0) de cada plantilla es la esquina superior-izquierda
#
# Ejemplo: dígito 8 tiene todos los segmentos activos:
#   [[0,1,0],   -> arista superior
#    [1,0,1],   -> aristas izquierda + derecha (medio)
#    [0,1,0],   -> arista horizontal media
#    [1,0,1],   -> aristas izquierda + derecha (inferior)
#    [0,1,0]]   -> arista inferior
# ═══════════════════════════════════════════════════════════════════════════════

DIGITOS_DICCIONARIO = {
    0: np.array([[0,1,0],[1,0,1],[0,1,0]]),                 # cuadrado 1x1 (4 aristas)
    1: np.array([[0,0,0],[0,0,1],[0,0,0],[0,0,1],[0,0,0]]), # segmentos b,c (derecha)
    2: np.array([[0,1,0],[0,0,1],[0,1,0],[1,0,0],[0,1,0]]), # a,b,g,e,d
    3: np.array([[0,1,0],[0,0,1],[0,1,0],[0,0,1],[0,1,0]]), # a,b,g,c,d
    4: np.array([[0,0,0],[1,0,1],[0,1,0],[0,0,1],[0,0,0]]), # f,b,g,c
    5: np.array([[0,1,0],[1,0,0],[0,1,0],[0,0,1],[0,1,0]]), # a,f,g,c,d
    6: np.array([[0,1,0],[1,0,0],[0,1,0],[1,0,1],[0,1,0]]), # a,f,g,e,c,d
    7: np.array([[0,1,0],[0,0,1],[0,0,0],[0,0,1],[0,0,0]]), # a,b,c
    8: np.array([[0,1,0],[1,0,1],[0,1,0],[1,0,1],[0,1,0]]), # todos los segmentos
    9: np.array([[0,1,0],[1,0,1],[0,1,0],[0,0,1],[0,1,0]]), # a,f,b,g,c,d
}


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES DE LA GRILLA UNIFICADA
# ═══════════════════════════════════════════════════════════════════════════════
# El tablero se representa internamente como una grilla unificada de 9×11,
# donde:
#   - Posiciones (par, par)     → esquinas / intersecciones (marcadas con '+')
#   - Posiciones (par, impar)   → aristas horizontales
#   - Posiciones (impar, par)   → aristas verticales
#   - Posiciones (impar, impar) → interior de celdas (no usado directamente)
#
# Ejemplo visual de una sub-región 5×5 de la grilla:
#   + ─ + ─ +         (0,0) (0,1) (0,2) (0,3) (0,4)
#   │   │   │         (1,0)       (1,2)       (1,4)
#   + ─ + ─ +         (2,0) (2,1) (2,2) (2,3) (2,4)
#
# La conversión de coordenadas de celda (0..3, 0..4) a grilla unificada se
# realiza multiplicando por 2. Ver `ingresar_piezas_fijas()`.
# ═══════════════════════════════════════════════════════════════════════════════

FILAS_MATRIZ, COLUMNAS_MATRIZ = 9, 11
TOTAL_HORIZONTALES, TOTAL_VERTICALES = 25, 24
TOTAL = TOTAL_HORIZONTALES + TOTAL_VERTICALES  # 49 aristas totales en el puzzle


def indice_arista(fila, columna):
    """
    Convierte una posición (fila, columna) de la grilla unificada 9×11
    a un índice lineal único en el rango [0, TOTAL).

    La grilla unificada contiene tanto aristas horizontales como verticales
    intercaladas. Esta función realiza la conversión necesaria para acceder
    a arrays lineales de aristas.

    Parámetros
    ----------
    fila : int
        Fila en la grilla unificada (0..8).
    columna : int
        Columna en la grilla unificada (0..10).

    Devuelve
    --------
    int
        Índice lineal de la arista.
        - Si fila es par:  índice en [0, TOTAL_HORIZONTALES)  (arista horizontal)
        - Si fila es impar: índice en [TOTAL_HORIZONTALES, TOTAL) (arista vertical)

    Fórmula
    -------
    - Horizontales (fila par):    (fila//2) * 5 + (columna//2)
      Cada fila de celdas tiene 5 aristas horizontales; hay 5 filas de celdas.
    - Verticales (fila impar):    TOTAL_HORIZONTALES + (fila//2) * 6 + (columna//2)
      Cada columna de celdas tiene 6 aristas verticales; hay 4 filas de celdas.

    Nota
    ----
    La columna siempre será impar para horizontales y par para verticales
    en uso normal, pero la función funciona para cualquier par (fila, columna).
    """
    return (
        (fila // 2) * 5 + columna // 2
        if fila % 2 == 0
        else TOTAL_HORIZONTALES + (fila // 2) * 6 + columna // 2
    )


def construir_colocaciones():
    """
    Genera TODAS las colocaciones válidas para cada dígito en el tablero.

    Una "colocación" es una tupla:
        (orientacion, fila, columna, aristas_tupla)
    donde:
        - orientacion : int  (0=0°, 1=90°, 2=180°, 3=270° rotación antihoraria)
        - fila, columna : int  (posición en la grilla unificada 9×11, siempre par)
        - aristas_tupla : tuple[int]  (índices lineales de las aristas que ocupa)

    Proceso de construcción (por dígito):
    1. Rota la plantilla base en 0°, 90°, 180°, 270° (sentido antihorario).
    2. Para cada orientación, la desliza por todas las posiciones válidas
       de la grilla unificada, avanzando de 2 en 2 (solo esquinas).
    3. Para cada posición válida, extrae los índices lineales de las aristas
       que la pieza ocuparía, según dónde la plantilla tenga valor 1.

    Retorno
    -------
    dict[int, list[tuple]]
        Mapeo: dígito (0..9) → lista de todas sus colocaciones válidas.

    Nota importante
    ---------------
    Las rotaciones se realizan con np.rot90(..., k), donde k indica cuántas
    veces se rota 90° en sentido ANTIHORARIO. No se permiten reflejos.
    """
    return {
        digito: [
            (
                orientacion,
                fila,
                columna,
                tuple(
                    indice_arista(
                        fila + desplaz_fila,
                        columna + desplaz_columna
                    )
                    for desplaz_fila, desplaz_columna in zip(*np.where(plantilla == 1))
                ),
            )
            # Genera las 4 orientaciones rotando 0°, 90°, 180°, 270°
            for orientacion, plantilla in enumerate(
                [np.rot90(DIGITOS_DICCIONARIO[digito], k) for k in range(4)]
            )
            # Desliza la pieza por la grilla unificada, en pasos de 2
            # (solo se anclan en coordenadas pares, que son las esquinas)
            for fila in range(0, FILAS_MATRIZ - plantilla.shape[0] + 1, 2)
            for columna in range(0, COLUMNAS_MATRIZ - plantilla.shape[1] + 1, 2)
        ]
        for digito in range(10)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SOLVER PRINCIPAL — Modelo CP-SAT (Constraint Programming - SATisfiability)
# ═══════════════════════════════════════════════════════════════════════════════
# El puzzle se modela como un problema de cobertura exacta con restricciones
# adicionales:
#
#   1. EXACTAMENTE UNA colocación por dígito (0..9).
#   2. Cada arista del tablero es ocupada por COMO MÁXIMO un dígito
#      (no solapamiento).
#   3. Piezas fijas: fuerzan una colocación específica de un dígito.
#   4. Pistas por celda: restricciones de suma y agrupamiento de aristas.
#
# Por diseño del puzzle, 47 de 49 aristas estarán ocupadas (2 libres).
# El solver busca la PRIMERA solución factible (no busca óptima ni todas).
# ═══════════════════════════════════════════════════════════════════════════════

def solver(piezas_fijas=None, restricciones_celda=None):
    """
    Resuelve el puzzle IQ Digits usando OR-Tools CP-SAT.

    Parámetros
    ----------
    piezas_fijas : list[tuple] | None
        Lista de piezas ya posicionadas en el tablero. Cada tupla:
            (digito, orientacion, fila, columna)
        donde fila y columna están en coordenadas de la GRILLA UNIFICADA
        (es decir, multiplicadas por 2 respecto a las coordenadas de celda).
        Si es None, se interpreta como lista vacía.

    restricciones_celda : list[tuple] | None
        Lista de pistas de suma por celda. Cada tupla:
            (fila_celda, columna_celda, suma_objetivo, *etiquetas)
        donde etiquetas son 4 enteros para izquierda, derecha, arriba, abajo:
            0     → arista vacía (no pertenece a ningún dígito)
            1..4  → etiqueta de grupo. Misma etiqueta = mismo dígito;
                     etiquetas distintas = dígitos distintos.
        Si es None, se interpreta como lista vacía.

    Comportamiento
    --------------
    - Crea un modelo CP-SAT con variables booleanas de decisión.
    - Agrega restricciones de unicidad, no-solapamiento, piezas fijas y pistas.
    - Lanza el solver con 8 workers en paralelo.
    - Si encuentra solución factible u óptima, la visualiza con `mostrar_solucion()`.
    - Si no existe solución, imprime un mensaje informativo.
    """
    # Normaliza argumentos None a listas vacías
    piezas_fijas = piezas_fijas or []
    restricciones_celda = restricciones_celda or []

    # Precalcula todas las colocaciones posibles para cada dígito
    COLOCACIONES = construir_colocaciones()

    # Inicializa el modelo CP-SAT
    modelo = cp_model.CpModel()

    # ──────────────────────────────────────────────────────────────────────────
    # Variables de decisión
    # ──────────────────────────────────────────────────────────────────────────
    # Para cada dígito, creamos un array de variables booleanas.
    # variables_decision[digito][indice] == 1  significa que se usa esa
    # colocación específica del dígito en la solución.
    #
    # Restricción: Exactamente una colocación por dígito.
    # Esto garantiza que cada dígito (0-9) aparece exactamente una vez.
    # ──────────────────────────────────────────────────────────────────────────

    variables_decision = {
        digito: [
            modelo.NewBoolVar(f"x{digito}_{indice}")
            for indice in range(len(COLOCACIONES[digito]))
        ]
        for digito in range(10)
    }

    for digito in range(10):
        # AddExactlyOne fuerza que exactamente una variable del array sea True
        modelo.AddExactlyOne(variables_decision[digito])

    # ──────────────────────────────────────────────────────────────────────────
    # Restricción de cobertura de aristas (no-solapamiento)
    # ──────────────────────────────────────────────────────────────────────────
    # Construimos una lista inversa: para cada arista del tablero, sabemos
    # qué colocaciones (de qué dígitos) la cubren.
    # Luego, para cada arista, sumamos las variables booleanas correspondientes
    # y exigimos que la suma sea ≤ 1.
    #
    # Esto impide que dos dígitos compartan una arista (no solapamiento).
    # Las aristas con suma == 0 serán las 2 aristas libres del puzzle.
    # ──────────────────────────────────────────────────────────────────────────

    cobertura_aristas = [[] for _ in range(TOTAL)]  # una lista por arista

    for digito in range(10):
        for indice, (_, _, _, aristas_pieza) in enumerate(COLOCACIONES[digito]):
            for arista in aristas_pieza:
                # Guardamos qué variable booleana controla esta arista
                cobertura_aristas[arista].append(
                    (digito, variables_decision[digito][indice])
                )

    for cobertura_arista in cobertura_aristas:
        if cobertura_arista:
            # La arista puede estar cubierta por 0 o 1 dígito (nunca 2+)
            modelo.Add(
                sum(var_bool for _, var_bool in cobertura_arista) <= 1
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Piezas fijas (entradas del usuario)
    # ──────────────────────────────────────────────────────────────────────────
    # Si el usuario proporcionó piezas con posición/orientación fijas,
    # buscamos la colocación correspondiente en COLOCACIONES y forzamos
    # su variable booleana a 1.
    #
    # Si la combinación (orientación, fila, columna) no existe en las
    # colocaciones precalculadas, se imprime una advertencia (podría ser
    # una posición inválida fuera del tablero).
    # ──────────────────────────────────────────────────────────────────────────

    for digito, orientacion, fila, columna in piezas_fijas:
        indice_colocacion = next(
            (
                i
                for i, (orient_p, fila_p, col_p, _) in enumerate(COLOCACIONES[digito])
                if (orient_p, fila_p, col_p) == (orientacion, fila, columna)
            ),
            None,
        )
        if indice_colocacion is not None:
            modelo.Add(variables_decision[digito][indice_colocacion] == 1)
        else:
            # Posible causa: coordenadas fuera de rango u orientación imposible
            print(
                f" Sin placement válido: dígito={digito}, "
                f"disp={orientacion}, pos=({fila//2},{columna//2})"
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Pistas por celda con etiquetas de grupo
    # ──────────────────────────────────────────────────────────────────────────
    # Cada celda del tablero (hay 4×5 = 20 celdas) tiene 4 aristas:
    #   izquierda, derecha, arriba, abajo.
    #
    # Etiquetas:
    #   0     → arista vacía (sin dígito adyacente en esa dirección)
    #   1..4  → etiqueta de grupo. Aristas con la MISMA etiqueta pertenecen
    #           al MISMO dígito. Etiquetas DISTINTAS implican dígitos DISTINTOS.
    #
    # Suma objetivo:
    #   Se calcula como la suma de los dígitos que tocan la celda,
    #   contando UNO por grupo de aristas (no uno por arista).
    #
    # Ejemplos (ver mostrar_matrices() para más detalles):
    #   [1,1,1,1] suma=8  → un solo dígito (el 8) toca las 4 aristas.
    #   [1,2,3,4] suma=18 → 4 dígitos distintos, suman 18.
    #   [1,2,2,2]         → 2 grupos: izquierda | (der+arr+aba) → 2 dígitos.
    # ──────────────────────────────────────────────────────────────────────────

    for fila_celda, columna_celda, suma_objetivo, *etiquetas in restricciones_celda:
        # Índices lineales de las 4 aristas que rodean esta celda
        aristas_celda = [
            TOTAL_HORIZONTALES + fila_celda * 6 + columna_celda,       # izquierda (V)
            TOTAL_HORIZONTALES + fila_celda * 6 + columna_celda + 1,   # derecha   (V)
            fila_celda * 5 + columna_celda,                            # arriba    (H)
            (fila_celda + 1) * 5 + columna_celda,                      # abajo     (H)
        ]

        # Agrupa aristas por etiqueta
        grupos = {}
        for arista, etiqueta in zip(aristas_celda, etiquetas):
            # Si etiqueta == 0, la arista debe estar libre (suma de cobertura == 0)
            modelo.Add(
                sum(var_bool for _, var_bool in cobertura_aristas[arista])
                == (1 if etiqueta else 0)
            )
            if etiqueta:
                grupos.setdefault(etiqueta, []).append(arista)

        # Para cada grupo de aristas, creamos una variable entera que representa
        # el dígito que cubre ese grupo. Todas las aristas del mismo grupo
        # deben ser cubiertas por el mismo dígito.
        digitos_grupos = []
        for aristas_grupo in grupos.values():
            digito_grupo = modelo.NewIntVar(
                0, 9, f"dg_{fila_celda}_{columna_celda}_{len(digitos_grupos)}"
            )
            for arista in aristas_grupo:
                # El dígito del grupo es igual al dígito que cubre la arista.
                # Si la arista está cubierta, la suma ponderada (d * var_bool)
                # da exactamente el dígito; si no está cubierta, la suma es 0
                # pero esto ya se controló arriba (etiqueta != 0 => debe estar cubierta).
                modelo.Add(
                    digito_grupo
                    == sum(d * var_bool for d, var_bool in cobertura_aristas[arista])
                )
            digitos_grupos.append(digito_grupo)

        # Dígitos de grupos distintos deben ser diferentes entre sí
        if len(digitos_grupos) > 1:
            modelo.AddAllDifferent(digitos_grupos)

        # La suma de los dígitos de todos los grupos debe coincidir con la pista
        modelo.Add(sum(digitos_grupos) == suma_objetivo)

    # ──────────────────────────────────────────────────────────────────────────
    # Resolución del modelo
    # ──────────────────────────────────────────────────────────────────────────
    # Usamos 8 workers en paralelo para acelerar la búsqueda.
    # El solver se detiene en la PRIMERA solución factible encontrada.
    # No buscamos óptima (no hay función objetivo) ni todas las soluciones.
    # ──────────────────────────────────────────────────────────────────────────

    solucionador = cp_model.CpSolver()
    solucionador.parameters.num_search_workers = 8

    estado = solucionador.Solve(modelo)
    if estado in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        mostrar_solucion(solucionador, variables_decision, COLOCACIONES)
    else:
        print("\n No hay solución para esta configuración.")


# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZACIÓN DE RESULTADOS
# ═══════════════════════════════════════════════════════════════════════════════

def mostrar_solucion(solucionador, variables_decision, colocaciones):
    """
    Convierte la solución numérica del CP-SAT a una representación visual
    legible en consola.

    Parámetros
    ----------
    solucionador : cp_model.CpSolver
        Instancia del solver ya ejecutada (con solución asignada).
    variables_decision : dict[int, list[BoolVar]]
        Variables de decisión del modelo.
    colocaciones : dict[int, list[tuple]]
        Diccionario de colocaciones precalculadas.

    Proceso de visualización
    ------------------------
    1. Recorre todas las variables de decisión; para aquellas con valor 1,
       marca las aristas correspondientes con el dígito que las cubre.
    2. Las aristas no cubiertas se marcan con '·' (punto medio).
    3. Reconstruye la grilla unificada 9×11 como una matriz de caracteres:
       - '+' en las esquinas (coordenadas pares, pares)
       - Dígitos 0-9 en las aristas ocupadas
       - '·' en las aristas libres (2 en total)
       - Espacios en los interiores de celdas
    """
    # Inicialmente todas las aristas están libres ('·')
    aristas_visuales = ["·"] * TOTAL

    # Para cada dígito, encuentra su colocación activa y marca sus aristas
    for digito in range(10):
        for indice, (_, _, _, aristas_pieza) in enumerate(colocaciones[digito]):
            if solucionador.Value(variables_decision[digito][indice]):
                for arista in aristas_pieza:
                    aristas_visuales[arista] = str(digito)

    # Construye la matriz visual 9×11
    tablero_visual = np.full((FILAS_MATRIZ, COLUMNAS_MATRIZ), " ", dtype="<U2")

    # Esquinas/intersecciones
    tablero_visual[::2, ::2] = "+"

    # Aristas horizontales (fila par, columna impar)
    tablero_visual[::2, 1::2] = np.array(
        aristas_visuales[:TOTAL_HORIZONTALES]
    ).reshape(5, 5)

    # Aristas verticales (fila impar, columna par)
    tablero_visual[1::2, ::2] = np.array(
        aristas_visuales[TOTAL_HORIZONTALES:]
    ).reshape(4, 6)

    # Imprime el tablero con espacios entre caracteres para legibilidad
    print("\n=== Tablero (· = arista vacía) ===")
    print("\n".join(" ".join(fila_visual) for fila_visual in tablero_visual))


# ═══════════════════════════════════════════════════════════════════════════════
# MATRICES DE REFERENCIA (ayuda para el usuario)
# ═══════════════════════════════════════════════════════════════════════════════

def mostrar_matrices():
    """
    Muestra en consola matrices de referencia para ayudar al usuario a
    ingresar piezas fijas y pistas de celda.

    Incluye:
    1. Matriz de aristas: muestra la posición de cada arista usando
       coordenadas (fila, columna) de la celda superior-izquierda.
    2. Matriz de celdas: muestra la numeración de las 20 celdas del puzzle.
    3. Instrucciones detalladas del formato de pista y las disposiciones.
    """
    print("Matriz de aristas (corner superior-izquierdo de la pieza):")
    print(f"      c=0    c=1    c=2    c=3    c=4    c=5")
    for fila in range(5):
        print(f"f={fila}  " + "".join(f"({fila},{columna})──" for columna in range(6)))
        if fila < 4:
            print(f"       │      │      │      │      │      │")

    print("\nMatriz de celdas (para pistas de suma):")
    print(f"      c=0    c=1    c=2    c=3    c=4")
    for fila in range(4):
        print(f"f={fila}  " + "".join(f"[{fila},{columna}]  " for columna in range(5)))

    print(
        """Formato de pista:  fila columna suma izquierda derecha arriba abajo
    - suma  = suma de los dígitos que tocan la celda (uno por grupo)
    - izquierda, derecha, arriba, abajo puede ser {0,1,2,3,4}:
        0   -> arista vacía
        1-4 -> etiqueta de grupo. Misma etiqueta = Mismo dígito. etiquetas distintas = dígitos distintos.
    Ejemplos:
        1 1 1 1 con suma 8  -> las 4 aristas por un mismo dígito que es el 8
        1 2 3 4 con suma 18 -> 4 dígitos distintos
        1 2 2 2             -> izquierda con un dígito; arr/der/aba con otro distinto que cubre las 3
        1 3 2 3             -> 3 grupos: izq | arr | (der+aba) -> 3 dígitos distintos

    Disposiciones (4 rotaciones):
    0 = original 0°  1 = rot 90°  2 = rot 180°  3 = rot 270° """
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRADA DE USUARIO (interactiva)
# ═══════════════════════════════════════════════════════════════════════════════

def ingresar_piezas_fijas():
    """
    Solicita al usuario la entrada interactiva de piezas fijas.

    Cada pieza se define por:
        - dígito      : int (0..9)
        - orientación : int (0..3)
        - fila, columna : int (0..3 y 0..4 respectivamente, coordenadas de CELDA)

    Conversión de coordenadas
    -------------------------
    El usuario ingresa coordenadas de celda (0..3, 0..4), pero internamente
    se almacenan multiplicadas por 2 para obtener coordenadas de la
    GRILLA UNIFICADA (0..8, 0..10). Esto es consistente con el sistema
    donde las esquinas de celdas corresponden a coordenadas pares.

    Ejemplo: si el usuario ingresa fila=1, columna=2, se almacena como (2, 4).

    Devuelve
    --------
    list[tuple]
        Lista de tuplas (digito, orientacion, fila*2, columna*2).
        El bucle termina cuando el usuario presiona Enter sin escribir nada.
    """
    lista_piezas = []
    print("\n-- Piezas fijas (Enter vacío para terminar) --")
    while (entrada := input("Dígito (0-9): ").strip()):
        digito = int(entrada)
        orientacion = int(input("  Disposición (0-3): "))
        fila, columna = map(int, input("  Fila columna: ").split())
        # Multiplicamos por 2 para convertir a coordenadas de grilla unificada
        lista_piezas.append((digito, orientacion, 2 * fila, 2 * columna))
    return lista_piezas


def ingresar_pistas_celda():
    """
    Solicita al usuario la entrada interactiva de pistas por celda.

    Formato esperado por línea (separado por espacios):
        fila columna suma izquierda derecha arriba abajo

    Donde:
        - fila, columna : int (0..3, 0..4)  → coordenadas de la celda
        - suma          : int  → suma objetivo de los dígitos en esa celda
        - izquierda, derecha, arriba, abajo : int (0..4)
            0   → arista vacía
            1-4 → etiqueta de grupo (misma etiqueta = mismo dígito)

    Devuelve
    --------
    list[tuple]
        Lista de tuplas con los 7 valores ingresados convertidos a enteros.
        El bucle termina cuando el usuario presiona Enter sin escribir nada.
    """
    lista_pistas = []
    print("\n-- Pistas por celda (Enter vacío para terminar) --")
    print("    Formato: fila columna suma izq der arr aba   (0 = vacía, 1-4 = etiqueta de grupo)")
    while (entrada := input("Pista: ").strip()):
        lista_pistas.append(tuple(map(int, entrada.split())))
    return lista_pistas


# ═══════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

while True:
    """
    Bucle principal infinito del programa.

    En cada iteración:
    1. Muestra el título del puzzle.
    2. Imprime las matrices de referencia (mostrar_matrices).
    3. Solicita piezas fijas y pistas de celda al usuario.
    4. Ejecuta el solver con los datos ingresados.
    5. Muestra la solución (si existe) o un mensaje de error.

    El programa no termina automáticamente; el usuario debe interrumpirlo
    con Ctrl+C o cerrar la terminal.
    """
    print("\n               Puzzle IQ Digits\n" + "=" * 45)
    mostrar_matrices()
    solver(
        piezas_fijas=ingresar_piezas_fijas(),
        restricciones_celda=ingresar_pistas_celda(),
    )
