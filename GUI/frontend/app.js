// ============================================================
// CONSTANTS
// ============================================================
const H_ROWS = 5,
  H_COLS = 5;
const V_ROWS = 4,
  V_COLS = 6;
const NODES_R = 5,
  NODES_C = 6;

const CELL_SIZE = 90;
const PAD = 20;
const SVG_W = (NODES_C - 1) * CELL_SIZE + PAD * 2;
const SVG_H = (NODES_R - 1) * CELL_SIZE + PAD * 2;

const DIGIT_COLORS = [
  "#00e5ff",
  "#ff6b35",
  "#39ff14",
  "#ff3f96",
  "#ffd600",
  "#a07cff",
  "#00bfa5",
  "#ff8a00",
  "#e040fb",
  "#b8ff03",
];

// ============================================================
// DIGIT SEGMENT DEFINITIONS (local coords)
// ============================================================
const DIGIT_SEGMENTS = {
  0: [
    ["H", 0, 0],
    ["H", 1, 0],
    ["V", 0, 0],
    ["V", 0, 1],
  ],
  1: [
    ["V", 0, 1],
    ["V", 1, 1],
  ],
  2: [
    ["H", 0, 0],
    ["V", 0, 1],
    ["H", 1, 0],
    ["V", 1, 0],
    ["H", 2, 0],
  ],
  3: [
    ["H", 0, 0],
    ["V", 0, 1],
    ["H", 1, 0],
    ["V", 1, 1],
    ["H", 2, 0],
  ],
  4: [
    ["V", 0, 0],
    ["H", 1, 0],
    ["V", 0, 1],
    ["V", 1, 1],
  ],
  5: [
    ["H", 0, 0],
    ["V", 0, 0],
    ["H", 1, 0],
    ["V", 1, 1],
    ["H", 2, 0],
  ],
  6: [
    ["H", 0, 0],
    ["V", 0, 0],
    ["H", 1, 0],
    ["V", 1, 0],
    ["V", 1, 1],
    ["H", 2, 0],
  ],
  7: [
    ["H", 0, 0],
    ["V", 0, 1],
    ["V", 1, 1],
  ],
  8: [
    ["H", 0, 0],
    ["V", 0, 0],
    ["V", 0, 1],
    ["H", 1, 0],
    ["V", 1, 0],
    ["V", 1, 1],
    ["H", 2, 0],
  ],
  9: [
    ["H", 0, 0],
    ["V", 0, 0],
    ["V", 0, 1],
    ["H", 1, 0],
    ["V", 1, 1],
    ["H", 2, 0],
  ],
};

// ============================================================
// SEGMENT TRANSFORMATIONS
// ============================================================
function segsToArrays(segs) {
  let hs = segs.filter((s) => s[0] === "H").map((s) => [s[1], s[2]]);
  let vs = segs.filter((s) => s[0] === "V").map((s) => [s[1], s[2]]);
  let maxHR = hs.length ? Math.max(...hs.map((s) => s[0])) : -1;
  let maxHC = hs.length ? Math.max(...hs.map((s) => s[1])) : -1;
  let maxVR = vs.length ? Math.max(...vs.map((s) => s[0])) : -1;
  let maxVC = vs.length ? Math.max(...vs.map((s) => s[1])) : -1;
  let nR = Math.max(maxHR, maxVR + 1) + 1;
  let nC = Math.max(maxHC + 1, maxVC) + 1;
  let H = Array.from({ length: nR }, () => Array(nC - 1).fill(false));
  let V = Array.from({ length: nR - 1 }, () => Array(nC).fill(false));
  hs.forEach(([r, c]) => {
    if (r < nR && c < nC - 1) H[r][c] = true;
  });
  vs.forEach(([r, c]) => {
    if (r < nR - 1 && c < nC) V[r][c] = true;
  });
  return { H, V, nR, nC };
}

