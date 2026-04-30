# IQ Digits Solver con OR-Tools CP-SAT

Proyecto universitario de Inteligencia Artificial que resuelve el rompecabezas *IQ Digits* utilizando **Programación con Restricciones** (CP-SAT de Google OR-Tools).
El objetivo es colocar los 10 dígitos (0–9) sobre las aristas de una cuadrícula, respetando piezas fijas y pistas por celda, de forma que no se solapen y que el tablero cumpla todas las restricciones.

---

## Reglas del juego

### 1. Tablero y aristas

- El tablero está formado por **5×5 aristas horizontales** y **4×6 aristas verticales** (total = 25 + 24 = **49 aristas**).
- Las piezas se colocan **sobre las aristas**, no dentro de las celdas.
- Existen **4×5 = 20 celdas** rodeadas por 4 aristas cada una.
- Coordenadas de las aristas: se utiliza una **grilla unificada de 9×11** donde las posiciones `(fila, columna)` con `fila` par representan aristas horizontales y con `fila` impar aristas verticales. Las esquinas `(par, par)` son puntos de cruce sin arista.

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

- El **dígito 0** es un cuadrado 1×1 (4 aristas).
- Los dígitos 1–9 usan los 7 segmentos clásicos de un display LCD:

| Dígito | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|--------|---|---|---|---|---|---|---|---|---|---|
| Aristas | 4 | 2 | 5 | 5 | 4 | 5 | 6 | 3 | 7 | 6 |

- **Total de aristas ocupadas** = 47. Como el tablero tiene 49, en cualquier solución válida quedan **2 aristas vacías**.

### 3. Transformaciones

- Cada pieza puede colocarse en **4 orientaciones** (rotaciones 0°, 90°, 180° y 270° en sentido antihorario). No se utilizan reflejos.

### 4. Restricciones de colocación

- **No solapamiento:** una arista no puede ser ocupada por más de un dígito.
- **Unicidad:** cada dígito (0–9) aparece exactamente una vez.
- **Piezas fijas (opcional):** el usuario puede pre‑fijar la orientación y la posición de algunos dígitos.
- **Pistas por celda (opcional):** ver sección siguiente.

---

## Pistas por celda — etiquetas de grupo

Una pista describe **qué pasa en las 4 aristas que rodean una celda**. Cada arista lleva un número en `{0, 1, 2, 3, 4}`:

| Valor | Significado |
|-------|-------------|
| `0` | La arista debe estar **vacía** |
| `1..4` | **Etiqueta de grupo**. Aristas con la misma etiqueta deben ser cubiertas por **el mismo dígito**; aristas con etiquetas distintas deben ser cubiertas por **dígitos distintos** |

La **suma** indicada en la pista es la suma de los dígitos que tocan la celda (un dígito por grupo, no por arista).

### Formato

```
fila columna suma izq der arr aba
```

### Ejemplos

| Entrada | Interpretación |
|---------|----------------|
| `0 0 8 1 1 1 1` | Las 4 aristas alrededor de la celda (0,0) ocupadas por **un mismo dígito** que vale 8 (es decir, el 8) |
| `0 0 0 1 1 1 1` | Las 4 aristas por un mismo dígito que vale 0 (es decir, el cuadradito 0) |
| `1 1 18 1 2 3 4` | 4 dígitos **distintos**, uno en cada arista, sumando 18 |
| `2 2 10 1 2 2 2` | Izquierda con un dígito; arr/der/aba con **otro** dígito que cubre las 3 |
| `0 1 9 1 2 1 2` | Izq y arr por un dígito; der y aba por otro distinto. Suma = 9 |

> **Nota:** el usuario puede ingresar combinaciones imposibles (por ejemplo `1 2 3 3`, donde la izquierda y la derecha deberían ser distintas pero la arr y la aba iguales — geométricamente sin sentido). El programa no valida estas entradas; simplemente reportará "No hay solución".

---

## Modelo CP-SAT

### Variables de decisión

Para cada dígito *d* y cada *colocación* (orientación + posición) se crea una variable booleana:
`variables_decision[d][i] = 1` si el dígito *d* se coloca en la *i*‑ésima colocación.

### Restricciones globales

1. **Una colocación por dígito**: `AddExactlyOne(variables_decision[d])` para cada *d*.
2. **No solapamiento**: en cada arista, la suma de booleanos que la cubren es ≤ 1.
3. **Piezas fijas**: se fuerza a 1 la variable de la colocación indicada.

### Restricciones por celda (etiquetas de grupo)

Para cada pista:

1. **Ocupación**: cada arista vacía (etiqueta 0) tiene suma de cobertura == 0; cada arista con etiqueta no nula tiene suma == 1.
2. **Agrupación**: las aristas se agrupan por etiqueta. Para cada grupo se crea una `IntVar` `digito_grupo ∈ {0..9}` que toma el valor del dígito que cubre el grupo.
3. **Mismo dígito por grupo**: para cada arista del grupo se fuerza `digito_grupo == sum(d * var_bool for d, var_bool in cobertura_aristas[arista])`. Como cada dígito se coloca una sola vez, todas las aristas del grupo terminan cubiertas por el mismo dígito.
4. **Dígitos distintos entre grupos**: `AddAllDifferent(digitos_grupos)`.
5. **Suma**: `sum(digitos_grupos) == suma_objetivo`.

