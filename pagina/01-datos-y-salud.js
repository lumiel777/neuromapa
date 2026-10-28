
  const URL_D3_DISPATCH = 'https://cdn.jsdelivr.net/npm/d3-dispatch@3.0.1/dist/d3-dispatch.min.js';
  const URL_D3_TIMER = 'https://cdn.jsdelivr.net/npm/d3-timer@3.0.1/dist/d3-timer.min.js';
  const URL_D3_QUADTREE = 'https://cdn.jsdelivr.net/npm/d3-quadtree@3.0.1/dist/d3-quadtree.min.js';
  const URL_D3_FORCE = 'https://cdn.jsdelivr.net/npm/d3-force@3.0.0/dist/d3-force.min.js';
  const URL_D3_SELECTION = 'https://cdn.jsdelivr.net/npm/d3-selection@3.0.0/dist/d3-selection.min.js';
  const URL_D3_COLOR = 'https://cdn.jsdelivr.net/npm/d3-color@3.1.0/dist/d3-color.min.js';
  const URL_D3_INTERPOLATE = 'https://cdn.jsdelivr.net/npm/d3-interpolate@3.0.1/dist/d3-interpolate.min.js';
  const URL_D3_EASE = 'https://cdn.jsdelivr.net/npm/d3-ease@3.0.1/dist/d3-ease.min.js';
  const URL_D3_TRANSITION = 'https://cdn.jsdelivr.net/npm/d3-transition@3.0.1/dist/d3-transition.min.js';
  const URL_D3_DRAG = 'https://cdn.jsdelivr.net/npm/d3-drag@3.0.0/dist/d3-drag.min.js';
  const URL_D3_ZOOM = 'https://cdn.jsdelivr.net/npm/d3-zoom@3.0.0/dist/d3-zoom.min.js';
  const URLS_D3 = [URL_D3_DISPATCH, URL_D3_TIMER, URL_D3_QUADTREE, URL_D3_FORCE, URL_D3_SELECTION, URL_D3_COLOR,
    URL_D3_INTERPOLATE, URL_D3_EASE, URL_D3_TRANSITION, URL_D3_DRAG, URL_D3_ZOOM];
  const URL_MARKED = 'https://cdn.jsdelivr.net/npm/marked@15.0.12/marked.min.js';
  const INTEGRIDAD = {
    [URL_D3_DISPATCH]: 'sha384-oGUk7ZMuIJXyjegrWZrjUkxuWZHJoUPTeaUNKzjcEhND8HzfagI4EnXVspF2mP60',
    [URL_D3_TIMER]: 'sha384-brChTSJXF1bpEGi+e8fNotmiEQtehLbv5EWt3njlDFlYjl/SwmXs4xofe0gvWd7E',
    [URL_D3_QUADTREE]: 'sha384-JzQQZeN94rbeGRpksNSu8TCkRWLlzTHev53JZngDT0faxrmd9bApgXS5pZWShqJb',
    [URL_D3_FORCE]: 'sha384-RM+ykRJc5/xPC56TVMOAYbZeVThoKXqcRlmRHZZc3YDHDCvFJrsEH2dpLMqL50K8',
    [URL_D3_SELECTION]: 'sha384-fpYWL7ZUVumFD+3Y+L5o9OvTX/TBgQKoQ/UP8BzGkkMTvfU9gS8NIxSoKmFgeVLs',
    [URL_D3_COLOR]: 'sha384-qeVKt5ofZEKt0cTx+PBxfcG00yP7tP+dESNy1bdg/QgA7dx9IEHR84+rXyR2U/Ss',
    [URL_D3_INTERPOLATE]: 'sha384-2PtmDWTi6j7xzzZdS7tLjZbKPqs6g738z+tlEHvzaPZ8tCXfypcL9nM0lO4+x3Xe',
    [URL_D3_EASE]: 'sha384-nV1dItG2cnmVo0ARHWr7XTKtTdKUmmbFG/S39sols78GivHGU38wdTSoX1iHd0y6',
    [URL_D3_TRANSITION]: 'sha384-0c9jWBqxuPPTuHvcYIdVLHOyNLsF+m5ppPOLueV/2KwXrX0zS1QpJSFYakCCM+dj',
    [URL_D3_DRAG]: 'sha384-sAq90GY25dIKenXjQl9K8xE3pd/N8B+QsrJECTNtohj84V34wnomgaxzTKqUrQK8',
    [URL_D3_ZOOM]: 'sha384-tR/iQ/4wI7mv99DI7giopwPD/nED+xAff2iNFp77OVE5+v/xxqaTa7YplKBoxAWP',
    [URL_MARKED]: 'sha384-948ahk4ZmxYVYOc+rxN1H2gM1EJ2Duhp7uHtZ4WSLkV4Vtx5MUqnV+l7u9B+jFv+'
  };
  const USA_D3 = ['forceSimulation', 'forceLink', 'forceManyBody', 'forceCollide', 'forceX', 'forceY', 'select', 'zoom',
    'zoomIdentity', 'drag', 'easeCubicInOut'];
  const ESPERA_LIBS = 12000;
  const DATOS = window.CEREBRO;

  const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  const $ = (sel, raiz) => (raiz || document).querySelector(sel);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ESCAPES[c]);

  if (!DATOS || typeof DATOS !== 'object' || !Array.isArray(DATOS.nodos)) {
    $('#app').hidden = true;
    $('#sin-datos').hidden = false;
    return;
  }

  const textoDe = v => (typeof v === 'string' ? v : '');
  const USUARIO = textoDe(DATOS.usuario);
  const CARPETA_CEREBRO = textoDe(DATOS.carpeta);
  const PROYECTOS = (Array.isArray(DATOS.proyectos) ? DATOS.proyectos : []).filter(p => p && typeof p.raiz === 'string' && typeof p.alias === 'string');
  const PROYECTO_PRINCIPAL = PROYECTOS.length ? PROYECTOS[0].alias : '';
  const RAIZ_PRUEBA = PROYECTOS.length ? PROYECTOS[0].raiz.replace(/[\\/]+$/, '') : 'C:\\proyecto';
  const ALIAS_RUTAS = (Array.isArray(DATOS.aliasRutas) ? DATOS.aliasRutas : []).filter(p => Array.isArray(p) && p.length === 2 && p.every(x => typeof x === 'string'));
  const HANDOFFS = DATOS.handoffs && typeof DATOS.handoffs === 'object' ? DATOS.handoffs : {};
  const LADOS = (Array.isArray(HANDOFFS.lados) ? HANDOFFS.lados : []).filter(l => l && typeof l.id === 'string' && l.id && typeof l.nombre === 'string');
  const PREFIJO_HANDOFF = typeof HANDOFFS.prefijo === 'string' ? HANDOFFS.prefijo : '';
  const RE_PREFIJO_HANDOFF = PREFIJO_HANDOFF ? new RegExp('^' + PREFIJO_HANDOFF.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '_?', 'i') : null;
  const ladoDe = id => LADOS.find(l => l.id === id) || null;
  const mayusculaInicial = s => s.charAt(0).toUpperCase() + s.slice(1);

  const ORDEN_CLASES = ['wiki', 'indice', 'enlace', 'responde', 'mencion', 'carpeta', 'cadena', 'sugerida', 'parecida', 'comparte', 'aprendida', 'duplicado'];
  const ORDEN_DIBUJO = ['aprendida', 'comparte', 'parecida', 'mencion', 'carpeta', 'indice', 'cadena', 'responde', 'enlace', 'wiki', 'sugerida', 'duplicado'];
  const CLASES = Object.assign(Object.create(null), {
    wiki: { nombre: 'Enlace [[…]]', ayuda: 'Una nota enlaza a otra con [[nombre-de-la-nota]]', ancho: 2.4, alfa: 0.75, guion: null, tinta: 'lineaFuerte', distancia: 42, fuerza: 0.8 },
    indice: { nombre: 'Índice', ayuda: 'Un MEMORY.md lista esta nota', ancho: 0.9, alfa: 0.4, guion: null, tinta: 'linea', distancia: 70, fuerza: 0.35 },
    enlace: { nombre: 'Enlace', ayuda: 'Enlace de Markdown: [texto](archivo.md)', ancho: 1.5, alfa: 0.6, guion: null, tinta: 'linea', distancia: 60, fuerza: 0.5 },
    responde: { nombre: 'Responde', ayuda: 'Un handoff responde a otro (lo dice su cabecera)', ancho: 1.2, alfa: 0.55, guion: null, tinta: 'linea', distancia: 20, fuerza: 0.9 },
    mencion: { nombre: 'Mención', ayuda: 'El texto nombra a la otra nota por ruta o por nombre', ancho: 0.7, alfa: 0.22, guion: null, tinta: 'linea', distancia: 95, fuerza: 0.12 },
    carpeta: { nombre: 'Carpeta', ayuda: 'La nota cita un archivo de la carpeta de este LEEME', ancho: 0.6, alfa: 0.2, guion: null, tinta: 'linea', distancia: 100, fuerza: 0.1 },
    cadena: { nombre: 'Cadena', ayuda: 'Sigue al anterior (el handoff no dice a quién responde)', ancho: 1, alfa: 0.45, guion: [2, 3], tinta: 'linea', distancia: 16, fuerza: 1 },
    sugerida: { nombre: 'Sugerida', ayuda: 'Conexión que convendría agregar', ancho: 1.6, alfa: 0.85, guion: [6, 4], tinta: 'acento', distancia: 80, fuerza: 0.05, debil: true },
    parecida: { nombre: 'Parecida', ayuda: 'Hablan de lo mismo y ninguna nombra a la otra (detectado por el texto)', ancho: 1.1, alfa: 0.5, guion: [2, 4], tinta: 'acento', distancia: 90, fuerza: 0.03, debil: true, sinCuenta: true },
    comparte: { nombre: 'Comparte', ayuda: 'Nombran los mismos archivos, commits o tablas', ancho: 0.8, alfa: 0.4, guion: [1, 4], tinta: 'linea', distancia: 110, fuerza: 0.02, debil: true, sinCuenta: true, apagada: true },
    aprendida: { nombre: 'Aprendida', ayuda: 'Se usan juntas en el trabajo real (lo aprendió del uso; si no se repite, se olvida). Si ya estaban conectadas, esa conexión se engrosa y los pulsos corren más rápido por ella', ancho: 1.3, alfa: 0.7, guion: [2, 3], tinta: 'acento', distancia: 120, fuerza: 0.02, debil: true, sinCuenta: true, porPeso: true },
    duplicado: { nombre: 'Duplicado', ayuda: 'Dos notas que parecen decir lo mismo', ancho: 1.7, alfa: 0.9, guion: [10, 3, 2, 3], tinta: 'peligro', distancia: 40, fuerza: 0.1, debil: true }
  });
  const TIPOS = Object.assign(Object.create(null), {
    instrucciones: { nombre: 'Instrucciones', ayuda: 'CLAUDE.md y parecidos' },
    indice: { nombre: 'Índice', ayuda: 'El MEMORY.md de una memoria' },
    user: { nombre: 'Usuario', ayuda: 'Memoria sobre ' + (USUARIO || 'el usuario') },
    feedback: { nombre: 'Cómo trabajar', ayuda: 'Memoria sobre cómo trabajar (en la ficha, type: feedback)' },
    project: { nombre: 'Proyecto', ayuda: 'Memoria sobre el estado de un proyecto' },
    reference: { nombre: 'Referencia', ayuda: 'Memoria sobre dónde está algo' },
    doc: { nombre: 'Documento', ayuda: 'Cualquier otro .md' },
    handoff: { nombre: 'Handoff', ayuda: 'Pedido o respuesta entre chats' }
  });
  const TIPOS_MEMORIA = new Set(['user', 'feedback', 'project', 'reference', 'indice']);
  const PALETA = ['#7c6cf0', '#2bb0a6', '#e0803a', '#d2508a', '#4a90e2', '#8bbd3c', '#c9a227', '#9b59b6', '#e05555', '#3fa7d6'];
  const ES_ARCHIVO_LOCAL = location.protocol === 'file:';
  const FUENTE = '12px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  const FUENTE_FUERTE = '600 12.5px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  const LETRA = 'px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  let escalaTexto = 1;
  let FUENTE_ROTULO = '600 11' + LETRA;
  let FUENTE_TOQUES = '500 10' + LETRA;
  let FUENTE_CARTEL = '650 12' + LETRA;

  const colorValido = c => (typeof c === 'string' && /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(c)) ? c : null;
  const recortar = (s, n) => {
    if (s.length <= n) return s;
    const corte = s.slice(0, n - 1);
    const i = corte.lastIndexOf(' ');
    return (i >= n * 0.55 ? corte.slice(0, i) : corte).replace(/[\s,;:.·—–-]+$/, '') + '…';
  };
  const SEPARADORES_TITULO = [': ', ' — ', ' – '];
  function tituloCorto(n, max) {
    const t = n.titulo;
    if (t.length <= max) return t;
    if (n.tipo !== 'handoff') {
      for (const sep of SEPARADORES_TITULO) {
        const i = t.indexOf(sep);
        if (i >= 16 && i <= max) return t.slice(0, i);
      }
    }
    return recortar(t, max);
  }
  const nombreArchivo = r => String(r || '').split(/[\\/]/).pop();
  const normalizar = s => String(s == null ? '' : s).toLowerCase().normalize('NFKD').replace(/\p{M}/gu, '').replace(/\\/g, '/');
  const normRuta = p => String(p || '').normalize('NFC').replace(/\\/g, '/').replace(/\/{2,}/g, '/').toLowerCase();
  const nombreTipo = t => (TIPOS[t] && TIPOS[t].nombre) || t;

  const grupos = [];
  const grupoPorId = new Map();
  function agregarGrupo(id, nombre, color) {
    const g = { id, nombre, color: colorValido(color) || PALETA[grupos.length % PALETA.length], cantidad: 0, ax: 0, ay: 0 };
    grupos.push(g);
    grupoPorId.set(id, g);
    return g;
  }
  (Array.isArray(DATOS.grupos) ? DATOS.grupos : []).forEach(g => {
    if (!g || g.id == null || grupoPorId.has(String(g.id))) return;
    agregarGrupo(String(g.id), String(g.nombre || g.id), g.color);
  });

  const proyectos = [];
  const proyectoPorId = new Map();
  function agregarProyecto(id, nombre, color) {
    const p = { id, nombre, color: colorValido(color) || PALETA[proyectos.length % PALETA.length], cantidad: 0 };
    proyectos.push(p);
    proyectoPorId.set(id, p);
    return p;
  }
  (Array.isArray(DATOS.gruposDeProyecto) ? DATOS.gruposDeProyecto : []).forEach(p => {
    if (!p || p.id == null || proyectoPorId.has(String(p.id))) return;
    agregarProyecto(String(p.id), String(p.nombre || p.id), p.color);
  });

  const nodos = [];
  const porId = new Map();
  DATOS.nodos.forEach(d => {
    if (!d || d.id == null || porId.has(String(d.id))) return;
    const n = {
      id: String(d.id),
      titulo: String(d.titulo || d.slug || nombreArchivo(d.ruta) || d.id),
      ruta: String(d.ruta || ''),
      grupo: String(d.grupo || 'sin-grupo'),
      proyecto: String(d.proyecto || ''),
      tipo: String(d.tipo || 'doc'),
      slug: String(d.slug || ''),
      descripcion: String(d.descripcion || ''),
      modificado: String(d.modificado || ''),
      lineas: Number(d.lineas) || 0,
      bytes: Number(d.bytes) || 0,
      texto: String(d.texto || ''),
      recortado: d.recortado === true || String(d.texto || '').length >= 60000,
      fecha: /^\d{4}-\d{2}-\d{2}$/.test(String(d.fecha || '')) ? String(d.fecha) : '',
      lado: ladoDe(d.lado) ? d.lado : '',
      responde: Array.isArray(d.responde) ? d.responde.map(String) : [],
      metaNota: String(d.meta || '').trim(),
      obsidian: d.obsidian && typeof d.obsidian === 'object' ? { boveda: String(d.obsidian.boveda || ''), archivo: String(d.obsidian.archivo || '') } : null,
      etiquetas: Array.isArray(d.etiquetas) ? d.etiquetas.map(String).filter(Boolean).slice(0, 40) : [],
      respondeA: [],
      respondidoPor: [],
      nombra: null,
      salientes: [],
      entrantes: [],
      grado: 0,
      r: 5,
      importante: false,
      problemas: []
    };
    n.archivo = nombreArchivo(n.ruta) || n.id;
    if (!grupoPorId.has(n.grupo)) agregarGrupo(n.grupo, n.grupo, null);
    if (!proyectoPorId.has(n.proyecto)) agregarProyecto(n.proyecto, 'Sin proyecto', '#868E96');
    if (!TIPOS[n.tipo]) TIPOS[n.tipo] = { nombre: n.tipo, ayuda: '' };
    nodos.push(n);
    porId.set(n.id, n);
  });
  nodos.forEach(n => { grupoPorId.get(n.grupo).cantidad++; proyectoPorId.get(n.proyecto).cantidad++; });
  const SIN_ETIQUETA = '';
  const etiquetaPorClave = new Map();
  nodos.forEach(n => n.etiquetas.forEach(e => {
    const clave = e.toLowerCase();
    if (!etiquetaPorClave.has(clave)) etiquetaPorClave.set(clave, { clave, nombre: e, cantidad: 0 });
    etiquetaPorClave.get(clave).cantidad++;
  }));
  const ETIQUETAS = Array.from(etiquetaPorClave.values()).sort((a, b) => b.cantidad - a.cantidad || a.nombre.localeCompare(b.nombre));
  const clavesEtiquetas = () => [SIN_ETIQUETA].concat(ETIQUETAS.map(e => e.clave));
  const hayProyectos = proyectos.filter(p => p.cantidad > 0).length > 1;
  const proyectoDelGrupo = new Map();
  grupos.forEach(g => {
    const cuenta = new Map();
    nodos.forEach(n => { if (n.grupo === g.id) cuenta.set(n.proyecto, (cuenta.get(n.proyecto) || 0) + 1); });
    let mejor = null;
    cuenta.forEach((c, id) => { if (!mejor || c > cuenta.get(mejor)) mejor = id; });
    if (mejor !== null) proyectoDelGrupo.set(g.id, proyectoPorId.get(mejor));
  });

  const aristas = [];
  let descartadas = 0;
  const vistas = new Set();
  const datosArista = d => {
    const x = {};
    let hay = false;
    if (typeof d.puntaje === 'number' && isFinite(d.puntaje)) { x.puntaje = d.puntaje; hay = true; }
    if (Array.isArray(d.comparten) && d.comparten.length) { x.comparten = d.comparten.map(String); hay = true; }
    if (Number(d.cuantas) > 0) { x.cuantas = Number(d.cuantas); hay = true; }
    if (typeof d.peso === 'number' && isFinite(d.peso)) { x.peso = Math.max(0, Math.min(1, d.peso)); hay = true; }
    if (d.hermanas === 'plantilla' || d.hermanas === 'partes') { x.hermanas = d.hermanas; hay = true; }
    if (typeof d.partesDe === 'string' && d.partesDe) { x.partesDe = d.partesDe; hay = true; }
    if (d.casiIgual === true) { x.casiIgual = true; hay = true; }
    return hay ? x : null;
  };
  const nivelPeso = l => {
    const p = l.datos && l.datos.peso;
    return typeof p !== 'number' ? 1 : p >= 0.6 ? 3 : p >= 0.35 ? 2 : 1;
  };
  (Array.isArray(DATOS.aristas) ? DATOS.aristas : []).forEach(d => {
    if (d && d.equivale && CLASES[d.equivale]) return;
    const a = d && porId.get(String(d.de));
    const b = d && porId.get(String(d.a));
    if (!a || !b || a === b || !CLASES[d.clase]) { descartadas++; return; }
    const clave = d.clase + '\u0001' + a.id + '\u0001' + b.id;
    if (vistas.has(clave)) return;
    vistas.add(clave);
    const l = { source: a, target: b, clase: d.clase, texto: String(d.texto || ''), datos: datosArista(d), _visible: false };
    aristas.push(l);
    a.salientes.push(l);
    b.entrantes.push(l);
    if (!CLASES[d.clase].debil) { a.grado++; b.grado++; }
  });
  const nivelUso = w => w >= 0.6 ? 3 : w >= 0.35 ? 2 : w > 0 ? 1 : 0;
  function fundirAprendidas(lista) {
    lista.forEach(l => { l._mielina = 0; l._sobre = null; });
    lista.forEach(l => {
      if (l.clase !== 'aprendida') return;
      const peso = (l.datos && l.datos.peso) || 0;
      const debajo = l.source.salientes.concat(l.source.entrantes)
        .filter(o => o.clase !== 'aprendida' && (o.source === l.target || o.target === l.target));
      if (!debajo.length) return;
      l._sobre = debajo;
      debajo.forEach(o => { o._mielina = Math.max(o._mielina, peso); });
    });
  }
  const tapada = l => !!l._sobre && l._sobre.some(o => o._visible);
  const usoDe = l => !estado.clasesOn.has('aprendida') ? 0 : l.clase === 'aprendida' ? (l.datos && l.datos.peso) || 0 : l._mielina || 0;
  fundirAprendidas(aristas);
  if (descartadas) console.warn('Neuromapa: ' + descartadas + ' aristas descartadas porque apuntan a notas que no existen o tienen una clase desconocida.');

  const unirRespuesta = (quien, a) => {
    if (!quien || !a || quien === a || quien.respondeA.includes(a)) return;
    quien.respondeA.push(a);
    a.respondidoPor.push(quien);
  };
  nodos.forEach(n => n.responde.forEach(id => unirRespuesta(n, porId.get(id))));
  aristas.forEach(l => { if (l.clase === 'responde') unirRespuesta(l.source, l.target); });

  const TIPOS_ENTIDAD = [['archivos', 'Archivos'], ['commits', 'Commits'], ['tablas', 'Tablas']];
  const ENTIDADES = DATOS.entidades && typeof DATOS.entidades === 'object' ? DATOS.entidades : {};
  const entidadesPorTipo = { archivos: [], commits: [], tablas: [] };
  TIPOS_ENTIDAD.forEach(([tipo]) => {
    (Array.isArray(ENTIDADES[tipo]) ? ENTIDADES[tipo] : []).forEach(d => {
      if (!d || d.valor == null || !Array.isArray(d.notas)) return;
      const ya = new Set();
      const notas = [];
      d.notas.forEach(x => {
        const nodo = Array.isArray(x) ? porId.get(String(x[0])) : null;
        if (!nodo || ya.has(nodo)) return;
        ya.add(nodo);
        notas.push({ nodo, linea: Number(x[1]) > 0 ? Number(x[1]) : 0 });
      });
      if (!notas.length) return;
      const e = {
        tipo,
        valor: String(d.valor),
        proyecto: String(d.proyecto || ''),
        sha: String(d.sha || ''),
        repo: d.repo ? String(d.repo) : null,
        fecha: String(d.fecha || ''),
        asunto: String(d.asunto || ''),
        notas
      };
      entidadesPorTipo[tipo].push(e);
      notas.forEach(x => {
        const m = x.nodo.nombra || (x.nodo.nombra = { archivos: [], commits: [], tablas: [] });
        m[tipo].push({ e, linea: x.linea });
      });
    });
  });
  nodos.forEach(n => {
    if (!n.nombra) return;
    TIPOS_ENTIDAD.forEach(([tipo]) => n.nombra[tipo].sort((x, y) => (x.linea || 1e9) - (y.linea || 1e9) || x.e.valor.localeCompare(y.e.valor, 'es')));
  });

  nodos.forEach(n => {
    n.r = n.tipo === 'handoff' ? Math.min(5, 2.6 + 0.45 * Math.sqrt(n.grado)) : Math.min(20, 4.5 + 1.7 * Math.sqrt(n.grado));
    if (n.tipo === 'indice' || n.tipo === 'instrucciones') n.r = Math.max(15, n.r);
  });
  const candidatosImportantes = nodos.filter(n => n.tipo !== 'handoff').sort((a, b) => b.grado - a.grado);
  const cupo = Math.max(8, Math.round(candidatosImportantes.length * 0.12));
  candidatosImportantes.forEach((n, i) => {
    n.importante = (i < cupo && n.grado > 0) || n.tipo === 'indice' || n.tipo === 'instrucciones';
  });
  const porImportancia = nodos.slice().sort((a, b) => (b.importante - a.importante) || (b.grado - a.grado));
  const tGenerado = Date.parse(String(DATOS.generado || '').replace(' ', 'T'));
  nodos.forEach(n => { const h = (tGenerado - Date.parse(n.modificado.replace(' ', 'T'))) / 3600000; n._fresco = h >= 0 && h < 24 ? 3 : h >= 0 && h < 72 ? 2 : 1; });

  const porRuta = new Map();
  nodos.forEach(n => { if (n.ruta) porRuta.set(normRuta(n.ruta), n); });

  const S = DATOS.salud && typeof DATOS.salud === 'object' ? DATOS.salud : {};
  const lista = x => Array.isArray(x) ? x : [];
  const objetos = x => lista(x).filter(e => e && typeof e === 'object' && !Array.isArray(e));
  const MINUTOS_CHOQUE = Number(DATOS.minutosChoque) > 0 ? Number(DATOS.minutosChoque) : 15;
  const decodificar = s => { try { return decodeURIComponent(s); } catch (e) { return s; } };
  const claveEnlace = (id, destino) => id + '\u0001' + normRuta(decodificar(String(destino || '')).trim());
  const rotosPorNota = new Set(lista(S.rotos).filter(x => x && x.clase !== 'wiki').map(x => claveEnlace(String(x.de), x.destino)));
  const ambiguosPorNota = new Set(lista(S.ambiguos).filter(Boolean).map(x => String(x.de) + '\u0001' + String(x.mencion || '').toLowerCase()));
  const yaEnIndiceRoto = new Set(lista(S.indiceRoto).filter(Boolean).map(x => String(x.indice) + '\u0001' + String(x.destino || '').toLowerCase()));
  const salud = {
    rotos: lista(S.rotos).filter(x => x && porId.has(String(x.de)) && !(x.clase === 'indice' && yaEnIndiceRoto.has(String(x.de) + '\u0001' + String(x.destino || '').toLowerCase()))),
    huerfanos: lista(S.huerfanos).map(String).filter(id => porId.has(id)),
    sinIndice: lista(S.sinIndice).map(String).filter(id => porId.has(id)),
    indiceRoto: lista(S.indiceRoto).filter(x => x && porId.has(String(x.indice))),
    ambiguos: lista(S.ambiguos).filter(x => x && porId.has(String(x.de))),
    sugeridas: aristas.filter(l => l.clase === 'sugerida'),
    duplicados: aristas.filter(l => l.clase === 'duplicado')
  };
  salud.rotos.forEach(x => porId.get(String(x.de)).problemas.push({ tono: 'aviso', texto: 'Enlace roto (' + (x.clase || '?') + '): «' + String(x.destino || '') + '» no lleva a ninguna nota.' }));
  salud.huerfanos.forEach(id => porId.get(id).problemas.push({ tono: 'aviso', texto: 'Huérfana: ninguna nota la nombra ni la enlaza, y ella tampoco nombra a otras.' }));
  salud.sinIndice.forEach(id => porId.get(id).problemas.push({ tono: 'aviso', texto: 'Es una memoria que su MEMORY.md no lista, así que nunca se carga sola.' }));
  salud.indiceRoto.forEach(x => porId.get(String(x.indice)).problemas.push({ tono: 'peligro', texto: 'El índice lista «' + String(x.destino || '') + '», que no existe.' }));
  salud.ambiguos.forEach(x => {
    const cuantos = lista(x.candidatos).length;
    const mencion = '«' + String(x.mencion || '') + '»';
    const texto = cuantos === 1
      ? 'Menciona ' + mencion + ' sin ruta; es un nombre genérico y la única nota con ese nombre está en otra carpeta, así que no la conecté.'
      : 'Menciona ' + mencion + ' sin ruta, y hay ' + cuantos + ' notas con ese nombre.';
    porId.get(String(x.de)).problemas.push({ tono: 'aviso', texto });
  });
  salud.duplicados.forEach(l => {
    l.source.problemas.push({ tono: 'peligro', texto: 'Posible duplicado de «' + l.target.titulo + '»' + (l.texto ? ': ' + l.texto : '.') });
    l.target.problemas.push({ tono: 'peligro', texto: 'Posible duplicado de «' + l.source.titulo + '»' + (l.texto ? ': ' + l.texto : '.') });
  });
  const TONOS_MEDICO = ['peligro', 'aviso', 'revisar', 'info'];
  const EN_SINGULAR = {
    'Enlaces rotos': 'Enlace roto', 'Huérfanas': 'Huérfana', 'Memorias sin índice': 'Memoria sin índice',
    'Menciones ambiguas': 'Mención ambigua', 'Conexiones sugeridas': 'Conexión sugerida', 'Posibles duplicados': 'Posible duplicado',
    'Rutas que ya no existen': 'Ruta que ya no existe', 'Commits que no existen': 'Commit que no existe',
    'Huellas que parecen commits': 'Huella que parece un commit', 'Huérfanas de verdad': 'Huérfana de verdad',
    'No entran en un Read': 'No entra en un Read', 'Cifras que no coinciden': 'Cifra que no coincide',
    'Memorias parecidas': 'Memoria parecida a otra', 'Se alcanzan desde otra nota del índice': 'Se alcanza desde otra nota del índice',
    'Notas fuera del cerebro': 'Nota fuera del cerebro', 'Anclas corridas': 'Ancla corrida', 'Cifras de control': 'Cifra de control',
    'Handoffs sin respuesta': 'Handoff sin respuesta', 'Respuestas sin acuse': 'Respuesta sin acuse',
    'Copias de conflicto': 'Copia de conflicto'
  };
  const nombreSalud = (nombre, n) => n === 1 && EN_SINGULAR[nombre] ? EN_SINGULAR[nombre] : nombre;
  const GRUPOS_MEDICO = {
    rutaVieja: 'Rutas que ya no existen',
    copiaDeConflicto: 'Copias de conflicto',
    commitInexistente: 'Commits que no existen',
    huellaProbable: 'Huellas que parecen commits',
    yaResuelto: 'Puede que ya esté resuelto',
    huerfanaReal: 'Huérfanas de verdad',
    noEntraEnRead: 'No entran en un Read',
    ficha: 'Ficha incompleta',
    cifras: 'Cifras que no coinciden',
    probadoOSinProbar: '¿Probado o sin probar?',
    repiteClaude: 'Repite CLAUDE.md',
    memoriasParecidas: 'Memorias parecidas',
    presupuestoIndice: 'Tamaño de MEMORY.md',
    llegaPorEnlace: 'Se alcanzan desde otra nota del índice',
    fueraDelCerebro: 'Notas fuera del cerebro',
    alcance: 'Alcance',
    commits: 'Revisión de commits'
  };
  const GRUPO_DE_REGLA = { frontmatter: 'ficha', descripcionFloja: 'ficha', ganchoFlojo: 'ficha', archivoSinMarca: 'ficha', casiLlena: 'noEntraEnRead', notaEnPartes: 'noEntraEnRead', ganchoLargo: 'presupuestoIndice',anclaCorrida: 'anclas', anclas: 'anclas', hecho: 'hechos', hechoHuerfano: 'hechos' };
  const REGLAS_YA_EN_SALUD = new Set(['sinIndice', 'indiceRoto', 'enlaceRoto', 'ambigua']);
  const SOLO_DATO = new Set(['alcance', 'presupuestoIndice', 'commits']);
  const tonoMedico = t => TONOS_MEDICO.includes(t) ? t : 'info';
  const esProblema = t => t === 'peligro' || t === 'aviso';
  const peorTono = items => items.reduce((peor, h) => TONOS_MEDICO.indexOf(h.tono) < TONOS_MEDICO.indexOf(peor) ? h.tono : peor, 'info');
  const lineaValida = x => Number.isInteger(Number(x)) && Number(x) > 0 ? Number(x) : null;
  const otroLado = lado => { const otro = LADOS.length === 2 && ladoDe(lado) ? LADOS.find(l => l.id !== lado) : null; return otro ? otro.nombre : ''; };
  const yaHuerfanas = new Set(salud.huerfanos);
  const medico = lista(S.medico)
    .filter(h => h && typeof h === 'object' && porId.has(String(h.nota)) && !REGLAS_YA_EN_SALUD.has(String(h.regla)) && !(h.regla === 'huerfanaReal' && yaHuerfanas.has(String(h.nota))))
    .map(h => ({ fila: 'medico', regla: String(h.regla || ''), nodo: porId.get(String(h.nota)), linea: lineaValida(h.linea), tono: tonoMedico(h.tono), texto: String(h.texto || ''), arreglo: String(h.arreglo || '') }));
  const porGrupoMedico = new Map();
  medico.forEach(h => {
    const clave = GRUPO_DE_REGLA[h.regla] || h.regla || 'otros';
    if (!porGrupoMedico.has(clave)) porGrupoMedico.set(clave, []);
    porGrupoMedico.get(clave).push(h);
  });
  const anclasDetalle = lista(S.anclas).filter(a => a && typeof a === 'object').map(a => ({
    fila: 'ancla',
    nodo: porId.get(String(a.nota)) || null,
    notaTexto: String(a.notaTexto || a.nota || ''),
    linea: lineaValida(a.linea),
    cita: String(a.cita || ''),
    archivo: String(a.archivo || ''),
    estado: String(a.estado || ''),
    por: a.por == null ? '' : String(a.por),
    propuesta: a.propuesta == null ? '' : String(a.propuesta),
    largo: Number(a.largo) || 0,
    base: String(a.base || ''),
    competidores: lista(a.competidores).filter(c => c && typeof c === 'object').map(c => ({ por: String(c.por || ''), linea: c.linea == null ? '' : String(c.linea) })),
    renglon: a.renglon && typeof a.renglon === 'object' && a.renglon.commit ? { commit: String(a.renglon.commit), fecha: String(a.renglon.fecha || '') } : null,
    cambios: lista(a.cambiosDespues).filter(c => c && c.commit).map(c => ({ commit: String(c.commit), fecha: String(c.fecha || '') }))
  }));
  const hechosDetalle = lista(S.hechos).filter(h => h && typeof h === 'object').map(h => ({
    fila: 'hecho',
    nodo: porId.get(String(h.nota)) || null,
    notaTexto: String(h.notaTexto || h.nota || ''),
    linea: lineaValida(h.linea),
    que: String(h.que || ''),
    dice: h.dice,
    disco: h.disco,
    sobra: lista(h.sobra).map(String),
    falta: lista(h.falta).map(String),
    estado: String(h.estado || ''),
    motivo: String(h.motivo || '')
  }));
  const anclasMedico = porGrupoMedico.get('anclas') || [];
  const hechosMedico = porGrupoMedico.get('hechos') || [];
  salud.anclas = anclasDetalle.length ? anclasDetalle : anclasMedico.filter(h => h.regla !== 'anclas');
  salud.hechos = hechosDetalle.length ? hechosDetalle : hechosMedico.filter(h => h.tono !== 'info');
  const extraSalud = { anclas: anclasMedico.filter(h => h.regla === 'anclas'), hechos: hechosMedico.filter(h => h.tono === 'info') };
  const aHandoff = x => ({ fila: 'handoff', nodo: porId.get(String(x.id)), fecha: String(x.fecha || ''), lado: String(x.lado || '') });
  salud.handoffsAbiertos = lista(S.handoffsAbiertos).filter(x => x && porId.has(String(x.id))).map(aHandoff);
  salud.respuestasSinAcuse = lista(S.respuestasSinAcuse).filter(x => x && porId.has(String(x.id))).map(aHandoff);
  medico.forEach(h => h.nodo.problemas.push({ tono: h.tono, texto: h.texto, linea: h.linea, arreglo: h.arreglo }));
  salud.handoffsAbiertos.forEach(h => h.nodo.problemas.push({ tono: 'aviso', texto: 'Handoff sin respuesta: ' + (otroLado(h.lado) ? otroLado(h.lado) + ' no lo contestó' : 'nadie lo contestó') + ' ni lo dio por leído.' }));
  salud.respuestasSinAcuse.forEach(h => h.nodo.problemas.push({ tono: 'info', texto: 'Respuesta sin acuse: ' + (otroLado(h.lado) ? otroLado(h.lado) + ' todavía no la dio' : 'nadie la dio todavía') + ' por leída. No pide nada, así que puede quedar así.' }));
  const TONO_DE_SALUD = { indiceRoto: 'peligro', duplicados: 'peligro', rotos: 'aviso', huerfanos: 'aviso', sinIndice: 'aviso', ambiguos: 'aviso' };
  const cuentaTonos = { peligro: 0, aviso: 0, revisar: 0 };
  Object.keys(TONO_DE_SALUD).forEach(c => { cuentaTonos[TONO_DE_SALUD[c]] += salud[c].length; });
  medico.forEach(h => { if (h.tono in cuentaTonos) cuentaTonos[h.tono]++; });
  const totalProblemas = cuentaTonos.peligro + cuentaTonos.aviso;

  const estado = {
    etiquetasOn: new Set(clavesEtiquetas()),
    gruposOn: new Set(grupos.map(g => g.id)),
    proyectosOn: new Set(proyectos.map(p => p.id)),
    porProyecto: false,
    tiposOn: new Set(Object.keys(TIPOS)),
    clasesOn: new Set(ORDEN_CLASES.filter(c => !CLASES[c].apagada)),
    terminos: [],
    resultados: [],
    coincidencias: null,
    nombrada: null,
    aristasBusqueda: new Set(),
    hover: null,
    seleccionado: null,
    local: null,
    vista: 'grafo',
    d3: null,
    markedOk: null,
    saludAbierta: null
  };
  let nodosVisibles = [];
  let aristasVisibles = [];
  let aristasFuerza = [];
  let visiblesPorClase = {};
  const pila = [];
  const foco = { teclado: false, origen: null, origenId: '' };
  document.addEventListener('keydown', () => { foco.teclado = true; }, true);
  document.addEventListener('pointerdown', () => { foco.teclado = false; }, true);

  const centro = $('#centro');
  const lienzo = $('#lienzo');
  const ctx = lienzo.getContext('2d');
  const pulso = $('#pulso');
  const pctx = pulso.getContext('2d');
  const menosMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');
  const panel = $('#panel');
  const lateral = $('#lateral');
  const buscador = $('#buscar');
  const tooltip = $('#tooltip');
  const movil = window.matchMedia('(max-width: 899px)');
  const esMovil = () => movil.matches;

  const vivo = { calor: false, uso: null, previo: null, tDisparo: 0, tapas: [], tapaPanel: null, alCerrar: null };
  const presenta = { cine: false, anonimo: false, pantalla: false };
  const anonimos = { notas: null, grupos: null, proyectos: null, chats: new Map() };
  const captura = { cuadro: 0, glEn: -1, pedidos: [], grabacion: null, ultimo: 0 };
  const compartir = { ocupado: false, vertical: false, dialogo: null, texto: null, foto: null, dia: null, sinNotas: null, grabar: null, formato: null, marca: null };

  function publico(clase, x, real) {
    if (!presenta.anonimo) return real;
    switch (clase) {
      case 'nota': {
        if (!anonimos.notas) {
          anonimos.notas = new Map();
          nodos.forEach((m, i) => anonimos.notas.set(m, 'Nota ' + (i + 1)));
        }
        return anonimos.notas.get(x) || 'una nota';
      }
      case 'grupo': {
        if (!anonimos.grupos) anonimos.grupos = new Map(grupos.map((g, i) => [g, 'Grupo ' + (i < 26 ? String.fromCharCode(65 + i) : i + 1)]));
        return anonimos.grupos.get(x) || 'un grupo';
      }
      case 'proyecto': {
        if (!anonimos.proyectos) anonimos.proyectos = new Map(proyectos.map((p, i) => [p, 'Proyecto ' + (i < 26 ? String.fromCharCode(65 + i) : i + 1)]));
        return anonimos.proyectos.get(x) || 'un proyecto';
      }
      case 'lobulo': return String(x.nombre).split(' · ')[0];
      case 'archivo': {
        const m = /\.([a-z0-9]{1,8})$/i.exec(nombreArchivo(x));
        return m ? 'un .' + m[1].toLowerCase() : 'un archivo';
      }
      case 'carpeta': return 'una carpeta';
      case 'chat': {
        let i = anonimos.chats.get(x);
        if (!i) { i = anonimos.chats.size + 1; anonimos.chats.set(x, i); }
        return 'chat ' + i;
      }
      case 'agente': return 'agente';
      default: return '';
    }
  }

  const colorDe = n => vivo.calor ? (n._calor || '#6b7280') : estado.porProyecto ? proyectoPorId.get(n.proyecto).color : grupoPorId.get(n.grupo).color;
  const colorDelGrupo = g => estado.porProyecto && proyectoDelGrupo.has(g.id) ? proyectoDelGrupo.get(g.id).color : g.color;
  const punto = n => '<span class="punto" style="--c:' + colorDe(n) + '"></span>';

  function marcarColor() {
    const actual = vivo.calor ? 'uso' : estado.porProyecto ? 'proyectos' : 'grupos';
    $('#modo-color').querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.color === actual)));
  }

  function ponerVistaDeColor(modo) {
    estado.porProyecto = modo === 'proyectos' && hayProyectos;
    marcarColor();
    if (!vivo.calor) try { localStorage.setItem('cerebro-color', estado.porProyecto ? 'proyectos' : 'grupos'); } catch (e) {}
    tooltip._nodo = null;
    if (estado.seleccionado) panel.style.setProperty('--c-panel', colorDe(estado.seleccionado));
    if (estado.vista === 'lista') renderLista();
    pedirDibujo();
  }

  function aviso(texto) {
    const t = $('#toast');
    t.textContent = texto;
    t.hidden = false;
    clearTimeout(aviso.temporizador);
    aviso.temporizador = setTimeout(() => { t.hidden = true; }, 2600);
  }

  function muestraLinea(clase) {
    const c = CLASES[clase];
    const color = { lineaFuerte: 'var(--linea-fuerte)', linea: 'var(--linea)', acento: 'var(--acento)', peligro: 'var(--peligro)' }[c.tinta];
    const guion = c.guion ? ';stroke-dasharray:' + c.guion.join(' ') : '';
    const tapa = c.guion ? 'butt' : 'round';
    return '<svg class="muestra" viewBox="0 0 34 10" width="34" height="10" aria-hidden="true"><line x1="2" y1="5" x2="32" y2="5" style="stroke:' + color + ';stroke-width:' + Math.max(1, c.ancho) + ';stroke-opacity:' + Math.max(0.5, c.alfa) + ';stroke-linecap:' + tapa + guion + '"/></svg>';
  }

  function somaSvg(cx, cy, r, punta, pad) {
    const delta = 0.9 * r;
    const R = 0.3 * r + pad;
    const apice = delta + r * punta * 0.35;
    const p = [[cx, cy - apice], [cx + 0.8660254 * delta, cy + 0.5 * delta], [cx - 0.8660254 * delta, cy + 0.5 * delta]];
    const normal = (a, b) => { const ex = b[0] - a[0]; const ey = b[1] - a[1]; const l = Math.hypot(ex, ey); return [ey / l, -ex / l]; };
    const f = v => +v.toFixed(2);
    let d = '';
    for (let i = 0; i < 3; i++) {
      const n0 = normal(p[(i + 2) % 3], p[i]);
      const n1 = normal(p[i], p[(i + 1) % 3]);
      d += (i ? ' L' : 'M') + f(p[i][0] + n0[0] * R) + ' ' + f(p[i][1] + n0[1] * R) + ' A' + f(R) + ' ' + f(R) + ' 0 0 1 ' + f(p[i][0] + n1[0] * R) + ' ' + f(p[i][1] + n1[1] * R);
    }
    return d + ' Z';
  }

  function muestraTipo(tipo) {
    const r = 'fill:var(--texto-3);stroke:var(--borde-nodo);';
    const soma = (cy, radio, punta, pad, estilo) => '<path d="' + somaSvg(8, cy, radio, punta, pad) + '" style="' + estilo + '"/>';
    const borde = 'fill:none;stroke:var(--borde-nodo);stroke-width:0.9';
    const halo = '<circle cx="8" cy="8.6" r="7.2" style="fill:var(--texto-3);opacity:0.2"/>';
    let f;
    switch (tipo) {
      case 'instrucciones': f = halo + soma(9.8, 4.6, 1, 0, r + 'stroke-width:1.5') + soma(9.8, 4.6, 1, 2, borde); break;
      case 'indice': f = halo + soma(9.8, 5.6, 1, 0, r + 'stroke-width:1.5'); break;
      case 'user': f = soma(9.6, 3.8, 0.95, 0, r + 'stroke-width:1.2') + soma(9.6, 3.8, 0.95, 2.2, borde); break;
      case 'feedback': f = soma(9.5, 5, 0.95, 0, r + 'stroke-width:1.6'); break;
      case 'project': f = soma(9.5, 5, 0.95, 0, r + 'stroke-width:1.6;stroke-dasharray:2.6 1.8'); break;
      case 'reference': f = soma(9.5, 5, 0.95, 0, r + 'stroke-width:1.8;stroke-dasharray:0.1 2.6;stroke-linecap:round'); break;
      case 'handoff': f = soma(9.6, 3.4, 0.95, 0, 'fill:var(--texto-3);opacity:0.55'); break;
      default: f = soma(9.5, 5, 0.95, 0, 'fill:var(--texto-3)');
    }
    return '<svg class="muestra-tipo" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">' + f + '</svg>';
  }

  function tituloApagadas() {
    const cuenta = {};
    aristas.forEach(l => { if (CLASES[l.clase].apagada) cuenta[l.clase] = (cuenta[l.clase] || 0) + 1; });
    const partes = ORDEN_CLASES.filter(c => cuenta[c]).map(c => cuenta[c] + ' «' + CLASES[c].nombre + '»');
    if (!partes.length) return '';
    return ' title="' + esc('Incluye ' + partes.join(' y ') + ', que arrancan apagadas en el filtro de conexiones: por eso el grafo cuenta menos.') + '"';
  }

  function construirCabecera() {
    $('#generado').textContent = DATOS.generado ? 'Generado el ' + DATOS.generado : '';
    $('#totales').innerHTML =
      '<span class="total"><b>' + nodos.length + '</b> notas</span>' +
      '<span class="total"' + tituloApagadas() + '><b>' + aristas.length + '</b> conexiones</span>' +
      '<button type="button" class="total' + (totalProblemas ? ' con-problemas' : '') + '" id="ir-salud" title="Ver el panel de salud: lo que encontró el médico de la memoria">' + textoProblemas() + '</button>';
  }

  function textoProblemas() {
    const cifra = (n, uno, varios) => '<b>' + n + '</b> ' + (n === 1 ? uno : varios);
    const partes = [];
    if (cuentaTonos.peligro) partes.push(cifra(cuentaTonos.peligro, 'grave', 'graves'));
    if (cuentaTonos.aviso) partes.push(cifra(cuentaTonos.aviso, 'aviso', 'avisos'));
    const revisar = cuentaTonos.revisar ? cifra(cuentaTonos.revisar, 'para revisar', 'para revisar') : '';
    if (!partes.length) return revisar || 'Sin problemas';
    return partes.join(' · ') + (revisar ? '<span class="total-revisar"> · ' + revisar + '</span>' : '');
  }

  function construirFiltros() {
    $('#filtro-grupos').innerHTML = grupos.filter(g => g.cantidad > 0).map(g =>
      '<div class="filtro"><label title="' + esc(publico('grupo', g, g.nombre)) + '"><input type="checkbox" data-grupo="' + esc(g.id) + '" checked>' +
      '<span class="punto" style="--c:' + g.color + '"></span><span class="filtro-nombre">' + esc(publico('grupo', g, g.nombre)) + '</span></label>' +
      '<button type="button" class="solo" data-solo-grupo="' + esc(g.id) + '" title="Mostrar solo este grupo" aria-label="Mostrar solo ' + esc(publico('grupo', g, g.nombre)) + '">solo</button>' +
      '<span class="cuenta">' + g.cantidad + '</span></div>').join('') || '<p class="vacio">No hay grupos.</p>';

    $('#bloque-proyectos').hidden = !hayProyectos;
    $('#filtro-proyectos').innerHTML = proyectos.filter(p => p.cantidad > 0).map(p =>
      '<div class="filtro"><label title="' + esc(publico('proyecto', p, p.nombre)) + '"><input type="checkbox" data-proyecto="' + esc(p.id) + '" checked>' +
      '<span class="punto" style="--c:' + p.color + '"></span><span class="filtro-nombre">' + esc(publico('proyecto', p, p.nombre)) + '</span></label>' +
      '<button type="button" class="solo" data-solo-proyecto="' + esc(p.id) + '" title="Mostrar solo este proyecto" aria-label="Mostrar solo ' + esc(publico('proyecto', p, p.nombre)) + '">solo</button>' +
      '<span class="cuenta">' + p.cantidad + '</span></div>').join('');

    const filaEtiqueta = (clave, nombre, cantidad) =>
      '<div class="filtro"><label title="' + esc(nombre) + '"><input type="checkbox" data-etiqueta="' + esc(clave) + '" checked>' +
      '<span class="filtro-nombre">' + esc(nombre) + '</span></label>' +
      '<button type="button" class="solo" data-solo-etiqueta="' + esc(clave) + '" title="Mostrar solo esta etiqueta" aria-label="Mostrar solo ' + esc(nombre) + '">solo</button>' +
      '<span class="cuenta">' + cantidad + '</span></div>';
    const sinEtiqueta = nodos.filter(n => !n.etiquetas.length).length;
    $('#bloque-etiquetas').hidden = !ETIQUETAS.length;
    $('#filtro-etiquetas').innerHTML = ETIQUETAS.map(e => filaEtiqueta(e.clave, '#' + e.nombre, e.cantidad)).join('') +
      (sinEtiqueta ? filaEtiqueta(SIN_ETIQUETA, 'Sin etiqueta', sinEtiqueta) : '');

    const cuentaTipos = {};
    nodos.forEach(n => { cuentaTipos[n.tipo] = (cuentaTipos[n.tipo] || 0) + 1; });
    $('#filtro-tipos').innerHTML = Object.keys(TIPOS).filter(t => cuentaTipos[t]).map(t =>
      '<div class="filtro"><label title="' + esc(publico('texto', t, TIPOS[t].ayuda) || nombreTipo(t)) + '"><input type="checkbox" data-tipo="' + esc(t) + '" checked>' +
      muestraTipo(t) + '<span class="filtro-nombre">' + esc(nombreTipo(t)) + '</span></label>' +
      '<button type="button" class="solo" data-solo-tipo="' + esc(t) + '" title="Mostrar solo este tipo" aria-label="Mostrar solo ' + esc(nombreTipo(t)) + '">solo</button>' +
      '<span class="cuenta">' + cuentaTipos[t] + '</span></div>').join('') || '<p class="vacio">No hay notas.</p>';

    const cuentaClases = {};
    aristas.forEach(l => { cuentaClases[l.clase] = (cuentaClases[l.clase] || 0) + 1; });
    $('#filtro-clases').innerHTML = ORDEN_CLASES.map(c =>
      '<div class="filtro"><label title="' + esc(CLASES[c].ayuda) + '"><input type="checkbox" data-clase="' + c + '"' + (estado.clasesOn.has(c) ? ' checked' : '') + '>' +
      muestraLinea(c) + '<span class="filtro-nombre">' + esc(CLASES[c].nombre) + '</span></label>' +
      '<span></span><span class="cuenta">' + (cuentaClases[c] || 0) + '</span></div>').join('');
  }

  function sincronizarCasillas() {
    lateral.querySelectorAll('input[data-grupo]').forEach(i => { i.checked = estado.gruposOn.has(i.dataset.grupo); });
    lateral.querySelectorAll('input[data-proyecto]').forEach(i => { i.checked = estado.proyectosOn.has(i.dataset.proyecto); });
    lateral.querySelectorAll('input[data-tipo]').forEach(i => { i.checked = estado.tiposOn.has(i.dataset.tipo); });
    lateral.querySelectorAll('input[data-etiqueta]').forEach(i => { i.checked = estado.etiquetasOn.has(i.dataset.etiqueta); });
    lateral.querySelectorAll('input[data-clase]').forEach(i => { i.checked = estado.clasesOn.has(i.dataset.clase); });
  }

  const SECCION_ENLACES = 'Enlaces y orden';
  const SALUD = [
    { clave: 'indiceRoto', nombre: 'Índice roto', tono: 'peligro', seccion: SECCION_ENLACES },
    { clave: 'duplicados', nombre: 'Posibles duplicados', tono: 'peligro', seccion: SECCION_ENLACES },
    { clave: 'rotos', nombre: 'Enlaces rotos', tono: 'aviso', seccion: SECCION_ENLACES },
    { clave: 'huerfanos', nombre: 'Huérfanas', tono: 'aviso', seccion: SECCION_ENLACES },
    { clave: 'sinIndice', nombre: 'Memorias sin índice', tono: 'aviso', seccion: SECCION_ENLACES },
    { clave: 'ambiguos', nombre: 'Menciones ambiguas', tono: 'aviso', seccion: SECCION_ENLACES },
    { clave: 'sugeridas', nombre: 'Conexiones sugeridas', tono: 'acento', seccion: SECCION_ENLACES }
  ];
  const DATOS_MEDICO = [];
  const ordenMedico = Object.keys(GRUPOS_MEDICO);
  const posMedico = c => ordenMedico.includes(c) ? ordenMedico.indexOf(c) : ordenMedico.length;
  Array.from(porGrupoMedico.keys())
    .filter(c => c !== 'anclas' && c !== 'hechos')
    .map(c => ({ clave: c, items: porGrupoMedico.get(c), peor: peorTono(porGrupoMedico.get(c)) }))
    .sort((a, b) => (TONOS_MEDICO.indexOf(a.peor) - TONOS_MEDICO.indexOf(b.peor)) || (posMedico(a.clave) - posMedico(b.clave)) || a.clave.localeCompare(b.clave))
    .forEach(g => {
      if (SOLO_DATO.has(g.clave) && g.peor === 'info') { DATOS_MEDICO.push(...g.items); return; }
      salud['medico-' + g.clave] = g.items;
      SALUD.push({ clave: 'medico-' + g.clave, nombre: GRUPOS_MEDICO[g.clave] || g.clave, tono: g.peor === 'info' ? 'acento' : g.peor, seccion: 'Médico de la memoria', revisar: g.peor === 'revisar', problemas: g.items.filter(h => esProblema(h.tono)).length });
    });
  if (Array.isArray(S.anclas) || salud.anclas.length || extraSalud.anclas.length) SALUD.push({ clave: 'anclas', nombre: 'Anclas corridas', tono: 'revisar', seccion: 'Médico de la memoria', revisar: true, problemas: 0 });
  if (Array.isArray(S.hechos) || salud.hechos.length || extraSalud.hechos.length) SALUD.push({ clave: 'hechos', nombre: 'Cifras de control', tono: 'revisar', seccion: 'Médico de la memoria', revisar: true, problemas: 0 });
  const hayHandoffs = nodos.some(n => n.tipo === 'handoff');
  if (hayHandoffs && Array.isArray(S.handoffsAbiertos)) SALUD.push({ clave: 'handoffsAbiertos', nombre: 'Handoffs sin respuesta', tono: 'aviso', seccion: 'Handoffs', problemas: 0 });
  if (hayHandoffs && Array.isArray(S.respuestasSinAcuse)) SALUD.push({ clave: 'respuestasSinAcuse', nombre: 'Respuestas sin acuse', tono: 'acento', seccion: 'Handoffs', problemas: 0 });
  const problemasDe = s => s.problemas != null ? s.problemas : s.clave === 'sugeridas' ? 0 : salud[s.clave].length;
  const QUE_ES = {
    indiceRoto: ['El índice (MEMORY.md) lista una nota que no existe: Claude la va a buscar y no la encuentra.',
      'Qué hacer: sacar esa línea del índice o corregir el nombre del archivo.'],
    duplicados: ['Dos notas que parecen decir lo mismo.', 'Qué hacer: dejar una sola, o que cada una diga en qué se diferencia de la otra.'],
    rotos: ['Un enlace que no lleva a ninguna nota.', 'Qué hacer: corregir el nombre o la ruta del enlace, o sacarlo si esa nota ya no existe.'],
    huerfanos: ['Notas que ninguna otra nombra ni enlaza: Claude no las va a encontrar solo.',
      'Qué hacer: nombrarlas desde el índice o desde una nota del mismo tema.'],
    sinIndice: ['Memorias que su MEMORY.md no lista: Claude no las carga al arrancar.', 'Qué hacer: sumarles una línea en MEMORY.md que diga cuándo abrirlas.'],
    ambiguos: ['Una nota nombra a otra sin ruta, y ese nombre sirve para más de una nota.', 'Qué hacer: poner la carpeta en la mención.'],
    sugeridas: ['Conexiones que convendría agregar entre notas que hablan de lo mismo.', ''],
    'medico-rutaVieja': ['Una nota nombra un archivo o una carpeta que ya no existe.', ''],
    'medico-copiaDeConflicto': ['Copias que deja la sincronización cuando una nota cambió en dos equipos a la vez.', ''],
    'medico-commitInexistente': ['Una nota cita un commit que no está en ningún repositorio conocido.', ''],
    'medico-huellaProbable': ['Algo citado como commit que parece la huella de un archivo.', ''],
    'medico-yaResuelto': ['Un problema anotado que quizás arregló un commit posterior.', ''],
    'medico-cifras': ['Una misma nota da dos números distintos para lo mismo.', ''],
    'medico-probadoOSinProbar': ['Una nota dice que algo está sin probar y otra, que ya se probó.', ''],
    'medico-memoriasParecidas': ['Dos memorias que hablan de lo mismo y ninguna nombra a la otra.', ''],
    'medico-presupuestoIndice': ['Cuánto ocupa MEMORY.md de lo que Claude lee al arrancar.', ''],
    'medico-fueraDelCerebro': ['Notas que existen pero están fuera de las carpetas que lee el mapa.', ''],
    'medico-noEntraEnRead': ['Notas tan largas que Claude no las lee enteras de una vez.', ''],
    'medico-ficha': ['Al encabezado de la nota (name, description, type) le falta algo o dice poco.', ''],
    'medico-repiteClaude': ['Una memoria repite lo que ya dice un CLAUDE.md, que Claude carga siempre.', ''],
    'medico-llegaPorEnlace': ['Memorias que el índice no lista pero se alcanzan desde otra nota que sí está.', ''],
    anclas: ['Una nota cita archivo:línea y esa línea del código ya no es la que dice.', ''],
    hechos: ['Números de las notas que se pueden contar en el disco («la API tiene 6 módulos») y ya no coinciden.', '']
  };

  function construirSalud() {
    let seccion = '';
    const leyenda = '<p class="salud-leyenda">' + [['peligro', 'grave'], ['aviso', 'aviso'], ['revisar', 'para revisar'], ['acento', 'dato o idea']]
      .map(([t, n]) => '<span class="tono-' + t + '"><span class="salud-punto"></span>' + n + '</span>').join('') + '</p>';
    $('#salud').innerHTML = leyenda + SALUD.map(s => {
      const n = salud[s.clave].length;
      const sub = (s.seccion || '') !== seccion ? '<div class="salud-sub">' + esc(s.seccion || '') + '</div>' : '';
      seccion = s.seccion || '';
      const queEs = QUE_ES[s.clave] ? ' title="' + esc(QUE_ES[s.clave][0]) + '"' : '';
      return sub + '<button type="button" class="salud-item tono-' + s.tono + '" data-salud="' + esc(s.clave) + '" aria-expanded="false"' + (n ? '' : ' data-cero') + queEs + '>' +
        '<span class="salud-num">' + n + '</span><span class="salud-nombre">' + esc(nombreSalud(s.nombre, n)) + '</span></button>';
    }).join('');
    const datos = $('#salud-datos');
    datos.hidden = !DATOS_MEDICO.length;
    datos.textContent = DATOS_MEDICO.map(h => h.texto).join(' ');
    const podadas = lista(DATOS.podadas).filter(p => p && p.ruta);
    const pie = $('#salud-pie');
    pie.hidden = !podadas.length;
    pie.textContent = podadas.length ? 'Carpetas pesadas, recorridas solo en parte: ' + podadas.map(p => nombreArchivo(p.ruta)).join(', ') : '';
    pie.title = podadas.map(p => String(p.ruta) + (Number(p.salteadas) > 0 ? ' (' + Number(p.salteadas) + ' carpetas salteadas)' : '')).join('\n');
  }

  function botonNodo(n, extra) {
    return '<button type="button" class="item-nodo" data-id="' + esc(n.id) + '"' + (extra || '') + '>' + punto(n) + '<span class="t">' + esc(n.titulo) + '</span></button>';
  }

  function filaSalud(clave, it) {
    switch (clave) {
      case 'rotos': {
        const n = porId.get(String(it.de));
        return '<div class="salud-fila">' + botonNodo(n) + '<div class="detalle">→ <code>' + esc(it.destino) + '</code> <span class="insignia">' + esc(it.clase || '?') + '</span></div></div>';
      }
      case 'huerfanos':
      case 'sinIndice': {
        const n = porId.get(it);
        return '<div class="salud-fila">' + botonNodo(n) + '<div class="detalle">' + esc(grupoPorId.get(n.grupo).nombre) + ' · <span class="ruta-chica">' + esc(n.archivo) + '</span></div></div>';
      }
      case 'indiceRoto': {
        const n = porId.get(String(it.indice));
        return '<div class="salud-fila">' + botonNodo(n) + '<div class="detalle">lista <code>' + esc(it.destino) + '</code>, que no existe</div></div>';
      }
      case 'ambiguos': {
        const n = porId.get(String(it.de));
        const cands = lista(it.candidatos).map(String).map(id => porId.get(id)).filter(Boolean);
        return '<div class="salud-fila">' + botonNodo(n) + '<div class="detalle">menciona <code>' + esc(it.mencion) + '</code>; puede ser:</div>' +
          '<div class="candidatos">' + (cands.length ? cands.map(c => '<button type="button" class="item-nodo" data-id="' + esc(c.id) + '" title="' + esc(c.ruta) + '">' + punto(c) + '<span class="t">' + esc(c.titulo) + '</span></button>').join('') : '<span class="detalle">sin candidatos conocidos</span>') + '</div></div>';
      }
      case 'sugeridas':
      case 'duplicados':
        return '<div class="salud-fila"><div class="salud-par">' + botonNodo(it.source) + '<span class="salud-flecha">' + (clave === 'duplicados' ? '≈' : '→') + '</span>' + botonNodo(it.target) + '</div>' +
          (it.texto ? '<div class="detalle">' + esc(it.texto) + '</div>' : '') + '</div>';
    }
    if (!it || typeof it !== 'object') return '';
    if (it.fila === 'medico') return filaMedico(it, false);
    if (it.fila === 'ancla') return filaAncla(it);
    if (it.fila === 'hecho') return filaHecho(it);
    if (it.fila === 'handoff') return filaHandoff(it, clave);
    return '';
  }

  function botonNota(n, linea, alternativo) {
    const l = linea ? '<span class="linea-chica">:' + linea + '</span>' : '';
    if (n) return '<button type="button" class="item-nodo" data-id="' + esc(n.id) + '" title="' + esc(n.titulo + (linea ? ', línea ' + linea : '')) + '">' + punto(n) + '<span class="t">' + esc(n.titulo) + '</span>' + l + '</button>';
    return '<div class="detalle" title="' + esc(alternativo) + '"><span class="ruta-chica">' + esc(nombreArchivo(alternativo) || 'nota fuera del cerebro') + (linea ? ':' + linea : '') + '</span></div>';
  }

  const htmlArreglo = a => a ? '<div class="detalle"><span class="arreglo">→ ' + esc(a) + '</span></div>' : '';
  const fechaCorta = f => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(f || '')); return m ? Number(m[3]) + '/' + Number(m[2]) : String(f || ''); };
  const cifra = x => typeof x === 'number' ? x.toLocaleString('es') : esc(x == null ? '?' : String(x));
  const listaCorta = (xs, tope) => xs.slice(0, tope).map(x => '<code>' + esc(x) + '</code>').join(', ') + (xs.length > tope ? ' y ' + (xs.length - tope) + ' más' : '');

  function filaMedico(h, dato) {
    return '<div class="salud-fila' + (dato ? ' dato' : '') + '">' + botonNota(h.nodo, h.linea) + '<div class="detalle">' + esc(h.texto) + '</div>' + htmlArreglo(h.arreglo) + '</div>';
  }

  function filaAncla(a) {
    const cita = '<code>' + esc(a.cita) + '</code>';
    const por = a.por ? ' por «' + esc(a.por) + '»' : '';
    const archivo = '<code title="' + esc(a.archivo) + '">' + esc(nombreArchivo(a.archivo) || a.archivo) + '</code>';
    let que;
    if (a.competidores.length) que = 'cita ' + cita + por + ': revisar a mano, en ' + archivo + ' puede ser ' + a.competidores.map(c => 'la ' + esc(c.linea) + (c.por ? ' («' + esc(c.por) + '»)' : '')).join(' o ');
    else if (a.estado === 'fuera') que = 'cita ' + cita + ', pero ' + archivo + ' tiene ' + cifra(a.largo) + ' líneas';
    else if (a.propuesta) que = 'cita ' + cita + por + ' → hoy <code title="' + esc(a.archivo) + '">' + esc((nombreArchivo(a.archivo) || a.archivo) + ':' + a.propuesta) + '</code>';
    else que = 'cita ' + cita + por + ', que ya no está cerca de esa línea';
    const historia = [];
    if (a.base && a.base !== PROYECTO_PRINCIPAL) historia.push('<span class="insignia">' + esc(a.base) + '</span>');
    if (a.renglon) historia.push('renglón del ' + esc(fechaCorta(a.renglon.fecha)) + ' <span class="insignia" title="' + esc(a.renglon.fecha) + '"><code>' + esc(a.renglon.commit) + '</code></span>');
    if (a.cambios.length) historia.push('después cambió en ' + a.cambios.map(c => '<span class="insignia" title="' + esc(c.fecha) + '"><code>' + esc(c.commit) + '</code></span>').join(' '));
    return '<div class="salud-fila">' + botonNota(a.nodo, a.linea, a.notaTexto) + '<div class="detalle">' + que + '</div>' +
      (historia.length ? '<div class="detalle">' + historia.join(' · ') + '</div>' : '') + '</div>';
  }

  function filaHecho(h) {
    if (h.estado === 'huerfano') {
      return '<div class="salud-fila dato">' + botonNota(h.nodo, h.linea, h.notaTexto) + '<div class="detalle"><span class="insignia">hecho huérfano</span> ' + esc(h.que) + (h.motivo ? ': ' + esc(h.motivo) : '') + '</div></div>';
    }
    const partes = [];
    if (h.sobra.length) partes.push('nombra y ya no está: ' + listaCorta(h.sobra, 4));
    if (h.falta.length) partes.push('falta: ' + listaCorta(h.falta, 4));
    const que = h.dice === h.disco && partes.length ? 'el número coincide (' + cifra(h.disco) + '), pero la lista no' : 'dice ' + cifra(h.dice) + ', hoy ' + cifra(h.disco);
    return '<div class="salud-fila">' + botonNota(h.nodo, h.linea, h.notaTexto) + '<div class="detalle">' + que + (h.que ? ' <span class="arreglo">(' + esc(h.que) + ')</span>' : '') + '</div>' +
      (partes.length ? '<div class="detalle">' + partes.join(' · ') + '</div>' : '') + '</div>';
  }

  function filaHandoff(h, clave) {
    const otro = otroLado(h.lado);
    const que = clave === 'handoffsAbiertos'
      ? (otro ? 'espera respuesta de ' + otro : 'espera respuesta')
      : (otro ? otro + ' todavía no la dio por leída' : 'nadie la dio por leída');
    return '<div class="salud-fila">' + botonNota(h.nodo, null) + '<div class="detalle">' + (h.fecha ? esc(h.fecha) + ' · ' : '') + esc(que) + '</div></div>';
  }

  const NOMBRE_ARREGLO = { roto: 'Enlace roto', huerfana: 'Huérfana', sinIndice: 'Memoria sin índice', indiceRoto: 'Índice roto', ambigua: 'Mención ambigua', duplicado: 'Posible duplicado' };
  const nombreArreglo = t => {
    if (NOMBRE_ARREGLO[t]) return NOMBRE_ARREGLO[t];
    const regla = String(t).replace(/^medico-/, '');
    return nombreSalud(GRUPOS_MEDICO[GRUPO_DE_REGLA[regla] || regla] || regla, 1);
  };

  function construirAhorro() {
    const A = DATOS.aprender !== false && DATOS.aprendido && typeof DATOS.aprendido === 'object' ? DATOS.aprendido : null;
    const s = A && A.semana && typeof A.semana === 'object' ? A.semana : {};
    const num = v => Math.max(0, Math.round(Number(v) || 0));
    const arreglados = objetos(DATOS.arreglados).filter(a => porId.has(String(a.id))).sort((a, b) => num(b.t) - num(a.t));
    const pistas = num(s.pistas), sirvieron = num(s.utiles), leidas = num(s.seguidas), recomendadas = num(s.notas);
    const bloque = $('#bloque-ahorro');
    bloque.hidden = !pistas && !arreglados.length;
    if (bloque.hidden) return;
    const tarjeta = (n, uno, varios, titulo) => '<div class="salud-item cifra tono-acento"' + (n ? '' : ' data-cero') + ' title="' + esc(titulo) + '">'
      + '<span class="salud-num">' + n.toLocaleString('es') + '</span><span class="salud-nombre">' + (n === 1 ? uno : varios) + '</span></div>';
    const tarjetas = pistas ? [
      tarjeta(pistas, 'pista en tus pedidos', 'pistas en tus pedidos', 'Cada vez que le escribiste, Neuromapa le pasó a Claude las notas que parecían venir al caso.'),
      tarjeta(sirvieron, 'pista sirvió', 'pistas sirvieron', 'En la media hora siguiente, Claude leyó una de esas notas o abrió un archivo que nombraban.'),
      tarjeta(leidas, 'nota recomendada leída', 'notas recomendadas leídas', 'De ' + recomendadas.toLocaleString('es') + ' que recomendó.')
    ] : [];
    tarjetas.push(tarjeta(arreglados.length, 'problema arreglado', 'problemas arreglados', 'Graves y avisos del médico que dejaron de estar en una nota que sigue en el mapa.'));
    $('#ahorro').innerHTML = tarjetas.join('');
    const cuando = t => { const d = new Date(num(t) * 1000); return d.getDate() + '/' + (d.getMonth() + 1); };
    let html = '';
    if (arreglados.length) html += '<div class="salud-sub">Problemas arreglados</div>'
      + arreglados.slice(0, 6).map(a => '<div class="salud-fila">' + botonNodo(porId.get(String(a.id))) + '<div class="detalle">' + esc(nombreArreglo(String(a.tipo || ''))) + ' · ' + cuando(a.t) + '</div></div>').join('')
      + (arreglados.length > 6 ? '<p class="salud-pie">… y ' + (arreglados.length - 6) + ' más.</p>' : '');
    html += '<p class="salud-pie">' + (pistas ? 'Cuenta lo que Claude hizo en la media hora después de cada pista: no prueba que sin ella no lo hubiera hecho igual. ' : '')
      + 'Un problema cuenta como arreglado si el médico dejó de verlo en una nota que sigue en el mapa; si vuelve, deja de contar.</p>';
    $('#ahorro-detalle').innerHTML = html;
  }

  function construirAprendido() {
    construirAhorro();
    const A = DATOS.aprendido;
    const bloque = $('#bloque-aprendido');
    if (DATOS.aprender === false) { bloque.hidden = true; return; }
    if (!A || typeof A !== 'object') {
      $('#aprendido').innerHTML = '<p>Todavía no aprendió nada: aprende mientras Claude trabaja, de qué archivos se usan juntos.</p>';
      bloque.hidden = !DATOS.aprendizajeEnVivo;
      return;
    }
    const num = v => Number(v) || 0;
    const coma = v => num(v).toFixed(2).replace('.', ',');
    const lugar = x => {
      const n = x && x.id != null ? porId.get(String(x.id)) : null;
      return n ? botonNodo(n) : '<span class="ruta-chica">' + esc(publico('archivo', x ? x.texto : '', x ? x.texto : '')) + '</span>';
    };
    const fila = (cabeza, detalle) => '<div class="salud-fila">' + cabeza + '<div class="detalle">' + detalle + '</div></div>';
    const s = A.semana || {};
    const plural = (n, uno, varios) => n + ' ' + (n === 1 ? uno : varios);
    let html = (num(s.pedidos) || num(s.toques)
      ? '<p>Últimos 7 días: ' + plural(num(s.pedidos), 'pedido', 'pedidos') + ' y ' + plural(num(s.toques), 'archivo abierto o editado', 'archivos abiertos o editados')
        + '.</p>'
      : '<p>En los últimos 7 días no se usó.</p>')
      + (typeof A.separado === 'string' && A.separado ? '<p>' + esc(A.separado) + '</p>' : '')
      + (typeof A.charlas === 'string' && A.charlas ? '<p>' + esc(A.charlas) + '</p>' : '');
    const pares = objetos(A.pares);
    const codigo = objetos(A.codigo);
    const pistas = objetos(A.pistas);
    if (pares.length || codigo.length || pistas.length)
      html += '<p class="salud-pie">Lo de abajo es de todo lo aprendido, no solo de estos 7 días: lo viejo pesa menos.</p>';
    const nivel = f => num(f) >= 0.6 ? 'fuerte' : num(f) >= 0.35 ? 'media' : 'floja';
    if (pares.length) html += '<div class="salud-sub">Se usan juntos</div>'
      + pares.map(p => fila(lugar(p.a), 'junto con ' + lugar(p.b) + ' <span class="fuerza" title="Qué tan seguido se usan juntos, de 0 a 1: ' + coma(p.fuerza) + '">' + nivel(p.fuerza) + '</span>')).join('');
    if (codigo.length) html += '<div class="salud-sub">Código que se abre con cada nota</div>'
      + codigo.map(c => fila(lugar(c.nota), lista(c.codigo).filter(x => typeof x === 'string').map(x => '<code>' + esc(publico('archivo', x, x)) + '</code>').join(' · '))).join('');
    const unas = v => { const r = Math.round(num(v)); return r < 1 ? 'menos de una' : r === 1 ? 'una' : 'unas ' + r; };
    if (pistas.length) html += '<div class="salud-sub">Notas recomendadas: se leyeron después</div>'
      + pistas.map(x => fila(lugar(x.nota), Math.round(num(x.leida) * 10) + ' de cada 10 veces que la recomendó (' + unas(x.veces) + ')')).join('');
    const hecho = num(A.hecho);
    if (hecho) {
      const minutos = Math.max(0, Math.round((Date.now() / 1000 - hecho) / 60));
      html += '<p class="salud-pie">Resumido ' + (minutos < 1 ? 'recién' : 'hace ' + minutos + ' min')
        + (DATOS.aprendizajeEnVivo ? '; con el mapa abierto se vuelve a resumir cada minuto.' : '.') + '</p>';
    }
    html += '<p class="salud-pie">Aprende de qué archivos se usan juntos y de qué pistas sirvieron, y olvida a la mitad cada '
      + num(A.vidaMedia) + ' días lo que no se repite. Las corridas de prueba no cuentan. '
      + (num(A.aristas) ? 'En el mapa son las conexiones «Aprendida», más gruesas cuanto más fuertes; si las dos notas ya estaban conectadas, esa conexión se engrosa. ' : '')
      + 'Se apaga con «"aprender": false» en config.json.</p>';
    $('#aprendido').innerHTML = html;
    bloque.hidden = false;
  }

  const llaveCamino = (a, b) => a.id < b.id ? a.id + '\u0001' + b.id : b.id + '\u0001' + a.id;
  const textoCamino = p => 'se usan juntas en el trabajo (fuerza ' + p.toFixed(2).replace('.', ',') + ')';
  const CAMBIOS_A_LA_VISTA = 10;
  let caminosAlDia = false;
  function actualizarCaminos(lista) {
    if (!Array.isArray(lista)) return null;
    const animar = caminosAlDia && gestoPosible() && !introCorriendo();
    caminosAlDia = true;
    const llegan = new Map();
    lista.forEach(x => {
      const a = Array.isArray(x) ? porId.get(String(x[0])) : null;
      const b = Array.isArray(x) ? porId.get(String(x[1])) : null;
      const peso = Array.isArray(x) ? Number(x[2]) : NaN;
      if (a && b && a !== b && peso > 0) llegan.set(llaveCamino(a, b), { a, b, peso: Math.min(1, peso) });
    });
    const quitar = (grupo, l) => { const i = grupo.indexOf(l); if (i >= 0) grupo.splice(i, 1); };
    const nacen = [], suben = [], seVan = [];
    let cambio = false;
    for (let i = aristas.length - 1; i >= 0; i--) {
      const l = aristas[i];
      if (l.clase !== 'aprendida') continue;
      const k = llaveCamino(l.source, l.target);
      const x = llegan.get(k);
      if (!x) {
        if (!tapada(l) && l._visible) seVan.push({ a: l.source, b: l.target });
        aristas.splice(i, 1);
        quitar(l.source.salientes, l);
        quitar(l.target.entrantes, l);
        l._visible = false;
        cambio = true;
        continue;
      }
      llegan.delete(k);
      const antes = (l.datos && l.datos.peso) || 0;
      if (antes === x.peso) continue;
      l.datos = Object.assign({}, l.datos, { peso: x.peso });
      l.texto = textoCamino(x.peso);
      if (nivelUso(x.peso) > nivelUso(antes)) suben.push(l);
      cambio = true;
    }
    for (const x of llegan.values()) {
      const l = { source: x.a, target: x.b, clase: 'aprendida', texto: textoCamino(x.peso), datos: { peso: x.peso }, _visible: false };
      aristas.push(l);
      x.a.salientes.push(l);
      x.b.entrantes.push(l);
      nacen.push(l);
      cambio = true;
    }
    if (!cambio) return { nacen: 0, suben: 0, seVan: 0 };
    fundirAprendidas(aristas);
    recalcularVisibles();
    recalcularAristasBusqueda();
    actualizarContador();
    const cuenta = $('#filtro-clases input[data-clase="aprendida"]');
    const caja = cuenta && cuenta.closest('.filtro');
    if (caja && caja.querySelector('.cuenta')) caja.querySelector('.cuenta').textContent = aristas.filter(l => l.clase === 'aprendida').length;
    const total = document.querySelectorAll('#totales .total b')[1];
    if (total) total.textContent = aristas.length;
    if (animar) {
      const ahora = performance.now();
      const visto = l => !tapada(l) ? l : l._sobre.find(o => o._visible);
      const efectos = [];
      nacen.forEach(l => {
        const o = visto(l);
        if (!o || !o._visible) return;
        efectos.push(o === l ? { tipo: 'brote', l, dur: 1800, color: colores.acento }
          : { tipo: 'potencia', l: o, dur: 1600, color: colorDe(o.source) });
      });
      suben.forEach(l => {
        const o = visto(l);
        if (o && o._visible) efectos.push({ tipo: 'potencia', l: o, dur: 1400, color: o === l ? colores.acento : colorDe(o.source) });
      });
      seVan.forEach(x => efectos.push({ tipo: 'apaga', desde: x.a, hacia: x.b, dur: 2600, color: colores.acento }));
      efectos.slice(0, CAMBIOS_A_LA_VISTA).forEach((e, i) => { e.t0 = ahora + i * 120; e.fuente = 'aprendido'; anim.efectos.push(e); });
      programarCuadro();
    }
    pedirDibujo();
    return { nacen: nacen.length, suben: suben.length, seVan: seVan.length };
  }

  function mostrarListaSalud() {
    const caja = $('#salud-lista');
    if (!caja.hidden) caja.scrollIntoView({ block: 'nearest', behavior: menosMovimiento.matches ? 'auto' : 'smooth' });
  }

  function abrirSalud(clave) {
    if (presenta.anonimo && clave) return;
    const caja = $('#salud-lista');
    if (estado.saludAbierta === clave || !clave) {
      estado.saludAbierta = null;
      caja.hidden = true;
      caja.innerHTML = '';
    } else {
      estado.saludAbierta = clave;
      const def = SALUD.find(s => s.clave === clave);
      const items = salud[clave];
      const extra = extraSalud[clave] || [];
      caja.hidden = false;
      const queEs = QUE_ES[clave] || [];
      caja.innerHTML = '<div class="salud-lista-cabeza">' + esc(nombreSalud(def.nombre, items.length)) + ' · ' + items.length +
        (def.revisar ? ' · <span class="suave">para revisar: el médico avisa, no afirma</span>' : '') +
        (queEs[0] ? '<br>' + esc(queEs[0]) + (items.length && queEs[1] ? ' ' + esc(queEs[1]) : '') : '') + '</div>' +
        (items.length ? items.map(it => filaSalud(clave, it)).join('') : '<p class="vacio">Nada por acá. Todo en orden.</p>') +
        extra.map(h => filaMedico(h, true)).join('');
      caja.scrollTop = 0;
      mostrarListaSalud();
    }
    $('#salud').querySelectorAll('[data-salud]').forEach(b => b.setAttribute('aria-expanded', String(b.dataset.salud === estado.saludAbierta)));
  }

  function etiquetaVisible(n) {
    if (!n.etiquetas.length) return estado.etiquetasOn.has(SIN_ETIQUETA);
    return n.etiquetas.some(e => estado.etiquetasOn.has(e.toLowerCase()));
  }

  function baseVisible(n) {
    return estado.gruposOn.has(n.grupo) && estado.proyectosOn.has(n.proyecto) && estado.tiposOn.has(n.tipo) && etiquetaVisible(n);
  }

  function recalcularVisibles() {
    let permitido = null;
    if (estado.local && porId.has(estado.local.id)) {
      const origen = porId.get(estado.local.id);
      permitido = new Set([origen]);
      let frontera = [origen];
      for (let p = 0; p < estado.local.saltos; p++) {
        const siguiente = [];
        frontera.forEach(n => {
          n.salientes.forEach(l => { if (estado.clasesOn.has(l.clase) && baseVisible(l.target) && !permitido.has(l.target)) { permitido.add(l.target); siguiente.push(l.target); } });
          n.entrantes.forEach(l => { if (estado.clasesOn.has(l.clase) && baseVisible(l.source) && !permitido.has(l.source)) { permitido.add(l.source); siguiente.push(l.source); } });
        });
        frontera = siguiente;
      }
    }
    const nacer = graficoListo && completo() ? performance.now() : 0;
    nodosVisibles = [];
    nodos.forEach(n => {
      const antes = n._visible;
      n._visible = permitido ? permitido.has(n) : baseVisible(n);
      n._cuenta = 0;
      if (nacer && n._visible && antes === false) n._nace = nacer;
      if (n._visible) nodosVisibles.push(n);
    });
    if (nacer) anim.escenaHasta = Math.max(anim.escenaHasta, nacer + 400);
    aristasVisibles = [];
    aristasFuerza = [];
    visiblesPorClase = {};
    aristas.forEach(l => {
      l._visible = estado.clasesOn.has(l.clase) && l.source._visible && l.target._visible;
      if (!l._visible) return;
      aristasVisibles.push(l);
      (visiblesPorClase[l.clase] || (visiblesPorClase[l.clase] = [])).push(l);
      if (CLASES[l.clase].sinCuenta) return;
      aristasFuerza.push(l);
      l.source._cuenta++;
      l.target._cuenta++;
    });
  }

  function recalcularAristasBusqueda() {
    estado.aristasBusqueda = new Set();
    if (!estado.coincidencias) return;
    aristasVisibles.forEach(l => {
      if (estado.coincidencias.has(l.source) && estado.coincidencias.has(l.target)) estado.aristasBusqueda.add(l);
    });
  }

  function aplicarFiltros() {
    recalcularVisibles();
    recalcularAristasBusqueda();
    actualizarSimulacion();
    ordenarResultados();
    renderResultados();
    if (estado.vista === 'lista') renderLista();
    actualizarContador();
    actualizarBandaLocal();
    pedirDibujo();
  }

  function actualizarContador() {
    $('#contador').textContent = nodosVisibles.length + ' de ' + nodos.length + ' notas · ' + aristasVisibles.length + (aristasVisibles.length < aristas.length ? ' de ' + aristas.length : '') + ' conexiones';
  }

  const BUSQUEDA_K = 1.2;
  const BUSQUEDA_B = 0.75;
  const PESO_TEXTO = 5;
  const TOPE_APARICIONES = 60;
  const TOPE_POSICIONES = 300;
  const ANCHO_FRAGMENTO = 130;
  const RESULTADOS_SERVIDOR = 40;
  const LARGO_CONSULTA = 300;
  const ESPERA_BUSCAR = 1500;
  const ESPERA_SOBRE = 4000;
  const PAUSA_SERVIDOR = 20000;
  const RE_PALABRA = /[\p{L}\p{N}]+/gu;
  const FINALES = ['aciones', 'acion', 'iones', 'ion', 'iendo', 'ando', 'ados', 'adas', 'ado', 'ada', 'idos', 'idas', 'ido', 'ida', 'ar', 'er', 'ir', 'es', 'os', 'as', 's', 'a', 'o', 'e'];
  const TERMINACIONES = new Set(FINALES.concat(['', 'an', 'en', 'amos', 'emos', 'imos', 'aron', 'ieron', 'aba', 'aban', 'ia', 'ian', 'ara', 'iera', 'are', 'iere', 'aria', 'eria', 'iria', 'ate', 'ete', 'ite', 'alo', 'arlo', 'erlo', 'irlo', 'arla', 'erla', 'irla', 'ciones', 'cion']));
  const MOTIVOS_LOCAL = {
    armando: 'El servidor todavía está armando el índice: por ahora busco en lo que trae la página.',
    caido: 'El servidor no respondió: busco en lo que trae la página.',
    error: 'El buscador del servidor falló: busco en lo que trae la página.'
  };
  const busq = { seq: 0, control: null, servidor: /^https?:$/.test(location.protocol) ? null : false, pausa: 0, consulta: '', fuente: 'local', motivo: '', corregida: '', total: 0, delServidor: 0, terminos: [], abiertas: new Set(), entidad: null, sobre: null, sobreControl: null };

  let indexado = false;
  let largoPromedio = 1;
  function indexar() {
    if (indexado) return;
    let suma = 0;
    nodos.forEach(n => {
      n._b = { titulo: normalizar(n.titulo), slug: normalizar(n.slug), ruta: normalizar(n.ruta), desc: normalizar(n.descripcion), texto: normalizar(n.texto) };
      suma += n._b.texto.length;
    });
    largoPromedio = Math.max(1, suma / Math.max(1, nodos.length));
    indexado = true;
  }

  function contarEn(texto, t) {
    let veces = 0;
    let i = texto.indexOf(t);
    while (i >= 0 && veces < TOPE_APARICIONES) {
      veces++;
      i = texto.indexOf(t, i + t.length);
    }
    return veces;
  }

  function buscarLocal(consulta) {
    const terminos = normalizar(consulta).split(/\s+/).filter(Boolean);
    if (!terminos.length) return { terminos, resultados: [] };
    indexar();
    const df = terminos.map(() => 0);
    const candidatos = [];
    nodos.forEach(n => {
      const b = n._b;
      const tf = terminos.map((t, i) => {
        const v = contarEn(b.texto, t);
        if (v) df[i]++;
        return v;
      });
      let p = 0;
      let enTexto = null;
      for (let i = 0; i < terminos.length; i++) {
        const t = terminos[i];
        if (b.titulo.includes(t)) p += b.titulo.startsWith(t) ? 120 : 90;
        else if (b.slug.includes(t)) p += 60;
        else if (b.ruta.includes(t)) p += 30;
        else if (b.desc.includes(t)) p += 20;
        else if (tf[i]) { if (!enTexto) enTexto = t; }
        else return;
      }
      candidatos.push({ n, p, enTexto, tf });
    });
    const total = nodos.length;
    const idf = df.map(d => Math.log(1 + (total - d + 0.5) / (d + 0.5)));
    candidatos.forEach(r => {
      const norma = BUSQUEDA_K * (1 - BUSQUEDA_B + BUSQUEDA_B * r.n._b.texto.length / largoPromedio);
      r.tf.forEach((v, i) => { if (v) r.p += PESO_TEXTO * idf[i] * v * (BUSQUEDA_K + 1) / (v + norma); });
    });
    return { terminos, resultados: candidatos };
  }

  function avisoCorreccion(datos) {
    const q = datos && typeof datos.corregida === 'string' ? datos.corregida.trim() : '';
    if (!q) return '';
    const raras = datos.raras && typeof datos.raras === 'object' && Object.keys(datos.raras).length;
    return '<p class="resultados-aviso">Parece una errata: busqué «' + esc(q) + '».' + (raras ? ' Para buscar la palabra tal cual, ponela entre comillas.' : '') + '</p>';
  }

  function desdeServidor(consulta, datos) {
    const vistos = new Set();
    const resultados = [];
    datos.resultados.forEach(x => {
      const n = x && x.id != null ? porId.get(String(x.id)) : null;
      if (!n || vistos.has(n)) return;
      vistos.add(n);
      const secciones = (Array.isArray(x.secciones) ? x.secciones : []).filter(s => s && typeof s === 'object');
      resultados.push({ n, p: 0, secciones });
    });
    resultados.forEach((r, i) => { r.p = resultados.length - i; });
    return {
      terminos: normalizar(consulta).split(/\s+/).filter(Boolean),
      resultados,
      servidor: true,
      corregida: avisoCorreccion(datos),
      total: Math.max(resultados.length, Number(datos.total) || 0),
      terminosServidor: (Array.isArray(datos.terminos) ? datos.terminos : []).map(t => normalizar(t)).filter(Boolean)
    };
  }

  function sumarLocales(b, local) {
    const ya = new Set(b.resultados.map(r => r.n));
    b.delServidor = b.resultados.length;
    local.resultados.filter(r => !ya.has(r.n)).sort((x, y) => y.p - x.p).forEach((r, i) => {
      r.p = -1 - i;
      b.resultados.push(r);
    });
    return b;
  }

  function entidadesDe(consulta) {
    const q = String(consulta || '').trim().replace(/^[`'"]+|[`'"]+$/g, '').trim().toLowerCase();
    if (q.length < 3 || /\s/.test(q)) return null;
    const nombre = q.split(/[\\/]+/).filter(Boolean).pop() || q;
    let tipo = 'commits';
    let hallados = /^[0-9a-f]{7,40}$/.test(q)
      ? entidadesPorTipo.commits.filter(e => e.sha ? e.sha.toLowerCase().startsWith(q) : e.valor.toLowerCase().startsWith(q) || q.startsWith(e.valor.toLowerCase()))
      : [];
    if (!hallados.length) { tipo = 'tablas'; hallados = entidadesPorTipo.tablas.filter(e => e.valor.toLowerCase() === q); }
    if (!hallados.length) { tipo = 'archivos'; hallados = entidadesPorTipo.archivos.filter(e => e.valor.toLowerCase() === nombre); }
    if (!hallados.length) return null;
    const vistas = new Set();
    const notas = [];
    hallados.forEach(e => e.notas.forEach(x => {
      if (vistas.has(x.nodo)) return;
      vistas.add(x.nodo);
      notas.push(x);
    }));
    return { tipo, hallados, notas };
  }

  function aplicarBusqueda(consulta, b, motivo) {
    const antes = estado.coincidencias;
    busq.consulta = consulta;
    busq.fuente = b.servidor ? 'servidor' : 'local';
    busq.motivo = b.servidor ? '' : (motivo || '');
    busq.corregida = b.servidor ? (b.corregida || '') : '';
    busq.total = b.total || b.resultados.length;
    busq.delServidor = b.servidor ? (b.delServidor || b.resultados.length) : 0;
    busq.terminos = b.terminosServidor || [];
    busq.abiertas = new Set();
    busq.entidad = b.terminos.length ? entidadesDe(consulta) : null;
    if (busq.sobre && busq.sobre.consulta !== consulta) cerrarSobre();
    estado.terminos = b.terminos;
    estado.resultados = b.resultados;
    estado.coincidencias = b.terminos.length ? new Set(b.resultados.map(r => r.n)) : null;
    if (busq.entidad) busq.entidad.notas.forEach(x => estado.coincidencias.add(x.nodo));
    if (b.terminos.length) ordenarResultados();
    recalcularAristasBusqueda();
    renderResultados();
    if (estado.vista === 'lista') renderLista();
    encenderCoincidencias(antes);
    pedirDibujo();
  }