function rotate90(H, V) {
  let nr = H.length,
    nc = H[0].length + 1;
  let H2 = Array.from({ length: nc }, () => Array(nr - 1).fill(false));
  let V2 = Array.from({ length: nc - 1 }, () => Array(nr).fill(false));
  for (let r = 0; r < V.length; r++)
    for (let c = 0; c < V[0].length; c++) if (V[r][c]) H2[c][nr - 2 - r] = true;
  for (let r = 0; r < H.length; r++)
    for (let c = 0; c < H[0].length; c++) if (H[r][c]) V2[c][nr - 1 - r] = true;
  return { H: H2, V: V2 };
}

function mirrorH(H, V) {
  return {
    H: H.map((row) => [...row].reverse()),
    V: V.map((row) => [...row].reverse()),
  };
}

function arraysToSegs(H, V, dr, dc) {
  let segs = [];
  for (let r = 0; r < H.length; r++)
    for (let c = 0; c < H[0].length; c++)
      if (H[r][c]) segs.push(["H", r + dr, c + dc]);
  for (let r = 0; r < V.length; r++)
    for (let c = 0; c < V[0].length; c++)
      if (V[r][c]) segs.push(["V", r + dr, c + dc]);
  return segs;
}

function arraysKey(H, V) {
  return JSON.stringify({ H, V });
}

function allOrientations(digit) {
  let { H, V } = segsToArrays(DIGIT_SEGMENTS[digit]);
  let seen = new Set(),
    out = [];
  let cur = { H, V };
  for (let rot = 0; rot < 4; rot++) {
    for (let m = 0; m < 2; m++) {
      let variant = m === 0 ? cur : mirrorH(cur.H, cur.V);
      let key = arraysKey(variant.H, variant.V);
      if (!seen.has(key)) {
        seen.add(key);
        out.push(variant);
      }
    }
    cur = rotate90(cur.H, cur.V);
  }
  return out;
}

// ============================================================
// STATE
// ============================================================
const state = {
  mode: "place",
  selectedDigit: null,
  orientIdx: 0,
  orientations: [],
  placed: {},
  fixed: {},
  hintNodes: [],
  hintCells: [],
  pendingHintNode: null,
  pendingHintCell: null,
};

// ============================================================
// SVG BOARD
// ============================================================
const svg = document.getElementById("board-svg");
svg.setAttribute("viewBox", `0 0 ${SVG_W} ${SVG_H}`);

function nodeXY(r, c) {
  return { x: PAD + c * CELL_SIZE, y: PAD + r * CELL_SIZE };
}

function mkSVG(tag, attrs = {}) {
  let el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}

function buildBoard() {
  svg.innerHTML = "";

  for (let r = 0; r < NODES_R - 1; r++)
    for (let c = 0; c < NODES_C - 1; c++) {
      let { x, y } = nodeXY(r, c);
      let rect = mkSVG("rect", {
        x,
        y,
        width: CELL_SIZE,
        height: CELL_SIZE,
        fill: "transparent",
        cursor: "pointer",
        "data-cell-r": r,
        "data-cell-c": c,
      });
      rect.classList.add("cell-area");
      rect.addEventListener("click", onCellClick);
      svg.appendChild(rect);
    }

  state.hintCells.forEach((h) => {
    let { x, y } = nodeXY(h.r, h.c);
    let rect = mkSVG("rect", {
      x: x + 2,
      y: y + 2,
      width: CELL_SIZE - 4,
      height: CELL_SIZE - 4,
      rx: 4,
      class: "hint-cell-rect",
    });
    svg.appendChild(rect);
    let tx = x + CELL_SIZE / 2,
      ty = y + CELL_SIZE / 2;
    let txt = mkSVG("text", { x: tx, y: ty, class: "hint-cell-text" });
    txt.textContent = h.v;
    svg.appendChild(txt);
  });

  for (let r = 0; r < H_ROWS; r++)
    for (let c = 0; c < H_COLS; c++) {
      let { x: x1, y: y1 } = nodeXY(r, c);
      let { x: x2, y: y2 } = nodeXY(r, c + 1);
      let line = mkSVG("line", {
        x1,
        y1,
        x2,
        y2,
        class: "seg-h",
        "data-type": "H",
        "data-r": r,
        "data-c": c,
      });
      line.addEventListener("click", onSegClick);
      svg.appendChild(line);
    }

  for (let r = 0; r < V_ROWS; r++)
    for (let c = 0; c < V_COLS; c++) {
      let { x: x1, y: y1 } = nodeXY(r, c);
      let { x: x2, y: y2 } = nodeXY(r + 1, c);
      let line = mkSVG("line", {
        x1,
        y1,
        x2,
        y2,
        class: "seg-v",
        "data-type": "V",
        "data-r": r,
        "data-c": c,
      });
      line.addEventListener("click", onSegClick);
      svg.appendChild(line);
    }

  refreshSegmentColors();
}

