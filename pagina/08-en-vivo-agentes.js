    function ponerCartelesAgentes(ahora, fCartel) {
      const lista = cartelesAg;
      if (!lista.length) return;
      lista.sort((a, b) => b.tAccion - a.tAccion);
      const muchos = lista.length > 6;
      for (let i = 0; i < lista.length; i++) {
        const s = lista[i];
        if (s.v.sx < 0 || s.v.sx > ancho || s.v.sy < 0 || s.v.sy > alto) continue;
        const nombre = nombreSub(s.chat, s);
        let texto;
        if (muchos && i >= 3) {
          const corto = s.chat.subs.size <= 1 ? '' : nombre.indexOf(' #') > 0 ? '#' + s.num : recortar(nombre, 10);
          const accion = s.actual ? recortar(s.actual, corto.length <= 3 ? 26 : 22) : '';
          texto = corto && accion ? corto + ' · ' + accion : corto || accion || recortar(nombre, 12);
        } else texto = nombre + (s.actual ? ' · ' + s.actual : '');
        const quieto = ahora - s.tAccion > 20000;
        cartelAgente(s, texto, s.v.alfa * 0.95 * fCartel * (quieto ? 0.45 : 1));
      }
      lista.length = 0;
    }
    let fCartelAg = 1;
    const cerrarCarteles = ahora => ponerCartelesAgentes(ahora, fCartelAg);

    const pilas = new Map();
    function etiquetaAl(pos, radio, piso, texto, color, alfa) {
      const y = pos.ly - radio - 16 + 24 * piso;
      const w = anchoEtiqueta(texto);
      const izquierda = pos.lx + radio + 18 + w > ancho - 4 && pos.lx - radio - 18 - w >= 4;
      etiqueta(izquierda ? pos.lx - radio - 18 : pos.lx + radio + 18, y, texto, color, alfa, izquierda);
    }
    function cometaChat(c, pos, alfa, ocupado, ahora, eL, fCartel) {
      pctx.strokeStyle = c.color;
      pctx.lineCap = 'round';
      pctx.beginPath();
      if (pos.q < 1) {
        trazarCurvaHasta(pctx, pos.x0, pos.y0, pos.qx, pos.qy, pos.x1, pos.y1, pos.e);
      } else {
        pctx.arc(pos.cx, pos.cy, pos.r, pos.ang - 1.3, pos.ang);
      }
      pctx.globalAlpha = 0.2 * alfa;
      pctx.lineWidth = 9;
      pctx.stroke();
      pctx.globalAlpha = 0.6 * alfa;
      pctx.lineWidth = 3;
      pctx.stroke();
      pctx.lineCap = 'butt';
      brillo(pos.x, pos.y, 26, c.color, alfa);
      pctx.globalAlpha = alfa;
      pctx.fillStyle = c.color;
      pctx.beginPath();
      pctx.arc(pos.x, pos.y, 6.5, 0, TAU);
      pctx.fill();
      pctx.fillStyle = '#ffffff';
      pctx.beginPath();
      pctx.arc(pos.x, pos.y, 2.6, 0, TAU);
      pctx.fill();
      if (ocupado) {
        const rot = ahora / 150;
        pctx.strokeStyle = c.color;
        pctx.lineWidth = 2.4;
        pctx.beginPath();
        pctx.arc(pos.x, pos.y, 12, rot, rot + 4.2);
        pctx.stroke();
      } else if (c.estado === 'esperando') {
        const k = (ahora % 1100) / 1100;
        pctx.globalAlpha = alfa * (1 - k);
        pctx.strokeStyle = '#eab308';
        pctx.lineWidth = 3;
        pctx.beginPath();
        pctx.arc(pos.x, pos.y, 9 + 18 * k, 0, TAU);
        pctx.stroke();
      } else if (c.estado === 'compactando') {
        for (let i = 0; i < 3; i++) {
          const k = ((ahora / 900) + i / 3) % 1;
          pctx.globalAlpha = alfa * k;
          pctx.strokeStyle = '#a78bfa';
          pctx.lineWidth = 2;
          pctx.beginPath();
          pctx.arc(pos.x, pos.y, 6 + 24 * (1 - k), 0, TAU);
          pctx.stroke();
        }
      }
      const extra = c.estado === 'trabajando' ? (c.actual ? ' · ' + c.actual : '') : ' · ' + ESTADO_TXT[c.estado];
      const rc = (pos.lr + 16 * eL) * 0.7;
      const ic = pilas.get(c.hacia) || 0;
      pilas.set(c.hacia, ic + 1);
      etiquetaAl(pos, rc, ic, nombreVisible(c) + extra, c.color, alfa * fCartel);
    }
    function vencerChats(ahora) {
      let cambio = false;
      for (const c of [...chats.values()]) {
        if (c.estado === 'listo' || c.estado === 'cerrado') {
          if (ahora - c.tFin > (c.estado === 'cerrado' ? 3000 : 45000) + 4000) {
            c.subs.forEach(soltarTerritorio);
            chats.delete(c.id);
            cambio = true;
          }
        } else if (ahora - c.tUlt > CHAT_QUIETO) {
          c.estado = 'listo';
          c.tFin = ahora;
          cambio = true;
        }
        for (const [aid, s] of [...c.subs]) {
          if (ahora - s.tUlt > 120000) {
            c.subs.delete(aid);
            despedir(c, s);
            cambio = true;
          }
        }
      }
      return cambio;
    }
    DIBUJO_EFECTO.chats = (e, p, eL) => {
      const ahora = performance.now();
      const dt = Math.min(100, ahora - (e.tPrev || ahora));
      e.tPrev = ahora;
      const borrados = vencerChats(ahora);
      pilas.clear();
      const paseo = paseoPosible();
      if (paseo) prepararPantalla();
      cartelesAg.length = 0;
      let activos = 0;
      let olaDe = null;
      const fCometa = fundidoIntro(INTRO.clima + 600, 800, ahora);
      const fCartel = fundidoIntro(INTRO.nombres, 600, ahora);
      for (const c of [...chats.values()]) {
        let alfa = 1;
        if (c.estado === 'listo' || c.estado === 'cerrado') {
          const pasado = ahora - c.tFin;
          const vida = c.estado === 'cerrado' ? 3000 : 45000;
          alfa = pasado > vida ? 0.6 * (1 - (pasado - vida) / 4000) : 0.6;
        }
        const ocupado = c.estado === 'trabajando' && c.enCurso.size > 0;
        c.giro += dt * (ocupado ? 0.0024 : c.estado === 'trabajando' ? 0.001 : 0.0002);
        alfa *= fCometa;
        const pos = posicion(c, 16 * eL, ahora);
        if (c.salen.length) {
          if (paseo) dibujarSalen(c, ahora, eL, fCometa, pos);
          else c.salen.length = 0;
        }
        if (alfa <= 0.004) continue;
        if (c.camino && c.camino.length) {
          const cam = c.camino.filter(x => ahora - x.t < 90000 && x.n._visible && x.n._sx !== undefined);
          pctx.lineCap = 'round';
          for (let i = 1; i < cam.length; i++) {
            const a = cam[i - 1].n;
            const b = cam[i].n;
            const al = alfa * (1 - (ahora - cam[i].t) / 90000) * (0.35 + 0.65 * i / (cam.length - 1));
            if (al <= 0.01) continue;
            const [qx, qy] = controlCurva(a, b);
            const largo = limitar(1 - (Math.hypot(b._sx - a._sx, b._sy - a._sy) - 160) / 480);
            pctx.beginPath();
            pctx.moveTo(a._sx, a._sy);
            pctx.quadraticCurveTo(qx, qy, b._sx, b._sy);
            pctx.strokeStyle = c.color;
            pctx.globalAlpha = al * 0.22 * (0.5 + 0.5 * largo);
            pctx.lineWidth = 10;
            pctx.stroke();
            pctx.globalAlpha = al * 0.9 * (0.5 + 0.5 * largo);
            pctx.lineWidth = 2.6;
            pctx.stroke();
            const nuevo = i === cam.length - 1;
            const ap = al * (0.25 + 0.75 * largo);
            pctx.fillStyle = anim.oscuro ? aclarar(c.color, 0.45) : c.color;
            for (let j = 0; j < 6; j++) {
              const s = (ahora / 1500 + j / 6) % 1;
              const aj = ap * Math.min(1, s / 0.12, (1 - s) / 0.12);
              if (aj <= 0.02) continue;
              const x = puntoCurva(a._sx, qx, b._sx, s);
              const y = puntoCurva(a._sy, qy, b._sy, s);
              if (nuevo) {
                cabeza(x, y, c.color, aj, 0.85, Math.max(14, 18 * eL), Math.max(2.4, 3 * eL), colores.texto);
                continue;
              }
              pctx.globalAlpha = aj * 0.9;
              pctx.beginPath();
              pctx.arc(x, y, Math.max(1.3, 1.6 * eL), 0, TAU);
              pctx.fill();
            }
          }
          cam.forEach(x => {
            const al = alfa * (1 - (ahora - x.t) / 90000) * 0.8;
            if (al <= 0.01) return;
            pctx.globalAlpha = al;
            pctx.strokeStyle = c.color;
            pctx.lineWidth = 1.6;
            pctx.beginPath();
            pctx.arc(x.n._sx, x.n._sy, x.n._sr + 5, 0, TAU);
            pctx.stroke();
          });
        }
        if (pos) cometaChat(c, pos, alfa, ocupado, ahora, eL, fCartel);
        for (const s of [...c.subs.values()]) {
          s.giro += dt * 0.003;
          if (paseo) {
            const v = visualDe(c, s, ahora);
            avanzarVisual(s, v, ahora, eL);
            v.alfa = alfa * v.luz;
            const fl = ahora - s.tAccion;
            if (pos && fl < 1400) {
              const [qx, qy] = curvaEntre(pos.x, pos.y, v.sx, v.sy);
              pctx.globalAlpha = 0.4 * alfa * (1 - fl / 1400);
              pctx.strokeStyle = s.color;
              pctx.lineWidth = 1.2;
              pctx.setLineDash([2, 5]);
              pctx.beginPath();
              pctx.moveTo(pos.x, pos.y);
              pctx.quadraticCurveTo(qx, qy, v.sx, v.sy);
              pctx.stroke();
              pctx.setLineDash([]);
            }
            dibujarAgente(s, v, v.alfa, eL, ahora);
            cartelesAg.push(s);
            if (c.estado === 'trabajando' && fl < 15000) {
              activos++;
              if (Math.random() * activos < 1) olaDe = s;
            }
            continue;
          }
          const sp = posicion(s, 9 * eL, ahora);
          if (!sp) continue;
          if (pos) {
            pctx.globalAlpha = 0.55 * alfa;
            pctx.strokeStyle = s.color;
            pctx.lineWidth = 1.4;
            pctx.setLineDash([2, 4]);
            pctx.beginPath();
            pctx.moveTo(pos.x, pos.y);
            pctx.lineTo(sp.x, sp.y);
            pctx.stroke();
            pctx.setLineDash([]);
          }
          brillo(sp.x, sp.y, 16, s.color, alfa);
          pctx.globalAlpha = alfa;
          pctx.fillStyle = s.color;
          pctx.beginPath();
          pctx.arc(sp.x, sp.y, 4.8, 0, TAU);
          pctx.fill();
          const rot = ahora / 120;
          pctx.strokeStyle = s.color;
          pctx.lineWidth = 1.8;
          pctx.beginPath();
          pctx.arc(sp.x, sp.y, 8.5, rot, rot + 3.6);
          pctx.stroke();
          const rs = (sp.lr + 16 * eL) * 0.7;
          const is = pilas.get(s.hacia) || 0;
          pilas.set(s.hacia, is + 1);
          etiquetaAl(sp, rs, is, nombreSub(c, s) + (s.actual ? ' · ' + s.actual : ''), s.color, alfa * 0.95 * fCartel);
        }
      }
      if (paseo && cartelesAg.length) {
        fCartelAg = fCartel;
        vivo.alCerrar = cerrarCarteles;
      }
      const focos = [];
      if (cerebro) {
        const r2 = (300 * cerebro.S) ** 2;
        for (const c of chats.values()) {
          if (paseo) for (const s of c.salen) focos.push(focoAgente(s, s.v, ahora, 1 - s.v.e * 0.6));
          if (c.estado !== 'trabajando') continue;
          if (c.hacia) focos.push({ x: c.hacia.x, y: c.hacia.y, z: c.hacia.z || 0, color: c.color, r2, cada: c.enCurso.size ? 40 : 110, fuerza: c.enCurso.size ? 0.32 : 0.18 });
          for (const s of c.subs.values()) {
            if (paseo && s.v) focos.push(focoAgente(s, s.v, ahora, 1));
            else if (s.hacia) focos.push({ x: s.hacia.x, y: s.hacia.y, z: s.hacia.z || 0, color: s.color, r2, cada: 55, fuerza: 0.22 });
          }
        }
      }
      vida.focos = focos;
      vida.extra = paseo ? Math.min(1, Math.max(0, activos - 1) / 7) : 0;
      if (!e.tOla) e.tOla = ahora + 4000;
      if (paseo && activos >= 3 && neuronasGL && olaDe && ahora > e.tOla) {
        e.tOla = ahora + 9000 + Math.random() * 6000;
        const o = actividad.onda;
        if (!o || ahora - o.t0 > o.dur) ondaGlobal(olaDe.color, 0.22 + 0.18 * vida.extra, [olaDe.v.x, olaDe.v.y, olaDe.v.z], 2600, true);
      }
      if (borrados) pintarChats();
      if (!chats.size) { e.dur = 1e-6; vida.focos = []; vida.extra = 0; }
    };

    const RIO_VENTANA = 600;
    const RIO_CARRILES = 5;
    const RIO_ALTO = 20;
    const rio = { eventos: [], caja: $('#rio'), lienzo: $('#rio-lienzo'), cuentas: [], sobre: null };
    function anotarRio(ev, pintar) {
      if (!ev || ev.repite || !ev.s || (ev.e || 'post') === 'pre' || !(Number(ev.t) > 0)) return;
      rio.eventos.push(ev);
      const corte = Date.now() / 1000 - RIO_VENTANA - 60;
      while (rio.eventos.length && (rio.eventos[0].t < corte || rio.eventos.length > 2000)) rio.eventos.shift();
      if (pintar) pintarRio();
    }
    function textoCuenta(ev) {
      const c = chats.get(ev.s);
      const sub = c && ev.a ? c.subs.get(ev.a) : null;
      const quien = (c ? nombreVisible(c) : publico('chat', ev.s, 'chat'))
        + (ev.a ? ' · ' + (sub ? nombreSub(c, sub) : formasTipo(ev.at || 'agente')[0]) : '');
      return hace(ev.t) + ' · ' + quien + ' · ' + nombreEvento(ev) + ' ' + textoFila(ev);
    }
    function lugarRio() {
      const centro = rio.caja.parentElement.getBoundingClientRect();
      const caja = el => el && !el.hidden && el.getClientRects().length ? el.getBoundingClientRect() : null;
      const ahora = caja($('#en-vivo'));
      const electro = caja(eeg.el);
      const nota = panel.classList.contains('abierto') ? caja(panel) : null;
      const izq = ahora && ahora.width ? ahora.right - centro.left + 8 : 12;
      let der = electro && electro.width ? centro.right - electro.left + 8 : 12;
      if (nota && nota.width && nota.left < centro.right) der = Math.max(der, centro.right - nota.left + 12);
      return centro.width - izq - der >= 260 ? [Math.round(izq), Math.round(der)] : null;
    }
    function carrilesRio(eventos, ahora) {
      const t0 = ahora - RIO_VENTANA;
      const vistos = eventos.filter(ev => ev.t >= t0);
      const ultimo = new Map();
      vistos.forEach(ev => ultimo.set(ev.s, ev.t));
      let carriles = [...ultimo.keys()];
      if (carriles.length > RIO_CARRILES) {
        const recientes = new Set(carriles.slice().sort((a, b) => ultimo.get(b) - ultimo.get(a)).slice(0, RIO_CARRILES));
        carriles = carriles.filter(s => recientes.has(s));
      }
      return { t0, vistos, carriles };
    }
    function pintarRio() {
      const ahora = Date.now() / 1000;
      const { t0, vistos, carriles } = carrilesRio(rio.eventos, ahora);
      rio.cuentas = [];
      const lugar = carriles.length && estado.vista === 'grafo' ? lugarRio() : null;
      rio.caja.hidden = !lugar;
      if (!lugar) return;
      rio.caja.style.left = lugar[0] + 'px';
      rio.caja.style.right = lugar[1] + 'px';
      const cv = rio.lienzo;
      const w = cv.clientWidth;
      if (!w) return;
      const h = carriles.length * RIO_ALTO + 12;
      cv.style.height = h + 'px';
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
        cv.width = Math.round(w * dpr);
        cv.height = Math.round(h * dpr);
      }
      const g = cv.getContext('2d');
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, w, h);
      const x = t => 3 + (t - t0) / RIO_VENTANA * (w - 6);
      const estilo = getComputedStyle(document.documentElement);
      const tenue = estilo.getPropertyValue('--texto-3').trim() || '#888';
      const fuerte = estilo.getPropertyValue('--texto').trim() || '#eee';
      const medio = estilo.getPropertyValue('--texto-2').trim() || '#555';
      const letra =getComputedStyle(document.body).fontFamily || 'sans-serif';
      const nombres = new Map(carriles.map(s => {
        const c = chats.get(s);
        const conCarpeta = c ? null : vistos.find(ev => ev.s === s && ev.c);
        return [s, c ? nombreVisible(c) : publico('chat', s, conCarpeta ? nombreChat(conCarpeta.c) : 'chat')];
      }));
      carriles.forEach(s => {
        if (!chats.has(s) && [...nombres].some(([o, n]) => o !== s && n === nombres.get(s))) nombres.set(s, nombres.get(s) + ' ' + s.slice(0, 4));
      });
      g.lineCap = 'round';
      carriles.forEach((s, i) => {
        const y = i * RIO_ALTO + 12;
        const c = chats.get(s);
        const evs = vistos.filter(ev => ev.s === s);
        const antes = rio.eventos.some(ev => ev.s === s && ev.t < t0);
        const sigue = !!c && (c.estado === 'trabajando' || c.estado === 'esperando' || c.estado === 'compactando');
        const desde = antes ? t0 : evs[0].t;
        const hasta = sigue ? ahora : evs[evs.length - 1].t;
        const color = c ? c.color : colorChat(s);
        g.globalAlpha = 0.5;
        g.strokeStyle = color;
        g.lineWidth = 2;
        g.beginPath();
        g.moveTo(x(desde), y);
        g.lineTo(Math.max(x(desde) + 1, x(hasta)), y);
        g.stroke();
        const nombre = nombres.get(s);
        g.font = '600 9px ' + letra;
        g.textBaseline = 'alphabetic';
        g.textAlign = 'left';
        g.globalAlpha = 0.9;
        g.fillStyle = anim.oscuro ? color : medio;
        g.fillText(nombre, Math.max(2, Math.min(x(desde), w - g.measureText(nombre).width - 2)), y - 4);
        const agentes = new Map();
        evs.forEach(ev => {
          if (!ev.a) return;
          const ag = agentes.get(ev.a) || { t0: ev.t, t1: ev.t, fin: false };
          ag.t1 = ev.t;
          if (ev.e === 'sub-fin') ag.fin = true;
          agentes.set(ev.a, ag);
        });
        agentes.forEach((ag, aid) => {
          const xa = x(ag.t0);
          const xb = Math.max(xa + 2, x(ag.fin || !sigue ? ag.t1 : ahora));
          g.globalAlpha = 0.6;
          g.strokeStyle = colorAgente(aid);
          g.lineWidth = 1;
          g.beginPath();
          g.moveTo(xa - 5, y);
          g.quadraticCurveTo(xa - 1, y, xa, y + 5);
          g.lineTo(xb, y + 5);
          if (ag.fin) g.quadraticCurveTo(xb + 1, y, xb + 5, y);
          g.stroke();
        });
        evs.forEach((ev, j) => {
          const e = ev.e || 'post';
          const cx = x(ev.t);
          const cy = ev.a ? y + 5 : y;
          g.globalAlpha = 1;
          if (e === 'usuario') {
            g.strokeStyle = fuerte;
            g.lineWidth = 1.5;
            g.beginPath();
            g.moveTo(cx, y - 5);
            g.lineTo(cx, y + 5);
            g.stroke();
          } else if (e === 'espera') {
            const sig = evs.slice(j + 1).find(o => !o.a);
            const xb = sig ? x(sig.t) : c && c.estado === 'esperando' ? x(ahora) : cx + 2;
            g.strokeStyle = '#eab308';
            g.lineWidth = 3;
            g.beginPath();
            g.moveTo(cx, y);
            g.lineTo(Math.max(cx + 2, xb), y);
            g.stroke();
          } else if (e === 'fin') {
            g.strokeStyle = colorEvento(ev);
            g.lineWidth = 1.2;
            g.beginPath();
            g.arc(cx, y, 2.6, 0, TAU);
            g.stroke();
          } else if (e === 'post' || e === 'falla' || e === 'aviso' || e === 'choque' || e === 'recuerda' || e === 'guarda') {
            g.fillStyle = colorEvento(ev);
            g.beginPath();
            g.arc(cx, cy, ev.a ? 1.7 : 2.4, 0, TAU);
            g.fill();
          } else return;
          rio.cuentas.push({ x: cx, y: cy, ev });
        });
      });
      g.globalAlpha = 1;
      g.fillStyle = tenue;
      g.font = '10px ' + letra;
      g.textBaseline = 'bottom';
      g.textAlign = 'left';
      g.fillText('hace 10 min', 2, h);
      g.textAlign = 'right';
      g.fillText('ahora', w - 2, h);
    }
    rio.lienzo.addEventListener('mousemove', e => {
      const r = rio.lienzo.getBoundingClientRect();
      const px = e.clientX - r.left;
      const py = e.clientY - r.top;
      let mejor = null;
      let dist = 49;
      for (const b of rio.cuentas) {
        const d = (b.x - px) * (b.x - px) + (b.y - py) * (b.y - py);
        if (d < dist) { dist = d; mejor = b; }
      }
      rio.sobre = mejor;
      rio.lienzo.title = mejor ? textoCuenta(mejor.ev) : '';
      rio.lienzo.style.cursor = mejor && notaDe(mejor.ev) ? 'pointer' : '';
    });
    rio.lienzo.addEventListener('mouseleave', () => { rio.sobre = null; });
    rio.lienzo.addEventListener('click', () => {
      const n = rio.sobre && notaDe(rio.sobre.ev);
      if (n) irA(n.id, true);
    });
    setInterval(() => { if (!document.hidden && rio.eventos.length) pintarRio(); }, 1000);

    const TOPE_AGENTES = 5;
    function pintarChats() {
      const lista = [...chats.values()].filter(c => c.estado !== 'cerrado');
      cajaChats.hidden = !lista.length;
      const caja = document.createElement('div');
      lista.forEach(c => {
        const d = document.createElement('div');
        d.className = 'chat';
        const i = document.createElement('i');
        i.className = 'agente';
        i.style.setProperty('--c', c.color);
        const b = document.createElement('b');
        b.textContent = nombreVisible(c);
        const s = document.createElement('span');
        s.className = 'estado-' + c.estado;
        const actual = c.estado === 'trabajando' && c.actual ? c.actual : '';
        s.textContent = ESTADO_TXT[c.estado] + (c.subs.size ? ' · ' + cuentaAgentes(c) + (actual ? ' · ' + actual : '') : actual ? ': ' + actual : '');
        d.append(i, b, s);
        caja.appendChild(d);
        const m = memorias.get(c.id);
        const plural = n => n + (n === 1 ? ' nota' : ' notas');
        if (m && m.episodio.size) {
          const f = document.createElement('div');
          f.className = 'chat sub';
          f.appendChild(botonCabeza(m, 'en la cabeza: ' + plural(m.episodio.size), 'en-cabeza', 'cabeza:' + c.id));
          caja.appendChild(f);
          if (m.ver) caja.appendChild(listaCabeza(m.episodio, false, m.color, 'lista:' + c.id));
        } else if (m && m.olvidando) {
          const f = document.createElement('div');
          f.className = 'chat sub';
          const o = document.createElement('span');
          o.className = 'olvidando';
          o.textContent = 'repasa y suelta ' + plural(m.olvidando.size);
          f.appendChild(o);
          caja.appendChild(f);
        }
        const subs = [...c.subs.values()].sort((x, y) => y.tUlt - x.tUlt);
        if (subs.length > TOPE_AGENTES) {
          const f = document.createElement('div');
          f.className = 'chat sub';
          const sb = document.createElement('button');
          sb.type = 'button';
          sb.className = 'mas-agentes';
          sb.dataset.foco = 'mas:' + c.id;
          sb.textContent = c.verTodos ? '↳ mostrar menos' : '↳ y ' + (subs.length - TOPE_AGENTES + 1) + ' agentes más';
          sb.addEventListener('click', () => { c.verTodos = !c.verTodos; pintarChats(); });
          f.appendChild(sb);
          if (!c.verTodos) subs.length = TOPE_AGENTES - 1;
          subs.push(f);
        }
        subs.forEach(sub => {
          if (sub instanceof Node) { caja.appendChild(sub); return; }
          const f = document.createElement('div');
          f.className = 'chat sub';
          const si = document.createElement('i');
          si.className = 'agente';
          si.style.setProperty('--c', sub.color);
          const sb = document.createElement('b');
          sb.textContent = '↳ ' + nombreSub(c, sub);
          const ss = document.createElement('span');
          ss.textContent = (sub.actual || 'arrancando') + ' · ' + sub.acciones + (sub.acciones === 1 ? ' acción' : ' acciones');
          f.append(si, sb, ss);
          const ag = m && m.agentes.get(sub.aid);
          if (ag && ag.episodio.size) f.appendChild(botonCabeza(ag, ag.episodio.size + ' en la cabeza', 'en-cabeza de-agente', 'cabeza:' + c.id + ':' + sub.aid));
          caja.appendChild(f);
          if (ag && ag.ver && ag.episodio.size) caja.appendChild(listaCabeza(ag.episodio, true, m.color, 'lista:' + c.id + ':' + sub.aid));
        });
      });
      if (caja.innerHTML !== cajaChats.innerHTML) {
        const activo = document.activeElement;
        const antes = [...cajaChats.querySelectorAll('button')];
        const i = cajaChats.contains(activo) ? antes.indexOf(activo) : -1;
        const foco = i >= 0 ? activo.dataset.foco : null;
        cajaChats.replaceChildren(...caja.childNodes);
        if (i >= 0) {
          const nuevos = [...cajaChats.querySelectorAll('button')];
          const igual = nuevos.find(x => x.dataset.foco === foco) || nuevos[Math.min(i, nuevos.length - 1)];
          if (igual) igual.focus();
        }
      }
      pintarResumen(lista);
    }

    function pintarResumen(lista) {
      const esperan = lista.filter(c => c.estado === 'esperando');
      let texto = '';
      if (lista.length === 1) {
        const c = lista[0];
        texto = nombreVisible(c) + ' · ' + ESTADO_TXT[c.estado] + (c.subs.size ? ' · ' + cuentaAgentes(c) : '');
      } else if (lista.length > 1) {
        const agentes = lista.reduce((a, c) => a + c.subs.size, 0);
        texto = lista.length + ' chats' + (esperan.length ? ' · ' + nombreVisible(esperan[0]) + ' espera tu OK' : '') + (agentes ? ' · ' + agentes + (agentes === 1 ? ' agente' : ' agentes') : '');
      }
      if (resumen.textContent !== texto) resumen.textContent = texto;
      resumen.title = texto;
      resumen.classList.toggle('esperando', esperan.length > 0);
    }

    function chatPre(c, ev) {
      if (!c || (ev.id && c.terminados.has(ev.id))) return;
      c.enCurso.set(ev.id || String(ev.t), { t: ev.t });
      c.estado = 'trabajando';
      const que = frase(ev);
      const n = destinoDe(ev);
      if (ev.a) {
        if (!c.hacia) mover(c, anclaDeChat(ev, n));
        const s = subDe(c, ev);
        s.actual = que;
        s.evActual = ev;
        mover(s, n);
        pasear(c, s, ev);
      } else {
        c.actual = que;
        c.evActual = ev;
        mover(c, n);
      }
    }

    function chatPost(c, ev) {
      if (!c) return;
      if (ev.id) { c.enCurso.delete(ev.id); c.terminados.set(ev.id, ev.t || 0); }
      const limite = Date.now() / 1000 - 600;
      c.enCurso.forEach((v, k) => { if (v.t < limite) c.enCurso.delete(k); });
      c.terminados.forEach((t, k) => { if (t < limite) c.terminados.delete(k); });
      if (!c.enCurso.size) c.actual = '';
      c.estado = 'trabajando';
      const n = destinoDe(ev);
      if (ev.a) {
        if (!c.hacia) mover(c, anclaDeChat(ev, n));
        const s = subDe(c, ev);
        s.acciones++;
        mover(s, n);
        s.tAccion = performance.now();
        const nota = notaDe(ev);
        if (nota && s.v && s.v.obj !== nota) pasear(c, s, ev);
      } else {
        mover(c, n);
      }
    }

    function chatFalla(c, ev) {
      if (!c) return;
      if (ev.id) { c.enCurso.delete(ev.id); c.terminados.set(ev.id, ev.t || 0); }
      const limite = Date.now() / 1000 - 600;
      c.enCurso.forEach((v, k) => { if (v.t < limite) c.enCurso.delete(k); });
      c.terminados.forEach((t, k) => { if (t < limite) c.terminados.delete(k); });
      if (!c.enCurso.size) c.actual = '';
      c.estado = 'trabajando';
      const s = ev.a && c.subs.get(ev.a);
      if (s) { s.actual = frase(ev); s.evActual = ev; }
    }

    function chatEvento(c, ev) {
      if (!c) return;
      const ahora = performance.now();
      if (!c.hacia && ev.c) mover(c, anclaDe(ev.c));
      if (ev.e === 'usuario') {
        c.estado = 'trabajando';
        c.actual = 'lee tu mensaje';
        c.evActual = null;
        if (completo() && graficoListo && !introCorriendo() && c.hacia && c.hacia._visible) {
          const llega = gestoPosible() ? RAYO.dur * RAYO.pega : 0;
          onda(c.hacia, llega, 0.9, 1000, 120);
          anim.efectos.push({ tipo: 'aro', n: c.hacia, t0: ahora + llega, dur: 1800, color: c.color });
        }
      } else if (ev.e === 'fin') {
        c.estado = 'listo';
        c.tFin = ahora;
        c.enCurso.clear();
        c.actual = '';
        c.subs.forEach(s => despedir(c, s));
        c.subs.clear();
        guardarVivido(c);
      } else if (ev.e === 'espera') {
        c.estado = 'esperando';
      } else if (ev.e === 'compacta') {
        c.estado = 'compactando';
      } else if (ev.e === 'inicio') {
        c.estado = 'listo';
        c.tFin = ahora;
      } else if (ev.e === 'cierre') {
        c.estado = 'cerrado';
        c.tFin = ahora;
      } else if (ev.e === 'sub-fin') {
        const k = ev.a && c.subs.has(ev.a) ? ev.a : c.subs.keys().next().value;
        if (k !== undefined) {
          despedir(c, c.subs.get(k));
          c.subs.delete(k);
        }
      }
    }

    function repasarCompactando(c, ahora, notas, alTerminar) {
      if (!completo() || !graficoListo || !cerebro || introCorriendo()) return null;
      const temporal = cerebro.lobulos.find(l => l.id === 'temporal');
      if (temporal) {
        activarLobulo('temporal', '#a78bfa', 1.2);
        anim.efectos.push({ tipo: 'rizo', lob: temporal, t0: ahora, dur: 900, color: '#a78bfa' });
      }
      const veces = notas.length <= 12 ? 3 : notas.length <= 20 ? 2 : 1;
      const deRepeticion = repite.activa;
      const lista = repasar(notas, c.color, veces, {
        alfa: 0.9, factores: [0.24, 0.16, 0.1], descarga: 0.5, luz: 0.7, fuente: 'repaso', retardo: 350,
        alTerminar: ns => {
          const t = performance.now();
          if (!deRepeticion) ns.forEach(n => { n._consolidada = t; });
          ritmo.repaso = 0;
          pedirDibujo();
          if (alTerminar) alTerminar();
        }
      });
      if (lista) ritmo.repaso = ahora + 800 + 260 * lista.length * veces;
      programarCuadro();
      return lista;
    }

    function visualAgente(ev) {
      const c = chats.get(ev.s);
      const s = c && c.subs.get(ev.a);
      return s && s.v && paseoPosible() ? s.v : null;
    }

    const aprende = { ventanas: new Map(), uniones: [], pendiente: 0 };
    const VENTANA_APRENDE = 8;
    const UNIONES_A_LA_VISTA = 5;
    function aprenderDe(ev) {
      if (DATOS.aprender === false) return;
      const e = ev.e || 'post';
      const llave = (ev.s || '') + '|' + (ev.a || '');
      if (e === 'usuario' && !ev.a) { aprende.ventanas.delete(llave); return; }
      if (e !== 'post' || (ev.k !== 'leer' && ev.k !== 'editar' && ev.k !== 'crear')) return;
      const rutas = (ev.f ? [ev.f] : rutasLeidas(ev)).filter(r => typeof r === 'string' && /\.[A-Za-z0-9]{1,12}$/.test(r));
      if (!rutas.length) return;
      const t = Number(ev.t) || Date.now() / 1000;
      let v = aprende.ventanas.get(llave);
      if (!v || t - v.t > 1800) {
        for (const [k, w] of aprende.ventanas) if (t - w.t > 1800) aprende.ventanas.delete(k);
        v = { t, lista: [] };
        aprende.ventanas.set(llave, v);
      }
      v.t = t;
      for (const r of rutas) {
        const k = clave(r);
        const i = v.lista.findIndex(x => x.k === k);
        if (i >= 0) v.lista.splice(i, 1);
        else {
          const nota = ev.a && /\.md$/i.test(r);
          const otras = v.lista.map(x => x.r).reverse().filter(o => !(nota && /\.md$/i.test(o)));
          if (otras.length) unir(r, otras, t, ev);
        }
        v.lista.push({ k, r });
        if (v.lista.length > VENTANA_APRENDE) v.lista.shift();
      }
    }
    function unir(r, otras, t, ev) {
      aprende.uniones.unshift({ r, otras, t, nueva: true });
      aprende.uniones.length = Math.min(aprende.uniones.length, UNIONES_A_LA_VISTA);
      const n = porRuta.get(clave(r));
      const color = anim.oscuro ? '#c4b5fd' : '#7c3aed';
      if (n && n._visible && gestoPosible() && !introCorriendo()) {
        const luz = anim.oscuro ? aclarar(color, 0.35) : color;
        const ahora = performance.now();
        otras.map(o => porRuta.get(clave(o))).filter(m => m && m !== n && m._visible && m._en).slice(0, 3).forEach((m, i) => {
          const l = aristaEntre(m, n);
          const camino = l && tapada(l) ? l._sobre.find(o => o._visible) : l;
          if (camino) {
            anim.efectos.push({ tipo: 'potencia', l: camino, t0: ahora + i * 140, dur: 900, color: luz, fuente: 'aprende',
                                alPegar: () => activarNota(n, color, 0.75, 2400) });
            return;
          }
          anim.efectos.push({ tipo: 'rayo', n, lob: null, t0: ahora + i * 140, dur: RAYO.dur, pega: RAYO.pega, color, giro: i % 2 ? -1 : 1,
                              alPegar: () => activarNota(n, color, 0.75, 2400), x0: m._sx, y0: m._sy, luz,
                              c0: aRgba(color, 0), c1: aRgba(luz, 1) });
        });
        programarCuadro();
      }
      clearTimeout(aprende.pendiente);
      aprende.pendiente = setTimeout(pintarAprendiendo, 250);
    }
    function nombreUnido(r) {
      const n = porRuta.get(clave(r));
      return n ? tituloVisto(n, 42) : publico('archivo', r, nombreArchivo(r));
    }
    function pintarAprendiendo() {
      const caja = $('#aprendiendo');
      if (!aprende.uniones.length || DATOS.aprender === false) { caja.hidden = true; return; }
      const ahora = Date.now() / 1000;
      caja.innerHTML = '<div class="salud-sub">Ahora está uniendo</div>' + aprende.uniones.map(u => {
        const hace = Math.max(0, Math.round(ahora - u.t));
        const cuando = hace < 60 ? 'hace ' + hace + ' s' : 'hace ' + Math.round(hace / 60) + ' min';
        const otras = u.otras.slice(0, 3).map(o => esc(nombreUnido(o))).join(', ') + (u.otras.length > 3 ? ' y ' + (u.otras.length - 3) + ' más' : '');
        const html = '<div class="union' + (u.nueva ? ' nueva' : '') + '"><b>' + esc(nombreUnido(u.r)) + '</b> con ' + otras
          + ' <span class="cuando">· ' + cuando + '</span></div>';
        u.nueva = false;
        return html;
      }).join('');
      caja.hidden = false;
      $('#bloque-aprendido').hidden = false;
    }
    setInterval(() => { if (aprende.uniones.length) pintarAprendiendo(); }, 10000);

    function pulsoConsulta(ev) {
      const color = COLOR.consulta;
      const notas = (ev.e === 'aviso' ? pistaDe(ev) : notasRecomendadas(ev).map(n => ({ n, motivo: '' }))).filter(x => x.n._visible);
      const lob = cerebro ? cerebro.lobulos.find(x => x.id === LOBULO_CONSULTA) : null;
      activarLobulo(LOBULO_CONSULTA, color, notas.length ? 1 : 0.7);
      choqueLobulo(LOBULO_CONSULTA, color, notas.length ? 0.6 : 0.5);
      if (!notas.length) return;
      const origen = lob && gestoPosible() ? blancoRayo({ lob }) : null;
      const ahora = performance.now();
      notas.forEach(({ n, motivo }, i) => {
        const tinta = motivo ? MOTIVO_PISTA[motivo][1] : color;
        const luz = anim.oscuro ? aclarar(tinta, 0.35) : tinta;
        const alPegar = () => {
          choque(n, tinta, 0.8 - 0.08 * i);
          activarNota(n, tinta, 1 - 0.1 * i, 6000);
        };
        if (!origen) { alPegar(); return; }
        anim.efectos.push({ tipo: 'rayo', n, lob: null, t0: ahora + i * 170, dur: RAYO.dur, pega: RAYO.pega, color: tinta, giro: i % 2 ? -1 : 1, alPegar,
                            x0: origen[0], y0: origen[1], luz, c0: aRgba(tinta, 0), c1: aRgba(luz, 1) });
      });
      if (origen) programarCuadro();
    }

    function reaccionar(ev) {
      if (introCorriendo()) return;
      const e = ev.e || 'post';
      const quien = ev.a ? colorAgente(ev.a) : colorChat(ev.s || 'x');
      if ((e === 'post' && ev.k === 'consulta') || e === 'aviso' || e === 'recuerda') pulsoConsulta(ev);
      if (e === 'pre' || e === 'post') {
        const sv = ev.a && !notaDe(ev) ? visualAgente(ev) : null;
        if (sv) {
          sv.pulso = performance.now();
          if (e === 'post' && GOLPE[ev.k] > 1) choqueEn(sv.x, sv.y, sv.z, colorEvento(ev), 0.55, null);
          if (e === 'post' && ev.b === 'compila') activarLobulo('cerebelo', '#fb923c', 1.1);
          if (e === 'post' && ev.b === 'commit') barrido('#22c55e', anclaEvento(ev));
          return;
        }
        const n = destinoDe(ev);
        if (n) activarNota(n, e === 'pre' ? quien : colorEvento(ev), e === 'pre' ? 0.55 : 1, ev.k === 'editar' || ev.k === 'crear' ? 3800 : 2600);
        if (e === 'post') {
          const golpe = GOLPE[ev.k];
          const nota = notaDe(ev);
          if (golpe && nota) choque(nota, colorEvento(ev), golpe);
          else if (golpe > 1 && n) choque(n, colorEvento(ev), 0.55);
          notasDe(ev).slice(1).forEach(x => activarNota(x, colorEvento(ev), 0.7, 2600));
        }
        if (e === 'post' && ev.b === 'compila') activarLobulo('cerebelo', '#fb923c', 1.1);
        if (e === 'post' && ev.b === 'commit') barrido('#22c55e', anclaEvento(ev));
      } else if (e === 'usuario') {
        const deSueno = ritmo.desperto && performance.now() - ritmo.desperto < 600;
        const color = anim.oscuro ? '#a5b4fc' : '#4f46e5';
        if (deSueno) {
          rayo(null, 'tronco', color, () => {
            activarLobulo('tronco', color, 1.2);
            ondaGlobal(color, 1.4, 'tronco');
            choqueLobulo('tronco', color, 1);
          });
        } else {
          const c = chats.get(ev.s);
          const n = c && c.hacia;
          rayo(n, 'prefrontal', color, () => {
            if (n && n._visible) choque(n, color, 0.9);
            else choqueLobulo('prefrontal', color, 0.9);
            activarLobulo('prefrontal', color, 0.9);
          });
        }
      } else if (e === 'fin') {
        apretar('suspiro', 1);
      } else if (e === 'compacta') {
        apretar('apreton', 1);
      } else if (e === 'inicio') {
        ondaGlobal(quien, 0.5);
      } else if (e === 'espera') {
        const c = chats.get(ev.s);
        if (c && c.hacia) activarNota(c.hacia, '#eab308', 1.2, 9000);
      }
    }

    function brasaDe(ev, n, t) {
      const peso = PESO_TOQUE[ev.k];
      if (!peso || (ev.e && ev.e !== 'post')) return;
      const primera = ev.f || rutasLeidas(ev)[0];
      const destino = n || (primera && anclaDe(primera)) || null;
      const color = ev.a ? colorAgente(ev.a) : colorChat(ev.s || 'x');
      if (destino) tocarBrasa(destino, color, n ? peso : peso * 0.5, t, !!ev.demo);
      if (n) notasDe(ev).forEach(x => { if (x !== n) tocarBrasa(x, color, peso, t, !!ev.demo); });
    }

    function sumarUso(n, ev, falla) {
      const u = n._uso || (n._uso = { leer: 0, editar: 0, shell: 0, parcial: 0, falla: 0 });
      if (falla) u.falla++;
      else if (ev.k === 'leer') u.leer++;
      else if (ev.k === 'editar' || ev.k === 'crear') u.editar++;
      if (!falla && porConsola(ev)) u.shell++;
      if (!falla && ev.k === 'leer' && ev.f && tramoLeido(ev)) u.parcial++;
    }

    function encenderBrasas() {
      if (brasas.activo) return;
      brasas.activo = true;
      pedirDibujo();
    }

    const CAMPOS_TEXTO = ['e', 's', 'h', 'k', 'c', 'a', 'at', 'id', 'f', 'p', 'b', 'o'];
    const CAMPOS_RUTAS = ['fs', 'fc', 'na', 'ca'];
    const CAMPOS_CIFRAS = ['m', 'r', 'x'];
    const CAMPOS_NUMERO = ['n', 'd', 'xc', 'bg', 'nr'];

    function eventoSano(ev) {
      if (!ev || typeof ev !== 'object' || Array.isArray(ev)) return null;
      const t = Number(ev.t);
      const ahora = Date.now() / 1000;
      ev.t = Number.isFinite(t) && t > 0 && t < ahora + 86400 ? t : ahora;
      CAMPOS_TEXTO.forEach(k => { if (k in ev && typeof ev[k] !== 'string') delete ev[k]; });
      CAMPOS_RUTAS.forEach(k => {
        if (!(k in ev)) return;
        if (Array.isArray(ev[k])) ev[k] = ev[k].filter(x => typeof x === 'string');
        else delete ev[k];
      });
      CAMPOS_CIFRAS.forEach(k => { if (k in ev && !(Array.isArray(ev[k]) && ev[k].every(Number.isFinite))) delete ev[k]; });
      CAMPOS_NUMERO.forEach(k => { if (k in ev && !(Number.isFinite(ev[k]) && ev[k] >= 0)) delete ev[k]; });
      if ('fp' in ev && !(Array.isArray(ev.fp) && ev.fp.every(m => Array.isArray(m) && m.length === 4 && typeof m[0] === 'string'
          && Number.isFinite(m[1]) && Number.isFinite(m[2]) && typeof m[3] === 'string'))) delete ev.fp;
      return ev;
    }

    function recibirSeguro(ev) {
      const sano = eventoSano(ev);
      if (!sano) return;
      try {
        recibir(sano);
      } catch (error) {
        vivo.fallas = (vivo.fallas || 0) + 1;
        console.error('Neuromapa: no pude mostrar un evento en vivo (' + vivo.fallas + ' en esta pestaña):', error);
      }
    }

    function recibir(ev) {
      const e = ev.e || 'post';
      if (ev.t && !ev.demo) brasas.ultimoT = Math.max(brasas.ultimoT, ev.t);
      despertar(e === 'usuario');
      marcarPicoEEG(e === 'usuario' ? 1.1 : e === 'pre' ? 0.35 : 0.6);
      const c = chatDe(ev);
      if (e === 'pre') {
        chatPre(c, ev);
      } else if (e === 'post') {
        if (c && ev.id && c.enCurso.has(ev.id)) ev._dur = ev.t - c.enCurso.get(ev.id).t;
        accion(ev);
        chatPost(c, ev);
      } else if (e === 'falla') {
        if (c && ev.id && c.enCurso.has(ev.id)) ev._dur = ev.t - c.enCurso.get(ev.id).t;
        fila(ev, false);
        chatFalla(c, ev);
        const n = ev.f ? notaDe(ev) : null;
        if (n && vivo.uso && !ev.demo) sumarUso(n, ev, true);
      } else {
        fila(ev, false);
        chatEvento(c, ev);
      }
      if (memoriaEvento(ev, true)) recalcularCabeza();
      aprenderDe(ev);
      recordarPista(ev);
      reaccionar(ev);
      pintarChats();
      anotarRio(ev, true);
      asegurarChats();
      if (document.hidden && anim.efectos.length) vaciarEfectos();
    }
    function podarVivo() {
      const ahora = Date.now();
      const segundos = ahora / 1000;
      archivos.forEach((a, k) => { if (!(a.t >= segundos - 1800)) archivos.delete(k); });
      ediciones.forEach((lista, k) => { if (!lista.length || segundos - lista[lista.length - 1].t > VENTANA_CHOQUE) ediciones.delete(k); });
      avisados.forEach((t, k) => { if (segundos - t > VENTANA_CHOQUE) avisados.delete(k); });
      memorias.forEach((m, s) => {
        m.agentes.forEach((ag, a) => { if (ahora - ag.tUlt > QUIETO_AGENTE) m.agentes.delete(a); });
        for (const ep of [m.episodio, ...[...m.agentes.values()].map(ag => ag.episodio)]) {
          while (ep.size > TOPE_CABEZA) ep.delete(ep.keys().next().value);
        }
        if (!chats.has(s) && !m.olvidando && ahora - m.tUlt > QUIETO_CHAT) memorias.delete(s);
      });
    }
    setInterval(() => {
      if (document.hidden && anim.efectos.length) vaciarEfectos();
      podarVivo();
      if (memorias.size) recalcularCabeza();
      if (!chats.size) return;
      if (vencerChats(performance.now())) pintarChats();
      for (const c of chats.values()) if (c.estado === 'trabajando' && c.enCurso.size) { despertar(); break; }
      asegurarChats();
      pintarChats();
    }, 3000);

    const VENTANA_CHOQUE = MINUTOS_CHOQUE * 60;
    const ediciones = new Map();
    const avisados = new Map();
    function anotarChoque(ev) {
      if ((ev.k !== 'editar' && ev.k !== 'crear') || !ev.f || !ev.s || ev.repite) return null;
      const k = clave(ev.f);
      const t = Number(ev.t) || Date.now() / 1000;
      const actor = ev.s + '|' + (ev.a || '');
      const lista = (ediciones.get(k) || []).filter(x => t - x.t <= VENTANA_CHOQUE);
      const otro = lista.filter(x => x.actor !== actor).pop();
      lista.push({ actor, t, s: ev.s, a: ev.a || '' });
      ediciones.set(k, lista.slice(-12));
      if (!otro) return null;
      const par = k + '|' + [actor, otro.actor].sort().join('|');
      if (t - (avisados.get(par) || -Infinity) <= VENTANA_CHOQUE) return null;
      avisados.set(par, t);
      return { e: 'choque', t, f: ev.f, s: ev.s, a: ev.a, at: ev.at, c: ev.c, demo: ev.demo, otro: { s: otro.s, a: otro.a, t: otro.t } };
    }
    function quienEdito(o) {
      const c = chats.get(o.s);
      return (o.a ? 'un agente de ' : '') + (c ? nombreVisible(c) : publico('chat', o.s, 'otro chat'));
    }

    function accion(ev) {
      fila(ev, false);
      const choque = anotarChoque(ev);
      if (choque) fila(choque, false);
      anotarArchivo(ev);
      pintarProgramando();
      if (ev.k === 'consulta' && !ev.demo) refrescarUso();
      const n = notaDe(ev);
      brasaDe(ev, n, performance.now());
      if (n && vivo.uso && !ev.demo) {
        const cuenta = ev.k === 'leer' || ev.k === 'editar' || ev.k === 'crear';
        const suma = cuenta ? 1 : ev.k === 'buscar' ? PESO_BUSCAR : 0;
        notasDe(ev).forEach(x => {
          if (suma) {
            x._usos = (x._usos || 0) + suma;
            x._calor = ESCALA[nivel(x._usos)];
          }
          if (cuenta || porConsola(ev)) sumarUso(x, ev, false);
        });
        if (suma && vivo.calor) { pintarUso(); pedirDibujo(); }
      }
      const suChat = chats.get(ev.s);
      const previo = (suChat && suChat.ultimaNota) || vivo.previo;
      if (n) {
        vivo.previo = n;
        if (suChat) {
          suChat.ultimaNota = n;
          suChat.camino = suChat.camino || [];
          const ult = suChat.camino[suChat.camino.length - 1];
          if (!ult || ult.n !== n) suChat.camino.push({ n, t: performance.now() });
          else ult.t = performance.now();
          if (suChat.camino.length > 12) suChat.camino.shift();
        }
      }
      if (!completo() || !graficoListo || estado.vista !== 'grafo' || introCorriendo()) return;
      const color = colorEvento(ev);
      const ahora = performance.now();
      if (n && n._visible) {
        anim.efectos.push({ tipo: 'aro', n, t0: ahora, dur: 1700, color });
        if (ev.a) anim.efectos.push({ tipo: 'aro', n, t0: ahora + 160, dur: 1600, color: colorAgente(ev.a), guion: true });
        if (previo && previo !== n && previo._visible) {
          anim.efectos.push({ tipo: 'rastro', desde: previo, hacia: n, t0: ahora, dur: 7000, color });
          viajar(previo, n, color, 840);
        }
        if ((ev.k === 'leer' || ev.k === 'editar' || ev.k === 'crear') && ahora - vivo.tDisparo > 900) {
          vivo.tDisparo = ahora;
          disparar(n);
        } else {
          descargar(n, 0.7);
        }
      } else if (!n) {
        const ancla = anclaEvento(ev);
        const deAgente = !!(ev.a && visualAgente(ev));
        if (ancla && ancla._visible) {
          if (!deAgente) anim.efectos.push({ tipo: 'aro', n: ancla, t0: ahora, dur: 1200, color });
          if (ev.s && !deAgente) anim.efectos.push({ tipo: 'aro', n: ancla, t0: ahora + 140, dur: 1400, color: colorChat(ev.s), guion: true });
          if (ev.b === 'commit' && ahora - vivo.tDisparo > 900) {
            vivo.tDisparo = ahora;
            disparar(ancla);
          }
          if ((ev.f || ev.p || rutasLeidas(ev).length) && !deAgente) {
            const orden = anim.efectos.filter(e => e.tipo === 'satelite' && e.n === ancla).length % 4;
            const nombre = nombreCorto(ev);
            const texto = recortar(nombre, 32) + (ev.m ? '  +' + ev.m[0] + ' −' + ev.m[1] : '');
            anim.efectos.push({ tipo: 'satelite', n: ancla, t0: ahora, dur: ev.m ? 12000 : 8000, color, texto, ang: anguloSatelite(ancla, nombre, texto, orden), orden });
          } else if (ev.k === 'ejecutar' && COMANDO[ev.b] && ev.b !== 'otro' && !deAgente && suChat && ahora - (suChat.tCartelComando || -Infinity) > CARTEL_COMANDO_MS) {
            suChat.tCartelComando = ahora;
            const s = segundosDe(ev);
            const texto = COMANDO[ev.b] + (ev._veces > 1 ? ' ×' + ev._veces : '') + (ev.nr ? ' · sin resultados' : '') + (s > 1.5 ? ' · ' + duracionTexto(s) : '');
            const orden = anim.efectos.filter(e => e.tipo === 'satelite' && e.n === ancla).length % 4;
            anim.efectos.push({ tipo: 'satelite', n: ancla, t0: ahora, dur: 6000, color, texto, ang: anguloSatelite(ancla, COMANDO[ev.b], texto, orden), orden });
          }
        }
      }
      programarCuadro();
    }
    const CARTEL_COMANDO_MS = 4000;

    const plegar = $('#en-vivo-plegar');
    function ponerPlegado(plegado, guardar) {
      caja.classList.toggle('plegado', plegado);
      plegar.setAttribute('aria-expanded', String(!plegado));
      plegar.setAttribute('aria-label', plegado ? 'Desplegar el panel Ahora' : 'Plegar el panel Ahora');
      plegar.title = plegado ? 'Desplegar' : 'Plegar';
      if (guardar) try { localStorage.setItem('cerebro-ahora', plegado ? 'plegado' : 'abierto'); } catch (e) {}
    }
    let plegadoGuardado = null;
    try { plegadoGuardado = localStorage.getItem('cerebro-ahora'); } catch (e) {}
    ponerPlegado(plegadoGuardado === 'plegado' || plegadoGuardado === 'abierto' ? plegadoGuardado === 'plegado' : esMovil(), false);

    caja.hidden = false;
    const medirCaja = () => {
      const antes = vivo.tapaPanel;
      if (caja.hidden || !caja.offsetWidth || !caja.offsetParent) vivo.tapaPanel = null;
      else {
        const r = caja.getBoundingClientRect(), p = caja.offsetParent.getBoundingClientRect();
        vivo.tapaPanel = [Math.round(r.left - p.left), Math.round(r.top - p.top), Math.round(r.right - p.left), Math.round(r.bottom - p.top)];
      }
      if (String(antes) !== String(vivo.tapaPanel)) pedirDibujo();
    };
    medirCaja();
    caja.addEventListener('click', (e) => {
      if (caja.classList.contains('plegado') && !e.target.closest('button, a, input')) plegar.click();
    });
    plegar.addEventListener('click', () => {
      ponerPlegado(!caja.classList.contains('plegado'), true);
      medirCaja();
      if (!estado.seleccionado && !introCorriendo()) {
        cancelarEncuadre();
        encuadrar(true);
      }
    });
    if (typeof ResizeObserver === 'function') {
      const ro = new ResizeObserver(medirCaja);
      ro.observe(caja);
      ro.observe(centro);
    } else {
      window.addEventListener('resize', medirCaja);
      setInterval(medirCaja, 3000);
    }
    modoColor.hidden = false;
    modoColor.querySelector('[data-color="uso"]').hidden = false;
    vivo.ponerColor = ponerColor;
    recargar.addEventListener('click', () => location.reload());

    const probar = $('#en-vivo-probar');
    probar.addEventListener('click', () => {
      if (repite.activa || repite.cargando) return;
      const grado = n => n.salientes.length + n.entrantes.length;
      const vecinos = n => n.salientes.map(l => l.target).concat(n.entrantes.map(l => l.source)).filter(v => v !== n && v._visible);
      const centro = nodos.filter(n => n._visible).sort((a, b) => grado(b) - grado(a))[0];
      if (!centro) return;
      const v = vecinos(centro).sort((a, b) => grado(b) - grado(a));
      const a = v[0] || centro;
      const b = vecinos(a).find(x => x !== centro) || v[1] || centro;
      const c = v[2] || v[1] || centro;
      const pasos = [
        { k: 'consulta', h: 'Bash', b: 'cerebro', p: 'sobre', fs: [centro.ruta, a.ruta, b.ruta, c.ruta] },
        { k: 'leer', h: 'Read', f: centro.ruta },
        { k: 'buscar', h: 'Grep', p: 'ActionSync', f: centro.ruta.replace(/[\\/][^\\/]+$/, '') },
        { k: 'leer', h: 'Read', f: a.ruta },
        { k: 'leer', h: 'Read', f: b.ruta },
        { k: 'leer', h: 'Read', f: RAIZ_PRUEBA + '\\src\\Servidor.cs' },
        { k: 'editar', h: 'Edit', f: RAIZ_PRUEBA + '\\src\\Servidor.cs', m: [12, 3] },
        { k: 'editar', h: 'Edit', f: b.ruta, m: [4, 1] },
        { k: 'ejecutar', h: 'Bash', b: 'compila' },
        { k: 'buscar', h: 'Grep', p: 'ActionSync', f: a.ruta, a: 'agente-de-prueba', at: 'Explore' },
        { k: 'leer', h: 'Read', f: c.ruta, a: 'agente-de-prueba', at: 'Explore' },
        { k: 'crear', h: 'Write', f: RAIZ_PRUEBA + '\\docs\\nota-de-prueba.ini', m: [20, 0] },
        { k: 'ejecutar', h: 'Bash', b: 'commit' },
        { k: 'leer', h: 'Read', f: centro.ruta }
      ];
      const base = { s: 'prueba', c: RAIZ_PRUEBA, demo: true };
      const seq = [{ e: 'usuario' }];
      pasos.forEach((p, i) => {
        seq.push(Object.assign({ e: 'pre', id: 'd' + i }, p));
        seq.push(Object.assign({ e: 'post', id: 'd' + i }, p));
        if (p.a && !(pasos[i + 1] && pasos[i + 1].a)) seq.push({ e: 'sub-fin', a: p.a });
      });
      seq.splice(seq.length - 4, 0, { e: 'espera' });
      seq.push({ e: 'fin' });
      const lecturas = [a, b, c, centro];
      const TAREAS = [
        { k: 'ejecutar', h: 'Bash', b: 'script' }, { k: 'ejecutar', h: 'Bash', b: 'git' }, { k: 'buscar', h: 'Grep', p: 'ActionSync' },
        { k: 'ejecutar', h: 'Bash', b: 'compila' }, { k: 'ejecutar', h: 'Bash', b: 'prueba' }, { k: 'ejecutar', h: 'Bash', b: 'base' }
      ];
      const flujo = [];
      for (let r = 0; r < 4; r++) {
        for (let i = 0; i < 6; i++) {
          const agente = { a: 'flujo-de-prueba-' + i, at: 'workflow-subagent' };
          const lee = r === 2 && i % 2 === 0;
          const tarea = lee ? { k: 'leer', h: 'Read', f: lecturas[(i / 2) % lecturas.length].ruta } : TAREAS[(i + r * 2) % TAREAS.length];
          const t = 2600 + r * 2800 + i * 230;
          flujo.push([t, Object.assign({ e: 'pre', id: 'f' + r + '-' + i }, tarea, agente)]);
          flujo.push([t + 380, Object.assign({ e: 'post', id: 'f' + r + '-' + i }, tarea, agente)]);
        }
      }
      for (let i = 0; i < 6; i++) flujo.push([2600 + 4 * 2800 + 900 + i * 420, { e: 'sub-fin', a: 'flujo-de-prueba-' + i }]);
      probar.disabled = true;
      if (estado.vista !== 'grafo') cambiarVista('grafo');
      flujo.forEach(([t, p]) => setTimeout(() => recibirSeguro(Object.assign({ t: Date.now() / 1000 }, base, p)), t));
      seq.forEach((p, i) => setTimeout(() => {
        recibirSeguro(Object.assign({ t: Date.now() / 1000 }, base, p));
        if (i === seq.length - 1) probar.disabled = false;
      }, 300 + i * 700));
    });

    const repetir = $('#en-vivo-repetir');
    const reloj = {
      el: $('#repite'), fecha: $('#repite-fecha'), hora: $('#repite-hora'), pausa: $('#repite-pausa'), cifras: $('#repite-cifras'),
      franja: $('#repite-franja'), cabezal: $('#repite-cabezal'), vel: $('#repite-vel'), pausar: $('#repite-pausar'),
      menos: $('#repite-menos'), mas: $('#repite-mas')
    };
    const VELOCIDADES = [10, 20, 30, 60, 120, 300, 600, 1200, 3000];
    const PAUSA_LARGA = 120;
    const PAUSA_REAL = 1500;
    const POR_SEGUNDO = 8;
    const DURACION_IDEAL = 90;
    const MINIMO_DEL_DIA = 30;
    const COLA_TOPE = 3000;
    const PAGINAS = 3;
    const ESPERA_HISTORIA = 20000;
    const AUSENCIA = 300;
    const CAMPOS_REPITE = ['s', 'e', 'k', 'h', 'b', 'p', 'a', 'at', 'm', 'f', 'fs', 'c'];
    const repite = { activa: false, cargando: false, eventos: [], i: 0, va: 0, vel: 60, pausaHasta: 0, detenida: false, tPrev: 0, reloj: 0, cierre: 0,
                     pendientes: [], cola: [], guardado: null, cuentas: null, t0: 0, t1: 0, fin: 0, hora: '', cifras: '' };

    const duracion = s => {
      const min = Math.max(1, Math.round(s / 60));
      if (min < 60) return min + ' min';
      const h = Math.floor(min / 60);
      return h + ' h' + (min % 60 ? ' ' + (min % 60) + ' min' : '');
    };
    const fechaLarga = t => new Date(t * 1000).toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'numeric' });

    function importancia(ev) {
      if (ev.e !== 'post') return ev.e === 'falla' ? 2 : 3;
      if (ev.b === 'commit' || ev.b === 'compila' || ev.k === 'agente') return 3;
      if (ev.k === 'consulta' || ev.k === 'editar' || ev.k === 'crear') return 2;
      return notaDe(ev) ? 1.5 : 1;
    }

    function prepararLinea(lista) {
      let a = 0;
      let previo = null;
      lista.forEach(ev => {
        ev._pausa = null;
        ev._vista = false;
        if (previo !== null) {
          const hueco = ev.t - previo;
          if (hueco > PAUSA_LARGA) ev._pausa = [previo, ev.t];
          else a += Math.max(0, hueco);
        }
        ev._a = a;
        previo = ev.t;
      });
      return a;
    }

    function velocidadCercana(v) {
      const x = Math.max(1, v);
      return VELOCIDADES.reduce((mejor, o) => Math.abs(Math.log(o / x)) < Math.abs(Math.log(mejor / x)) ? o : mejor, VELOCIDADES[0]);
    }

    function pintarVel() {
      reloj.vel.textContent = '×' + repite.vel;
      reloj.vel.title = 'Cada segundo pasan ' + duracion(repite.vel) + ' del día';
      reloj.menos.disabled = repite.vel === VELOCIDADES[0];
      reloj.mas.disabled = repite.vel === VELOCIDADES[VELOCIDADES.length - 1];
    }

    function cambiarVelocidad(paso) {
      const i = VELOCIDADES.indexOf(repite.vel);
      repite.vel = VELOCIDADES[Math.max(0, Math.min(VELOCIDADES.length - 1, (i < 0 ? 3 : i) + paso))];
      pintarVel();
    }

    function pintarFranja(cv, cuentas, t0, t1) {
      const w = cv.clientWidth;
      const h = cv.clientHeight;
      const g = w && h ? cv.getContext('2d') : null;
      if (!g) return;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      cv.width = Math.round(w * dpr);
      cv.height = Math.round(h * dpr);
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, w, h);
      const cajones = Math.max(1, Math.floor(w / 3));
      const suma = new Float64Array(cajones);
      const largo = Math.max(1, t1 - t0);
      cuentas.forEach(([t, n]) => { suma[Math.min(cajones - 1, Math.max(0, Math.floor((t - t0) / largo * cajones)))] += n; });
      let max = 0;
      suma.forEach(v => { if (v > max) max = v; });
      const estilo = getComputedStyle(document.documentElement);
      g.fillStyle = estilo.getPropertyValue('--borde-fuerte').trim() || '#888';
      g.fillRect(0, h - 1, w, 1);
      g.fillStyle = estilo.getPropertyValue('--acento').trim() || '#6366f1';
      suma.forEach((v, i) => {
        if (!v) return;
        const alto = Math.max(2, Math.sqrt(v / max) * (h - 2));
        g.fillRect(i * 3, h - 1 - alto, 2, alto);
      });
    }

    function horaRepite() {
      const lista = repite.eventos;
      if (!repite.i) return repite.t0;
      const ult = lista[repite.i - 1];
      const sig = lista[repite.i];
      const t = ult.t + Math.max(0, repite.va - ult._a);
      return sig ? Math.min(t, sig.t) : ult.t;
    }

    function pintarReloj() {
      const t = horaRepite();
      const hora = horaCorta(t);
      if (hora !== repite.hora) {
        repite.hora = hora;
        reloj.hora.textContent = hora;
        reloj.hora.setAttribute('aria-label', 'Hora del día que se repite: ' + hora);
      }
      const k = repite.cuentas;
      const cifras = [[k.mensajes, 'mensaje', 'mensajes'], [k.commits, 'commit', 'commits'], [k.agentes.size, 'agente', 'agentes'], [k.notas.size, 'nota', 'notas']]
        .map(([n, uno, varios]) => '<b>' + n + '</b> ' + (n === 1 ? uno : varios)).join(' · ');
      if (cifras !== repite.cifras) {
        repite.cifras = cifras;
        reloj.cifras.innerHTML = cifras;
      }
      reloj.cabezal.style.left = (100 * Math.max(0, Math.min(1, (t - repite.t0) / Math.max(1, repite.t1 - repite.t0)))) + '%';
    }

    function contarRepite(ev) {
      const k = repite.cuentas;
      if (ev.e === 'usuario') k.mensajes++;
      if (ev.a) k.agentes.add(ev.a);
      if (ev.e !== 'post') return;
      if (ev.b === 'commit') k.commits++;
      notasDe(ev).forEach(n => k.notas.add(n));
    }

    function encolarRepite(ev) {
      const p = repite.pendientes;
      ev._imp = importancia(ev);
      p.push(ev);
      if (p.length <= POR_SEGUNDO) return;
      let peor = 0;
      for (let i = 1; i < p.length; i++) if (p[i]._imp < p[peor]._imp) peor = i;
      p.splice(peor, 1);
    }

    function entregarRepite(ev) {
      const copia = { t: Date.now() / 1000, to: ev.t, demo: true, repite: true };
      CAMPOS_REPITE.forEach(k => { if (ev[k] !== undefined) copia[k] = ev[k]; });
      recibirSeguro(copia);
    }

    function pasoRepite() {
      if (!repite.activa) return;
      const ahora = performance.now();
      const dt = Math.min(250, Math.max(0, ahora - repite.tPrev));
      repite.tPrev = ahora;
      const lista = repite.eventos;
      if (!repite.detenida) {
        if (repite.pausaHasta && ahora >= repite.pausaHasta) {
          repite.pausaHasta = 0;
          reloj.pausa.textContent = '';
        }
        if (!repite.pausaHasta) {
          repite.va += dt / 1000 * repite.vel;
          while (repite.i < lista.length && lista[repite.i]._a <= repite.va) {
            const ev = lista[repite.i];
            if (ev._pausa && !ev._vista) {
              ev._vista = true;
              repite.va = ev._a;
              repite.pausaHasta = ahora + PAUSA_REAL;
              reloj.pausa.textContent = 'Pausa de ' + duracion(ev._pausa[1] - ev._pausa[0]) + ': de las ' + horaCorta(ev._pausa[0]) + ' a las ' + horaCorta(ev._pausa[1]);
              break;
            }
            repite.i++;
            contarRepite(ev);
            encolarRepite(ev);
          }
        }
        const ev = repite.pendientes.shift();
        if (ev) entregarRepite(ev);
      }
      pintarReloj();
      if (!repite.fin && repite.i >= lista.length && !repite.pendientes.length) {
        repite.fin = ahora;
        reloj.pausa.textContent = 'Fin de la repetición';
        repite.cierre = setTimeout(terminarRepite, 3000);
      }
    }

    function guardarVivo() {
      repite.guardado = {
        chats: [...chats.entries()], memorias: [...memorias.entries()], memoriaT, territorios: [...territoriosUsados],
        hechas: hechas.slice(), previo: vivo.previo, brasas: [...brasas.notas.entries()]
      };
      chats.clear();
      memorias.clear();
      territoriosUsados.clear();
      brasas.notas.forEach((b, n) => { n._brasa = null; });
      brasas.notas.clear();
      brasas.lista.length = 0;
      brasas.tElegir = 0;
      vivo.previo = null;
      hechas.length = 0;
      filas.textContent = '';
      vivo.apagarZocalo();
      recalcularCabeza();
      pintarChats();
    }

    function restaurarVivo() {
      const g = repite.guardado;
      repite.guardado = null;
      if (!g) return;
      chats.clear();
      g.chats.forEach(([k, v]) => chats.set(k, v));
      memorias.clear();
      g.memorias.forEach(([k, v]) => memorias.set(k, v));
      memoriaT = g.memoriaT;
      territoriosUsados.clear();
      g.territorios.forEach(i => territoriosUsados.add(i));
      brasas.notas.forEach((b, n) => { n._brasa = null; });
      brasas.notas.clear();
      brasas.lista.length = 0;
      g.brasas.forEach(([n, b]) => { n._brasa = b; brasas.notas.set(n, b); });
      brasas.tElegir = 0;
      vivo.previo = g.previo;
      vivo.apagarZocalo();
      repintando = true;
      hechas.length = 0;
      filas.textContent = '';
      g.hechas.forEach(([ev, viejo]) => fila(ev, viejo));
      repintando = false;
    }

    async function pedirHistoria(desde, hasta) {
      const control = new AbortController();
      const reloj = setTimeout(() => control.abort(), ESPERA_HISTORIA);
      try {
        let eventos = [];
        let d = desde;
        for (let pagina = 0; pagina < PAGINAS; pagina++) {
          const r = await fetch('/historia?desde=' + d.toFixed(3) + '&hasta=' + hasta.toFixed(3), { cache: 'no-store', signal: control.signal });
          if (!r.ok) throw new Error(String(r.status));
          const datos = await r.json();
          if (Array.isArray(datos.eventos)) eventos = eventos.concat(datos.eventos);
          if (!datos.recortado || !(datos.siguiente > d)) break;
          d = datos.siguiente;
        }
        return eventos.filter(ev => ev && Number.isFinite(ev.t)).map(eventoSano).filter(ev => ev && ev.s);
      } finally {
        clearTimeout(reloj);
      }
    }

    async function empezarRepite(desde, hasta, titulo, delDia) {
      if (repite.activa || repite.cargando || probar.disabled) return;
      repite.cargando = true;
      repetir.disabled = true;
      let eventos = null;
      try { eventos = await pedirHistoria(desde, hasta); } catch (x) {}
      repite.cargando = false;
      if (!eventos) {
        repetir.disabled = false;
        aviso('No pude leer la historia: ¿está prendido el servidor?');
        return;
      }
      if (delDia) {
        const hoy = new Date();
        hoy.setHours(0, 0, 0, 0);
        const deHoy = eventos.filter(ev => ev.t >= hoy.getTime() / 1000);
        if (deHoy.length >= MINIMO_DEL_DIA) eventos = deHoy;
        else titulo = 'Las últimas 24 h';
      }
      if (!eventos.length) {
        repetir.disabled = false;
        aviso('No hay nada para repetir en ese tramo');
        return;
      }
      cerrarAusencia();
      const activo = prepararLinea(eventos);
      const pausas = eventos.filter(ev => ev._pausa).length;
      clearTimeout(repite.cierre);
      Object.assign(repite, {
        activa: true, eventos, i: 0, va: 0, pausaHasta: 0, detenida: false, tPrev: performance.now(), pendientes: [], cola: [], fin: 0, hora: '', cifras: '',
        vel: velocidadCercana(activo / Math.max(20, DURACION_IDEAL - pausas * PAUSA_REAL / 1000)),
        t0: eventos[0].t, t1: eventos[eventos.length - 1].t, cuentas: { mensajes: 0, commits: 0, agentes: new Set(), notas: new Set() }
      });
      guardarVivo();
      if (estado.vista !== 'grafo') cambiarVista('grafo');
      probar.disabled = true;
      caja.classList.add('repitiendo');
      repetir.textContent = 'Repitiendo…';
      const f0 = fechaLarga(repite.t0);
      const f1 = fechaLarga(repite.t1);
      reloj.fecha.textContent = titulo + ' · ' + (f0 === f1 ? f0 : 'del ' + f0 + ' al ' + f1);
      reloj.pausa.textContent = '';
      reloj.pausar.textContent = 'Pausa';
      reloj.pausar.setAttribute('aria-pressed', 'false');
      reloj.el.hidden = false;
      pintarVel();
      pintarFranja(reloj.franja, eventos.map(ev => [ev.t, 1]), repite.t0, repite.t1);
      pintarReloj();
      repite.reloj = setInterval(pasoRepite, 1000 / POR_SEGUNDO);
    }

    function terminarRepite() {
      clearTimeout(repite.cierre);
      if (!repite.activa) return;
      repite.activa = false;
      clearInterval(repite.reloj);
      repite.eventos = [];
      repite.pendientes = [];
      reloj.el.hidden = true;
      try {
        restaurarVivo();
        const cola = repite.cola.splice(0);
        let lista = [];
        let reemplaza = false;
        cola.forEach(([tipo, dato]) => {
          if (tipo === 'previos') { lista = dato.slice(); reemplaza = true; }
          else lista.push(dato);
        });
        if (lista.length || reemplaza) aplicarPrevios(lista, !reemplaza);
        if (cola.length && vivo.uso) cargarUso();
        recalcularCabeza();
        pintarChats();
        asegurarChats();
        pedirDibujo();
      } catch (error) {
        console.error('Neuromapa: no pude volver al vivo después de repetir:', error);
      } finally {
        probar.disabled = false;
        caja.classList.remove('repitiendo');
        repetir.disabled = false;
        repetir.textContent = 'Repetir el día';
      }
    }

    repetir.addEventListener('click', () => {
      const ahora = Date.now() / 1000;
      empezarRepite(ahora - 86400, ahora, 'Hoy', true);
    });
    reloj.menos.addEventListener('click', () => cambiarVelocidad(-1));
    reloj.mas.addEventListener('click', () => cambiarVelocidad(1));
    reloj.pausar.addEventListener('click', () => {
      repite.detenida = !repite.detenida;
      repite.tPrev = performance.now();
      reloj.pausar.textContent = repite.detenida ? 'Seguir' : 'Pausa';
      reloj.pausar.setAttribute('aria-pressed', String(repite.detenida));
    });
    $('#repite-salir').addEventListener('click', terminarRepite);

    const ausencia = { el: $('#ausencia'), cuando: $('#ausencia-cuando'), cifras: $('#ausencia-cifras'), franja: $('#ausencia-franja'), desde: 0, hasta: 0, pedido: 0 };
    function cerrarAusencia() {
      ausencia.pedido++;
      ausencia.el.hidden = true;
    }

    async function historiaPorMinuto(desde, hasta) {
      const control = new AbortController();
      const reloj = setTimeout(() => control.abort(), ESPERA_HISTORIA);
      try {
        const r = await fetch('/historia?modo=minuto&desde=' + desde.toFixed(3) + '&hasta=' + hasta.toFixed(3), { cache: 'no-store', signal: control.signal });
        if (!r.ok) throw new Error('el servidor contestó ' + r.status);
        return await r.json();
      } catch (e) {
        if (e && e.name === 'AbortError') throw new Error('el servidor no contestó en ' + Math.round(ESPERA_HISTORIA / 1000) + ' s');
        throw e;
      } finally {
        clearTimeout(reloj);
      }
    }

    async function mostrarAusencia(desde, hasta) {
      if (!ausencia.el.hidden) desde = Math.min(desde, ausencia.desde);
      const pedido = ++ausencia.pedido;
      let datos = null;
      try {
        datos = await historiaPorMinuto(desde, hasta);
      } catch (x) {}
      const tot = datos && datos.totales;
      if (pedido !== ausencia.pedido || repite.activa || repite.cargando || !tot || !tot.eventos) return;
      ausencia.desde = desde;
      ausencia.hasta = hasta;
      ausencia.cuando.textContent = 'De las ' + horaCorta(desde) + ' a las ' + horaCorta(hasta) + ' · ' + duracion(hasta - desde);
      const notas = lista => new Set((Array.isArray(lista) ? lista : []).map(r => porRuta.get(clave(String(r)))).filter(Boolean)).size;
      const cifras = [
        [tot.usuario, 'mensaje tuyo', 'mensajes tuyos'],
        [tot.commit, 'commit', 'commits'],
        [notas(tot.editadas), 'nota editada', 'notas editadas'],
        [notas(tot.leidas), 'nota leída', 'notas leídas'],
        [tot.agentes, 'agente', 'agentes'],
        [Array.isArray(tot.chats) ? tot.chats.length : 0, 'chat', 'chats'],
        [tot.espera, 'vez esperó tu OK', 'veces esperó tu OK'],
        [tot.falla, 'falla', 'fallas'],
        [tot.compacta, 'compactación', 'compactaciones']
      ].filter(x => Number(x[0]) > 0);
      if (!cifras.length) cifras.push([tot.eventos, 'acción', 'acciones']);
      ausencia.cifras.textContent = '';
      cifras.slice(0, 6).forEach(([n, uno, varios]) => {
        const d = document.createElement('div');
        const dt = document.createElement('dt');
        const dd = document.createElement('dd');
        dd.textContent = Number(n).toLocaleString('es');
        dt.textContent = Number(n) === 1 ? uno : varios;
        d.append(dt, dd);
        ausencia.cifras.appendChild(d);
      });
      ausencia.el.hidden = false;
      pintarFranja(ausencia.franja, (Array.isArray(datos.minutos) ? datos.minutos : []).map(m => [Number(m.t) + 30, Number(m.n) || 0]), desde, hasta);
    }

    vivo.resumenDia = async () => {
      const hasta = Date.now() / 1000;
      const pedir = desde => historiaPorMinuto(desde, hasta);
      const hoy = new Date();
      hoy.setHours(0, 0, 0, 0);
      let titulo = 'Hoy';
      let datos = await pedir(hoy.getTime() / 1000);
      if (!datos.totales || (Number(datos.totales.eventos) || 0) < MINIMO_DEL_DIA) {
        datos = await pedir(hasta - 86400);
        titulo = 'Las últimas 24 h';
      }
      const tot = datos.totales || {};
      const nota = r => porRuta.get(clave(String(r)));
      const cuentas = new Map();
      (Array.isArray(tot.tocadas) ? tot.tocadas : []).forEach(par => {
        const n = Array.isArray(par) ? nota(par[0]) : null;
        if (n) cuentas.set(n, (cuentas.get(n) || 0) + (Number(par[1]) || 0));
      });
      const lista = x => Array.isArray(x) ? x : [];
      const editadas = new Set(lista(tot.editadas).map(nota).filter(Boolean)).size;
      const tocadas = new Set(lista(tot.editadas).concat(lista(tot.leidas)).map(nota).filter(Boolean)).size;
      return { titulo, desde: datos.desde, hasta: datos.hasta, tot, minutos: lista(datos.minutos), editadas, tocadas,
               notas: [...cuentas].sort((a, b) => b[1] - a[1]) };
    };

    $('#ausencia-cerrar').addEventListener('click', cerrarAusencia);
    $('#ausencia-repetir').addEventListener('click', () => empezarRepite(ausencia.desde, ausencia.hasta, 'Mientras no estabas', false));
    let ocultaDesde = document.hidden ? Date.now() / 1000 : 0;
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        if (!ocultaDesde) ocultaDesde = Date.now() / 1000;
        return;
      }
      const desde = ocultaDesde;
      const hasta = Date.now() / 1000;
      ocultaDesde = 0;
      if (desde && hasta - desde >= AUSENCIA && !repite.activa && !repite.cargando) mostrarAusencia(desde, hasta);
    });

    let guardado = null;
    try { guardado = localStorage.getItem('cerebro-color'); } catch (e) {}
    if (guardado === 'uso') ponerColor(true);

    let reintentos = 0;
    function conectar() {
      const fuente = new EventSource('/eventos');
      fuente.addEventListener('open', () => {
        reintentos = 0;
        caja.classList.add('conectado');
        estadoTxt.textContent = 'conectado';
        encenderBrasas();
        if (!DATOS.aprendizajeEnVivo) { DATOS.aprendizajeEnVivo = true; construirAprendido(); }
      });
      fuente.addEventListener('aprendido', e => {
        let datos = null;
        try { datos = JSON.parse(e.data); } catch (x) { return; }
        DATOS.aprendido = datos && typeof datos === 'object' ? datos : null;
        construirAprendido();
        if (DATOS.aprendido) actualizarCaminos(DATOS.aprendido.caminos);
      });
      fuente.addEventListener('error', () => {
        caja.classList.remove('conectado');
        if (fuente.readyState !== EventSource.CLOSED) {
          estadoTxt.textContent = 'sin conexión, reintentando…';
          return;
        }
        reintentos++;
        const espera = Math.min(60, 5 * reintentos);
        estadoTxt.textContent = 'sin conexión: el mapa se apagó o cambió la clave. Pruebo de nuevo en ' + espera
          + ' s; si sigue así, recargá la página o abrilo de nuevo.';
        setTimeout(conectar, espera * 1000);
      });
      fuente.addEventListener('previos', e => {
        let lista = [];
        try { lista = JSON.parse(e.data); } catch (x) {}
        lista = Array.isArray(lista) ? lista.map(eventoSano).filter(Boolean) : [];
        if (repite.activa) repite.cola.push(['previos', lista]);
        else aplicarPrevios(lista, false);
      });
      fuente.addEventListener('accion', e => {
        let ev = null;
        try { ev = eventoSano(JSON.parse(e.data)); } catch (x) { return; }
        if (!ev) return;
        if (!repite.activa) recibirSeguro(ev);
        else if (repite.cola.length < COLA_TOPE) repite.cola.push(['accion', ev]);
      });
      fuente.addEventListener('cambio', () => { recargar.hidden = false; });
    }
    conectar();

    function aplicarPrevios(lista, sumar) {
      if (!sumar) filas.textContent = '';
      lista.filter(ev => ev.e !== 'pre').slice(-6).forEach(ev => fila(ev, true));
      lista.forEach(recordarPista);
      lista.forEach(ev => anotarRio(ev, false));
      const umbralArchivos = archivosT;
      lista.forEach(ev => { if (ev.t > umbralArchivos) anotarArchivo(ev); });
      pintarProgramando();
      for (let i = lista.length - 1; i >= 0; i--) {
        const n = notaDe(lista[i]);
        if (n) { vivo.previo = n; break; }
      }
      const ahora = performance.now();
      const ultimo = brasas.ultimoT;
      lista.forEach(ev => {
        if (!ev.t || ev.t <= ultimo) return;
        brasas.ultimoT = Math.max(brasas.ultimoT, ev.t);
        const hace = Math.max(0, Date.now() / 1000 - ev.t) * 1000;
        if (hace < VENTANA_TOQUES) brasaDe(ev, notaDe(ev), ahora - hace);
      });
      encenderBrasas();
      lista.forEach(ev => {
        const c = chatDe(ev);
        if (!c) return;
        const hace = Math.max(0, Date.now() / 1000 - (ev.t || 0)) * 1000;
        c.tUlt = ahora - hace;
        const n = destinoDe(ev);
        if (n && (!ev.a || !c.hacia)) { c.hacia = ev.a ? anclaDeChat(ev, n) : n; c.desde = null; }
        if (ev.e === 'fin' || ev.e === 'inicio') { c.estado = 'listo'; c.tFin = ahora - hace; }
        else if (ev.e === 'cierre') { c.estado = 'cerrado'; c.tFin = ahora - hace; }
        else if (ev.e === 'espera') c.estado = 'esperando';
        else if (ev.e === 'compacta') c.estado = 'compactando';
        else c.estado = 'trabajando';
      });
      chats.forEach(c => {
        if (c.estado !== 'listo' && c.estado !== 'cerrado' && ahora - c.tUlt > CHAT_QUIETO) { c.estado = 'listo'; c.tFin = c.tUlt; }
      });
      const umbral = memoriaT;
      lista.forEach(ev => { if (!ev.t || ev.t > umbral) memoriaEvento(ev, false); });
      recalcularCabeza();
      pintarChats();
      asegurarChats();
    }
  }

  iniciarVivo();
