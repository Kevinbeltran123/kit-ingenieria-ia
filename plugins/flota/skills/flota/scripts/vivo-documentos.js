// Vista «documento» de En vivo: tarjeta con las últimas líneas y, en el detalle, el documento renderizado que se
// actualiza en cada consulta sin perder el scroll (contrato: references/vivo-contrato.md).
// El .md se dibuja con un renderizador propio que solo crea nodos con createElement/textContent: nunca innerHTML.
(function () {
  const LINEAS_EXTRACTO = 4;
  const ANCHO_EXTRACTO = 160;

  /* ---------- Markdown pequeño y seguro: texto -> nodos ---------- */
  const INLINE = /`([^`]+)`|\[([^\]]+)\]\(([^)\s]*)\)|\*\*([^*]+)\*\*|__([^_]+)__|\*([^*\s][^*]*)\*|(?<![\w])_([^_\s][^_]*)_(?![\w])/;

  function inline(h, texto) {
    const nodos = [];
    let ultimo = 0;
    const re = new RegExp(INLINE.source, "g"); // propio de cada llamada: inline se llama a sí misma
    for (let m = re.exec(texto); m; m = re.exec(texto)) {
      if (m.index > ultimo) nodos.push(texto.slice(ultimo, m.index));
      if (m[1] != null) nodos.push(h("code", { class: "md-codigo" }, m[1]));
      else if (m[2] != null) {
        // los enlaces se muestran como texto: ningún href, así que javascript: no llega a ser un destino
        nodos.push(h("span", { class: "md-enlace", title: m[3] }, ...inline(h, m[2])));
      } else if (m[4] != null || m[5] != null) nodos.push(h("strong", {}, ...inline(h, m[4] != null ? m[4] : m[5])));
      else nodos.push(h("em", {}, ...inline(h, m[6] != null ? m[6] : m[7])));
      ultimo = re.lastIndex;
    }
    if (ultimo < texto.length) nodos.push(texto.slice(ultimo));
    return nodos;
  }

  const RE_ENCABEZADO = /^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/;
  const RE_VALLA = /^\s{0,3}```/;
  const RE_ITEM = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
  const RE_REGLA = /^\s{0,3}([-*_])(\s*\1){2,}\s*$/;
  const RE_SEPARADOR = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/;
  const sangria = (s) => s.replace(/\t/g, "    ").length - s.replace(/\t/g, "    ").trimStart().length;
  const esTabla = (lineas, i) => lineas[i].includes("|") && i + 1 < lineas.length && lineas[i + 1].includes("-") && RE_SEPARADOR.test(lineas[i + 1]);

  function celdas(linea) {
    let t = linea.trim().replace(/\\\|/g, "\u0000");
    if (t.startsWith("|")) t = t.slice(1);
    if (t.endsWith("|")) t = t.slice(0, -1);
    return t.split("|").map((c) => c.replace(/\u0000/g, "|").trim());
  }

  function inicioDeBloque(lineas, i) {
    const l = lineas[i];
    return RE_ENCABEZADO.test(l) || RE_VALLA.test(l) || RE_ITEM.test(l) || RE_REGLA.test(l) || /^\s{0,3}>/.test(l) || esTabla(lineas, i);
  }

  function lista(h, items) {
    const raiz = [];
    const pila = []; // { sangria, el, ultimo }
    for (const it of items) {
      while (pila.length && it.sangria < pila[pila.length - 1].sangria) pila.pop();
      let tope = pila[pila.length - 1];
      if (tope && it.sangria === tope.sangria && it.ordenada !== tope.ordenada) { // de - a 1. al mismo nivel: lista nueva
        pila.pop();
        tope = pila[pila.length - 1];
        if (tope) tope = { ...tope, sangria: -1 };
      }
      if (!tope || it.sangria > tope.sangria) {
        const el = h(it.ordenada ? "ol" : "ul", { class: "md-lista" });
        if (tope && tope.ultimo) tope.ultimo.append(el);
        else raiz.push(el);
        tope = { sangria: it.sangria, el, ultimo: null, ordenada: it.ordenada };
        pila.push(tope);
      }
      const li = h("li", {}, ...inline(h, it.texto));
      tope.el.append(li);
      tope.ultimo = li;
    }
    return raiz;
  }

  function mdADom(texto, h) {
    const lineas = String(texto).replace(/\r\n?/g, "\n").split("\n");
    const salida = [];
    let i = 0;
    while (i < lineas.length) {
      const l = lineas[i];
      if (!l.trim()) { i++; continue; }
      if (RE_VALLA.test(l)) { // un bloque sin cerrar es normal mientras el agente escribe: llega hasta el final
        const cuerpo = [];
        i++;
        while (i < lineas.length && !RE_VALLA.test(lineas[i])) cuerpo.push(lineas[i++]);
        i++;
        salida.push(h("pre", { class: "md-bloque" }, h("code", {}, cuerpo.join("\n"))));
        continue;
      }
      const enc = RE_ENCABEZADO.exec(l);
      if (enc) { salida.push(h("h" + enc[1].length, { class: "md-h" }, ...inline(h, enc[2]))); i++; continue; }
      if (RE_REGLA.test(l)) { salida.push(h("hr", { class: "md-hr" })); i++; continue; }
      if (esTabla(lineas, i)) {
        const cab = celdas(l);
        const filas = [];
        i += 2;
        while (i < lineas.length && lineas[i].trim() && lineas[i].includes("|")) filas.push(celdas(lineas[i++]));
        salida.push(h("div", { class: "md-tabla" }, h("table", {},
          h("thead", {}, h("tr", {}, ...cab.map((c) => h("th", {}, ...inline(h, c))))),
          h("tbody", {}, ...filas.map((f) => h("tr", {}, ...cab.map((_, k) => h("td", {}, ...inline(h, f[k] || ""))))))
        )));
        continue;
      }
      if (/^\s{0,3}>/.test(l)) {
        const cita = [];
        while (i < lineas.length && /^\s{0,3}>/.test(lineas[i])) cita.push(lineas[i++].replace(/^\s{0,3}>\s?/, ""));
        salida.push(h("blockquote", { class: "md-cita" }, ...mdADom(cita.join("\n"), h)));
        continue;
      }
      if (RE_ITEM.test(l)) {
        const items = [];
        while (i < lineas.length && lineas[i].trim()) {
          const m = RE_ITEM.exec(lineas[i]);
          if (m) items.push({ sangria: sangria(lineas[i]), ordenada: /\d/.test(m[2]), texto: m[3] });
          else if (RE_ENCABEZADO.test(lineas[i]) || RE_VALLA.test(lineas[i])) break;
          else items[items.length - 1].texto += " " + lineas[i].trim();
          i++;
        }
        salida.push(...lista(h, items));
        continue;
      }
      const parrafo = [l.trim()];
      i++;
      while (i < lineas.length && lineas[i].trim() && !inicioDeBloque(lineas, i)) parrafo.push(lineas[i++].trim());
      salida.push(h("p", { class: "md-p" }, ...inline(h, parrafo.join(" "))));
    }
    return salida;
  }

  /* ---------- Vista ---------- */
  let estiloListo = false;
  function estilo(h) {
    if (estiloListo || typeof document === "undefined") return;
    estiloListo = true;
    document.head.append(h("style", {}, `
.vivo-doc { color: var(--texto); min-width: 0; }
.vivo-doc .doc-meta { color: var(--tenue); font-size: 12px; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }
.vivo-doc .md-h { margin: 1.1em 0 .4em; line-height: 1.25; }
.vivo-doc h1.md-h { font-size: 1.5em; } .vivo-doc h2.md-h { font-size: 1.28em; } .vivo-doc h3.md-h { font-size: 1.12em; }
.vivo-doc h4.md-h, .vivo-doc h5.md-h, .vivo-doc h6.md-h { font-size: 1em; color: var(--tenue); }
.vivo-doc .md-p { margin: .5em 0; overflow-wrap: anywhere; }
.vivo-doc .md-lista { margin: .4em 0; padding-left: 22px; } .vivo-doc .md-lista li { margin: .15em 0; overflow-wrap: anywhere; }
.vivo-doc .md-codigo { background: var(--panel2); border: 1px solid var(--borde); border-radius: 4px; padding: 0 4px; }
.vivo-doc .md-bloque { background: var(--panel2); border: 1px solid var(--borde); border-radius: 6px; padding: 8px 10px; overflow: auto; margin: .6em 0; }
.vivo-doc .md-cita { margin: .6em 0; padding: 0 12px; border-left: 3px solid var(--borde); color: var(--tenue); }
.vivo-doc .md-hr { border: 0; border-top: 1px solid var(--borde); margin: 1em 0; }
.vivo-doc .md-enlace { text-decoration: underline dotted; text-underline-offset: 2px; }
.vivo-doc .md-tabla { overflow: auto; margin: .6em 0; }
.vivo-doc table { border-collapse: collapse; } .vivo-doc th, .vivo-doc td { border: 1px solid var(--borde); padding: 3px 8px; text-align: left; vertical-align: top; }
.vivo-doc th { background: var(--panel2); }
.vivo-doc iframe { width: 100%; height: 75vh; border: 1px solid var(--borde); background: var(--panel); }
.vivo-doc .doc-extracto { margin: 4px 0 0; padding: 6px 8px; background: var(--panel2); border-radius: 6px; color: var(--tenue); white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; font-size: 12px; }
`));
  }

  function tamano(n) {
    if (n < 1024) return n + " B";
    if (n < 1048576) return (n / 1024).toFixed(n < 10240 ? 1 : 0) + " KB";
    return (n / 1048576).toFixed(1) + " MB";
  }
  const quien = (p) => [p.proyecto, p.agente].filter(Boolean).join(" / ");
  const etiquetas = (h, p) => {
    const d = p.datos;
    return h("div", { class: "doc-meta" },
      h("span", { class: "chip" }, d.formato),
      quien(p) ? h("span", {}, quien(p)) : null,
      h("span", {}, `${tamano(d.tamano)} · ${d.lineas} ${d.lineas === 1 ? "línea" : "líneas"}`));
  };

  async function leer(ctx, p) {
    const r = await fetch(ctx.archivo(p.datos.archivo), { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.text();
  }

  function ultimasLineas(texto) {
    return texto.slice(-4000).split("\n").map((l) => l.trim()).filter(Boolean).slice(-LINEAS_EXTRACTO)
      .map((l) => (l.length > ANCHO_EXTRACTO ? l.slice(0, ANCHO_EXTRACTO - 1) + "…" : l));
  }

  FlotaVivo.registrar("documento", {
    mdADom,

    resumen(p, ctx) {
      const { h } = ctx;
      estilo(h);
      const extracto = h("pre", { class: "doc-extracto" }, p.datos.formato === "md" ? "…" : "documento HTML");
      if (p.datos.formato === "md") {
        leer(ctx, p).then((t) => {
          const l = ultimasLineas(t);
          if (l.length) extracto.textContent = l.join("\n");
          else extracto.remove();
        }).catch(() => { extracto.textContent = "no se pudo leer"; });
      }
      return h("div", { class: "vivo-doc" },
        h("strong", {}, p.titulo),
        etiquetas(h, p), extracto);
    },

    // El host llama otra vez con el nodo anterior cuando el documento cambia: se actualiza ese mismo nodo.
    detalle(p, ctx, anterior) {
      const { h } = ctx;
      estilo(h);
      const d = p.datos;
      let raiz = anterior && anterior.dataset && anterior.dataset.doc === p.id ? anterior : null;
      if (!raiz) {
        raiz = h("div", { class: "vivo-doc", "data-doc": p.id });
        raiz.append(h("div", { class: "doc-meta" }), h("div", { class: "doc-cuerpo" }));
      }
      raiz.firstChild.replaceWith(etiquetas(h, p));
      const cuerpo = raiz.lastChild;
      if (d.formato === "html") {
        // sin allow-scripts: el HTML de un agente se ve, pero no ejecuta nada
        let marco = cuerpo.firstChild;
        if (!marco) {
          marco = h("iframe", { sandbox: "", title: p.titulo });
          cuerpo.append(marco);
        }
        if (marco.dataset.t !== String(p.t)) {
          marco.dataset.t = String(p.t);
          marco.src = ctx.archivo(d.archivo) + "&v=" + encodeURIComponent(p.t);
        }
        return raiz;
      }
      const turno = (raiz.turno = (raiz.turno || 0) + 1);
      leer(ctx, p).then((texto) => {
        if (turno !== raiz.turno) return; // llegó una respuesta más nueva
        const sc = raiz.closest(".det-cuerpo") || raiz.parentNode;
        const abajo = sc ? sc.scrollHeight - sc.scrollTop - sc.clientHeight < 40 : false;
        const arriba = sc ? sc.scrollTop : 0;
        cuerpo.replaceChildren(...mdADom(texto, h));
        if (sc) sc.scrollTop = abajo ? sc.scrollHeight : arriba;
      }).catch((e) => {
        if (turno === raiz.turno && !cuerpo.firstChild) cuerpo.replaceChildren(h("p", { class: "md-p" }, "No se pudo leer el documento: " + e.message));
      });
      if (!cuerpo.firstChild) cuerpo.append(h("p", { class: "md-p" }, "Cargando…"));
      return raiz;
    },
  });
})();
