  function calcularModo() {
    if (!anim.pref || anim.nivel === 0) return 'nada';
    return menosMovimiento.matches ? 'suave' : 'completo';
  }

  function aplicarModo() {
    anim.modo = calcularModo();
    document.documentElement.setAttribute('data-anim', anim.modo);
    const b = $('#alternar-animaciones');
    b.setAttribute('aria-checked', String(anim.pref));
    b.title = !anim.pref ? 'Prender las animaciones'
      : anim.nivel === 0 ? 'Las apagué solas porque la compu venía lenta. Apagalas y prendelas para probar de nuevo.'
      : anim.modo === 'suave' ? 'Tu sistema pide menos movimiento: solo hay fundidos suaves y nada se desplaza.'
      : anim.nivel === 1 ? 'Animaciones livianas: las bajé porque la compu venía lenta.'
      : 'Apagar las animaciones';
    if (!completo()) { saltarIntro(true); detenerVida(); vaciarEfectos(); todosNacidos(); } else programarAmbiente();
    pedirDibujo();
  }

  function detenerVida() {
    clearTimeout(anim.tAmbiente);
    clearTimeout(anim.tHover);
    clearTimeout(anim.tDisparo);
    anim.tAmbiente = anim.tHover = anim.tDisparo = 0;
  }

  function vaciarEfectos() {
    anim.efectos = [];
    anim.pulsoSucio = true;
    gestos.choques.length = 0;
    gestos.apreton = null;
    gestos.barrido = null;
    gestos.t = -1;
    programarCuadro();
  }

  function todosNacidos() {
    nodos.forEach(n => { n._nace = 0; });
    anim.encendido = null;
  }

  function nacerPorLobulos(t0) {
    const N = cerebro.nido;
    const alcance = giro.R * 1.55;
    const lotes = new Map();
    const hand = nodosVisibles.filter(n => n.tipo === 'handoff').sort((a, b) => a.modificado.localeCompare(b.modificado));
    for (const n of porImportancia.filter(n => n.tipo !== 'handoff').concat(hand)) {
      if (!n._visible) continue;
      const k = lobuloDe(n);
      let l = lotes.get(k);
      if (!l) lotes.set(k, l = []);
      l.push(n);
    }
    for (const [k, lista] of lotes) {
      const L = cerebro.lobulos[k];
      const d = L ? Math.hypot(L.wx - N[0], L.wy - N[1]) : alcance * 0.6;
      const tl = t0 + 80 + d / alcance * INTRO.dur;
      const paso = INTRO.lote / Math.max(1, lista.length - 1);
      lista.forEach((n, j) => { n._nace = tl + Math.round(j * paso); });
    }
  }

  function climaIntro(fuerza) {
    const color = INTRO.color[anim.oscuro ? 1 : 0];
    ondaGlobal(color, 1.3 * fuerza, 'tronco', INTRO.dur);
    activarLobulo('tronco', color, 1.1 * fuerza);
    choqueLobulo('tronco', color, 0.8 * fuerza);
    marcarPicoEEG(1.2 * fuerza);
  }

  function avanzarIntro(ahora) {
    if (!cerebro || !cerebro.introT0 || cerebro.introPaso >= 4) return;
    const t = ahora - cerebro.introT0;
    if (t >= INTRO.fin) { cerebro.introPaso = 4; return; }
    while (cerebro.introPaso < 2 && t >= INTRO.latidos[cerebro.introPaso]) {
      marcarPicoEEG(0.8);
      cerebro.introPaso++;
    }
    if (cerebro.introPaso === 2 && t >= INTRO.explota) {
      marcarPicoEEG(1.4);
      cerebro.introPaso = 3;
    }
    if (cerebro.introPaso === 3 && t >= INTRO.clima) {
      cerebro.introPaso = 4;
      climaIntro(1);
    }
  }

  function saltarIntro(callado) {
    if (!introCorriendo()) return;
    const paso = cerebro.introPaso;
    cerebro.introT0 = performance.now() - INTRO.fin - 1;
    cerebro.introPaso = 4;
    todosNacidos();
    anim.efectos = anim.efectos.filter(e => e.tipo !== 'intro');
    anim.pulsoSucio = true;
    if (!callado && paso < 4 && completo()) climaIntro(0.8);
    pedirDibujo();
  }

  function camaraIntro(ahora, tiltMeta, escMeta) {
    const t = tiempoIntro(ahora);
    const N = cerebro.nido;
    if (t >= INTRO.fin || !N) return false;
    const d = sale3(limitar((t - INTRO.explota) / (INTRO.clima - INTRO.explota)));
    giro.esc = escMeta * (1 + (INTRO.esc - 1) * (1 - d));
    giro.tilt = tiltMeta + (INTRO.tilt - tiltMeta) * (1 - d);
    const p = proyectar(N[0], N[1], N[2], giro.ang, giro.tilt, giro.esc);
    const q = proyectar(N[0], N[1], N[2], giro.ang, tiltMeta, escMeta);
    giro.px = q.x - p.x;
    giro.py = q.y - p.y;
    return true;
  }

  function soltarPrevia() {
    if (!anim.previa) return;
    anim.previa = null;
    anim.efectos = anim.efectos.filter(e => e.fuente !== 'previa');
    anim.pulsoSucio = true;
    programarCuadro();
  }

  function despertar(sinOla) {
    const ahora = performance.now();
    anim.ultimaActividad = ahora;
    anim.calmado = false;
    if (ritmo.estado === 'sueno') despertarDelSueno(ahora, sinOla);
    if (!anim.encadenado && graficoListo) programarCuadro();
  }

  function despertarDelSueno(ahora, sinOla) {
    ritmo.estado = 'calma';
    ritmo.desperto = ahora;
    ritmo.ensueno = null;
    if (anim.efectos.some(e => e.fuente === 'sueno')) {
      anim.efectos = anim.efectos.filter(e => e.fuente !== 'sueno');
      anim.pulsoSucio = true;
    }
    if (completo() && cerebro && !sinOla) {
      const color = anim.oscuro ? '#a5b4fc' : '#4f46e5';
      activarLobulo('tronco', color, 1.1);
      ondaGlobal(color, 1.1, 'tronco');
    }
    marcarPicoEEG(1.2);
    programarAmbiente(1500);
  }

  function marcarActividad(ev) {
    if (ev.type !== 'pointermove' && (anim.encendido || introCorriendo())) { saltarIntro(false); todosNacidos(); pedirDibujo(); }
    despertar();
  }

  window.addEventListener('wheel', () => { anim.tsRueda = performance.now(); }, { passive: true, capture: true });

  try { anim.calidadFija = localStorage.getItem('cerebro-calidad') === 'fija'; } catch (e) { anim.calidadFija = false; }

  function restaurarCalidad() {
    anim.nivel = 2;
    anim.resplandor = true;
    anim.enfoque = true;
    anim.aristasLivianas = false;
    anim.masivoForzado = false;
    anim.muestras = anim.malas = 0;
    anim.msVentana = anim.msSano = anim.subidas = 0;
    anim.bajadas = [];
    anim.esperaSubir = 20000;
    anim.dtBase = Infinity;
    anim.lentosSeguidos = 0;
    anim.lucesEnDuda = false;
    anim.escala = 1;
    ajustarLienzo();
  }

  function ponerCalidadFija(fija) {
    anim.calidadFija = fija;
    try { localStorage.setItem('cerebro-calidad', fija ? 'fija' : 'auto'); } catch (e) {}
    const c = $('#calidad-fija');
    if (c) c.checked = fija;
    if (fija) {
      restaurarCalidad();
      aplicarModo();
      aviso('Listo: la calidad queda siempre al máximo. Se cambia en la ayuda (?).');
    }
  }

  const NO_BAJAR = { texto: 'No bajarla nunca', hacer: () => ponerCalidadFija(true) };

  function medirCuadro(ahora) {
    const previo = anim.tsPrevio;
    anim.tsPrevio = ahora;
    if (anim.calidadFija) return;
    if (!anim.encadenado || !completo() || arrastrando || ahora - anim.tsListo < 2000 || introCorriendo(ahora)
      || (anim.calmado && anim.escala < 1) || ahora - (anim.tsRueda || -1e9) < 300) return;
    const dt = ahora - previo;
    if (!previo || dt <= 0) return;
    anim.lentosSeguidos = dt > MS_MUY_LENTO + (anim.calmado ? pausaDeCalma() : 0) ? anim.lentosSeguidos + 1 : 0;
    if (anim.lentosSeguidos >= LENTOS_PARA_MINIMO) {
      anim.lentosSeguidos = 0;
      modoMinimo();
      return;
    }
    if (dt > 1000 || (sim && sim.alpha() > 0.05)) return;
    if (!anim.calmado) anim.dtBase = Math.max(6.9, Math.min(anim.dtBase, dt));
    anim.muestras++;
    anim.msVentana += dt;
    const umbral = anim.calmado ? pausaDeCalma() * 2 : Math.min(MS_MALO, Math.max(26, anim.dtBase * 1.6));
    if (dt > umbral) anim.malas++;
    if (anim.muestras < 60 && anim.msVentana < 3000) return;
    const bajar = anim.malas >= anim.muestras * 2 / 3;
    const sana = anim.malas < anim.muestras / 10;
    anim.msSano = sana ? anim.msSano + anim.msVentana : 0;
    if (!bajar) anim.lucesEnDuda = false;
    anim.muestras = anim.malas = 0;
    anim.msVentana = 0;
    if (bajar) bajarNivel();
    else if (anim.bajadas.length && anim.msSano >= anim.esperaSubir && !anim.porSoftware) subirNivel();
  }

  function pausaDeCalma() {
    return anim.escala < 1 ? MS_CALMA_MINIMO : ritmo.estado === 'sueno' ? MS_SUENO : MS_CALMA;
  }

  function bajarNivel() {
    if (anim.nivel <= 1 && anim.masivoForzado) {
      modoMinimo();
      return;
    }
    if (anim.subidas) anim.esperaSubir = Math.min(anim.esperaSubir * 2, 320000);
    anim.msSano = 0;
    if (anim.nivel <= 1) {
      anim.masivoForzado = true;
      anim.bajadas.push('masivo');
      aviso('Pasé al dibujo simple de las conexiones porque la compu seguía lenta. Si se recupera, lo vuelvo a subir solo.', NO_BAJAR);
      pedirDibujo();
      return;
    }
    if (!anim.aristasLivianas && giro.activo) {
      anim.aristasLivianas = true;
      anim.bajadas.push('aristas');
      aviso('Simplifiqué las conexiones mientras el cerebro gira porque la compu venía lenta.', NO_BAJAR);
      pedirDibujo();
      return;
    }
    const conResplandor = anim.resplandor && neuronasGL && neuronasGL.brillo;
    const conEnfoque = anim.enfoque && camara.dof > 0.05;
    if (conResplandor || conEnfoque) {
      if (!anim.lucesEnDuda) {
        anim.lucesEnDuda = true;
        return;
      }
      anim.lucesEnDuda = false;
      anim.resplandor = false;
      anim.enfoque = false;
      anim.bajadas.push('luces');
      aviso(conResplandor && conEnfoque ? 'Apagué el resplandor y el desenfoque de la cámara porque la compu venía lenta.'
        : conResplandor ? 'Apagué el resplandor porque la compu venía lenta.' : 'Apagué el desenfoque de la cámara porque la compu venía lenta.', NO_BAJAR);
      pedirDibujo();
      return;
    }
    anim.nivel = 1;
    anim.bajadas.push('nivel');
    aviso('Bajé las animaciones porque la compu venía lenta. Si se recupera, las vuelvo a subir solo.', NO_BAJAR);
    aplicarModo();
  }

  function dibujaPorSoftware(gl) {
    try {
      const info = gl && gl.getExtension('WEBGL_debug_renderer_info');
      if (info && RE_SOFTWARE.test(String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL)))) return true;
    } catch (e) {}
    let prueba = null;
    try { prueba = document.createElement('canvas').getContext('webgl', { failIfMajorPerformanceCaveat: true }); } catch (e) { prueba = null; }
    if (!prueba) return true;
    const soltar = prueba.getExtension('WEBGL_lose_context');
    if (soltar) soltar.loseContext();
    return false;
  }

  function arrancarLiviano() {
    if (anim.bajadas.length) return;
    anim.aristasLivianas = true;
    anim.resplandor = false;
    anim.enfoque = false;
    anim.nivel = 1;
    anim.masivoForzado = true;
    anim.bajadas.push('aristas', 'luces', 'nivel', 'masivo');
    aviso('El navegador dibuja sin placa de video: uso el dibujo simple, y mientras no pasa nada el cerebro se queda quieto para no gastar procesador.');
  }

  function modoMinimo() {
    if (anim.escala < 1) return;
    if (anim.subidas) anim.esperaSubir = Math.min(anim.esperaSubir * 2, 320000);
    anim.msSano = 0;
    anim.aristasLivianas = true;
    anim.resplandor = false;
    anim.enfoque = false;
    anim.nivel = 1;
    anim.escala = 0.5;
    anim.masivoForzado = true;
    anim.bajadas = ['aristas', 'luces', 'nivel', 'masivo', 'resolucion'];
    aviso('La compu dibuja muy lento: bajé la resolución y los efectos, y mientras no pasa nada el cerebro se queda quieto. Si mejora, los vuelvo a subir solo.', NO_BAJAR);
    aplicarModo();
    ajustarLienzo();
  }

  function subirNivel() {
    const paso = anim.bajadas.pop();
    anim.msSano = 0;
    anim.subidas++;
    if (paso === 'resolucion') {
      anim.escala = 1;
      aviso('Volví a la resolución completa.');
      ajustarLienzo();
      return;
    }
    if (paso === 'nivel') {
      anim.nivel = 2;
      aviso('Volví a subir las animaciones: la compu ya anda bien.');
      aplicarModo();
      return;
    }
    if (paso === 'masivo') {
      anim.masivoForzado = false;
      aviso('Volví a dibujar las conexiones completas.');
    }
    if (paso === 'luces') {
      anim.resplandor = true;
      anim.enfoque = true;
      aviso('Volví a prender el resplandor y el desenfoque.');
    } else if (paso === 'aristas') {
      anim.aristasLivianas = false;
      aviso('Volví a dibujar las conexiones completas al girar.');
    }
    pedirDibujo();
  }

  function aRgba(color, a) {
    pctx.fillStyle = '#000';
    pctx.fillStyle = color;
    const c = pctx.fillStyle;
    if (c[0] !== '#') return c;
    return 'rgba(' + parseInt(c.slice(1, 3), 16) + ',' + parseInt(c.slice(3, 5), 16) + ',' + parseInt(c.slice(5, 7), 16) + ',' + a + ')';
  }

  function sprite(color, forma) {
    const clave = forma + color;
    let s = anim.sprites.get(clave);
    if (s) return s;
    const lado = forma === 'aura' ? 128 : 64;
    const m = lado / 2;
    s = document.createElement('canvas');
    s.width = s.height = lado;
    const c = s.getContext('2d');
    const g = c.createRadialGradient(m, m, 0, m, m, m);
    const paradas = forma === 'aura' ? [[0, 1], [0.5, 0.45], [1, 0]] : [[0, 1], [0.3, 0.55], [1, 0]];
    paradas.forEach(p => g.addColorStop(p[0], aRgba(color, p[1])));
    c.fillStyle = g;
    c.fillRect(0, 0, lado, lado);
    anim.sprites.set(clave, s);
    return s;
  }

  const tinta = e => e.color || (typeof e.tinta === 'string' ? colores[e.tinta] : colorDe(e.tinta));
  const tintaArista = (l, base) => l.clase === 'sugerida' || l.clase === 'parecida' ? 'acento' : l.clase === 'duplicado' ? 'peligro' : base;

  function aristaEntre(a, b) {
    return a && (a.salientes.find(l => l.target === b && l._visible) || a.entrantes.find(l => l.source === b && l._visible)) || null;
  }

  function efectoValido(e) {
    const ok = n => n && n._visible && n._sx !== undefined;
    if (e.n && !ok(e.n)) return false;
    if (e.l && (!e.l._visible || !ok(e.l.source) || !ok(e.l.target))) return false;
    if (e.desde && (!ok(e.desde) || !ok(e.hacia))) return false;
    return true;
  }

  function onda(n, retardo, alfa, dur, crece) {
    anim.efectos.push({ tipo: 'onda', n, t0: performance.now() + retardo, dur, alfa, crece });
    programarCuadro();
  }

  function destello(n, alfa, fuente) {
    anim.efectos.push({ tipo: 'destello', n, t0: performance.now(), dur: 450, alfa, fuente });
    programarCuadro();
  }

  const PRIORIDAD = { wiki: 0, sugerida: 1, duplicado: 2, indice: 3, enlace: 4, responde: 5, cadena: 5, mencion: 6, carpeta: 7, parecida: 8, comparte: 9, aprendida: 10 };
  const BASE_MS = { wiki: 420, sugerida: 800, duplicado: 800, indice: 520, enlace: 520, responde: 380, cadena: 380, mencion: 700, carpeta: 720, parecida: 800, comparte: 800, aprendida: 640 };
  const PESO_RAFAGA = { wiki: 3, indice: 3, enlace: 2, responde: 2, cadena: 2, sugerida: 1, mencion: 1, carpeta: 1, parecida: 1, duplicado: 0, comparte: 0, aprendida: 1 };
  const pesoRafaga = l => PESO_RAFAGA[l.clase] * (1 + nivelUso(usoDe(l)));
  const ALFA_ESTELA = [0.5, 0.3, 0.15];
  const COLA = [[6, 2.6, 0.6], [12, 2.2, 0.42], [18, 1.8, 0.26], [24, 1.4, 0.12]];

  function nuevoImpulso(l, t, op, t0, factor) {
    const a = l.source;
    const b = l.target;
    const largo = Math.hypot(b._sx - a._sx, b._sy - a._sy) || 0;
    const uso = nivelUso(usoDe(l));
    const dur = BASE_MS[l.clase] * Math.min(1.6, Math.max(0.85, 0.75 + largo / 600)) * (factor || 1) * (1 - 0.15 * uso);
    return { tipo: 'impulso', l, t0, dur, tinta: t, alfa: op.alfa, estela: op.estela, hueco: l.clase === 'sugerida' || l.clase === 'parecida', fuente: op.fuente, salto: uso >= 2 ? 11 : 0 };
  }

  function lanzarImpulsos(n, op) {
    let cands = [];
    const sumar = l => { if (l._visible && !tapada(l) && (l.source._en || l.target._en)) cands.push(l); };
    n.salientes.forEach(sumar);
    n.entrantes.forEach(sumar);
    if (op.azar) {
      for (let i = cands.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        const x = cands[i];
        cands[i] = cands[j];
        cands[j] = x;
      }
    } else {
      cands.sort((a, b) => (PRIORIDAD[a.clase] - PRIORIDAD[b.clase]) || (hashArista(a) - hashArista(b)));
    }
    cands = cands.slice(0, op.tope);
    const ahora = performance.now();
    let entrantes = 0;
    const alTerminarEntrante = () => { if (--entrantes === 0) onda(n, 0, 0.35, 500, 30); };
    for (const l of cands) {
      const imp = nuevoImpulso(l, tintaArista(l, n), op, ahora + (op.retardo || 0) + 80 + hashArista(l) % 120);
      if (l.source === n && op.destello) imp.alLlegar = () => { destello(l.target, op.alfa * 0.75); descargar(l.target, 0.45); };
      else if (l.target === n && op.ondaFinal) { entrantes++; imp.alLlegar = alTerminarEntrante; }
      anim.efectos.push(imp);
    }
    programarCuadro();
  }

  function disparar(n) {
    if (!completo() || !graficoListo || estado.vista !== 'grafo' || !n || !n._visible) return;
    if (esMovil() && panel.classList.contains('abierto')) return;
    anim.efectos = anim.efectos.filter(e => e.tipo !== 'impulso' || e.fuente === 'repaso');
    descargar(n, 1);
    choque(n, colorDe(n), 0.8);
    onda(n, 0, 0.6, 600, 56);
    onda(n, 120, 0.4, 600, 56);
    lanzarImpulsos(n, { fuente: 'disparo', tope: anim.nivel === 2 ? 48 : 16, alfa: 0.95, estela: anim.nivel === 2 ? 3 : 1, destello: true, ondaFinal: true });
    latirLogo();
  }

  function latirLogo() {
    if (!completo()) return;
    const s = $('.marca svg');
    s.classList.remove('late');
    void s.getBoundingClientRect();
    s.classList.add('late');
    clearTimeout(anim.tLogo);
    anim.tLogo = setTimeout(() => s.classList.remove('late'), 1000);
  }

  function chispa(n) {
    if (estado.hover !== n || arrastrando || !completo() || anim.nivel !== 2 || estado.vista !== 'grafo') return;
    const u = anim.ultimaChispa;
    if (u && u.n === n && performance.now() - u.t < 3000) return;
    anim.ultimaChispa = { n, t: performance.now() };
    anim.efectos = anim.efectos.filter(e => e.fuente !== 'chispa' && e.fuente !== 'latido' && e.fuente !== 'ambiente');
    lanzarImpulsos(n, { fuente: 'chispa', tope: 16, alfa: 0.55, estela: 1 });
  }

  function ambientePosible() {
    return completo() && anim.nivel === 2 && !document.hidden && graficoListo && estado.vista === 'grafo';
  }

  function ambienteOcupado() {
    return !!(estado.hover || arrastrando || estado.coincidencias || estado.nombrada || (sim && sim.alpha() > 0.05) || anim.encendido || anim.efectos.some(e => e.fuente === 'disparo' || e.fuente === 'chispa'));
  }

  function programarAmbiente(demora) {
    clearTimeout(anim.tAmbiente);
    anim.tAmbiente = 0;
    if (!ambientePosible()) return;
    const base = estado.seleccionado ? 5200 + Math.random() * 1600 : 3500 + Math.random() * 3500;
    anim.tAmbiente = setTimeout(tickAmbiente, demora == null ? base : demora);
  }

  function tickAmbiente() {
    anim.tAmbiente = 0;
    if (!ambientePosible()) return;
    if (ritmo.estado === 'sueno') {
      if (!ambienteOcupado()) dormir(performance.now());
      programarAmbiente(6000 + Math.random() * 4000);
      return;
    }
    if (ambienteOcupado()) { programarAmbiente(1500); return; }
    const s = estado.seleccionado;
    if (s) { if (s._visible && s._en && !anim.sobrePanel && !esMovil()) latido(s); }
    else if (Math.random() < 0.75) rafaga();
    else pensarCadena();
    programarAmbiente();
  }

  function elegirOrigen(filtro) {
    let total = 0;
    const cands = [];
    for (const n of nodosVisibles) {
      if (!n._en || !filtro(n)) continue;
      total += (1 + n.grado / 10) * (n._fresco || 1);
      cands.push([n, total]);
    }
    if (!cands.length) return null;
    const r = Math.random() * total;
    for (const c of cands) if (r < c[1]) return c[0];
    return cands[cands.length - 1][0];
  }

  function rafaga() {
    const o = elegirOrigen(n => n._cuenta > 0);
    if (!o) return;
    destello(o, 0.5, 'ambiente');
    const util = l => l._visible && PESO_RAFAGA[l.clase] > 0 && !tapada(l);
    let ls = o.salientes.filter(util);
    if (!ls.length) ls = o.entrantes.filter(util);
    const cuantos = Math.min(ls.length, 2 + Math.floor(Math.random() * 3));
    const t = performance.now();
    for (let i = 0; i < cuantos; i++) {
      let total = 0;
      ls.forEach(l => { total += pesoRafaga(l); });
      let r = Math.random() * total;
      let j = 0;
      while (j < ls.length - 1 && (r -= pesoRafaga(ls[j])) >= 0) j++;
      const l = ls.splice(j, 1)[0];
      const imp = nuevoImpulso(l, tintaArista(l, o), { alfa: 0.5, estela: 2, fuente: 'ambiente' }, t + 60 + i * 90);
      imp.alLlegar = () => destello(l.target, 0.4, 'ambiente');
      anim.efectos.push(imp);
    }
    programarCuadro();
  }

  function pensarCadena() {
    const esPaso = l => l._visible && (l.clase === 'wiki' || l.clase === 'cadena' || l.clase === 'responde' || l.clase === 'indice');
    const o = elegirOrigen(n => n.salientes.some(esPaso));
    if (!o) return;
    const visitadas = new Set([o]);
    let restantes = 3 + Math.floor(Math.random() * 3);
    const paso = (n, t0) => {
      if (restantes-- <= 0) return;
      const ops = n.salientes.filter(l => esPaso(l) && !visitadas.has(l.target) && (l.source._en || l.target._en));
      if (!ops.length) return;
      const l = ops[Math.floor(Math.random() * ops.length)];
      visitadas.add(l.target);
      const imp = nuevoImpulso(l, n, { alfa: 0.6, estela: 3, fuente: 'ambiente' }, t0, 1.1);
      imp.alLlegar = ahora => {
        destello(l.target, 0.45, 'ambiente');
        if (ambientePosible() && !ambienteOcupado()) paso(l.target, ahora);
      };
      anim.efectos.push(imp);
      programarCuadro();
    };
    destello(o, 0.45, 'ambiente');
    paso(o, performance.now() + 60);
  }

  function repasar(notas, color, veces, op) {
    const lista = [];
    for (const n of notas) if (n && n._visible && n._sx !== undefined && n !== lista[lista.length - 1]) lista.push(n);
    if (lista.length < 2 || !completo() || !graficoListo || estado.vista !== 'grafo') return null;
    let pasada = 0;
    const paso = (i, t0) => {
      const b = lista[i + 1];
      const f = op.factores[Math.min(pasada, op.factores.length - 1)];
      const imp = nuevoImpulso({ source: lista[i], target: b, _visible: true, clase: 'cadena' }, null, { alfa: op.alfa, estela: 3, fuente: op.fuente }, t0, f);
      imp.color = color;
      imp.alLlegar = ahora => {
        if (op.descarga) descargar(b, op.descarga);
        if (op.luz) activarNota(b, color, op.luz, 900);
        if (i + 2 < lista.length) paso(i + 1, ahora);
        else if (++pasada < veces) {
          if (op.descarga) descargar(lista[0], op.descarga);
          paso(0, ahora + 160);
        } else if (op.alTerminar) op.alTerminar(lista);
      };
      anim.efectos.push(imp);
      programarCuadro();
    };
    if (op.descarga) descargar(lista[0], op.descarga);
    paso(0, performance.now() + (op.retardo || 0));
    return lista;
  }

  function husoDormido(ahora) {
    if (!cerebro || !cerebro.vecinos.length) return;
    const ady = cerebro.ady;
    const px = cerebro.px;
    const i0 = cerebro.vecinos[Math.floor(Math.random() * cerebro.vecinos.length)][0];
    const color = anim.oscuro ? '#a5b4fc' : '#6366f1';
    const cola = [i0];
    const vistos = new Set(cola);
    let n = 0;
    while (cola.length && n < 16 && vida.chispas.length < 160) {
      const i = cola.shift();
      for (const j of ady[i]) {
        if (vistos.has(j)) continue;
        vistos.add(j);
        cola.push(j);
        vida.chispas.push({ a: i, b: j, t0: ahora + n * 55, color, saltos: 0, max: 2 + n % 3 });
        if (++n >= 16) break;
      }
    }
    const A = px[i0];
    activar(A.x, A.y, A.z, 170 * cerebro.S, color, 0.5, 1500);
    ritmo.huso = ahora;
  }

  function ensonar(s) {
    const lista = repasar(s.notas, s.color, 1, { alfa: 0.3, factores: [0.4], descarga: 0.25, luz: 0.3, fuente: 'sueno' });
    if (!lista) return false;
    const t0 = performance.now();
    const dur = 2600 + 190 * lista.length;
    s.hasta = t0 + dur;
    ritmo.ensueno = s;
    if (DIBUJO_EFECTO.cartelSueno) anim.efectos.push({ tipo: 'cartelSueno', fuente: 'sueno', n: lista[0], texto: s.texto, color: s.color, t0, dur });
    return true;
  }

  function dormir(ahora) {
    if (ahora >= ritmo.proximoSueno && vivo.elegirSueno) {
      ritmo.proximoSueno = ahora + 10000 + Math.random() * 5000;
      const s = vivo.elegirSueno();
      if (s && ensonar(s)) return;
    }
    husoDormido(ahora);
  }

  function latido(s) {
    onda(s, 0, 0.35, 900, 22);
    lanzarImpulsos(s, { fuente: 'latido', tope: 3, azar: true, alfa: 0.3, estela: 1 });
  }

  function ponerPrevia(id) {
    const n = id ? porId.get(id) || null : null;
    if ((anim.previa ? anim.previa.n : null) === n) return;
    anim.efectos = anim.efectos.filter(e => e.fuente !== 'previa');
    anim.previa = n ? { n, t0: performance.now() } : null;
    if (n && completo() && graficoListo) {
      const l = aristaEntre(estado.seleccionado, n);
      if (l && l.source._sx !== undefined && l.target._sx !== undefined) anim.efectos.push(nuevoImpulso(l, 'resalte', { alfa: 0.9, estela: 3, fuente: 'previa' }, performance.now()));
    }
    anim.pulsoSucio = true;
    programarCuadro();
  }

  function cabeza(x, y, color, alfa, alfaBrillo, lado, r, nucleo) {
    const c = pctx;
    if (anim.oscuro) {
      c.globalAlpha = alfaBrillo * alfa;
      c.drawImage(sprite(color, 'brillo'), x - lado / 2, y - lado / 2, lado, lado);
      c.globalAlpha = alfa;
      c.fillStyle = nucleo || color;
      c.beginPath();
      c.arc(x, y, r, 0, TAU);
      c.fill();
    } else {
      c.globalAlpha = alfa;
      c.beginPath();
      c.arc(x, y, r, 0, TAU);
      c.strokeStyle = colores.halo;
      c.lineWidth = 2.4;
      c.stroke();
      c.fillStyle = color;
      c.fill();
    }
  }

  const centroPant = { x: 0, y: 0 };
  function curvaEntre(x0, y0, x1, y1) {
    const mx = (x0 + x1) / 2;
    const my = (y0 + y1) / 2;
    const vx = centroPant.x - mx;
    const vy = centroPant.y - my;
    const dc = Math.hypot(vx, vy) || 1;
    const m = Math.min(dc * 0.4, Math.hypot(x1 - x0, y1 - y0) * 0.32);
    return [mx + vx / dc * m, my + vy / dc * m];
  }

  function curvaPor(x0, y0, x1, y1, vx, vy) {
    const mx = (x0 + x1) / 2;
    const my = (y0 + y1) / 2;
    const L = Math.hypot(x1 - x0, y1 - y0) || 1;
    const ux = (x1 - x0) / L;
    const uy = (y1 - y0) / L;
    const a = Math.max(-0.2 * L, Math.min(0.2 * L, 1.6 * ((vx - mx) * ux + (vy - my) * uy)));
    const b = Math.max(-0.4 * L, Math.min(0.4 * L, 1.6 * ((vy - my) * ux - (vx - mx) * uy)));
    return [mx + a * ux - b * uy, my + a * uy + b * ux];
  }

  function lobuloDe(n) {
    if (n._lob !== undefined) return n._lob;
    const R = cerebro && cerebro.rutas;
    if (!R) return -1;
    const x = n._tx !== undefined ? n._tx : n.x;
    const y = n._ty !== undefined ? n._ty : n.y;
    let i = -1;
    if (ctxForma.isPointInPath(cerebro.cerebelo, x, y)) i = R.idx.get('cerebelo');
    else if (ctxForma.isPointInPath(cerebro.tronco, x, y)) i = R.idx.get('tronco');
    else {
      let md = Infinity;
      cerebro.lobulos.forEach((l, j) => {
        if (!R.corteza[j]) return;
        const d = (l.wx - x) ** 2 + (l.wy - y) ** 2;
        if (d < md) { md = d; i = j; }
      });
    }
    if (n._tx !== undefined) n._lob = i;
    return i;
  }

  let cuadroVia = 1;
  function ranuraVia(a, b) {
    const R = cerebro && cerebro.rutas;
    if (!R) return -1;
    const la = lobuloDe(a);
    const lb = lobuloDe(b);
    if (la < 0 || lb < 0 || la === lb || !R.hay[la * R.n + lb]) return -1;
    const sa = (a.z || 0) < 0 ? 0 : 1;
    const sb = (b.z || 0) < 0 ? 0 : 1;
    const lado = sa !== sb && R.corteza[la] && R.corteza[lb] ? 2 : R.corteza[la] ? sa : sb;
    return (la * R.n + lb) * 3 + lado;
  }

  function viaMundo(k, out) {
    const R = cerebro.rutas;
    const j = k - k % 3;
    const lado = k % 3;
    const f = lado === 2 ? R.cruce : R.vias;
    out[0] = f[j];
    out[1] = f[j + 1];
    out[2] = lado === 2 ? 0 : lado ? f[j + 2] : -f[j + 2];
    return out;
  }

  function controlCurva(a, b) {
    const k = ranuraVia(a, b);
    if (k < 0) return curvaEntre(a._sx, a._sy, b._sx, b._sy);
    const R = cerebro.rutas;
    if (R.marca[k] !== cuadroVia) {
      const v = viaMundo(k, R.tmp);
      const p = proyectar(v[0], v[1], v[2]);
      R.px[k] = p.x * transformacion.k + transformacion.x;
      R.py[k] = p.y * transformacion.k + transformacion.y;
      R.marca[k] = cuadroVia;
    }
    return curvaPor(a._sx, a._sy, b._sx, b._sy, R.px[k], R.py[k]);
  }

  const puntoCurva = (p0, p1, p2, t) => { const u = 1 - t; return u * u * p0 + 2 * u * t * p1 + t * t * p2; };

  function trazarCurvaHasta(c, x0, y0, cx, cy, x1, y1, t) {
    c.moveTo(x0, y0);
    if (t >= 1) { c.quadraticCurveTo(cx, cy, x1, y1); return; }
    const ax = x0 + (cx - x0) * t;
    const ay = y0 + (cy - y0) * t;
    c.quadraticCurveTo(ax, ay, ax + (cx + (x1 - cx) * t - ax) * t, ay + (cy + (y1 - cy) * t - ay) * t);
  }

  function recorrido(a, b) {
    const dx = b._sx - a._sx;
    const dy = b._sy - a._sy;
    const d = Math.hypot(dx, dy);
    const ini = a._sr + 1;
    const tramo = d - b._sr - 2 - ini;
    if (!(tramo >= 4)) return null;
    const [cx, cy] = controlCurva(a, b);
    return { x: a._sx, y: a._sy, ux: dx / d, uy: dy / d, d, ini, tramo,
             px: s => puntoCurva(a._sx, cx, b._sx, s / d), py: s => puntoCurva(a._sy, cy, b._sy, s / d) };
  }

  const DIBUJO_EFECTO = {
    onda(e, p, eL) {
      const n = e.n;
      if (!n._en) return;
      const q = sale3(p);
      pctx.globalAlpha = e.alfa * (1 - q);
      pctx.strokeStyle = colorDe(n);
      pctx.lineWidth = 2 - 1.5 * q;
      trazarForma(n, n._sx, n._sy, n._sr + 2 + e.crece * eL * q, pctx);
      pctx.stroke();
    },
    destello(e, p, eL) {
      const n = e.n;
      if (!n._en) return;
      const q = sale3(p);
      const color = colorDe(n);
      if (anim.oscuro) {
        const R = Math.max(10, 3 * n._sr);
        pctx.globalAlpha = e.alfa * (1 - q);
        pctx.drawImage(sprite(color, 'brillo'), n._sx - R, n._sy - R, 2 * R, 2 * R);
      }
      pctx.globalAlpha = 0.5 * e.alfa * (1 - q);
      pctx.strokeStyle = color;
      pctx.lineWidth = 1.5;
      trazarForma(n, n._sx, n._sy, n._sr + 1 + 10 * eL * q, pctx);
      pctx.stroke();
    },
    anillo(e, p) {
      const n = e.n;
      if (!n._en) return;
      const q = sale3(p);
      pctx.globalAlpha = e.alfa * (1 - q);
      pctx.strokeStyle = colores.resalte;
      pctx.lineWidth = 2;
      trazarForma(n, n._sx, n._sy, n._sr + 3.4 + 11 * q, pctx);
      pctx.stroke();
    },
    impulso(e, p, eL) {
      const c = pctx;
      const R = recorrido(e.l.source, e.l.target);
      if (!R) return;
      const env = Math.min(1, p / 0.08, (1 - p) / 0.08);
      const color = tinta(e);
      let pos = R.ini + R.tramo * seno(p);
      if (e.salto) {
        const paso = e.salto * eL;
        const k = Math.floor((pos - R.ini) / paso);
        const f = (pos - R.ini) / paso - k;
        const nodo = R.ini + k * paso;
        pos = Math.min(R.ini + R.tramo, R.ini + (k + sale3(f)) * paso);
        c.globalAlpha = 0.55 * e.alfa * env * (1 - f);
        c.fillStyle = color;
        c.beginPath();
        c.arc(R.px(nodo), R.py(nodo), 2.4 * eL, 0, TAU);
        c.fill();
      }
      const x = R.px(pos);
      const y = R.py(pos);
      if (e.hueco) {
        c.globalAlpha = e.alfa * env;
        c.strokeStyle = color;
        c.lineWidth = 1.4;
        c.beginPath();
        c.arc(x, y, 3 * eL, 0, TAU);
        c.stroke();
        return;
      }
      const L = Math.min(40 * eL, 0.25 * R.d, pos - R.ini);
      if (L > 0.5) {
        c.strokeStyle = color;
        c.lineWidth = 2 * eL;
        c.lineCap = 'round';
        for (let i = 0; i < e.estela; i++) {
          const s0 = pos - L * i / e.estela;
          const s1 = pos - L * (i + 1) / e.estela;
          c.globalAlpha = ALFA_ESTELA[i] * e.alfa * env;
          c.beginPath();
          c.moveTo(R.px(s0), R.py(s0));
          c.lineTo(R.px(s1), R.py(s1));
          c.stroke();
        }
      }
      cabeza(x, y, color, e.alfa * env, 0.9, 14 * eL, (anim.oscuro ? 2.2 : 2.6) * eL, colores.texto);
    },
    cometa(e, p, eL) {
      const R = recorrido(e.desde, e.hacia);
      if (!R) return;
      const pos = R.ini + R.tramo * entraSale(p);
      const color = colorDe(e.hacia);
      pctx.fillStyle = color;
      for (const [dist, radio, alfa] of COLA) {
        const s = pos - dist * eL;
        if (s < R.ini) break;
        pctx.globalAlpha = alfa;
        pctx.beginPath();
        pctx.arc(R.px(s), R.py(s), radio * eL, 0, TAU);
        pctx.fill();
      }
      cabeza(R.px(pos), R.py(pos), color, 1, 0.95, 16 * eL, 3 * eL, colores.texto);
    }
  };

  function trazarCurva(c, a, b, hasta) {
    const [qx, qy] = controlCurva(a, b);
    c.beginPath();
    c.moveTo(a._sx, a._sy);
    if (hasta >= 1) { c.quadraticCurveTo(qx, qy, b._sx, b._sy); return; }
    for (let i = 1; i <= 24; i++) {
      const t = hasta * i / 24;
      c.lineTo(puntoCurva(a._sx, qx, b._sx, t), puntoCurva(a._sy, qy, b._sy, t));
    }
  }

  DIBUJO_EFECTO.potencia = (e, p, eL) => {
    const q = p < 0.25 ? sale3(p / 0.25) : 1 - seno((p - 0.25) / 0.75);
    pctx.strokeStyle = e.color;
    pctx.lineCap = 'round';
    trazarCurva(pctx, e.l.source, e.l.target, 1);
    pctx.globalAlpha = 0.22 * q;
    pctx.lineWidth = (4 + 8 * q) * eL;
    pctx.stroke();
    pctx.globalAlpha = 0.9 * q;
    pctx.lineWidth = (1.2 + 2.6 * q) * eL;
    pctx.stroke();
  };

  DIBUJO_EFECTO.brote = (e, p, eL) => {
    const a = e.l.source;
    const b = e.l.target;
    const crece = sale3(Math.min(1, p / 0.6));
    const alfa = p < 0.6 ? 1 : 1 - (p - 0.6) / 0.4;
    pctx.strokeStyle = e.color;
    pctx.fillStyle = e.color;
    pctx.lineCap = 'round';
    trazarCurva(pctx, a, b, crece);
    pctx.globalAlpha = 0.9 * alfa;
    pctx.lineWidth = 2 * eL;
    pctx.stroke();
    const [qx, qy] = controlCurva(a, b);
    pctx.beginPath();
    pctx.arc(puntoCurva(a._sx, qx, b._sx, crece), puntoCurva(a._sy, qy, b._sy, crece), 3 * eL, 0, TAU);
    pctx.fill();
  };

  DIBUJO_EFECTO.apaga = (e, p, eL) => {
    pctx.strokeStyle = e.color;
    pctx.lineCap = 'butt';
    pctx.setLineDash([2 * eL, 3 * eL]);
    trazarCurva(pctx, e.desde, e.hacia, 1);
    pctx.globalAlpha = 0.7 * (1 - p);
    pctx.lineWidth = 1.3 * eL * (1 - 0.6 * p);
    pctx.stroke();
    pctx.setLineDash([]);
  };

  DIBUJO_EFECTO.intro = (e, p, eL) => {
    const N = cerebro && cerebro.nido;
    if (!N) return;
    const t = p * e.dur;
    const q = proyectar(N[0], N[1], N[2]);
    const tr = transformacion;
    const x = q.x * tr.k + tr.x;
    const y = q.y * tr.k + tr.y;
    const color = INTRO.color[anim.oscuro ? 1 : 0];
    const nucleo = anim.oscuro ? '#ffffff' : color;
    const luz = anim.oscuro ? 1 : 0.6;
    const c = pctx;
    c.strokeStyle = color;
    c.lineCap = 'round';
    if (t < INTRO.explota) {
      let late = 0;
      for (const tb of INTRO.latidos) {
        const g = (t - tb) / 60;
        late = Math.max(late, Math.exp(-g * g));
        const u = (t - tb) / 380;
        if (u < 0 || u >= 1) continue;
        c.globalAlpha = 0.7 * (1 - u) * (1 - u);
        c.lineWidth = 1.6;
        c.beginPath();
        c.arc(x, y, (6 + 38 * sale3(u)) * eL, 0, TAU);
        c.stroke();
      }
      const entra = Math.min(1, t / 140);
      const toma = limitar((t - INTRO.explota + 160) / 160);
      const R = (12 + 26 * late + 20 * toma) * eL;
      c.globalAlpha = entra * (0.45 + 0.55 * Math.max(late, toma)) * luz;
      c.drawImage(sprite(color, 'brillo'), x - R, y - R, 2 * R, 2 * R);
      cabeza(x, y, color, entra, 0, 0, (2.4 + 2.2 * late) * (1 - 0.45 * toma) * eL, nucleo);
      c.lineCap = 'butt';
      return;
    }
    const v = limitar((t - INTRO.explota) / (e.dur - INTRO.explota));
    const a = 1 - v;
    const s = sale3(v);
    const R = (40 + 260 * s) * eL;
    c.globalAlpha = a * a * luz;
    c.drawImage(sprite(color, 'aura'), x - R, y - R, 2 * R, 2 * R);
    c.globalAlpha = 0.85 * a;
    c.lineWidth = (0.6 + 2.6 * a) * eL;
    c.beginPath();
    c.arc(x, y, (10 + 330 * s) * eL, 0, TAU);
    c.stroke();
    c.globalAlpha = 0.6 * a;
    c.lineWidth = (0.8 + 1.4 * a) * eL;
    c.beginPath();
    for (let i = 0; i < INTRO.rayos; i++) {
      const ang = i / INTRO.rayos * TAU + 0.3;
      const r0 = (8 + 150 * s) * eL;
      const r1 = r0 + (i % 2 ? 26 : 46) * a * eL;
      c.moveTo(x + Math.cos(ang) * r0, y + Math.sin(ang) * r0);
      c.lineTo(x + Math.cos(ang) * r1, y + Math.sin(ang) * r1);
    }
    c.stroke();
    cabeza(x, y, color, a, 0, 0, Math.max(0.5, 5.5 * a * eL), nucleo);
    c.lineCap = 'butt';
  };

  function limpiarPulso() {
    if (!anim.pulsoSucio) return;
    pctx.setTransform(1, 0, 0, 1, 0, 0);
    pctx.clearRect(0, 0, pulso.width, pulso.height);
    anim.pulsoSucio = false;
  }

  function despejarTextos() {
    const cajas = anim.cajasTexto;
    if (!cajas.length) return;
    const tapas = vivo.tapas;
    pctx.save();
    pctx.globalCompositeOperation = 'destination-out';
    pctx.fillStyle = '#000';
    for (const b of cajas) {
      let tapada = false;
      for (const t of tapas) if (b[0] < t[2] && b[2] > t[0] && b[1] < t[3] && b[3] > t[1]) { tapada = true; break; }
      if (tapada) continue;
      pctx.globalAlpha = 0.6 * Math.min(1, b[4]);
      pctx.fillRect(b[0], b[1], b[2] - b[0], b[3] - b[1]);
    }
    pctx.restore();
  }

  function dibujarPulso(ahora) {
    limpiarPulso();
    pctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const eL = Math.min(1.6, Math.max(0.55, Math.sqrt(transformacion.k)));
    const lista = anim.efectos;
    anim.efectos = [];
    let hubo = false;
    const dv = anim.descargasVivas;
    dv.length = 0;
    for (const e of lista) if (e.tipo === 'descarga' && ahora >= e.t0 && ahora < e.t0 + e.dur && e.n._en) dv.push(e.n);
    vivo.tapas.length = 0;
    for (const e of lista) {
      const p = (ahora - e.t0) / e.dur;
      if (p < 0) { anim.efectos.push(e); continue; }
      const valido = efectoValido(e);
      if (!valido || p >= 1) {
        if (e.alPegar && !e.pego) { e.pego = true; e.alPegar(); }
        if (valido && e.alLlegar) e.alLlegar(ahora);
        continue;
      }
      DIBUJO_EFECTO[e.tipo](e, p, eL);
      hubo = true;
      anim.efectos.push(e);
    }
    const previaViva = anim.previa ? dibujarPrevia(ahora, eL) : false;
    if (hubo || previaViva) despejarTextos();
    let firma = vivo.tapas.length;
    for (const b of vivo.tapas) firma = (Math.imul(firma, 31) + Math.round(b[0] / 3) * 7 + Math.round(b[1] / 3) * 13 + Math.round(b[2] / 3)) | 0;
    if (firma !== anim.firmaTapas) { anim.firmaTapas = firma; pedirDibujo(); }
    if (vivo.alCerrar) {
      const f = vivo.alCerrar;
      vivo.alCerrar = null;
      f(ahora);
    }
    if (hubo || anim.previa) anim.pulsoSucio = true;
    pctx.globalAlpha = 1;
    pctx.setLineDash([]);
    return anim.efectos.length > 0 || previaViva;
  }

  function dibujarPrevia(ahora, eL) {
    const pv = anim.previa;
    const n = pv.n;
    if (!n._visible || n._sx === undefined) return false;
    const q = Math.min(1, (ahora - pv.t0) / 260);
    const x0 = 18;
    const y0 = 58;
    const x1 = ancho - anchoPanel() - 18;
    const y1 = alto - 58;
    if (x1 - x0 < 40 || y1 - y0 < 40) return false;
    const c = pctx;
    if (n._sx >= x0 && n._sx <= x1 && n._sy >= 18 && n._sy <= alto - 18) {
      const l = aristaEntre(estado.seleccionado, n);
      if (l) {
        c.globalAlpha = 0.9;
        c.strokeStyle = colores.resalte;
        c.lineWidth = 2 * eL;
        c.lineCap = 'round';
        c.beginPath();
        c.moveTo(l.source._sx, l.source._sy);
        c.lineTo(l.target._sx, l.target._sy);
        c.stroke();
      }
      c.globalAlpha = 1;
      c.strokeStyle = colores.resalte;
      c.lineWidth = 2.4;
      trazarForma(n, n._sx, n._sy, n._sr + (completo() ? 5 + 3 * atras(q) : 8), c);
      c.stroke();
    } else {
      const cx = (x0 + x1) / 2;
      const cy = (y0 + y1) / 2;
      const dx = n._sx - cx;
      const dy = n._sy - cy;
      let t = Infinity;
      if (dx > 0) t = Math.min(t, (x1 - cx) / dx); else if (dx < 0) t = Math.min(t, (x0 - cx) / dx);
      if (dy > 0) t = Math.min(t, (y1 - cy) / dy); else if (dy < 0) t = Math.min(t, (y0 - cy) / dy);
      const d = Math.hypot(dx, dy);
      if (!isFinite(t) || !d) return false;
      const px = cx + dx * t;
      const py = cy + dy * t;
      const ux = dx / d;
      const uy = dy / d;
      c.globalAlpha = 1;
      c.beginPath();
      c.moveTo(px, py);
      c.lineTo(px - ux * 11 - uy * 6, py - uy * 11 + ux * 6);
      c.lineTo(px - ux * 11 + uy * 6, py - uy * 11 - ux * 6);
      c.closePath();
      c.strokeStyle = colores.halo;
      c.lineWidth = 2;
      c.lineJoin = 'round';
      c.stroke();
      c.fillStyle = colores.resalte;
      c.fill();
    }
    return completo() && q < 1;
  }

  function leerColores() {
    const cs = getComputedStyle(document.documentElement);
    const v = n => cs.getPropertyValue(n).trim();
    colores = {
      fondo: v('--fondo-grafo'),
      fondoCentro: v('--fondo-grafo-centro'),
      vineta: v('--vineta'),
      texto: v('--texto'),
      texto2: v('--texto-2'),
      texto3: v('--texto-3'),
      linea: v('--linea'),
      lineaFuerte: v('--linea-fuerte'),
      acento: v('--acento'),
      peligro: v('--peligro'),
      resalte: v('--resalte'),
      halo: v('--halo'),
      bordeNodo: v('--borde-nodo'),
      auraAlfa: parseFloat(v('--aura-alfa')) || 0,
      brilloAlfa: parseFloat(v('--brillo-alfa')) || 0,
      nucleo: v('--nucleo') === 'transparent' ? '' : v('--nucleo')
    };
  }

  function ajustarLienzo() {
    const r = centro.getBoundingClientRect();
    ancho = Math.max(1, r.width);
    alto = Math.max(1, r.height);
    dpr = (window.devicePixelRatio || 1) * anim.escala;
    lienzo.width = Math.round(ancho * dpr);
    lienzo.height = Math.round(alto * dpr);
    lienzo.style.width = ancho + 'px';
    lienzo.style.height = alto + 'px';
    pulso.width = lienzo.width;
    pulso.height = lienzo.height;
    pulso.style.width = ancho + 'px';
    pulso.style.height = alto + 'px';
    anim.pulsoSucio = false;
    pedirDibujo();
  }

  function pedirDibujo() {
    escenaSucia = true;
    programarCuadro();
  }

  function programarCuadro(espera = 0) {
    if (enCuadro) {
      pedidoEnCuadro = true;
      return;
    }
    if (dibujoPendiente) {
      if (!espera && esperaCuadro && !anim.calmado) {
        clearTimeout(esperaCuadro);
        esperaCuadro = 0;
        requestAnimationFrame(cuadro);
      }
      return;
    }
    dibujoPendiente = true;
    const falta = espera - (performance.now() - anim.ahora);
    if (falta > 4) esperaCuadro = setTimeout(() => { esperaCuadro = 0; requestAnimationFrame(cuadro); }, falta);
    else requestAnimationFrame(cuadro);
  }

  function pegarNotaAlCursor() {
    if (!arrastrando || !cursorNota) return;
    const n = arrastrando;
    const q = desproyectar(transformacion.invertX(cursorNota[0]), transformacion.invertY(cursorNota[1]), n.z || 0);
    n.fx = n.x = q[0];
    n.fy = n.y = q[1];
  }

  function cuadro() {
    dibujoPendiente = false;
    enCuadro = true;
    pedidoEnCuadro = false;
    let seguir = false;
    try {
      seguir = vueltaDeCuadro();
    } finally {
      enCuadro = false;
      if (seguir || pedidoEnCuadro) programarCuadro(seguir && anim.calmado ? pausaDeCalma() : 0);
    }
  }

  function vueltaDeCuadro() {
    const ahora = performance.now();
    anim.ahora = ahora;
    captura.cuadro++;
    if (!graficoListo || estado.vista !== 'grafo') { anim.efectos = []; limpiarPulso(); limpiarNeuronas(); dibujarEEG(ahora); anim.encadenado = false; anim.calmado = false; fallarCapturas(); return false; }
    medirCuadro(ahora);
    avanzarIntro(ahora);
    actualizarGestos(ahora);
    actualizarRitmo(ahora);
    elegirBrasas(ahora);
    asegurarVida();
    const gira = moverGiro(ahora);
    pegarNotaAlCursor();
    anim.gira = gira;
    if (anim.dibujoLiviano && !gira) escenaSucia = true;
    const reposo = anim.calmado && (anim.escala < 1 || anim.porSoftware);
    const neuronasVivas = !!(neuronasGL && cerebro && completo()) && !reposo;
    if (escenaSucia || gira || ahora < anim.escenaHasta) { escenaSucia = false; dibujar(ahora); }
    else if (neuronasVivas) pintarNeuronas(ahora);
    dibujarEEG(ahora);
    const vivo = (anim.efectos.length || anim.previa || anim.pulsoSucio) ? dibujarPulso(ahora) : false;
    if (captura.pedidos.length || captura.grabacion) componerCaptura(ahora);
    const efectosVivos = vivo && !(reposo && anim.efectos.every(e => e.tipo === 'vida' || e.tipo === 'chats'));
    const seguir = efectosVivos || gira || neuronasVivas || ahora < anim.escenaHasta || !!captura.grabacion;
    anim.encadenado = seguir;
    anim.calmado = (seguir || reposo) && !captura.grabacion && !arrastrando && !anim.previa && ahora - anim.ultimaActividad > CALMA_MS
      && anim.efectos.every(e => e.tipo === 'vida' || e.tipo === 'chats' || e.fuente === 'ambiente' || e.fuente === 'sueno');
    return seguir;
  }

  function dibujarYa() {
    if (!graficoListo || estado.vista !== 'grafo') return;
    const ahora = performance.now();
    anim.ahora = ahora;
    escenaSucia = false;
    dibujar(ahora);
    if ((anim.efectos.length || anim.previa || anim.pulsoSucio) && dibujarPulso(ahora)) programarCuadro();
  }

  const FPS_CLIP = 30;
  const SEGUNDOS_CLIP = 30;
  const TIPOS_CLIP = ['video/mp4;codecs=avc1.640028', 'video/mp4;codecs=avc1.4d0028', 'video/mp4;codecs=avc1', 'video/mp4',
    'video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'];
  const CAJA_CEREBRO = [[-450, -300], [440, -300], [440, 370], [-450, 370]];

  function fallarCapturas() {
    if (!captura.pedidos.length) return;
    captura.pedidos.splice(0).forEach(p => p.fallar(new Error('El grafo no está a la vista')));
  }

  function cajaCerebro() {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const sumar = (x, y) => {
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    };
    nodosVisibles.forEach(n => sumar(n._sx, n._sy));
    if (cerebro) {
      const t = transformacion;
      CAJA_CEREBRO.forEach(([x, y]) => {
        const p = proyectar(x * cerebro.S, y * cerebro.S, 0);
        sumar(p.x * t.k + t.x, p.y * t.k + t.y);
      });
      (cerebro.rotulos || []).forEach(r => {
        if (!(r.a > 0.05) || !r.w) return;
        sumar(r.x - r.w / 2, r.y - 12);
        sumar(r.x + r.w / 2, r.y + 12);
      });
    }
    x0 = Math.max(0, x0);
    y0 = Math.max(0, y0);
    x1 = Math.min(ancho, x1);
    y1 = Math.min(alto, y1);
    return x1 - x0 > 40 && y1 - y0 > 40 ? [x0, y0, x1, y1] : null;
  }

  function regionCaptura(asp, extraAbajo, dentro) {
    const c = cajaCerebro();
    const cabe = Math.min(ancho, alto * asp);
    let w = cabe;
    let cx = ancho / 2;
    let cy = alto / 2;
    if (c) {
      const bw = c[2] - c[0];
      const bh = c[3] - c[1] + (c[3] - c[1]) * (extraAbajo || 0);
      const minimo = Math.max(bw + 16, (bh + 16) * asp);
      const justo = Math.max(bw * 1.12 + 32, (bh * 1.12 + 32) * asp);
      const lados = c[0] <= 1 && c[2] >= ancho - 1;
      const alturas = c[1] <= 1 && c[3] >= alto - 1;
      const desborda = (lados && alturas) || (lados && cabe / asp >= bh) || (alturas && cabe >= bw);
      w = dentro || desborda || minimo <= cabe ? Math.min(cabe, justo * 1.2) : justo;
      cx = (c[0] + c[2]) / 2;
      cy = c[1] + bh / 2;
    }
    const h = w / asp;
    if (w <= ancho) cx = Math.min(ancho - w / 2, Math.max(w / 2, cx));
    if (h <= alto) cy = Math.min(alto - h / 2, Math.max(h / 2, cy));
    const r = [cx - w / 2, cy - h / 2, w, h];
    r.caja = c;
    return r;
  }

  function fundirBordes(c, r) {
    const b = r.caja || [0, 0, ancho, alto];
    const ancho0 = gap => Math.min(140, Math.max(72, gap));
    const banda = (x, y, w, h, gx0, gy0, gx1, gy1) => {
      const g = c.createLinearGradient(gx0, gy0, gx1, gy1);
      g.addColorStop(0, colores.fondo);
      g.addColorStop(1, sinAlfa(colores.fondo));
      c.fillStyle = g;
      c.fillRect(x, y, w, h);
    };
    if (r[1] < 0) { const f = ancho0(b[1]); banda(r[0], 0, r[2], f, 0, 0, 0, f); }
    if (r[1] + r[3] > alto) { const f = ancho0(alto - b[3]); banda(r[0], alto - f, r[2], f, 0, alto, 0, alto - f); }
    if (r[0] < 0) { const f = ancho0(b[0]); banda(0, r[1], f, r[3], 0, 0, f, 0); }
    if (r[0] + r[2] > ancho) { const f = ancho0(ancho - b[2]); banda(ancho - f, r[1], f, r[3], ancho, 0, ancho - f, 0); }
  }

  function pintarElipse(c, cx, cy, rx, ry, paradas, r) {
    c.save();
    c.translate(cx, cy);
    c.scale(rx, ry);
    const g = c.createRadialGradient(0, 0, 0, 0, 0, 1);
    paradas.forEach(([o, color]) => g.addColorStop(o, color));
    c.fillStyle = g;
    c.fillRect((r[0] - cx) / rx, (r[1] - cy) / ry, r[2] / rx, r[3] / ry);
    c.restore();
  }

  function componer(c, W, H, r) {
    const s = W / r[2];
    c.save();
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.globalAlpha = 1;
    c.globalCompositeOperation = 'source-over';
    c.fillStyle = colores.fondo;
    c.fillRect(0, 0, W, H);
    c.setTransform(s, 0, 0, s, -r[0] * s, -r[1] * s);
    pintarElipse(c, ancho * 0.5, alto * 0.45, ancho * 0.8, alto * 0.7, [[0, colores.fondoCentro], [0.75, colores.fondo]], r);
    const capas = neuronasGL && !neuronasGL.perdido ? [lienzoNeuronas, lienzo, pulso] : [lienzo, pulso];
    capas.forEach(cv => { if (cv && cv.width > 1 && cv.height > 1) c.drawImage(cv, 0, 0, ancho, alto); });
    fundirBordes(c, r);
    if (!$('#vineta').hidden) pintarElipse(c, ancho * 0.5, alto * 0.47, ancho * 0.8, alto * 0.76, [[0.54, sinAlfa(colores.vineta)], [1, colores.vineta]], r);
    c.restore();
  }

  function sinAlfa(color) {
    const m = /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)/i.exec(color || '');
    if (m) return 'rgba(' + m[1] + ', ' + m[2] + ', ' + m[3] + ', 0)';
    if (/^#[0-9a-f]{6}$/i.test(color || '')) return 'rgba(' + hexARgb(color).map(v => Math.round(v * 255)).join(', ') + ', 0)';
    return 'rgba(0, 0, 0, 0)';
  }

  function textoConHalo(c, fuente, texto, x, y, color, grosor) {
    c.font = fuente;
    c.lineWidth = grosor;
    c.strokeText(texto, x, y);
    c.fillStyle = color;
    c.fillText(texto, x, y);
  }

  function ajustarTexto(c, texto, maximo) {
    if (c.measureText(texto).width <= maximo) return texto;
    let n = texto.length;
    while (n > 4 && c.measureText(texto.slice(0, n) + '…').width > maximo) n--;
    return texto.slice(0, n).trimEnd() + '…';
  }

  const textoPie = () => 'Neuromapa · ' + nodos.length.toLocaleString('es') + (nodos.length === 1 ? ' nota' : ' notas') + ' · ' + new Date().toLocaleDateString('es');

  function pintarPie(c, W, H) {
    const tam = Math.max(12, Math.round(Math.min(W, H) * 0.02));
    c.save();
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.textAlign = 'right';
    c.textBaseline = 'alphabetic';
    c.lineJoin = 'round';
    c.strokeStyle = colores.halo;
    textoConHalo(c, '600 ' + tam + LETRA, textoPie(), W - tam * 1.3, H - tam * 1.1, colores.texto2, Math.max(3, tam * 0.35));
    c.restore();
  }

  function pintarSubtitulos(c, W, H) {
    const u = Math.min(W, H) / 1080;
    c.save();
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.lineJoin = 'round';
    c.textBaseline = 'alphabetic';
    c.strokeStyle = colores.halo;
    const reloj = $('#repite');
    if (reloj && !reloj.hidden) {
      c.textAlign = 'center';
      const fecha = $('#repite-fecha').textContent;
      const cifras = $('#repite-cifras').textContent;
      const chica = '600 ' + Math.round(26 * u) + LETRA;
      c.font = chica;
      if (fecha) textoConHalo(c, chica, ajustarTexto(c, fecha, W - 80 * u), W / 2, 60 * u, colores.texto2, 8 * u);
      textoConHalo(c, '700 ' + Math.round(104 * u) + LETRA, $('#repite-hora').textContent, W / 2, 160 * u, colores.texto, 14 * u);
      c.font = chica;
      if (cifras) textoConHalo(c, chica, ajustarTexto(c, cifras, W - 80 * u), W / 2, 204 * u, colores.texto2, 8 * u);
    }
    const zocalo = $('#zocalo');
    if (presenta.cine && zocalo && zocalo.classList.contains('visible')) {
      const quien = $('#zocalo-quien');
      const texto = $('#zocalo-texto').textContent;
      const x = 56 * u;
      c.textAlign = 'left';
      if (quien.textContent) {
        const color = getComputedStyle(quien).getPropertyValue('--c').trim() || colores.acento;
        c.beginPath();
        c.arc(x + 9 * u, H - 128 * u, 9 * u, 0, Math.PI * 2);
        c.lineWidth = 6 * u;
        c.stroke();
        c.fillStyle = color;
        c.fill();
        c.font = '650 ' + Math.round(28 * u) + LETRA;
        textoConHalo(c, c.font, ajustarTexto(c, quien.textContent, W - x * 2 - 30 * u), x + 30 * u, H - 118 * u, colores.texto2, 8 * u);
      }
      if (texto) {
        c.font = '650 ' + Math.round(64 * u) + LETRA;
        textoConHalo(c, c.font, ajustarTexto(c, texto, W - x * 2), x, H - 50 * u, colores.texto, 14 * u);
      }
    }
    c.restore();
  }

  function componerCaptura(ahora) {
    const g = captura.grabacion;
    const toca = !!g && ahora - captura.ultimo >= 1000 / FPS_CLIP - 4;
    if (!captura.pedidos.length && !toca) return;
    if (neuronasGL && cerebro && captura.glEn !== captura.cuadro) pintarNeuronas(ahora);
    if (toca) {
      captura.ultimo = ahora;
      const meta = regionCaptura(g.w / g.h, presenta.cine ? 0.2 : 0);
      if (!g.region || g.ancho0 !== ancho || g.alto0 !== alto || g.cine !== presenta.cine) {
        g.region = meta;
        g.ancho0 = ancho;
        g.alto0 = alto;
        g.cine = presenta.cine;
      } else {
        for (let i = 0; i < 4; i++) g.region[i] += (meta[i] - g.region[i]) * 0.12;
        g.region.caja = meta.caja;
      }
      componer(g.ctx, g.w, g.h, g.region);
      pintarSubtitulos(g.ctx, g.w, g.h);
      pintarPie(g.ctx, g.w, g.h);
      if (!g.empezo) empezarGrabacion(g);
    }
    captura.pedidos.splice(0).forEach(p => {
      try { p.listo(p.armar()); } catch (e) { p.fallar(e); }
    });
  }

  function pedirCaptura(armar) {
    return new Promise((listo, fallar) => {
      if (!graficoListo) { fallar(new Error('El cerebro todavía no está listo')); return; }
      if (estado.vista !== 'grafo') cambiarVista('grafo', true);
      const p = { armar, listo, fallar };
      captura.pedidos.push(p);
      setTimeout(() => {
        const i = captura.pedidos.indexOf(p);
        if (i < 0) return;
        captura.pedidos.splice(i, 1);
        fallar(new Error('la página no dibujó a tiempo'));
      }, 4000);
      pedirDibujo();
    });
  }

  function nombreBajada(prefijo, ext) {
    const f = new Date();
    const d = n => String(n).padStart(2, '0');
    return prefijo + '-' + f.getFullYear() + '-' + d(f.getMonth() + 1) + '-' + d(f.getDate()) + '-' + d(f.getHours()) + d(f.getMinutes()) + '.' + ext;
  }

  function bajar(blob, nombre) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nombre;
    a.hidden = true;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  const lienzoABlob = cv => new Promise((listo, fallar) => cv.toBlob(b => b ? listo(b) : fallar(new Error('no se pudo armar el PNG')), 'image/png'));

  const TEXTO_NOMBRES = {
    foto: 'La foto va a mostrar los nombres reales de las notas, los grupos y los lóbulos. Si la vas a compartir, conviene el modo anónimo.',
    tarjeta: 'La tarjeta lleva una foto del cerebro con los nombres reales y las notas que más tocó Claude. Si la vas a compartir, conviene el modo anónimo.',
    video: 'El video va a mostrar los nombres reales de las notas, los grupos, los lóbulos y los subtítulos mientras grabás. Si lo vas a compartir, conviene el modo anónimo.'
  };

  function confirmarNombres(que) {
    if (presenta.anonimo) return Promise.resolve(true);
    const d = compartir.dialogo;
    const texto = TEXTO_NOMBRES[que];
    if (!d || typeof d.showModal !== 'function') return Promise.resolve(window.confirm(texto + '\n\n¿Bajar igual, con los nombres?'));
    return new Promise(listo => {
      compartir.texto.textContent = texto;
      d.returnValue = '';
      d.addEventListener('close', () => {
        if (d.returnValue === 'anonimo') { ponerAnonimo(true, true); listo(true); }
        else listo(d.returnValue === 'real');
      }, { once: true });
      d.showModal();
      $('#compartir-anonimo').focus();
    });
  }

  async function sacarFoto() {
    if (captura.grabacion) { aviso('Estoy grabando: la foto, cuando termine el video.'); return; }
    if (compartir.ocupado) { aviso('Esperá un momento: todavía estoy armando lo anterior.'); return; }
    if (!(await confirmarNombres('foto'))) return;
    compartir.ocupado = true;
    compartir.foto.disabled = true;
    try {
      const cv = await pedirCaptura(() => {
        const r = regionCaptura(ancho / alto, 0, true);
        const escala = Math.min(Math.max(1, dpr), 4096 / r[2]);
        const W = Math.round(r[2] * escala);
        const H = Math.round(r[3] * escala);
        const lienzoFoto = document.createElement('canvas');
        lienzoFoto.width = W;
        lienzoFoto.height = H;
        const c = lienzoFoto.getContext('2d');
        componer(c, W, H, r);
        pintarPie(c, W, H);
        return lienzoFoto;
      });
      bajar(await lienzoABlob(cv), nombreBajada('cerebro', 'png'));
      aviso('Bajé la foto del cerebro (' + cv.width + '×' + cv.height + ').');
    } catch (e) {
      aviso('No pude sacar la foto: ' + e.message + '.');
    } finally {
      compartir.ocupado = false;
      compartir.foto.disabled = false;
    }
  }

  function datosSinNotas() {
    const idGrupo = new Map();
    const grupos = [];
    const grupoNuevo = (id, g) => {
      if (idGrupo.has(id)) return idGrupo.get(id);
      const i = grupos.length;
      const x = { id: 'g' + (i + 1), nombre: 'Grupo ' + (i < 26 ? String.fromCharCode(65 + i) : i + 1), color: g && g.color, cantidad: 0 };
      if (g && typeof g.lobulo === 'string' && /^[a-z]{3,12}$/.test(g.lobulo)) x.lobulo = g.lobulo;
      if (g && Array.isArray(g.ancla) && g.ancla.every(v => typeof v === 'number' && isFinite(v))) x.ancla = g.ancla.slice(0, 4);
      grupos.push(x);
      idGrupo.set(id, x.id);
      return x.id;
    };
    (Array.isArray(DATOS.grupos) ? DATOS.grupos : []).forEach(g => { if (g && g.id != null) grupoNuevo(String(g.id), g); });
    const idNota = new Map();
    const nodosSin = [];
    const redondo = x => { const n = Math.max(0, Math.round(Number(x) || 0)); return n < 10 ? n : Number(n.toPrecision(2)); };
    const mezcladas = DATOS.nodos.slice();
    for (let i = mezcladas.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [mezcladas[i], mezcladas[j]] = [mezcladas[j], mezcladas[i]];
    }
    mezcladas.forEach(d => {
      if (!d || d.id == null || idNota.has(String(d.id))) return;
      const nuevo = 'n' + (nodosSin.length + 1);
      idNota.set(String(d.id), nuevo);
      const tipo = TIPOS[String(d.tipo)] ? String(d.tipo) : 'doc';
      const grupo = grupoNuevo(String(d.grupo || 'sin-grupo'), null);
      grupos.find(g => g.id === grupo).cantidad++;
      nodosSin.push({ id: nuevo, titulo: 'Nota ' + (nodosSin.length + 1), ruta: nuevo + '.md', slug: nuevo, grupo, tipo,
        lineas: redondo(d.lineas), bytes: redondo(d.bytes), descripcion: '', texto: '' });
    });
    const aristasSin = (Array.isArray(DATOS.aristas) ? DATOS.aristas : [])
      .filter(d => d && !d.equivale && CLASES[d.clase] && idNota.has(String(d.de)) && idNota.has(String(d.a)))
      .map(d => ({ de: idNota.get(String(d.de)), a: idNota.get(String(d.a)), clase: d.clase }));
    const salud = {};
    ['rotos', 'huerfanos', 'sinIndice', 'indiceRoto', 'ambiguos', 'handoffsAbiertos', 'respuestasSinAcuse', 'medico', 'anclas',
      'hechos', 'repiteClaude', 'memoriasParecidas'].forEach(k => { salud[k] = []; });
    return { generado: String(DATOS.generado || '').slice(0, 10), usuario: '', carpeta: '', proyectos: [], aliasRutas: [], lobulos: {}, handoffs: null,
      grupos, nodos: nodosSin, aristas: aristasSin, salud, podadas: [], entidades: {}, compartido: true };
  }

  async function bajarSinNotas() {
    if (!/^https?:$/.test(location.protocol)) { aviso('Para bajar la copia sin notas, abrí el mapa con /neuromapa:abrir.'); return; }
    if (compartir.ocupado) { aviso('Esperá un momento: todavía estoy armando lo anterior.'); return; }
    compartir.ocupado = true;
    compartir.sinNotas.disabled = true;
    try {
      const r = await fetch(location.pathname, { cache: 'no-store', credentials: 'same-origin' });
      if (!r.ok) throw new Error('el servidor contestó ' + r.status);
      const html = (await r.text()).replace(/^<script nonce="[\w-]+">/gm, '<script>');
      const partes = html.split(/<script>window\.CEREBRO = [^\n]*;<\/script>/);
      if (partes.length !== 2) throw new Error('no encontré los datos en la página');
      const datos = JSON.stringify(datosSinNotas()).replace(/</g, '\\u003c');
      const bloque = '<script>window.CEREBRO = ' + datos + ';<\/script>';
      bajar(new Blob([partes[0] + bloque + partes[1]], { type: 'text/html' }), nombreBajada('neuromapa-sin-notas', 'html'));
      aviso('Bajé una copia del mapa sin el texto ni los nombres de las notas. Esa sí se puede pasar.');
    } catch (e) {
      aviso('No pude armar la copia sin notas: ' + e.message + '.');
    } finally {
      compartir.ocupado = false;
      compartir.sinNotas.disabled = false;
    }
  }

  function pintarBotonGrabar() {
    const g = captura.grabacion;
    const b = compartir.grabar;
    if (!b) return;
    const s = g && g.empezo ? Math.floor((performance.now() - g.t0) / 1000) : 0;
    const reloj = '0:' + String(Math.min(SEGUNDOS_CLIP, s)).padStart(2, '0');
    b.classList.toggle('grabando', !!g);
    b.setAttribute('aria-pressed', String(!!g));
    b.innerHTML = g ? (g.empezo ? 'Parar · ' + reloj : 'Preparando…') : 'Grabar<span class="solo-ancho"> 30 s</span>';
    b.title = g ? 'Corta el video ahora y lo baja (G)' : 'Graba ' + SEGUNDOS_CLIP + ' s del cerebro y baja el video (G)';
    compartir.formato.disabled = !!g;
    compartir.marca.hidden = !g;
    compartir.marca.lastElementChild.textContent = 'Grabando ' + reloj + ' · G corta';
  }

  function pintarFormato() {
    const b = compartir.formato;
    b.textContent = compartir.vertical ? '4:5' : '16:9';
    b.setAttribute('aria-label', 'Formato del video: ' + (compartir.vertical ? 'vertical 4:5' : 'horizontal 16:9'));
    b.title = compartir.vertical ? 'Video vertical 1080×1350, para el celular. Clic para horizontal' : 'Video horizontal 1920×1080. Clic para vertical, para el celular';
  }

  async function alternarGrabacion() {
    if (captura.grabacion) { pararGrabacion(); return; }
    if (compartir.ocupado) { aviso('Esperá un momento: todavía estoy armando lo anterior.'); return; }
    const puede = typeof MediaRecorder === 'function' && typeof HTMLCanvasElement.prototype.captureStream === 'function';
    const tipo = puede ? TIPOS_CLIP.find(t => { try { return MediaRecorder.isTypeSupported(t); } catch (e) { return false; } }) : null;
    if (!tipo) { aviso('Este navegador no puede grabar video desde la página.'); return; }
    if (!(await confirmarNombres('video'))) return;
    if (!graficoListo || captura.grabacion) return;
    if (estado.vista !== 'grafo') cambiarVista('grafo', true);
    const liviano = anim.bajadas.length > 0;
    const vertical = compartir.vertical;
    const [w, h] = vertical ? (liviano ? [720, 900] : [1080, 1350]) : (liviano ? [1280, 720] : [1920, 1080]);
    const cv = document.createElement('canvas');
    cv.width = w;
    cv.height = h;
    const ctxClip = cv.getContext('2d', { alpha: false });
    let pista = null;
    let rec = null;
    try {
      pista = cv.captureStream(FPS_CLIP);
      rec = new MediaRecorder(pista, { mimeType: tipo, videoBitsPerSecond: liviano ? 6e6 : 12e6 });
    } catch (e) {
      if (pista) pista.getTracks().forEach(t => t.stop());
      aviso('No pude preparar la grabación: ' + e.message + '.');
      return;
    }
    const g = { cv, ctx: ctxClip, w, h, pista, rec, tipo, trozos: [], empezo: false, t0: 0, region: null, corte: 0, reloj: 0, cerrado: false, liviano };
    rec.ondataavailable = e => { if (e.data && e.data.size) g.trozos.push(e.data); };
    rec.onstop = () => terminarClip(g);
    captura.grabacion = g;
    captura.ultimo = -Infinity;
    pintarBotonGrabar();
    programarCuadro();
  }

  function empezarGrabacion(g) {
    g.empezo = true;
    try { g.rec.start(1000); } catch (e) {
      captura.grabacion = null;
      g.cerrado = true;
      g.pista.getTracks().forEach(t => t.stop());
      aviso('No pude empezar a grabar: ' + e.message + '.');
      pintarBotonGrabar();
      return;
    }
    g.t0 = performance.now();
    g.corte = setTimeout(pararGrabacion, SEGUNDOS_CLIP * 1000);
    g.reloj = setInterval(pintarBotonGrabar, 250);
    pintarBotonGrabar();
  }

  function pararGrabacion() {
    const g = captura.grabacion;
    if (!g) return;
    captura.grabacion = null;
    clearTimeout(g.corte);
    clearInterval(g.reloj);
    g.segundos = g.empezo ? (performance.now() - g.t0) / 1000 : 0;
    if (g.empezo && g.rec.state !== 'inactive') {
      try { g.rec.stop(); } catch (e) { terminarClip(g); }
    } else terminarClip(g);
    pintarBotonGrabar();
  }

  function terminarClip(g) {
    if (g.cerrado) return;
    g.cerrado = true;
    g.pista.getTracks().forEach(t => t.stop());
    if (!g.trozos.length) { if (g.empezo) aviso('El video salió vacío: probá de nuevo con la pestaña a la vista.'); return; }
    const tipo = g.tipo.split(';')[0];
    const ext = tipo === 'video/mp4' ? 'mp4' : 'webm';
    bajar(new Blob(g.trozos, { type: tipo }), nombreBajada('cerebro', ext));
    aviso('Bajé el video: ' + Math.round(g.segundos || 0) + ' s, ' + g.w + '×' + g.h + ', ' + ext.toUpperCase() + (g.liviano ? ' (más chico porque la compu venía lenta)' : '') + '.');
  }

  const miles = n => Math.round(Number(n) || 0).toLocaleString('es');
  const cifraCorta = n => n >= 10000 ? (n / 1000).toLocaleString('es', { maximumFractionDigits: 1 }) + ' k' : miles(n);
  const horaMinuto = t => new Date(t * 1000).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
  const lapso = s => {
    const min = Math.max(1, Math.round(s / 60));
    if (min < 60) return min + ' min';
    const h = Math.floor(min / 60);
    return h + ' h' + (min % 60 ? ' ' + (min % 60) + ' min' : '');
  };
  const plural = (n, uno, varios) => Number(n) === 1 ? uno : varios;

  function cuentasDelDia(dia) {
    const tot = dia.tot;
    const porHora = new Array(24).fill(0);
    let activos = 0;
    let pausa = null;
    let previo = null;
    dia.minutos.forEach(m => {
      const t = Number(m.t);
      const n = Number(m.n) || 0;
      if (!n || !Number.isFinite(t)) return;
      activos++;
      porHora[new Date(t * 1000).getHours()] += n;
      if (previo !== null && (!pausa || t - previo - 60 > pausa[1] - pausa[0])) pausa = [previo + 60, t];
      previo = t;
    });
    if (pausa && pausa[1] - pausa[0] < 20 * 60) pausa = null;
    const maximo = Math.max(...porHora);
    const pico = maximo > 0 ? porHora.indexOf(maximo) : -1;
    const lineas = Array.isArray(tot.lineas) ? tot.lineas.map(x => Number(x) || 0) : [0, 0];
    const chats = Array.isArray(tot.chats) ? tot.chats.length : 0;
    const agentes = Number(tot.agentes) || 0;
    const commits = Number(tot.commit) || 0;
    const cifras = [
      [miles(tot.usuario), plural(tot.usuario, 'mensaje tuyo', 'mensajes tuyos')],
      [miles(commits), plural(commits, 'commit', 'commits')],
      [miles(agentes), plural(agentes, 'agente', 'agentes')],
      lineas[0] || lineas[1] ? ['+' + cifraCorta(lineas[0]), 'líneas · −' + cifraCorta(lineas[1]) + ' borradas'] : [miles(dia.editadas), plural(dia.editadas, 'nota editada', 'notas editadas')],
      [pico >= 0 ? String(pico).padStart(2, '0') + ' h' : '—', 'hora pico'],
      pausa ? [lapso(pausa[1] - pausa[0]), 'durmió, de ' + horaMinuto(pausa[0]) + ' a ' + horaMinuto(pausa[1])] : [miles(dia.tocadas), plural(dia.tocadas, 'nota tocada', 'notas tocadas')]
    ];
    const partes = [(dia.titulo === 'Hoy' ? 'Hoy' : 'En las últimas 24 h') + ' Claude trabajó ' + lapso(activos * 60) + ' en ' + chats + ' ' + plural(chats, 'chat', 'chats')];
    if (agentes) partes.push('lanzó ' + miles(agentes) + ' ' + plural(agentes, 'agente', 'agentes'));
    if (commits) partes.push('hizo ' + miles(commits) + ' ' + plural(commits, 'commit', 'commits'));
    if (pausa) partes.push('durmió ' + lapso(pausa[1] - pausa[0]));
    const frase = (partes.length > 1 ? partes.slice(0, -1).join(', ') + ' y ' + partes[partes.length - 1] : partes[0]) + '.';
    const porLobulo = new Map();
    dia.notas.forEach(([n, k]) => {
      const i = lobuloDe(n);
      if (i >= 0) porLobulo.set(i, (porLobulo.get(i) || 0) + k);
    });
    const mejor = [...porLobulo].sort((a, b) => b[1] - a[1])[0];
    const lobulo = mejor && cerebro ? cerebro.lobulos[mejor[0]] : null;
    return { porHora, pico, cifras, frase, lobulo };
  }

  function armarTarjeta(dia) {
    const W = 1080;
    const H = 1350;
    const M = 64;
    const cuentas = cuentasDelDia(dia);
    const tarjeta = document.createElement('canvas');
    tarjeta.width = W;
    tarjeta.height = H;
    const c = tarjeta.getContext('2d');
    c.fillStyle = colores.fondo;
    c.fillRect(0, 0, W, H);
    c.textBaseline = 'alphabetic';
    c.lineJoin = 'round';
    c.textAlign = 'left';
    c.fillStyle = colores.texto3;
    c.font = '650 22' + LETRA;
    c.fillText((dia.titulo === 'Hoy' ? 'MI DÍA CON CLAUDE' : 'LAS ÚLTIMAS 24 H CON CLAUDE'), M, 74);
    const fecha = new Date(((dia.hasta || Date.now() / 1000)) * 1000).toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' });
    c.fillStyle = colores.texto;
    c.font = '700 56' + LETRA;
    c.fillText(ajustarTexto(c, fecha.charAt(0).toUpperCase() + fecha.slice(1), W - M * 2), M, 136);
    const FOTO_Y = 150;
    const FOTO_H = 570;
    const FOTO_W = Math.min(W, Math.round(FOTO_H * Math.max(1, ancho / alto)));
    const FOTO_X = Math.round((W - FOTO_W) / 2);
    const foto = document.createElement('canvas');
    foto.width = FOTO_W;
    foto.height = FOTO_H;
    componer(foto.getContext('2d'), FOTO_W, FOTO_H, regionCaptura(FOTO_W / FOTO_H, 0, true));
    c.drawImage(foto, FOTO_X, FOTO_Y);
    const transparente = sinAlfa(colores.fondo);
    const fundido = (x0, y0, x1, y1) => {
      const g = c.createLinearGradient(x0, y0, x1, y1);
      g.addColorStop(0, colores.fondo);
      g.addColorStop(1, transparente);
      c.fillStyle = g;
      c.fillRect(Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0) || FOTO_W, Math.abs(y1 - y0) || FOTO_H);
    };
    fundido(FOTO_X, FOTO_Y, FOTO_X, FOTO_Y + 48);
    fundido(FOTO_X, FOTO_Y + FOTO_H, FOTO_X, FOTO_Y + FOTO_H - 90);
    if (FOTO_W < W) {
      fundido(FOTO_X, FOTO_Y, FOTO_X + 110, FOTO_Y);
      fundido(FOTO_X + FOTO_W, FOTO_Y, FOTO_X + FOTO_W - 110, FOTO_Y);
    }
    c.fillStyle = colores.texto2;
    c.font = '500 30' + LETRA;
    let y = FOTO_Y + FOTO_H + 44;
    partirLineas(c, cuentas.frase, W - M * 2).slice(0, 2).forEach(l => { c.fillText(l, M, y); y += 42; });
    const celda = (W - M * 2) / 3;
    const filaY = [y + 56, y + 176];
    cuentas.cifras.forEach(([numero, rotulo], i) => {
      const x = M + (i % 3) * celda;
      const fy = filaY[Math.floor(i / 3)];
      c.fillStyle = i === 4 ? colores.acento : colores.texto;
      c.font = '750 68' + LETRA;
      let tam = 68;
      while (tam > 30 && c.measureText(numero).width > celda - 16) { tam -= 4; c.font = '750 ' + tam + LETRA; }
      c.fillText(numero, x, fy);
      c.fillStyle = colores.texto3;
      c.font = '500 23' + LETRA;
      c.fillText(ajustarTexto(c, rotulo, celda - 16), x, fy + 34);
    });
    const barrasY = filaY[1] + 74;
    const barrasH = 60;
    const paso = (W - M * 2) / 24;
    const maximo = Math.max(1, ...cuentas.porHora);
    cuentas.porHora.forEach((n, i) => {
      const bh = n ? Math.max(3, barrasH * n / maximo) : 2;
      c.globalAlpha = i === cuentas.pico ? 1 : n ? 0.5 : 0.25;
      c.fillStyle = n ? colores.acento : colores.texto3;
      c.beginPath();
      if (c.roundRect) c.roundRect(M + i * paso + 3, barrasY + barrasH - bh, paso - 6, bh, 3);
      else c.rect(M + i * paso + 3, barrasY + barrasH - bh, paso - 6, bh);
      c.fill();
    });
    c.globalAlpha = 1;
    c.fillStyle = colores.texto3;
    c.font = '500 19' + LETRA;
    [0, 6, 12, 18, 23].forEach(h => {
      c.textAlign = h === 0 ? 'left' : h === 23 ? 'right' : 'center';
      const x = h === 0 ? M + 3 : h === 23 ? W - M - 3 : M + h * paso + paso / 2;
      c.fillText(h + ' h', x, barrasY + barrasH + 26);
    });
    c.textAlign = 'left';
    let pieY = barrasY + barrasH + 76;
    pieY = Math.min(pieY, H - 116);
    if (cuentas.lobulo) {
      const l = cuentas.lobulo;
      const g = grupoPorId.get(l.grupo);
      c.fillStyle = g ? g.color : colores.acento;
      c.beginPath();
      c.arc(M + 9, pieY - 9, 9, 0, Math.PI * 2);
      c.fill();
      c.fillStyle = colores.texto;
      c.font = '600 28' + LETRA;
      c.fillText(ajustarTexto(c, 'Donde más pensó: ' + publico('lobulo', l, l.nombre), W - M * 2 - 30), M + 30, pieY);
      pieY += 40;
    }
    if (!presenta.anonimo && dia.notas.length && pieY < H - 60) {
      const titulos = dia.notas.slice(0, 3).map(([n]) => tituloCorto(n, 30));
      c.fillStyle = colores.texto2;
      c.font = '500 23' + LETRA;
      c.fillText(ajustarTexto(c, 'Lo que más tocó: ' + titulos.join(' · '), W - M * 2), M, pieY);
    }
    c.textAlign = 'right';
    c.fillStyle = colores.texto3;
    c.font = '600 21' + LETRA;
    c.fillText(textoPie(), W - M, H - 36);
    return tarjeta;
  }

