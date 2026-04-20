"""
IQ Digits solver — CSP con OR-Tools CP-SAT y NumPy.
Incluye servidor Flask para comunicación con el frontend HTML.
"""

from __future__ import annotations
import json, sys
import numpy as np
from ortools.sat.python import cp_model
from flask import Flask, request, jsonify
from flask_cors import CORS

# ---------------------------------------------------------------------------
# 1.  Definicion de las piezas (dígitos 0..9)
# ---------------------------------------------------------------------------
DIGIT_SEGMENTS = {
    0: [('H', 0, 0), ('H', 1, 0), ('V', 0, 0), ('V', 0, 1)],
    1: [('V', 0, 1), ('V', 1, 1)],
    2: [('H', 0, 0), ('V', 0, 1), ('H', 1, 0), ('V', 1, 0), ('H', 2, 0)],
    3: [('H', 0, 0), ('V', 0, 1), ('H', 1, 0), ('V', 1, 1), ('H', 2, 0)],
    4: [('V', 0, 0), ('H', 1, 0), ('V', 0, 1), ('V', 1, 1)],
    5: [('H', 0, 0), ('V', 0, 0), ('H', 1, 0), ('V', 1, 1), ('H', 2, 0)],
    6: [('H', 0, 0), ('V', 0, 0), ('H', 1, 0), ('V', 1, 0), ('V', 1, 1), ('H', 2, 0)],
    7: [('H', 0, 0), ('V', 0, 1), ('V', 1, 1)],
    8: [('H', 0, 0), ('V', 0, 0), ('V', 0, 1), ('H', 1, 0),
        ('V', 1, 0), ('V', 1, 1), ('H', 2, 0)],
    9: [('H', 0, 0), ('V', 0, 0), ('V', 0, 1), ('H', 1, 0),
        ('V', 1, 1), ('H', 2, 0)],
}

H_ROWS, H_COLS = 5, 5
V_ROWS, V_COLS = 4, 6
NODES_R, NODES_C = 5, 6

# ---------------------------------------------------------------------------
# 2.  Utilidades numpy
# ---------------------------------------------------------------------------

def segments_to_arrays(segs):
    hs = [(r, c) for t, r, c in segs if t == 'H']
    vs = [(r, c) for t, r, c in segs if t == 'V']
    max_hr = max((r for r, _ in hs), default=-1)
    max_hc = max((c for _, c in hs), default=-1)
    max_vr = max((r for r, _ in vs), default=-1)
    max_vc = max((c for _, c in vs), default=-1)
    node_rows = max(max_hr, max_vr + 1) + 1
    node_cols = max(max_hc + 1, max_vc) + 1
    H = np.zeros((node_rows, node_cols - 1), bool)
    V = np.zeros((node_rows - 1, node_cols), bool)
    for r, c in hs: H[r, c] = True
    for r, c in vs: V[r, c] = True
    return H, V


def rotate90(H, V):
    nr = H.shape[0]
    nc = H.shape[1] + 1
    H_new = np.zeros((nc, nr - 1), bool)
    V_new = np.zeros((nc - 1, nr), bool)
    for r in range(V.shape[0]):
        for c in range(V.shape[1]):
            if V[r, c]: H_new[c, nr - 2 - r] = True
    for r in range(H.shape[0]):
        for c in range(H.shape[1]):
            if H[r, c]: V_new[c, nr - 1 - r] = True
    return H_new, V_new


def mirror_h(H, V):
    return H[:, ::-1].copy(), V[:, ::-1].copy()


def canonical(H, V):
    return (H.shape, V.shape, H.tobytes(), V.tobytes())


def all_orientations(H, V):
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
# 3.  Enumeracion de colocaciones
# ---------------------------------------------------------------------------

def enumerate_placements(digit):
    H0, V0 = segments_to_arrays(DIGIT_SEGMENTS[digit])
    placements, seen_global = [], set()
    for H, V in all_orientations(H0, V0):
        hr, hc = H.shape
        vr, vc = V.shape
        node_rows, node_cols = hr, vc
        for dr in range(NODES_R - node_rows + 1):
            for dc in range(NODES_C - node_cols + 1):
                edges, ok = set(), True
                rs, cs = np.nonzero(H)
                for r, c in zip(rs, cs):
                    gr, gc = r + dr, c + dc
                    if not (0 <= gr < H_ROWS and 0 <= gc < H_COLS):
                        ok = False; break
                    edges.add(('H', int(gr), int(gc)))
                if not ok: continue
                rs, cs = np.nonzero(V)
                for r, c in zip(rs, cs):
                    gr, gc = r + dr, c + dc
                    if not (0 <= gr < V_ROWS and 0 <= gc < V_COLS):
                        ok = False; break
                    edges.add(('V', int(gr), int(gc)))
                if not ok: continue
                key = frozenset(edges)
                if key in seen_global: continue
                seen_global.add(key)
                placements.append(key)
    return placements


