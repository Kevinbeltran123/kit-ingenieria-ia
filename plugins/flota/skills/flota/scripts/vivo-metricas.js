// Vista de «En vivo» para el producto `metricas`: progreso, curvas en SVG y el log del entrenamiento.
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const PERDIDA = /loss/i;
  const METRICA = /f1|acc|map|recall/i;
  const ERROR = /error|traceback|\bnan\b|\binf\b/i;

  function svg(tag, attrs, ...hijos) {
    const el = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) if (v != null) el.setAttribute(k, String(v));
    for (const c of hijos) if (c != null) el.append(c.nodeType ? c : document.createTextNode(String(c)));
    return el;
  }

  const num = (v) => (v == null ? "—" : String(Number(Number(v).toPrecision(4))));

  // Pérdida y métrica principal: primero las de validación, como en vivo_metricas.principales.
  function principales(d) {
    const EJES = ["epoch", "step", "fila", "época", "global_step"];
    const nombres = Object.keys(d.series || {}).filter((n) => n !== d.x && !EJES.includes(n));
    const elegir = (re) => {
      const c = nombres.filter((n) => re.test(n));
      return c.find((n) => /^val/i.test(n)) || c[0] || null;
    };
    return [elegir(PERDIDA), elegir(METRICA)].filter(Boolean);
  }

  // Pares [x, y] con valor, en el orden de las filas.
  function puntos(d, col) {
    const ys = d.series[col] || [];
    const xs = d.x !== "fila" && d.series[d.x] ? d.series[d.x] : null;
    const pares = [];
    ys.forEach((y, i) => {
      const x = xs ? xs[i] : i;
      if (y != null && x != null) pares.push([x, y]);
    });
    return pares;
  }

  function escala(pares, ancho, alto, margen) {
    const xs = pares.map((p) => p[0]);
    const ys = pares.map((p) => p[1]);
    const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
    const [y0, y1] = [Math.min(...ys), Math.max(...ys)];
    const fx = (x) => margen.izq + (x1 === x0 ? 0.5 : (x - x0) / (x1 - x0)) * (ancho - margen.izq - margen.der);
    const fy = (y) => margen.arr + (y1 === y0 ? 0.5 : 1 - (y - y0) / (y1 - y0)) * (alto - margen.arr - margen.aba);
    return { fx, fy, x0, x1, y0, y1 };
  }

  function linea(pares, e, color) {
    const d = pares.map((p, i) => `${i ? "L" : "M"}${e.fx(p[0]).toFixed(1)} ${e.fy(p[1]).toFixed(1)}`).join("");
    return svg("path", { d, style: `fill:none;stroke:var(${color});stroke-width:1.5;stroke-linejoin:round` });
  }

  function chispa(pares, color) {
    const margen = { izq: 2, der: 4, arr: 4, aba: 4 };
    const e = escala(pares, 120, 30, margen);
    const ult = pares[pares.length - 1];
    return svg("svg", { viewBox: "0 0 120 30", width: 120, height: 30, "aria-hidden": "true", style: "flex:none" },
      linea(pares, e, color),
      svg("circle", { cx: e.fx(ult[0]), cy: e.fy(ult[1]), r: 2, style: `fill:var(${color})` }));
  }

  function grafica(nombre, pares, eje, color) {
    const [ancho, alto] = [320, 150];
    const margen = { izq: 52, der: 10, arr: 10, aba: 24 };
    const e = escala(pares, ancho, alto, margen);
    const texto = (x, y, ancla, t) => svg("text", { x, y, "text-anchor": ancla, style: "fill:var(--suave);font-size:10px" }, t);
    const ult = pares[pares.length - 1];
    const base = alto - margen.aba;
    return svg("svg", { viewBox: `0 0 ${ancho} ${alto}`, role: "img", "aria-label": `${nombre}: último ${num(ult[1])}`,
      style: "width:100%;height:auto;display:block" },
      svg("path", { d: `M${margen.izq} ${margen.arr}V${base}H${ancho - margen.der}`, style: "fill:none;stroke:var(--borde)" }),
      texto(margen.izq - 4, margen.arr + 8, "end", num(e.y1)),
      texto(margen.izq - 4, base, "end", num(e.y0)),
      texto(margen.izq, alto - 8, "start", num(e.x0)),
      texto(ancho - margen.der, alto - 8, "end", `${num(e.x1)} ${eje}`),
      linea(pares, e, color),
      svg("circle", { cx: e.fx(ult[0]), cy: e.fy(ult[1]), r: 2.5, style: `fill:var(${color})` }));
  }

  // ↑/↓ frente al valor anterior; verde si mejora (pérdida que baja, métrica que sube).
  function flecha(h, nombre, pares) {
    if (pares.length < 2) return null;
    const [a, b] = [pares[pares.length - 2][1], pares[pares.length - 1][1]];
    if (a === b) return h("span", { style: "color:var(--suave)" }, "=");
    const sube = b > a;
    const mejora = PERDIDA.test(nombre) ? !sube : sube;
    return h("span", { style: `color:var(${mejora ? "--listo" : "--espera"})`, title: `antes ${num(a)}` }, sube ? "↑" : "↓");
  }

  function barra(h, prog) {
    if (!prog || !prog.total) return null;
    const pct = Math.max(0, Math.min(100, (100 * prog.actual) / prog.total));
    return h("div", { style: "display:flex;gap:8px;align-items:center" },
      h("div", { role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(prog.total), "aria-valuenow": String(prog.actual),
        style: "flex:1;height:6px;border-radius:3px;background:var(--panel2);overflow:hidden" },
        h("div", { style: `width:${pct.toFixed(1)}%;height:100%;background:var(--trabajando)` })),
      h("span", { style: "color:var(--tenue);font-size:12px;white-space:nowrap" }, `${prog.actual}/${prog.total}`));
  }

  function etiquetas(h, d) {
    const chips = [];
    if (d.pueue) {
      chips.push(h("span", { class: "chip", title: d.pueue.comando }, `pueue ${d.pueue.id}${d.pueue.grupo ? " · " + d.pueue.grupo : ""}`));
    }
    if (d.errores) chips.push(h("span", { class: "chip alerta" }, `${d.errores} ${d.errores === 1 ? "línea" : "líneas"} con error`));
    return chips.length ? h("div", { style: "display:flex;gap:6px;flex-wrap:wrap" }, chips) : null;
  }

  function registro(h, lineas) {
    return h("pre", { style: "background:var(--panel2);border:1px solid var(--borde);border-radius:8px;padding:8px 10px;color:var(--tenue)" },
      lineas.map((l) => h("div", { style: ERROR.test(l) ? "color:var(--espera)" : null }, l)));
  }

  const COLORES = ["--trabajando", "--listo"];

  FlotaVivo.registrar("metricas", {
    resumen(p, ctx) {
      const h = ctx.h;
      const d = p.datos || {};
      const filas = principales(d).map((col, i) => {
        const pares = puntos(d, col);
        if (!pares.length) return null;
        return h("div", { style: "display:flex;gap:8px;align-items:center;min-width:0" },
          pares.length > 1 ? chispa(pares, COLORES[i]) : null,
          h("span", { style: "color:var(--tenue);overflow:hidden;text-overflow:ellipsis;white-space:nowrap" }, col),
          h("span", { style: "color:var(--texto);font-weight:600" }, num(pares[pares.length - 1][1])),
          flecha(h, col, pares));
      });
      const sinCurvas = !filas.some(Boolean);
      return h("div", { style: "display:grid;gap:6px;min-width:0" },
        barra(h, d.progreso),
        filas,
        sinCurvas && d.log && d.log.length ? registro(h, d.log.slice(-2)) : null,
        etiquetas(h, d));
    },

    detalle(p, ctx) {
      const h = ctx.h;
      const d = p.datos || {};
      const orden = principales(d);
      const columnas = [...orden, ...Object.keys(d.series || {}).filter((n) => n !== d.x && !orden.includes(n) && !["epoch", "step", "fila", "época", "global_step"].includes(n))];
      const tarjetas = columnas.map((col, i) => {
        const pares = puntos(d, col);
        if (!pares.length) return null;
        const ult = pares[pares.length - 1][1];
        return h("figure", { style: "margin:0;background:var(--panel2);border:1px solid var(--borde);border-radius:8px;padding:8px 10px;min-width:0" },
          h("figcaption", { style: "display:flex;gap:8px;align-items:baseline;margin-bottom:4px" },
            h("span", { style: "color:var(--tenue);overflow:hidden;text-overflow:ellipsis;white-space:nowrap" }, col),
            h("span", { style: "margin-left:auto;color:var(--texto);font-weight:600" }, num(ult)),
            flecha(h, col, pares)),
          pares.length > 1 ? grafica(col, pares, d.x === "fila" ? "fila" : d.x, COLORES[i < orden.length ? i : 0])
            : h("div", { style: "color:var(--suave);font-size:12px" }, "un solo punto"));
      });
      return h("div", { style: "display:grid;gap:12px" },
        d.archivo ? h("div", { style: "color:var(--tenue);font-size:12px;overflow-wrap:anywhere" }, d.archivo) : null,
        d.pueue ? h("pre", { style: "color:var(--tenue)" }, d.pueue.comando) : null,
        barra(h, d.progreso),
        etiquetas(h, d),
        tarjetas.some(Boolean) ? h("div", { style: "display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px" }, tarjetas) : null,
        d.log && d.log.length ? registro(h, d.log) : h("div", { style: "color:var(--suave)" }, "Sin log en la carpeta."));
    },
  });
})();