function refreshSegmentColors() {
  svg.querySelectorAll(".seg-h,.seg-v").forEach((el) => {
    el.style.stroke = "var(--seg-empty)";
    el.style.strokeWidth = "5";
    el.classList.remove("seg-placed", "seg-fixed");
  });

  Object.entries(state.placed).forEach(([d, segs]) => {
    let color = DIGIT_COLORS[+d];
    let isFixed = state.fixed[+d];
    segs.forEach(([t, r, c]) => {
      let el = svg.querySelector(
        `.seg-${t.toLowerCase()}[data-type="${t}"][data-r="${r}"][data-c="${c}"]`,
      );
      if (!el) return;
      el.style.stroke = color;
      el.style.strokeWidth = isFixed ? "7" : "5";
      el.classList.add("seg-placed");
      if (isFixed) el.classList.add("seg-fixed");
      el.style.filter = `drop-shadow(0 0 6px ${color}88)`;
    });
  });
}

// ============================================================
// PREVIEW SVG
// ============================================================
function updatePreview() {
  const psvg = document.getElementById("preview-svg");
  psvg.innerHTML = "";
  if (state.selectedDigit === null) return;
  let d = state.selectedDigit;
  let color = DIGIT_COLORS[d];
  let { H, V } =
    state.orientations[state.orientIdx % state.orientations.length];
  let nR = H.length,
    nC = H[0].length + 1;
  let CS = Math.min(70 / (nC - 1 || 1), 70 / (nR - 1 || 1), 30);
  let ox = 5,
    oy = 10;

  for (let r = 0; r < H.length; r++)
    for (let c = 0; c < H[0].length; c++) {
      if (H[r][c]) {
        let l = mkSVG("line", {
          x1: ox + c * CS,
          y1: oy + r * CS,
          x2: ox + (c + 1) * CS,
          y2: oy + r * CS,
          stroke: color,
          "stroke-width": 4,
          "stroke-linecap": "round",
        });
        l.style.filter = `drop-shadow(0 0 4px ${color})`;
        psvg.appendChild(l);
      }
    }
  for (let r = 0; r < V.length; r++)
    for (let c = 0; c < V[0].length; c++) {
      if (V[r][c]) {
        let l = mkSVG("line", {
          x1: ox + c * CS,
          y1: oy + r * CS,
          x2: ox + c * CS,
          y2: oy + (r + 1) * CS,
          stroke: color,
          "stroke-width": 4,
          "stroke-linecap": "round",
        });
        l.style.filter = `drop-shadow(0 0 4px ${color})`;
        psvg.appendChild(l);
      }
    }
  let lbl = mkSVG("text", {
    x: ox + (nC - 1) * CS + 12,
    y: oy + 4,
    fill: color,
    "font-family": "Orbitron,sans-serif",
    "font-size": "14",
    "font-weight": "900",
  });
  lbl.textContent = d;
  psvg.appendChild(lbl);
}

// ============================================================
// PIECE GRID
// ============================================================
function buildPieceGrid() {
  const grid = document.getElementById("piece-grid");
  grid.innerHTML = "";
  for (let d = 0; d <= 9; d++) {
    let btn = document.createElement("button");
    btn.className = "piece-btn";
    btn.dataset.digit = d;
    btn.textContent = d;
    let pip = document.createElement("span");
    pip.className = "pip";
    pip.textContent = DIGIT_SEGMENTS[d].length + "seg";
    btn.appendChild(pip);
    updatePieceBtn(btn, d);
    btn.addEventListener("click", () => selectDigit(d));
    grid.appendChild(btn);
  }
}

