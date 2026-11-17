// Vista «web» de En vivo: tarjeta con los últimos archivos y, en el detalle, la página en un iframe que se recarga
// solo cuando cambia `ultimo_cambio` (contrato: references/vivo-contrato.md).
(function () {
  const vistos = {}; // id del producto -> último `ultimo_cambio` visto
  const nombre = (ruta) => String(ruta).split("/").pop();
  const abrir = (h, url) =>
    h("a", { class: "chip", href: url, target: "_blank", rel: "noopener" }, "abrir");

  FlotaVivo.registrar("web", {
    resumen(p, ctx) {
      const { h } = ctx;
      const d = p.datos;
      const archivos = (d.archivos || []).slice(0, 3).map((a) => nombre(a)).join(", ");
      return h("div", { class: "vivo-web" },
        h("div", { style: "display:flex;gap:8px;align-items:center;justify-content:space-between" },
          h("strong", { style: "color:var(--texto)" }, p.titulo),
          abrir(h, d.url)),
        h("div", { style: "color:var(--tenue)" },
          d.ultimo_cambio ? "cambió hace " + ctx.hace(d.ultimo_cambio) : "sin cambios en la ventana"),
        archivos ? h("div", { style: "color:var(--suave)" }, archivos) : null);
    },

    detalle(p, ctx) {
      const { h } = ctx;
      const d = p.datos;
      const marco = h("iframe", {
        src: d.url,
        sandbox: "allow-scripts allow-same-origin allow-forms",
        style: "width:100%;height:70vh;border:1px solid var(--borde);background:var(--panel2)",
      });
      const estado = h("span", { style: "color:var(--tenue)" });
      let recargada = Date.now();
      const pintar = () => { estado.textContent = "recargado hace " + Math.round((Date.now() - recargada) / 1000) + "s"; };
      // primera vez que se ve este producto: carga normal; después, solo si cambió el último cambio
      if (!(p.id in vistos)) vistos[p.id] = d.ultimo_cambio;
      else if (vistos[p.id] !== d.ultimo_cambio) {
        vistos[p.id] = d.ultimo_cambio;
        marco.src = d.url;
      }
      pintar();
      const reloj = setInterval(() => {
        if (!marco.isConnected) { clearInterval(reloj); return; }
        pintar();
      }, 1000);
      return h("div", { class: "vivo-web" },
        h("div", { style: "display:flex;gap:8px;align-items:center;justify-content:space-between" },
          h("strong", { style: "color:var(--texto)" }, p.titulo), estado, abrir(h, d.url)),
        marco,
        h("div", { style: "color:var(--suave)" }, "Archivos que lo provocaron"),
        h("ul", { style: "margin:4px 0;padding-left:18px;color:var(--tenue)" },
          ...(d.archivos || []).map((a) => h("li", { title: a }, nombre(a)))));
    },
  });
})();
