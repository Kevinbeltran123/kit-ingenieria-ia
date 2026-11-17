// Vista de «En vivo» para el producto `imagenes`: tira de miniaturas y rejilla con ampliación.
FlotaVivo.registrar("imagenes", {
  resumen(p, ctx) {
    const h = ctx.h;
    const tira = h("div", { style: "display:flex;gap:4px;overflow:hidden;margin-top:6px" });
    for (const ruta of p.datos.recientes.slice(0, 8)) {
      tira.appendChild(
        h("img", {
          loading: "lazy",
          src: ctx.archivo(ruta),
          alt: ruta.split("/").pop(),
          style: "width:56px;height:56px;flex:none;object-fit:cover;border-radius:4px;background:var(--panel2)",
        }),
      );
    }
    return h(
      "div",
      {},
      h("div", { style: "color:var(--texto)" }, p.titulo),
      h("div", { style: "color:var(--tenue);font-size:12px" }, `${p.datos.nuevas} nuevas · ${p.datos.total} en total · ${ctx.hace(p.t)}`),
      tira,
    );
  },

  detalle(p, ctx) {
    const h = ctx.h;
    const ampliar = (ruta) => {
      const cerrar = () => {
        capa.remove();
        document.removeEventListener("keydown", alTecla);
      };
      const alTecla = (ev) => {
        if (ev.key === "Escape") cerrar();
      };
      const capa = h(
        "div",
        {
          style: "position:fixed;inset:0;z-index:1000;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;padding:16px;background:var(--panel);cursor:zoom-out",
          onclick: cerrar,
        },
        h("img", { src: ctx.archivo(ruta), style: "max-width:100%;max-height:calc(100% - 32px);object-fit:contain" }),
        h("div", { style: "color:var(--texto);font-size:13px" }, ruta.split("/").pop()),
      );
      document.addEventListener("keydown", alTecla);
      document.body.appendChild(capa);
    };
    const rejilla = h("div", { style: "display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin-top:10px" });
    for (const ruta of p.datos.recientes) {
      const nombre = ruta.split("/").pop();
      rejilla.appendChild(
        h(
          "figure",
          { style: "margin:0;cursor:zoom-in", onclick: () => ampliar(ruta) },
          h("img", {
            loading: "lazy",
            src: ctx.archivo(ruta),
            alt: nombre,
            style: "width:100%;aspect-ratio:1;object-fit:cover;border-radius:6px;background:var(--panel2);display:block",
          }),
          h("figcaption", { style: "color:var(--tenue);font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" }, nombre),
        ),
      );
    }
    return h(
      "div",
      {},
      h("div", { style: "color:var(--texto)" }, p.titulo),
      h("div", { style: "color:var(--tenue);font-size:12px" }, p.datos.carpeta),
      rejilla,
    );
  },
});