function updatePieceBtn(btn, d) {
  btn.classList.remove("available", "selected", "placed", "fixed-piece");
  if (state.placed[d] !== undefined) {
    if (state.fixed[d]) btn.classList.add("fixed-piece");
    else btn.classList.add("placed");
  } else if (state.selectedDigit === d) {
    btn.classList.add("selected");
  } else {
    btn.classList.add("available");
  }
}

function refreshPieceBtns() {
  document.querySelectorAll(".piece-btn").forEach((btn) => {
    updatePieceBtn(btn, +btn.dataset.digit);
  });
}

function selectDigit(d) {
  if (state.placed[d] !== undefined) return;
  state.selectedDigit = d;
  state.orientIdx = 0;
  state.orientations = allOrientations(d);
  refreshPieceBtns();
  updatePreview();
  updateOrientBtns();
  log(
    `Seleccionado dígito ${d} — ${state.orientations.length} orientaciones`,
    "info",
  );
}

function updateOrientBtns() {
  let has = state.selectedDigit !== null;
  document.getElementById("btn-rot").disabled = !has;
  document.getElementById("btn-mir").disabled = !has;
  document.getElementById("btn-next-orient").disabled = !has;
  if (has) {
    document.getElementById("btn-next-orient").textContent =
      `ORIENT ${state.orientIdx + 1}/${state.orientations.length}`;
  }
}

// ============================================================
// PLACEMENT LOGIC
// ============================================================
function tryPlaceDigit(segType, segR, segC) {
  if (state.selectedDigit === null) return;
  let d = state.selectedDigit;
  let { H, V } =
    state.orientations[state.orientIdx % state.orientations.length];
  let nR = H.length;
  let nC = H[0].length + 1;

  let placed = false;
  outer: for (let dr = 0; dr <= NODES_R - nR; dr++) {
    for (let dc = 0; dc <= NODES_C - nC; dc++) {
      let segs = arraysToSegs(H, V, dr, dc);
      let hit = segs.some(
        ([t, r, c]) => t === segType && r === segR && c === segC,
      );
      if (!hit) continue;
      let ok = true;
      for (let [t, r, c] of segs) {
        if (t === "H" && !(r >= 0 && r < H_ROWS && c >= 0 && c < H_COLS)) {
          ok = false;
          break;
        }
        if (t === "V" && !(r >= 0 && r < V_ROWS && c >= 0 && c < V_COLS)) {
          ok = false;
          break;
        }
        for (let [od, osegs] of Object.entries(state.placed)) {
          if (+od === d) continue;
          if (osegs.some(([ot, or, oc]) => ot === t && or === r && oc === c)) {
            ok = false;
            break;
          }
        }
        if (!ok) break;
      }
      if (!ok) continue;
      state.placed[d] = segs;
      state.selectedDigit = null;
      placed = true;
      log(`Dígito ${d} colocado (${segs.length} aristas)`, "ok");
      break outer;
    }
  }
  if (!placed)
    log(`No se puede colocar dígito ${d} con esta orientación aquí`, "warn");
  refreshPieceBtns();
  buildBoard();
  updateOrientBtns();
  updatePreview();
  updateLegend();
}

// ============================================================
// EVENT HANDLERS
// ============================================================
function onSegClick(e) {
  let t = e.target.dataset.type;
  let r = +e.target.dataset.r;
  let c = +e.target.dataset.c;
  if (state.mode !== "place") return;
  tryPlaceDigit(t, r, c);
}

function onNodeClick(e) {
  let r = +e.target.dataset.nodeR;
  let c = +e.target.dataset.nodeC;
}

function onCellClick(e) {
  let r = +e.target.dataset.cellR;
  let c = +e.target.dataset.cellC;
  if (state.mode === "hint-cell") {
    document.getElementById("hc-r").value = r;
    document.getElementById("hc-c").value = c;
    log(`Celda (${r},${c}) seleccionada — ingresa el valor de suma`, "info");
  }
}