### Búsqueda

- 8 workers en paralelo (`solver.parameters.num_search_workers = 8`).
- Se detiene en la primera solución factible.

---

## Optimizaciones aplicadas

A lo largo del desarrollo se redujeron significativamente las líneas de código sin perder funcionalidad. Las decisiones clave fueron:

1. **`IntVar` por grupo en vez de `BoolVar` por (grupo, dígito)**. En lugar de mantener una matriz de 10 booleanos por grupo (uno indicando "este grupo está cubierto por el dígito *d*"), se usa **una sola variable entera** que es directamente el dígito. Esto convierte el "dígitos distintos entre grupos" en un único `AddAllDifferent` global, en vez de un triple `for` con restricciones `<= 1` por par.

2. **Eliminación de `valores_aristas`**. Las `IntVar` por arista existían sólo para la suma del modelo viejo (suma de las 4 aristas con repetición). Con la nueva semántica, esa información ya está dentro de `digito_grupo`, así que se eliminaron por completo.

3. **`construir_colocaciones` como dict-comprehension**. Las cuatro variables anidadas (dígito → orientación → fila → columna) caben en una sola expresión gracias a que en una *comprehension* de Python cada cláusula `for` posterior puede referenciar variables de las anteriores (por ejemplo, `plantilla.shape` se usa dentro del `range` de `fila`).

4. **`mostrar_solucion` con array lineal**. En lugar de mantener dos matrices `(5×5)` y `(4×6)` con valores `-1/dígito` y luego convertirlas a strings con `np.where`, se usa un único array de 49 caracteres (`'·'` o el dígito) y se hace `reshape` al final.

5. **`next(...)` con generador para piezas fijas** en vez del patrón `for`/`break` con flag `encontrado`.

6. **Walrus operator `:=`** en los bucles de entrada para fusionar lectura y condición.

---

## Uso del programa

### Requisitos

- Python 3.8+
- [OR-Tools](https://developers.google.com/optimization) (`pip install ortools`)
- NumPy (`pip install numpy`)

### Ejecución

```bash
python main.py
```

### Interfaz interactiva

Al iniciar se muestran las matrices de referencia. Luego se solicita:

1. **Piezas fijas**: dígito (0‑9), disposición (0‑3) y fila/columna del corner superior‑izquierdo. Enter vacío para terminar.
2. **Pistas por celda**: una línea con el formato `fila columna suma izq der arr aba`. Enter vacío para terminar.

Si se quiere omitir alguna sección, sólo presionar Enter directamente.

### Salida esperada

Un tablero de 9×11 caracteres donde:

- `+` : esquina
- dígito o `·` : arista (ocupada / vacía)

```text
+ 8 + 4 + 4 + 6 + 7 +
8   8   4   6   ·   7
+ 8 + 4 + 5 + 6 + · +
8   8   5   6   6   7
+ 8 + 9 + 5 + 6 + 0 +
9   9   9   5   0   0
+ 9 + 9 + 5 + 2 + 0 +
3   3   3   2   2   2
+ 3 + 3 + 1 + 1 + 2 +
```

---

## Estructura del código

| Función / Bloque | Descripción |
|------------------|-------------|
| `DIGITOS_DICCIONARIO` | Plantillas binarias de cada dígito en la grilla unificada. |
| `indice_arista(fila, columna)` | Convierte coordenadas de la grilla unificada al índice lineal de arista (0‑48). |
| `construir_colocaciones()` | Para cada dígito, calcula todas las colocaciones válidas (orientación, posición, lista de aristas). |
| `solver(piezas_fijas, restricciones_celda)` | Construye y resuelve el modelo CP-SAT. |
| `mostrar_solucion(...)` | Extrae la solución y dibuja el tablero en ASCII. |
| `mostrar_matrices()` | Imprime las matrices de referencia para el usuario. |
| `ingresar_piezas_fijas()` / `ingresar_pistas_celda()` | Lectura interactiva de datos. |
| Bloque `main` | Bucle principal que orquesta la entrada y la resolución. |

---

## Posibles extensiones

- Verificar la unicidad de la solución (seguir buscando después de la primera factible).
- Incluir reflejos además de rotaciones para explorar el espacio completo de simetrías.
- Exportar la solución en formato gráfico o como JSON.
- Interfaz gráfica con Pygame o Tkinter.

---

## Referencias

- [OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver)
- Rompecabezas *IQ Digits* de SmartGames.

---

*Proyecto realizado en el contexto de la asignatura de Inteligencia Artificial — Resolución de problemas mediante búsqueda con restricciones.*