# ---------------------------------------------------------------------------
# 4.  Modelo CP-SAT
# ---------------------------------------------------------------------------

def solve(fixed=None, hints=None, cell_hints=None, cover_all=False, verbose=True):
    fixed = fixed or {}
    hints = hints or []
    cell_hints = cell_hints or []
    model = cp_model.CpModel()

    all_placements = {d: enumerate_placements(d) for d in range(10)}

    for d, edges in fixed.items():
        cand = [p for p in all_placements[d] if p == edges]
        if not cand:
            raise ValueError(f"Colocación fija inválida para el dígito {d}")
        all_placements[d] = cand

    x = {d: [model.NewBoolVar(f"x_{d}_{i}") for i in range(len(ps))]
         for d, ps in all_placements.items()}

    for d in range(10):
        model.AddExactlyOne(x[d])

    edge_users = {}
    for d, ps in all_placements.items():
        for i, edges in enumerate(ps):
            for e in edges:
                edge_users.setdefault(e, []).append((x[d][i], d))

    for e, users in edge_users.items():
        if cover_all:
            model.AddExactlyOne([v for v, _ in users])
        else:
            model.AddAtMostOne([v for v, _ in users])

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

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if verbose: print("Sin solución.")
        return None

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
# 5.  Serialización JSON para el frontend
# ---------------------------------------------------------------------------

def result_to_json(result):
    """Convierte el resultado del solver a formato JSON para el frontend."""
    if result is None:
        return {"status": "no_solution"}
    data = {"status": "solved", "placements": {}}
    for d, edges in result.items():
        data["placements"][str(d)] = [list(e) for e in sorted(edges)]
    return data


def frozenset_from_json(edges_list):
    """Convierte lista JSON [['H',r,c], ...] a frozenset de tuplas."""
    return frozenset(tuple(e) for e in edges_list)


# ---------------------------------------------------------------------------
# 6.  Renderizado ASCII
# ---------------------------------------------------------------------------

def render(result, hints=None, cell_hints=None):
    em = {e: d for d, edges in result.items() for e in edges}
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
            for k in range(1, 4): grid[r * 2, c * 4 + k] = ch
    for r in range(V_ROWS):
        for c in range(V_COLS):
            d = em.get(('V', r, c))
            ch = str(d) if d is not None else '│'
            grid[r * 2 + 1, c * 4] = ch
    if hints:
        for nr, nc, val in hints:
            if len(str(val)) == 1: grid[nr * 2, nc * 4] = str(val)
    if cell_hints:
        for cr, cc, val in cell_hints:
            if len(str(val)) == 1: grid[cr * 2 + 1, cc * 4 + 2] = str(val)
    print('\n'.join(''.join(row) for row in grid))
    print()
    for d, edges in sorted(result.items()):
        print(f"  dígito {d} ({len(edges)} aristas): {sorted(edges)}")


# ---------------------------------------------------------------------------
# 7.  Servidor Flask API
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)


@app.route('/api/solve', methods=['POST'])
def api_solve():
    """
    Recibe JSON con:
    {
      "fixed": {"0": [["H",r,c], ...], ...},
      "hints": [[nr, nc, val], ...],
      "cell_hints": [[cr, cc, val], ...],
      "cover_all": false
    }
    Devuelve JSON con la solución o error.
    """
    try:
        body = request.get_json(force=True)
        fixed_raw = body.get("fixed", {})
        fixed = {int(k): frozenset_from_json(v) for k, v in fixed_raw.items()}
        hints = [tuple(h) for h in body.get("hints", [])]
        cell_hints = [tuple(h) for h in body.get("cell_hints", [])]
        cover_all = body.get("cover_all", False)

        result = solve(fixed=fixed, hints=hints, cell_hints=cell_hints,
                       cover_all=cover_all, verbose=False)
        return jsonify(result_to_json(result))
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/placements/<int:digit>', methods=['GET'])
def api_placements(digit):
    """Devuelve todas las colocaciones válidas de un dígito."""
    if not 0 <= digit <= 9:
        return jsonify({"error": "Dígito inválido"}), 400
    places = enumerate_placements(digit)
    return jsonify({
        "digit": digit,
        "count": len(places),
        "placements": [[list(e) for e in sorted(p)] for p in places]
    })