// ============================================================
// HINT MANAGEMENT
// ============================================================
function addHintNode() {
  let r = +document.getElementById("hn-r").value;
  let c = +document.getElementById("hn-c").value;
  let v = +document.getElementById("hn-v").value;
  if (
    isNaN(r) ||
    isNaN(c) ||
    isNaN(v) ||
    r < 0 ||
    r > 4 ||
    c < 0 ||
    c > 5 ||
    v < 0
  ) {
    log("Valores de nodo inválidos (r:0-4, c:0-5)", "err");
    return;
  }
  if (state.hintNodes.find((h) => h.r === r && h.c === c)) {
    log(`Ya existe pista en nodo (${r},${c})`, "warn");
    return;
  }
  state.hintNodes.push({ r, c, v });
  renderHintList("node");
  buildBoard();
  log(`Pista nodo (${r},${c})=${v} añadida`, "ok");
}

function addHintCell() {
  let r = +document.getElementById("hc-r").value;
  let c = +document.getElementById("hc-c").value;
  let v = +document.getElementById("hc-v").value;
  if (
    isNaN(r) ||
    isNaN(c) ||
    isNaN(v) ||
    r < 0 ||
    r > 3 ||
    c < 0 ||
    c > 4 ||
    v < 0
  ) {
    log("Valores de celda inválidos (r:0-3, c:0-4)", "err");
    return;
  }
  if (state.hintCells.find((h) => h.r === r && h.c === c)) {
    log(`Ya existe pista en celda (${r},${c})`, "warn");
    return;
  }
  state.hintCells.push({ r, c, v });
  renderHintList("cell");
  buildBoard();
  log(`Pista celda (${r},${c})=${v} añadida`, "ok");
}

function removeHintNode(r, c) {
  state.hintNodes = state.hintNodes.filter((h) => !(h.r === r && h.c === c));
  renderHintList("node");
  buildBoard();
  log(`Pista nodo (${r},${c}) eliminada`, "info");
}

function removeHintCell(r, c) {
  state.hintCells = state.hintCells.filter((h) => !(h.r === r && h.c === c));
  renderHintList("cell");
  buildBoard();
}

function renderHintList(type) {
  let list = document.getElementById(`hint-${type}-list`);
  list.innerHTML = "";
  let hints = type === "node" ? state.hintNodes : state.hintCells;
  hints.forEach((h) => {
    let tag = document.createElement("div");
    tag.className = "hint-tag";
    tag.innerHTML = `<span>${type === "node" ? "Nodo" : "Celda"} (${h.r},${h.c}) = <strong>${h.v}</strong></span>`;
    let rm = document.createElement("button");
    rm.textContent = "×";
    rm.addEventListener("click", () => {
      type === "node" ? removeHintNode(h.r, h.c) : removeHintCell(h.r, h.c);
    });
    tag.appendChild(rm);
    list.appendChild(tag);
  });
}

// ============================================================
// ROTATION & MIRROR
// ============================================================
document.getElementById("btn-rot").addEventListener("click", () => {
  if (state.selectedDigit === null) return;
  let { H, V } =
    state.orientations[state.orientIdx % state.orientations.length];
  let { H: H2, V: V2 } = rotate90(H, V);
  let key = arraysKey(H2, V2);
  let idx = state.orientations.findIndex((o) => arraysKey(o.H, o.V) === key);
  if (idx >= 0) state.orientIdx = idx;
  updatePreview();
  updateOrientBtns();
  log(`Dígito ${state.selectedDigit} rotado`, "info");
});

document.getElementById("btn-mir").addEventListener("click", () => {
  if (state.selectedDigit === null) return;
  let { H, V } =
    state.orientations[state.orientIdx % state.orientations.length];
  let { H: H2, V: V2 } = mirrorH(H, V);
  let key = arraysKey(H2, V2);
  let idx = state.orientations.findIndex((o) => arraysKey(o.H, o.V) === key);
  if (idx >= 0) state.orientIdx = idx;
  else state.orientIdx = (state.orientIdx + 1) % state.orientations.length;
  updatePreview();
  updateOrientBtns();
  log(`Dígito ${state.selectedDigit} reflejado`, "info");
});

document.getElementById("btn-next-orient").addEventListener("click", () => {
  if (state.selectedDigit === null) return;
  state.orientIdx = (state.orientIdx + 1) % state.orientations.length;
  updatePreview();
  updateOrientBtns();
  log(
    `Orientación ${state.orientIdx + 1}/${state.orientations.length}`,
    "info",
  );
});

