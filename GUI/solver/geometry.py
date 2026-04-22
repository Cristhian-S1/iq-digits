"""Utilidades numpy para transformar segmentos: rotación, reflexión y orientaciones."""

import numpy as np


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
    for r, c in hs:
        H[r, c] = True
    for r, c in vs:
        V[r, c] = True
    return H, V


def rotate90(H, V):
    nr = H.shape[0]
    nc = H.shape[1] + 1
    H_new = np.zeros((nc, nr - 1), bool)
    V_new = np.zeros((nc - 1, nr), bool)
    for r in range(V.shape[0]):
        for c in range(V.shape[1]):
            if V[r, c]:
                H_new[c, nr - 2 - r] = True
    for r in range(H.shape[0]):
        for c in range(H.shape[1]):
            if H[r, c]:
                V_new[c, nr - 1 - r] = True
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
