
# IQ Digits Solver con OR-Tools CP-SAT

Proyecto universitario de Inteligencia Artificial que resuelve el rompecabezas *IQ Digits* utilizando **Programación con Restricciones** (CP-SAT de Google OR-Tools).  
El objetivo es colocar los 10 dígitos (0–9) sobre las aristas de una cuadrícula, respetando piezas fijas y pistas de suma en las celdas, de forma que no se solapen y que el tablero cumpla todas las restricciones.

## Reglas del Juego

### 1. Tablero y aristas
- El tablero está formado por **5×5 aristas horizontales** y **4×6 aristas verticales** (total = 25 + 24 = **49 aristas**).
- Las piezas se colocan **sobre las aristas**, no dentro de las celdas.
- Existen **4×5 = 20 celdas** rodeadas por 4 aristas cada una.
- Coordenadas de las aristas: se utiliza una **grilla unificada de 9×11** donde las posiciones `(fila, columna)` con `fila` par representan aristas horizontales y con `fila` impar aristas verticales.  
  Las esquinas `(par, par)` son puntos de cruce sin arista.

> Visualización de las matrices de aristas y celdas:

```text
Matriz de ARISTAS (esquinas superiores‑izquierdas de las piezas):
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

Matriz de CELDAS:
         c=0    c=1    c=2    c=3    c=4
  f=0   [0,0]  [0,1]  [0,2]  [0,3]  [0,4]
  f=1   [1,0]  [1,1]  [1,2]  [1,3]  [1,4]
  f=2   [2,0]  [2,1]  [2,2]  [2,3]  [2,4]
  f=3   [3,0]  [3,1]  [3,2]  [3,3]  [3,4]
```

### 2. Piezas (dígitos 0–9)
- Cada dígito está formado por un conjunto de segmentos (aristas) que ocupan posiciones en la grilla.
- **El dígito “0”** es un cuadrado de 1×1 (4 aristas). Es la única pieza de tamaño reducido.
- Los dígitos 1–9 usan los 7 segmentos clásicos de un display LCD, con diferente número de segmentos activos según el dígito:

| Dígito | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|--------|---|---|---|---|---|---|---|---|---|---|
| Aristas | 4 | 2 | 5 | 5 | 4 | 5 | 6 | 3 | 7 | 6 |

- **Total de aristas ocupadas** = 4+2+5+5+4+5+6+3+7+6 = **47** - Como el tablero tiene 49 aristas, siempre quedan **2 aristas vacías** en cualquier solución válida.

### 3. Transformaciones
- Cada pieza puede colocarse en **4 orientaciones** (rotaciones de 0°, 90°, 180° y 270° en sentido antihorario).  
  *Nota: esta implementación no utiliza reflejos (espejo), únicamente rotaciones.*

### 4. Restricciones de colocación
- **No solapamiento:** una arista del tablero no puede ser ocupada por más de un dígito.
- **Unicidad de dígitos:** cada dígito (0–9) debe aparecer **exactamente una vez**.
- **Piezas fijas (opcional):** el usuario puede pre‑fijar la orientación y la posición de algunos dígitos.
- **Pistas de celda (opcional):** para cada celda se puede definir una **suma objetivo** de los dígitos que tocan esa celda, y forzar que ciertos lados estén ocupados (1) o vacíos (0).  
  *Importante:* un dígito que toca una celda con varias aristas contribuye su valor **una sola vez** a la suma, no multiplicado por el número de aristas.

Formato de una pista:  
`fila columna suma izq der arr aba`  
donde `izq`, `der`, `arr`, `aba` ∈ {0,1} indican si la arista correspondiente debe estar ocupada (1) o vacía (0).  
Ejemplo: `2 3 20 1 1 1 0` → celda (2,3) debe sumar 20, arista de abajo vacía.

- **Solución única:** el juego oficial asegura que solo existe una configuración que cumple todas las condiciones; el solver se detiene al encontrar la primera (o puede verificar unicidad si se desea).

---

## Solver – Modelo CP-SAT

Se utiliza el **solucionador CP-SAT** de Google OR-Tools, que combina programación con restricciones y búsqueda SAT.  
El modelo se construye de la siguiente manera:

### Variables de decisión
Para cada dígito *d* y cada posible *colocación* (orientación + posición en la grilla) se crea una variable booleana:  
`x[d][i] = 1` si el dígito *d* se coloca en la colocación *i*, 0 en caso contrario.

