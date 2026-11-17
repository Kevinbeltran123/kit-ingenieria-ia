// Vistas de «En vivo» para lo que sale de los registros de sesión: archivos editados (codigo) y comandos (comando).
// Contrato en references/vivo-contrato.md. Todo con ctx.h: nada de innerHTML con datos.
(function () {
  "use strict";
  const MONO = "font-family: inherit; font-size: 12px; white-space: pre-wrap; word-break: break-word; margin: 0;";

  function corta(ruta) {
    return String(ruta || "").split("/").filter(Boolean).slice(-3).join("/");
  }

  function pie(p, ctx) {
    const h = ctx.h;
    return h("div", { style: "color: var(--tenue); font-size: 12px; display: flex; gap: 6px; flex-wrap: wrap;" },
      ...[p.agente ? h("span", { class: "chip" }, p.agente) : null, h("span", {}, "hace " + ctx.hace(p.t))]
        .filter(Boolean));
  }

  function lineaDiff(h, linea) {
    let color = "var(--texto)";
    if (linea.startsWith("+")) color = "var(--listo)";
    else if (linea.startsWith("-")) color = "var(--espera)";
    else if (linea.startsWith("@@")) color = "var(--tenue)";
    return h("span", { style: "display: block; color: " + color + ";" }, linea || " ");
  }

  FlotaVivo.registrar("codigo", {
    resumen(p, ctx) {
      const h = ctx.h;
      const d = p.datos || {};
      return h("div", { style: "display: grid; gap: 4px;" },
        h("div", { style: "display: flex; gap: 8px; align-items: baseline; min-width: 0;" },
          h("span", { style: "overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--texto);",
            title: d.archivo || "" }, corta(d.archivo)),
          h("span", { style: "color: var(--listo); white-space: nowrap;" }, "+" + (d.mas || 0)),
          h("span", { style: "color: var(--espera); white-space: nowrap;" }, "−" + (d.menos || 0))),
        pie(p, ctx));
    },
    detalle(p, ctx) {
      const h = ctx.h;
      const d = p.datos || {};
      const lineas = String(d.fragmento || "").split("\n");
      return h("div", { style: "display: grid; gap: 8px;" },
        h("div", { style: "color: var(--texto); word-break: break-all;" }, d.archivo || ""),
        h("div", { style: "display: flex; gap: 8px; color: var(--tenue); font-size: 12px;" },
          h("span", { class: "chip" }, d.herramienta || ""),
          h("span", { style: "color: var(--listo);" }, "+" + (d.mas || 0)),
          h("span", { style: "color: var(--espera);" }, "−" + (d.menos || 0)),
          h("span", {}, (p.agente || "") + " · hace " + ctx.hace(p.t))),
        h("pre", { style: MONO + " background: var(--panel2); border: 1px solid var(--borde); border-radius: 8px;"
          + " padding: 8px; overflow: auto;" }, ...lineas.map((l) => lineaDiff(h, l))));
    },
  });

  function marca(h, ok) {
    if (ok === true) return h("span", { style: "color: var(--listo);", title: "terminó bien" }, "✓");
    if (ok === false) return h("span", { style: "color: var(--espera);", title: "falló" }, "✗");
    return h("span", { style: "color: var(--tenue);", title: "sin resultado todavía" }, "…");
  }

  FlotaVivo.registrar("comando", {
    resumen(p, ctx) {
      const h = ctx.h;
      const d = p.datos || {};
      const resultado = d.resultado || [];
      return h("div", { style: "display: grid; gap: 4px;" }, ...[
        h("div", { style: "display: flex; gap: 8px; align-items: baseline; min-width: 0;" },
          marca(h, d.ok),
          h("code", { style: "overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--texto);",
            title: d.comando || "" }, p.titulo || d.comando || "")),
        resultado.length ? h("pre", { style: MONO + " color: var(--suave); max-height: 4.5em; overflow: hidden;" },
          resultado.slice(-3).join("\n")) : null,
        pie(p, ctx)].filter(Boolean));
    },
    detalle(p, ctx) {
      const h = ctx.h;
      const d = p.datos || {};
      const extra = d.duracion == null ? "" : " · " + Number(d.duracion).toFixed(1) + " s";
      return h("div", { style: "display: grid; gap: 8px;" },
        h("div", { style: "display: flex; gap: 8px; color: var(--tenue); font-size: 12px;" },
          marca(h, d.ok), h("span", {}, (p.agente || "") + " · hace " + ctx.hace(p.t) + extra)),
        h("pre", { style: MONO + " color: var(--texto); background: var(--panel2); border: 1px solid var(--borde);"
          + " border-radius: 8px; padding: 8px; overflow: auto;" }, d.comando || ""),
        h("pre", { style: MONO + " color: var(--suave); padding: 0 8px; overflow: auto;" },
          (d.resultado || []).join("\n")));
    },
  });
})();
