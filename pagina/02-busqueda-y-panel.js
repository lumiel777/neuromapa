  function servidorBusca() {
    return busq.servidor !== false && performance.now() >= busq.pausa && typeof fetch === 'function' && typeof AbortController === 'function';
  }

  function actualizarBusqueda(consulta) {
    consulta = String(consulta == null ? '' : consulta);
    const seq = ++busq.seq;
    if (busq.control) { busq.control.abort(); busq.control = null; }
    const q = consulta.trim().slice(0, LARGO_CONSULTA);
    if (!q || !servidorBusca()) {
      aplicarBusqueda(consulta, buscarLocal(consulta), q && busq.servidor !== false ? 'caido' : '');
      return Promise.resolve();
    }
    const control = new AbortController();
    busq.control = control;
    let motivo = '';
    const reloj = setTimeout(() => { motivo = 'caido'; control.abort(); }, ESPERA_BUSCAR);
    return fetch('/buscar?q=' + encodeURIComponent(q) + '&n=' + RESULTADOS_SERVIDOR, { cache: 'no-store', signal: control.signal })
      .then(r => {
        if (r.status === 404 || r.status === 405 || r.status === 501) { busq.servidor = false; return null; }
        if (r.status === 503) { motivo = 'armando'; return null; }
        if (!r.ok) { motivo = 'error'; return null; }
        return r.json();
      })
      .catch(e => {
        if (!e || e.name !== 'AbortError') {
          motivo = motivo || 'caido';
          if (seq === busq.seq) busq.pausa = performance.now() + PAUSA_SERVIDOR;
        }
        return null;
      })
      .then(datos => {
        clearTimeout(reloj);
        if (seq !== busq.seq) return;
        busq.control = null;
        if (motivo === 'caido') busq.pausa = performance.now() + PAUSA_SERVIDOR;
        let b = null;
        if (datos && datos.listo === true && Array.isArray(datos.resultados)) {
          busq.servidor = true;
          b = desdeServidor(consulta, datos);
        } else if (datos && !motivo) {
          motivo = 'error';
        }
        const local = buscarLocal(consulta);
        if (!b || !b.resultados.length) {
          if (!b || local.resultados.length) b = local;
        } else {
          sumarLocales(b, local);
        }
        aplicarBusqueda(consulta, b, motivo);
      });
  }

  function cerrarSobre() {
    if (busq.sobreControl) { busq.sobreControl.abort(); busq.sobreControl = null; }
    busq.sobre = null;
  }

  function pedirSobre(boton) {
    const consulta = busq.consulta;
    const q = consulta.trim().slice(0, LARGO_CONSULTA);
    if (!q || busq.fuente !== 'servidor') return;
    cerrarSobre();
    const control = new AbortController();
    busq.sobreControl = control;
    if (boton) { boton.disabled = true; boton.textContent = 'Juntando…'; }
    const reloj = setTimeout(() => control.abort(), ESPERA_SOBRE);
    fetch('/sobre?q=' + encodeURIComponent(q), { cache: 'no-store', signal: control.signal })
      .then(r => r.ok ? r.json() : null)
      .catch(() => null)
      .then(datos => {
        clearTimeout(reloj);
        if (busq.sobreControl !== control) return;
        busq.sobreControl = null;
        if (busq.consulta !== consulta) return;
        if (!datos || datos.listo !== true || !Array.isArray(datos.grupos)) {
          aviso('El servidor no pudo juntar lo que sé sobre eso. Probá de nuevo en un rato.');
          renderResultados();
          return;
        }
        busq.sobre = { consulta, datos };
        renderResultados();
      });
  }

  function encenderCoincidencias(antes) {
    const c = estado.coincidencias;
    if (!completo() || !graficoListo || estado.vista !== 'grafo' || !c || c.size > 60) return;
    const t = performance.now();
    let i = 0;
    for (const r of estado.resultados) {
      if (i >= 30) break;
      if (!r.n._visible || (antes && antes.has(r.n))) continue;
      anim.efectos.push({ tipo: 'anillo', n: r.n, t0: t + i * 25, dur: 420, alfa: 0.85 });
      if (r === estado.resultados[0]) anim.efectos.push({ tipo: 'anillo', n: r.n, t0: t + 90, dur: 420, alfa: 0.6 });
      i++;
    }
    if (i) programarCuadro();
  }

  function ordenarResultados() {
    estado.resultados.sort((x, y) => (y.n._visible - x.n._visible) || (y.p - x.p) || (y.n.grado - x.n.grado) || x.n.titulo.localeCompare(y.n.titulo, 'es'));
  }

  function normalizarConMapa(s) {
    let out = '';
    const mapa = [];
    for (let i = 0; i < s.length;) {
      const cp = s.codePointAt(i);
      const ancho = cp > 0xffff ? 2 : 1;
      const c = s.slice(i, i + ancho);
      const nc = cp < 128 ? (c === '\\' ? '/' : c.toLowerCase()) : normalizar(c);
      for (let k = 0; k < nc.length; k++) mapa.push(i);
      out += nc;
      i += ancho;
    }
    return { out, mapa };
  }

  function marcar(texto, terminos) {
    const t = String(texto);
    if (!terminos.length) return esc(t);
    const { out: nt, mapa } = normalizarConMapa(t);
    const marcas = new Uint8Array(t.length);
    terminos.forEach(term => {
      let i = nt.indexOf(term);
      while (i >= 0) {
        for (let k = i; k < i + term.length; k++) {
          const o = mapa[k];
          marcas[o] = 1;
          if (t.codePointAt(o) > 0xffff) marcas[o + 1] = 1;
        }
        i = nt.indexOf(term, i + term.length);
      }
    });
    let out = '';
    let dentro = 0;
    for (let i = 0; i < t.length; i++) {
      if (marcas[i] !== dentro) { out += marcas[i] ? '<mark>' : '</mark>'; dentro = marcas[i]; }
      out += esc(t[i]);
    }
    return dentro ? out + '</mark>' : out;
  }

  const quitarMarcas = s => s.toLowerCase().normalize('NFKD').replace(/\p{M}/gu, '');

  function raizDe(t) {
    if (t.length < 6 || !/^\p{L}+$/u.test(t)) return null;
    for (const f of FINALES) if (t.endsWith(f) && t.length - f.length >= 4) return t.slice(0, -f.length);
    return null;
  }

  function casaTermino(forma, terminos, raices) {
    for (let i = 0; i < terminos.length; i++) {
      const t = terminos[i];
      if (forma === t || (t.length >= 3 && forma.startsWith(t))) return true;
      const r = raices[i];
      if (r && forma.startsWith(r) && TERMINACIONES.has(forma.slice(r.length))) return true;
    }
    return false;
  }

  function marcarTerminos(texto, terminos) {
    const s = String(texto == null ? '' : texto);
    if (!terminos.length) return esc(s);
    const raices = terminos.map(raizDe);
    let out = '';
    let ultimo = 0;
    for (const m of s.matchAll(RE_PALABRA)) {
      if (!casaTermino(quitarMarcas(m[0]), terminos, raices)) continue;
      out += esc(s.slice(ultimo, m.index)) + '<mark>' + esc(m[0]) + '</mark>';
      ultimo = m.index + m[0].length;
    }
    return out + esc(s.slice(ultimo));
  }

  function mejorVentana(texto, terminos) {
    const pos = [];
    terminos.forEach((t, i) => {
      let k = texto.indexOf(t);
      let c = 0;
      while (k >= 0 && c < TOPE_POSICIONES) {
        pos.push([k, k + t.length, i]);
        c++;
        k = texto.indexOf(t, k + t.length);
      }
    });
    if (!pos.length) return null;
    pos.sort((x, y) => x[0] - y[0]);
    const cuenta = terminos.map(() => 0);
    let distintos = 0;
    let a = 0;
    let mejor = null;
    for (let z = 0; z < pos.length; z++) {
      if (!cuenta[pos[z][2]]++) distintos++;
      while (a < z && pos[z][1] - pos[a][0] > ANCHO_FRAGMENTO) {
        if (!--cuenta[pos[a][2]]) distintos--;
        a++;
      }
      const veces = z - a + 1;
      if (!mejor || distintos > mejor.d || (distintos === mejor.d && veces > mejor.v)) mejor = { d: distintos, v: veces, ini: pos[a][0], fin: pos[z][1] };
    }
    return mejor;
  }

  function fragmento(r) {
    if (r.frag !== undefined) return r.frag;
    const n = r.n;
    const { out: norm, mapa } = normalizarConMapa(n.texto);
    const v = mejorVentana(norm, estado.terminos);
    if (!v) return (r.frag = esc(n.ruta));
    const base = n.texto;
    const a = mapa[v.ini];
    const b = v.fin < mapa.length ? mapa[v.fin] : base.length;
    const extra = Math.max(0, ANCHO_FRAGMENTO - (b - a));
    const ini = Math.max(0, a - Math.floor(extra / 3));
    const fin = Math.min(base.length, b + extra - (a - ini));
    const trozo = (ini > 0 ? '…' : '') + base.slice(ini, fin).replace(/\s+/g, ' ').trim() + (fin < base.length ? '…' : '');
    return (r.frag = marcar(trozo, estado.terminos));
  }

  function lineasEnPanel(n) {
    if (n._lineasPanel === undefined) n._lineasPanel = n.texto.split('\n').length;
    return n._lineasPanel;
  }

  const limpiarTitulo = s => String(s || '').replace(/[*`]/g, '').replace(/\s+/g, ' ').trim();

  function atributosSeccion(s) {
    if (!s) return '';
    const linea = Number(s.linea) || 0;
    return (s.titulo ? ' data-seccion="' + esc(limpiarTitulo(s.titulo)) + '"' : '') + (linea ? ' data-linea="' + linea + '"' : '');
  }

  function htmlLugar(r, s) {
    const linea = Number(s.linea) || 0;
    const titulo = limpiarTitulo(s.titulo);
    const fuera = r.n.recortado && linea > lineasEnPanel(r.n);
    const partes = [];
    if (titulo) partes.push(marcarTerminos(titulo, busq.terminos));
    if (linea) partes.push('línea ' + linea);
    if (!partes.length) return '';
    return '<span class="resultado-lugar"' + (titulo ? ' title="' + esc(titulo) + '"' : '') + '>' + partes.join(' · ') + '</span>' +
      (fuera ? '<span class="resultado-aviso">esta parte no entra en el panel: la nota está recortada</span>' : '');
  }

  const tituloOculta = ' title="Oculta por los filtros: al abrirla se vuelve a mostrar"';

  function filaLocal(r) {
    return '<button type="button" class="resultado' + (r.n._visible ? '' : ' oculto') + '" data-id="' + esc(r.n.id) + '"' + (r.n._visible ? '' : tituloOculta) + '>' + punto(r.n) +
      '<span class="resultado-texto"><span class="resultado-titulo">' + marcar(r.n.titulo, estado.terminos) + '</span>' +
      '<span class="resultado-sub">' + (r.enTexto ? fragmento(r) : marcar(r.n.ruta, estado.terminos)) + '</span>' +
      (r.n.recortado ? '<span class="resultado-aviso">nota recortada: la búsqueda completa necesita el servidor</span>' : '') + '</span></button>';
  }

  function filaServidor(r) {
    const t = busq.terminos;
    const s0 = r.secciones[0];
    const sub = s0 && s0.fragmento ? String(s0.fragmento) : (r.n.descripcion || r.n.ruta);
    let html = '<div class="resultado-caja"><button type="button" class="resultado' + (r.n._visible ? '' : ' oculto') + '" data-id="' + esc(r.n.id) + '"' + atributosSeccion(s0) + (r.n._visible ? '' : tituloOculta) + '>' + punto(r.n) +
      '<span class="resultado-texto"><span class="resultado-titulo">' + marcarTerminos(r.n.titulo, t) + '</span>' +
      (s0 ? htmlLugar(r, s0) : '') + '<span class="resultado-sub">' + marcarTerminos(sub, t) + '</span></span></button>';
    const extras = r.secciones.slice(1);
    if (extras.length) {
      const abierta = busq.abiertas.has(r.n.id);
      html += '<button type="button" class="resultado-plegar" data-plegar="' + esc(r.n.id) + '" aria-expanded="' + abierta + '">' + (abierta ? 'Ocultar ' : 'Ver ') +
        (extras.length === 1 ? 'otra sección' : 'otras ' + extras.length + ' secciones') + '</button>' +
        '<div class="resultado-extras"' + (abierta ? '' : ' hidden') + '>' + extras.map(s =>
          '<button type="button" class="resultado resultado-extra" data-id="' + esc(r.n.id) + '"' + atributosSeccion(s) + '><span class="resultado-texto">' + htmlLugar(r, s) +
          '<span class="resultado-sub">' + marcarTerminos(String(s.fragmento || ''), t) + '</span></span></button>').join('') + '</div>';
    }
    return html + '</div>';
  }

  let recortadas = null;
  function pieLocal() {
    let html = busq.motivo && MOTIVOS_LOCAL[busq.motivo] ? '<p class="resultados-aviso">' + esc(MOTIVOS_LOCAL[busq.motivo]) + '</p>' : '';
    if (!recortadas) recortadas = nodos.filter(n => n.recortado);
    if (recortadas.length) {
      html += '<p class="resultados-aviso" title="' + esc(recortadas.map(n => n.titulo).join(' · ')) + '">' +
        (recortadas.length === 1 ? 'Una nota larga está recortada' : recortadas.length + ' notas largas están recortadas') +
        ' y acá solo se busca en su principio: la búsqueda completa necesita el servidor.</p>';
    }
    return html;
  }

  function botonSobre(x, sub) {
    const n = x && x.id != null ? porId.get(String(x.id)) : null;
    if (!n) return '<div class="resultado sin-nota"><span class="resultado-texto"><span class="resultado-titulo">' + esc(String((x && (x.titulo || x.ruta)) || '')) + '</span><span class="resultado-sub">' + esc(sub) + '</span></span></div>';
    return '<button type="button" class="resultado' + (n._visible ? '' : ' oculto') + '" data-id="' + esc(n.id) + '"' + (n._visible ? '' : tituloOculta) + '>' + punto(n) +
      '<span class="resultado-texto"><span class="resultado-titulo">' + esc(n.titulo) + '</span><span class="resultado-sub">' + esc(sub) + '</span></span></button>';
  }

  function tramoSobre(x) {
    const desde = Number(x.linea) || 1;
    const hasta = Number(x.fin) || 0;
    const seccion = x.seccion && x.seccion !== x.titulo ? ' · ' + String(x.seccion) : '';
    return nombreArchivo(x.ruta) + ':' + desde + (hasta > desde ? '-' + hasta : '') + seccion;
  }

  function htmlSobre(s) {
    const d = s.datos;
    const t = (Array.isArray(d.terminos) ? d.terminos : []).map(x => normalizar(x)).filter(Boolean);
    const aproximado = d.aproximado === true;
    const cuantas = aproximado ? Number(d.notas) || 0 : Number(d.conPasajes) || 0;
    const verbo = aproximado ? (cuantas === 1 ? ' nota lo nombra' : ' notas lo nombran') : (cuantas === 1 ? ' nota lo dice' : ' notas lo dicen');
    let html = '<div class="resultados-cabeza">Qué sé sobre «' + esc(s.consulta.trim()) + '» · ' + cuantas + verbo + '</div>' +
      '<div class="resultados-acciones"><button type="button" class="boton-chico" data-volver>Volver a los resultados</button></div>' + avisoCorreccion(d);
    const gruposSobre = d.grupos.filter(g => g && Array.isArray(g.notas) && g.notas.length);
    if (!gruposSobre.length) html += '<p class="vacio">Ninguna nota lo dice con esas palabras juntas.</p>';
    else if (aproximado) html += '<p class="resultados-aviso">' + (Number(d.juntas) ? 'Ningún renglón junta todas las palabras: van las notas que más las nombran, con sus mejores renglones.' : 'Ningún renglón las nombra: van las notas que las tienen en el título o la descripción.') + '</p>';
    else if (Number(d.casi)) html += '<p class="resultados-aviso">' + (Number(d.casi) === 1 ? 'Va 1 nota más que junta casi todas las palabras.' : 'Van ' + Number(d.casi) + ' notas más que juntan casi todas las palabras.') + '</p>';
    gruposSobre.forEach(g => {
      html += '<div class="sobre-grupo">' + esc(String(g.nombre || g.clave || '')) + '</div>';
      g.notas.forEach(x => {
        const pasajes = Array.isArray(x.pasajes) ? x.pasajes : [];
        const mas = Number(x.masPasajes) || 0;
        html += '<div class="resultado-caja">' + botonSobre(x, nombreArchivo(x.ruta)) +
          (pasajes.length ? '<ul class="sobre-pasajes">' + pasajes.map(p => '<li><span class="sobre-linea">:' + (Number(p && p.linea) || 0) + '</span> ' + marcarTerminos(p && p.texto, t) +
            (Array.isArray(p && p.avisos) ? p.avisos.map(a => '<div class="sobre-aviso">⚠ dato viejo: ' + esc(a) + '</div>').join('') : '') + '</li>').join('') + '</ul>' : '') +
          (mas ? '<p class="sobre-mas">y ' + mas + (mas === 1 ? ' pasaje más' : ' pasajes más') + '</p>' : '') + '</div>';
      });
    });
    const leer = Array.isArray(d.leerPrimero) ? d.leerPrimero.filter(x => x && typeof x === 'object') : [];
    if (leer.length) {
      html += '<div class="sobre-grupo">Leer primero</div><ol class="sobre-leer">' + leer.map(x =>
        '<li>' + botonSobre(x, tramoSobre(x) + (x.porque ? ' · ' + x.porque : '')) +
        (Array.isArray(x.avisos) ? x.avisos.filter(a => a && typeof a === 'object').map(a => '<div class="sobre-aviso">⚠ dato viejo en la línea ' + (Number(a.linea) || 0) + ': ' + esc(a.texto) + '</div>').join('') : '') +
        '</li>').join('') + '</ol>';
    }
    return html;
  }

  function renderResultados() {
    soltarPrevia();
    const caja = $('#resultados');
    if (!estado.terminos.length) { caja.hidden = true; caja.innerHTML = ''; return; }
    caja.hidden = false;
    if (busq.sobre) { caja.innerHTML = htmlSobre(busq.sobre); return; }
    const res = estado.resultados;
    const servidor = busq.fuente === 'servidor';
    const pie = servidor ? '' : pieLocal();
    const entidad = htmlEntidadBuscada();
    const errata = servidor ? busq.corregida : '';
    if (!res.length) { caja.innerHTML = errata + entidad + (entidad ? '' : '<p class="vacio">No encontré ninguna nota con eso.</p>') + pie; return; }
    const max = 40;
    const total = res.length;
    const ocultas = res.filter(r => !r.n._visible).length;
    const resto = total - Math.min(max, res.length);
    const ayudaTotal = servidor
      ? 'Las marca el grafo. ' + (busq.delServidor >= total ? 'Las ordena el servidor por relevancia.' : 'Las primeras ' + busq.delServidor + ' las ordena el servidor por relevancia; las demás tienen todas las palabras.') +
        (busq.total !== total ? ' El servidor encontró ' + busq.total + ' con alguna de las palabras.' : '')
      : '';
    caja.innerHTML = errata + entidad + '<div class="resultados-cabeza"' + (ayudaTotal ? ' title="' + esc(ayudaTotal) + '"' : '') + '>' + total + (total === 1 ? ' nota' : ' notas') + (servidor && total > 1 ? ', de la más a la menos relevante' : '') +
      (ocultas ? ' (' + ocultas + (ocultas === 1 ? ' oculta' : ' ocultas') + ' por filtros)' : '') + ' · <kbd>Enter</kbd> abre la primera</div>' +
      (servidor ? '<div class="resultados-acciones"><button type="button" class="boton-chico" data-sobre title="Junta lo que dicen las notas de este tema, por tipo, y qué leer primero">Qué sé sobre esto</button></div>' : '') +
      res.slice(0, max).map(r => r.secciones ? filaServidor(r) : filaLocal(r)).join('') +
      (resto > 0 ? '<p class="vacio">y ' + resto + ' más' + (servidor ? ' con menos relevancia' : '') + '. Afiná la búsqueda para verlas.</p>' : '') + pie;
  }

  const TOPE_ENTIDAD = 8;
  function htmlEntidadBuscada() {
    const x = busq.entidad;
    if (!x) return '';
    const cuantas = x.notas.length;
    const valores = x.hallados.map(e => '<code>' + esc(e.valor) + '</code>' +
      (e.tipo === 'archivos' && e.proyecto ? ' <span class="insignia">' + esc(e.proyecto) + '</span>' : '') +
      (e.tipo === 'commits' ? ' <span class="insignia"' + (e.asunto ? ' title="' + esc([e.fecha, e.asunto].filter(Boolean).join(' · ')) + '"' : '') + '>' + esc(e.repo || 'no está en git') + '</span>' : '')).join(', ');
    const fila = y => botonNota(y.nodo, y.linea);
    const abierta = busq.abiertas.has('entidad');
    const resto = x.notas.slice(TOPE_ENTIDAD);
    return '<div class="resultados-cabeza">Lo ' + (cuantas === 1 ? 'nombra 1 nota' : 'nombran ' + cuantas + ' notas') + ' · ' + valores + '</div>' +
      '<div class="resultado-caja resultado-entidad">' + x.notas.slice(0, TOPE_ENTIDAD).map(fila).join('') +
      (resto.length ? '<button type="button" class="resultado-plegar" data-plegar="entidad" aria-expanded="' + abierta + '">' + (abierta ? 'Ocultar ' : 'Ver ') + (resto.length === 1 ? 'otra nota' : 'otras ' + resto.length + ' notas') + '</button>' +
        '<div class="resultado-extras"' + (abierta ? '' : ' hidden') + '>' + resto.map(fila).join('') + '</div>' : '') + '</div>';
  }

  function irASeccion(titulo) {
    const buscada = normalizar(titulo).replace(/[^\p{L}\p{N}]+/gu, '');
    if (!buscada) return;
    const h = Array.from($('#panel-md').querySelectorAll('h1, h2, h3, h4, h5, h6')).find(x => normalizar(x.textContent).replace(/[^\p{L}\p{N}]+/gu, '') === buscada);
    if (h) h.scrollIntoView({ block: 'start', behavior: menosMovimiento.matches ? 'auto' : 'smooth' });
  }

  function abrirResultado(id, seccion) {
    irA(id, true);
    if (seccion) irASeccion(seccion);
    if (esMovil()) cerrarLateral();
  }

  function renderLista() {
    const cont = $('#lista');
    let items = nodosVisibles.slice();
    if (estado.coincidencias) items = items.filter(n => estado.coincidencias.has(n));
    const orden = $('#orden-lista').value;
    const porTitulo = (a, b) => a.titulo.localeCompare(b.titulo, 'es');
    const comparar = {
      nombre: porTitulo,
      conexiones: (a, b) => (b.grado - a.grado) || porTitulo(a, b),
      fecha: (a, b) => b.modificado.localeCompare(a.modificado) || porTitulo(a, b),
      grupo: (a, b) => grupoPorId.get(a.grupo).nombre.localeCompare(grupoPorId.get(b.grupo).nombre, 'es') || porTitulo(a, b)
    }[orden] || porTitulo;
    items.sort(comparar);
    const cabeza = '<div class="lista-cabeza">' + items.length + (items.length === 1 ? ' nota' : ' notas') +
      (estado.coincidencias ? ' que coinciden con la búsqueda' : '') + (items.length < nodos.length ? ' de ' + nodos.length : '') + '</div>';
    const entradas = [];
    let grupoActual = null;
    items.forEach(n => {
      if (orden === 'grupo' && n.grupo !== grupoActual) {
        grupoActual = n.grupo;
        entradas.push({ g: grupoPorId.get(n.grupo) });
      }
      entradas.push({ n });
    });
    const previo = cont.scrollTop;
    listaVirtual.entradas = items.length >= LISTA_VIRTUAL ? entradas : null;
    if (listaVirtual.entradas) {
      medirFilasLista(cont, cabeza, entradas);
      cont.innerHTML = cabeza + '<div class="lista-filas lista-virtual"><div style="height:' + listaVirtual.total + 'px"></div></div>';
      cont.scrollTop = previo;
      pintarTramoLista(true);
      return;
    }
    let html = cabeza + '<div class="lista-filas">' + entradas.map(htmlEntradaLista).join('') + '</div>';
    if (!items.length) html += '<p class="vacio" style="text-align:center">No hay notas para mostrar con estos filtros.</p>';
    cont.innerHTML = html;
  }

  const LISTA_VIRTUAL = 500;
  const MARGEN_LISTA = 600;
  const listaVirtual = { entradas: null, tops: [], grupoDe: [], total: 0, alto: null, desde: -1, hasta: -1, cuadro: 0 };

  function htmlEntradaLista(e) {
    if (e.g) return '<div class="lista-grupo">' + '<span class="punto" style="--c:' + e.g.color + '"></span>' + esc(e.g.nombre) + '</div>';
    const n = e.n;
    return '<button type="button" class="fila' + (estado.seleccionado === n ? ' activa' : '') + '" data-id="' + esc(n.id) + '">' + punto(n) +
      '<span class="fila-texto"><span class="fila-titulo">' + (estado.terminos.length ? marcar(n.titulo, estado.terminos) : esc(n.titulo)) + '</span>' +
      '<span class="fila-sub">' + esc(grupoPorId.get(n.grupo).nombre) + ' · ' + esc(nombreTipo(n.tipo)) + ' · ' + esc(n.ruta) + '</span></span>' +
      '<span class="fila-num" title="Conexiones">' + n.grado + '</span>' +
      '<span class="fila-fecha">' + esc(n.modificado) + '</span></button>';
  }

  function medirFilasLista(cont, cabeza, entradas) {
    const v = listaVirtual;
    const muestra = [entradas.find(e => e.n), entradas.find(e => e.g)].filter(Boolean);
    cont.innerHTML = cabeza + '<div class="lista-filas lista-virtual">' + muestra.map(htmlEntradaLista).join('') + '</div>';
    const fila = cont.querySelector('.lista-virtual > .fila');
    const grupo = cont.querySelector('.lista-virtual > .lista-grupo');
    v.alto = { fila: (fila ? fila.getBoundingClientRect().height : 52) + 2, grupo: (grupo ? grupo.getBoundingClientRect().height : 34) + 2 };
    let y = 0;
    let ultimoGrupo = -1;
    v.tops = new Float64Array(entradas.length);
    v.grupoDe = new Int32Array(entradas.length);
    entradas.forEach((e, i) => {
      if (e.g) ultimoGrupo = i;
      v.tops[i] = y;
      v.grupoDe[i] = ultimoGrupo;
      y += e.g ? v.alto.grupo : v.alto.fila;
    });
    v.total = y;
    v.desde = v.hasta = -1;
  }

  function pintarTramoLista(forzar) {
    const v = listaVirtual;
    const cont = $('#lista');
    const caja = cont.querySelector('.lista-virtual');
    if (!v.entradas || !caja || estado.vista !== 'lista') return;
    const arriba = cont.scrollTop - caja.offsetTop - MARGEN_LISTA;
    const abajo = cont.scrollTop - caja.offsetTop + cont.clientHeight + MARGEN_LISTA;
    const primera = (y) => {
      let a = 0, b = v.entradas.length;
      while (a < b) {
        const m = (a + b) >> 1;
        if (v.tops[m] < y) a = m + 1; else b = m;
      }
      return a;
    };
    const desde = Math.max(0, primera(arriba) - 1);
    const hasta = Math.min(v.entradas.length, primera(abajo) + 1);
    if (!forzar && desde === v.desde && hasta === v.hasta) return;
    v.desde = desde;
    v.hasta = hasta;
    const g = v.grupoDe[desde];
    const pegado = g >= 0 && g < desde ? htmlEntradaLista(v.entradas[g]) : '';
    const tope = v.tops[desde] - (pegado ? v.alto.grupo : 0);
    const resto = v.total - (hasta < v.entradas.length ? v.tops[hasta] : v.total);
    const enfocada = caja.contains(document.activeElement) ? document.activeElement.dataset.id : null;
    caja.innerHTML = '<div style="height:' + tope + 'px"></div>' + pegado + v.entradas.slice(desde, hasta).map(htmlEntradaLista).join('') +
      '<div style="height:' + resto + 'px"></div>';
    if (enfocada) {
      const b = caja.querySelector('.fila[data-id="' + CSS.escape(enfocada) + '"]');
      if (b) b.focus({ preventScroll: true });
    }
  }

  function pedirTramoLista() {
    if (!listaVirtual.entradas || listaVirtual.cuadro) return;
    listaVirtual.cuadro = requestAnimationFrame(() => {
      listaVirtual.cuadro = 0;
      pintarTramoLista(false);
    });
  }

  function marcarFilaLista() {
    if (estado.vista !== 'lista') return;
    $('#lista').querySelectorAll('.fila').forEach(f => f.classList.toggle('activa', !!estado.seleccionado && f.dataset.id === estado.seleccionado.id));
  }

  function cambiarVista(v, sinRecordar) {
    if (v === 'grafo' && estado.d3 === false) { aviso('El grafo no está disponible porque no cargó d3.'); return; }
    if (v === 'lista' && (presenta.anonimo || presenta.cine)) { v = 'grafo'; sinRecordar = true; }
    estado.vista = v;
    if (!sinRecordar) {
      try { localStorage.setItem('cerebro-vista', v); } catch (e) {}
    }
    document.querySelectorAll('[data-vista]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.vista === v)));
    lienzo.hidden = v !== 'grafo';
    pulso.hidden = v !== 'grafo';
    $('#vineta').hidden = v !== 'grafo';
    $('#lista').hidden = v !== 'lista';
    $('#resumen').hidden = v !== 'resumen';
    $('#orden-lista').hidden = v !== 'lista';
    $('#controles-grafo').hidden = v !== 'grafo' || !graficoListo;
    $('#contador').hidden = v !== 'grafo';
    $('#estado-grafo').hidden = v !== 'grafo' || graficoListo;
    ocultarTooltip();
    if (v === 'lista' || v === 'resumen') {
      detenerVida();
      vaciarEfectos();
      soltarPrevia();
      if (v === 'lista') renderLista(); else renderResumen();
    } else {
      pedirDibujo();
      programarAmbiente(1500);
      if (estado.seleccionado && completo()) {
        clearTimeout(anim.tDisparo);
        anim.tDisparo = setTimeout(() => disparar(estado.seleccionado), 150);
      }
    }
  }

  function activarLocal(n, saltos) {
    estado.local = { id: n.id, saltos: saltos || (estado.local ? estado.local.saltos : 1) };
    aplicarFiltros();
    encuadrarLuego();
    actualizarBotonLocal();
  }

  function salirLocal() {
    if (!estado.local) return;
    estado.local = null;
    aplicarFiltros();
    encuadrarLuego();
    actualizarBotonLocal();
  }

  function actualizarBandaLocal() {
    const banda = $('#banda-local');
    const n = estado.local && porId.get(estado.local.id);
    centro.classList.toggle('con-local', !!n);
    if (!n) { banda.hidden = true; banda.innerHTML = ''; return; }
    banda.hidden = false;
    banda.innerHTML = '<span>Solo las conexiones de <b>' + esc(publico('nota', n, recortar(n.titulo, 48))) + '</b></span>' +
      '<span class="saltos">Saltos: <button type="button" data-saltos="1" aria-pressed="' + (estado.local.saltos === 1) + '">1</button>' +
      '<button type="button" data-saltos="2" aria-pressed="' + (estado.local.saltos === 2) + '">2</button></span>' +
      '<button type="button" data-salir-local>Ver todo</button>';
    medirBanda();
  }

  function medirBanda() {
    const banda = $('#banda-local');
    if (banda.hidden) return;
    centro.style.setProperty('--alto-banda', banda.offsetHeight + 'px');
  }

  function actualizarBotonLocal() {
    const b = $('#ver-local');
    const activo = !!(estado.local && estado.seleccionado && estado.local.id === estado.seleccionado.id);
    b.setAttribute('aria-pressed', String(activo));
    b.textContent = activo ? 'Volver al grafo completo' : 'Ver solo sus conexiones';
  }

  function asegurarVisible(n) {
    if (n._visible) return;
    if (estado.local) {
      estado.local.id = n.id;
      aplicarFiltros();
      return;
    }
    const avisos = [];
    if (!estado.gruposOn.has(n.grupo)) { const g = grupoPorId.get(n.grupo); estado.gruposOn.add(n.grupo); avisos.push('el grupo «' + publico('grupo', g, g.nombre) + '»'); }
    if (!estado.proyectosOn.has(n.proyecto)) { const p = proyectoPorId.get(n.proyecto); estado.proyectosOn.add(n.proyecto); avisos.push('el proyecto «' + publico('proyecto', p, p.nombre) + '»'); }
    if (!estado.tiposOn.has(n.tipo)) { estado.tiposOn.add(n.tipo); avisos.push('el tipo «' + nombreTipo(n.tipo) + '»'); }
    if (!etiquetaVisible(n)) {
      (n.etiquetas.length ? n.etiquetas.map(e => e.toLowerCase()) : [SIN_ETIQUETA]).forEach(k => estado.etiquetasOn.add(k));
      avisos.push(n.etiquetas.length ? 'sus etiquetas' : 'las notas sin etiqueta');
    }
    sincronizarCasillas();
    aplicarFiltros();
    if (avisos.length) aviso('Volví a mostrar ' + avisos.join(' y ') + ' para que se vea la nota.');
  }

  function irA(id, centrar, sinPila) {
    const n = porId.get(id);
    if (!n) return;
    const anterior = estado.seleccionado;
    if (!sinPila && estado.seleccionado && estado.seleccionado !== n) {
      pila.push(estado.seleccionado.id);
      if (pila.length > 60) pila.shift();
    }
    if (estado.local && estado.local.id !== n.id && (centrar || !n._visible)) {
      estado.local.id = n.id;
      aplicarFiltros();
      encuadrarLuego();
    }
    asegurarVisible(n);
    const mostrar = !presenta.anonimo && !presenta.cine;
    if (mostrar) {
      abrirPanel(n);
      llevarFocoAlPanel();
    }
    clearTimeout(anim.tDisparo);
    if (centrar) {
      const dur = centrarEn(n);
      if (completo() && graficoListo) {
        const l = anterior && anterior !== n && anterior._visible ? aristaEntre(anterior, n) : null;
        if (l && dur) { anim.efectos.push({ tipo: 'cometa', l, desde: anterior, hacia: n, t0: performance.now(), dur, fuente: 'cometa' }); programarCuadro(); }
        anim.tDisparo = setTimeout(() => disparar(n), dur + 20);
      }
    } else if (completo()) anim.tDisparo = setTimeout(() => disparar(n), 40);
    if (mostrar) try { history.replaceState(null, '', '#n=' + encodeURIComponent(n.id)); } catch (e) {}
  }

  function llevarFocoAlPanel() {
    const activo = document.activeElement;
    if (!foco.teclado || !activo || activo === document.body || esCampo(activo)) return;
    if (!panel.contains(activo)) {
      foco.origen = activo;
      foco.origenId = activo.dataset ? activo.dataset.id || '' : '';
    }
    $('#panel-titulo').focus({ preventScroll: true });
  }

  function devolverFoco() {
    const volver = foco.origen && foco.origen.isConnected ? foco.origen
      : foco.origenId ? document.querySelector('[data-id="' + CSS.escape(foco.origenId) + '"]') : null;
    const adentro = panel.contains(document.activeElement);
    foco.origen = null;
    foco.origenId = '';
    if (volver && adentro) volver.focus({ preventScroll: true });
  }

  function cerrarPanel() {
    soltarPrevia();
    if (!estado.seleccionado && !panel.classList.contains('abierto')) return;
    devolverFoco();
    estado.seleccionado = null;
    estado.nombrada = null;
    pila.length = 0;
    panel.classList.remove('abierto');
    panel.setAttribute('aria-hidden', 'true');
    centro.classList.remove('con-panel');
    try { history.replaceState(null, '', location.pathname + location.search); } catch (e) {}
    actualizarVelo();
    marcarFilaLista();
    pedirDibujo();
  }

  function formatoBytes(b) {
    if (b < 1024) return b + ' B';
    return (b / 1024).toFixed(1).replace('.', ',') + ' KB';
  }

  function insigniasDatos(l) {
    const d = l.datos || {};
    const chips = [];
    if (l._mielina) chips.push('además se usan juntas en el trabajo (fuerza ' + l._mielina.toFixed(2).replace('.', ',') + ')');
    if (d.casiIgual) chips.push('casi iguales');
    if (d.puntaje !== undefined) chips.push('parecido ' + d.puntaje.toFixed(2).replace('.', ','));
    if (d.partesDe) chips.push('partes de ' + d.partesDe + ', a propósito');
    else if (d.hermanas === 'plantilla') chips.push('por plantilla, a propósito');
    else if (d.hermanas === 'partes') chips.push('partes de lo mismo: convendría enlazarlas');
    const nombres = d.cuantas || (d.comparten && l.clase !== 'parecida' ? d.comparten.length : 0);
    if (nombres) chips.push(nombres === 1 ? '1 nombre en común' : nombres + ' nombres en común');
    return chips.length ? '<div class="detalle">' + chips.map(c => '<span class="insignia">' + esc(c) + '</span>').join(' ') + '</div>' : '';
  }

  function tituloDatos(l) {
    const d = l.datos;
    if (!d || !d.comparten) return '';
    const etiqueta = l.clase === 'parecida' ? 'Palabras en común: ' : 'Nombran las dos: ';
    const resto = d.cuantas > d.comparten.length ? ' y ' + (d.cuantas - d.comparten.length) + ' más' : '';
    return ' title="' + esc(etiqueta + d.comparten.join(', ') + resto) + '"';
  }

  function htmlRelaciones(aristasNodo, lado) {
    if (!aristasNodo.length) return '<p class="vacio">Ninguna.</p>';
    const grupo = {};
    aristasNodo.forEach(l => { (grupo[l.clase] || (grupo[l.clase] = [])).push(l); });
    return ORDEN_CLASES.filter(c => grupo[c]).map(c => {
      const items = grupo[c].map(l => ({ l, o: lado === 'salientes' ? l.target : l.source }))
        .sort((x, y) => x.o.titulo.localeCompare(y.o.titulo, 'es'));
      const fuerte = c === 'sugerida' || c === 'duplicado' || c === 'parecida';
      return '<div class="rel-grupo"><div class="rel-cabeza">' + muestraLinea(c) + '<span>' + esc(CLASES[c].nombre) + '</span><span class="cuenta">' + items.length + '</span></div><ul>' +
        items.map(x => '<li' + tituloDatos(x.l) + '><button type="button" class="item-nodo" data-id="' + esc(x.o.id) + '" title="' + esc(x.o.ruta) + '">' + punto(x.o) +
          '<span class="t">' + esc(x.o.titulo) + '</span><span class="g">' + esc(grupoPorId.get(x.o.grupo).nombre) + '</span></button>' +
          (x.l.texto ? '<div class="motivo' + (fuerte ? ' fuerte' : '') + '">' + esc(x.l.texto) + '</div>' : '') + insigniasDatos(x.l) + '</li>').join('') +
        '</ul></div>';
    }).join('');
  }

  const ladoTexto = lado => ladoDe(lado) ? mayusculaInicial(lado) : '';
  const colorLado = lado => LADOS.length && LADOS[0].id === lado ? 'var(--acento)' : 'var(--texto-3)';
  const numeroHandoff = n => { const m = /_(\d+)$/.exec(n.slug || n.archivo.replace(/\.md$/i, '')); return m ? Number(m[1]) : null; };
  const nombreHandoff = n => { const k = numeroHandoff(n); const nombre = n.slug || n.archivo.replace(/\.md$/i, ''); return k !== null ? String(k) : (RE_PREFIJO_HANDOFF ? nombre.replace(RE_PREFIJO_HANDOFF, '') : nombre) || 'sin número'; };
  const fichaHandoff = n => [ladoTexto(n.lado), n.fecha ? fechaCorta(n.fecha) : ''].filter(Boolean).join(' · ');
  const ordenHilo = (a, b) => (numeroHandoff(a) ?? -1) - (numeroHandoff(b) ?? -1) ||
    (a.fecha || a.modificado.slice(0, 10)).localeCompare(b.fecha || b.modificado.slice(0, 10)) || a.titulo.localeCompare(b.titulo, 'es');

  function antesEnHilo(x) {
    const previos = x.respondeA.slice();
    x.entrantes.forEach(l => { if (l.clase === 'cadena') previos.push(l.source); });
    return previos;
  }

  function hiloDe(n) {
    const ya = new Set([n]);
    const cola = [n];
    while (cola.length && ya.size < 120) {
      const x = cola.shift();
      const vecinos = x.respondeA.concat(x.respondidoPor);
      x.salientes.forEach(l => { if (l.clase === 'cadena') vecinos.push(l.target); });
      x.entrantes.forEach(l => { if (l.clase === 'cadena') vecinos.push(l.source); });
      vecinos.forEach(v => { if (!ya.has(v)) { ya.add(v); cola.push(v); } });
    }
    const faltan = new Map();
    ya.forEach(x => faltan.set(x, new Set(antesEnHilo(x).filter(p => ya.has(p) && p !== x))));
    const orden = [];
    const listo = new Set();
    while (orden.length < ya.size) {
      let elegido = null;
      let libre = false;
      faltan.forEach((previos, x) => {
        if (listo.has(x)) return;
        const esLibre = Array.from(previos).every(p => listo.has(p));
        if ((esLibre && !libre) || (esLibre === libre && (!elegido || ordenHilo(x, elegido) < 0))) { elegido = x; libre = esLibre; }
      });
      listo.add(elegido);
      orden.push(elegido);
    }
    return orden;
  }

  function filaHilo(x) {
    const ficha = fichaHandoff(x);
    return '<li><button type="button" class="item-nodo" data-id="' + esc(x.id) + '" title="' + esc(x.ruta) + '">' + punto(x) + '<span class="t">' + esc(x.titulo) + '</span></button>' +
      (ficha ? '<div class="detalle">' + esc(ficha) + '</div>' : '') + '</li>';
  }

  function htmlHilo(n) {
    if (n.tipo !== 'handoff' && !n.respondeA.length && !n.respondidoPor.length) return '';
    const hilo = hiloDe(n);
    if (hilo.length < 2) return '';
    const grupoHilo = (titulo, xs, vacio) => '<div class="rel-grupo"><div class="rel-cabeza"><span>' + esc(titulo) + '</span><span class="cuenta">' + xs.length + '</span></div>' +
      (xs.length ? '<ul>' + xs.slice().sort(ordenHilo).map(filaHilo).join('') + '</ul>' : '<p class="vacio">' + esc(vacio) + '</p>') + '</div>';
    const lados = new Set(hilo.map(x => x.lado).filter(Boolean));
    const pasos = hilo.map(x => {
      const titulo = [x.titulo, fichaHandoff(x)].filter(Boolean).join(' · ');
      return '<button type="button" class="item-nodo" data-id="' + esc(x.id) + '" title="' + esc(titulo) + '"' + (x === n ? ' aria-current="true"' : '') + '>' +
        (x.lado ? '<span class="punto" style="--c:' + colorLado(x.lado) + '"></span>' : '') + '<span class="t">' + esc(nombreHandoff(x)) + '</span></button>';
    }).join('');
    const leyenda = lados.size ? '<div class="hilo-leyenda">' + LADOS.map(l => l.id).filter(l => lados.has(l)).map(l => '<span class="punto" style="--c:' + colorLado(l) + '"></span>' + esc(ladoTexto(l))).join(' ') + '</div>' : '';
    return '<div class="seccion-titulo">Hilo <span class="cuenta">· ' + hilo.length + ' notas</span></div>' +
      grupoHilo('Responde a', n.respondeA, 'No responde a ningún handoff.') +
      grupoHilo('Le responden', n.respondidoPor, 'Nadie le respondió todavía.') +
      '<div class="rel-grupo"><div class="rel-cabeza"><span>Todo el hilo, en orden</span></div><div class="candidatos hilo-pasos">' + pasos + '</div>' + leyenda + '</div>';
  }

  function htmlParecidas(n) {
    const xs = n.salientes.filter(l => l.clase === 'parecida').map(l => ({ l, o: l.target }))
      .concat(n.entrantes.filter(l => l.clase === 'parecida').map(l => ({ l, o: l.source })));
    if (!xs.length) return '';
    const puntaje = x => x.l.datos && x.l.datos.puntaje !== undefined ? x.l.datos.puntaje : -1;
    xs.sort((a, b) => puntaje(b) - puntaje(a) || a.o.titulo.localeCompare(b.o.titulo, 'es'));
    return '<div class="seccion-titulo">Parecidas <span class="cuenta">' + xs.length + '</span></div><div class="rel-grupo"><div class="rel-cabeza">' + muestraLinea('parecida') +
      '<span>Hablan de lo mismo; de la más a la menos parecida</span></div><ul>' + xs.map(x => {
        const d = x.l.datos || {};
        const chips = [];
        if (d.casiIgual) chips.push('casi iguales');
        if (d.puntaje !== undefined) chips.push('parecido ' + d.puntaje.toFixed(2).replace('.', ','));
        if (d.partesDe) chips.push('partes de ' + d.partesDe + ', a propósito');
        else if (d.hermanas === 'plantilla') chips.push('por plantilla, a propósito');
        else if (d.hermanas === 'partes') chips.push('partes de lo mismo: convendría enlazarlas');
        const palabras = d.comparten ? 'comparten ' + d.comparten.map(p => '<code>' + esc(p) + '</code>').join(', ') : '';
        const detalle = chips.map(c => '<span class="insignia">' + esc(c) + '</span>').join(' ') + (chips.length && palabras ? ' ' : '') + palabras;
        return '<li' + (x.l.texto ? ' title="' + esc(x.l.texto) + '"' : '') + '><button type="button" class="item-nodo" data-id="' + esc(x.o.id) + '">' + punto(x.o) +
          '<span class="t">' + esc(x.o.titulo) + '</span><span class="g">' + esc(grupoPorId.get(x.o.grupo).nombre) + '</span></button>' +
          (detalle ? '<div class="detalle">' + detalle + '</div>' : '') + '</li>';
      }).join('') + '</ul></div>';
  }

  const SIN_DIRECCION = new Set(['parecida', 'comparte']);

  function htmlComparte(n) {
    const xs = n.salientes.filter(l => l.clase === 'comparte').map(l => ({ l, o: l.target }))
      .concat(n.entrantes.filter(l => l.clase === 'comparte').map(l => ({ l, o: l.source })));
    if (!xs.length) return '';
    const cuantas = x => x.l.datos ? x.l.datos.cuantas || (x.l.datos.comparten || []).length : 0;
    xs.sort((a, b) => cuantas(b) - cuantas(a) || a.o.titulo.localeCompare(b.o.titulo, 'es'));
    return '<div class="seccion-titulo">Nombran lo mismo <span class="cuenta">' + xs.length + '</span></div><div class="rel-grupo"><div class="rel-cabeza">' + muestraLinea('comparte') +
      '<span>Citan los mismos archivos, commits o tablas</span></div><ul>' + xs.map(x => {
        const d = x.l.datos || {};
        const c = cuantas(x);
        const nombres = d.comparten || [];
        const resto = c > nombres.length ? ' y ' + (c - nombres.length) + ' más' : '';
        const detalle = (c ? '<span class="insignia">' + (c === 1 ? '1 nombre en común' : c + ' nombres en común') + '</span> ' : '') +
          (nombres.length ? 'comparten ' + nombres.map(p => '<code>' + esc(p) + '</code>').join(', ') + esc(resto) : '');
        return '<li' + tituloDatos(x.l) + '><button type="button" class="item-nodo" data-id="' + esc(x.o.id) + '">' + punto(x.o) +
          '<span class="t">' + esc(x.o.titulo) + '</span><span class="g">' + esc(grupoPorId.get(x.o.grupo).nombre) + '</span></button>' +
          (detalle ? '<div class="detalle">' + detalle + '</div>' : '') + '</li>';
      }).join('') + '</ul></div>';
  }

  const panelNombra = { abiertos: new Set() };
  const TOPE_NOMBRA = 12;

  function filaEntidad(n, x, clave) {
    const e = x.e;
    const otras = e.notas.filter(y => y.nodo !== n);
    const abierta = !!(estado.nombrada && estado.nombrada.clave === clave);
    let etiqueta = '';
    if (e.tipo === 'archivos' && e.proyecto) etiqueta = '<span class="insignia">' + esc(e.proyecto) + '</span>';
    else if (e.tipo === 'commits') etiqueta = '<span class="insignia">' + esc(e.repo || 'no está en git') + '</span>';
    const cuenta = otras.length ? (otras.length === 1 ? '1 nota más' : otras.length + ' notas más') : 'solo esta';
    const cuerpo = '<span class="t"><code>' + esc(e.valor) + '</code></span>' + etiqueta + (x.linea ? '<span class="linea-chica">:' + x.linea + '</span>' : '') + '<span class="g">' + esc(cuenta) + '</span>';
    const titulo = (e.tipo === 'commits' ? [e.sha || e.valor, e.fecha, e.asunto].filter(Boolean).join(' · ') : e.valor) + (x.linea ? ', línea ' + x.linea : '');
    const detalle = e.tipo === 'commits' && (e.fecha || e.asunto) ? '<div class="detalle">' + esc([e.fecha ? fechaCorta(e.fecha) : '', e.asunto].filter(Boolean).join(' · ')) + '</div>' : '';
    const boton = otras.length
      ? '<button type="button" class="item-nodo item-entidad" data-entidad="' + esc(clave) + '" aria-expanded="' + abierta + '" title="' + esc(titulo + '. Clic: las otras notas que lo nombran') + '">' + cuerpo + '</button>'
      : '<div class="item-nodo item-entidad sola" title="' + esc(titulo + '. Ninguna otra nota lo nombra') + '">' + cuerpo + '</div>';
    return '<li>' + boton + detalle + (abierta ? '<div class="candidatos">' + otras.map(y => botonNota(y.nodo, y.linea)).join('') + '</div>' : '') + '</li>';
  }

  function htmlNombra(n) {
    const m = n.nombra;
    if (!m) return '';
    const total = TIPOS_ENTIDAD.reduce((s, t) => s + m[t[0]].length, 0);
    if (!total) return '';
    return '<div class="seccion-titulo">Nombra <span class="cuenta">' + total + '</span></div>' + TIPOS_ENTIDAD.filter(t => m[t[0]].length).map(([tipo, nombre]) => {
      const items = m[tipo];
      const tope = panelNombra.abiertos.has(tipo) || items.length <= TOPE_NOMBRA + 3 ? items.length : TOPE_NOMBRA;
      return '<div class="rel-grupo"><div class="rel-cabeza"><span>' + esc(nombre) + '</span><span class="cuenta">' + items.length + '</span></div><ul>' +
        items.slice(0, tope).map((x, i) => filaEntidad(n, x, tipo + ':' + i)).join('') + '</ul>' +
        (items.length > tope ? '<button type="button" class="boton-chico ver-mas" data-tipo="' + esc(tipo) + '">Ver ' + (items.length - tope) + ' más</button>' : '') + '</div>';
    }).join('');
  }

  function pintarNombra(n) {
    const caja = $('#panel-nombra');
    const html = htmlNombra(n);
    caja.innerHTML = html;
    caja.hidden = !html;
  }

  function marcarEntidad(clave) {
    const n = estado.seleccionado;
    if (!n || !n.nombra) return;
    if (estado.nombrada && estado.nombrada.clave === clave) estado.nombrada = null;
    else {
      const p = String(clave).split(':');
      const x = n.nombra[p[0]] && n.nombra[p[0]][Number(p[1])];
      if (!x) return;
      const ns = new Set(x.e.notas.map(y => y.nodo));
      ns.add(n);
      const as = new Set();
      n.salientes.forEach(l => { if (ns.has(l.target)) as.add(l); });
      n.entrantes.forEach(l => { if (ns.has(l.source)) as.add(l); });
      estado.nombrada = { clave, nota: n, nodos: ns, aristas: as };
      const ocultas = x.e.notas.filter(y => y.nodo !== n && !y.nodo._visible).length;
      if (ocultas) aviso(ocultas === 1 ? 'Una de las notas que lo nombran está oculta por los filtros.' : ocultas + ' de las notas que lo nombran están ocultas por los filtros.');
    }
    pintarNombra(n);
    pedirDibujo();
  }

  function abrirPanel(n) {
    const yaAbierto = panel.classList.contains('abierto');
    if (estado.seleccionado !== n) {
      estado.nombrada = null;
      panelNombra.abiertos.clear();
    }
    soltarPrevia();
    panel.style.setProperty('--c-panel', colorDe(n));
    estado.seleccionado = n;
    const g = grupoPorId.get(n.grupo);
    const p = proyectoPorId.get(n.proyecto);
    const chip = (color, nombre) => '<span class="chip"><span class="punto" style="--c:' + color + '"></span>' + esc(nombre) + '</span>';
    $('#panel-chips').innerHTML = chip(vivo.calor ? colorDe(n) : g.color, g.nombre) + (hayProyectos ? chip(p.color, p.nombre) : '') +
      '<span class="chip">' + muestraTipo(n.tipo) + esc(nombreTipo(n.tipo)) + '</span>' +
      n.etiquetas.map(e => '<span class="chip etiqueta">#' + esc(e) + '</span>').join('');
    $('#panel-titulo').textContent = n.titulo;
    $('#panel-ruta').textContent = n.ruta || '(sin ruta)';
    $('#abrir-obsidian').hidden = !enlaceObsidian(n);
    const desc = $('#panel-desc');
    desc.textContent = n.descripcion;
    desc.hidden = !n.descripcion;
    const metaNota = $('#panel-nota-meta');
    metaNota.textContent = n.metaNota;
    metaNota.hidden = !n.metaNota;
    const porQuePista = $('#panel-pista');
    porQuePista.textContent = publico('texto', null, vivo.porQuePista ? vivo.porQuePista(n) : '');
    porQuePista.hidden = !porQuePista.textContent;
    const meta = [
      ['Modificado', n.modificado || '—'],
      ['Líneas', String(n.lineas)],
      ['Tamaño', formatoBytes(n.bytes)],
      ['Conexiones', String(n.grado)]
    ];
    if (n.slug && TIPOS_MEMORIA.has(n.tipo)) meta.push(['Nombre para enlazar', n.slug]);
    if (n.lado) meta.push(['Lo escribe', mayusculaInicial(ladoDe(n.lado).nombre)]);
    if (n.fecha) meta.push(['Fecha', n.fecha]);
    $('#panel-meta').innerHTML = meta.map(m => '<div><dt>' + esc(m[0]) + '</dt><dd>' + esc(m[1]) + '</dd></div>').join('');
    const prob = $('#panel-problemas');
    prob.hidden = !n.problemas.length;
    prob.innerHTML = n.problemas.map(p => '<li class="' + p.tono + '">' + (p.tono === 'revisar' ? '<span class="insignia">a revisar</span>' : '') + esc(p.texto) +
      (p.linea ? ' <span class="linea">(línea ' + p.linea + ')</span>' : '') + (p.arreglo ? '<span class="arreglo">→ ' + esc(p.arreglo) + '</span>' : '') + '</li>').join('');
    const hilo = $('#panel-hilo');
    hilo.innerHTML = htmlHilo(n);
    hilo.hidden = !hilo.innerHTML;
    const salientes = n.salientes.filter(l => !SIN_DIRECCION.has(l.clase));
    const entrantes = n.entrantes.filter(l => !SIN_DIRECCION.has(l.clase));
    $('#cuenta-salientes').textContent = salientes.length;
    $('#cuenta-entrantes').textContent = entrantes.length;
    $('#rel-salientes').innerHTML = htmlRelaciones(salientes, 'salientes');
    $('#rel-entrantes').innerHTML = htmlRelaciones(entrantes, 'entrantes');
    const parecidas = $('#panel-parecidas');
    parecidas.innerHTML = htmlParecidas(n) + htmlComparte(n);
    parecidas.hidden = !parecidas.innerHTML;
    pintarNombra(n);
    renderizarContenido(n);
    $('#panel-scroll').scrollTop = 0;
    $('#panel-volver').hidden = !pila.length;
    panel.classList.add('abierto');
    panel.removeAttribute('aria-hidden');
    centro.classList.toggle('con-panel', !esMovil());
    actualizarBotonLocal();
    actualizarVelo();
    marcarFilaLista();
    pedirDibujo();
    if (yaAbierto && anim.modo !== 'nada') {
      const ps = $('#panel-scroll');
      ps.classList.remove('entrando');
      void ps.offsetWidth;
      ps.classList.add('entrando');
      clearTimeout(anim.tPanel);
      anim.tPanel = setTimeout(() => ps.classList.remove('entrando'), 450);
    }
  }

  const RE_BARRA_DE_RUTA = /(?<=[\w:\]\)])\\(?=[_.\-\[\]$~#@!{}()+',;=&%])/g;
  function protegerRutas(md) {
    const lineas = md.split('\n');
    let valla = null;
    for (let i = 0; i < lineas.length; i++) {
      const l = lineas[i];
      const m = /^\s{0,3}(`{3,}|~{3,})/.exec(l);
      if (valla) {
        if (m && m[1][0] === valla[0] && m[1].length >= valla.length) valla = null;
        continue;
      }
      if (m) { valla = m[1]; continue; }
      if (l.indexOf('\\') < 0) continue;
      lineas[i] = l.split(/(`+[^`]*`+)/).map((trozo, j) => {
        if (j % 2 === 0) return trozo.replace(RE_BARRA_DE_RUTA, '\\\\');
        const m = /^(`+)([^`]*\\)\1$/.exec(trozo);
        return m ? '`` ' + m[2] + ' ``' : trozo;
      }).join('');
    }
    return lineas.join('\n');
  }

  function markdownAHtml(md) {
    const M = window.marked;
    if (!M) return null;
    try {
      md = protegerRutas(md);
      if (typeof M.parse === 'function') return M.parse(md, { gfm: true, breaks: false, async: false });
      if (typeof M === 'function') return M(md);
    } catch (e) {
      console.warn('Neuromapa: marked no pudo con esta nota', e);
    }
    return null;
  }

  const PROHIBIDAS = new Set(['script', 'style', 'iframe', 'frame', 'frameset', 'object', 'embed', 'link', 'meta', 'base', 'form', 'textarea', 'select', 'button', 'svg', 'math', 'template', 'noscript', 'audio', 'video', 'source', 'dialog']);
  function sanear(raiz) {
    Array.from(raiz.querySelectorAll('*')).forEach(el => {
      const tag = el.tagName.toLowerCase();
      if (PROHIBIDAS.has(tag)) { el.remove(); return; }
      Array.from(el.attributes).forEach(at => {
        const nombre = at.name.toLowerCase();
        const valor = at.value.replace(/[\u0000- \u007f-\u009f]/g, '');
        if (nombre.startsWith('on') || nombre === 'style' || nombre === 'srcset' || nombre === 'formaction' || nombre === 'id' || nombre === 'name' || nombre === 'ping' || nombre === 'background') el.removeAttribute(at.name);
        else if ((nombre === 'href' || nombre === 'src' || nombre === 'xlink:href' || nombre === 'action' || nombre === 'poster') && /^(javascript|vbscript|data):/i.test(valor) && !(tag === 'img' && /^data:image\//i.test(valor))) el.removeAttribute(at.name);
      });
      if (tag === 'input') {
        if ((el.getAttribute('type') || '').toLowerCase() !== 'checkbox') el.remove();
        else el.setAttribute('disabled', '');
      }
    });
  }

  function resolverPuntos(p) {
    const salida = [];
    p.split('/').forEach((x, i) => {
      if (x === '' && i === 0) { salida.push(''); return; }
      if (x === '' || x === '.') return;
      if (x === '..') { if (salida.length > 1) salida.pop(); return; }
      salida.push(x);
    });
    return salida.join('/');
  }

  function rutaAbsoluta(href, n) {
    let h;
    try { h = decodeURIComponent(href); } catch (e) { h = href; }
    h = h.replace(/[?#].*$/, '').replace(/^file:\/\/\/?/i, '').replace(/\\/g, '/').trim();
    if (!h) return null;
    if (/^\/[a-zA-Z]\//.test(h)) h = h[1] + ':' + h.slice(2);
    if (/^[a-zA-Z]:\//.test(h) || h.startsWith('/')) return resolverPuntos(h);
    const r = n.ruta.replace(/\\/g, '/');
    const corte = r.lastIndexOf('/');
    if (corte < 0) return null;
    return resolverPuntos(r.slice(0, corte) + '/' + h);
  }

  function resolverRuta(href, n) {
    const abs = rutaAbsoluta(href, n);
    return abs ? porRuta.get(normRuta(abs)) || null : null;
  }

  function conMdSiFalta(href) {
    const corte = href.search(/[?#]/);
    const base = corte < 0 ? href : href.slice(0, corte);
    if (!base || /\/$/.test(base) || /\.md$/i.test(base) || RE_ADJUNTO.test(base) || /^[a-z][a-z0-9+.\-]+:/i.test(base)) return null;
    return base + '.md' + (corte < 0 ? '' : href.slice(corte));
  }

  function resolverPorCola(href, n) {
    const cola = normRuta(decodificar(href).replace(/[?#].*$/, '')).replace(/^(\.\.?\/)+/, '').replace(/^\/+/, '');
    if (!cola || !/\.md$/.test(cola)) return null;
    const cands = nodos.filter(o => normRuta(o.ruta).endsWith('/' + cola));
    if (cands.length === 1) return cands[0];
    return cands.find(o => o.grupo === n.grupo) || null;
  }

  function enlazarNota(a, destino) {
    a.setAttribute('href', '#n=' + encodeURIComponent(destino.id));
    a.setAttribute('data-nodo', destino.id);
    a.setAttribute('title', destino.ruta);
    a.classList.add('enlace-nota');
  }

  function enlaceObsidian(n) {
    const o = n && n.obsidian;
    if (!o || typeof o.boveda !== 'string' || !o.boveda || typeof n.ruta !== 'string' || !n.ruta) return '';
    return 'obsidian://open?path=' + encodeURIComponent(n.ruta);
  }

  function aUrlArchivo(abs) {
    if (abs.startsWith('/')) return 'file://' + abs.split('/').map(encodeURIComponent).join('/');
    return 'file:///' + abs.split('/').map((s, i) => (i === 0 && /^[a-zA-Z]:$/.test(s)) ? s : encodeURIComponent(s)).join('/');
  }

  function resolverWikiConCarpeta(s, desde) {
    const propia = rutaAbsoluta(s + '.md', desde);
    const enSuCarpeta = propia ? porRuta.get(normRuta(propia)) || null : null;
    if (/^\.\.?\//.test(s)) return enSuCarpeta;
    const cola = '/' + s.replace(/^\/+/, '') + '.md';
    const cands = desde.salientes.filter(l => l.clase === 'wiki' && normRuta(l.target.ruta).endsWith(cola)).map(l => l.target);
    if (cands.length === 1) return cands[0];
    return cands.find(o => o === enSuCarpeta) || null;
  }

  function resolverWiki(slug, desde) {
    const s = slug.trim().toLowerCase().replace(/\\/g, '/').replace(/\.md$/, '');
    if (s.indexOf('/') >= 0) return resolverWikiConCarpeta(s, desde);
    const coincide = o => o.slug.toLowerCase() === s || o.archivo.toLowerCase().replace(/\.md$/, '') === s;
    const arista = desde.salientes.find(l => l.clase === 'wiki' && coincide(l.target));
    if (arista) return arista.target;
    return coincide(desde) ? desde : null;
  }

  function ajustarEnlaces(raiz, n) {
    raiz.querySelectorAll('a[href]').forEach(a => {
      const href = a.getAttribute('href') || '';
      if (/^(https?:|mailto:)/i.test(href)) { a.setAttribute('target', '_blank'); a.setAttribute('rel', 'noopener noreferrer'); return; }
      if (href.startsWith('#')) { a.removeAttribute('href'); return; }
      const destino = resolverRuta(href, n);
      if (destino) { enlazarNota(a, destino); return; }
      const conMd = conMdSiFalta(href);
      const sinExtension = conMd ? resolverRuta(conMd, n) || resolverPorCola(conMd, n) : null;
      if (sinExtension) { enlazarNota(a, sinExtension); return; }
      const esNota = /\.md$/i.test(href.replace(/[?#].*$/, ''));
      if (esNota && rotosPorNota.has(claveEnlace(n.id, href))) {
        a.removeAttribute('href');
        a.classList.add('enlace-roto');
        a.setAttribute('title', 'Enlace roto: no lleva a ninguna nota del cerebro (' + decodificar(href) + ')');
        return;
      }
      const porCola = esNota ? resolverPorCola(href, n) : null;
      if (porCola) { enlazarNota(a, porCola); return; }
      const abs = ES_ARCHIVO_LOCAL ? rutaAbsoluta(href, n) : null;
      if (abs) {
        a.setAttribute('href', aUrlArchivo(abs));
        a.setAttribute('target', '_blank');
        a.setAttribute('rel', 'noopener');
        a.setAttribute('title', esNota ? 'No está en el cerebro: ' + abs : abs);
      } else {
        a.removeAttribute('href');
        if (esNota) a.setAttribute('title', 'No está en el cerebro: ' + decodificar(href));
      }
    });
    raiz.querySelectorAll('img').forEach(img => {
      img.setAttribute('loading', 'lazy');
      img.setAttribute('referrerpolicy', 'no-referrer');
      const src = img.getAttribute('src') || '';
      if (/^https?:/i.test(src)) {
        const enlace = document.createElement('a');
        enlace.setAttribute('href', src);
        enlace.setAttribute('target', '_blank');
        enlace.setAttribute('rel', 'noopener noreferrer');
        enlace.setAttribute('title', src);
        enlace.textContent = '[' + (img.getAttribute('alt') || 'imagen') + ': imagen de internet, no se carga sola]';
        img.replaceWith(enlace);
        return;
      }
      if (!src || /^data:image\//i.test(src)) return;
      const abs = ES_ARCHIVO_LOCAL ? rutaAbsoluta(src, n) : null;
      if (abs) img.setAttribute('src', aUrlArchivo(abs));
      else img.removeAttribute('src');
    });
  }

  const RE_WIKI = /\[\[(?![^\[\]\n]*(?:\{\{|<%))([^\[\]\n|#]+)(#[^\[\]\n|]*)?(\|[^\[\]\n]*)?\]\]/g;
  const RE_ADJUNTO = /\.(?!md$)[a-z][a-z0-9]{0,7}$/i;
  function convertirWiki(raiz, n) {
    const doc = raiz.ownerDocument || document;
    const recorrido = doc.createTreeWalker(raiz, NodeFilter.SHOW_TEXT);
    const textos = [];
    while (recorrido.nextNode()) {
      const t = recorrido.currentNode;
      if (t.nodeValue.indexOf('[[') < 0) continue;
      if (t.parentElement && t.parentElement.closest('code, pre, a')) continue;
      textos.push(t);
    }
    textos.forEach(t => {
      const s = t.nodeValue;
      const frag = doc.createDocumentFragment();
      let ultimo = 0;
      let hubo = false;
      let m;
      RE_WIKI.lastIndex = 0;
      while ((m = RE_WIKI.exec(s))) {
        hubo = true;
        const incrustado = m.index > ultimo && s[m.index - 1] === '!' ? 1 : 0;
        if (m.index - incrustado > ultimo) frag.appendChild(doc.createTextNode(s.slice(ultimo, m.index - incrustado)));
        const slug = m[1].trim();
        const alias = m[3] ? m[3].slice(1).trim() : '';
        const destino = resolverWiki(slug, n);
        const adjunto = !destino && RE_ADJUNTO.test(slug);
        const ambigua = !destino && !adjunto && ambiguosPorNota.has(n.id + '\u0001' + m[0].toLowerCase());
        const a = doc.createElement(ambigua || adjunto ? 'span' : 'a');
        a.textContent = alias || slug;
        if (destino) {
          a.setAttribute('href', '#n=' + encodeURIComponent(destino.id));
          a.setAttribute('data-nodo', destino.id);
          a.setAttribute('title', destino.titulo);
          a.className = 'enlace-nota wiki';
        } else if (adjunto) {
          a.className = 'adjunto wiki';
          a.setAttribute('title', 'Archivo adjunto, no es una nota: ' + slug);
        } else if (ambigua) {
          a.className = 'enlace-ambiguo wiki';
          a.setAttribute('title', 'Varias notas calzan con «' + slug + '»; mirá las menciones ambiguas en Salud');
        } else {
          a.className = 'enlace-roto wiki';
          a.setAttribute('title', 'Ninguna nota tiene el slug «' + slug + '»');
        }
        frag.appendChild(a);
        ultimo = m.index + m[0].length;
      }
      if (!hubo) return;
      if (ultimo < s.length) frag.appendChild(doc.createTextNode(s.slice(ultimo)));
      t.parentNode.replaceChild(frag, t);
    });
  }

  function renderizarContenido(n) {
    const destino = $('#panel-md');
    const front = $('#panel-front');
    let md = n.texto;
    const m = /^﻿?---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/.exec(md);
    if (m) {
      front.hidden = false;
      front.open = false;
      $('#panel-front-texto').textContent = m[1];
      md = md.slice(m[0].length);
    } else {
      front.hidden = true;
    }
    const recorte = $('#panel-recorte');
    recorte.hidden = !n.recortado;
    recorte.textContent = 'El texto está recortado a los primeros 60 000 caracteres.' + (busq.servidor === true ? ' El buscador sí lee la nota entera.' : '');
    destino.textContent = '';
    if (!md.trim()) { destino.innerHTML = '<p class="vacio">La nota no tiene texto.</p>'; return; }
    const html = markdownAHtml(md);
    if (html == null) {
      if (estado.markedOk === false) {
        const nota = document.createElement('p');
        nota.className = 'vacio';
        nota.textContent = 'No cargó marked, así que la nota se ve como texto plano.';
        destino.appendChild(nota);
      }
      const pre = document.createElement('pre');
      pre.className = 'texto-plano';
      pre.textContent = md;
      destino.appendChild(pre);
      return;
    }
    const plantilla = document.createElement('template');
    plantilla.innerHTML = html;
    sanear(plantilla.content);
    ajustarEnlaces(plantilla.content, n);
    convertirWiki(plantilla.content, n);
    destino.appendChild(plantilla.content);
  }

  async function copiar(texto) {
    try {
      await navigator.clipboard.writeText(texto);
      return true;
    } catch (e) {}
    try {
      const ta = document.createElement('textarea');
      ta.value = texto;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      ta.remove();
      return ok;
    } catch (e) {
      return false;
    }
  }

  function abrirLateral() {
    lateral.classList.add('abierto');
    actualizarVelo();
  }
  function cerrarLateral() {
    lateral.classList.remove('abierto');
    actualizarVelo();
  }
  function actualizarVelo() {
    const hay = esMovil() && (lateral.classList.contains('abierto') || panel.classList.contains('abierto'));
    $('#velo').hidden = !hay;
    $('#lateral-cabeza').hidden = !esMovil();
  }

  let D3 = null;
  let sim = null;
  let fuerzaEnlaces = null;
  let zoom = null;
  let seleccionLienzo = null;
  let transformacion = { k: 1, x: 0, y: 0, invertX: x => x, invertY: y => y };
  let graficoListo = false;
  let usuarioMovio = false;
  let arrastrando = null;
  let cursorNota = null;
  let centroPendiente = null;
  let ancho = 1;
  let alto = 1;
  let dpr = 1;
  let colores = {};
  let dibujoPendiente = false;
  let esperaCuadro = 0;
  let enCuadro = false;
  let pedidoEnCuadro = false;
  let escenaSucia = false;
  const anim = {
    pref: true, nivel: 2, modo: 'completo', oscuro: false,
    ahora: 0, escenaHasta: 0, efectos: [], previa: null, pulsoSucio: false, sprites: new Map(),
    aA: 1, aN: 1, aE: 1, tFoco: 0, focoPrevio: null, focoSoltado: 0, encendido: null,
    tsPrevio: 0, encadenado: false, tsListo: 0, muestras: 0, malas: 0, dtBase: Infinity, lentosSeguidos: 0, escala: 1,
    msVentana: 0, msSano: 0, bajadas: [], subidas: 0, esperaSubir: 20000,
    ultimaActividad: 0, sobrePanel: false, ultimaChispa: null,
    tAmbiente: 0, tHover: 0, tDisparo: 0, tPanel: 0, tLogo: 0,
    descargasVivas: [], tEtq: 0, cuadroEtq: 0, firmaTapas: 0, resplandor: true, tRec: 0, penNota: 1, enfoque: true,
    aristasLivianas: false, gira: false, dibujoLiviano: false, cajasTexto: [], masivoForzado: false, porSoftware: false
  };
  const TAU = Math.PI * 2;
  const MASIVO = 800;
  const MS_MUY_LENTO = 125;
  const MS_MALO = 34;
  const MS_CALMA = 33;
  const MS_CALMA_MINIMO = 80;
  const MS_SUENO = 66;
  const CALMA_MS = 3000;
  const CHAT_QUIETO = 180000;
  const RE_SOFTWARE = /swiftshader|llvmpipe|softpipe|basic render|software/i;
  const LENTOS_PARA_MINIMO = 8;
  let capaAristas = null;
  const completo = () => anim.modo === 'completo';
  const sale3 = p => 1 - Math.pow(1 - p, 3);
  const entraSale = p => p < 0.5 ? 4 * p * p * p : 1 - Math.pow(2 - 2 * p, 3) / 2;
  const seno = p => 0.5 - 0.5 * Math.cos(Math.PI * p);
  const atras = p => 1 + 2.2 * Math.pow(p - 1, 3) + 1.2 * Math.pow(p - 1, 2);
  const limitar = v => Math.min(1, Math.max(0, v));
  const hashArista = l => l._h === undefined ? (l._h = hashTexto(l.source.id + '>' + l.target.id)) : l._h;
  const suaveR = (a, b, x) => { const t = limitar((x - a) / (b - a)); return t * t * (3 - 2 * t); };

  const DORMIR_MS = 120000;
  const REPOSO = { pensando: 0, trabajando: 0.2, espera: 0.5, calma: 0.5, sueno: 1 };
  const ritmo = {
    estado: 'calma', reposo: 0.5, luz: 1, sueno: 0, giro: 1, pesos: new Float32Array([0.28, 1, 0, 0]),
    t: 0, desperto: 0, proximoSueno: 0, huso: 0, repaso: 0, ensueno: null, aguanta: 0
  };
  const HUELLAS = 16;
  const FOCOS_MAX = 24;
  const bufFoco = new Float32Array(FOCOS_MAX * 4);
  const bufFocoCol = new Float32Array(FOCOS_MAX * 4);
  const brasas = { notas: new Map(), lista: [], golpes: [], tElegir: 0, activo: false, ultimoT: 0 };
  const CHOQUES = 4;
  const gestos = { choques: [], apreton: null, barrido: null, contraer: 0, suspiro: 0, hay: false, t: -1 };
  const INTRO = {
    latidos: [110, 400], explota: 700, reparto: 1200, azar: 150, vuelo: 1000, remolino: 2.4,
    clima: 2900, dur: 1700, lote: 260, nace: 420, nombres: 4700, fin: 5300, esc: 2, tilt: 0.35, rayos: 14,
    color: ['#0891b2', '#a5f3fc']
  };
  const saltar = p => 1 + 2.70158 * Math.pow(p - 1, 3) + 1.70158 * Math.pow(p - 1, 2);
  const tiempoIntro = ahora => cerebro && cerebro.introT0 ? (ahora === undefined ? performance.now() : ahora) - cerebro.introT0 : 1e9;
  const introCorriendo = ahora => tiempoIntro(ahora) < INTRO.fin;
  const fundidoIntro = (desde, dura, ahora) => limitar((tiempoIntro(ahora) - desde) / dura);

  function estadoVigilia(ahora) {
    let trabaja = false;
    let piensa = false;
    let espera = false;
    if (vivo.chats) {
      for (const c of vivo.chats.values()) {
        if (ahora - c.tUlt > CHAT_QUIETO) continue;
        if (c.estado === 'trabajando' || c.estado === 'compactando') {
          trabaja = true;
          if (c.enCurso.size) piensa = true;
        } else if (c.estado === 'esperando') espera = true;
      }
    }
    if (piensa) return 'pensando';
    if (trabaja) return 'trabajando';
    if (espera) return 'espera';
    return ahora - anim.ultimaActividad < DORMIR_MS ? 'calma' : 'sueno';
  }

  function actualizarRitmo(ahora) {
    const dt = ritmo.t ? Math.min(250, Math.max(0, ahora - ritmo.t)) : 1e9;
    ritmo.t = ahora;
    const antes = ritmo.estado;
    ritmo.estado = estadoVigilia(ahora);
    if (ritmo.estado === 'sueno' && antes !== 'sueno') {
      ritmo.proximoSueno = ahora + 9000 + Math.random() * 4000;
      if (vivo.prepararSuenos && completo()) vivo.prepararSuenos();
    }
    const meta = REPOSO[ritmo.estado];
    const a = completo() ? 1 - Math.exp(-dt / (meta < ritmo.reposo ? 900 : 3000)) : 1;
    ritmo.reposo += (meta - ritmo.reposo) * a;
    const r = ritmo.reposo;
    const metaG = ritmo.estado === 'espera' ? 1 : 0;
    ritmo.aguanta += (metaG - ritmo.aguanta) * (completo() ? 1 - Math.exp(-dt / (metaG ? 500 : 300)) : 1);
    const g = ritmo.aguanta;
    ritmo.sueno = suaveR(0.6, 1, r);
    const pleno = brasas.activo ? 0.9 : 1;
    ritmo.luz = Math.max(0.7, (pleno - (pleno - 0.78) * r * r) * (1 - 0.08 * g) * (1 - 0.2 * gestos.suspiro));
    ritmo.giro = (1 - ritmo.sueno) * (1 - 0.5 * g);
    const p = ritmo.pesos;
    p[0] = 0.1 + 0.9 * suaveR(0.5, 1, r);
    p[1] = limitar(1 - Math.abs(r - 0.5) / 0.35) * (1 - 0.7 * g);
    p[2] = 1 - suaveR(0, 0.5, r);
    p[3] = ritmo.sueno;
    return ritmo;
  }

  const EEG_N = 200;
  const EEG_W = 184;
  const EEG_H = 30;
  const EEG_PASO = 25;
  const EEG_COLOR = { sueno: ['#4f46e5', '#a5b4fc'], calma: ['#0f766e', '#5eead4'], espera: ['#a16207', '#fde047'], trabajando: ['#0369a1', '#7dd3fc'], pensando: ['#be185d', '#f9a8d4'] };
  const EEG_TEXTO = { sueno: 'durmiendo', calma: 'en calma', espera: 'espera tu OK', trabajando: 'trabajando', pensando: 'pensando' };
  const eeg = { el: $('#eeg'), cv: $('#eeg-traza'), txt: $('#eeg-estado'), cx: null, v: new Float32Array(EEG_N), i: 0, reloj: 0, picos: [], texto: '', color: '', dpr: 0, trazo: null, sucio: true };

  function marcarPicoEEG(f) {
    const forma = [1.05, -0.6, 0.28, -0.1];
    for (let k = 0; k < forma.length; k++) eeg.picos[k] = Math.max(-1.5, Math.min(1.5, (eeg.picos[k] || 0) + forma[k] * f));
  }

  function muestraEEG(ms) {
    const w = ritmo.pesos;
    const s = ms / 1000;
    let v = w[0] * 0.8 * Math.sin(TAU * 0.9 * s)
      + w[1] * 0.5 * Math.sin(TAU * 2.2 * s) * (0.7 + 0.3 * Math.sin(TAU * s / 5))
      + w[2] * (0.22 * Math.sin(TAU * 8.5 * s + 1.7 * Math.sin(TAU * 0.7 * s)) + 0.2 * (Math.random() - 0.5))
      + 0.05 * (Math.random() - 0.5);
    const u = (ms - ritmo.huso) / 1000;
    if (ritmo.huso && u >= 0 && u < 1) v += 0.4 * Math.sin(Math.PI * u) * Math.sin(TAU * 11 * s);
    if (eeg.picos.length) v += eeg.picos.shift() || 0;
    return Math.max(-1.25, Math.min(1.25, v));
  }

  function dibujarEEG(ahora) {
    const el = eeg.el;
    if (!el || !eeg.cv) return;
    const ver = completo() && graficoListo && estado.vista === 'grafo';
    if (el.hidden === ver) el.hidden = !ver;
    if (!ver) { eeg.reloj = 0; return; }
    if (!eeg.reloj || ahora - eeg.reloj > 2000) eeg.reloj = ahora - EEG_PASO;
    while (eeg.reloj + EEG_PASO <= ahora) {
      eeg.reloj += EEG_PASO;
      eeg.v[eeg.i] = muestraEEG(eeg.reloj);
      eeg.i = (eeg.i + 1) % EEG_N;
      eeg.sucio = true;
    }
    let texto = EEG_TEXTO[ritmo.estado] || '';
    if (ritmo.estado === 'sueno' && ritmo.ensueno && ahora < ritmo.ensueno.hasta) texto = ritmo.ensueno.texto;
    else if (ahora < ritmo.repaso) texto = 'repasa lo que vivió';
    else if (ahora - ritmo.desperto < 2500 && ritmo.desperto) texto = 'despertando';
    if (texto !== eeg.texto) { eeg.texto = texto; eeg.txt.textContent = texto; }
    if (esMovil() || centro.classList.contains('con-panel')) return;
    const par = EEG_COLOR[ritmo.estado] || EEG_COLOR.calma;
    const color = par[anim.oscuro ? 1 : 0];
    const d = window.devicePixelRatio || 1;
    if (eeg.dpr !== d) {
      eeg.dpr = d;
      eeg.cv.width = Math.round(EEG_W * d);
      eeg.cv.height = Math.round(EEG_H * d);
      eeg.cx = eeg.cv.getContext('2d');
      eeg.color = '';
    }
    const c = eeg.cx;
    if (!c) return;
    if (color !== eeg.color) {
      eeg.color = color;
      el.style.setProperty('--c', color);
      eeg.trazo = c.createLinearGradient(0, 0, EEG_W, 0);
      eeg.trazo.addColorStop(0, aRgba(color, 0));
      eeg.trazo.addColorStop(0.35, aRgba(color, 0.55));
      eeg.trazo.addColorStop(1, aRgba(color, 1));
      eeg.sucio = true;
    }
    if (!eeg.sucio) return;
    eeg.sucio = false;
    c.setTransform(d, 0, 0, d, 0, 0);
    c.clearRect(0, 0, EEG_W, EEG_H);
    c.lineWidth = 1.4;
    c.lineJoin = 'round';
    c.strokeStyle = eeg.trazo;
    c.beginPath();
    let x = 0;
    let y = 0;
    for (let k = 0; k < EEG_N; k++) {
      x = 2 + k / (EEG_N - 1) * (EEG_W - 7);
      y = EEG_H / 2 - eeg.v[(eeg.i + k) % EEG_N] * EEG_H * 0.36;
      if (k) c.lineTo(x, y);
      else c.moveTo(x, y);
    }
    c.stroke();
    c.fillStyle = color;
    c.beginPath();
    c.arc(x, y, 2.2, 0, TAU);
    c.fill();
  }