### Restricciones
1. **Exactamente una colocación por dígito**: `sum_i x[d][i] == 1` para cada dígito *d*.
2. **No solapamiento por arista**: para cada arista *e*, la suma de las variables de todos los pares (dígito, colocación) que ocupan esa arista es ≤ 1.
3. **Valor de la arista**: se introduce una variable entera (0–9) que vale el dígito que ocupa la arista, o 0 si está vacía.
4. **Piezas fijas**: se fuerza a 1 la variable de colocación que coincide con la orientación y coordenadas dadas por el usuario (las coordenadas se ingresan en la grilla de aristas y se convierten a la grilla unificada).
5. **Pistas de celda**:  
   - Se fuerza la ocupación/vacío de cada arista perimetral según la pista (si `izq=1`, la arista izquierda debe estar ocupada).  
   - Se calcula para cada dígito si *toca* la celda (al menos una arista de su colocación pertenece a las cuatro aristas de la celda).  
   - La suma de los valores de los dígitos que tocan la celda debe ser igual al objetivo.  
   Como cada dígito se coloca una sola vez, la contribución individual es exactamente su valor (no se multiplica por el número de aristas que comparte con la celda).

### Búsqueda
- Se emplean **8 workers en paralelo** (`solver.parameters.num_search_workers = 8`) para acelerar la exploración.
- El solver se detiene en la primera solución factible (estado `OPTIMAL` o `FEASIBLE`).  
- Si no existe solución, se informa al usuario.

---

## Uso del programa

### Requisitos
- Python 3.7+
- [OR-Tools](https://developers.google.com/optimization) (`pip install ortools`)
- NumPy (`pip install numpy`)

### Ejecución
```bash
python iq_digits_solver.py
```

### Interfaz interactiva
Al iniciar, se muestran las matrices de referencia de aristas y celdas. Luego se solicitan secuencialmente:

- **Piezas fijas** Se ingresa:
  1. Dígito (0‑9)
  2. Disposición (0‑3, ver tabla de rotaciones)
  3. Fila y columna del **corner superior‑izquierdo** de la pieza (según la matriz de aristas mostrada).  
  Para terminar, dejar vacío el campo del dígito.

- **Pistas de celda** Formato: `fila columna suma izq der arr aba`  
  Para terminar, dejar vacía la línea.

A continuación el solver busca una solución y, si la encuentra, imprime el tablero resuelto visualmente.

> *Nota:* Se puede omitir completamente la entrada de piezas fijas (solo pistas) o viceversa, adaptándose al escenario deseado.

### Ejemplo de entrada (solo con pistas)
```text
── Piezas fijas (Enter vacío para terminar) ──
Dígito (0-9): 
── Pistas por celda (Enter vacío para terminar) ──
Pista: 0 0 12 1 1 1 0
Pista: 
```
(Se especifica que la celda (0,0) sume 12, con las aristas izquierda, derecha y superior ocupadas, inferior vacía.)

### Salida esperada
Un tablero de 9×11 caracteres donde:
- `+` : esquina
- `─` : arista horizontal (con dígito si ocupada, `·` si vacía)
- `│` : arista vertical (con dígito si ocupada, `·` si vacía)

Ejemplo (ficticio):
```text
+ 1 ─ 2 ─ + · ─ · ─ +
│      │      │      │
... etc ...
```

---

## Estructura del código

El script se organiza en las siguientes partes:

| Función / Bloque | Descripción |
|------------------|-------------|
| `DIGITOS_DICCIONARIO` | Plantillas binarias de cada dígito en la grilla unificada. |
| `indice_arista(i, j)` | Convierte coordenadas de la grilla unificada al índice lineal de arista (0‑48). |
| `calcular_orientaciones()` | Genera las 4 rotaciones de una plantilla. |
| `construir_colocaciones()` | Para cada dígito, calcula todas las colocaciones válidas (orientación, posición, lista de aristas que ocupa). |
| `solver(piezas_fijas, restricciones_celda)` | Construye y resuelve el modelo CP-SAT. |
| `mostrar_solucion(solver, x, P)` | Extrae la solución y dibuja el tablero en ASCII. |
| `mostrar_matrices()` | Imprime las matrices de referencia para el usuario. |
| `ingresar_piezas_fijas()` / `ingresar_pistas_celda()` | Lectura interactiva de datos. |
| Bloque `main` | Bucle principal que orquesta la entrada y la resolución. |

---

## Posibles extensiones (trabajo futuro)
- Añadir un menú numérico (opciones 1‑4) para elegir entre “sólo piezas fijas”, “sólo pistas”, “ambas” o “mostrar matrices”.
- Incluir reflejos (espejo) además de rotaciones, para explorar completamente el espacio de simetrías.
- Verificar la unicidad de la solución (seguir buscando después de la primera factible).
- Exportar la solución en formato gráfico o como JSON.
- Interfaz gráfica simple con Pygame o Tkinter.

---

## Referencias
- [OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver)
- Rompecabezas *IQ Digits* de SmartGames.
- Documentación de NumPy.

---

*Proyecto realizado en el contexto de la asignatura de Inteligencia Artificial – Resolución de problemas mediante búsqueda con restricciones.*
