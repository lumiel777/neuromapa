  function datosResumen() {
    const clave = n => estado.porProyecto ? n.proyecto : n.grupo;
    const juntos = new Map();
    nodos.forEach(n => {
      if (!n._visible) return;
      const k = clave(n);
      if (!juntos.has(k)) {
        const origen = estado.porProyecto ? proyectoPorId.get(k) : grupoPorId.get(k);
        if (!origen) return;
        juntos.set(k, { id: k, nombre: publico(estado.porProyecto ? 'proyecto' : 'grupo', origen, origen.nombre),
                        color: origen.color, notas: 0, adentro: 0 });
      }
      juntos.get(k).notas++;
    });
    const cruces = new Map();
    aristas.forEach(l => {
      if (!l._visible) return;
      const a = clave(l.source);
      const b = clave(l.target);
      if (!juntos.has(a) || !juntos.has(b)) return;
      if (a === b) { juntos.get(a).adentro++; return; }
      const llave = a < b ? a + '\u0001' + b : b + '\u0001' + a;
      cruces.set(llave, (cruces.get(llave) || 0) + 1);
    });
    return { grupos: [...juntos.values()].sort((x, y) => y.notas - x.notas), cruces };
  }

  function renderResumen() {
    const caja = $('#resumen');
    if (!caja || estado.vista !== 'resumen') return;
    const { grupos: lista, cruces } = datosResumen();
    if (!lista.length) {
      caja.innerHTML = '<p class="resumen-vacio">No hay notas visibles con los filtros de ahora.</p>';
      return;
    }
    const ancho = Math.max(320, caja.clientWidth || 900);
    const alto = Math.max(320, caja.clientHeight || 600);
    const cx = ancho / 2;
    const cy = alto / 2;
    const maximo = Math.max(...lista.map(g => g.notas));
    const radioMayor = Math.min(70, Math.max(26, Math.min(ancho, alto) / (lista.length > 8 ? 9 : 6)));
    const radio = g => 10 + (radioMayor - 10) * Math.sqrt(g.notas / maximo);
    const orbita = Math.max(0, Math.min(ancho, alto) / 2 - radioMayor - 34);
    const lugar = new Map();
    lista.forEach((g, i) => {
      const angulo = lista.length === 1 ? 0 : -Math.PI / 2 + (2 * Math.PI * i) / lista.length;
      const r = lista.length === 1 ? 0 : orbita;
      lugar.set(g.id, { x: cx + r * Math.cos(angulo), y: cy + r * Math.sin(angulo), r: radio(g) });
    });
    const mayorCruce = Math.max(1, ...cruces.values());
    const lineas = [...cruces.entries()].sort((x, y) => x[1] - y[1]).map(([llave, cuantas]) => {
      const [a, b] = llave.split('\u0001');
      const pa = lugar.get(a);
      const pb = lugar.get(b);
      const qx = cx + (pa.x + pb.x - 2 * cx) * 0.25;
      const qy = cy + (pa.y + pb.y - 2 * cy) * 0.25;
      const grosor = 0.8 + 5 * Math.sqrt(cuantas / mayorCruce);
      const ga = lista.find(g => g.id === a);
      const gb = lista.find(g => g.id === b);
      return '<path class="resumen-cruce" d="M' + pa.x.toFixed(1) + ',' + pa.y.toFixed(1) + ' Q' + qx.toFixed(1) + ',' + qy.toFixed(1) +
        ' ' + pb.x.toFixed(1) + ',' + pb.y.toFixed(1) + '" stroke="' + ga.color + '" stroke-width="' + grosor.toFixed(2) +
        '" stroke-opacity="' + (0.25 + 0.5 * cuantas / mayorCruce).toFixed(2) + '"><title>' + esc(ga.nombre) + ' ↔ ' + esc(gb.nombre) +
        ': ' + cuantas + (cuantas === 1 ? ' conexión' : ' conexiones') + '</title></path>';
    });
    const circulos = lista.map(g => {
      const p = lugar.get(g.id);
      const debajo = p.y + p.r + 16;
      return '<g class="resumen-grupo" tabindex="0" role="button" data-resumen="' + esc(g.id) + '" aria-label="' + esc(g.nombre) + ': ' +
        g.notas + ' notas. Ver solo este grupo en el grafo">' +
        '<circle cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="' + (p.r * 1.9).toFixed(1) + '" fill="url(#aura-' + esc(g.id) + ')"/>' +
        '<circle cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="' + p.r.toFixed(1) + '" fill="' + g.color + '" fill-opacity="0.85"/>' +
        '<text class="resumen-cuenta" x="' + p.x.toFixed(1) + '" y="' + (p.y + 4).toFixed(1) + '">' + g.notas + '</text>' +
        '<text class="resumen-nombre" x="' + p.x.toFixed(1) + '" y="' + debajo.toFixed(1) + '">' + esc(g.nombre) + '</text>' +
        '<title>' + esc(g.nombre) + ': ' + g.notas + (g.notas === 1 ? ' nota' : ' notas') + ', ' + g.adentro +
        ' conexiones adentro. Clic: ver solo este grupo en el grafo.</title></g>';
    });
    const auras = lista.map(g => '<radialGradient id="aura-' + esc(g.id) + '"><stop offset="0" stop-color="' + g.color +
      '" stop-opacity="0.45"/><stop offset="1" stop-color="' + g.color + '" stop-opacity="0"/></radialGradient>');
    caja.innerHTML = '<svg class="resumen-svg" viewBox="0 0 ' + ancho + ' ' + alto + '" width="' + ancho + '" height="' + alto +
      '" role="img" aria-label="Resumen: un círculo por ' + (estado.porProyecto ? 'proyecto' : 'grupo') +
      ' y líneas con las conexiones entre ellos"><defs>' + auras.join('') + '</defs>' + lineas.join('') + circulos.join('') + '</svg>' +
      '<p class="resumen-pie">Un círculo por ' + (estado.porProyecto ? 'proyecto' : 'grupo') + ' (el tamaño, sus notas) y una línea por ' +
      'cada par que se conecta (el grosor, cuántas conexiones). Clic en uno para verlo solo en el grafo.</p>';
  }

  function abrirGrupoDelResumen(id) {
    if (estado.porProyecto) estado.proyectosOn = new Set([id]); else estado.gruposOn = new Set([id]);
    sincronizarCasillas();
    cambiarVista('grafo');
    aplicarFiltros();
    encuadrarLuego();
  }

  $('#resumen').addEventListener('click', ev => {
    const g = ev.target.closest('[data-resumen]');
    if (g) abrirGrupoDelResumen(g.dataset.resumen);
  });
  $('#resumen').addEventListener('keydown', ev => {
    const g = ev.target.closest('[data-resumen]');
    if (g && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); abrirGrupoDelResumen(g.dataset.resumen); }
  });
  window.addEventListener('resize', () => { if (estado.vista === 'resumen') renderResumen(); });