@app.route('/api/validate', methods=['POST'])
def api_validate():
    """
    Valida si una configuración parcial es factible (sin resolver completamente).
    Recibe el mismo formato que /api/solve.
    Devuelve {"valid": true/false, "message": "..."}.
    """
    try:
        body = request.get_json(force=True)
        fixed_raw = body.get("fixed", {})
        hints = [tuple(h) for h in body.get("hints", [])]
        cell_hints = [tuple(h) for h in body.get("cell_hints", [])]

        # Verificar solapamiento entre piezas fijas
        used_edges = {}
        for k, edges_list in fixed_raw.items():
            d = int(k)
            for e in edges_list:
                key = tuple(e)
                if key in used_edges:
                    return jsonify({
                        "valid": False,
                        "message": f"Solapamiento: arista {key} usada por dígitos {used_edges[key]} y {d}"
                    })
                used_edges[key] = d

        # Verificar límites del tablero
        for key, d in used_edges.items():
            t, r, c = key
            if t == 'H' and not (0 <= r < H_ROWS and 0 <= c < H_COLS):
                return jsonify({"valid": False, "message": f"Arista H({r},{c}) fuera del tablero"})
            if t == 'V' and not (0 <= r < V_ROWS and 0 <= c < V_COLS):
                return jsonify({"valid": False, "message": f"Arista V({r},{c}) fuera del tablero"})

        # Verificar restricciones de suma si hay hints
        violations = []
        for nr, nc, S in hints:
            inc = []
            if 0 <= nr < NODES_R and 0 <= nc - 1 < H_COLS: inc.append(('H', nr, nc - 1))
            if 0 <= nr < NODES_R and 0 <= nc < H_COLS: inc.append(('H', nr, nc))
            if 0 <= nr - 1 < V_ROWS and 0 <= nc < V_COLS: inc.append(('V', nr - 1, nc))
            if 0 <= nr < V_ROWS and 0 <= nc < V_COLS: inc.append(('V', nr, nc))
            digits_touching = set()
            for e in inc:
                if tuple(e) in used_edges:
                    digits_touching.add(used_edges[tuple(e)])
            if digits_touching:
                current_sum = sum(digits_touching)
                if current_sum > S:
                    violations.append(f"Nodo ({nr},{nc}): suma {current_sum} > {S}")

        if violations:
            return jsonify({"valid": False, "message": "; ".join(violations)})

        return jsonify({"valid": True, "message": "Configuración válida"})
    except Exception as e:
        return jsonify({"valid": False, "message": str(e)}), 500


@app.route('/api/info', methods=['GET'])
def api_info():
    return jsonify({
        "board": {"H_ROWS": H_ROWS, "H_COLS": H_COLS, "V_ROWS": V_ROWS, "V_COLS": V_COLS,
                  "NODES_R": NODES_R, "NODES_C": NODES_C},
        "digits": list(range(10)),
        "segment_counts": {d: len(DIGIT_SEGMENTS[d]) for d in range(10)}
    })


# ---------------------------------------------------------------------------
# 8.  CLI main()
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
        if not s: break
        try:
            a, b, v = map(int, s.split())
            hints.append((a, b, v))
        except ValueError:
            print("    Formato inválido. Usa: fila col valor")
    return hints


def _input_fixed():
    fixed = {}
    print("Fijar piezas. Línea vacía para terminar.")
    while True:
        s = input("  Dígito a fijar (0-9) o ENTER: ").strip()
        if not s: break
        try:
            d = int(s)
            if not 0 <= d <= 9: continue
        except ValueError:
            continue
        places = enumerate_placements(d)
        print(f"    {len(places)} colocaciones disponibles para el dígito {d}.")
        idx = _read_int("    Índice (0..N-1): ", 0, len(places) - 1)
        fixed[d] = places[idx]
    return fixed


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5050
        print(f"🚀 IQ Digits API server en http://localhost:{port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        return

    while True:
        print("\n=== IQ Digits Solver (CP-SAT) ===")
        print(" 1) Resolver reto por defecto (sin pistas)")
        print(" 2) Resolver con piezas fijas")
        print(" 3) Resolver con pistas por nodo")
        print(" 4) Resolver con pistas por celda")
        print(" 5) Resolver combinando fijas + pistas")
        print(" 6) Mostrar colocaciones por dígito (cantidad)")
        print(" 7) Mostrar primeras colocaciones de un dígito")
        print(" 8) Iniciar servidor web (API REST)")
        print(" 0) Salir")
        op = input("Opción: ").strip()
        if op == '0':
            break
        elif op == '1':
            solve(cover_all=False)
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
        elif op == '8':
            port = _read_int("Puerto (default 5050): ", 1024, 65535) if input("¿Puerto personalizado? (s/n): ").strip().lower() == 's' else 5050
            print(f"🚀 Servidor en http://localhost:{port}")
            app.run(host='0.0.0.0', port=port, debug=False)
        else:
            print("Opción inválida.")


if __name__ == '__main__':
    main()