// ============================================================
// CLEAR / UNFIX
// ============================================================
document.getElementById("btn-clear").addEventListener("click", () => {
  state.placed = {};
  state.fixed = {};
  state.selectedDigit = null;
  state.orientations = [];
  refreshPieceBtns();
  buildBoard();
  updateOrientBtns();
  updatePreview();
  updateLegend();
  log("Tablero limpiado", "warn");
});

document.getElementById("btn-unfix").addEventListener("click", () => {
  let digits = Object.keys(state.placed).map(Number);
  if (!digits.length) {
    log("No hay piezas colocadas", "info");
    return;
  }
  let last = digits[digits.length - 1];
  delete state.placed[last];
  delete state.fixed[last];
  log(`Dígito ${last} eliminado del tablero`, "warn");
  refreshPieceBtns();
  buildBoard();
  updateLegend();
});

// ============================================================
// MODE TABS
// ============================================================
document.querySelectorAll(".mode-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    state.mode = tab.dataset.mode;
    document
      .querySelectorAll(".mode-tab")
      .forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("place-panel").style.display =
      state.mode === "place" ? "block" : "none";
    document.getElementById("hint-cell-panel").style.display =
      state.mode === "hint-cell" ? "block" : "none";
    log(`Modo: ${state.mode}`, "info");
  });
});

// ============================================================
// SERVER COMMUNICATION
// ============================================================
function getServer() {
  return document.getElementById("server-url").value.replace(/\/$/, "");
}

async function ping() {
  let dot = document.getElementById("conn-dot");
  dot.className = "";
  try {
    let r = await fetch(getServer() + "/api/info", {
      signal: AbortSignal.timeout(3000),
    });
    if (r.ok) {
      let data = await r.json();
      dot.className = "ok";
      log(
        `Servidor OK — tablero ${data.board.NODES_R}×${data.board.NODES_C}`,
        "ok",
      );
    } else {
      dot.className = "err";
      log(`Servidor respondió ${r.status}`, "err");
    }
  } catch (e) {
    dot.className = "err";
    log(
      `Sin conexión: ${e.message} — ¿Ejecutaste "python main.py --server 5050"?`,
      "err",
    );
  }
}

document.getElementById("btn-ping").addEventListener("click", ping);

function buildPayload() {
  let fixed = {};
  Object.entries(state.placed).forEach(([d, segs]) => {
    fixed[d] = segs;
  });
  return {
    fixed,
    hints: state.hintNodes.map((h) => [h.r, h.c, h.v]),
    cell_hints: state.hintCells.map((h) => [h.r, h.c, h.v]),
    cover_all: false,
  };
}

document.getElementById("btn-validate").addEventListener("click", async () => {
  let payload = buildPayload();
  log("Validando configuración...", "info");
  try {
    let r = await fetch(getServer() + "/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(5000),
    });
    let data = await r.json();
    if (data.valid) log("✓ Configuración válida: " + data.message, "ok");
    else log("✗ " + data.message, "err");
  } catch (e) {
    log("Error de conexión: " + e.message, "err");
  }
});

document.getElementById("btn-solve").addEventListener("click", async () => {
  let btn = document.getElementById("btn-solve");
  btn.classList.add("solving");
  btn.disabled = true;
  let payload = buildPayload();
  log("⚡ Enviando al solver CP-SAT...", "solve");

  Object.keys(state.placed).forEach((d) => {
    state.fixed[+d] = true;
  });

  try {
    let r = await fetch(getServer() + "/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(60000),
    });
    let data = await r.json();
    btn.classList.remove("solving");
    btn.disabled = false;

    if (data.status === "solved") {
      log(
        `✓ SOLUCIÓN ENCONTRADA — ${Object.keys(data.placements).length} dígitos`,
        "ok",
      );
      applySolution(data.placements);
    } else if (data.status === "no_solution") {
      log("✗ Sin solución con las restricciones dadas", "err");
    } else {
      log("✗ Error: " + data.message, "err");
    }
  } catch (e) {
    btn.classList.remove("solving");
    btn.disabled = false;
    log("Error: " + e.message + " — ¿Servidor activo?", "err");
  }
});

