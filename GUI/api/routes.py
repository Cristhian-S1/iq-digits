"""Servidor Flask: endpoints REST para comunicación con el frontend."""

from flask import Flask, request, jsonify
from flask_cors import CORS

from core.core import solve, result_to_json, frozenset_from_json
from core.pieces import H_ROWS, H_COLS, V_ROWS, V_COLS, NODES_R, NODES_C
from core.placements import enumerate_placements

app = Flask(__name__)
CORS(app)


@app.route('/api/solve', methods=['POST'])
def api_solve():
    """
    Recibe JSON con:
    {
      "fixed": {"0": [["H",r,c], ...], ...},
      "cell_hints": [[cr, cc, val], ...],
      "cover_all": false
    }
    Devuelve JSON con la solución o error.
    """
    try:
        body = request.get_json(force=True)
        fixed_raw = body.get("fixed", {})
        fixed = {int(k): frozenset_from_json(v) for k, v in fixed_raw.items()}
        cell_hints = [tuple(h) for h in body.get("cell_hints", [])]
        cover_all = body.get("cover_all", False)

        result = solve(fixed=fixed, cell_hints=cell_hints,
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

        for key, d in used_edges.items():
            t, r, c = key
            if t == 'H' and not (0 <= r < H_ROWS and 0 <= c < H_COLS):
                return jsonify({"valid": False, "message": f"Arista H({r},{c}) fuera del tablero"})
            if t == 'V' and not (0 <= r < V_ROWS and 0 <= c < V_COLS):
                return jsonify({"valid": False, "message": f"Arista V({r},{c}) fuera del tablero"})

        return jsonify({"valid": True, "message": "Configuración válida"})
    except Exception as e:
        return jsonify({"valid": False, "message": str(e)}), 500


@app.route('/api/info', methods=['GET'])
def api_info():
    return jsonify({
        "board": {
            "H_ROWS": H_ROWS, "H_COLS": H_COLS,
            "V_ROWS": V_ROWS, "V_COLS": V_COLS,
            "NODES_R": NODES_R, "NODES_C": NODES_C,
        },
        "digits": list(range(10)),
        "segment_counts": {},
    })
