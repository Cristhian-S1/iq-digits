"""Núcleo del solver: modelo CP-SAT, renderizado ASCII y serialización JSON."""

import numpy as np
from ortools.sat.python import cp_model

from .pieces import H_ROWS, H_COLS, V_ROWS, V_COLS, NODES_R, NODES_C
from .placements import enumerate_placements


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
        if verbose:
            print("Sin solución.")
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
            for k in range(1, 4):
                grid[r * 2, c * 4 + k] = ch
    for r in range(V_ROWS):
        for c in range(V_COLS):
            d = em.get(('V', r, c))
            ch = str(d) if d is not None else '│'
            grid[r * 2 + 1, c * 4] = ch
    if hints:
        for nr, nc, val in hints:
            if len(str(val)) == 1:
                grid[nr * 2, nc * 4] = str(val)
    if cell_hints:
        for cr, cc, val in cell_hints:
            if len(str(val)) == 1:
                grid[cr * 2 + 1, cc * 4 + 2] = str(val)
    print('\n'.join(''.join(row) for row in grid))
    print()
    for d, edges in sorted(result.items()):
        print(f"  dígito {d} ({len(edges)} aristas): {sorted(edges)}")


def result_to_json(result):
    if result is None:
        return {"status": "no_solution"}
    data = {"status": "solved", "placements": {}}
    for d, edges in result.items():
        data["placements"][str(d)] = [list(e) for e in sorted(edges)]
    return data


def frozenset_from_json(edges_list):
    return frozenset(tuple(e) for e in edges_list)