function applySolution(placements) {
  Object.entries(placements).forEach(([d, segs]) => {
    state.placed[+d] = segs.map((s) => [s[0], s[1], s[2]]);
  });
  state.selectedDigit = null;
  refreshPieceBtns();
  buildBoard();
  updateLegend();
  log("Solución visualizada en el tablero", "ok");
}

// ============================================================
// EXPORT / IMPORT
// ============================================================
document.getElementById("btn-export").addEventListener("click", () => {
  let payload = buildPayload();
  let box = document.getElementById("export-box");
  box.textContent = JSON.stringify(payload, null, 2);
  box.classList.add("visible");
  navigator.clipboard
    ?.writeText(JSON.stringify(payload))
    .then(() => log("JSON copiado al portapapeles", "ok"));
  log("JSON exportado", "info");
});

document.getElementById("btn-import-sol").addEventListener("click", () => {
  let json = prompt(
    'Pega el JSON de solución (formato {"placements": {...}}):',
  );
  if (!json) return;
  try {
    let data = JSON.parse(json);
    if (data.placements) {
      applySolution(data.placements);
      log("Solución importada desde JSON", "ok");
    } else {
      log('Formato inválido — se espera {"placements": {...}}', "err");
    }
  } catch (e) {
    log("JSON inválido: " + e.message, "err");
  }
});

// ============================================================
// LEGEND
// ============================================================
function updateLegend() {
  let leg = document.getElementById("legend");
  leg.innerHTML = "";
  Object.keys(state.placed).forEach((d) => {
    let item = document.createElement("div");
    item.className = "legend-item";
    let dot = document.createElement("div");
    dot.className = "legend-dot";
    dot.style.background = DIGIT_COLORS[+d];
    dot.style.boxShadow = `0 0 6px ${DIGIT_COLORS[+d]}88`;
    item.appendChild(dot);
    let lbl = document.createElement("span");
    lbl.textContent = `${d}${state.fixed[+d] ? " (fijo)" : ""}`;
    item.appendChild(lbl);
    leg.appendChild(item);
  });
}

// ============================================================
// LOG
// ============================================================
function log(msg, type = "info") {
  let el = document.getElementById("status-log");
  let span = document.createElement("span");
  span.className = `log-entry log-${type}`;
  let ts = new Date().toLocaleTimeString("es", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  span.textContent = `[${ts}] ${msg}`;
  el.appendChild(document.createElement("br"));
  el.appendChild(span);
  el.scrollTop = el.scrollHeight;
}

// ============================================================
// HINT ADD BUTTONS
// ============================================================
document
  .getElementById("btn-add-hint-cell")
  .addEventListener("click", addHintCell);

["hn-r", "hn-c", "hn-v"].forEach((id) => {
  document.getElementById(id).addEventListener("keydown", (e) => {
    if (e.key === "Enter") addHintNode();
  });
});
["hc-r", "hc-c", "hc-v"].forEach((id) => {
  document.getElementById(id).addEventListener("keydown", (e) => {
    if (e.key === "Enter") addHintCell();
  });
});

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================
document.addEventListener("keydown", (e) => {
  if (e.key === "r" || e.key === "R")
    document.getElementById("btn-rot").click();
  if (e.key === "m" || e.key === "M")
    document.getElementById("btn-mir").click();
  if (e.key === "n" || e.key === "N")
    document.getElementById("btn-next-orient").click();
  if (e.key === "Escape") {
    state.selectedDigit = null;
    refreshPieceBtns();
    updatePreview();
  }
  if (e.key >= "0" && e.key <= "9") selectDigit(+e.key);
});

// ============================================================
// INIT
// ============================================================
buildPieceGrid();
buildBoard();
updateOrientBtns();
updatePreview();

setTimeout(ping, 800);

log(
  "Atajos: 0-9 selecciona pieza · R rota · M refleja · N siguiente orient.",
  "info",
);
log(
  "Haz clic en una arista del tablero para colocar la pieza seleccionada",
  "info",
);
