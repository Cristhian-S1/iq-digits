"""Enumeración de todas las colocaciones válidas de cada dígito en el tablero."""

import numpy as np

from .geometry import segments_to_arrays, all_orientations
from .pieces import DIGIT_SEGMENTS, H_ROWS, H_COLS, V_ROWS, V_COLS, NODES_R, NODES_C


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
                        ok = False
                        break
                    edges.add(('H', int(gr), int(gc)))
                if not ok:
                    continue
                rs, cs = np.nonzero(V)
                for r, c in zip(rs, cs):
                    gr, gc = r + dr, c + dc
                    if not (0 <= gr < V_ROWS and 0 <= gc < V_COLS):
                        ok = False
                        break
                    edges.add(('V', int(gr), int(gc)))
                if not ok:
                    continue
                key = frozenset(edges)
                if key in seen_global:
                    continue
                seen_global.add(key)
                placements.append(key)
    return placements
